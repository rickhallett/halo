# Halo for Aura (Client 001)

## What This Is

A bespoke Halo deployment for Aura Enache — Daoist practitioner, UHT UK certified instructor (Master Chia's complete system), teaching Qi Gong, Somatic Breathwork, Chi Nei Tsang, and feminine energy cultivation. Two AI agents (Content Alchemist and Dao Assistant) running in a dedicated K8s namespace (`halo-aura`), delivered via Telegram, with LLM eval infrastructure to ensure agent quality from day one.

## Core Value

The Content Alchemist turns Aura's 80-90min Zoom practice recordings into Instagram-ready content that sounds exactly like her — soft, educational, meditative, with a touch of wit. If this doesn't work, nothing else matters.

## Requirements

### Validated

- Aura intake conversation completed — voice, lineage, teaching philosophy, two agent personas defined
- Aura gateway pod running in `halo-aura` namespace on Vultr VKE (41h uptime, 2/2 containers)
- Memory profile populated (USER.md, MEMORY.md with 6 structured memories)
- Session data captured (252KB intake conversation, multiple sessions)

### Active

- [ ] Content Alchemist agent: Zoom recording in, Instagram-ready posts and video clips out, in Aura's voice
- [ ] Dao Assistant agent: programme structuring, class summary holder, website/funnel guidance
- [ ] Custom UHT dictionary: Microcosmic Orbit, Chi Nei Tsang, nüdan, 6 Healing Sounds, ovarian breathing, 9 Flowers Nei Kung, etc.
- [ ] LLM eval framework: baseline from intake session, drift detection, overpromise monitoring, voice fidelity scoring
- [ ] Prompt tuning pipeline: eval results feed back into system prompt refinements
- [ ] Video content converter workflow: recording ingestion, transcription, clip extraction, caption generation, posting schedule
- [ ] Aura-specific council advisors (deferred — agents first, council later)

### Out of Scope

- Multi-tenant architecture — separate namespace per client, defer shared infrastructure
- Web UI — Telegram is the interface, proven path
- WhatsApp integration — Telegram chosen, revisit only if Aura requests
- Autonomous posting without review — Aura reviews before publish (confirmed in intake)
- Full website rebuild — Dao Assistant advises on structure, doesn't build the site
- Payment/billing automation — manual invoicing during pilot (GBP 300 setup + compute cost)

## Context

**Client profile:** Aura Enache, Romanian-born UK practitioner. Official UHT UK instructor across Master Chia's complete system. Currently 10-12 students on Sunday Zoom sessions. Vision: 100 students at GBP 10/session. Website: aureliana-therapies.com (basic). No selling funnel, no structured programmes for sale yet.

**Strategic angle:** Master Chia is 82 with massive Instagram following. Succession opportunity for certified instructors who can capture his audience. Content Alchemist is the growth engine.

**Teaching content:**
- 5 Elements Qi Gong: Earth (recorded), Metal (recorded), Water/Wood/Fire (next 3 weeks)
- Healing Love for Women: ovarian breathing, 4 wheels breathing, moon orbit, 9 Flowers Nei Kung
- Academic backing: nüdan (female alchemy) research validates ancient practices

**Aura's voice:** Soft, educational, kind, meditative pace. Aware Instagram favours wit. Natural, flowing communication style. Lao Tzu quotes woven naturally. Never generic or salesy. Body leads, healing is return not fix, nothing forced, slowness creates transformation.

**Aura's workflow:** Sunday afternoons — processes morning teachings, sends recordings and summaries to mail list. Content Alchemist activates the moment recordings are shared.

**Business model:** GBP 300 setup fee. 8-12 week pilot at pure compute cost (est. GBP 50-80/month). Post-pilot: fair monthly price based on real usage data. Trade: video testimonial and flagship case study permission.

**Technical baseline:**
- Gateway pod: `halo-aura` namespace, Vultr VKE, 2 containers (gateway + aura-relay)
- Hermes gateway with 73 bundled skills
- Session storage: `/opt/data/sessions/` (JSONL format)
- Memory storage: `/opt/data/memories/` (USER.md, MEMORY.md)
- Document cache: `/opt/data/cache/documents/`

**Integration decisions still needed from Aura:**
- Recording delivery: Zoom cloud link, Google Drive, or direct Telegram upload?
- Output format: text posts from transcript, actual video clip extraction, or both?
- Review flow: Telegram preview with approve/reject, or out-of-band review?
- Instagram posting: direct API integration or manual copy-paste from agent output?
- Caption style: pull exact quotes from transcript, or LLM-paraphrased in her style?

## Constraints

- **Infrastructure**: Separate K8s namespace on Vultr VKE — no multi-tenant, no shared resources with main Halo fleet
- **Interface**: Telegram via Hermes gateway — no web UI, no WhatsApp
- **Voice fidelity**: LLM output must pass eval against Aura's actual communication patterns — no generic wellness slop
- **Budget**: Pilot economics — compute cost transparency, no margin during pilot
- **Terminology**: Custom dictionary required before any content generation — UHT terms must transcribe correctly
- **Pace**: Organic growth, no rush, no big automation — matches Aura's philosophy
- **Scope boundary**: Plan concretely through workflow specification and solution space exploration. Planning beyond that is premature until integration decisions are made and eval baseline is established.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Separate namespace, not multi-tenant | Ship faster, defer scaling complexity. TD-3 (no health check sidecar) blocks multi-tenant anyway | -- Pending |
| Telegram, not web UI | Proven path, lowest build cost, Aura is already on Telegram | -- Pending |
| Content Alchemist ships first | Highest immediate value — Aura has recordings ready. Dao Assistant is advisory, not urgent | -- Pending |
| LLM evals from day one | Prevent voice drift and overpromising. Aura's communication style is specific — generic LLM tendencies are the biggest risk | -- Pending |
| Prompt tuning pipeline before feature expansion | Get the voice right first. Every feature built on bad prompts compounds the problem | -- Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? Move to Out of Scope with reason
2. Requirements validated? Move to Validated with phase reference
3. New requirements emerged? Add to Active
4. Decisions to log? Add to Key Decisions
5. "What This Is" still accurate? Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-07 after initialization*
