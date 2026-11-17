package app

import (
	"testing"

	"github.com/simonwa01/nordvpn-tui/internal/state"
	"github.com/simonwa01/nordvpn-tui/internal/vpn"
)

func TestPreview_Settings(t *testing.T) {
	m := newTestModel(vpn.Status{State: vpn.StateDisconnected}, state.ViewSettings, 100, 28)
	m.S.Settings = vpn.Settings{
		Technology:       "NORDLYNX",
		KillSwitch:       false,
		AutoConnect:      true,
		ThreatProtection: false,
		Notify:           true,
	}
	m.S.Cursor[state.ViewSettings] = 0
	t.Logf("\n%s\n", m.View())
}

func TestPreview_SettingsConfirm(t *testing.T) {
	m := newTestModel(vpn.Status{State: vpn.StateConnected, Country: "United States", City: "New York"}, state.ViewSettings, 100, 28)
	m.S.Settings = vpn.Settings{Technology: "NORDLYNX", KillSwitch: false, Notify: true}
	m.S.Cursor[state.ViewSettings] = 0
	m.S.SettingsConfirm = &state.SettingsConfirm{
		Message: "Turn Kill Switch ON? It blocks traffic if the tunnel drops.",
		Key:     "killswitch",
		Value:   "on",
	}
	t.Logf("\n%s\n", m.View())
}
