package app

import (
	"strings"
	"testing"
	"time"

	"github.com/simonwa01/nordvpn-tui/internal/state"
	"github.com/simonwa01/nordvpn-tui/internal/vpn"
)

// These aren't strict assertions — they render to stdout with `-v` so a human
// can eyeball the design, and they assert the output is non-empty and stable-ish.
// Pure regression guard plus a dev ergonomics tool.

func newTestModel(st vpn.Status, view state.ViewID, w, h int) *Model {
	m := New(vpn.NewFakeClient(), true)
	m.S.Width = w
	m.S.Height = h
	m.S.View = view
	m.S.Status = st
	m.S.Account = vpn.Account{LoggedIn: true, Email: "demo@example.com"}
	m.S.Settings = vpn.Settings{Technology: "NORDLYNX", Notify: true, Firewall: true}
	m.S.Now = time.Unix(0, 0)
	return m
}

func TestPreview_HomeDisconnected(t *testing.T) {
	m := newTestModel(vpn.Status{State: vpn.StateDisconnected}, state.ViewHome, 100, 28)
	out := m.View()
	if !strings.Contains(out, "Disconnected") {
		t.Fatalf("expected state word in output")
	}
	t.Logf("\n%s\n", out)
}

func TestPreview_HomeConnected(t *testing.T) {
	st := vpn.Status{
		State:      vpn.StateConnected,
		Country:    "United States",
		City:       "New York",
		Hostname:   "us4521.nordvpn.com",
		IP:         "198.51.100.42",
		Technology: "NORDLYNX",
		Protocol:   "UDP",
		Uptime:     12*time.Minute + 37*time.Second,
	}
	m := newTestModel(st, state.ViewHome, 100, 28)
	out := m.View()
	if !strings.Contains(out, "Connected") {
		t.Fatalf("expected state word in output")
	}
	t.Logf("\n%s\n", out)
}

func TestPreview_HomeConnecting(t *testing.T) {
	m := newTestModel(vpn.Status{State: vpn.StateConnecting}, state.ViewHome, 100, 28)
	m.S.Pending.Action = true
	out := m.View()
	if !strings.Contains(out, "Connecting") {
		t.Fatalf("expected state word")
	}
	t.Logf("\n%s\n", out)
}

func TestPreview_HomeNarrow(t *testing.T) {
	st := vpn.Status{
		State:      vpn.StateConnected,
		Country:    "United States",
		City:       "New York",
		Hostname:   "us4521.nordvpn.com",
		IP:         "198.51.100.42",
		Technology: "NORDLYNX",
		Uptime:     12 * time.Minute,
	}
	m := newTestModel(st, state.ViewHome, 80, 20)
	out := m.View()
	t.Logf("\n%s\n", out)
}
