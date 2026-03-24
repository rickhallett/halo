---
id: 20260323-020617-615
title: Agentic AI Twitter Monitoring System — Research Report
type: reference
tags:
- xitter
- agentic-ai
- monitoring
- system-design
- x-api
- twitter
- agents
entities:
- karpathy
- lilianweng
- swyx
- langchain
- cursor
- devin
- twscrape
- x-cli
- memctl
- nightctl
confidence: high
created: '2026-03-23T02:06:17Z'
modified: '2026-03-23T02:06:17Z'
expires: null
---

# X/Twitter Agentic AI Monitoring System — Research Report

Generated: 2026-03-23

## 1. Key Accounts to Monitor

Starting from Karpathy's network, these are the top voices in agentic AI engineering.

### Tier 1 — Nucleus

| Handle | Name | Affiliation | Why They Matter |
|--------|------|-------------|-----------------|
| @karpathy | Andrej Karpathy | Eureka Labs / Independent | Coined "agentic engineering" and "vibe coding". His Dec 2025 "profession is being dramatically refactored" thread got 14M+ views. "March of nines" framework for agent reliability. ~1.9M followers, tight following list (~1,069) = signal-dense. |
| @lilianweng | Lilian Weng | Thinking Machines Lab (ex-OpenAI VP) | Author of canonical "LLM-Powered Autonomous Agents" blog post (June 2023) — foundational reference for the entire field. Defined agent memory, planning, tool use. |
| @polynoamial | Noam Brown | OpenAI | Co-created o1/o3 reasoning models — the foundational technology powering all modern agentic loops. Posts on test-time compute scaling. |
| @ShunyuYao12 | Shunyu Yao | OpenAI (ex-Princeton) | Author of ReAct (ICLR 2023 Oral), Tree of Thoughts, SWE-bench, Reflexion, WebShop. These papers define canonical agent reasoning patterns used in virtually every production agent. |

### Tier 2 — Builders & Framework Architects

| Handle | Name | Affiliation | Why They Matter |
|--------|------|-------------|-----------------|
| @hwchase17 | Harrison Chase | LangChain CEO | Created LangChain and LangGraph — dominant agent orchestration framework. "Deep agents" concept shaping enterprise architecture. |
| @simonw | Simon Willison | Independent (Datasette, llm CLI) | Best practitioner blogger on LLM tool use and agents. Proposed widely-adopted definition: "An LLM agent runs tools in a loop to achieve a goal." Tracks what actually works vs hype. |
| @paulgauthier | Paul Gauthier | Aider (independent) | Built Aider — one of the most popular open-source autonomous coding agents. Publishes rigorous model coding leaderboards. |
| @swyx | Swyx (Shawn Wang) | Smol.ai / Latent Space | Coined "Rise of the AI Engineer." Organizes AI Engineer World's Fair. Latent Space podcast is the most technically rigorous interviews on agent frameworks. |
| @ScottWu46 | Scott Wu | Cognition (Devin) | Built Devin — first publicly demonstrated fully autonomous AI software engineer. Shaped the autonomous coding agent market. |
| @amanrsanger | Aman Sanger | Cursor / Anysphere ($29B) | Co-built Cursor — most widely adopted AI coding environment (360K devs, 50%+ Fortune 500). Pioneered human-AI agentic collaboration UX. |

### Tier 3 — Advocates, Researchers & Adjacent Operators

| Handle | Name | Affiliation | Why They Matter |
|--------|------|-------------|-----------------|
| @alexalbert__ | Alex Albert | Anthropic (Claude Relations) | Head of Claude Relations. Most public-facing voice for Claude Code and Anthropic's agentic vision. MCP champion. |
| @ErikSchluntz | Erik Schluntz | Anthropic (Claude Code) | Co-authored "Building Effective Agents" essay. Led Claude Code engineering. |
| @DrJimFan | Jim Fan | NVIDIA GEAR Lab | Director of AI. Leads Project GR00T (humanoid robotics). Creator of Voyager (Minecraft agent), Eureka. Bridges software agents and physical AI. |
| @emollick | Ethan Mollick | Wharton / UPenn | Foremost researcher on how humans work with AI agents professionally. Evidence-based views on agent adoption and human-AI teaming. |
| @yoheinakajima | Yohei Nakajima | Untapped Capital | Created BabyAGI (April 2023) — one of the first viral autonomous agent frameworks. Demonstrated the agent loop concept publicly. |
| @AndrewYNg | Andrew Ng | DeepLearning.AI | Systematized agentic design patterns (reflection, tool use, planning, multi-agent) for 1M+ practitioners. |
| @thorstenball | Thorsten Ball | Sourcegraph / Zed | Published "How to build a code-editing agent in 315 lines" — widely-shared demystification. Daily builder-level takes on agentic coding tools. |
| @GregKamradt | Greg Kamradt | ARC Prize | Leads ARC-AGI benchmark — de facto measure of genuine reasoning vs pattern matching. Also: semantic chunking, LLM context evaluation. |
| @DarioAmodei | Dario Amodei | Anthropic CEO | Predicted AI writing 90% of code within 3-6 months (early 2025, proved accurate). Shapes Claude agent vision and industry direction. |

### Honorable Mentions
- @OfficialLoganK (Logan Kilpatrick) — ex-OpenAI DevRel, now Google AI Studio PM
- @levelsio (Pieter Levels) — prolific indie hacker using vibe coding, high practitioner signal
- @rohanpaul_ai — high-signal aggregator for agentic coding news


## 2. System Design

### Available APIs and Tools

**Official X API v2:**

| Tier | Cost/month | Tweet Reads | Search Window | Streaming |
|------|-----------|-------------|---------------|-----------|
| Free | $0 | ~100/month | None | No |
| Basic | $100 | 10,000/month | 7 days | No |
| Pro | $5,000 | 1,000,000/month | Full archive | Yes (1 conn) |

Key endpoints for monitoring:
- `GET /2/users/:id/tweets` — user timeline (10K req/15min, app-level)
- `GET /2/tweets/search/recent` — keyword/`from:` search, 7-day window (450 req/15min)
- `GET /2/lists/:id/tweets` — list timeline, most efficient for bulk account monitoring
- `GET /2/tweets/search/stream` — real-time filtered stream (Pro+ only)

Rate limits reset every 15 minutes. Monthly quotas and per-window limits are independent.

**OSS Alternatives (2025 status):**

| Tool | Status | Method | Risk |
|------|--------|--------|------|
| twscrape | ✅ Active | GraphQL internal API via X accounts | Medium (ToS violation, account ban risk) |
| twikit | ✅ Active | Internal API, session-based | Medium |
| snscrape | ❌ Dead | Scraping (broken since Apr 2023) | N/A |
| nitter | ❌ Unreliable | RSS/scraping | N/A |

**Key finding:** twscrape's `list_timeline` endpoint is the most cost-efficient approach for bulk monitoring — put all target accounts into an X List (up to 1,400 accounts), poll one endpoint. No API costs, but violates X ToS and risks account bans.

**Recommended approach for halos:**
- X API Basic ($100/month) for compliance safety: poll `user_tweets` per account or `list_timeline`
- Or twscrape with a burner account pool for zero-cost (accepts ToS risk)
- The existing `x-cli` tool (xitter skill) covers reads and writes via OAuth 1.0a

### Architecture for Cron Monitoring Agent

```
cron schedule (e.g. every 6 hours)
    → monitoring agent fires
    → for each monitored account: fetch last N tweets (since last run)
    → deduplicate against seen tweet IDs (stored in memctl or SQLite)
    → pass new tweets to synthesis LLM
    → store synthesis note in memctl
    → optionally: post digest to Telegram via gateway
    → update nightctl task state
```


## 3. Implementation Plan

### Phase 1 — Account Seeding (one-time)
1. Create a watchlist note in memctl with initial 20 handles from this report
2. Create an X List containing all target accounts (via x-cli or web UI)
3. Store List ID in memctl as a config note

### Phase 2 — Cron Job Setup
Using nanoclaw cron infrastructure:

```python
# cron/jobs.py — add a new job entry
{
    "name": "xitter_monitor",
    "schedule": "0 */6 * * *",   # every 6 hours
    "task": "monitor_agentic_ai_twitter",
    "enabled": True
}
```

The job should:
1. Load watchlist from memctl (`memctl search --tags xitter-watchlist`)
2. For each account (or via List), fetch recent tweets using x-cli:
   ```bash
   x-cli -j user timeline <handle> --max 20
   ```
3. Filter out: retweets (unless comment), tweets older than last run timestamp
4. Deduplicate against stored tweet IDs in a memctl note or local SQLite
5. Pass batched new tweets to synthesis step

### Phase 3 — Signal Synthesis
Feed new tweets to an LLM synthesis call (via the halos HAL briefing infrastructure or direct API call).

### Phase 4 — Storage and Delivery
- Store synthesis as a new memctl note (type: insight, tags: agentic-ai, xitter-digest)
- Optionally route digest to Telegram via halos gateway
- Track job runs in nightctl

### Using Existing Halos Infrastructure
- **Scheduling**: nanoclaw cron scheduler (`cron/scheduler.py`, `cron/jobs.py`)
- **X access**: xitter skill → `x-cli -j user timeline <handle> --max 20`
- **Memory**: memctl for watchlist storage, seen-tweet deduplication, synthesis notes
- **Task tracking**: nightctl to track monitoring runs, flag errors, log when new signal found
- **Delivery**: halos gateway → Telegram for digest delivery
- **Synthesis LLM**: use HAL briefing pattern (auxiliary_client in claude-code, or direct Anthropic API call in nanoclaw)


## 4. Signal Synthesis — Prompt Design

### Synthesis Prompt Template

```
You are an agentic AI engineering research analyst. Your job is to surface the highest-signal content from a stream of recent tweets by leading figures in agentic AI.

Context: These accounts are chosen for their technical credibility and direct involvement in building, researching, or deploying AI agents.

Input: The following tweets were posted in the last 6 hours by monitored accounts. Each entry includes the author handle, timestamp, and tweet text.

---
{formatted_tweets}
---

Your task:
1. IGNORE: retweets without commentary, promotional announcements, personal anecdotes unrelated to AI/agents
2. FLAG as HIGH SIGNAL: new papers, new tools/repos, benchmark results, architectural insights, opinion shifts, warnings about risks or failures
3. FLAG as MEDIUM SIGNAL: threads explaining concepts, interesting observations about AI progress, links to good external content
4. SYNTHESISE: write a concise digest (3-5 bullet points) of the most important developments. Each bullet should name the author and give a 1-2 sentence summary.
5. HIGHLIGHT: call out any emerging consensus or recurring theme across multiple authors
6. If nothing significant was posted, say "No high-signal content in this window."

Output format:
## Agentic AI Signal Digest — {date} {time_window}

### High Signal
- @handle: [summary]

### Medium Signal  
- @handle: [summary]

### Recurring Themes
[if any]

### Assessment
[1-2 sentence overall read on the window]
```

### Deduplication and Memory
- Store processed tweet IDs in a memctl note (type: state, id: xitter-seen-tweets)
- Only synthesise new content each run
- Link synthesis notes to watchlist note via memctl backlinks


## 5. Gaps and Risks

### API Costs
- X Basic ($100/month) is the minimum viable paid tier for polling 20 accounts without ToS risk
- 10,000 tweet reads/month = ~500 tweets/day = ~25 tweets/day per account — tight but workable for 20 accounts at 6-hour polling
- Pro ($5,000/month) is needed for real-time streaming or >10K reads — not justified here
- Alternative: twscrape with burner accounts avoids costs but carries ban risk and ToS violation

### Rate Limits
- x-cli uses OAuth 1.0a; user-level rate limits apply (900 user timeline req / 15 min — very generous for 20 accounts)
- If polling every 6 hours with 20 accounts = 80 API calls/day, well within Basic limits
- Key bottleneck: the 10,000 tweet/month read quota (not the per-window rate limit)

### Account Suspension Risk (twscrape path)
- X actively bans scraper accounts; rotating burner account pools + proxies required
- Violation of X ToS creates legal exposure for commercial use
- Recommendation: use official API for this use case (commercial/personal tool building)

### Content Quality vs. Noise
- These 20 accounts post 5-20 tweets/day each = up to 400 tweets/day raw
- Most will be noise (casual comments, retweets, jokes)
- Synthesis prompt must aggressively filter; consider caching and only synthesising when >3 high-signal items found
- Risk: LLM synthesis may hallucinate importance of marginal content — mitigate by including raw tweet text in synthesis output for spot-checking

### Account List Drift
- The agentic AI space moves fast; today's key accounts may be less relevant in 6 months
- Build in a quarterly review step (nightctl recurring task) to evaluate watchlist
- Consider automated discovery: when a monitored account frequently retweets or mentions a non-monitored account, flag for potential addition

### Tool Maintenance
- x-cli is upstream OSS (github.com/Infatoshi/x-cli) — must track for breaking changes
- X API policy changes historically without warning; the Free→Basic→Pro tier structure may shift
- xitter skill's credential setup (5 secrets) is high-friction; document clearly and store securely in ~/.hermes/.env


## References
- X API v2 documentation: https://developer.x.com/en/docs/x-api
- x-cli (xitter skill): https://github.com/Infatoshi/x-cli
- twscrape: https://github.com/vladkens/twscrape
- Anthropic "Building Effective Agents": https://www.anthropic.com/research/building-effective-agents
- Lilian Weng "LLM Powered Autonomous Agents": https://lilianweng.github.io/posts/2023-06-23-agent/
- Latent Space / AI Engineer World's Fair: https://latent.space
