package vpn

import (
	"strings"
)

// ParseList turns one-per-line (or comma-separated) CLI output into a
// sorted, deduped slice. Shared by countries and cities.
func ParseList(raw string) []string {
	seen := make(map[string]struct{})
	out := make([]string, 0, 64)

	// Some nordvpn versions print comma-separated; most print one per line.
	replacer := strings.NewReplacer(",", "\n")
	for _, rawLine := range strings.Split(replacer.Replace(raw), "\n") {
		line := strings.TrimSpace(rawLine)
		if line == "" {
			continue
		}
		// Skip obvious non-entries (headers, warnings).
		if strings.Contains(line, ":") && !looksLikeName(line) {
			continue
		}
		for _, tok := range strings.Fields(line) {
			t := strings.TrimSpace(tok)
			if t == "" {
				continue
			}
			if _, ok := seen[t]; ok {
				continue
			}
			seen[t] = struct{}{}
			out = append(out, t)
		}
	}
	return out
}

// Display converts "United_States" → "United States" for rendering.
func Display(name string) string {
	return strings.ReplaceAll(name, "_", " ")
}

// Arg converts "United States" → "United_States" for the CLI.
func Arg(name string) string {
	return strings.ReplaceAll(strings.TrimSpace(name), " ", "_")
}

func looksLikeName(line string) bool {
	// Country/city tokens may contain letters, digits, underscores only.
	for _, r := range line {
		if r == ' ' || r == '_' || r == ',' {
			continue
		}
		if !(r >= 'A' && r <= 'Z') && !(r >= 'a' && r <= 'z') && !(r >= '0' && r <= '9') {
			return false
		}
	}
	return true
}
