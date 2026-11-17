package vpn

import (
	"os"
	"path/filepath"
	"testing"
	"time"
)

func readFixture(t *testing.T, name string) string {
	t.Helper()
	b, err := os.ReadFile(filepath.Join("testdata", name))
	if err != nil {
		t.Fatalf("read fixture %s: %v", name, err)
	}
	return string(b)
}

func TestParseStatus_Disconnected(t *testing.T) {
	s := ParseStatus(readFixture(t, "status_disconnected.txt"))
	if s.State != StateDisconnected {
		t.Errorf("state = %v, want Disconnected", s.State)
	}
}

func TestParseStatus_Connecting(t *testing.T) {
	s := ParseStatus(readFixture(t, "status_connecting.txt"))
	if s.State != StateConnecting {
		t.Errorf("state = %v, want Connecting", s.State)
	}
}

func TestParseStatus_Connected(t *testing.T) {
	s := ParseStatus(readFixture(t, "status_connected.txt"))
	if s.State != StateConnected {
		t.Fatalf("state = %v, want Connected", s.State)
	}
	if s.Country != "United States" || s.City != "New York" {
		t.Errorf("country/city = %q/%q", s.Country, s.City)
	}
	if s.Hostname != "us4521.nordvpn.com" {
		t.Errorf("hostname = %q", s.Hostname)
	}
	if s.IP != "198.51.100.42" {
		t.Errorf("ip = %q", s.IP)
	}
	if s.Technology != "NORDLYNX" || s.Protocol != "UDP" {
		t.Errorf("tech/proto = %q/%q", s.Technology, s.Protocol)
	}
	want := time.Hour + 23*time.Minute + 5*time.Second
	if s.Uptime != want {
		t.Errorf("uptime = %v, want %v", s.Uptime, want)
	}
}

func TestParseStatus_WithANSI(t *testing.T) {
	raw := "\x1b[36mStatus:\x1b[0m Connected\n" +
		"\x1b[36mCountry:\x1b[0m Sweden\n" +
		"\x1b[36mCity:\x1b[0m Stockholm\n" +
		"\x1b[36mUptime:\x1b[0m 45 seconds\n"
	s := ParseStatus(stripANSI(raw))
	if s.State != StateConnected {
		t.Errorf("state = %v", s.State)
	}
	if s.Country != "Sweden" || s.City != "Stockholm" {
		t.Errorf("country/city = %q/%q", s.Country, s.City)
	}
	if s.Uptime != 45*time.Second {
		t.Errorf("uptime = %v", s.Uptime)
	}
}

func TestParseStatus_UnknownField(t *testing.T) {
	raw := "Status: Connected\nFuture Field: something\nCountry: France\n"
	s := ParseStatus(raw)
	if s.State != StateConnected || s.Country != "France" {
		t.Errorf("parse degraded: %+v", s)
	}
}
