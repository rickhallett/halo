---
id: 20260316-133401-345
title: 'Agent chains: serial pipeline pattern distinct from parallel teams'
type: fact
tags:
- architecture
- governance
entities:
- kai
confidence: high
created: '2026-03-16T13:34:01Z'
modified: '2026-03-16T13:34:01Z'
expires: null
---

Sequential agent execution where each agent's output feeds the next. Distinct from agent teams (parallel subagents working simultaneously). Scout then planner then builder then reviewer. The verification fabric (gate then adversarial then human then post-merge) is conceptually an agent chain. nightctl has serial job dependencies but not output-forwarding between jobs. Making the verification fabric executable as a nightctl pipeline would close the loop.
