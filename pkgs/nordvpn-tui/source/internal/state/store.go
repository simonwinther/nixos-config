package state

import (
	"time"

	"github.com/simonwa01/nordvpn-tui/internal/log"
	"github.com/simonwa01/nordvpn-tui/internal/vpn"
)

type ViewID int

const (
	ViewHome ViewID = iota
	ViewCountries
	ViewServers
	ViewSettings
	ViewHelp
	ViewLog
)

type Toast struct {
	Text    string
	IsError bool
	Until   time.Time
}

type PendingOps struct {
	Status   bool
	Settings bool
	List     bool
	Action   bool // connect/disconnect/set
}

// Any returns true if any operation is in flight.
func (p PendingOps) Any() bool {
	return p.Status || p.Settings || p.List || p.Action
}

type AppState struct {
	View ViewID
	Prev ViewID

	Status   vpn.Status
	Settings vpn.Settings
	Account  vpn.Account

	Countries       []string
	Cities          map[string][]string
	SelectedCountry string

	// Per-view search query. Keyed by ViewID.
	Search map[ViewID]string

	Pending   PendingOps
	LastErr   error
	FatalErr  error // daemon-down / binary-missing — blocks the UI
	Toast     *Toast
	Log       *log.Buffer
	Width     int
	Height    int
	Now       time.Time
	ShowHelp  bool
	ShowLog   bool
	UsingFake bool

	// Per-view transient UI state. Cursor positions and search modes are
	// kept here so switching views preserves their position.
	Cursor     map[ViewID]int
	SearchMode map[ViewID]bool

	// SettingsConfirm, when non-nil, shows an inline y/n prompt in the
	// settings view. Used for risky toggles only (Kill Switch).
	SettingsConfirm *SettingsConfirm
}

// SettingsConfirm holds the pending apply for a risky setting change.
type SettingsConfirm struct {
	Message string
	Key     string
	Value   string
}

func New(usingFake bool) *AppState {
	return &AppState{
		View:       ViewHome,
		Status:     vpn.Status{State: vpn.StateUnknown},
		Cities:     make(map[string][]string),
		Search:     make(map[ViewID]string),
		Cursor:     make(map[ViewID]int),
		SearchMode: make(map[ViewID]bool),
		Log:        log.NewBuffer(50),
		Now:        time.Now(),
		UsingFake:  usingFake,
	}
}

func (s *AppState) SetToast(text string, isError bool) {
	s.Toast = &Toast{Text: text, IsError: isError, Until: time.Now().Add(4 * time.Second)}
}

func (s *AppState) ClearToast() { s.Toast = nil }
