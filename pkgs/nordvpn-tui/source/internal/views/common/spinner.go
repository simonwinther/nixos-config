package common

import (
	"time"

	"github.com/simonwa01/nordvpn-tui/internal/theme"
)

// brailleFrames is a subtle single-braille spinner — one character wide,
// no visual noise. Frame picked from wall-clock time so we don't need
// a separate tea.Cmd ticker for a purely decorative glyph.
var brailleFrames = []string{"⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"}

// Spinner returns one frame of a subtle braille spinner in the accent color.
// There is only ever one spinner visible per screen, by design.
func Spinner(s theme.Styles, now time.Time) string {
	idx := (now.UnixNano() / int64(time.Millisecond*90)) % int64(len(brailleFrames))
	return s.Accent.Render(brailleFrames[idx])
}
