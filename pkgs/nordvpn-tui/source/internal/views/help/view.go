// Package help renders the keybinding overlay. Shown on top of the body
// (hero and hint bar stay visible) and dismissed with esc or ?.
package help

import (
	"strings"

	"github.com/charmbracelet/lipgloss"

	"github.com/simonwa01/nordvpn-tui/internal/theme"
)

type Entry struct{ Key, Label string }

type Section struct {
	Title   string
	Entries []Entry
}

func Sections() []Section {
	return []Section{
		{
			Title: "Global",
			Entries: []Entry{
				{"1 2 3", "switch view"},
				{"c", "quick connect"},
				{"d", "disconnect"},
				{"L", "open log"},
				{"?", "toggle this help"},
				{"q / ctrl-c", "quit"},
			},
		},
		{
			Title: "Lists (Countries / Servers)",
			Entries: []Entry{
				{"↑ ↓ / k j", "move"},
				{"/", "search — type to filter"},
				{"enter", "connect"},
				{"→ / l", "open cities (from Countries)"},
				{"esc / ← / h", "back / clear search"},
			},
		},
		{
			Title: "Settings",
			Entries: []Entry{
				{"enter / space", "toggle / cycle"},
				{"y / n", "confirm prompt"},
			},
		},
	}
}

// Render returns the overlay block to place inside the available body area.
func Render(width, height int, s theme.Styles) string {
	// Build each section with a muted title and tight key column.
	blocks := make([]string, 0, len(Sections())*2)
	for i, sec := range Sections() {
		if i > 0 {
			blocks = append(blocks, "")
		}
		blocks = append(blocks, s.OverlayTitle.Render(sec.Title))
		for _, e := range sec.Entries {
			blocks = append(blocks, "  "+s.HintKey.Render(padRight(e.Key, 14))+" "+s.Muted.Render(e.Label))
		}
	}
	content := strings.Join(blocks, "\n")

	panel := s.Overlay.Render(content)
	return lipgloss.Place(width, height, lipgloss.Center, lipgloss.Center, panel)
}

func padRight(s string, w int) string {
	cw := lipgloss.Width(s)
	if cw >= w {
		return s
	}
	return s + strings.Repeat(" ", w-cw)
}
