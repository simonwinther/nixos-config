package vpn

import "testing"

func TestParseList_Countries(t *testing.T) {
	got := ParseList(readFixture(t, "countries.txt"))
	if len(got) < 5 {
		t.Fatalf("expected several countries, got %d", len(got))
	}
	wantPresent := map[string]bool{
		"Afghanistan":    true,
		"United_States":  true,
		"United_Kingdom": true,
		"Germany":        true,
	}
	for _, c := range got {
		delete(wantPresent, c)
	}
	if len(wantPresent) != 0 {
		t.Errorf("missing countries: %v", wantPresent)
	}
}

func TestParseList_CitiesWithCommas(t *testing.T) {
	raw := "New_York, Los_Angeles, Chicago\nDallas, Seattle\n"
	got := ParseList(raw)
	want := []string{"New_York", "Los_Angeles", "Chicago", "Dallas", "Seattle"}
	if len(got) != len(want) {
		t.Fatalf("got %v, want %v", got, want)
	}
}

func TestParseList_Dedup(t *testing.T) {
	raw := "Germany\nGermany\nFrance\n"
	got := ParseList(raw)
	if len(got) != 2 {
		t.Errorf("dedupe failed: %v", got)
	}
}

func TestDisplayArgRoundtrip(t *testing.T) {
	cases := map[string]string{
		"United_States": "United States",
		"Germany":       "Germany",
	}
	for in, disp := range cases {
		if got := Display(in); got != disp {
			t.Errorf("Display(%q)=%q want %q", in, got, disp)
		}
		if got := Arg(disp); got != in {
			t.Errorf("Arg(%q)=%q want %q", disp, got, in)
		}
	}
}
