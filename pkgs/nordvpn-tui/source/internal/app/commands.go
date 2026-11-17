package app

import (
	"context"
	"fmt"
	"time"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/simonwa01/nordvpn-tui/internal/vpn"
)

// Timeouts per category — see plan.
const (
	statusTimeout = 3 * time.Second
	listTimeout   = 8 * time.Second
	actionTimeout = 30 * time.Second
)

// fetchStatus issues `nordvpn status` and returns a StatusMsg.
func fetchStatus(client vpn.Client) tea.Cmd {
	return func() tea.Msg {
		ctx, cancel := context.WithTimeout(context.Background(), statusTimeout)
		defer cancel()
		st, err := client.Status(ctx)
		return StatusMsg{Status: st, Err: err}
	}
}

func fetchSettings(client vpn.Client) tea.Cmd {
	return func() tea.Msg {
		ctx, cancel := context.WithTimeout(context.Background(), statusTimeout)
		defer cancel()
		s, err := client.Settings(ctx)
		return SettingsMsg{Settings: s, Err: err}
	}
}

func fetchAccount(client vpn.Client) tea.Cmd {
	return func() tea.Msg {
		ctx, cancel := context.WithTimeout(context.Background(), statusTimeout)
		defer cancel()
		a, err := client.Account(ctx)
		return AccountMsg{Account: a, Err: err}
	}
}

func fetchCountries(client vpn.Client) tea.Cmd {
	return func() tea.Msg {
		ctx, cancel := context.WithTimeout(context.Background(), listTimeout)
		defer cancel()
		cs, err := client.Countries(ctx)
		return CountriesMsg{Countries: cs, Err: err}
	}
}

func fetchCities(client vpn.Client, country string) tea.Cmd {
	return func() tea.Msg {
		ctx, cancel := context.WithTimeout(context.Background(), listTimeout)
		defer cancel()
		cs, err := client.Cities(ctx, country)
		return CitiesMsg{Country: country, Cities: cs, Err: err}
	}
}

func runConnect(client vpn.Client) tea.Cmd {
	return func() tea.Msg {
		ctx, cancel := context.WithTimeout(context.Background(), actionTimeout)
		defer cancel()
		err := client.Connect(ctx)
		msg := "Connected"
		if err != nil {
			msg = "Connect failed"
		}
		return ActionMsg{Kind: ActionConnect, Summary: msg, Err: err}
	}
}

func runConnectCountry(client vpn.Client, country string) tea.Cmd {
	return func() tea.Msg {
		ctx, cancel := context.WithTimeout(context.Background(), actionTimeout)
		defer cancel()
		err := client.ConnectCountry(ctx, country)
		summary := fmt.Sprintf("Connected to %s", vpn.Display(country))
		if err != nil {
			summary = fmt.Sprintf("Connect to %s failed", vpn.Display(country))
		}
		return ActionMsg{Kind: ActionConnect, Summary: summary, Err: err}
	}
}

func runConnectCity(client vpn.Client, country, city string) tea.Cmd {
	return func() tea.Msg {
		ctx, cancel := context.WithTimeout(context.Background(), actionTimeout)
		defer cancel()
		err := client.ConnectCity(ctx, country, city)
		summary := fmt.Sprintf("Connected to %s — %s", vpn.Display(country), vpn.Display(city))
		if err != nil {
			summary = fmt.Sprintf("Connect to %s — %s failed", vpn.Display(country), vpn.Display(city))
		}
		return ActionMsg{Kind: ActionConnect, Summary: summary, Err: err}
	}
}

func runDisconnect(client vpn.Client) tea.Cmd {
	return func() tea.Msg {
		ctx, cancel := context.WithTimeout(context.Background(), actionTimeout)
		defer cancel()
		err := client.Disconnect(ctx)
		msg := "Disconnected"
		if err != nil {
			msg = "Disconnect failed"
		}
		return ActionMsg{Kind: ActionDisconnect, Summary: msg, Err: err}
	}
}

func runSet(client vpn.Client, key, value string) tea.Cmd {
	return func() tea.Msg {
		ctx, cancel := context.WithTimeout(context.Background(), actionTimeout)
		defer cancel()
		err := client.Set(ctx, key, value)
		summary := fmt.Sprintf("Set %s = %s", key, value)
		if err != nil {
			summary = fmt.Sprintf("Set %s failed", key)
		}
		return ActionMsg{Kind: ActionSet, Summary: summary, Err: err}
	}
}

func tick() tea.Cmd {
	return tea.Tick(2*time.Second, func(t time.Time) tea.Msg {
		return TickMsg(t)
	})
}

func spinnerTick() tea.Cmd {
	return tea.Tick(90*time.Millisecond, func(t time.Time) tea.Msg {
		return SpinnerTickMsg(t)
	})
}

func toastExpire() tea.Cmd {
	return tea.Tick(4*time.Second, func(_ time.Time) tea.Msg {
		return ToastExpireMsg{}
	})
}
