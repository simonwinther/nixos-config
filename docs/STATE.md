# Configuration and state ownership

| Material | Fresh system source | Restoration/update |
| --- | --- | --- |
| Hyprland, terminals, bars, launchers, scripts, themes, wallpapers | Stow files linked by Home Manager | Edit repository, rebuild; Stow on other distributions |
| Monitor/GPU/disk configuration | Host modules after hardware review | Separate configuration per machine |
| VS Code/Cursor preferences and bindings | Imported plain files under `dotfiles/code` | Declarative; edit source to change on NixOS |
| Editor extensions | Inventory of 142 VS Code and 3 Cursor extensions | Restore private extension directories or reinstall from recorded IDs/versions; native helpers need Nix-compatible runtimes |
| Breakd preferences | Redacted `default.toml` | Seeded once into writable `config.toml`; interactive changes remain application state; room credential is provisioned separately |
| Theme, wallpaper, file-backed gaps/input/display choices | Declared defaults | Writable XDG state, retained across configuration rebuilds |
| Browser/1Password/mail/VPN/Canvas authentication | None | Fresh login or deliberate encrypted private transfer |
| Browser extensions | Plain source under `.local/share/browser-extensions` | Load unpacked; verify IDs and native-messaging permissions |
| Browser, mail, game, Flatpak and application databases | Desktop backup / selected laptop transfer | Restore with apps stopped, compare versions before opening |
| Projects, documents, mail archives, photos, phone files | Independent encrypted backup | Restore preserving metadata and verify samples |
| Container data and databases | Application-consistent dumps/volume backups | Restore volumes and test DNS/network isolation |
| Password hash, API keys, recovery keys | Private runtime files or optional SOPS | Never plaintext in Git/Nix store; independent recovery copy |

The system, packages, service definitions, and portable configuration are declarative. User data and interactive application state have separate lifecycles. Rebuilding NixOS does not restore a deleted database, reset Breakd's interactive preferences, or reinstall a retired marketplace/Flatpak artifact. Preserve those artifacts in the encrypted transfer backup until the new desktop is accepted.

The reference worktree changed during preparation. The latest special-workspace visibility setting and tmux modified-Enter settings were carried into this repository. Original files and backups were left untouched. `inventory/reference.json` records the initial snapshot and subsequent imported preferences; this is provenance, not a backup of private application state.

Canvas MCP clients can launch the packaged `canvas-mcp-server` in its default stdio mode and supply private Canvas settings themselves. The optional, manually started `canvas-mcp.service` uses HTTP on `127.0.0.1:8819` and only starts when `~/.config/canvas-mcp/http-environment` exists. That file needs the Canvas URL and HTTP access-key settings described in the [server source documentation](../pkgs/canvas-mcp/source/README.md); its HTTP mode rejects a server-side `CANVAS_API_TOKEN`, because clients supply their own Canvas token. Do not reuse a stdio environment file for HTTP. No Canvas connection or authenticated operation was made during preparation.

Further uncommitted changes appeared in the original dotfiles after the inspected snapshot: a Rust wallpaper-grid replacement, a Rust audio-duck helper, a new text picker, and related launchers/documentation. They were left untouched and are listed, with observed hashes, in [reference-drift.json](inventory/reference-drift.json). The user confirmed retaining the inspected implementations and listing these later changes separately. The replacements need a separate resnapshot and their own packaging/validation before inclusion.
