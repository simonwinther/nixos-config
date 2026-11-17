package vpn

import (
	"context"
	"sort"
	"strings"
	"sync"
	"time"
)

// FakeClient is a scripted in-memory implementation used with --fake for
// development and snapshot tests. It simulates connect/disconnect latency
// and keeps settings state in memory.
type FakeClient struct {
	mu       sync.Mutex
	status   Status
	settings Settings
	account  Account
	delay    time.Duration
}

func NewFakeClient() *FakeClient {
	return &FakeClient{
		status: Status{State: StateDisconnected},
		settings: Settings{
			Technology:      "NORDLYNX",
			Firewall:        true,
			Routing:         true,
			Notify:          true,
			VirtualLocation: true,
		},
		account: Account{
			LoggedIn:     true,
			Email:        "demo@example.com",
			Subscription: "Active until Jan 1, 2030",
		},
		delay: 600 * time.Millisecond,
	}
}

func (f *FakeClient) wait(ctx context.Context) error {
	select {
	case <-time.After(f.delay):
		return nil
	case <-ctx.Done():
		return ErrTimeout
	}
}

func (f *FakeClient) Status(_ context.Context) (Status, error) {
	f.mu.Lock()
	defer f.mu.Unlock()
	s := f.status
	if s.State == StateConnected && !s.Since.IsZero() {
		s.Uptime = time.Since(s.Since).Round(time.Second)
	}
	return s, nil
}

func (f *FakeClient) Settings(_ context.Context) (Settings, error) {
	f.mu.Lock()
	defer f.mu.Unlock()
	return f.settings, nil
}

func (f *FakeClient) Account(_ context.Context) (Account, error) {
	f.mu.Lock()
	defer f.mu.Unlock()
	return f.account, nil
}

func (f *FakeClient) Countries(_ context.Context) ([]string, error) {
	cs := []string{
		"United_States", "United_Kingdom", "Germany", "France", "Netherlands",
		"Sweden", "Switzerland", "Canada", "Japan", "Australia", "Norway",
		"Denmark", "Finland", "Spain", "Italy", "Poland", "Brazil", "Mexico",
		"Singapore", "South_Korea", "Iceland", "Ireland", "Belgium", "Austria",
	}
	sort.Strings(cs)
	return cs, nil
}

func (f *FakeClient) Cities(_ context.Context, country string) ([]string, error) {
	switch strings.ToLower(country) {
	case "united_states", "united states":
		return []string{"New_York", "Los_Angeles", "Chicago", "Dallas", "Seattle", "Atlanta", "Denver", "Miami"}, nil
	case "united_kingdom", "united kingdom":
		return []string{"London", "Manchester"}, nil
	case "germany":
		return []string{"Berlin", "Frankfurt"}, nil
	}
	return []string{"Default_City"}, nil
}

func (f *FakeClient) setConnected(country, city string) {
	f.status = Status{
		State:      StateConnected,
		Country:    Display(country),
		City:       Display(city),
		Hostname:   strings.ToLower(country) + "123.nordvpn.com",
		IP:         "198.51.100.42",
		Technology: f.settings.Technology,
		Protocol:   "UDP",
		Since:      time.Now(),
	}
}

func (f *FakeClient) Connect(ctx context.Context) error {
	if err := f.wait(ctx); err != nil {
		return err
	}
	f.mu.Lock()
	defer f.mu.Unlock()
	f.setConnected("United_States", "New_York")
	return nil
}

func (f *FakeClient) ConnectCountry(ctx context.Context, country string) error {
	if err := f.wait(ctx); err != nil {
		return err
	}
	f.mu.Lock()
	defer f.mu.Unlock()
	f.setConnected(country, "Default_City")
	return nil
}

func (f *FakeClient) ConnectCity(ctx context.Context, country, city string) error {
	if err := f.wait(ctx); err != nil {
		return err
	}
	f.mu.Lock()
	defer f.mu.Unlock()
	f.setConnected(country, city)
	return nil
}

func (f *FakeClient) Disconnect(ctx context.Context) error {
	if err := f.wait(ctx); err != nil {
		return err
	}
	f.mu.Lock()
	defer f.mu.Unlock()
	f.status = Status{State: StateDisconnected}
	return nil
}

func (f *FakeClient) Set(_ context.Context, key, value string) error {
	f.mu.Lock()
	defer f.mu.Unlock()
	b := parseBool(value)
	switch strings.ToLower(key) {
	case "killswitch":
		f.settings.KillSwitch = b
	case "threatprotectionlite":
		f.settings.ThreatProtection = b
	case "notify":
		f.settings.Notify = b
	case "autoconnect":
		f.settings.AutoConnect = b
	case "technology":
		f.settings.Technology = strings.ToUpper(value)
	}
	return nil
}
