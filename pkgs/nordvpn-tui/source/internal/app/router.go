package app

import (
	"strings"

	"github.com/charmbracelet/lipgloss"

	"github.com/simonwa01/nordvpn-tui/internal/state"
	"github.com/simonwa01/nordvpn-tui/internal/theme"
	"github.com/simonwa01/nordvpn-tui/internal/views/common"
	"github.com/simonwa01/nordvpn-tui/internal/views/countries"
	"github.com/simonwa01/nordvpn-tui/internal/views/help"
	"github.com/simonwa01/nordvpn-tui/internal/views/home"
	"github.com/simonwa01/nordvpn-tui/internal/views/servers"
	settingsview "github.com/simonwa01/nordvpn-tui/internal/views/settings"
)

// compose assembles the full screen: hero (2 rows), middle view, hint bar (1 row).
// All views share this frame so the chrome is consistent by construction.
func compose(m *Model, styles theme.Styles) string {
	w, h := m.S.Width, m.S.Height
	if w < 60 || h < 16 {
		return renderTooSmall(w, h, styles)
	}

	if m.S.FatalErr != nil {
		return renderFatal(m, w, h, styles)
	}

	// Frame: hero + 1 blank + view + 1 blank + hint bar = hero(1) + 1 + view + 1 + hint(1) = 4 extra rows.
	heroLine := common.Hero(m.S.Status, "", styles, w)
	hintBar := renderHints(m, styles, w)

	bodyH := h - 4 // 1 hero + 1 blank + 1 blank + 1 hint
	if bodyH < 4 {
		bodyH = 4
	}

	body := renderBody(m, styles, w, bodyH)
	if m.S.ShowHelp {
		body = help.Render(w, bodyH, styles)
	} else if m.S.ShowLog {
		body = help.RenderLog(m.S.Log.Snapshot(), w, bodyH, styles)
	}

	return heroLine + "\n\n" + body + "\n\n" + hintBar
}

func renderBody(m *Model, styles theme.Styles, w, h int) string {
	switch m.S.View {
	case state.ViewHome:
		return home.Render(home.Props{
			Status:    m.S.Status,
			Account:   m.S.Account,
			Pending:   m.S.Pending.Action,
			UsingFake: m.S.UsingFake,
			Width:     w,
			Height:    h,
			Now:       m.S.Now,
		}, styles)
	case state.ViewCountries:
		return countries.Render(countries.Props{
			All:        m.S.Countries,
			Query:      m.S.Search[state.ViewCountries],
			SearchMode: m.S.SearchMode[state.ViewCountries],
			Cursor:     m.S.Cursor[state.ViewCountries],
			Loading:    m.S.Pending.List && len(m.S.Countries) == 0,
			Width:      w,
			Height:     h,
		}, styles)
	case state.ViewServers:
		cities := m.S.Cities[m.S.SelectedCountry]
		return servers.Render(servers.Props{
			Country:    m.S.SelectedCountry,
			Cities:     cities,
			Query:      m.S.Search[state.ViewServers],
			SearchMode: m.S.SearchMode[state.ViewServers],
			Cursor:     m.S.Cursor[state.ViewServers],
			Loading:    m.S.Pending.List && len(cities) == 0,
			Width:      w,
			Height:     h,
		}, styles)
	case state.ViewSettings:
		props := settingsview.Props{
			Items:   settingsview.Items(m.S.Settings),
			Cursor:  m.S.Cursor[state.ViewSettings],
			Pending: m.S.Pending.Action,
			Width:   w,
			Height:  h,
		}
		if m.S.SettingsConfirm != nil {
			props.Confirm = &settingsview.ConfirmPrompt{Message: m.S.SettingsConfirm.Message}
		}
		return settingsview.Render(props, styles)
	default:
		// Placeholder until later phases implement the view.
		return lipgloss.Place(w, h, lipgloss.Center, lipgloss.Center,
			styles.Muted.Render("("+viewName(m.S.View)+" coming next)"))
	}
}

func viewName(v state.ViewID) string {
	switch v {
	case state.ViewCountries:
		return "countries"
	case state.ViewServers:
		return "servers"
	case state.ViewSettings:
		return "settings"
	case state.ViewHelp:
		return "help"
	case state.ViewLog:
		return "log"
	default:
		return "home"
	}
}

func renderHints(m *Model, s theme.Styles, w int) string {
	hints := viewHints(m)
	toast := ""
	toastStyle := s.ToastInfo
	if m.S.Toast != nil {
		toast = m.S.Toast.Text
		if m.S.Toast.IsError {
			toastStyle = s.ToastErr
		}
	}
	return common.HintBar(hints, toast, toastStyle, s, w)
}

func viewHints(m *Model) []common.Hint {
	if m.S.ShowHelp {
		return []common.Hint{{Key: "esc", Label: "close help"}, {Key: "q", Label: "quit"}}
	}
	if m.S.ShowLog {
		return []common.Hint{{Key: "esc", Label: "close log"}, {Key: "q", Label: "quit"}}
	}
	// While search mode is active, show capture-mode hints.
	if m.S.SearchMode[m.S.View] {
		return []common.Hint{
			{Key: "type", Label: "filter"},
			{Key: "enter", Label: "apply"},
			{Key: "esc", Label: "cancel"},
		}
	}
	switch m.S.View {
	case state.ViewHome:
		return []common.Hint{
			{Key: "enter", Label: "primary"},
			{Key: "2", Label: "countries"},
			{Key: "3", Label: "settings"},
			{Key: "?", Label: "help"},
			{Key: "q", Label: "quit"},
		}
	case state.ViewCountries:
		return []common.Hint{
			{Key: "↑↓", Label: "move"},
			{Key: "/", Label: "search"},
			{Key: "enter", Label: "connect"},
			{Key: "esc", Label: "back"},
			{Key: "q", Label: "quit"},
		}
	case state.ViewServers:
		return []common.Hint{
			{Key: "↑↓", Label: "move"},
			{Key: "/", Label: "search"},
			{Key: "enter", Label: "connect"},
			{Key: "esc", Label: "back"},
			{Key: "q", Label: "quit"},
		}
	case state.ViewSettings:
		return []common.Hint{
			{Key: "↑↓", Label: "move"},
			{Key: "enter", Label: "toggle"},
			{Key: "esc", Label: "back"},
			{Key: "q", Label: "quit"},
		}
	default:
		return []common.Hint{
			{Key: "1", Label: "home"},
			{Key: "?", Label: "help"},
			{Key: "q", Label: "quit"},
		}
	}
}

func renderTooSmall(w, h int, s theme.Styles) string {
	msg := s.Muted.Render("terminal too small — resize to at least 60×16")
	if w <= 0 || h <= 0 {
		return msg
	}
	return lipgloss.Place(w, h, lipgloss.Center, lipgloss.Center, msg)
}

func renderFatal(m *Model, w, h int, s theme.Styles) string {
	var title, detail, hint string
	switch {
	case errIsBinaryMissing(m.S.FatalErr):
		title = "nordvpn CLI not found"
		detail = "The nordvpn binary isn't on your PATH."
		hint = "Install NordVPN for Linux, then restart this app. (Or launch with --fake for a demo.)"
	case errIsDaemonDown(m.S.FatalErr):
		title = "nordvpn daemon is not running"
		detail = "The TUI needs the background service to be active."
		hint = "Start it with: systemctl --user start nordvpnd  (or systemctl start nordvpnd)"
	default:
		title = "Unexpected nordvpn error"
		detail = strings.TrimSpace(m.S.FatalErr.Error())
		hint = "Press q to quit."
	}
	return common.FatalBanner(title, detail, hint, s, w, h)
}
