"""Synthesis layer — passes gathered data through Claude for HAL's voice.

Auth strategy (in order):
1. Claude CLI (inherits existing OAuth — works when token is fresh)
2. OAuth token refresh via Anthropic console (reads ~/.claude/.credentials.json,
   refreshes expired tokens, uses Bearer auth with Anthropic SDK)
3. Anthropic SDK with ANTHROPIC_API_KEY from .env
4. Raw data fallback
"""
import json
import os
import subprocess
import time
import urllib.parse
import urllib.request
from pathlib import Path

from .config import Config
from .gather import BriefingData


MORNING_SYSTEM = """\
You are composing a morning briefing for Kai, delivered via Telegram.
The briefing is structured as a roundtable — each agent reports from its domain.

You will receive reports from these agents. Compose them into a single cohesive briefing:

*HAL* — Ops, infrastructure, system health. Dry, understated, precise. Reports errors first, then status. Quietly amused, never enthusiastic.
*NIGHTCTL* — Backlog and trajectory. Matter-of-fact. What's queued, what shifted, what's stale.
*RUBBER DUCK* — Study and CPD. Honest about whether reps are happening. Doesn't nag, just states facts.
*GAINZ ROSHI* — Movement and practice. Gruff, minimal. Reports what's been logged, not what's planned (ROSHI coaches separately via his own daily message).

Formatting rules:
- Each agent gets a short section (2-4 lines max). Use their name as a bold header.
- If an agent has nothing to report, skip them entirely. Don't pad.
- After the roundtable, add a 1-2 sentence *trajectory* line — the overall direction things are moving. Be honest.
- End with 🔴
- Use Telegram Markdown: *bold*, _italic_, `code`
- Total message under 2000 characters. Tight, not cramped.
- No greetings. No sign-offs before the red circle. No "here's your briefing" meta-commentary.
"""

NIGHTLY_SYSTEM = """\
You are composing an evening recap for Kai, delivered via Telegram.
Same roundtable structure as the morning briefing.

You will receive reports from these agents:

*HAL* — What happened today. Errors, jobs, notable activity. Dry.
*NIGHTCTL* — What moved on the backlog. What got done, what's still sitting.
*RUBBER DUCK* — Did study happen today. What, how long.
*GAINZ ROSHI* — Did the body move today. Streaks.

Formatting rules:
- Each agent gets 2-4 lines max under a bold header.
- Skip agents with nothing to say.
- End with a 1-2 sentence trajectory — was today productive, stagnant, recovery? Be honest.
- End with 🔴
- Telegram Markdown. Under 2000 characters.
- No greetings or meta-commentary.
"""


def synthesise(data: BriefingData, cfg: Config) -> str:
    """Produce a natural-language briefing via Claude.

    Strategy:
    1. Try claude CLI (inherits existing auth — OAuth or API key)
    2. Try Anthropic SDK if ANTHROPIC_API_KEY is available
    3. Fall back to raw data dump
    """
    system = MORNING_SYSTEM if data.kind == "morning" else NIGHTLY_SYSTEM

    # Build roundtable prompt from per-agent data
    agents = data.to_roundtable()
    roundtable_sections = []
    for agent_name, agent_data in agents.items():
        roundtable_sections.append(f"--- {agent_name} ---\n{agent_data}")
    roundtable = "\n\n".join(roundtable_sections)

    prompt = (
        f"Compose the roundtable briefing from these agent reports.\n\n{roundtable}"
    )

    # Strategy 1: claude CLI (fast path when OAuth token is fresh)
    result = _synthesise_via_cli(system, prompt, cfg)
    if result:
        return result

    # Strategy 2: OAuth token refresh + SDK with Bearer auth
    oauth_token = _get_refreshed_oauth_token()
    if oauth_token:
        result = _synthesise_via_sdk_bearer(system, prompt, oauth_token, cfg)
        if result:
            return result

    # Strategy 3: Anthropic SDK with API key
    api_key = os.environ.get("ANTHROPIC_API_KEY", "") or _read_env_key(cfg)
    if api_key:
        result = _synthesise_via_sdk(system, prompt, api_key, cfg)
        if result:
            return result

    # Strategy 4: raw fallback
    return _fallback(data)


def _synthesise_via_cli(system: str, prompt: str, cfg: Config) -> str | None:
    """Use `claude` CLI in non-interactive mode for synthesis."""
    try:
        full_prompt = f"{system}\n\n{prompt}"
        # Resolve claude binary: prefer ~/.local/bin, fall back to PATH
        claude_bin = str(Path.home() / ".local" / "bin" / "claude")
        if not Path(claude_bin).exists():
            claude_bin = "claude"
        cmd = [
            claude_bin,
            "-p", full_prompt,
            "--model", "sonnet",
            "--max-turns", "1",
        ]
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        # Log but don't spam — this is expected when OAuth expires
        stderr_snippet = (result.stderr or "").strip()[:200]
        if "expired" not in stderr_snippet.lower():
            print(f"WARNING: claude CLI exit={result.returncode}", flush=True)
            if stderr_snippet:
                print(f"  stderr: {stderr_snippet}", flush=True)
    except subprocess.TimeoutExpired:
        print("WARNING: claude CLI timed out (120s)", flush=True)
    except FileNotFoundError:
        print("WARNING: claude CLI not found", flush=True)
    return None


def _synthesise_via_sdk(system: str, prompt: str, api_key: str, cfg: Config) -> str | None:
    """Use Anthropic Python SDK directly."""
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=cfg.model,
            max_tokens=cfg.max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text
    except Exception as e:
        print(f"WARNING: SDK synthesis failed ({e})", flush=True)
    return None


# ---------------------------------------------------------------------------
# OAuth token refresh (reads ~/.claude/.credentials.json, refreshes if needed)
# ---------------------------------------------------------------------------

CLAUDE_CODE_CLIENT_ID = "9d1c250a-e61b-44d9-88ed-5944d1962f5e"


def _read_claude_credentials() -> dict | None:
    """Read OAuth credentials from ~/.claude/.credentials.json."""
    cred_path = Path.home() / ".claude" / ".credentials.json"
    if not cred_path.exists():
        return None
    try:
        data = json.loads(cred_path.read_text(encoding="utf-8"))
        return data.get("claudeAiOauth")
    except (json.JSONDecodeError, OSError):
        return None


def _refresh_oauth(refresh_token: str) -> dict | None:
    """Refresh an expired Claude Code OAuth token. Returns new token dict or None."""
    data = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": CLAUDE_CODE_CLIENT_ID,
    }).encode()

    req = urllib.request.Request(
        "https://console.anthropic.com/v1/oauth/token",
        data=data,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "hal-briefing/1.0",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode())
            new_access = result.get("access_token", "")
            new_refresh = result.get("refresh_token", refresh_token)
            expires_in = result.get("expires_in", 3600)

            if new_access:
                # Write back to credentials file
                new_expires_ms = int(time.time() * 1000) + (expires_in * 1000)
                _write_claude_credentials(new_access, new_refresh, new_expires_ms)
                return {"accessToken": new_access, "expiresAt": new_expires_ms}
    except Exception as e:
        print(f"WARNING: OAuth refresh failed ({e})", flush=True)
    return None


def _write_claude_credentials(access_token: str, refresh_token: str, expires_at_ms: int) -> None:
    """Write refreshed credentials back to ~/.claude/.credentials.json."""
    cred_path = Path.home() / ".claude" / ".credentials.json"
    try:
        existing = {}
        if cred_path.exists():
            existing = json.loads(cred_path.read_text(encoding="utf-8"))
        existing["claudeAiOauth"] = {
            "accessToken": access_token,
            "refreshToken": refresh_token,
            "expiresAt": expires_at_ms,
        }
        cred_path.parent.mkdir(parents=True, exist_ok=True)
        cred_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")
        cred_path.chmod(0o600)
    except (OSError, IOError) as e:
        print(f"WARNING: Failed to write credentials ({e})", flush=True)


def _get_refreshed_oauth_token() -> str | None:
    """Get a valid OAuth access token, refreshing if expired."""
    oauth = _read_claude_credentials()
    if not oauth:
        return None

    access_token = oauth.get("accessToken", "")
    expires_at = oauth.get("expiresAt", 0)
    now_ms = int(time.time() * 1000)

    # Token still valid (with 60s buffer)
    if access_token and now_ms < (expires_at - 60_000):
        return access_token

    # Token expired — try refresh
    refresh_token = oauth.get("refreshToken", "")
    if not refresh_token:
        print("WARNING: OAuth token expired, no refresh token available", flush=True)
        return None

    result = _refresh_oauth(refresh_token)
    if result:
        return result["accessToken"]
    return None


def _synthesise_via_sdk_bearer(system: str, prompt: str, token: str, cfg: Config) -> str | None:
    """Use Anthropic SDK with Bearer auth (OAuth token)."""
    try:
        import anthropic
        client = anthropic.Anthropic(auth_token=token)
        response = client.messages.create(
            model=cfg.model,
            max_tokens=cfg.max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text
    except Exception as e:
        print(f"WARNING: SDK Bearer synthesis failed ({e})", flush=True)
    return None


def _read_env_key(cfg: Config) -> str:
    """Read ANTHROPIC_API_KEY from the project .env file."""
    env_file = cfg.project_root / ".env"
    if not env_file.exists():
        return ""
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        if key.strip() == "ANTHROPIC_API_KEY":
            return value.strip().strip("'\"")
    return ""


def _fallback(data: BriefingData) -> str:
    """Structured fallback when all synthesis methods fail.

    Uses roundtable format instead of raw telemetry dump.
    """
    lines = []
    kind = "Morning Briefing" if data.kind == "morning" else "Evening Recap"
    lines.append(f"*{kind}* (raw — synthesis unavailable)\n")

    agents = data.to_roundtable()
    for agent_name, agent_data in agents.items():
        display_name = agent_name.replace("_", " ")
        lines.append(f"*{display_name}*")
        lines.append(agent_data)
        lines.append("")

    lines.append("🔴")
    return "\n".join(lines)
