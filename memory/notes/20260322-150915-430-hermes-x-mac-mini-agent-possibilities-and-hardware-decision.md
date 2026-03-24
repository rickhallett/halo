---
id: 20260322-150915-430
title: Hermes x Mac Mini Agent possibilities and hardware decision brainstorm
type: decision
tags:
- mac
- agents
- hardware
- career
- mac-mini-agent
- strategy
confidence: high
created: '2026-03-22T15:09:15Z'
modified: '2026-03-22T15:09:15Z'
expires: null
---

# Hermes x Mac Mini Agent + Hardware Decision Brainstorm
Date: 2026-03-22

## Context
Rick is setting up mac-mini-agent (disler/mac-mini-agent) on his brother Ben's Mac.
Repo forked to github.com/rickhallett/mac-mini-agent (private).
Two brainstorm docs exist in that repo under specs/:
- specs/hermes-x-mac-mini-agent-possibilities.md — 40 use cases across 10 domains
- specs/hardware-setup-brainstorm.md — hardware consolidation thinking

---

## Core Insight: The Closed Loop

Most AI tools can plan but not verify. They call APIs and hope. This stack
sees the actual screen, reads the actual output, captures the actual error.
Hermes decides. The Mac agent executes in the real world. Hermes observes truth.
That closed loop is multiplicative, not additive.

---

## 10 Domains of Use Cases

### I. Software Development
- Self-healing CI: failure detected → fix written → real tests run → PR merged
- Bug reproduction with actual screenshots as evidence
- Live browser testing in real Safari/Chrome, no Playwright needed
- Multi-agent coding swarm: N jobs dispatched in parallel, Hermes integrates results
- Automated dependency upgrades with real test verification

### II. Research
- arXiv paper → OCR equations from screen → running implementation → results
- blogwatcher monitors feeds, Mac agent reads gated sites via real browser
- Polymarket + live data dashboards (no APIs block a real browser + OCR)

### III. ML Operations
- Local model inference on Apple Silicon, fully remote-controlled via drive
- Training run babysitter: W&B + log polling + auto-kill on divergence
- Eval pipelines, dataset curation with real progress monitoring

### IV. Apple Ecosystem (unique to this setup)
- iMessage as natural language remote control of your Mac
- Reminders fire → Mac stages your workspace before you sit down
- Apple Notes as structured agent audit trail
- FindMy location triggers automated environment prep

### V. Productivity
- Morning briefing: calendar + email + news → synthesized doc + TTS
- Meeting prep: windows arranged, notes open, call ready — 15 min before
- Email → action pipeline (invoices entered, PRs opened, meetings booked)

### VI. Creative
- Stable Diffusion → iterative art direction loop without touching keyboard
- AI DJ: music generation → drive playback → steer volume control
- Screenshot → auto-captioned tweet via xitter

### VII. Monitoring
- Desktop state snapshot every 30 min to searchable Obsidian history
- Log tailing → ERROR detected → screenshot evidence → Linear issue filed
- Browser tab auditor: close week-old tabs, weekly digest to iMessage

### VIII. Communications
- Slack participation without API (Electron OCR)
- iMessage as remote status dashboard ("what did the agent do today?")

### IX. Meta-Recursive
- 3-level agent nesting: Hermes → Mac Claude Code → terminal sub-agents
- Self-modifying toolkit: agent detects its own gap, writes + builds new steer command
- Desktop UI as RL environment with steer as the observation layer
- Nightly paper reader: 20 arXiv papers processed, Obsidian notes, Sunday digest

### X. Full Autonomy Stack
Task arrives → Hermes plans → Mac implements → real tests run → PR opened →
self-reviewed → merged → Obsidian updated → Hermes skill updated with new patterns.
No human in the loop.

---

## Hardware Decision: Linux Arch Boxes vs M5 MacBook Pro

### The Case For Mac
- mac-mini-agent stack is NOT portable to Linux. Accessibility API, Vision
  framework for OCR, steer's ability to read ANY app including Electron,
  AppleScript, iMessage, FindMy — these are macOS kernel-level capabilities.
  xdotool and atspi are fragile toys by comparison.
- Apple Silicon: unified memory means 24GB shared between CPU and GPU.
  llama.cpp on M-series gets full Metal acceleration. Run a 14B model locally
  at real-time speeds while simultaneously running steer + drive + listen.
- macOS trigger ecosystem: launchd (location-aware, event-driven), Shortcuts
  automations triggered by app events, Accessibility observers, iMessage as
  bidirectional control surface.
- pmset can disable all sleep when docked:
    sudo pmset -a sleep 0 displaysleep 0 disksleep 0 standby 0 autopoweroff 0
    sudo pmset -a autorestart 1
  On battery: sudo pmset -b sleep 10 displaysleep 5
  A docked MacBook Pro IS the two-machine setup.

### Caveats
- Docker on macOS runs inside a Linux VM (OrbStack is the good option, nearly
  transparent). Fine for small workloads.
- MacBook Air will thermal throttle under sustained agentic load. M5 Pro has
  a fan — won't clock down during prolonged autonomous sessions.
- Laptop vs always-on: Mac Mini ($599) is designed to sit and never sleep.
  For truly always-on, Mini > Laptop. But pmset on docked Pro is close enough.

### Linux's Role
- Linux won't compete at consumer surface. Doesn't need to.
- Linux owns the infrastructure substrate — every listen server, vector DB,
  fine-tuning run, CI runner. Agents make this MORE true.
- The Arch background is an asset: "I understand the full stack from inference
  infrastructure to desktop automation."
- Wayland + AT-SPI2 improving but nobody has built a reliable Linux steer
  equivalent yet. That's a resources/incentive gap, not a technical impossibility.

---

## Job Market Positioning: Mac vs Linux for Agentic Engineering

### Answer: Mac. Reasoning:

Three hiring buckets in 2026 agentic engineering:
1. Infrastructure — model serving, fine-tuning, evals. Linux-native, abundant competition.
2. Agent tooling — building the steer/drive layer. Mac-native. Almost nobody with prod experience.
3. Applied agentic — browser automation, workflow automation, agent-to-human handoff,
   credential/safety architecture. Fastest growing. Primarily Mac.

Buckets 2 and 3 = highest leverage, easiest differentiation, both favour Mac.

### The Signal
- A GitHub full of mac-mini-agent patterns, steer integrations, Hermes orchestration
  pipelines, real E2E automation with screenshots as evidence = rare and demonstrable.
- Every well-funded AI startup right now issues MacBook Pros.
- Showing up with polished macOS agentic workflow = speaking the language of the env.

### Concrete Next Steps
1. Get M5 Pro, run pmset setup, always-on when docked
2. Private mac-mini-agent repo becomes live portfolio — every workflow in specs/,
   every new steer/drive pattern committed
3. Write one public post about something specific built — not "learning agents" but
   "here's a real workflow that does X" with screenshots, job YAML outputs, actual result
4. Arch experience = infrastructure credibility mentioned in interviews, not the lead

### Credential Layer Architecture (remaining unlock)
- Secrets in macOS Keychain (encrypted at rest, Touch ID protected)
- Agents access via `security find-generic-password` CLI
- Thin credential broker script exposes only what each job needs
- listen/worker.py already strips env vars before spawning Claude Code
- Jobs receive scoped tokens, not master keys
- Buildable in a week on top of existing stack

---

## Summary Judgment
The Mac is not just a better tool for this work.
In the current market it is also a better signal.
Both things are true simultaneously.
