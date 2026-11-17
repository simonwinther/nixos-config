// Package servers renders the cities available for a chosen country.
// MVP-scope decision: NordVPN CLI doesn't expose a per-server list, so
// "servers" here == cities. Picking a city delegates to `nordvpn connect
// <country> <city>`, which is all the CLI meaningfully gives us.
package servers

import (
	"strconv"
	"strings"

	"github.com/simonwa01/nordvpn-tui/internal/theme"
	"github.com/simonwa01/nordvpn-tui/internal/views/common"
	"github.com/simonwa01/nordvpn-tui/internal/vpn"
)

type Props struct {
	Country    string
	Cities     []string
	Query      string
	SearchMode bool
	Cursor     int
	Loading    bool
	Width      int
	Height     int
}

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

func Render(p Props, s theme.Styles) string {
	bc := common.Breadcrumb([]string{"Countries", vpn.Display(p.Country)}, s)

	var header string
	if p.SearchMode || p.Query != "" {
		header = renderSearchLine(p, s)
	} else {
		header = s.Muted.Render("  Choose a city — or press ") +
			s.HintKey.Render("enter") +
			s.Muted.Render(" on the country header row to connect without a city.")
	}

	filtered := Filter(p.Cities, p.Query)

	var body string
	switch {
	case p.Loading && len(p.Cities) == 0:
		body = common.Skeleton(5, s)
	case len(filtered) == 0 && p.Query != "":
		body = common.Empty("No cities match \""+p.Query+"\"", "press esc to clear", s, p.Width, p.Height-5)
	case len(filtered) == 0:
		body = common.Empty(
			"No cities listed for "+vpn.Display(p.Country),
			"press enter to connect to "+vpn.Display(p.Country)+" directly",
			s, p.Width, p.Height-5)
	default:
		body = renderList(filtered, p.Cursor, p.Height-5, s)
	}

	return bc + "\n\n" + header + "\n\n" + body
}

func renderSearchLine(p Props, s theme.Styles) string {
	prompt := s.SearchPrompt.Render("  / ")
	cursor := ""
	if p.SearchMode {
		cursor = s.Accent.Render("▏")
	}
	return prompt + s.SearchText.Render(p.Query) + cursor
}

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
		rows = append(rows, common.FocusRow(vpn.Display(items[i]), i == cursor, s))
	}
	if start > 0 || end < len(items) {
		rows = append(rows, "  "+s.Faint.Render("· "+strconv.Itoa(start+1)+"–"+strconv.Itoa(end)+" of "+strconv.Itoa(len(items))+" ·"))
	}
	return strings.Join(rows, "\n")
}
