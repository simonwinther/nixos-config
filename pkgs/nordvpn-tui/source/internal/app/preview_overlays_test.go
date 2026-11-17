package app

import (
	"testing"
	"time"

	applog "github.com/simonwa01/nordvpn-tui/internal/log"
	"github.com/simonwa01/nordvpn-tui/internal/state"
	"github.com/simonwa01/nordvpn-tui/internal/vpn"
)

func TestPreview_Help(t *testing.T) {
	m := newTestModel(vpn.Status{State: vpn.StateConnected, Country: "Germany", City: "Frankfurt"}, state.ViewHome, 100, 32)
	m.S.ShowHelp = true
	t.Logf("\n%s\n", m.View())
}

func TestPreview_Log(t *testing.T) {
	m := newTestModel(vpn.Status{State: vpn.StateDisconnected}, state.ViewHome, 100, 28)
	m.S.ShowLog = true
	now := time.Now()
	m.S.Log.Add(applog.LevelInfo, "Connected to United States — New York")
	m.S.Log.Add(applog.LevelWarn, "Slow response from nordvpn status")
	m.S.Log.Add(applog.LevelError, "Connect to Germany failed: Whoops! Connection failed.")
	m.S.Log.Add(applog.LevelInfo, "Disconnected")
	_ = now
	t.Logf("\n%s\n", m.View())
}
