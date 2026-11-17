package common

import (
	"strings"

	"github.com/charmbracelet/lipgloss"

	"github.com/simonwa01/nordvpn-tui/internal/theme"
)

// Hint is a single keymap hint: a key cap and its label.
type Hint struct {
	Key   string
	Label string
}

// HintBar renders keymap hints in the fixed bottom-right position with a toast slot on the left.
// Keys are bold-normal, labels are muted, separators are faint bullets. This is the only
// place the app displays keybindings outside the help overlay — by design.
func HintBar(hints []Hint, toast string, toastStyle lipgloss.Style, s theme.Styles, width int) string {
	if width <= 0 {
		return ""
	}
	right := renderHints(hints, s)
	left := ""
	if toast != "" {
		left = toastStyle.Render("› " + toast)
	}

	rightW := lipgloss.Width(right)
	leftW := lipgloss.Width(left)
	gap := width - leftW - rightW - 4 // 2-col padding each side
	if gap < 1 {
		// Not enough room — drop the toast, keep the hints.
		gap = width - rightW - 4
		if gap < 0 {
			gap = 0
		}
		return "  " + strings.Repeat(" ", gap) + right + "  "
	}
	return "  " + left + strings.Repeat(" ", gap) + right + "  "
}

func renderHints(hints []Hint, s theme.Styles) string {
	if len(hints) == 0 {
		return ""
	}
	parts := make([]string, 0, len(hints)*2-1)
	for i, h := range hints {
		parts = append(parts, s.HintKey.Render(h.Key)+" "+s.Hint.Render(h.Label))
		if i < len(hints)-1 {
			parts = append(parts, s.HintSep.Render(" · "))
		}
	}
	return strings.Join(parts, "")
}
