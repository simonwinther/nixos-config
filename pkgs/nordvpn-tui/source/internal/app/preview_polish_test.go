package app

import (
	"strings"
	"testing"

	"github.com/simonwa01/nordvpn-tui/internal/state"
	"github.com/simonwa01/nordvpn-tui/internal/vpn"
)

func TestPreview_Fatal_DaemonDown(t *testing.T) {
	m := newTestModel(vpn.Status{}, state.ViewHome, 100, 28)
	m.S.FatalErr = vpn.ErrDaemonDown
	out := m.View()
	if !strings.Contains(out, "daemon") {
		t.Fatalf("expected daemon message")
	}
	t.Logf("\n%s\n", out)
}

func TestPreview_Fatal_BinaryMissing(t *testing.T) {
	m := newTestModel(vpn.Status{}, state.ViewHome, 100, 28)
	m.S.FatalErr = vpn.ErrBinaryMissing
	t.Logf("\n%s\n", m.View())
}

func TestPreview_TooSmall(t *testing.T) {
	m := newTestModel(vpn.Status{State: vpn.StateDisconnected}, state.ViewHome, 40, 10)
	out := m.View()
	if !strings.Contains(out, "too small") {
		t.Fatalf("expected too-small banner")
	}
	t.Logf("\n%s\n", out)
}

func TestPreview_Responsive_80x24(t *testing.T) {
	st := vpn.Status{
		State:      vpn.StateConnected,
		Country:    "United States",
		City:       "New York",
		Hostname:   "us4521.nordvpn.com",
		IP:         "198.51.100.42",
		Technology: "NORDLYNX",
	}
	m := newTestModel(st, state.ViewHome, 80, 24)
	t.Logf("\n%s\n", m.View())
}

func TestPreview_Toast(t *testing.T) {
	m := newTestModel(vpn.Status{State: vpn.StateConnected, Country: "Germany", City: "Frankfurt"}, state.ViewHome, 100, 28)
	m.S.SetToast("Connected to Germany — Frankfurt", false)
	t.Logf("\n%s\n", m.View())
}
