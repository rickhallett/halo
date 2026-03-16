---
id: 20260316-065510-445
title: Defensive coding mandate for agent-facing CLIs
type: decision
tags:
- standing-order
- governance
- engineering
- decision
entities:
- kai
confidence: high
created: '2026-03-16T06:55:10Z'
modified: '2026-03-16T06:55:10Z'
expires: null
---

All halOS modules must handle unhappy paths defensively. LLMs are probabilistic; the unhappy path is a question of time. Atomic writes (tmp+rename), collision guards, missing directory handling, accurate error counts, index consistency after mutations. No silent swallowing of errors.
