// Package home renders the landing screen: the shortest path from "open the app"
// to "I know what's going on and can act". Deliberately sparse.
package home

import (
	"strings"
	"time"

	"github.com/charmbracelet/lipgloss"

	"github.com/simonwa01/nordvpn-tui/internal/theme"
	"github.com/simonwa01/nordvpn-tui/internal/views/common"
	"github.com/simonwa01/nordvpn-tui/internal/vpn"
)

type Props struct {
	Status    vpn.Status
	Account   vpn.Account
	Pending   bool
	UsingFake bool
	Width     int
	Height    int
	Now       time.Time
}

// Render draws the middle of the Home screen (between hero and hint bar).
// Centers a small column with state word + location + primary CTA.
func Render(p Props, s theme.Styles) string {
	column := buildColumn(p, s)
	// Vertical centering against available middle-area height.
	return lipgloss.Place(p.Width, p.Height, lipgloss.Center, lipgloss.Center, column)
}

func buildColumn(p Props, s theme.Styles) string {
	stateWord, stateStyle := stateWordFor(p.Status.State, s)
	spinner := ""
	if p.Pending {
		spinner = " " + common.Spinner(s, p.Now)
	}

	bigState := stateStyle.Render(stateWord) + spinner
	sub := subtitle(p, s)
	cta := ctaPill(p, s)

	secondary := s.Muted.Render("2 Countries") +
		s.HintSep.Render("  ·  ") +
		s.Muted.Render("3 Settings") +
		s.HintSep.Render("  ·  ") +
		s.Muted.Render("? Help")

	loginBanner := ""
	if !p.Account.LoggedIn {
		loginBanner = s.Warn.Render("You are not logged in.") + "\n" +
			s.Muted.Render("Run ") + s.Body.Render("nordvpn login") + s.Muted.Render(" from a shell to continue.")
	}

	fakeBanner := ""
	if p.UsingFake {
		fakeBanner = s.Faint.Render("demo mode — using scripted client")
	}

	rows := []string{bigState, "", sub, "", cta, "", secondary}
	if loginBanner != "" {
		rows = append([]string{loginBanner, ""}, rows...)
	}
	if fakeBanner != "" {
		rows = append(rows, "", fakeBanner)
	}
	return lipgloss.JoinVertical(lipgloss.Center, rows...)
}

func stateWordFor(st vpn.ConnState, s theme.Styles) (string, lipgloss.Style) {
	big := lipgloss.NewStyle().Bold(true)
	switch st {
	case vpn.StateConnected:
		return "Connected", big.Foreground(s.P.OK)
	case vpn.StateConnecting:
		return "Connecting", big.Foreground(s.P.Warn)
	case vpn.StateDisconnecting:
		return "Disconnecting", big.Foreground(s.P.Warn)
	case vpn.StateDisconnected:
		return "Disconnected", big.Foreground(s.P.Faint)
	default:
		return "Unknown", big.Foreground(s.P.Muted)
	}
}

func subtitle(p Props, s theme.Styles) string {
	switch p.Status.State {
	case vpn.StateConnected:
		loc := p.Status.Country
		if p.Status.City != "" {
			loc = p.Status.Country + " — " + p.Status.City
		}
		meta := []string{}
		if p.Status.Hostname != "" {
			meta = append(meta, p.Status.Hostname)
		}
		if p.Status.IP != "" {
			meta = append(meta, p.Status.IP)
		}
		return s.Body.Render(loc) + "\n" + s.Muted.Render(strings.Join(meta, "  ·  "))
	case vpn.StateConnecting:
		return s.Muted.Render("Establishing tunnel…")
	case vpn.StateDisconnecting:
		return s.Muted.Render("Tearing down…")
	case vpn.StateDisconnected:
		return s.Muted.Render("No active connection")
	default:
		return s.Muted.Render("Status unknown")
	}
}

// ctaPill is the primary action: a single, clearly marked keybind.
// Rendered as "[enter] Quick Connect" / "[enter] Disconnect" with the bracket
// in accent/error tone. No actual button chrome — chips look toylike in terminals.
func ctaPill(p Props, s theme.Styles) string {
	if p.Pending {
		return s.Muted.Render("working…")
	}
	switch p.Status.State {
	case vpn.StateConnected:
		return s.HintKey.Render("[enter]") + " " + s.CTADisconn.Render("Disconnect")
	default:
		return s.HintKey.Render("[enter]") + " " + s.CTAConnect.Render("Quick Connect")
	}
}
