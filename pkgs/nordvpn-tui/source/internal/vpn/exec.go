package vpn

import (
	"bytes"
	"context"
	"errors"
	"os/exec"
	"regexp"
	"strings"
)

// ansiRE matches CSI/OSC escape sequences produced by some nordvpn output paths.
var ansiRE = regexp.MustCompile(`\x1b\[[0-9;?]*[a-zA-Z]|\x1b\][^\x07]*\x07`)

func stripANSI(s string) string {
	return ansiRE.ReplaceAllString(s, "")
}

// run executes `nordvpn args...`, returns cleaned stdout or a typed error.
func run(ctx context.Context, args ...string) (string, error) {
	cmd := exec.CommandContext(ctx, "nordvpn", args...)
	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr
	err := cmd.Run()

	out := stripANSI(stdout.String())
	errOut := stripANSI(stderr.String())
	combined := out + "\n" + errOut

	if err != nil {
		if ctx.Err() == context.DeadlineExceeded {
			return out, ErrTimeout
		}
		if errors.Is(err, exec.ErrNotFound) {
			return "", ErrBinaryMissing
		}
		if classified := classifyError(combined); classified != nil {
			return out, classified
		}
		return out, &CLIError{
			Cmd:    strings.Join(args, " "),
			Stderr: errOut,
			Stdout: out,
			Err:    err,
		}
	}

	// Some nordvpn commands exit 0 but print an error sentence on stdout.
	if classified := classifyError(combined); classified != nil {
		return out, classified
	}
	return out, nil
}

func classifyError(s string) error {
	ls := strings.ToLower(s)
	switch {
	case strings.Contains(ls, "you are not logged in"):
		return ErrNotLoggedIn
	case strings.Contains(ls, "daemon is not running"),
		strings.Contains(ls, "cannot reach system daemon"),
		strings.Contains(ls, "socket is not available"):
		return ErrDaemonDown
	case strings.Contains(ls, "whoops! connection failed"),
		strings.Contains(ls, "the specified server is not available"):
		return ErrConnectFailed
	case strings.Contains(ls, "does not exist"),
		strings.Contains(ls, "we couldn't find"):
		return ErrUnknownServer
	}
	return nil
}
