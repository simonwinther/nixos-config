package vpn

import "strings"

// ParseAccount turns `nordvpn account` output into an Account struct.
// If the CLI indicated not-logged-in, callers detect that via ErrNotLoggedIn
// from run(); this function only parses a logged-in payload.
func ParseAccount(raw string) Account {
	a := Account{LoggedIn: true, Raw: raw}
	for _, line := range strings.Split(raw, "\n") {
		m := statusFieldRE.FindStringSubmatch(line)
		if m == nil {
			continue
		}
		key := strings.ToLower(strings.TrimSpace(m[1]))
		val := strings.TrimSpace(m[2])
		switch key {
		case "email address":
			a.Email = val
		case "subscription":
			a.Subscription = val
		}
	}
	if a.Email == "" {
		a.LoggedIn = false
	}
	return a
}
