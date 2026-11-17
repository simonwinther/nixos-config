package help

import (
	"strings"

	"github.com/charmbracelet/lipgloss"

	"github.com/simonwa01/nordvpn-tui/internal/log"
	"github.com/simonwa01/nordvpn-tui/internal/theme"
)

// RenderLog draws the activity log as an overlay panel over the body area.
// Newest entries are at the bottom; we show the last N that fit.
func RenderLog(entries []log.Entry, width, height int, s theme.Styles) string {
	title := s.OverlayTitle.Render("Activity log") + s.Muted.Render("   esc to close")

	if len(entries) == 0 {
		empty := s.Muted.Render("no events yet — actions you take will show up here")
		panel := s.Overlay.Render(title + "\n\n" + empty)
		return lipgloss.Place(width, height, lipgloss.Center, lipgloss.Center, panel)
	}

	// Tail so newest fits in available height; overlay has 2 border + 2 padding rows.
	maxRows := height - 8
	if maxRows < 3 {
		maxRows = 3
	}
	start := 0
	if len(entries) > maxRows {
		start = len(entries) - maxRows
	}

	rows := make([]string, 0, len(entries)-start)
	for _, e := range entries[start:] {
		ts := s.Faint.Render(e.Time.Format("15:04:05"))
		lvl := levelGlyph(e.Level, s)
		rows = append(rows, ts+"  "+lvl+"  "+s.Body.Render(e.Message))
	}

	panel := s.Overlay.Render(title + "\n\n" + strings.Join(rows, "\n"))
	return lipgloss.Place(width, height, lipgloss.Center, lipgloss.Center, panel)
}

func levelGlyph(l log.Level, s theme.Styles) string {
	switch l {
	case log.LevelError:
		return s.Err.Render("●")
	case log.LevelWarn:
		return s.Warn.Render("●")
	default:
		return s.OK.Render("●")
	}
}
