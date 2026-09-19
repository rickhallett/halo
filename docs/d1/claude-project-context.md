---
title: "Claude Project Context"
category: reference
status: active
created: 2026-04-15
---

# Claude Project Context

Active project state, technical debt, and governance policies.
Read this when you need project context -- not loaded at boot.

## Active Technical Debt

From [2026-04-04 daily review](docs/d2/reviews/2026-04-04-daily-work-review.md) -- action before next major release:

| ID | Area | Severity | Action |
|----|------|----------|--------|
| TD-1 | journalctl | Medium | Replace `claude` CLI subprocess with proper client; add retry/rate-limit |
| TD-3 | infra | Medium | Add HTTP health check sidecar before multi-tenant deployment |
| TD-4 | infra | Low | Document or fix `pip` usage in Dockerfile (violates uv-only policy) |
| TD-5 | infra | Medium | Add automated integration test for container build |

## Project: Halo for Aura (Client 001)

A bespoke Halo deployment for Aura Enache -- Daoist practitioner, UHT UK certified instructor (Master Chia's complete system), teaching Qi Gong, Somatic Breathwork, Chi Nei Tsang, and feminine energy cultivation. Two AI agents (Content Alchemist and Dao Assistant) running in a dedicated K8s namespace (`halo-aura`), delivered via Telegram, with LLM eval infrastructure to ensure agent quality from day one.

**Core Value:** The Content Alchemist turns Aura's 80-90min Zoom practice recordings into Instagram-ready content that sounds exactly like her -- soft, educational, meditative, with a touch of wit. If this doesn't work, nothing else matters.

### Constraints

- **Infrastructure**: Separate K8s namespace on Ryzen k3s (halo-aura) -- no multi-tenant, no shared resources with main Halo fleet
- **Interface**: Telegram via Hermes gateway -- no web UI, no WhatsApp
- **Voice fidelity**: LLM output must pass eval against Aura's actual communication patterns -- no generic wellness slop
- **Budget**: Pilot economics -- compute cost transparency, no margin during pilot
- **Terminology**: Custom dictionary required before any content generation -- UHT terms must transcribe correctly
- **Pace**: Organic growth, no rush, no big automation -- matches Aura's philosophy
- **Scope boundary**: Plan concretely through workflow specification and solution space exploration. Planning beyond that is premature until integration decisions are made and eval baseline is established.

## Scope Estimation

Scope estimates must separate **agent work** from **human work** -- never express them as a single wall-clock figure.

Why:

- LLM reasoning priors about task duration are calibrated to human software development speeds. Those priors are outdated in an agent-assisted context.
- Read/write operations are asymmetric: agents read fast and write fast; humans read slower but judge better. Estimates that ignore this produce bad plans.
- A wrong estimate at the top cascades through scheduling, parallelism, review allocation, and commit cadence.

Express scope as: generation volume (agent work) x review and decision load (human work). The distinction changes how we plan.

## AI Engineering Governance

Full catalogue: [docs/ai-engineering-patterns.md](docs/ai-engineering-patterns.md). Source: [Augmented Coding Patterns](https://lexler.github.io/augmented-coding-patterns/). Load on-demand when needed -- the patterns doc is the source of truth.

**Hard constraints** (invariant): fixed weights, finite context, non-determinism, black box reasoning.
**Common failure tendencies**: context rot, compliance bias, solution fixation, selective hearing, hallucinations, excess verbosity. See patterns doc for full table.

**Evidence hierarchy** -- rank verification by strength: (1) reproducible test > (2) static/tool validation > (3) human inspection > (4) cross-family model review > (5) same-model self-review. Rank 4-5 is a prompt to investigate, not confirmation.

## Development Commands

Run commands directly -- don't tell the user to run them.

```bash
# Halos Python tooling
uv sync                  # Install/update Python deps
pytest                   # Run test suite
cronctl install --execute # Regenerate and install crontab

# Halo Gateway (when working on gateway)
npm run dev              # Run with hot reload
npm run build            # Compile TypeScript
./container/build.sh     # Rebuild agent container

# Agent (listen/direct)
cd agent && just listen  # Start job server on :7600
cd agent && just send "prompt"  # Queue a job
```
