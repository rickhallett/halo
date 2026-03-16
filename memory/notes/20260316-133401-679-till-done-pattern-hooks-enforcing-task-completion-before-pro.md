---
id: 20260316-133401-679
title: 'Till-done pattern: hooks enforcing task completion before proceeding'
type: fact
tags:
- governance
- architecture
- hci
entities:
- kai
confidence: high
created: '2026-03-16T13:34:01Z'
modified: '2026-03-16T13:34:01Z'
expires: null
---

Deterministic scaffolding around a probabilistic agent. Block the agent from running tools until it creates a task list. Force it to work through every item. Require human approval before clearing. Already partially implemented: post-write enrichment enforcement ('this is not optional') is the same principle. Systematic version: a halos hook that blocks agent tool use until a todoctl item is in-progress.
