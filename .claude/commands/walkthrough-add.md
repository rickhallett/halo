---
description: Add an entry to the system walkthrough (docs/d1/walkthrough/)
---

# Walkthrough: Add Entry

Add content about **$ARGUMENTS** to the system walkthrough.

## Process

1. **Read the current index** at `docs/d1/walkthrough/index.md` to determine the next entry number.

2. **Determine the file:**
   - If `--new` appears in the arguments: create a new numbered file (e.g., `002-topic-slug.md`).
   - Otherwise: append to the most recent existing entry file (the highest-numbered file in the index).

3. **Write the content:**
   - For new files: use the format established by `001-codebase-census.md` — title with number, date, clear sections.
   - For appending: add a new `## Section` to the existing file.
   - Content should capture understanding gained, not just facts. Include "why it works this way" and connections to other parts of the system.

4. **Update the index** at `docs/d1/walkthrough/index.md`:
   - For new files: add a row to the entries table.
   - For appends: update the topic description of the existing row if the scope has expanded.

## Quality Bar

Each walkthrough entry should leave the reader able to:
- Explain the component's purpose in one sentence
- Identify its inputs, outputs, and side effects
- Name the files involved and their roles
- Describe how it connects to adjacent components

## Arguments

The arguments describe the topic or area to document. Examples:
- `/walkthrough-add the message lifecycle from Telegram to container response --new`
- `/walkthrough-add how IPC authentication works` (appends to current entry)
- `/walkthrough-add briefing pipeline: gather, synthesise, deliver --new`
