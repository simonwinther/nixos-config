package app

import (
	"errors"
	"time"

	tea "github.com/charmbracelet/bubbletea"

	"github.com/simonwa01/nordvpn-tui/internal/state"
	"github.com/simonwa01/nordvpn-tui/internal/theme"
	"github.com/simonwa01/nordvpn-tui/internal/vpn"
)

// Model is the Bubble Tea root model. Views are plain functions invoked by View().
type Model struct {
	Client vpn.Client
	Keys   KeyMap
	Styles theme.Styles
	S      *state.AppState
}

func New(client vpn.Client, usingFake bool) *Model {
	return &Model{
		Client: client,
		Keys:   DefaultKeys(),
		Styles: theme.Build(theme.Current()),
		S:      state.New(usingFake),
	}
}

func errIsBinaryMissing(err error) bool { return errors.Is(err, vpn.ErrBinaryMissing) }
func errIsDaemonDown(err error) bool    { return errors.Is(err, vpn.ErrDaemonDown) }

func (m *Model) Init() tea.Cmd {
	m.S.Pending.Status = true
	m.S.Pending.Settings = true
	m.S.Pending.List = true
	return tea.Batch(
		fetchStatus(m.Client),
		fetchSettings(m.Client),
		fetchAccount(m.Client),
		fetchCountries(m.Client),
		tick(),
	)
}

func (m *Model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {

	case tea.WindowSizeMsg:
		m.S.Width = msg.Width
		m.S.Height = msg.Height
		return m, nil

	case tea.KeyMsg:
		return m.dispatchKey(msg)

	case TickMsg:
		m.S.Now = time.Time(msg)
		// Only poll when nothing is in flight.
		if !m.S.Pending.Any() && m.S.FatalErr == nil {
			m.S.Pending.Status = true
			return m, tea.Batch(fetchStatus(m.Client), tick())
		}
		return m, tick()

	case SpinnerTickMsg:
		m.S.Now = time.Time(msg)
		if m.S.Pending.Action {
			return m, spinnerTick()
		}
		return m, nil

	case StatusMsg:
		m.S.Pending.Status = false
		if msg.Err != nil {
			m.handleErr(msg.Err, "status")
			return m, nil
		}
		m.S.Status = msg.Status
		m.S.FatalErr = nil
		return m, nil

	case SettingsMsg:
		m.S.Pending.Settings = false
		if msg.Err != nil {
			m.handleErr(msg.Err, "settings")
			return m, nil
		}
		m.S.Settings = msg.Settings
		return m, nil

	case AccountMsg:
		if msg.Err != nil {
			if errors.Is(msg.Err, vpn.ErrNotLoggedIn) {
				m.S.Account = vpn.Account{LoggedIn: false}
				return m, nil
			}
			m.handleErr(msg.Err, "account")
			return m, nil
		}
		m.S.Account = msg.Account
		return m, nil

	case CountriesMsg:
		m.S.Pending.List = false
		if msg.Err != nil {
			m.handleErr(msg.Err, "countries")
			return m, nil
		}
		m.S.Countries = msg.Countries
		return m, nil

	case CitiesMsg:
		m.S.Pending.List = false
		if msg.Err != nil {
			m.handleErr(msg.Err, "cities")
			return m, nil
		}
		m.S.Cities[msg.Country] = msg.Cities
		return m, nil

	case ActionMsg:
		m.S.Pending.Action = false
		if msg.Err != nil {
			m.S.LastErr = msg.Err
			m.S.Log.Error(msg.Summary + ": " + msg.Err.Error())
			m.S.SetToast(msg.Summary, true)
		} else {
			m.S.Log.Info(msg.Summary)
			m.S.SetToast(msg.Summary, false)
		}
		// Refresh status immediately after any action.
		return m, tea.Batch(fetchStatus(m.Client), fetchSettings(m.Client), toastExpire())

	case ToastExpireMsg:
		m.S.ClearToast()
		return m, nil
	}
	return m, nil
}

func (m *Model) handleErr(err error, ctx string) {
	switch {
	case errors.Is(err, vpn.ErrBinaryMissing), errors.Is(err, vpn.ErrDaemonDown):
		m.S.FatalErr = err
	case errors.Is(err, vpn.ErrNotLoggedIn):
		m.S.Account = vpn.Account{LoggedIn: false}
	}
	m.S.LastErr = err
	m.S.Log.Error(ctx + ": " + err.Error())
}

// View composes every screen through the router, which guarantees that the
// persistent chrome (hero + hint bar) is identical everywhere.
func (m *Model) View() string {
	return compose(m, m.Styles)
}
