// Package common holds chrome elements that appear on every screen:
// the status hero, the hint bar, and transient toast/overlay primitives.
package common

import (
	"fmt"
	"strings"
	"time"

	"github.com/charmbracelet/lipgloss"

	"github.com/simonwa01/nordvpn-tui/internal/theme"
	"github.com/simonwa01/nordvpn-tui/internal/vpn"
)

// Hero renders the one-line connection status that anchors every screen.
//
// Layout:
//
//	●  Connected · United States — New York · #us4521        NordLynx · 198.51.100.42 · 00:12:37
//	└── glyph      └── primary cluster                          └── meta cluster (dim, right-aligned)
//
// Truncation order (as width shrinks): drop meta tech → ip → uptime → hostname → city.
// Returns a pre-composed string of the full width so the caller can simply print it.
func Hero(st vpn.Status, subtitle string, s theme.Styles, width int) string {
	glyph, glyphStyle := heroGlyph(st.State, s)
	state := s.HeroState.Foreground(glyphStyle.GetForeground()).Render(st.State.String())

	primary := heroPrimary(st, subtitle, s)
	meta := heroMeta(st, s, width)

	left := lipgloss.JoinHorizontal(lipgloss.Top,
		"  ",
		glyphStyle.Render(glyph),
		"  ",
		state,
		primary,
	)

	// Right-align meta by measuring and padding.
	leftW := lipgloss.Width(left)
	metaW := lipgloss.Width(meta)
	gap := width - leftW - metaW
	if gap < 2 {
		// Not enough room; drop meta entirely.
		return left
	}
	return left + strings.Repeat(" ", gap) + meta
}

func heroGlyph(state vpn.ConnState, s theme.Styles) (string, lipgloss.Style) {
	switch state {
	case vpn.StateConnected:
		return "●", s.HeroDot.Foreground(s.P.OK)
	case vpn.StateConnecting, vpn.StateDisconnecting:
		return "●", s.HeroDot.Foreground(s.P.Warn)
	case vpn.StateDisconnected:
		return "○", s.HeroDot.Foreground(s.P.Faint)
	default:
		return "○", s.HeroDot.Foreground(s.P.Muted)
	}
}

func heroPrimary(st vpn.Status, subtitle string, s theme.Styles) string {
	sep := s.HeroSep.Render("  ·  ")
	switch st.State {
	case vpn.StateConnected:
		loc := st.Country
		if st.City != "" {
			loc = st.Country + " — " + st.City
		}
		if loc == "" {
			loc = "Active connection"
		}
		return sep + s.HeroPrimary.Render(loc)
	case vpn.StateConnecting:
		return sep + s.Muted.Render("establishing tunnel…")
	case vpn.StateDisconnecting:
		return sep + s.Muted.Render("tearing down…")
	case vpn.StateDisconnected:
		if subtitle != "" {
			return sep + s.Muted.Render(subtitle)
		}
		return sep + s.Muted.Render("no active connection")
	default:
		return sep + s.Muted.Render("status unknown")
	}
}

// heroMeta returns the dim, right-aligned technical cluster.
// Truncates gracefully as width shrinks.
func heroMeta(st vpn.Status, s theme.Styles, width int) string {
	if st.State != vpn.StateConnected {
		return ""
	}
	parts := []string{}
	if st.Technology != "" {
		parts = append(parts, prettyTech(st.Technology))
	}
	if st.IP != "" {
		parts = append(parts, st.IP)
	}
	if st.Uptime > 0 {
		parts = append(parts, formatUptime(st.Uptime))
	}

	// Budget meta to at most ~45% of width — keeps the primary cluster prominent.
	budget := width / 2
	sep := "  ·  "
	for {
		joined := strings.Join(parts, sep)
		if lipgloss.Width(joined) <= budget || len(parts) == 0 {
			return s.HeroMeta.Render(joined)
		}
		parts = parts[:len(parts)-1]
	}
}

func prettyTech(t string) string {
	switch strings.ToUpper(t) {
	case "NORDLYNX":
		return "NordLynx"
	case "OPENVPN":
		return "OpenVPN"
	}
	return t
}

func formatUptime(d time.Duration) string {
	d = d.Round(time.Second)
	h := int(d / time.Hour)
	m := int(d % time.Hour / time.Minute)
	sec := int(d % time.Minute / time.Second)
	return fmt.Sprintf("%02d:%02d:%02d", h, m, sec)
}
