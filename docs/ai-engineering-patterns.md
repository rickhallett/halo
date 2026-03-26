---
title: "AI Engineering Patterns - Field Notes"
category: reference
status: active
created: 2026-03-25
---

# AI Engineering Patterns — Field Notes

Source: [Augmented Coding Patterns](https://lexler.github.io/augmented-coding-patterns/) by Lada Kesseler et al.

Scraped 2026-03-25. 43 patterns, 10 anti-patterns, 14 obstacles.

---

## Obstacles — Know Your Limits

These are inherent to LLMs. You can't fix them, only work around them.

### Black Box AI
AI's reasoning is hidden. With code, you can open it up and see what's there. With AI, you only see inputs and outputs. AI has something resembling a human mental model, but you can't inspect it.

### Cannot Learn
Two fundamental limitations: **Fixed Weights** — the model cannot learn from your interactions. You can't teach it your coding style through conversation. **Statelessness** — no memory between API calls. What appears as "memory" is the tool re-sending all messages with each request.

### Compliance Bias
AI is trained to be helpful and compliant above all else. It will say "Sure thing, boss" even when your request makes no sense. It prioritizes following instructions over asking questions or pushing back — even when instructions are unclear, contradictory, or impossible.

### Context Rot
Context degrades as conversation grows. The model stops following earlier instructions, and performance drops unpredictably. This happens long before you hit the context window limit. Context doesn't decay evenly — it fades in zones.

### Degrades Under Complexity
AI struggles with complex, multi-step tasks requiring many moving pieces simultaneously. Reliability degrades as complexity increases, either through larger steps or larger artifacts. Small errors accumulate.

### Excess Verbosity
AI is a token machine — verbose by default. The level of detail you get rarely matches your actual level of curiosity. It overwhelms you with unnecessary detail, filler, and redundancy.

### Hallucinations
AI makes up APIs, methods, or syntax that don't exist. A minor inconvenience because code is self-verifiable — unlike factual hallucinations, code hallucinations are self-revealing (the code won't compile or run).

### Keeping Up
AI agents generate code faster than humans can review and understand it. The code is often verbose. Attempting to thoroughly understand every change becomes a bottleneck. AI focuses on speed and quantity over comprehensibility.

### Limited Context Window
Context has a fixed size limit. Once reached, older content has to be dropped or summarized. Everything you put in context competes for this limited space.

### Limited Focus
LLMs have limited attention. Everything you load into context competes for that attention. When too much is loaded at once, the model either ignores or deprioritizes items.

### Non-Determinism
AI outputs are non-deterministic. The same input may yield different results across runs. Responses can vary in quality: sometimes worse, sometimes better.

### Obedient Contractor
AI behaves like a contractor hired for a single day — focused on completing the immediate task and leaving quickly. Short-term mindset: prioritizes getting the job done now over long-term maintainability. Excessive politeness: treats contradicting the original request as impolite. Won't push back even when it should.

### Selective Hearing
Even after narrowing scope and pruning ground rules, AI still ignores certain instructions. It filters based on what it deems important (from training), not what you mark important. Your instructions compete against billions of training examples. Root causes: contradicting training data, attention overload.

### Solution Fixation
AI latches onto the first plausible solution and loses critical thinking. When it finds something that might be the problem, it declares "found it!" and stops exploring alternatives.

---

## Anti-Patterns — What NOT to Do

### AI Slop
Accepting AI output without review. Just letting it generate and commit without checking quality, correctness, or fit.

### Answer Injection
You already have a solution in mind and unconsciously steer AI toward it. Your framing constrains AI's exploration space. You get confirmation of your idea instead of AI's best suggestion. The more specific your question, the more you inject your answer into it. Instead: describe the problem, not your solution. Let AI explore freely first.

### Distracted Agent
Overloading AI with too many responsibilities at once. Every additional concern dilutes focus on the primary task. Ground rules get ignored, quality drops across the board. The fix: focused agents with single responsibilities.

### Flying Blind
Working with AI without feedback mechanisms. No tests, no verification, no way to know if the output is correct. You're trusting without verifying. The AI has no way to check its own work.

### Obsess Over Rules
Spending excessive time perfecting ground rules and system prompts instead of getting work done. Diminishing returns on prompt engineering. Better to start working and iterate on rules as problems surface.

### Perfect Recall Fallacy
Assuming AI remembers everything from earlier in the conversation. It doesn't. Context degrades. Important instructions from the beginning get lost. Don't assume — reinforce critical information.

### Silent Misalignment
AI appears to understand your request but has a fundamentally different interpretation. It implements confidently but in the wrong direction. The danger: AI never asks for clarification — it just builds what it thinks you meant. By the time you notice, significant work is wasted. Prevention: check alignment before implementation.

### Sunk Cost
Continuing with a failing AI approach because you've already invested time. Trying to fix broken AI output instead of reverting and starting fresh. AI-generated code is cheap to regenerate. Your time spent debugging bad output is expensive. Revert early, revert often.

### Tell Me a Lie
Asking AI to confirm something instead of asking it to evaluate. "This is correct, right?" vs "What's wrong with this?" The former invites compliance bias. The latter invites honest critique.

### Unvalidated Leaps
Letting AI make large changes without intermediate verification. Multiple steps combined into one big leap. If anything goes wrong, you can't tell which step failed. Break into small, verifiable steps instead.

---

## Patterns — What TO Do

### Context & Knowledge Management

**Context Management** — Treat context as a scarce, degrading resource. You have only two operations: append to context (prompt it) and reset it (start a new conversation). Everything you do with AI works within this constraint.

**Ground Rules** — Knowledge documents that auto-load when you open a session. Put only your most important things here — behaviors, tools, context, links. Whatever is essential for each scope.

**Knowledge Document** — Save important information to markdown files. Load them into context when needed. Makes resetting easier: extract valuable parts to files first, then load into clean context.

**Knowledge Checkpoint** — Before attempting implementation, checkpoint the plan. Extract planning knowledge to a document, git commit. If implementation fails, git reset and retry without redoing planning. Protect your time, not the code.

**Knowledge Composition** — Split knowledge into focused, composable files. Single responsibility per file. Load only what's relevant for the current task instead of polluting context with everything.

**Extract Knowledge** — Like "extract variable" for conversations. When you figure something out, explicitly ask AI to save it to a file. Save as you go — don't wait until end of session.

**Reference Docs** — On-demand knowledge documents. Load only when needed, unlike ground rules which are always loaded. Keeps context focused.

**Pin Context** — Keep critical information persistent across the conversation. Pin important context so it doesn't degrade. Reinforce what matters.

**Rolling Context** — Actively manage context as conversation grows. Summarize and compress earlier parts. Keep recent context fresh while preserving essential earlier knowledge.

**Lean Context** — Minimize what's in context. Less noise = better signal. Only load what's directly relevant to the current task. Remove anything that's not actively needed.

**Context Markers** — Use visual markers (emojis) to signal active context. Start responses with markers showing current mode. Makes invisible parts of context visible at a glance.

**Noise Cancellation** — Explicitly ask AI to be succinct. Strip filler, compress to essence. For documents: regularly compress, remove outdated info. Delete mercilessly.

**Semantic Zoom** — AI makes text elastic. Control level of detail by how you ask. Zoom out for overview, zoom in for details. Expand, collapse, shift abstraction levels on demand.

### Workflow & Process

**Chain of Small Steps** — Break complex goals into small, focused, verifiable steps. Execute each with AI, verify, commit, move to next. Small steps are reliable — narrow focus that AI handles well. Verification catches problems early.

**One Thing at a Time** — Give AI a single focused task. Don't combine multiple concerns. Sequential focused tasks beat one complex multi-part task.

**Smallest Useful Step** — Find the minimum increment that's still useful. Not the smallest possible step (too slow), not the biggest possible step (too risky). The sweet spot where progress is meaningful and verification is easy.

**Prompt-Commit-Test** — Tight loop: prompt AI, review output, commit if good, test. Keep iterations small and verifiable. Each cycle produces a tested, committed increment.

**Semi-Automated Workflow** — Human stays in the loop but AI does the heavy lifting. You steer, AI executes. Review at checkpoints rather than every keystroke.

**Feedback Loop** — Set up automated feedback, give AI permission to iterate autonomously. Identify clear success signal (tests pass, UI matches). Grant permission: "Keep iterating until tests pass." Step away. Human elevates from tactical executor to strategic director.

**Feedback Flip** — Flip from producing to evaluating. AI implements, then different AI (or same AI refocused) reviews: "Find problems and suggest improvements." Feed critique back. When implementing, AI hyper-focuses on completion. Flip to finding problems — now quality is the main goal.

**Refinement Loop** — Give AI a specific improvement goal and loop. Each iteration removes a layer of noise, making the next layer visible. Repeat until nothing noticeable to improve.

**Observe and Calibrate** — Watch how AI behaves, adjust your approach based on what works and what doesn't. Calibrate expectations and prompts to the model's actual capabilities.

### Testing & Quality

**Red-Green-Refactor** — Classic TDD cycle with AI. Write a failing test (red), AI implements to pass (green), refactor. AI is great at the green step.

**Outside-In TDD** — Start from the outermost behavior and work inward. Write acceptance test first, then implement layer by layer. AI implements each layer to satisfy the current failing test.

**Test-First Agent** — AI writes tests before implementation. Forces thinking about requirements and edge cases upfront. Tests become the specification.

**Test Guardian** — Dedicated agent or process that watches test quality. Ensures tests are meaningful, not just coverage theater.

**Constrained Tests** — Create domain-specific testing language that makes it impossible to write tests without sufficient assertions. External DSLs make it easier to enforce required components.

**Approved Fixtures** — Design tests around approval files combining input and expected output in a domain-specific format. Validate test execution logic once; after that, adding new tests only requires reviewing fixtures.

**Approved Logs** — Turn production logs into regression tests. When a bug appears: grab logs, fix incorrect lines to show expected behavior, save as test file. Requires structured logging throughout.

**Canary in the Code Mine** — When AI struggles with code changes, treat this as a signal that code quality is degrading. The AI's struggle is your canary — an early warning that code quality is declining.

**Review Generated Code** — Always review what AI generates. Don't blindly accept. Look for: correctness, style consistency, unnecessary complexity, security issues, test coverage.

**Ongoing Refactoring** — Continuously refactor AI-generated code. Don't let technical debt accumulate. AI tends to produce functional but not always clean code. Regular refactoring keeps the codebase healthy.

### Prompting & Communication

**Intentional Prompt** — Be deliberate about how you prompt. Structure matters. Clear, specific prompts get better results than vague ones. Think about what you're asking before you ask it.

**Structured Prompt** — Format prompts with clear sections: context, task, constraints, examples. Structure helps AI parse your intent correctly. Reduces ambiguity.

**Check Alignment** — Before letting AI implement, make it show its understanding. Force it to be succinct. When you see something, you immediately spot what needs adjusting. Catch it early.

**Active Partner** — Grant AI permission to push back on unclear instructions, challenge assumptions, flag contradictions, say "I don't understand." Transform one-way command into two-way dialogue. Actively reinforce: "What do you really think?"

**Thinking Out Loud** — Have AI explain its reasoning as it works. Makes the thought process visible and reviewable. Helps catch misunderstandings early.

**Rubber Duck AI** — Use AI as a sounding board. Explain your problem to it. The act of explaining often reveals the solution, and AI may offer useful perspectives.

**Mind Dump** — Speak unfiltered thoughts directly into AI. Don't organize — just dump everything. Modern dictation + AI's natural language understanding. Speed of voice enables qualitative shift from crafted prompts to stream of consciousness.

**Reverse Direction** — Break conversational inertia. AI asks you to decide → "What do you think?" You're stuck telling → "What questions do you have?" Turns monologue into dialogue.

### Architecture & Code

**LLM-Friendly Code** — Write code that AI can understand and work with effectively. Clear naming, consistent patterns, good documentation. Code that's readable by humans is usually readable by AI.

**Coerce to Interface** — Design MCP tool interfaces that enforce structure through API definition. Required fields, enums, typed parameters become constraints the agent cannot bypass. Shifts enforcement from instructions to mechanism.

**Borrow Behaviors** — AI can quickly grab and transform from other sources. Show a JavaScript pattern, get the Python version. Point to a Figma design, get matching CSS.

**Spec to Test** — Turn specifications directly into test cases. AI excels at this transformation. Specs become living, executable documentation.

### Multi-Agent & Delegation

**Multi-Agent** — Use multiple AI agents, each with focused responsibilities. Divide and conquer complex tasks across specialized agents.

**Background Agent** — Delegate standalone tasks to background agents running in parallel. Collect todos, identify delegatable tasks, spawn agents, continue main work, integrate results when ready.

**Focused Agent** — Prefer single, narrow responsibility on important tasks. Gives AI cognitive space to follow ground rules, pay attention to details, perform at its best.

**Chunking** — Main orchestrator agent with focused subagents. Main agent stays strategic (plans, designs, breaks down work). Subagents handle execution (read files, implement, test). Like humans delegating practiced skills to automatic processes.

**Orchestrator** — Dedicated agent that monitors background work, integrates changes, resolves conflicts, runs tests, updates main trunk.

**Parallel Implementations** — Run multiple implementations in parallel from the same checkpoint. Fork, launch multiple AIs simultaneously, review all, pick the best. Trading tokens (cheap) for your time (expensive).

### Exploration & Prototyping

**Cast Wide** — Don't settle for your first solution. Push AI for alternatives: "What alternative solutions might be possible that we haven't considered?" Iterate several times with different agents.

**Trust but Verify** — Use AI's output but always verify. Trust the capability, verify the result. Automated tests, manual review, sanity checks.

**Take All Paths** — Prototyping is now so cheap you can try all paths. Build 10 variations, test them all, pick the best. Actually feel how each works instead of imagining it.

**Softest Prototype** — AI + files is softer than software. Use AI as flexible agent with markdown instructions instead of code. Discover what you need by using it. Shape solution while using it. Pivot instantly.

**Playgrounds** — Create isolated playground folders where AI can experiment safely. When AI gets stuck or when working with new libraries/languages.

### Habits & Automation

**Habit Hooks** — Deterministic scripts that detect triggers (quality violations) and provide actionable prompts. Reduces context bloat while improving compliance.

**Hooks** — Lifecycle event hooks that intercept agent workflow at specific trigger points. Inject targeted prompts, corrections, validations, or monitoring. Deterministic + custom scripts = flexible and reliable correction.

**Show the Agent, Let It Repeat/Automate** — Work through task together, document the process, AI attempts using docs, refine docs, repeat until AI works independently, optionally automate mechanical steps.

**Offload Deterministic** — Don't ask AI to do deterministic work. Ask AI to write code that does it. Use AI to explore. Use code to repeat.

**Reminders** — AI has recency bias. Force attention on what matters through repetition: TODOs as explicit checkboxes, instruction sandwich (repeat critical instructions where they matter), user reminders injected into every message.

### Knowledge & Documentation

**Knowledge Base** — Maintain a structured knowledge base that AI can reference. Accumulated institutional knowledge accessible to AI agents.

**JIT Docs** — Rely on up-to-date documentation searched in real-time rather than AI's outdated training data. Point AI to docs, it searches relevant sections based on task.

**Shared Canvas** — Text/markdown files as shared workspace. All humans and AI collaborate in it. Specs both can refine, docs both can update, plans both can modify.

**Text Native** — Text is AI's native medium. Stay in text. Everything is directly editable, no barriers, instant iteration, version-controlled by default.

### Modality

**Polyglot AI** — Use the right modality. Voice for natural speech and hands-free. Images both ways — AI reads screenshots, diagrams. Show a mockup, get implementation. Show a bug screenshot, get diagnosis.

**Happy to Delete** — Embrace disposability of AI-generated code. Revert freely. Start fresh with lessons learned. Git liberally. The willingness to delete removes pressure to "make it work" and paradoxically leads to better outcomes faster.

---

## Key Takeaways

1. **Context is everything** — Treat it as scarce, manage it actively, reset often, externalize knowledge to files
2. **Small steps beat big leaps** — Break down, verify, commit, repeat
3. **AI is an obedient contractor** — It won't push back unless you explicitly grant permission
4. **Code is cheap, your time isn't** — Revert early, try multiple approaches, delete freely
5. **Tests are your safety net** — TDD patterns work especially well with AI; tests catch what review misses
6. **Multi-agent beats single agent** — Focused agents with narrow scope outperform overloaded ones
7. **Don't fight the obstacles, work around them** — Context rot, non-determinism, and compliance bias are features of the technology, not bugs to fix
8. **Automate the deterministic, explore with AI** — Use each tool for what it's good at
9. **Verify everything** — Trust but verify. AI slop is the default without active review
10. **Knowledge compounds** — Extract, document, compose, and maintain your knowledge base across sessions
