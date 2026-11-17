package common

import (
	"strings"

	"github.com/charmbracelet/lipgloss"

	"github.com/simonwa01/nordvpn-tui/internal/theme"
)

// Breadcrumb renders `Countries › United States` with muted separators.
func Breadcrumb(parts []string, s theme.Styles) string {
	if len(parts) == 0 {
		return ""
	}
	out := make([]string, 0, len(parts)*2-1)
	for i, p := range parts {
		style := s.Breadcrumb
		if i == len(parts)-1 {
			style = s.Breadcrumb.Foreground(s.P.Accent).Bold(true)
		}
		out = append(out, style.Render(p))
		if i < len(parts)-1 {
			out = append(out, s.BreadcrumbSep.Render(" › "))
		}
	}
	return "  " + strings.Join(out, "")
}

// Empty renders a centered empty-state message. Short text + optional hint.
func Empty(title, hint string, s theme.Styles, width, height int) string {
	block := s.Title.Render(title)
	if hint != "" {
		block = lipgloss.JoinVertical(lipgloss.Center, block, "", s.Muted.Render(hint))
	}
	return lipgloss.Place(width, height, lipgloss.Center, lipgloss.Center, block)
}

// Skeleton renders N dim placeholder rows — used while a list is loading.
// No spinner here; one spinner per screen lives in the hero area when relevant.
func Skeleton(n int, s theme.Styles) string {
	rows := make([]string, n)
	for i := range rows {
		rows[i] = "  " + s.Skeleton.Render(strings.Repeat("─", 18+(i%3)*6))
	}
	return strings.Join(rows, "\n")
}

// FocusRow renders a list row with left accent bar + bold text.
// Non-focused rows get matching padding so selection doesn't shift horizontally.
func FocusRow(content string, focused bool, s theme.Styles) string {
	if focused {
		return s.FocusMarker.Render("▌ ") + s.FocusRow.Render(content)
	}
	return "  " + s.Body.Render(content)
}

// FatalBanner renders a full-screen blocking error for daemon-down /
// binary-missing situations — explicit, calm, instructive.
func FatalBanner(title, detail, hint string, s theme.Styles, width, height int) string {
	body := lipgloss.JoinVertical(lipgloss.Center,
		s.Err.Bold(true).Render("● "+title),
		"",
		s.Body.Render(detail),
		"",
		s.Muted.Render(hint),
	)
	return lipgloss.Place(width, height, lipgloss.Center, lipgloss.Center,
		s.Overlay.Render(body))
}
