# Codebase Concerns

**Analysis Date:** 2026-04-07

## Tech Debt

**TD-1: journalctl uses Claude CLI subprocess instead of proper client (Medium):**
- Issue: `halos/journalctl/window.py` shells out to `claude -p` CLI binary for LLM synthesis instead of using the Anthropic Python SDK directly. This creates a hard dependency on the `claude` CLI being installed and authenticated, with no retry or rate-limit handling.
- Files: `halos/journalctl/window.py` (lines 90-103)
- Impact: Window synthesis silently fails when CLI is missing or OAuth expired. No retry logic. 120s hard timeout with no backoff. Falls back to raw text dump which loses the value of the summary.
- Fix approach: Replace `subprocess.run(["claude", ...])` with direct Anthropic SDK call using the same multi-strategy auth pattern already implemented in `halos/briefings/synthesise.py` (SDK with API key, OAuth token refresh, CLI fallback). Add retry with exponential backoff.

**TD-3: No HTTP health check sidecar for multi-tenant deployment (Medium):**
- Issue: The heartbeat wrapper in `docker/entrypoint.sh` detects process death but NOT asyncio deadlocks. A file-based heartbeat (touch every 30s, liveness probe at 120s) is the only health signal.
- Files: `docker/entrypoint.sh` (lines 232-269)
- Impact: An agent stuck in an asyncio deadlock continues to appear healthy. K8s will not restart the pod. This is acceptable for single-tenant but blocks multi-tenant deployment.
- Fix approach: Add an in-process HTTP health endpoint (e.g., aiohttp on localhost:8080/healthz) that proves the event loop is responsive. Wire K8s liveness probe to HTTP instead of file staleness.

**TD-4: pip usage in Dockerfile violates uv-only policy (Low):**
- Issue: The Dockerfile uses `pip install` for all Python dependency installation instead of `uv`, violating the repo's standing order that Python uses uv exclusively.
- Files: `Dockerfile` (lines 29, 36, 42, 47)
- Impact: Inconsistency between local dev (uv) and container build (pip). Potential for dependency resolution differences. Low severity because container builds are isolated.
- Fix approach: Install uv in the container image and replace `pip install` with `uv pip install` (or `uv sync` with the lockfile).

**TD-5: No automated integration test for container build (Medium):**
- Issue: No CI job or test that builds the Docker image and validates it starts successfully.
- Files: `Dockerfile`, `docker/entrypoint.sh`
- Impact: Container regressions are caught only during manual deployment. The entrypoint has complex bootstrap logic (env generation, WAL mode, NATS hooks, cron setup) that could break silently.
- Fix approach: Add a CI step that builds the image, runs it with mock env vars, and asserts the heartbeat file appears within 60s.

**TD-6: Legacy todoctl module still registered (Low):**
- Issue: `todoctl` is superseded by `nightctl` (migration path exists at `halos/nightctl/migrate_todoctl.py`), but `todoctl` is still registered as a console script in `pyproject.toml` and has active test files.
- Files: `pyproject.toml` (line 53: `todoctl`), `halos/todoctl/`, `tests/todoctl/`
- Impact: Dead code increases maintenance surface. New contributors may be confused about which module to use.
- Fix approach: Remove `todoctl` entry from `pyproject.toml` scripts, archive or delete `halos/todoctl/` and `tests/todoctl/`.

**TD-7: Widespread bare `except Exception` with silent swallowing (Medium):**
- Issue: 104 occurrences of `except Exception` across 45 files in `halos/`, many of which silently swallow errors with `pass` or `return None/""`. While some are intentional (resilience in briefing gathering), many hide real bugs.
- Files: Highest concentrations in `halos/halctl/behavioral_smoke.py` (15), `halos/calctl/sources.py` (7), `halos/halctl/cli.py` (8), `halos/halctl/supervisor.py` (5), `halos/halctl/health.py` (5)
- Impact: Errors in data collection, parsing, and health checks are silently swallowed. Debugging failures requires adding logging after the fact.
- Fix approach: Audit each `except Exception` block. Keep intentional ones (briefing resilience) but add `hlog` calls. Replace silent `pass` blocks with at minimum a log line. Use specific exception types where possible.

**TD-8: Hardcoded paths assume macOS dev machine layout (Medium):**
- Issue: Multiple modules hardcode `Path.home() / "code" / "halo"` or `Path.home() / "code" / "halfleet"` which only works on the developer's machine.
- Files:
  - `halos/hal.py` line 17: `AGENT_DIR = Path.home() / "code" / "halo" / "agent"`
  - `halos/halctl/supervisor.py` line 31: `LOG_DIR = Path.home() / "code" / "halo" / "logs"`
  - `halos/halctl/supervisor.py` line 309: `Path.home() / "code" / "halo" / "data" / "supervisor"`
  - `halos/halctl/config.py` line 48: `Path.home() / "code" / "halfleet"`
- Impact: These paths break in containers, CI, or any non-standard dev environment. The container overrides via `HERMES_HOME` but the Python-side hardcoding is fragile.
- Fix approach: Derive paths from environment variables or config files. Use `HALO_ROOT` env var with fallback to the `pyproject.toml` location via `Path(__file__).resolve().parents[N]`.

**TD-9: hal.py references deleted agent modules (Low):**
- Issue: `halos/hal.py` AGENT_MODULES dict references `steer` (GUI automation) which was deleted in the heritage sweep. Running `hal steer` will fail with a confusing `execvp` error.
- Files: `halos/hal.py` lines 44-55
- Impact: Minor UX issue. The `steer` command appears in help but doesn't work.
- Fix approach: Remove `steer` from AGENT_MODULES dict.

## Security Considerations

**Unix Socket secretctl daemon has no authentication:**
- Risk: Any local process owned by the same user can connect to the secretctl Unix socket and resolve 1Password secrets without biometric re-authentication.
- Files: `halos/secretctl/daemon.py` (lines 160-164)
- Current mitigation: Socket permissions are 0o600 (owner-only). 30-minute auto-expiry TTL. Single-user system.
- Recommendations: For multi-user environments, add a bearer token written to a per-session file at daemon start. Current mitigation is adequate for single-operator use.

**OAuth credential management in briefings/synthesise.py:**
- Risk: The briefings module reads, refreshes, and writes back OAuth tokens to `~/.claude/.credentials.json`. A bug in `_write_claude_credentials` could corrupt the credential file.
- Files: `halos/briefings/synthesise.py` (lines 160-228)
- Current mitigation: File permissions set to 0o600. Write operation is within try/except.
- Recommendations: Add atomic write (write to tmp file, then rename) to prevent corruption on partial write. The current direct write_text is not crash-safe.

**Custom .env parser in multiple modules:**
- Risk: Multiple modules implement their own `.env` file parsing (split on `=`, strip quotes) rather than using a library like `python-dotenv`. Inconsistent parsing could lead to different modules reading different values from the same file.
- Files: `halos/briefings/deliver.py` (lines 31-35), `halos/briefings/synthesise.py` (lines 274-285), `halos/watchctl/evaluate.py` (lines 91-103)
- Current mitigation: The parsing is simple and consistent across instances.
- Recommendations: Consolidate into a single `halos.common.env` utility or add `python-dotenv` as a dependency.

## Performance Bottlenecks

**Subprocess-heavy data gathering in briefings:**
- Problem: `halos/briefings/gather.py` spawns 5+ subprocesses sequentially to collect data (dashctl, logctl, agentctl, git-pulse.sh, mailctl). Each has a 10-15s timeout.
- Files: `halos/briefings/gather.py` (lines 312-405)
- Cause: Each data source is collected via `subprocess.run()` with sequential execution. Worst case: 60s+ if all timeout.
- Improvement path: Run data collection concurrently using `concurrent.futures.ThreadPoolExecutor` or import the modules directly instead of spawning subprocesses (most are already Python and importable).

**behavioral_smoke.py is 2297 lines:**
- Problem: Single monolithic file containing all behavioral smoke test scenarios, validators, and harness code.
- Files: `halos/halctl/behavioral_smoke.py` (2297 lines)
- Cause: Organic growth of test scenarios without refactoring into separate modules.
- Improvement path: Extract scenarios into individual files under `halos/halctl/behavioral_scenarios/`. Keep the harness/runner in the main file.

## Fragile Areas

**nightctl executor with shell=True:**
- Files: `halos/nightctl/executor.py` (lines 237-244), `halos/cronctl/cli.py` (line 180)
- Why fragile: Jobs with `shell: true` in their config pass commands directly to `/bin/sh`. While this is by design (cron-like execution), any malformed command or unexpected shell metacharacters could cause issues.
- Safe modification: Always validate command strings before execution. Never construct commands from user input without sanitization.
- Test coverage: `tests/nightctl/test_executor.py` exists but does not test shell=True paths with edge-case inputs.

**Entrypoint.sh inline Python for NATS hooks:**
- Files: `docker/entrypoint.sh` (lines 62-148)
- Why fragile: A full Python module (NATS event hook handler) is embedded inline in the entrypoint via heredoc. Any syntax error in the embedded Python silently fails. No tests cover the generated hook code.
- Safe modification: Extract the hook handler to a proper Python file in `docker/` or `halos/`. Copy it during container build instead of generating at runtime.
- Test coverage: None for the generated hook code.

**SQLite databases without connection pooling:**
- Files: Every module using sqlite3 (26+ files) creates connections ad-hoc with `sqlite3.connect()`.
- Why fragile: No connection pooling, no shared connection management. WAL mode is enforced at container startup but not guaranteed in local dev. Concurrent writes from multiple processes (briefings, nightctl executor, event consumer) could hit SQLITE_BUSY.
- Safe modification: Use the WAL enforcement pattern from entrypoint.sh in Python module init. Consider a shared connection factory in `halos/common/`.
- Test coverage: No tests for concurrent database access patterns.

## Test Coverage Gaps

**Modules with zero test coverage:**
- What's not tested: `halos/mailctl/`, `halos/secretctl/`, `halos/telemetry/`, `halos/blogctl/`, `halos/halyt/`
- Files: All Python files in those directories
- Risk: Any change to these modules has no safety net. mailctl wraps an external binary (himalaya) and secretctl manages 1Password access -- both are high-value targets for regression.
- Priority: High for mailctl and secretctl (security-adjacent), Low for telemetry and blogctl.

**journalctl tests exist but limited:**
- What's not tested: `halos/journalctl/window.py` synthesis path (subprocess mocking), cache invalidation edge cases
- Files: `tests/test_journalctl.py` (262 lines, covers store operations)
- Risk: Window synthesis failures only caught in production.
- Priority: Medium

**No tests for Docker entrypoint logic:**
- What's not tested: Bootstrap sequence (env generation, WAL mode, skill sync, NATS hook generation, cron setup)
- Files: `docker/entrypoint.sh`
- Risk: Container startup regressions caught only during deployment.
- Priority: Medium (overlaps with TD-5)

**No tests for briefings delivery path:**
- What's not tested: `halos/briefings/deliver.py` Telegram API call, IPC fallback
- Files: `halos/briefings/deliver.py`
- Risk: Briefing delivery failures (the final mile) are untested.
- Priority: Medium

## Dependencies at Risk

**playwright dependency in core pyproject.toml:**
- Risk: `playwright>=1.58.0` is listed as a core dependency in `pyproject.toml` but appears to be used only for optional browser automation. It pulls in significant native binaries.
- Impact: Bloats install for users who don't need browser automation. The Dockerfile has `INSTALL_BROWSER=false` by default, suggesting this is rarely needed.
- Migration plan: Move `playwright` to an optional dependency group (e.g., `[project.optional-dependencies] browser = ["playwright>=1.58.0"]`).

**himalaya CLI as hard dependency for mailctl:**
- Risk: `halos/mailctl/engine.py` depends on the `himalaya` binary being installed and configured. No fallback if the binary is missing or misconfigured.
- Impact: mailctl fails completely without himalaya. No pip-installable alternative.
- Migration plan: Consider adding a pure-Python IMAP fallback or at minimum a clear error message when himalaya is not found.

## Missing Critical Features

**No centralized error reporting:**
- Problem: Errors are logged to individual module log files, stderr, or silently swallowed. No aggregated error view across all halos modules.
- Blocks: Proactive debugging, alerting on cron failures, understanding system health at a glance.

**nightctl notifications are a stub:**
- Problem: `halos/nightctl/notify.py` writes to stderr and a log file only. The TODO comment says "wire to halos send_message when available." Failure notifications for overnight job execution don't reach Telegram.
- Files: `halos/nightctl/notify.py` (line 40)
- Blocks: Operator awareness of overnight job failures without manually checking logs.

---

*Concerns audit: 2026-04-07*
