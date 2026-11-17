package vpn

import "testing"

func TestParseAccount(t *testing.T) {
	a := ParseAccount(readFixture(t, "account.txt"))
	if !a.LoggedIn {
		t.Fatalf("expected logged-in")
	}
	if a.Email != "demo@example.com" {
		t.Errorf("email = %q", a.Email)
	}
	if a.Subscription == "" {
		t.Errorf("subscription should be set")
	}
}

func TestClassifyErrors(t *testing.T) {
	cases := map[string]error{
		"You are not logged in.":               ErrNotLoggedIn,
		"Daemon is not running. Please start.": ErrDaemonDown,
		"Whoops! Connection failed.":           ErrConnectFailed,
		"The specified server does not exist.": ErrUnknownServer,
		"something else entirely":              nil,
	}
	for in, want := range cases {
		if got := classifyError(in); got != want {
			t.Errorf("classifyError(%q)=%v want %v", in, got, want)
		}
	}
}
