package index

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestWriteAndReadIndex(t *testing.T) {
	dir := t.TempDir()
	claudeFile := filepath.Join(dir, "CLAUDE.md")

	entries := []Entry{
		{
			ID:            "20260315-143022",
			File:          "memory/notes/20260315-143022-test.md",
			Title:         "Test note",
			Type:          "fact",
			Tags:          []string{"test"},
			Entities:      []string{"alice"},
			Summary:       "A test claim.",
			Hash:          "abc123",
			BacklinkCount: 0,
			Modified:      "2026-03-15T14:30:22Z",
		},
	}

	idx := &Index{
		NoteCount:     1,
		Entities:      []string{"alice"},
		TagVocabulary: []string{"test"},
		Notes:         entries,
	}

	err := Write(claudeFile, idx)
	if err != nil {
		t.Fatalf("Write: %v", err)
	}

	data, _ := os.ReadFile(claudeFile)
	content := string(data)

	if !strings.Contains(content, "LOOKUP PROTOCOL") {
		t.Error("missing LOOKUP PROTOCOL section")
	}
	if !strings.Contains(content, "MEMORY_INDEX") {
		t.Error("missing MEMORY_INDEX section")
	}
	if !strings.Contains(content, "20260315-143022") {
		t.Error("missing note entry in index")
	}

	parsed, err := Read(claudeFile)
	if err != nil {
		t.Fatalf("Read: %v", err)
	}
	if parsed.NoteCount != 1 {
		t.Errorf("NoteCount = %d, want 1", parsed.NoteCount)
	}
	if len(parsed.Notes) != 1 {
		t.Fatalf("len(Notes) = %d, want 1", len(parsed.Notes))
	}
	if parsed.Notes[0].ID != "20260315-143022" {
		t.Errorf("note ID = %q", parsed.Notes[0].ID)
	}
}

func TestVerifyDetectsDrift(t *testing.T) {
	dir := t.TempDir()
	notesDir := filepath.Join(dir, "memory", "notes")
	os.MkdirAll(notesDir, 0755)

	noteContent := []byte("---\nid: \"20260315-143022\"\n---\nBody.")
	noteFile := filepath.Join(notesDir, "20260315-143022-test.md")
	os.WriteFile(noteFile, noteContent, 0644)

	correctHash := HashBytes(noteContent)
	wrongHash := "0000000000000000000000000000000000000000000000000000000000000000"

	results := Verify([]Entry{
		{ID: "20260315-143022", File: noteFile, Hash: correctHash},
	})
	if results[0].Status != "MATCH" {
		t.Errorf("expected MATCH, got %s", results[0].Status)
	}

	results = Verify([]Entry{
		{ID: "20260315-143022", File: noteFile, Hash: wrongHash},
	})
	if results[0].Status != "DRIFT" {
		t.Errorf("expected DRIFT, got %s", results[0].Status)
	}

	results = Verify([]Entry{
		{ID: "20260315-143022", File: filepath.Join(notesDir, "nonexistent.md"), Hash: correctHash},
	})
	if results[0].Status != "MISSING" {
		t.Errorf("expected MISSING, got %s", results[0].Status)
	}
}
