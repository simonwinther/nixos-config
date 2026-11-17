package theme

import "github.com/charmbracelet/lipgloss"

// Palette defines the full set of semantic colors the app uses.
// One accent, three status colors, three neutrals — and nothing else.
// Lip Gloss auto-degrades to the nearest ANSI color on low-capability terminals.
type Palette struct {
	Accent    lipgloss.Color
	OK        lipgloss.Color
	Warn      lipgloss.Color
	Err       lipgloss.Color
	Fg        lipgloss.Color
	Muted     lipgloss.Color
	Faint     lipgloss.Color
	BorderDim lipgloss.Color
}

// Dark is the default palette. Values are tuned against a dark background
// and intentionally low-saturation so nothing shouts.
var Dark = Palette{
	Accent:    lipgloss.Color("#5E81F4"),
	OK:        lipgloss.Color("#7EC98F"),
	Warn:      lipgloss.Color("#E0AF68"),
	Err:       lipgloss.Color("#E06C75"),
	Fg:        lipgloss.Color("#D4D4D8"),
	Muted:     lipgloss.Color("#8B8D97"),
	Faint:     lipgloss.Color("#5A5C66"),
	BorderDim: lipgloss.Color("#3A3C44"),
}

// Current returns the active palette. Kept as a function so a future
// --theme flag can swap it without changing call sites.
func Current() Palette { return Dark }
