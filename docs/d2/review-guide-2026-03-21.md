---
title: "Adversarial Review Guide — 24h Halos Expansion (2026-03-21)"
category: review
status: active
created: 2026-03-21
---

# Adversarial Review Guide — 24h Halos Expansion

**Scope:** All changes between `35a79ee` and `HEAD` (~17,000 lines added across 242 files)
**Purpose:** Find bugs, security issues, design flaws, and test gaps before these modules see production use.
**Deliverable:** Structured findings report + Telegram notification to Operator on completion.

---

## Context for the Reviewing Agent

Over the last 24 hours, five new halos modules were built in parallel by subagents and merged into main. Each module follows the trackctl pattern (cli.py + engine.py + store/source layer + briefing.py). The modules were built from specs in `docs/d2/spec-*.md` and tested with 281+ tests.

Additionally: mailctl, trackctl, dashctl panels, briefing checkin system, and infrastructure updates were committed from prior unstaged work.

### What Was Built

| Module | Files | Tests | Spec |
|--------|-------|-------|------|
| calctl | `halos/calctl/` | `tests/calctl/` (71) | `docs/d2/spec-calctl.md` |
| statusctl | `halos/statusctl/` | `tests/statusctl/` (45) | `docs/d2/spec-statusctl.md` |
| backupctl | `halos/backupctl/` | `tests/backupctl/` (64) | `docs/d2/spec-backupctl.md` |
| ledgerctl | `halos/ledgerctl/` | `tests/ledgerctl/` (85) | `docs/d2/spec-ledgerctl.md` |
| dashctl --html | `halos/dashctl/html_export.py` | `tests/dashctl/` (16) | `docs/d2/spec-dashctl-html.md` |
| mailctl | `halos/mailctl/` | (no dedicated tests yet) | N/A |
| trackctl | `halos/trackctl/` | (existing tests) | N/A |

### Key Commits (review in this order)

```bash
git log --oneline 35a79ee..HEAD
```

---

## Review Protocol

### Phase 1: Structural Integrity (read-only, ~10 min)

1. **Verify all tests pass:**
   ```bash
   uv run python -m pytest tests/calctl/ tests/statusctl/ tests/backupctl/ tests/ledgerctl/ tests/dashctl/ -v --tb=short
   ```

2. **Check for import errors across all new modules:**
   ```bash
   uv run python -c "import halos.calctl; import halos.statusctl; import halos.backupctl; import halos.ledgerctl; import halos.dashctl; import halos.mailctl; print('all imports ok')"
   ```

3. **Verify CLI entry points are registered and runnable:**
   ```bash
   calctl --help
   statusctl --help
   backupctl --help
   ledgerctl --help
   dashctl --help
   mailctl --help
   ```

4. **Check pyproject.toml for consistency:**
   - All new modules have `[project.scripts]` entries
   - No duplicate entries
   - Dependencies are declared

### Phase 2: Security Review (~20 min)

Focus areas per the project's security model:

1. **No LLM on untrusted input.** Check that NO module passes external content (email bodies, bank CSV payee fields, user messages) through LLM classification prompts. This is a hard constraint — see `feedback_no_llm_on_untrusted_input.md` in project memory.

2. **File write atomicity.** All file writes in halos modules must use write-then-rename (temp file + `os.replace()`). Check:
   - `halos/ledgerctl/journal.py` — journal append
   - `halos/ledgerctl/rules.py` — rules save
   - `halos/backupctl/engine.py` — backup operations
   - `halos/calctl/` — any file writes

3. **SQLite safety.** `backupctl` must use `sqlite3.backup()` for database copies, never raw file copy of a live .db. Verify in `halos/backupctl/engine.py`.

4. **Subprocess injection.** Check all `subprocess.run()` / `subprocess.Popen()` calls:
   - No `shell=True` with user-controlled input
   - Arguments passed as lists, not strings
   - Timeouts set on all subprocess calls
   ```bash
   grep -rn "subprocess\.\(run\|Popen\|call\)" halos/statusctl/ halos/backupctl/ halos/calctl/ halos/ledgerctl/
   ```

5. **Path traversal.** Check that file paths from user input (e.g., `--output`, `--to`, CSV paths) are validated:
   - `backupctl restore --to PATH` — can this write outside the project?
   - `ledgerctl import --csv PATH` — can this read arbitrary files?
   - `dashctl --html --output PATH` — can this overwrite sensitive files?

6. **Credential exposure.** Verify no module logs, prints, or stores API keys, tokens, or passwords. Check `hlog()` calls for sensitive data fields.

### Phase 3: Logic & Correctness (~30 min)

For each module, read the implementation and check against the spec:

#### calctl
- [ ] NightctlSource correctly loads items with `due`/`deadline` fields
- [ ] CronctlSource filtering: verify `max_daily_runs=12` correctly filters hourly jobs but keeps daily/weekly
- [ ] GoogleCalendarSource graceful degradation: returns empty list, logs debug once
- [ ] `merge_events()` correctly deduplicates across sources
- [ ] `find_conflicts()` handles edge cases: adjacent events, all-day events, point-in-time events
- [ ] `find_free_slots()` handles edge cases: empty day, fully booked day, overnight events
- [ ] Timezone handling: are all times consistently UTC?

#### statusctl
- [ ] Each check handles the "tool not installed" case (Docker not present, systemd not available)
- [ ] Health grade computation: verify HEALTHY/DEGRADED/DOWN thresholds
- [ ] `statusctl check` exit code: 0 for HEALTHY, 1 for anything else
- [ ] `/proc` parsing: handles missing files, unexpected formats
- [ ] Container check: handles Docker daemon not running
- [ ] Does `statusctl` work on macOS (no /proc)? Should it gracefully degrade?

#### backupctl
- [ ] `sqlite3.backup()` is used for ALL .db files, never raw copy
- [ ] Restic detection via `shutil.which()` — correct fallback to tar
- [ ] Tar backup: verify contents match source, compression works
- [ ] Restore requires explicit `--to PATH` (never overwrites in-place)
- [ ] Snapshot listing: handles empty repository, corrupt snapshots
- [ ] Config loading: defaults are sensible when no `backupctl.yaml` exists

#### ledgerctl
- [ ] Journal parsing: round-trip (write then read) produces identical data
- [ ] Duplicate detection in imports: same (date, amount, payee) skipped
- [ ] Categorisation rules: regex patterns, first-match-wins, uncategorised fallback
- [ ] Balance computation: double-entry accounting (debits = credits)
- [ ] Bank CSV import: column mapping for ANZ and Wise formats
- [ ] No LLM classification anywhere (deterministic rules only)
- [ ] Currency handling: configurable, not hardcoded

#### dashctl --html
- [ ] HTML output is self-contained (inline styles, no external CSS/JS)
- [ ] Dark background matches terminal aesthetic
- [ ] Empty dashboard produces valid HTML
- [ ] `--open` flag works (webbrowser.open)

#### mailctl (if tests exist)
- [ ] Triage rules are deterministic (no LLM)
- [ ] himalaya subprocess calls have timeouts
- [ ] Filter audit trail is logged

### Phase 4: Test Coverage Gaps (~20 min)

1. **Run coverage report:**
   ```bash
   uv run python -m pytest tests/calctl/ tests/statusctl/ tests/backupctl/ tests/ledgerctl/ tests/dashctl/ --cov=halos.calctl --cov=halos.statusctl --cov=halos.backupctl --cov=halos.ledgerctl --cov=halos.dashctl --cov-report=term-missing
   ```

2. **Check for missing test categories:**
   - Error paths (what happens when things fail?)
   - Edge cases (empty inputs, very large inputs, concurrent access)
   - Integration between modules (does calctl correctly read nightctl items?)
   - Smoke tests against real data (not just fixtures)

3. **Check for tests that always pass** (tautological assertions, mocks that don't exercise real code paths)

4. **mailctl has no dedicated test suite** — flag this as a gap

### Phase 5: Design Review (~15 min)

1. **Module boundaries.** Do any modules reach into another module's internals? All cross-module access should be through public APIs (e.g., `engine.text_summary()`, `store.add_entry()`).

2. **Briefing integration.** Does each module's `briefing.py` follow the `text_summary() -> str` pattern? Is the output format consistent with existing modules?

3. **CLI consistency.** Do all modules support `--json` where claimed? Is argparse help text clear?

4. **Error messages.** Are errors actionable? Does the user know what to do when something fails?

5. **Naming consistency.** Variable names, function signatures, module layout — do they follow the trackctl/nightctl patterns?

---

## Findings Report Format

Create the report at `docs/d2/review-findings-2026-03-21.md` with this structure:

```markdown
---
title: "Adversarial Review Findings — 24h Halos Expansion"
category: review
status: active
created: 2026-03-21
---

# Adversarial Review Findings

## Summary
- Total findings: N
- Critical: N
- High: N
- Medium: N
- Low: N

## Critical Findings
[Security issues, data loss risks, correctness bugs that affect production]

## High Findings
[Logic errors, missing error handling, test gaps that could mask bugs]

## Medium Findings
[Design issues, inconsistencies, missing edge case handling]

## Low Findings
[Style issues, minor inconsistencies, documentation gaps]

## Test Coverage Report
[Output of coverage command]

## Recommendations
[Prioritised list of fixes]
```

---

## Notification

On completion, send a summary to the Operator via Telegram. Use the existing NanoClaw channel infrastructure:

```bash
# The IPC message mechanism — write a message file for the orchestrator to pick up
# Or use the Telegram Bot API directly if TELEGRAM_BOT_TOKEN is in .env

# Option 1: Direct Telegram API call
source .env
CHAT_ID=$(grep TELEGRAM_MAIN_CHAT_ID .env | cut -d= -f2)
curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
  -d "chat_id=${CHAT_ID}" \
  -d "parse_mode=Markdown" \
  -d "text=$(cat <<'MSG'
*Adversarial Review Complete*

Reviewed 17,262 lines across 242 files (24h of halos expansion).

Findings: [N critical, N high, N medium, N low]

Full report: docs/d2/review-findings-2026-03-21.md

Top issues:
1. [most important finding]
2. [second most important]
3. [third most important]
MSG
)"
```

If direct API call fails, fall back to writing the summary to `store/review-notification.txt` for the next operator session.

---

## How to Run This Review

```bash
# From the repo root:
# 1. Read this guide
# 2. Follow each phase in order
# 3. Write findings to docs/d2/review-findings-2026-03-21.md
# 4. Send Telegram notification
# 5. Commit the findings report
```

The review should take approximately 60-90 agent-minutes. Do not rush — the purpose is to find bugs, not to confirm correctness.
