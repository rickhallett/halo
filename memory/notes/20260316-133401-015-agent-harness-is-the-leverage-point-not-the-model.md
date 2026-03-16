---
id: 20260316-133401-015
title: Agent harness is the leverage point, not the model
type: fact
tags:
- architecture
- hci
- engineering
entities:
- kai
- nanoclaw
confidence: high
created: '2026-03-16T13:34:01Z'
modified: '2026-03-16T13:34:01Z'
expires: null
---

Customising the orchestration layer (hooks, tool registration, subagent dispatch, system prompt, IPC) yields more differentiation than model selection. The model is replaceable; the harness is the product. halos + NanoClaw container + IPC + CLAUDE.md is the harness. Pi agent demonstrates the same principle from the opposite direction: 200 token system prompt, 4 default tools, everything else user-built.
