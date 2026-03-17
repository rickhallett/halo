# microHAL Smoke Test v1.0
# Run this as the first message to a freshly provisioned instance.
# Paste the entire block. The agent will execute each section and report.

You are running a standardised smoke test. Execute each section in order. For each, report PASS or FAIL with a one-line reason. Do not skip any section. Do not ask for clarification. At the end, produce a summary table.

## 1. Identity Check

Read your CLAUDE.md. Answer:
- What is the primary user's name?
- What is the operator's name?
- What personality template are you running?

PASS if: you can name all three correctly.
FAIL if: you say "I don't know" or get any wrong.

## 2. Workspace Permissions

Run these commands and report the results:
```bash
# Writable dirs
touch /workspace/group/test-write && rm /workspace/group/test-write && echo "group: WRITABLE"
touch /workspace/extra/test-write && rm /workspace/extra/test-write && echo "extra: WRITABLE"
touch /workspace/global/test-write && rm /workspace/global/test-write && echo "global: WRITABLE"

# Read-only dirs (should FAIL to write)
touch /workspace/project/test-write 2>&1 && echo "project: WRITABLE (BAD)" || echo "project: READ-ONLY (GOOD)"

# Memory (writable via tool)
ls /workspace/project/memory/INDEX.md >/dev/null 2>&1 && echo "memory/INDEX.md: EXISTS" || echo "memory/INDEX.md: MISSING"
```

PASS if: group/extra/global are writable, project is read-only, memory/INDEX.md exists.
FAIL if: any permission is wrong.

## 3. Tool Availability

Run each command and report version or "NOT FOUND":
```bash
echo "=== CLI Tools ==="
memctl --help 2>&1 | head -1 || echo "memctl: NOT FOUND"
gh --version 2>&1 | head -1 || echo "gh: NOT FOUND"
vercel --version 2>&1 | head -1 || echo "vercel: NOT FOUND"
git --version 2>&1 | head -1 || echo "git: NOT FOUND"
python3 --version 2>&1 || echo "python3: NOT FOUND"
node --version 2>&1 || echo "node: NOT FOUND"
curl --version 2>&1 | head -1 || echo "curl: NOT FOUND"
npm --version 2>&1 || echo "npm: NOT FOUND"

echo "=== Should NOT exist ==="
which todoctl 2>&1 || echo "todoctl: NOT FOUND (GOOD)"
which logctl 2>&1 || echo "logctl: NOT FOUND (GOOD)"
which neonctl 2>&1 || echo "neonctl: NOT FOUND (EXPECTED)"
which sqlite3 2>&1 || echo "sqlite3: NOT FOUND (EXPECTED)"
```

PASS if: memctl, gh, vercel, git, python3, node, curl, npm all found. todoctl and logctl NOT found.
FAIL if: any expected tool missing or any retired tool present.

## 4. Service Authentication

```bash
echo "=== GitHub ==="
gh auth status 2>&1 | head -3

echo "=== Vercel ==="
vercel whoami 2>&1 | head -2
```

PASS if: both report authenticated.
FAIL if: either says "not logged in" or errors.

## 5. Memory System

```bash
# Test memctl write
memctl new --title "Smoke test $(date +%Y%m%d-%H%M%S)" --type fact --tags smoke-test --body "Automated smoke test verification." 2>&1

# Test memctl read
memctl list 2>&1 | head -5
```

PASS if: note created successfully and appears in list.
FAIL if: any error.

## 6. Network & API Access

```bash
# Can we reach the internet?
curl -sf https://httpbin.org/get -o /dev/null && echo "Internet: REACHABLE" || echo "Internet: UNREACHABLE"

# Can we reach the Claude API proxy?
curl -sf http://host.docker.internal:3001/ -o /dev/null && echo "API proxy: REACHABLE" || echo "API proxy: UNREACHABLE"
```

PASS if: both reachable.
FAIL if: either unreachable.

## 7. File System Basics

```bash
# Create a test project structure
mkdir -p /workspace/group/smoke-test-project
echo "console.log('hello from smoke test');" > /workspace/group/smoke-test-project/test.js
node /workspace/group/smoke-test-project/test.js
rm -rf /workspace/group/smoke-test-project
echo "File ops: CLEAN"
```

PASS if: file created, executed, cleaned up.
FAIL if: any step errors.

## 8. Python Environment

```bash
python3 -c "
import sqlite3, json, os, sys
print(f'Python: {sys.version}')
print(f'sqlite3: {sqlite3.sqlite_version}')
print(f'Can import json, os, sys: YES')
# Test we can create a DB in writable space
db = sqlite3.connect('/workspace/group/test.db')
db.execute('CREATE TABLE t (id INTEGER PRIMARY KEY, val TEXT)')
db.execute('INSERT INTO t VALUES (1, \"smoke\")')
result = db.execute('SELECT val FROM t').fetchone()
db.close()
os.remove('/workspace/group/test.db')
print(f'SQLite operations: {\"PASS\" if result[0] == \"smoke\" else \"FAIL\"}')
"
```

PASS if: all imports work and SQLite operations succeed.
FAIL if: any error.

## 9. Git Configuration

```bash
git config --global user.name 2>&1 || echo "git user.name: NOT SET"
git config --global user.email 2>&1 || echo "git user.email: NOT SET"
```

Report status. Not a hard FAIL if unset — just note it.

## 10. CLAUDE.md Governance Check

Read your CLAUDE.md and answer:
- Does it contain a "Core Principle" section?
- Does it contain "Response Discipline" rules?
- Does it contain "Emotional Grounding" instructions?
- Does it list tools NOT to suggest?

PASS if: all present.
FAIL if: any section missing (report which).

---

## Summary

Produce a table:

| # | Check | Status | Notes |
|---|-------|--------|-------|
| 1 | Identity | PASS/FAIL | ... |
| 2 | Permissions | PASS/FAIL | ... |
| 3 | Tools | PASS/FAIL | ... |
| 4 | Auth | PASS/FAIL | ... |
| 5 | Memory | PASS/FAIL | ... |
| 6 | Network | PASS/FAIL | ... |
| 7 | File Ops | PASS/FAIL | ... |
| 8 | Python | PASS/FAIL | ... |
| 9 | Git Config | INFO | ... |
| 10 | Governance | PASS/FAIL | ... |

Then state: "Smoke test complete. X/10 passed. Instance is [READY / NOT READY] for user."
