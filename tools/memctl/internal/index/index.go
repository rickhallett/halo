package index

import (
	"bytes"
	"fmt"
	"os"
	"strings"
	"time"

	"gopkg.in/yaml.v3"
)

type Entry struct {
	ID            string   `yaml:"id"`
	File          string   `yaml:"file"`
	Title         string   `yaml:"title"`
	Type          string   `yaml:"type"`
	Tags          []string `yaml:"tags,flow"`
	Entities      []string `yaml:"entities,flow,omitempty"`
	Summary       string   `yaml:"summary"`
	Hash          string   `yaml:"hash"`
	BacklinkCount int      `yaml:"backlink_count"`
	Modified      string   `yaml:"modified"`
	Expires       *string  `yaml:"expires"`
}

type Index struct {
	Generated     string   `yaml:"generated"`
	NoteCount     int      `yaml:"note_count"`
	Entities      []string `yaml:"entities,omitempty"`
	TagVocabulary []string `yaml:"tag_vocabulary,omitempty"`
	Notes         []Entry  `yaml:"notes"`
}

type VerifyResult struct {
	ID     string `json:"id"`
	File   string `json:"file"`
	Status string `json:"status"` // MATCH, DRIFT, MISSING
}

const lookupProtocol = `# MEMORY INDEX
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
   Run ` + "`memctl index verify`" + ` to surface all drift.

3. Load only the matching note files. Do not load the full corpus.

4. If no candidates match, say so. Do not hallucinate memory.

5. To write a new note: call ` + "`memctl new`" + ` with structured args.
   Do not write to memory files directly.

6. A note with type=decision is treated as authoritative.
   A note with confidence=low should be stated with uncertainty.
   A note with an expires date in the past should be treated as stale.

## HOW TO USE MEMORY

### Writing a note
Always use memctl. Never write to memory files directly.

` + "```" + `
memctl new \
  --title "Short factual title" \
  --type [decision|fact|reference|project|person|event] \
  --tags tag1,tag2 \
  --entities entity1,entity2 \
  --confidence [high|medium|low] \
  --body "Single claim. One sentence if possible."
` + "```" + `

One claim per note. If you need to record two things, run memctl new twice.
Use --link-to <id> if the new note references an existing one.

### What you must not do
- Do not hand-edit CLAUDE.md or any note file
- Do not invent backlinks — use memctl link
- Do not prune or archive notes — that is a scripted job
- Do not write notes with multiple claims

`

func Write(path string, idx *Index) error {
	idx.Generated = time.Now().UTC().Format(time.RFC3339)

	var yamlBuf bytes.Buffer
	enc := yaml.NewEncoder(&yamlBuf)
	enc.SetIndent(2)
	if err := enc.Encode(idx); err != nil {
		return fmt.Errorf("marshal index: %w", err)
	}
	enc.Close()

	var buf bytes.Buffer
	buf.WriteString(lookupProtocol)
	buf.WriteString("## MEMORY_INDEX\n")
	buf.WriteString("```yaml\n")
	buf.Write(yamlBuf.Bytes())
	buf.WriteString("```\n")

	return os.WriteFile(path, buf.Bytes(), 0644)
}

func Read(path string) (*Index, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}

	content := string(data)
	start := strings.Index(content, "```yaml\n")
	if start == -1 {
		return &Index{}, nil
	}
	start += len("```yaml\n")

	end := strings.Index(content[start:], "```")
	if end == -1 {
		return nil, fmt.Errorf("unterminated YAML block in %s", path)
	}

	yamlBlock := content[start : start+end]

	var idx Index
	if err := yaml.Unmarshal([]byte(yamlBlock), &idx); err != nil {
		return nil, fmt.Errorf("parse index YAML: %w", err)
	}
	return &idx, nil
}

func Verify(entries []Entry) []VerifyResult {
	var results []VerifyResult
	for _, e := range entries {
		hash, err := HashFile(e.File)
		if err != nil {
			results = append(results, VerifyResult{ID: e.ID, File: e.File, Status: "MISSING"})
			continue
		}
		if hash != e.Hash {
			results = append(results, VerifyResult{ID: e.ID, File: e.File, Status: "DRIFT"})
		} else {
			results = append(results, VerifyResult{ID: e.ID, File: e.File, Status: "MATCH"})
		}
	}
	return results
}
