package vpn

import "testing"

func TestParseSettings(t *testing.T) {
	s := ParseSettings(readFixture(t, "settings.txt"))
	if s.Technology != "NORDLYNX" {
		t.Errorf("technology = %q", s.Technology)
	}
	if s.KillSwitch {
		t.Errorf("killswitch should be disabled")
	}
	if !s.Notify {
		t.Errorf("notify should be enabled")
	}
	if !s.Firewall {
		t.Errorf("firewall should be enabled")
	}
	if s.AutoConnect {
		t.Errorf("autoconnect should be disabled")
	}
	if !s.VirtualLocation {
		t.Errorf("virtual location should be enabled")
	}
	if s.ThreatProtection {
		t.Errorf("tp should be disabled")
	}
}
