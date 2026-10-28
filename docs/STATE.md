# Configuration and state ownership

| Material | Fresh system source | Restoration/update |
| --- | --- | --- |
| Hyprland, terminals, bars, launchers, scripts, themes, wallpapers | Stow files linked by Home Manager | Edit repository, rebuild; Stow on other distributions |
| Monitor/GPU/disk configuration | Host modules after hardware review | Separate configuration per machine |
| VS Code/Cursor preferences and bindings | Imported plain files under `dotfiles/code` | Declarative; edit source to change on NixOS |
| Editor extensions | Hash-pinned sources for all 142 VS Code and 3 Cursor extensions, linked by Home Manager | Nix patches bundled native helpers; extension databases, authentication, downloaded runtimes and workspace state remain separate. Retain cached VSIX archives before migration. |
| Other application preferences | Plain terminal/viewer settings plus seed defaults for htop, Fcitx5, Wiremix, Lazydocker, Cliamp, Gnuplot, GitHub CLI, Cppman, Kdenlive, Qalculate, Pinta, and Xournal++ | Immutable portable settings live in Stow; mutable defaults are copied only when absent and never overwrite interactive settings |
| Breakd preferences | Redacted `default.toml` | Seeded once into writable `config.toml`; interactive changes remain application state; room credential is provisioned separately |
| Theme, wallpaper, file-backed gaps/input/display choices | Declared defaults | Writable XDG state, retained across configuration rebuilds |
| Font, personal/desktop terminal colors, lock-screen background and custom screensaver/About artwork | Portable defaults and captured artwork | Writable desktop state; controls and scope in [DESKTOP-MENUS.md](DESKTOP-MENUS.md) |
| Clipboard history and images | Empty on a fresh system | Elephant runtime cache; optional private transfer, never Git/Nix-store source |
| Browser/1Password/mail/VPN/Canvas authentication | None | Fresh login or deliberate encrypted private transfer |
| Browser extensions | Plain source under `.local/share/browser-extensions` | Load unpacked; verify IDs and native-messaging permissions |
| Browser, mail, game, Flatpak and application databases | Desktop backup / selected laptop transfer | Restore with apps stopped, compare versions before opening |
| Projects, documents, mail archives, photos, phone files | Independent encrypted backup | Restore preserving metadata and verify samples |
| Container data and databases | Application-consistent dumps/volume backups | Restore volumes and test DNS/network isolation |
| Password hash, API keys, recovery keys | Private runtime files or optional SOPS | Never plaintext in Git/Nix store; independent recovery copy |

The system, packages, service definitions, and portable configuration are declarative. User data and interactive application state have separate lifecycles. Rebuilding NixOS does not restore a deleted database, reset Breakd's interactive preferences, or reinstall a retired marketplace/Flatpak artifact. Preserve those artifacts in the encrypted transfer backup until the new desktop is accepted.

`desktopctl` validates `${XDG_STATE_HOME:-~/.local/state}/desktop/state.json` before using it. Schema version 1 retains the flat object shared with the Rust wallpaper picker and adds `"schemaVersion": 1`. Unversioned files and explicit version 0 migrate under the shared `state.lock`; all valid preferences and unknown extension fields survive. A missing file uses defaults without creating `state.json`. Newer schema versions produce an actionable error and are left unchanged by the coordinator.

| State fields | Schema constraints |
| --- | --- |
| `theme` | Lowercase letters, digits, underscores and hyphens, starting with a letter or digit |
| `font`, `wallpaper`, `lockBackground` | Nonempty strings without control characters |
| `terminalTheme`, `desktopTheme`, `aboutArt` | JSON booleans |
| `screensaver` | `naruto`, `tomoe-sharingan`, `matrix` or `custom` |
| `wallpapers` | Object mapping nonempty output names (including `*`) to nonempty image paths, without control characters |

When state is malformed or violates this schema, the coordinator first saves the exact original bytes in a mode-600 `state.json.invalid-*.json` file beside it. It then atomically publishes recovered state, retaining valid fields and valid per-output wallpaper entries; rejected choices fall back to existing defaults. Diagnostics go to stderr with the state path and failing field or JSON line/column, without printing saved preference values. Invalid UTF-8, duplicate keys, non-finite numbers and excessive nesting are rejected too. Recovery copies are private runtime state, never Git or Nix-store material. I/O failures and state symlinks produce errors instead of silently resetting preferences. Configuration JSON gets diagnostics but is never recovered or rewritten. The schema and migrations live in [desktopctl.py](../dotfiles/desktop-tools/.local/share/desktop-tools/desktopctl.py), with isolated regression coverage in [test_desktop_state.py](../tests/test_desktop_state.py).

The reference worktree changed during preparation. The latest special-workspace visibility setting and tmux modified-Enter settings were carried into this repository. Original files and backups were left untouched. `inventory/reference.json` records the initial snapshot and subsequent imported preferences; this is provenance, not a backup of private application state.

Canvas MCP clients can launch the packaged `canvas-mcp-server` in its default stdio mode and supply private Canvas settings themselves. The optional, manually started `canvas-mcp.service` uses HTTP on `127.0.0.1:8819` and only starts when `~/.config/canvas-mcp/http-environment` exists. That file needs the Canvas URL and HTTP access-key settings described in the [server source documentation](../pkgs/canvas-mcp/source/README.md); its HTTP mode rejects a server-side `CANVAS_API_TOKEN`, because clients supply their own Canvas token. Do not reuse a stdio environment file for HTTP. No Canvas connection or authenticated operation was made during preparation.

The original snapshot and [reference-drift.json](inventory/reference-drift.json) remain historical provenance. On 2026-10-18 Simon superseded the snapshot-only decision and approved including the current setup and newer Rust changes. [current-reference.json](inventory/current-reference.json) records the new source captures and dependency locks. These include Rust wallpaper grid, audio ducking, text picker, plotting, cluster tools, iPhone transfer, updated dictation, and the uncommitted Hyprspace and Breakd source changes. Source import is separate from successful package builds and interactive acceptance; consult the current validation results.

On 2026-10-19 Simon approved building the current live image and preparing the Cruzer USB for testing on the stationary desktop. This supersedes the previous pause on media preparation. Installation remains dependent on the desktop's reviewed hardware, independent backups and selected disk. The earlier image is historical output; see [LIVE-USB.md](LIVE-USB.md) for the current medium.

`scripts/audit-parity.py` compares the reference with the recorded captures and inventories configuration locations, home commands, development manifests, and private-state locations. Write its output under `.work/` or other private storage. It does not read credential contents or copy projects/databases. A config directory having some managed files is partial evidence, not proof that the entire application has been migrated. Every remaining source/runtime/state gap must be accounted for before claiming one-to-one parity.

The metadata audit also accounts for root shell dotfiles and every observed top-level `.config` entry in [home-state-map.json](inventory/home-state-map.json). Bash defaults are independent portable source alongside the primary Zsh configuration. The user-installed `uipro-cli` 2.2.3 is packaged with an npm dependency lock; other recorded local commands are mapped in [user-tools.json](inventory/user-tools.json). The audit found 67 development manifests in the documented search roots. Those projects are backup/restore material, not copies embedded in this configuration. Existing Arch virtual environments and compiled project outputs may need recreation on NixOS.

Nautilus folder-view and zoom choices are declared from the reference in `desktop/applications.json`. Portable preparation seeds only unset dconf values once; Home Manager declares the same values. The source audit also compares new files against [reference-path-decisions.json](inventory/reference-path-decisions.json), so a newly added Rust module or plugin cannot silently escape the captured-hash comparison. Account/conversation directories and history are handled as private state without reading their contents.
