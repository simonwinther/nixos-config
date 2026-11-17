package app

import (
	tea "github.com/charmbracelet/bubbletea"

	"github.com/simonwa01/nordvpn-tui/internal/state"
	"github.com/simonwa01/nordvpn-tui/internal/views/countries"
	"github.com/simonwa01/nordvpn-tui/internal/views/servers"
	settingsview "github.com/simonwa01/nordvpn-tui/internal/views/settings"
	"github.com/simonwa01/nordvpn-tui/internal/vpn"
)

// dispatchKey is the single entry point for keyboard events. It applies
// the shortest applicable handler in order: search-mode capture, then
// per-view handler, then global fallbacks.
func (m *Model) dispatchKey(msg tea.KeyMsg) (tea.Model, tea.Cmd) {
	// Overlays take priority and only let esc / ? / L / q through.
	if m.S.ShowHelp || m.S.ShowLog {
		return m.handleOverlayKey(msg)
	}

	if m.S.SearchMode[m.S.View] {
		return m.handleSearchKey(msg)
	}

	if cmd := m.handleViewKey(msg); cmd != nil || m.consumedByView(msg) {
		return m, cmd
	}
	return m.handleGlobalKey(msg)
}

func (m *Model) handleOverlayKey(msg tea.KeyMsg) (tea.Model, tea.Cmd) {
	switch msg.String() {
	case "esc", "?":
		m.S.ShowHelp = false
		if msg.String() == "esc" {
			m.S.ShowLog = false
		}
	case "L":
		m.S.ShowLog = false
	case "q", "ctrl+c":
		return m, tea.Quit
	}
	return m, nil
}

func (m *Model) consumedByView(msg tea.KeyMsg) bool {
	k := msg.String()
	switch m.S.View {
	case state.ViewCountries:
		switch k {
		case "up", "k", "down", "j", "/", "enter", "esc", "right", "l":
			return true
		}
	case state.ViewServers:
		switch k {
		case "up", "k", "down", "j", "/", "enter", "esc", "left", "h":
			return true
		}
	case state.ViewSettings:
		switch k {
		case "up", "k", "down", "j", "enter", " ", "esc", "y", "n":
			return true
		}
	}
	return false
}

// handleSearchKey captures all keys while search mode is active on the current view.
func (m *Model) handleSearchKey(msg tea.KeyMsg) (tea.Model, tea.Cmd) {
	v := m.S.View
	q := m.S.Search[v]
	switch msg.Type {
	case tea.KeyEsc:
		m.S.SearchMode[v] = false
		m.S.Search[v] = ""
		m.S.Cursor[v] = 0
		return m, nil
	case tea.KeyEnter:
		m.S.SearchMode[v] = false
		return m, nil
	case tea.KeyBackspace:
		if len(q) > 0 {
			m.S.Search[v] = q[:len(q)-1]
			m.S.Cursor[v] = 0
		}
		return m, nil
	case tea.KeyRunes, tea.KeySpace:
		m.S.Search[v] = q + msg.String()
		m.S.Cursor[v] = 0
		return m, nil
	case tea.KeyCtrlC:
		return m, tea.Quit
	}
	return m, nil
}

func (m *Model) handleViewKey(msg tea.KeyMsg) tea.Cmd {
	k := msg.String()
	switch m.S.View {
	case state.ViewHome:
		return m.handleHomeKey(k)
	case state.ViewCountries:
		return m.handleCountriesKey(k)
	case state.ViewServers:
		return m.handleServersKey(k)
	case state.ViewSettings:
		return m.handleSettingsKey(k)
	}
	return nil
}

func (m *Model) handleHomeKey(k string) tea.Cmd {
	switch k {
	case "c":
		if !m.S.Pending.Action {
			m.S.Pending.Action = true
			return tea.Batch(runConnect(m.Client), spinnerTick())
		}
	case "d":
		if !m.S.Pending.Action {
			m.S.Pending.Action = true
			return tea.Batch(runDisconnect(m.Client), spinnerTick())
		}
	case "enter":
		if m.S.Pending.Action {
			return nil
		}
		m.S.Pending.Action = true
		if m.S.Status.State == vpn.StateConnected {
			return tea.Batch(runDisconnect(m.Client), spinnerTick())
		}
		return tea.Batch(runConnect(m.Client), spinnerTick())
	}
	return nil
}

func (m *Model) handleCountriesKey(k string) tea.Cmd {
	filtered := countries.Filter(m.S.Countries, m.S.Search[state.ViewCountries])
	cursor := m.S.Cursor[state.ViewCountries]

	switch k {
	case "up", "k":
		if cursor > 0 {
			m.S.Cursor[state.ViewCountries] = cursor - 1
		}
	case "down", "j":
		if cursor < len(filtered)-1 {
			m.S.Cursor[state.ViewCountries] = cursor + 1
		}
	case "/":
		m.S.SearchMode[state.ViewCountries] = true
	case "esc":
		if m.S.Search[state.ViewCountries] != "" {
			m.S.Search[state.ViewCountries] = ""
			m.S.Cursor[state.ViewCountries] = 0
		} else {
			m.S.View = state.ViewHome
		}
	case "enter":
		if cursor < len(filtered) && !m.S.Pending.Action {
			country := filtered[cursor]
			m.S.Pending.Action = true
			return tea.Batch(runConnectCountry(m.Client, country), spinnerTick())
		}
	case "right", "l":
		if cursor < len(filtered) {
			country := filtered[cursor]
			m.S.SelectedCountry = country
			m.S.View = state.ViewServers
			m.S.Cursor[state.ViewServers] = 0
			if _, ok := m.S.Cities[country]; !ok {
				m.S.Pending.List = true
				return fetchCities(m.Client, country)
			}
		}
	}
	return nil
}

func (m *Model) handleServersKey(k string) tea.Cmd {
	country := m.S.SelectedCountry
	cities := m.S.Cities[country]
	filtered := servers.Filter(cities, m.S.Search[state.ViewServers])
	cursor := m.S.Cursor[state.ViewServers]

	switch k {
	case "up", "k":
		if cursor > 0 {
			m.S.Cursor[state.ViewServers] = cursor - 1
		}
	case "down", "j":
		if cursor < len(filtered)-1 {
			m.S.Cursor[state.ViewServers] = cursor + 1
		}
	case "/":
		m.S.SearchMode[state.ViewServers] = true
	case "esc", "left", "h":
		if m.S.Search[state.ViewServers] != "" {
			m.S.Search[state.ViewServers] = ""
			m.S.Cursor[state.ViewServers] = 0
		} else {
			m.S.View = state.ViewCountries
		}
	case "enter":
		if m.S.Pending.Action {
			return nil
		}
		m.S.Pending.Action = true
		if cursor < len(filtered) {
			city := filtered[cursor]
			return tea.Batch(runConnectCity(m.Client, country, city), spinnerTick())
		}
		// Empty list — enter connects to country only.
		return tea.Batch(runConnectCountry(m.Client, country), spinnerTick())
	}
	return nil
}

func (m *Model) handleSettingsKey(k string) tea.Cmd {
	// If a confirm prompt is up, capture everything until answered.
	if m.S.SettingsConfirm != nil {
		return m.handleSettingsConfirm(k)
	}

	items := settingsview.Items(m.S.Settings)
	cursor := m.S.Cursor[state.ViewSettings]
	if cursor >= len(items) {
		cursor = 0
	}

	switch k {
	case "up", "k":
		if cursor > 0 {
			m.S.Cursor[state.ViewSettings] = cursor - 1
		}
	case "down", "j":
		if cursor < len(items)-1 {
			m.S.Cursor[state.ViewSettings] = cursor + 1
		}
	case "esc":
		m.S.View = state.ViewHome
	case "enter", " ":
		if m.S.Pending.Action {
			return nil
		}
		return m.applySettingToggle(items[cursor])
	}
	return nil
}

func (m *Model) applySettingToggle(it settingsview.Item) tea.Cmd {
	switch it.Kind {
	case settingsview.ItemBool:
		newVal := "on"
		if it.BoolVal {
			newVal = "off"
		}
		// Kill Switch is the one change we confirm: flipping it while
		// connected can cut all traffic, and flipping it off defeats a
		// safety feature the user opted into.
		if it.CLIKey == "killswitch" {
			msg := "Turn Kill Switch ON? It blocks traffic if the tunnel drops."
			if it.BoolVal {
				msg = "Turn Kill Switch OFF? Your traffic will continue if the tunnel drops."
			}
			m.S.SettingsConfirm = &state.SettingsConfirm{
				Message: msg,
				Key:     it.CLIKey,
				Value:   newVal,
			}
			return nil
		}
		m.S.Pending.Action = true
		return runSet(m.Client, it.CLIKey, newVal)
	case settingsview.ItemEnum:
		next := nextEnum(it.Enum, it.EnumVal)
		m.S.Pending.Action = true
		return runSet(m.Client, it.CLIKey, next)
	}
	return nil
}

func (m *Model) handleSettingsConfirm(k string) tea.Cmd {
	c := m.S.SettingsConfirm
	switch k {
	case "y", "enter":
		m.S.SettingsConfirm = nil
		m.S.Pending.Action = true
		return runSet(m.Client, c.Key, c.Value)
	case "n", "esc":
		m.S.SettingsConfirm = nil
	}
	return nil
}

func nextEnum(opts []string, current string) string {
	for i, v := range opts {
		if v == current {
			return opts[(i+1)%len(opts)]
		}
	}
	if len(opts) > 0 {
		return opts[0]
	}
	return current
}

func (m *Model) handleGlobalKey(msg tea.KeyMsg) (tea.Model, tea.Cmd) {
	k := msg.String()
	switch k {
	case "ctrl+c", "q":
		return m, tea.Quit
	case "1":
		m.S.View = state.ViewHome
	case "2":
		m.S.View = state.ViewCountries
	case "3":
		m.S.View = state.ViewSettings
	case "c":
		if !m.S.Pending.Action {
			m.S.Pending.Action = true
			return m, tea.Batch(runConnect(m.Client), spinnerTick())
		}
	case "d":
		if !m.S.Pending.Action {
			m.S.Pending.Action = true
			return m, tea.Batch(runDisconnect(m.Client), spinnerTick())
		}
	case "?":
		m.S.ShowHelp = true
	case "L":
		m.S.ShowLog = true
	}
	return m, nil
}
