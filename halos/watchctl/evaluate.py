"""LLM-as-judge evaluator — sends transcript + rubric, validates output."""

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import httpx

from .rubric import Rubric
from .feed import VideoEntry


@dataclass
class Evaluation:
    scores: dict[str, dict]       # {criterion: {score: int, note: str}}
    overall: float
    verdict: str
    summary: str
    goodies: list[dict]           # [{tier: str, item: str}]
    tags: list[str]
    related_notes: list[str]
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    model: str = ""


class EvalError(Exception):
    """Raised when evaluation fails."""

    def __init__(self, message: str, error_type: str = "EVAL_ERROR"):
        super().__init__(message)
        self.error_type = error_type


def build_prompt(video: VideoEntry, transcript: str, rubric: Rubric) -> str:
    """Construct the evaluation prompt."""
    return f"""You are an expert content evaluator. Evaluate the following YouTube video transcript against the provided rubric.

## Video Metadata
- **Title:** {video.title}
- **Channel:** {video.channel_name}
- **Published:** {video.published.isoformat()}
- **URL:** {video.url}

## Rubric: {rubric.name} (v{rubric.version})
{rubric.description}

### Criteria
{rubric.criteria_prompt()}

### Verdict Thresholds
{json.dumps(rubric.verdict_thresholds, indent=2)}

## Instructions
1. Read the full transcript carefully.
2. Score each criterion on its scale with a one-line justification.
3. Compute the weighted overall score.
4. Assign a verdict based on the thresholds.
5. Write a 5-10 sentence summary of the video content.
6. Extract actionable goodies, classified as HIGH, MEDIUM, or LOW value.
7. Suggest Obsidian tags (lowercase, hyphenated).
8. Suggest related note titles if you recognise topics that might connect to other notes.

## Output Format
Respond with ONLY a JSON object (no markdown fences, no commentary):
{{
  "scores": {{
    "<criterion_name>": {{"score": <int>, "note": "<one-line justification>"}},
    ...
  }},
  "overall": <float>,
  "verdict": "<REQUIRED|WATCH|SKIM|SKIP>",
  "summary": "<5-10 sentences>",
  "goodies": [
    {{"tier": "HIGH", "item": "<description>"}},
    {{"tier": "MEDIUM", "item": "<description>"}},
    {{"tier": "LOW", "item": "<description>"}}
  ],
  "tags": ["tag1", "tag2"],
  "related_notes": ["Note Title 1", "Note Title 2"]
}}

## Transcript
{transcript}"""


def _load_env() -> None:
    """Load .env from project root if not already in environment."""
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        key, val = key.strip(), val.strip().strip('"').strip("'")
        if key and val and key not in os.environ:
            os.environ[key] = val


def _call_llm(prompt: str, model: str) -> tuple[str, int, int]:
    """Call LLM and return (response_text, input_tokens, output_tokens).

    Strategy:
    1. If ANTHROPIC_API_KEY is set, use the Anthropic API directly.
    2. If GROQ_API_KEY is set, use Groq (fast, cheap, good for eval).
    3. Otherwise, use the `claude` CLI which handles OAuth automatically.
    """
    _load_env()
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
    groq_key = os.environ.get("GROQ_API_KEY", "")

    if anthropic_key:
        return _call_anthropic_api(prompt, model, anthropic_key)
    elif groq_key:
        return _call_groq_api(prompt, model, groq_key)
    else:
        return _call_claude_cli(prompt, model)


def _call_anthropic_api(prompt: str, model: str, api_key: str) -> tuple[str, int, int]:
    """Direct Anthropic API call."""
    r = httpx.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": model,
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=120,
    )

    if r.status_code != 200:
        raise EvalError(
            f"Anthropic API error {r.status_code}: {r.text[:500]}",
            error_type="EVAL_API_ERROR",
        )

    data = r.json()
    text = data["content"][0]["text"]
    usage = data.get("usage", {})
    return (
        text,
        usage.get("input_tokens", 0),
        usage.get("output_tokens", 0),
    )


def _call_groq_api(prompt: str, model: str, api_key: str) -> tuple[str, int, int]:
    """Call Groq API (OpenAI-compatible). Fast and cheap for eval tasks."""
    # Map generic model names to Groq models
    groq_model = {
        "sonnet": "llama-3.3-70b-versatile",
        "haiku": "llama-3.1-8b-instant",
    }.get(model, "llama-3.3-70b-versatile")

    r = httpx.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": groq_model,
            "max_tokens": 4096,
            "temperature": 0.3,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=120,
    )

    if r.status_code != 200:
        raise EvalError(
            f"Groq API error {r.status_code}: {r.text[:500]}",
            error_type="EVAL_API_ERROR",
        )

    data = r.json()
    text = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})
    return (
        text,
        usage.get("prompt_tokens", 0),
        usage.get("completion_tokens", 0),
    )


def _call_claude_cli(prompt: str, model: str) -> tuple[str, int, int]:
    """Call via claude CLI (handles OAuth/Claude Max automatically).

    Falls back to this when no API key is available. The claude CLI
    uses the Claude Max subscription through OAuth.
    """
    import subprocess
    import tempfile

    # Write prompt to temp file (too long for stdin pipe sometimes)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(prompt)
        prompt_path = f.name

    try:
        result = subprocess.run(
            ["claude", "-p", "--output-format", "json", "--model", model],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=180,
        )
    except FileNotFoundError:
        raise EvalError(
            "claude CLI not found. Install it or set ANTHROPIC_API_KEY.",
            "EVAL_AUTH_ERROR",
        )
    except subprocess.TimeoutExpired:
        raise EvalError("claude CLI timed out", "EVAL_TIMEOUT")
    finally:
        os.unlink(prompt_path)

    if result.returncode != 0:
        raise EvalError(
            f"claude CLI error: {result.stderr[:500]}",
            "EVAL_API_ERROR",
        )

    # Parse JSON output from claude CLI
    try:
        data = json.loads(result.stdout)
        text = data.get("result", result.stdout)
        # Claude CLI JSON output has 'result' for the text
        # and 'usage' for token counts
        usage = data.get("usage", {})
        return (
            text,
            usage.get("input_tokens", 0),
            usage.get("output_tokens", 0),
        )
    except json.JSONDecodeError:
        # Plain text output
        return (result.stdout, 0, 0)


def _parse_response(text: str, rubric: Rubric) -> dict:
    """Parse and validate the LLM JSON response."""
    # Strip markdown fences if present
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise EvalError(f"Invalid JSON from LLM: {e}", "EVAL_SCHEMA_INVALID")

    # Validate required fields
    required = ["scores", "overall", "verdict", "summary", "goodies", "tags"]
    missing = [f for f in required if f not in data]
    if missing:
        raise EvalError(
            f"Missing fields in LLM response: {missing}",
            "EVAL_SCHEMA_INVALID",
        )

    # Validate scores have all criteria
    for c in rubric.criteria:
        if c.name not in data["scores"]:
            raise EvalError(
                f"Missing criterion score: {c.name}",
                "EVAL_SCHEMA_INVALID",
            )

    # Validate verdict
    valid_verdicts = set(rubric.verdict_thresholds.keys()) | {"SKIP"}
    if data["verdict"] not in valid_verdicts:
        raise EvalError(
            f"Invalid verdict: {data['verdict']}",
            "EVAL_SCHEMA_INVALID",
        )

    return data


def evaluate(
    video: VideoEntry,
    transcript: str,
    rubric: Rubric,
    model: str = "claude-sonnet-4-5-20250514",
    max_retries: int = 1,
) -> Evaluation:
    """Run LLM-as-judge evaluation of a video transcript.

    Args:
        video: Video metadata.
        transcript: Plain text transcript.
        rubric: Loaded rubric with criteria and thresholds.
        model: Anthropic model ID.
        max_retries: Retries on schema validation failure.

    Returns:
        Evaluation dataclass with scores, verdict, goodies, etc.

    Raises:
        EvalError: On persistent failure.
    """
    prompt = build_prompt(video, transcript, rubric)

    last_error = None
    for attempt in range(1 + max_retries):
        try:
            text, in_tok, out_tok = _call_llm(prompt, model)
            data = _parse_response(text, rubric)

            # Recompute overall from rubric weights (don't trust LLM math)
            raw_scores = {
                name: info["score"]
                for name, info in data["scores"].items()
            }
            overall = rubric.compute_overall(raw_scores)
            verdict = rubric.score_to_verdict(overall)

            return Evaluation(
                scores=data["scores"],
                overall=overall,
                verdict=verdict,
                summary=data["summary"],
                goodies=data.get("goodies", []),
                tags=data.get("tags", []),
                related_notes=data.get("related_notes", []),
                input_tokens=in_tok,
                output_tokens=out_tok,
                model=model,
            )
        except EvalError as e:
            last_error = e
            if e.error_type != "EVAL_SCHEMA_INVALID":
                raise  # Don't retry non-schema errors

    raise last_error
