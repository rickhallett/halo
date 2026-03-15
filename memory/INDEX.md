# MEMORY INDEX
<!-- AUTO-MAINTAINED BY memctl — DO NOT HAND-EDIT THE YAML BLOCK -->
<!-- Run: memctl index verify   to check for drift              -->
<!-- Run: memctl index rebuild  to regenerate from notes corpus -->

## LOOKUP PROTOCOL

When answering a question that may depend on stored memory:

1. Parse MEMORY_INDEX below. Identify candidate notes by:
   a. entity intersection (does the query mention a known entity?)
   b. tag intersection (does the query map to known tags?)
   c. type filter (decisions? facts? people?)

2. For each candidate, check: does the hash in the index match
   the file? If not, flag drift and re-read the file directly.
   Run `memctl index verify` to surface all drift.

3. Load only the matching note files. Do not load the full corpus.

4. If no candidates match, say so. Do not hallucinate memory.

5. To write a new note: call `memctl new` with structured args.
   Do not write to memory files directly.

6. A note with type=decision is treated as authoritative.
   A note with confidence=low should be stated with uncertainty.
   A note with an expires date in the past should be treated as stale.

## HOW TO USE MEMORY

### Writing a note
Always use memctl. Never write to memory files directly.

```
memctl new \
  --title "Short factual title" \
  --type [decision|fact|reference|project|person|event] \
  --tags tag1,tag2 \
  --entities entity1,entity2 \
  --confidence [high|medium|low] \
  --body "Single claim. One sentence if possible."
```

One claim per note. If you need to record two things, run memctl new twice.
Use --link-to <id> if the new note references an existing one.

### What you must not do
- Do not hand-edit CLAUDE.md or any note file
- Do not invent backlinks — use memctl link
- Do not prune or archive notes — that is a scripted job
- Do not write notes with multiple claims

## MEMORY_INDEX
```yaml
generated: "2026-03-15T20:34:11Z"
note_count: 0
tag_vocabulary:
  - architecture
  - auth
  - blocker
  - database
  - deadline
  - decision
  - deployment
  - infra
  - person
  - postgres
  - resolved
  - security
notes: []
```
