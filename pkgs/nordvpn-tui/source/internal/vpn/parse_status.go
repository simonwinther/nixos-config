package vpn

import (
	"regexp"
	"strings"
	"time"
)

var statusFieldRE = regexp.MustCompile(`^\s*([A-Za-z][A-Za-z \-]+):\s*(.+?)\s*$`)

// ParseStatus turns `nordvpn status` output into a Status struct.
// Missing fields become zero values; it never returns an error.
func ParseStatus(raw string) Status {
	s := Status{State: StateUnknown, Raw: raw}
	for _, line := range strings.Split(raw, "\n") {
		m := statusFieldRE.FindStringSubmatch(line)
		if m == nil {
			continue
		}
		key := strings.ToLower(strings.TrimSpace(m[1]))
		val := strings.TrimSpace(m[2])
		switch key {
		case "status":
			s.State = parseConnState(val)
		case "hostname":
			s.Hostname = val
		case "ip":
			s.IP = val
		case "country":
			s.Country = val
		case "city":
			s.City = val
		case "current technology":
			s.Technology = val
		case "current protocol":
			s.Protocol = val
		case "uptime":
			s.Uptime = parseUptime(val)
			if s.Uptime > 0 {
				s.Since = time.Now().Add(-s.Uptime)
			}
		}
	}
	return s
}

func parseConnState(v string) ConnState {
	switch strings.ToLower(v) {
	case "connected":
		return StateConnected
	case "connecting":
		return StateConnecting
	case "disconnected":
		return StateDisconnected
	case "disconnecting":
		return StateDisconnecting
	}
	return StateUnknown
}

var uptimeRE = regexp.MustCompile(`(\d+)\s*(year|month|week|day|hour|minute|second)s?`)

func parseUptime(v string) time.Duration {
	var total time.Duration
	for _, m := range uptimeRE.FindAllStringSubmatch(v, -1) {
		n := atoi(m[1])
		switch m[2] {
		case "year":
			total += time.Duration(n) * 365 * 24 * time.Hour
		case "month":
			total += time.Duration(n) * 30 * 24 * time.Hour
		case "week":
			total += time.Duration(n) * 7 * 24 * time.Hour
		case "day":
			total += time.Duration(n) * 24 * time.Hour
		case "hour":
			total += time.Duration(n) * time.Hour
		case "minute":
			total += time.Duration(n) * time.Minute
		case "second":
			total += time.Duration(n) * time.Second
		}
	}
	return total
}

func atoi(s string) int {
	n := 0
	for _, r := range s {
		if r < '0' || r > '9' {
			return n
		}
		n = n*10 + int(r-'0')
	}
	return n
}
