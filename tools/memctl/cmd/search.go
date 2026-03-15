package cmd

import (
	"encoding/json"
	"fmt"
	"os"
	"strings"

	"github.com/rickhallett/nanoclaw/tools/memctl/internal/config"
	"github.com/rickhallett/nanoclaw/tools/memctl/internal/index"
	"github.com/spf13/cobra"
)

var (
	searchTags     string
	searchEntities string
	searchType     string
	searchText     string
	searchSince    string
	searchExpired  bool
	searchLimit    int
)

var searchCmd = &cobra.Command{
	Use:   "search",
	Short: "Search notes by tag, entity, type, or text",
	RunE:  runSearch,
}

func init() {
	searchCmd.Flags().StringVar(&searchTags, "tags", "", "match notes with ALL these tags")
	searchCmd.Flags().StringVar(&searchEntities, "entities", "", "match notes referencing ANY of these entities")
	searchCmd.Flags().StringVar(&searchType, "type", "", "filter by note type")
	searchCmd.Flags().StringVar(&searchText, "text", "", "full-text search in title and body")
	searchCmd.Flags().StringVar(&searchSince, "since", "", "only notes modified after this ISO8601 date")
	searchCmd.Flags().BoolVar(&searchExpired, "expired", false, "include expired notes")
	searchCmd.Flags().IntVar(&searchLimit, "limit", 20, "max results")

	rootCmd.AddCommand(searchCmd)
}

func searchIndex(idx *index.Index, typeFilter string, entities []string, tags string, text string, includeExpired bool) []index.Entry {
	tagList := splitTrim(tags)
	var results []index.Entry

	for _, n := range idx.Notes {
		if typeFilter != "" && n.Type != typeFilter {
			continue
		}
		if len(tagList) > 0 && !hasAllTags(n.Tags, tagList) {
			continue
		}
		if len(entities) > 0 && !hasAnyEntity(n.Entities, entities) {
			continue
		}
		if text != "" && !containsText(n, text) {
			continue
		}
		results = append(results, n)
	}
	return results
}

func hasAllTags(noteTags, required []string) bool {
	tagSet := make(map[string]bool)
	for _, t := range noteTags {
		tagSet[t] = true
	}
	for _, r := range required {
		if !tagSet[r] {
			return false
		}
	}
	return true
}

func hasAnyEntity(noteEntities, query []string) bool {
	for _, q := range query {
		for _, e := range noteEntities {
			if strings.EqualFold(e, q) {
				return true
			}
		}
	}
	return false
}

func containsText(n index.Entry, text string) bool {
	lower := strings.ToLower(text)
	return strings.Contains(strings.ToLower(n.Title), lower) ||
		strings.Contains(strings.ToLower(n.Summary), lower)
}

func runSearch(cmd *cobra.Command, args []string) error {
	cfg, err := config.Load(cfgFile)
	if err != nil {
		return err
	}

	idx, err := index.Read(cfg.IndexFile)
	if err != nil {
		return fmt.Errorf("read index: %w", err)
	}

	entities := splitTrim(searchEntities)
	results := searchIndex(idx, searchType, entities, searchTags, searchText, searchExpired)

	if len(results) > searchLimit {
		results = results[:searchLimit]
	}

	if jsonOut {
		enc := json.NewEncoder(os.Stdout)
		enc.SetIndent("", "  ")
		enc.Encode(results)
	} else {
		for _, r := range results {
			fmt.Println(r.File)
		}
		if len(results) == 0 {
			fmt.Println("No matches found.")
		}
	}
	return nil
}
