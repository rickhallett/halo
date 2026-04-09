"""Live query to an advisor via the Hermes HTTP API or direct LLM call.

Two modes:
  - Remote (default): POST to the advisor's gateway /v1/chat/completions
  - Local (--local):  Call Anthropic directly with persona as system prompt
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Iterator

import httpx

from .config import persona_path, resolve_url


def ask(
    advisor: str,
    prompt: str,
    *,
    url_override: str | None = None,
    session_id: str | None = None,
    system: str | None = None,
    stream: bool = True,
    timeout: float = 120.0,
    local: bool = False,
) -> str:
    """Send a prompt to the advisor and return the full response text.

    When local=True, calls Anthropic directly with the advisor's persona
    as system prompt — no gateway or cluster required.

    When stream=True (default), tokens are printed to stdout as they arrive.
    Returns the accumulated response either way.
    """
    if local:
        return _local_ask(advisor, prompt, system=system, stream=stream)

    base_url = resolve_url(advisor, url_override)
    endpoint = f"{base_url}/v1/chat/completions"

    messages: list[dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    body = {
        "messages": messages,
        "stream": stream,
    }

    headers: dict[str, str] = {"Content-Type": "application/json"}
    if session_id:
        headers["X-Hermes-Session-Id"] = session_id

    if stream:
        return _stream_response(endpoint, body, headers, timeout)
    else:
        return _blocking_response(endpoint, body, headers, timeout)


# ---------------------------------------------------------------------------
# Local mode — direct Anthropic SDK call with persona injection
# ---------------------------------------------------------------------------

def _resolve_api_key() -> str | None:
    """Resolve Anthropic API key from env or .env file."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return key
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("ANTHROPIC_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def _local_ask(
    advisor: str,
    prompt: str,
    *,
    system: str | None = None,
    stream: bool = True,
) -> str:
    """Call Anthropic directly with the advisor's persona as system prompt."""
    import anthropic

    api_key = _resolve_api_key()
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not available for local mode")

    # Load persona as system prompt
    pp = persona_path(advisor)
    if pp.exists():
        persona = pp.read_text()
    else:
        persona = f"You are {advisor}, an advisor in the Halo fleet."

    system_prompt = persona
    if system:
        system_prompt = f"{persona}\n\n---\n\n{system}"

    client = anthropic.Anthropic(api_key=api_key)

    if stream:
        chunks: list[str] = []
        with client.messages.stream(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            system=system_prompt,
            messages=[{"role": "user", "content": prompt}],
        ) as resp:
            for text in resp.text_stream:
                chunks.append(text)
                sys.stdout.write(text)
                sys.stdout.flush()
        sys.stdout.write("\n")
        sys.stdout.flush()
        return "".join(chunks)
    else:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            system=system_prompt,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text
        print(text)
        return text


def _stream_response(
    endpoint: str,
    body: dict,
    headers: dict[str, str],
    timeout: float,
) -> str:
    """SSE streaming — print tokens as they arrive, return accumulated text."""
    chunks: list[str] = []

    with httpx.Client(timeout=httpx.Timeout(timeout, connect=10.0)) as client:
        with client.stream("POST", endpoint, json=body, headers=headers) as resp:
            resp.raise_for_status()
            for chunk in _parse_sse(resp.iter_lines()):
                chunks.append(chunk)
                sys.stdout.write(chunk)
                sys.stdout.flush()

    # Newline after streamed output
    if chunks:
        sys.stdout.write("\n")
        sys.stdout.flush()

    return "".join(chunks)


def _blocking_response(
    endpoint: str,
    body: dict,
    headers: dict[str, str],
    timeout: float,
) -> str:
    """Non-streaming — wait for full response."""
    with httpx.Client(timeout=httpx.Timeout(timeout, connect=10.0)) as client:
        resp = client.post(endpoint, json=body, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    choices = data.get("choices", [])
    if not choices:
        return ""
    return choices[0].get("message", {}).get("content", "")


def _parse_sse(lines: Iterator[str]) -> Iterator[str]:
    """Parse OpenAI-format SSE stream, yielding content deltas."""
    for line in lines:
        if not line.startswith("data: "):
            continue
        payload = line[6:]
        if payload.strip() == "[DONE]":
            return
        try:
            obj = json.loads(payload)
            delta = obj.get("choices", [{}])[0].get("delta", {})
            content = delta.get("content")
            if content:
                yield content
        except (json.JSONDecodeError, IndexError, KeyError):
            continue
