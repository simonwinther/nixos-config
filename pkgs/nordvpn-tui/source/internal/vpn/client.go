package vpn

import (
	"context"
	"errors"
	"time"
)

type ConnState int

const (
	StateUnknown ConnState = iota
	StateDisconnected
	StateConnecting
	StateConnected
	StateDisconnecting
)

func (s ConnState) String() string {
	switch s {
	case StateDisconnected:
		return "Disconnected"
	case StateConnecting:
		return "Connecting"
	case StateConnected:
		return "Connected"
	case StateDisconnecting:
		return "Disconnecting"
	default:
		return "Unknown"
	}
}

type Status struct {
	State      ConnState
	Hostname   string
	IP         string
	Country    string
	City       string
	Technology string
	Protocol   string
	Uptime     time.Duration
	Since      time.Time
	Raw        string
}

type Settings struct {
	Technology       string
	KillSwitch       bool
	ThreatProtection bool
	Notify           bool
	AutoConnect      bool
	Firewall         bool
	Routing          bool
	Meshnet          bool
	DNS              bool
	LANDiscovery     bool
	VirtualLocation  bool
	PostQuantum      bool
	Raw              string
}

type Account struct {
	LoggedIn     bool
	Email        string
	Subscription string
	Raw          string
}

// Errors are typed so the UI layer never inspects raw strings.
var (
	ErrNotLoggedIn   = errors.New("not logged in")
	ErrDaemonDown    = errors.New("nordvpn daemon not running")
	ErrBinaryMissing = errors.New("nordvpn binary not found")
	ErrConnectFailed = errors.New("connection failed")
	ErrUnknownServer = errors.New("unknown server or country")
	ErrTimeout       = errors.New("nordvpn command timed out")
)

// CLIError wraps an unclassified CLI failure. The raw output is preserved for logging.
type CLIError struct {
	Cmd    string
	Stderr string
	Stdout string
	Err    error
}

func (e *CLIError) Error() string {
	if e.Stderr != "" {
		return "nordvpn " + e.Cmd + ": " + strings1stLine(e.Stderr)
	}
	if e.Err != nil {
		return "nordvpn " + e.Cmd + ": " + e.Err.Error()
	}
	return "nordvpn " + e.Cmd + ": failed"
}

func (e *CLIError) Unwrap() error { return e.Err }

func strings1stLine(s string) string {
	for i, r := range s {
		if r == '\n' {
			return s[:i]
		}
	}
	return s
}

// Client is the contract between the app and the CLI. Implementations are
// the real wrapper (exec.go) and a scripted fake (fake.go) for dev/tests.
type Client interface {
	Status(ctx context.Context) (Status, error)
	Settings(ctx context.Context) (Settings, error)
	Account(ctx context.Context) (Account, error)
	Countries(ctx context.Context) ([]string, error)
	Cities(ctx context.Context, country string) ([]string, error)

	Connect(ctx context.Context) error
	ConnectCountry(ctx context.Context, country string) error
	ConnectCity(ctx context.Context, country, city string) error
	Disconnect(ctx context.Context) error

	Set(ctx context.Context, key, value string) error
}
