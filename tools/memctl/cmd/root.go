package cmd

import (
	"fmt"
	"os"

	"github.com/spf13/cobra"
)

var (
	cfgFile string
	jsonOut bool
	dryRun  bool
	verbose bool
)

var rootCmd = &cobra.Command{
	Use:   "memctl",
	Short: "NanoClaw memory governance CLI",
	Long: `memctl manages atomic memory notes for NanoClaw agents.
It maintains a CLAUDE.md index, enforces note schema, detects drift,
and runs scripted pruning/archival.`,
}

func Execute() {
	if err := rootCmd.Execute(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

func init() {
	rootCmd.PersistentFlags().StringVar(&cfgFile, "config", "", "config file (default: ./memctl.yaml)")
	rootCmd.PersistentFlags().BoolVar(&jsonOut, "json", false, "output as JSON")
	rootCmd.PersistentFlags().BoolVar(&dryRun, "dry-run", false, "print what would happen without doing it")
	rootCmd.PersistentFlags().BoolVar(&verbose, "verbose", false, "include debug output")
}
