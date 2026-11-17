package theme

import "github.com/charmbracelet/lipgloss"

// Styles centralizes every reusable style so views stay declarative.
// Rules of thumb (mirrored from the design spec):
//   - One accent color. Never combine accent + OK/Warn/Err in the same region.
//   - Weight + dim, not background fills, to express hierarchy.
//   - Rounded border only on the one focused primary; everything else sharp or no border.
//   - Keymap hints always dim, bullet-separated, bottom-right.
type Styles struct {
	P Palette

	// Text roles.
	Title  lipgloss.Style
	Body   lipgloss.Style
	Muted  lipgloss.Style
	Faint  lipgloss.Style
	Accent lipgloss.Style
	OK     lipgloss.Style
	Warn   lipgloss.Style
	Err    lipgloss.Style

	// Hero (the persistent status line).
	HeroState   lipgloss.Style // bold state word, colored by state
	HeroDot     lipgloss.Style // small glyph before state word
	HeroPrimary lipgloss.Style // country — city
	HeroMeta    lipgloss.Style // tech · ip · uptime, dim, right
	HeroSep     lipgloss.Style // " · " between fields

	// Hint bar (bottom).
	Hint    lipgloss.Style
	HintKey lipgloss.Style
	HintSep lipgloss.Style

	// Lists.
	ListRow     lipgloss.Style
	ListRowDim  lipgloss.Style
	FocusRow    lipgloss.Style // left accent bar + bold text
	FocusMarker lipgloss.Style // the "▌" glyph

	// Breadcrumb.
	Breadcrumb    lipgloss.Style
	BreadcrumbSep lipgloss.Style

	// Empty state + skeleton rows.
	Empty    lipgloss.Style
	Skeleton lipgloss.Style

	// Search.
	SearchPrompt lipgloss.Style
	SearchText   lipgloss.Style

	// Toast.
	ToastInfo lipgloss.Style
	ToastErr  lipgloss.Style

	// Overlay (help, log). Subtle rounded border, accent-dim.
	Overlay      lipgloss.Style
	OverlayTitle lipgloss.Style

	// Primary CTA (e.g. Home quick-connect pill).
	CTA        lipgloss.Style
	CTAConnect lipgloss.Style
	CTADisconn lipgloss.Style

	// Settings key/value columns.
	SettingsKey     lipgloss.Style
	SettingsValOn   lipgloss.Style
	SettingsValOff  lipgloss.Style
	SettingsEnumVal lipgloss.Style
}

// Build returns a Styles instance from a palette. Call once at startup.
func Build(p Palette) Styles {
	s := Styles{P: p}

	s.Title = lipgloss.NewStyle().Foreground(p.Fg).Bold(true)
	s.Body = lipgloss.NewStyle().Foreground(p.Fg)
	s.Muted = lipgloss.NewStyle().Foreground(p.Muted)
	s.Faint = lipgloss.NewStyle().Foreground(p.Faint)
	s.Accent = lipgloss.NewStyle().Foreground(p.Accent)
	s.OK = lipgloss.NewStyle().Foreground(p.OK)
	s.Warn = lipgloss.NewStyle().Foreground(p.Warn)
	s.Err = lipgloss.NewStyle().Foreground(p.Err)

	s.HeroState = lipgloss.NewStyle().Bold(true)
	s.HeroDot = lipgloss.NewStyle().Bold(true)
	s.HeroPrimary = lipgloss.NewStyle().Foreground(p.Fg)
	s.HeroMeta = lipgloss.NewStyle().Foreground(p.Muted)
	s.HeroSep = lipgloss.NewStyle().Foreground(p.Faint)

	s.Hint = lipgloss.NewStyle().Foreground(p.Muted)
	s.HintKey = lipgloss.NewStyle().Foreground(p.Fg).Bold(true)
	s.HintSep = lipgloss.NewStyle().Foreground(p.Faint)

	s.ListRow = lipgloss.NewStyle().Foreground(p.Fg).PaddingLeft(2)
	s.ListRowDim = lipgloss.NewStyle().Foreground(p.Muted).PaddingLeft(2)
	s.FocusRow = lipgloss.NewStyle().Foreground(p.Fg).Bold(true)
	s.FocusMarker = lipgloss.NewStyle().Foreground(p.Accent).Bold(true)

	s.Breadcrumb = lipgloss.NewStyle().Foreground(p.Fg)
	s.BreadcrumbSep = lipgloss.NewStyle().Foreground(p.Faint)

	s.Empty = lipgloss.NewStyle().Foreground(p.Muted).Align(lipgloss.Center)
	s.Skeleton = lipgloss.NewStyle().Foreground(p.BorderDim)

	s.SearchPrompt = lipgloss.NewStyle().Foreground(p.Accent).Bold(true)
	s.SearchText = lipgloss.NewStyle().Foreground(p.Fg)

	s.ToastInfo = lipgloss.NewStyle().Foreground(p.OK).Bold(true)
	s.ToastErr = lipgloss.NewStyle().Foreground(p.Err).Bold(true)

	s.Overlay = lipgloss.NewStyle().
		Foreground(p.Fg).
		Border(lipgloss.RoundedBorder()).
		BorderForeground(p.BorderDim).
		Padding(1, 2)
	s.OverlayTitle = lipgloss.NewStyle().Foreground(p.Accent).Bold(true)

	s.CTA = lipgloss.NewStyle().Bold(true)
	s.CTAConnect = s.CTA.Foreground(p.OK)
	s.CTADisconn = s.CTA.Foreground(p.Accent)

	s.SettingsKey = lipgloss.NewStyle().Foreground(p.Fg).Bold(true)
	s.SettingsValOn = lipgloss.NewStyle().Foreground(p.Accent).Bold(true)
	s.SettingsValOff = lipgloss.NewStyle().Foreground(p.Muted)
	s.SettingsEnumVal = lipgloss.NewStyle().Foreground(p.Accent)

	return s
}
