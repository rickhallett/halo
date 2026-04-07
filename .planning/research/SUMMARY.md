# Project Research Summary

**Project:** Halo for Aura (Client 001) -- Content Repurposing + LLM Eval
**Domain:** AI content repurposing for wellness practitioners with voice fidelity evaluation
**Researched:** 2026-04-07
**Confidence:** MEDIUM-HIGH

## Executive Summary

Halo for Aura is a bespoke content pipeline that transforms 80-90 minute Zoom practice recordings into Instagram-ready posts in Aura's exact voice -- soft, educational, meditative, never salesy. The expert approach for this class of product is dictionary-augmented transcription (Deepgram Nova-3 with keyword boosting), LLM content generation with few-shot voice examples, and LLM-as-judge evaluation against a weighted rubric. The critical insight across all four research tracks: **eval infrastructure must ship before content generation, not after.** Without voice fidelity scoring as a hard gate, the system produces generic wellness slop that erodes client trust within weeks.

The recommended stack is lean and deliberate: Deepgram Nova-3 for transcription (native keyword boosting for UHT terms), Claude for content generation and eval judging, ffmpeg for media processing, and the existing halos module pattern for orchestration. Total incremental API cost is approximately GBP 8-12/month. No new frameworks are needed -- the existing watchctl rubric pattern and nightctl state machine pattern cover evaluation and pipeline orchestration respectively. The architecture deploys as K8s Jobs in the existing halo-aura namespace, with file-based handoff on NFS between pipeline stages.

The primary risks are voice drift without detection (solved by shipping eval in phase 1), transcription errors on UHT terminology (solved by comprehensive dictionary + post-processing correction), and Instagram token expiry causing silent publish failures (solved by expiry tracking and proactive alerts). A secondary risk is eval metrics that do not correlate with Aura's actual preferences -- this requires a calibration phase where Aura rates real outputs and the rubric is adjusted until correlation exceeds 0.7.

## Key Findings

### Recommended Stack

The stack maximises reuse of existing halos infrastructure while adding only three new dependencies: deepgram-sdk, deepeval (dev-only, if used at all), and ffmpeg-python. The architecture research strongly recommends against DeepEval in production, favouring the existing watchctl/rubric.py pattern for eval. DeepEval remains useful as a dev-time benchmark tool only.

**Core technologies:**
- **Deepgram Nova-3**: Transcription with native keyword boosting -- feeds UHT terms at API call time, no fine-tuning. $0.0043-0.0145/min.
- **ffmpeg + ffmpeg-python**: Audio extraction and clip cutting -- already in fleet containers, thin wrapper fits halos pattern.
- **Claude (Anthropic SDK)**: Content generation (Sonnet) and eval judging (Haiku for bulk, Sonnet for flagged) -- already a dependency.
- **Jinja2 + YAML**: Prompt template management -- already in stack, git-versioned, zero new deps.
- **SQLite**: Pipeline state tracking -- same pattern as nightctl, trackctl, every other halos module.
- **Instagram Graph API + httpx**: Content publishing -- 3 HTTP calls, no SDK needed.

**Stack disagreement to resolve:** STACK.md recommends DeepEval as the eval framework. ARCHITECTURE.md and FEATURES.md both argue for extending the existing watchctl/rubric.py pattern instead. **Recommendation: follow ARCHITECTURE.md.** The existing pattern is proven, adds zero dependencies, and the team already knows it. Use DeepEval only if the eval requirements outgrow the in-house pattern (unlikely at single-client scale).

### Expected Features

**Must have (table stakes -- Content Alchemist does not work without these):**
- Custom UHT terminology dictionary (YAML registry, used by all downstream)
- Zoom recording ingestion (single delivery path via Telegram)
- Transcription with dictionary correction (Deepgram + post-processing)
- Transcript segmentation by topic (LLM-classified chapters)
- Text post generation in Aura's voice (few-shot from intake)
- Voice fidelity eval rubric (LLM-as-judge, hard gate before review)
- Overpromise detection (deterministic deny-list + LLM judge, highest weight)
- Telegram review flow (preview, approve/edit/reject)
- Instagram post formatting (2200 char limit, hashtag strategy, visual rhythm)

**Should have (add after validation, v1.x):**
- Content queue and scheduling (trigger: 5+ approved pieces)
- Engagement pattern learning (trigger: 20+ approve/reject decisions)
- Prompt tuning pipeline (trigger: eval scores show consistent weak dimensions)
- Instagram API direct publishing (trigger: manual posting becomes friction)
- Drift monitoring dashboard (trigger: 4+ weeks of generation history)

**Defer (v2+):**
- Programme structure extraction (needs 5+ session recordings)
- Video clip extraction (text content must be validated first)
- Dao Assistant agent (Content Alchemist must prove value first)
- Multi-platform distribution (Instagram-first, single platform mastery)

### Architecture Approach

The system deploys into the existing halo-aura K8s namespace as on-demand Jobs (not long-running workers) that communicate via file handoff on NFS. Two new halos modules (contentctl and evalctl) follow established patterns: CLI entry point, engine functions, SQLite store, YAML config. The pipeline state machine mirrors nightctl: pending -> ingested -> transcribed -> generated -> evaluated -> reviewing -> approved. The eval runner operates as a CronJob (nightly) or post-generation Job, scoring all output against the voice fidelity rubric before it reaches Aura.

**Major components:**
1. **contentctl** -- Pipeline orchestration: ingest, transcribe, segment, generate. K8s Jobs, file-based handoff.
2. **evalctl** -- LLM evaluation: voice fidelity, terminology accuracy, overpromise detection, tone scoring. Extends watchctl pattern.
3. **Aura Gateway skills** -- Recording intake and content review via Telegram. Creates Jobs, presents results.
4. **UHT Dictionary** -- ConfigMap mounted into all pipeline components. Single source of truth for terminology.
5. **instactl** -- Instagram Graph API wrapper: container create, publish, token refresh. Thin module, 3 HTTP calls.

### Critical Pitfalls

1. **Voice drift without detection** -- Ship eval infrastructure in phase 1, not phase 3. Score every generation against intake baseline. Alert when fidelity drops below 0.7.
2. **Transcription garbage in, content garbage out** -- Comprehensive UHT dictionary with phonetic hints before first transcription. Post-processing regex correction. Manual verification of first 5 transcriptions.
3. **Eval metrics that do not correlate with human judgment** -- Calibration phase: generate 20 posts, have Aura rate them, adjust rubric until correlation exceeds 0.7. Track approve/reject rate as ground truth.
4. **Instagram token expiry silent failure** -- Token expiry tracking in SQLite, proactive alerts 7 days before expiry, refresh endpoint in instactl. Start Meta developer account setup early.
5. **Over-engineering for 4 recordings/month** -- SQLite state machine, manual retry via CLI, no workflow engines. Add infrastructure only when it breaks.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Foundation and Eval Baseline
**Rationale:** Dictionary and eval infrastructure must exist before any content is generated. The dictionary unblocks transcription accuracy. The eval baseline (from intake session) defines what "sounds like Aura" means quantitatively. Without these, all downstream output is unvalidated.
**Delivers:** UHT dictionary (ConfigMap), evalctl module with scorers, eval baseline from intake transcript, contentctl.dictionary module.
**Addresses:** Custom UHT dictionary, voice fidelity eval rubric, overpromise detection framework.
**Avoids:** Pitfall 2 (transcription garbage), Pitfall 4 (uncalibrated eval).

### Phase 2: Transcription Pipeline
**Rationale:** With dictionary in place, transcription can be built and validated. This is the critical data path -- everything downstream depends on accurate transcripts.
**Delivers:** contentctl.transcribe (Deepgram integration + correction), contentctl.ingest (ffmpeg audio extraction), Ingestion Job manifest, transcript segmentation.
**Uses:** Deepgram Nova-3 API, ffmpeg-python, UHT dictionary from Phase 1.
**Avoids:** Pitfall 2 (test with real recordings, not clean audio), Pitfall 5 (Deepgram cost -- use short clips in dev).

### Phase 3: Content Generation and Review
**Rationale:** Transcription output provides the input for content generation. Review flow is the human gate -- nothing publishes without Aura's approval.
**Delivers:** contentctl.generate (LLM content creation), Telegram review flow (approve/edit/reject), content formatting for Instagram.
**Implements:** Content Generator component, Review Relay (Gateway skill), pipeline state machine.
**Avoids:** Pitfall 1 (voice drift -- eval gates every generation), Pitfall 3 (segment boundaries -- let Aura adjust).

### Phase 4: Integration and Publishing
**Rationale:** Once content generation is validated and Aura is approving posts, add the publishing pipeline and connect eval reporting to briefings.
**Delivers:** instactl module (Instagram Graph API publishing), eval CronJob, eval reporting in nightly briefings, Gateway RBAC for Job creation.
**Avoids:** Pitfall 3 (Instagram token expiry -- build refresh tracking from day one), Pitfall 4 (Meta account setup -- start in Phase 1).

### Phase 5: Feedback Loop and Maturation
**Rationale:** Requires 2-4 weeks of operational data. Engagement pattern learning needs 20+ approve/reject decisions. Drift monitoring needs 4+ weeks of scores. Prompt tuning needs consistent eval data showing weak dimensions.
**Delivers:** Engagement pattern learning, prompt tuning pipeline, drift monitoring dashboard, content queue and scheduling.
**Implements:** Closed-loop quality improvement (human-gated, never automated).

### Phase Ordering Rationale

- **Eval before generation** is the single most important ordering decision. Every research track converges on this: FEATURES.md calls it a hard gate, ARCHITECTURE.md puts eval infrastructure in Phase 1 of its build order, PITFALLS.md flags voice drift as the top critical pitfall.
- **Dictionary before transcription** is a hard dependency. Without UHT terms loaded, Deepgram will mangle domain vocabulary and every downstream artifact is corrupted.
- **Generation before publishing** allows validating content quality with Aura before building the Instagram integration. If generated content quality is poor, Instagram publishing is wasted work.
- **Feedback loop last** because it requires weeks of accumulated data. Building it early means building infrastructure that sits idle.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 1 (Eval Baseline):** Rubric calibration methodology -- how to efficiently capture Aura's preferences and translate them into weighted criteria.
- **Phase 4 (Instagram Publishing):** Meta developer account setup, OAuth token flow, Graph API container model. Well-documented but procedurally complex.

Phases with standard patterns (skip research-phase):
- **Phase 2 (Transcription):** Deepgram SDK integration is well-documented. Keyword boosting API is straightforward.
- **Phase 3 (Content Generation):** LLM content generation with few-shot examples is a well-understood pattern. Telegram inline keyboards are established in the codebase.
- **Phase 5 (Feedback Loop):** Pattern already exists in trackctl and watchctl.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All recommended technologies have official documentation, pricing verified, most already in stack. |
| Features | MEDIUM-HIGH | Feature landscape well-defined by intake session and competitor analysis. Uncertainty: whether eval rubric aligns with Aura's actual preferences. |
| Architecture | MEDIUM-HIGH | Extends proven patterns (nightctl state machine, watchctl rubric, K8s Jobs). Uncertainty: Gateway Job creation RBAC untested. |
| Pitfalls | MEDIUM | Well-identified but prevention strategies theoretical until validated. Voice drift detection depends on Aura's subjective judgment. |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

- **Eval calibration protocol:** No concrete methodology for calibration phase. Needs definition during Phase 1 planning.
- **Zoom recording delivery path:** Three options identified but no decision. Ask Aura during Phase 2 kickoff.
- **Gateway Job creation RBAC:** New pattern not in fleet. Needs testing before Phase 3.
- **Deepgram keyword boosting on real recordings:** Theoretical confidence high, actual performance on Aura's audio unknown. Budget spike in Phase 2.
- **Meta developer account timeline:** Can take days to weeks. Start application during Phase 1.

## Sources

### Primary (HIGH confidence)
- [Deepgram Nova-3 docs](https://deepgram.com/learn/introducing-nova-3-speech-to-text-api) -- keyword boosting, pricing, SDK
- [Instagram Graph API publishing](https://developers.facebook.com/docs/instagram-platform/content-publishing/) -- container model, token lifecycle
- Existing codebase: watchctl/evaluate.py, watchctl/rubric.py, nightctl/, halctl/eval_harness.py

### Secondary (MEDIUM confidence)
- [DeepEval G-Eval docs](https://deepeval.com/docs/metrics-llm-evals) -- eval framework comparison
- [arxiv:2410.18363](https://arxiv.org/abs/2410.18363) -- contextual biasing for domain-specific transcription
- [Promptfoo self-hosting limitations](https://www.promptfoo.dev/docs/usage/self-hosting/) -- why not Promptfoo

### Tertiary (LOW confidence)
- Competitor feature analysis (OpusClip, Repurpose.io, Descript) -- feature landscape
- [FDA Digital Health Advisory Committee](https://www.lexology.com/library/detail.aspx?g=e58f075b-5bbc-41ab-95f7-87b379ceaa88) -- wellness content regulatory context

---
*Research completed: 2026-04-07*
*Ready for roadmap: yes*
