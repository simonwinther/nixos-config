# nordvpn-tui

A keyboard-first terminal UI for NordVPN on Linux. Wraps the official `nordvpn`
CLI and gives you the five things you actually do every day — see status, quick
connect, disconnect, pick a country/city, toggle core settings — on one clean,
focused screen.

## Runtime dependency

`nordvpn-tui` is a front-end for the official NordVPN client. It requires:

- The `nordvpn` CLI on `$PATH` (provided by the NordVPN Linux package)
- The `nordvpnd` daemon running (`systemctl start nordvpnd`)

Install the NordVPN Linux client first: https://nordvpn.com/download/linux/

## Install

### Arch Linux (AUR)

```
yay -S nordvpn-tui-bin
```

Or with any AUR helper, or manually:

```
git clone https://aur.archlinux.org/nordvpn-tui-bin.git
cd nordvpn-tui-bin
makepkg -si
```

### Debian / Ubuntu (.deb)

Download the `.deb` from the [latest GitHub Release][releases] and install:

```
sudo dpkg -i nordvpn-tui_<version>_amd64.deb
```

### Tarball (any Linux)

Download the tarball for your architecture from the [latest GitHub Release][releases],
extract, and place the binary on your `$PATH`:

```
tar xf nordvpn-tui_<version>_linux_amd64.tar.gz
sudo install -m755 nordvpn-tui /usr/local/bin/
```

### Build from source

Requires Go 1.22+.

```
git clone https://github.com/simonwa01/nordvpn-tui.git
cd nordvpn-tui
make build
./bin/nordvpn-tui
```

[releases]: https://github.com/simonwa01/nordvpn-tui/releases

## Demo mode

Run without the real daemon to try the UI:

```
./bin/nordvpn-tui --fake
```

## Keymap

| Key                   | Action                                      |
| --------------------- | ------------------------------------------- |
| `1` `2` `3`           | Home / Countries / Settings                 |
| `enter`               | Primary action in the current view          |
| `c`                   | Quick connect                               |
| `d`                   | Disconnect                                  |
| `/`                   | Search (inline, Countries / Servers)        |
| `↑` `↓` / `k` `j`    | Move cursor                                 |
| `→` `l`               | Open cities for the focused country         |
| `←` `h` / `esc`       | Back / clear search                         |
| `?`                   | Toggle help overlay                         |
| `L`                   | Open activity log                           |
| `q` / `ctrl-c`        | Quit                                        |

## Releases

Releases are created automatically by GitHub Actions when a semver tag is
pushed:

```
git tag v0.1.0
git push origin v0.1.0
```

GoReleaser produces:
- Linux `amd64` and `arm64` tarballs
- A `.deb` package
- SHA-256 checksums
- AUR `nordvpn-tui-bin` update (if `AUR_SSH_PRIVATE_KEY` secret is set)

To build a local snapshot without publishing:

```
make snapshot
```

## Manual test matrix

- [ ] Disconnected start — Home shows "Disconnected", primary CTA is Quick Connect.
- [ ] `c` connects and the hero flips to "Connected" with country/city/IP.
- [ ] `2` enters Countries; `/` filters; `enter` connects to a country.
- [ ] `→` opens cities for the focused country; `enter` connects to city.
- [ ] `3` enters Settings; toggling each bool updates its row; Technology cycles NordLynx/OpenVPN.
- [ ] Kill Switch toggle shows a confirm prompt; `n` cancels, `y` applies.
- [ ] `d` disconnects; Kill Switch warning is surfaced when relevant.
- [ ] Logged-out: Home shows login CTA pointing at `nordvpn login`.
- [ ] Daemon down: full-screen banner with systemctl hint.
- [ ] Binary missing: full-screen banner on startup.
- [ ] Resize to 80×24, 100×30, 140×40 — no layout breakage.
- [ ] `NO_COLOR=1` and `TERM=xterm` — still legible.

## Architecture

```
UI (Bubble Tea)  ↔  Store (pure reducers)  ↔  VPN service (exec wrapper)
                                                    │
                                                    ▼
                                               `nordvpn` CLI
```

- `internal/vpn/`   — CLI wrapper, parsers, typed errors, fake client.
- `internal/state/` — single `AppState` struct, no ad-hoc mutation.
- `internal/app/`   — Bubble Tea root model, messages, key dispatch, router.
- `internal/theme/` — palette and named Lip Gloss styles.
- `internal/views/` — per-view render functions, each pure.

Parsers live in one place. The UI never inspects raw CLI output.

## License

MIT — see [LICENSE](LICENSE).
