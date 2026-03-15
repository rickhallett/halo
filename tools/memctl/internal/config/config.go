package config

import (
	"fmt"
	"os"
	"path/filepath"

	"gopkg.in/yaml.v3"
)

type NoteConfig struct {
	Tags            []string `yaml:"tags"`
	ValidTypes      []string `yaml:"valid_types"`
	ValidConfidence []string `yaml:"valid_confidence"`
}

type IndexConfig struct {
	MaxSummaryChars int    `yaml:"max_summary_chars"`
	HashAlgorithm   string `yaml:"hash_algorithm"`
}

type PruneConfig struct {
	HalfLifeDays           int     `yaml:"half_life_days"`
	MinScore               float64 `yaml:"min_score"`
	MinBacklinksToExempt   int     `yaml:"min_backlinks_to_exempt"`
	DryRun                 bool    `yaml:"dry_run"`
	TombstoneRetentionDays int     `yaml:"tombstone_retention_days"`
}

type Config struct {
	MemoryDir   string      `yaml:"memory_dir"`
	IndexFile   string      `yaml:"index_file"`
	ArchiveDir  string      `yaml:"archive_dir"`
	BacklinkDir string      `yaml:"backlink_dir"`
	Note        NoteConfig  `yaml:"note"`
	Index       IndexConfig `yaml:"index"`
	Prune       PruneConfig `yaml:"prune"`
}

func Load(path string) (*Config, error) {
	if path == "" {
		if env := os.Getenv("MEMCTL_CONFIG"); env != "" {
			path = env
		} else {
			path = "memctl.yaml"
		}
	}

	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("read config %s: %w", path, err)
	}

	var cfg Config
	if err := yaml.Unmarshal(data, &cfg); err != nil {
		return nil, fmt.Errorf("parse config: %w", err)
	}

	if cfg.MemoryDir == "" {
		cfg.MemoryDir = "./memory"
	}
	if cfg.IndexFile == "" {
		cfg.IndexFile = "./CLAUDE.md"
	}
	if cfg.ArchiveDir == "" {
		cfg.ArchiveDir = filepath.Join(cfg.MemoryDir, "archive")
	}
	if cfg.BacklinkDir == "" {
		cfg.BacklinkDir = filepath.Join(cfg.MemoryDir, "backlinks")
	}
	if cfg.Index.MaxSummaryChars == 0 {
		cfg.Index.MaxSummaryChars = 120
	}
	if cfg.Index.HashAlgorithm == "" {
		cfg.Index.HashAlgorithm = "sha256"
	}
	if cfg.Prune.HalfLifeDays == 0 {
		cfg.Prune.HalfLifeDays = 30
	}
	if cfg.Prune.MinScore == 0 {
		cfg.Prune.MinScore = 0.15
	}
	if cfg.Prune.TombstoneRetentionDays == 0 {
		cfg.Prune.TombstoneRetentionDays = 90
	}

	return &cfg, nil
}
