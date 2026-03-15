# docs/

BFS-friendly documentation hierarchy. Depth correlates with lookup frequency.

```
docs/
├── d1/          Operational — day-to-day reference
│   ├── DEBUG_CHECKLIST.md
│   └── SECURITY.md
├── d2/          Architecture — design decisions, specs
│   ├── REQUIREMENTS.md
│   ├── SPEC.md
│   ├── nanoclaw-architecture-final.md
│   ├── nanorepo-architecture.md
│   └── skills-as-branches.md
├── d3/          Deep dives — historical, niche topics
│   ├── APPLE-CONTAINER-NETWORKING.md
│   ├── docker-sandboxes.md
│   └── SDK_DEEP_DIVE.md
└── plans/       Implementation plans (ephemeral, per-feature)
```

**d1/** — Things you grep for during a debugging session or incident.
**d2/** — Things you read when planning a feature or understanding the system.
**d3/** — Things you read once, then never again unless something breaks in that area.
**plans/** — Timestamped implementation plans. Consumed during development, archived after.
