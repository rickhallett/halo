---
title: "docs/ hierarchy"
category: reference
status: active
created: 2026-03-15
---

# docs/

BFS-friendly documentation hierarchy. Depth correlates with lookup frequency.

```
docs/
├── d1/              Operational — day-to-day reference
│   ├── briefings/   Daily operator digests (morning/nightly)
│   ├── DEBUG_CHECKLIST.md
│   ├── SECURITY.md
│   ├── architecture-diagrams.md   ← mermaid diagrams (system, fleet, tools, eval)
│   ├── halos-modules.md
│   ├── memctl-operations.md
│   ├── microhal-operations.md
│   └── session-patterns-*.md      ← post-session lessons learned
├── d2/              Architecture — design decisions, specs
│   ├── REQUIREMENTS.md
│   ├── SPEC.md
│   ├── spec-microhal.md
│   ├── spec-nightctl-merge.md
│   ├── spec-bathw.md
│   ├── spec-portfolio-showcase.md
│   ├── personality-config-plan.md
│   └── ...
├── d3/              Deep dives — historical, niche, archived
│   ├── archive/     Completed plans, superseded docs
│   ├── SDK_DEEP_DIVE.md
│   ├── docker-sandboxes.md
│   └── APPLE-CONTAINER-NETWORKING.md
└── docs-audit.py    Repeatable documentation audit script
```

**d1/** — Things you grep for during a debugging session or incident. Includes briefings and operational guides.
**d2/** — Things you read when planning a feature or understanding the system. Specs, architecture reviews, research.
**d3/** — Things you read once, then never again unless something breaks. Includes archive/ for completed plans and superseded docs.
