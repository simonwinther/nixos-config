package app

import (
	"testing"

	"github.com/simonwa01/nordvpn-tui/internal/state"
	"github.com/simonwa01/nordvpn-tui/internal/vpn"
)

func TestPreview_Countries(t *testing.T) {
	m := newTestModel(vpn.Status{State: vpn.StateDisconnected}, state.ViewCountries, 100, 28)
	m.S.Countries = []string{
		"Australia", "Austria", "Belgium", "Canada", "Denmark", "Finland",
		"France", "Germany", "Iceland", "Ireland", "Italy", "Japan",
		"Netherlands", "Norway", "Poland", "Singapore", "Spain", "Sweden",
		"Switzerland", "United_Kingdom", "United_States",
	}
	m.S.Cursor[state.ViewCountries] = 7
	t.Logf("\n%s\n", m.View())
}

func TestPreview_CountriesSearch(t *testing.T) {
	m := newTestModel(vpn.Status{State: vpn.StateDisconnected}, state.ViewCountries, 100, 28)
	m.S.Countries = []string{"Germany", "France", "Finland", "Iceland", "United_States", "United_Kingdom"}
	m.S.Search[state.ViewCountries] = "uni"
	m.S.SearchMode[state.ViewCountries] = true
	t.Logf("\n%s\n", m.View())
}

func TestPreview_CountriesEmpty(t *testing.T) {
	m := newTestModel(vpn.Status{State: vpn.StateDisconnected}, state.ViewCountries, 100, 28)
	m.S.Countries = []string{"Germany", "France"}
	m.S.Search[state.ViewCountries] = "xyz"
	m.S.SearchMode[state.ViewCountries] = true
	t.Logf("\n%s\n", m.View())
}
