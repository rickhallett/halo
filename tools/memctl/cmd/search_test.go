package cmd

import (
	"testing"

	"github.com/rickhallett/nanoclaw/tools/memctl/internal/index"
)

func TestSearchByEntity(t *testing.T) {
	idx := &index.Index{
		NoteCount: 2,
		Notes: []index.Entry{
			{ID: "1", File: "a.md", Title: "About Alice", Entities: []string{"alice"}, Tags: []string{"auth"}, Type: "decision"},
			{ID: "2", File: "b.md", Title: "About Bob", Entities: []string{"bob"}, Tags: []string{"infra"}, Type: "fact"},
		},
	}

	results := searchIndex(idx, "", []string{"alice"}, "", "", false)
	if len(results) != 1 || results[0].ID != "1" {
		t.Errorf("expected 1 result for alice, got %d", len(results))
	}
}

func TestSearchByTag(t *testing.T) {
	idx := &index.Index{
		Notes: []index.Entry{
			{ID: "1", Tags: []string{"auth", "postgres"}, Type: "decision"},
			{ID: "2", Tags: []string{"infra"}, Type: "fact"},
			{ID: "3", Tags: []string{"auth", "security"}, Type: "fact"},
		},
	}

	results := searchIndex(idx, "", nil, "auth", "", false)
	if len(results) != 2 {
		t.Errorf("expected 2 results for tag=auth, got %d", len(results))
	}
}
