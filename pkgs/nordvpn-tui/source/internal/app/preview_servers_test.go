package app

import (
	"testing"

	"github.com/simonwa01/nordvpn-tui/internal/state"
	"github.com/simonwa01/nordvpn-tui/internal/vpn"
)

func TestPreview_Servers(t *testing.T) {
	m := newTestModel(vpn.Status{State: vpn.StateDisconnected}, state.ViewServers, 100, 28)
	m.S.SelectedCountry = "United_States"
	m.S.Cities["United_States"] = []string{
		"Atlanta", "Boston", "Chicago", "Dallas", "Denver", "Los_Angeles",
		"Miami", "New_York", "Phoenix", "Portland", "Seattle",
	}
	m.S.Cursor[state.ViewServers] = 5
	t.Logf("\n%s\n", m.View())
}
