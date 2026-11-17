// Package countries renders the browsable list of VPN locations.
// Search is an *inline* prompt, not a permanent bar — the design priority is
// "the list is the screen", with search appearing only when asked for.
package countries

import (
	"strconv"
	"strings"

	"github.com/simonwa01/nordvpn-tui/internal/theme"
	"github.com/simonwa01/nordvpn-tui/internal/views/common"
	"github.com/simonwa01/nordvpn-tui/internal/vpn"
)

type Props struct {
	All        []string
	Query      string
	SearchMode bool
	Cursor     int
	Loading    bool
	Width      int
	Height     int
}

// Filter returns the indexes (into All) that match query, case-insensitive.
func Filter(all []string, query string) []string {
	if query == "" {
		return all
	}
	q := strings.ToLower(query)
	out := make([]string, 0, len(all))
	for _, c := range all {
		if strings.Contains(strings.ToLower(vpn.Display(c)), q) {
			out = append(out, c)
		}
	}
	return out
}

// Render paints the main body (below the hero, above the hint bar).
func Render(p Props, s theme.Styles) string {
	var header string
	if p.SearchMode || p.Query != "" {
		header = renderSearchLine(p, s)
	} else {
		header = s.Muted.Render("  Choose a country — press ") +
			s.HintKey.Render("/") +
			s.Muted.Render(" to search, ") +
			s.HintKey.Render("→") +
			s.Muted.Render(" to open cities")
	}

	filtered := Filter(p.All, p.Query)

	var body string
	switch {
	case p.Loading && len(p.All) == 0:
		body = common.Skeleton(6, s)
	case len(filtered) == 0 && p.Query != "":
		body = common.Empty("No countries match \""+p.Query+"\"", "press esc to clear", s, p.Width, p.Height-4)
	case len(filtered) == 0:
		body = common.Empty("No countries available", "", s, p.Width, p.Height-4)
	default:
		body = renderList(filtered, p.Cursor, p.Height-3, s)
	}

	return header + "\n\n" + body
}

func renderSearchLine(p Props, s theme.Styles) string {
	prompt := s.SearchPrompt.Render("  / ")
	text := p.Query
	cursorGlyph := ""
	if p.SearchMode {
		cursorGlyph = s.Accent.Render("▏")
	}
	return prompt + s.SearchText.Render(text) + cursorGlyph
}

// renderList draws a windowed slice centered around the cursor.
// Two-space left indent on every row + accent bar on focused row.
func renderList(items []string, cursor, maxRows int, s theme.Styles) string {
	if maxRows < 3 {
		maxRows = 3
	}
	start := 0
	if cursor >= maxRows {
		start = cursor - maxRows + 1
	}
	end := start + maxRows
	if end > len(items) {
		end = len(items)
	}

	rows := make([]string, 0, end-start)
	for i := start; i < end; i++ {
		name := vpn.Display(items[i])
		rows = append(rows, common.FocusRow(name, i == cursor, s))
	}

	// Scroll indicator when truncated.
	if start > 0 || end < len(items) {
		rows = append(rows, "  "+s.Faint.Render(scrollHint(start, end, len(items))))
	}
	return strings.Join(rows, "\n")
}

func scrollHint(start, end, total int) string {
	return "· " + strconv.Itoa(start+1) + "–" + strconv.Itoa(end) + " of " + strconv.Itoa(total) + " ·"
}
