// Package settings renders the toggleable core options. Scope is intentionally
// narrow: five items a user routinely flips. Advanced knobs live in the CLI.
package settings

import (
	"strings"

	"github.com/charmbracelet/lipgloss"

	"github.com/simonwa01/nordvpn-tui/internal/theme"
	"github.com/simonwa01/nordvpn-tui/internal/views/common"
	"github.com/simonwa01/nordvpn-tui/internal/vpn"
)

type ItemKind int

const (
	ItemBool ItemKind = iota
	ItemEnum
)

type Item struct {
	Label   string
	CLIKey  string // passed to `nordvpn set`
	Kind    ItemKind
	BoolVal bool
	EnumVal string
	Enum    []string
}

// Items returns the MVP-curated list of settings in the order shown.
func Items(s vpn.Settings) []Item {
	return []Item{
		{Label: "Kill Switch", CLIKey: "killswitch", Kind: ItemBool, BoolVal: s.KillSwitch},
		{Label: "Auto-connect", CLIKey: "autoconnect", Kind: ItemBool, BoolVal: s.AutoConnect},
		{Label: "Threat Protection", CLIKey: "threatprotectionlite", Kind: ItemBool, BoolVal: s.ThreatProtection},
		{Label: "Notify", CLIKey: "notify", Kind: ItemBool, BoolVal: s.Notify},
		{Label: "Technology", CLIKey: "technology", Kind: ItemEnum, EnumVal: s.Technology, Enum: []string{"NORDLYNX", "OPENVPN"}},
	}
}

type Props struct {
	Items   []Item
	Cursor  int
	Pending bool
	Confirm *ConfirmPrompt // non-nil when an inline confirm dialog is showing
	Width   int
	Height  int
}

// ConfirmPrompt is an inline y/n question shown before applying a risky change.
// MVP only uses it for Kill Switch toggles — a misfired Kill Switch can cut all
// traffic on a user who didn't mean to enable it.
type ConfirmPrompt struct {
	Message string
}

func Render(p Props, s theme.Styles) string {
	title := s.Muted.Render("  Core settings") + s.HintSep.Render("  ·  ") +
		s.Faint.Render("toggle with ") + s.HintKey.Render("enter")

	rows := make([]string, 0, len(p.Items))
	for i, it := range p.Items {
		rows = append(rows, renderRow(it, i == p.Cursor, s))
	}
	list := strings.Join(rows, "\n")

	body := title + "\n\n" + list

	if p.Confirm != nil {
		prompt := s.Warn.Bold(true).Render("● ") + s.Body.Render(p.Confirm.Message) +
			"   " + s.HintKey.Render("[y]") + s.Muted.Render(" yes  ") +
			s.HintKey.Render("[n]") + s.Muted.Render(" cancel")
		confirmBlock := lipgloss.NewStyle().
			Border(lipgloss.RoundedBorder()).
			BorderForeground(s.P.Warn).
			Padding(0, 2).
			MarginLeft(2).
			Render(prompt)
		body += "\n\n" + confirmBlock
	}

	return body
}

// renderRow lays out a label + right-aligned value. Key column is fixed width
// so values line up in a clean column instead of following the label.
func renderRow(it Item, focused bool, s theme.Styles) string {
	const labelCol = 24
	label := it.Label
	if len(label) < labelCol {
		label = label + strings.Repeat(" ", labelCol-len(label))
	}

	var val string
	switch it.Kind {
	case ItemBool:
		if it.BoolVal {
			val = s.SettingsValOn.Render("● on")
		} else {
			val = s.SettingsValOff.Render("○ off")
		}
	case ItemEnum:
		val = s.SettingsEnumVal.Render(prettyTech(it.EnumVal))
	}

	content := s.SettingsKey.Render(label) + val
	return common.FocusRow(content, focused, s)
}

func prettyTech(t string) string {
	switch strings.ToUpper(t) {
	case "NORDLYNX":
		return "NordLynx"
	case "OPENVPN":
		return "OpenVPN"
	}
	if t == "" {
		return "—"
	}
	return t
}
