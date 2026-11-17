package main

import (
	"flag"
	"fmt"
	"os"

	tea "github.com/charmbracelet/bubbletea"

	"github.com/simonwa01/nordvpn-tui/internal/app"
	"github.com/simonwa01/nordvpn-tui/internal/vpn"
)

var (
	fakeFlag    = flag.Bool("fake", false, "use a scripted in-memory client instead of shelling out to nordvpn")
	versionFlag = flag.Bool("version", false, "print version and exit")
)

// Injected at build time via -ldflags.
var (
	version = "dev"
	commit  = "none"
	date    = "unknown"
)

func main() {
	flag.Parse()
	if *versionFlag {
		fmt.Printf("nordvpn-tui %s (%s, built %s)\n", version, commit, date)
		return
	}

	var client vpn.Client
	if *fakeFlag {
		client = vpn.NewFakeClient()
	} else {
		client = vpn.NewCLIClient()
	}

	m := app.New(client, *fakeFlag)
	prog := tea.NewProgram(m, tea.WithAltScreen())
	if _, err := prog.Run(); err != nil {
		fmt.Fprintln(os.Stderr, "nordvpn-tui:", err)
		os.Exit(1)
	}
}
