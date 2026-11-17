package vpn

import (
	"strings"
)

// ParseSettings turns `nordvpn settings` output into a Settings struct.
// Uses the same "Key: value" convention as status.
func ParseSettings(raw string) Settings {
	s := Settings{Raw: raw}
	for _, line := range strings.Split(raw, "\n") {
		m := statusFieldRE.FindStringSubmatch(line)
		if m == nil {
			continue
		}
		key := strings.ToLower(strings.TrimSpace(m[1]))
		val := strings.TrimSpace(m[2])
		b := parseBool(val)
		switch key {
		case "technology":
			s.Technology = val
		case "kill switch":
			s.KillSwitch = b
		case "threat protection lite", "threat protection":
			s.ThreatProtection = b
		case "notify":
			s.Notify = b
		case "auto-connect":
			s.AutoConnect = b
		case "firewall":
			s.Firewall = b
		case "routing":
			s.Routing = b
		case "meshnet":
			s.Meshnet = b
		case "dns":
			s.DNS = b
		case "lan discovery":
			s.LANDiscovery = b
		case "virtual location":
			s.VirtualLocation = b
		case "post-quantum vpn":
			s.PostQuantum = b
		}
	}
	return s
}

func parseBool(v string) bool {
	switch strings.ToLower(strings.TrimSpace(v)) {
	case "enabled", "on", "true", "yes":
		return true
	}
	return false
}
