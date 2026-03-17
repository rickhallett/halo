---
id: 20260317-145108-172
title: 'Standing decision: halos is artisanal architecture, not multi-tenant'
type: decision
tags:
- halos
- architecture
entities:
- halos
- nanoclaw
confidence: high
created: '2026-03-17T14:51:08Z'
modified: '2026-03-17T14:51:08Z'
expires: null
---

halos is built for a single-user power-operator. O(N) index loading and filesystem polling create scaling walls bounded by LLM context window physics, not RAM. Multi-tenant and enterprise are explicitly out of scope. Scale by multiplying instances (microHAL fleet), not by scaling one. Do not apologise for this — it is a design choice, not a limitation.
