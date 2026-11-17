package app

import (
	"time"

	"github.com/simonwa01/nordvpn-tui/internal/vpn"
)

// Domain messages flowing from vpn.Client operations back into Update.
// Keep them small and explicit — the reducer matches on these types.

type StatusMsg struct {
	Status vpn.Status
	Err    error
}

type SettingsMsg struct {
	Settings vpn.Settings
	Err      error
}

type AccountMsg struct {
	Account vpn.Account
	Err     error
}

type CountriesMsg struct {
	Countries []string
	Err       error
}

type CitiesMsg struct {
	Country string
	Cities  []string
	Err     error
}

// ActionMsg reports the result of a connect/disconnect/set operation.
type ActionKind int

const (
	ActionConnect ActionKind = iota
	ActionDisconnect
	ActionSet
)

type ActionMsg struct {
	Kind    ActionKind
	Summary string // short human-readable, e.g. "Connected to United States"
	Err     error
}

// TickMsg drives the 2s status poller. Only dispatched when no action is pending.
type TickMsg time.Time

// SpinnerTickMsg drives the 100ms spinner frame refresh while an action is in flight.
type SpinnerTickMsg time.Time

// ToastExpireMsg clears the current toast.
type ToastExpireMsg struct{}
