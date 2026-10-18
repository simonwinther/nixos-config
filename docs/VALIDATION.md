# Validation record

Current reference: **2026-10-18**, including the newer Rust tools and dirty Hyprspace/Breakd working trees approved by Simon. Source provenance is in [current-reference.json](inventory/current-reference.json). The previous snapshot-only decision is superseded.

All work runs in an isolated checkout and Docker Nix store. No Home Manager activation, NixOS activation, desktop reload, host package installation, media writing or disk operation has been performed on the reference Arch laptop. The current phase permits package/environment builds and checks only. The earlier ISO is historical, stale output; it has not been rebuilt in this phase. Media and installation require Simon's explicit later approval.

## Current-source results

| Check | Result and scope |
| --- | --- |
| Reference inventory | All 260 explicit package names and versions still match the recorded inventory. Every package has an installation, service, replacement or exclusion decision. |
| Source coverage | The read-only audit accounts for all 119 top-level `.config` entries, 21 root dotfiles, 55 home commands and 67 development manifests in its documented search roots. No unresolved home commands, unreviewed additional source paths, or unexplained imported-source drift were found. New files are checked as well as previously recorded hashes; remaining reference paths have explicit private-state, backup, replacement or exclusion decisions. Coverage decisions do not prove state transfer or runtime acceptance. |
| Portable source | Shell/Lua/Python syntax, unique Stow targets, plugin locks and all 145 editor extension source pins pass. Additional mutable preferences are seeded only when absent. |
| Desktop behavior | All 15 isolated tests pass, including all 21 theme palettes, Matugen generation, wallpaper state, preference seeding (including existing dconf settings), bar persistence, screenshot cancellation/freezing and copy/save behavior. The transcode check creates an image, preserves its input, verifies the output/clipboard URI with fake tools, and rejects replacement of an existing output. No real display or clipboard is contacted. |
| Hyprland / Hyprspace | The exact pinned Hyprland 0.56.2 and current plugin build. The repeatable parser check reports `config ok` using the plugin and portable Lua configuration, without a display server. Current Rust launch helper tests pass. |
| Neovim | All 62 locked plugin sources and 37 parsers build. The startup check loads completion, LuaSnip and the native fuzzy library, discovers every parser, and parses Lua/Python/C/LaTeX/Typst samples. The 62 reference plugin worktrees match their locked commits with no tracked modifications. Rust-specific Neovim configuration/parsers were not enabled in the reference and have not been invented here. |
| Tmux | Pinned navigator/resurrect/continuum sources build. A private server passes startup, navigation binding, modified-key, session-save and pane-capture checks. Existing servers are untouched. |
| Current Rust helpers | Dictation: 48 tests; audio ducking: 16; wallpaper grid: 19; text picker: 9; formula plotter: 30; iPhone transfer: 19; static cluster agent: 9. All pass. File picker and workspace slider retain their previously built/tested sources. |
| Break reminders | The current Breakd working source builds with 169 passed tests and two upstream tests ignored. |
| VS Code / Cursor | All 145 recorded VSIX entries build (142 VS Code, three Cursor). Bundled native libraries are patched for NixOS. Home Manager declares their original version/platform directory names; application state and extension-internal downloads are separate. |
| User tools | Current native launchers and seven added Cargo locks are preserved. `uipro-cli` 2.2.3 builds from a committed npm dependency lock. Primary Zsh and independent Bash settings are portable Stow source. |

All five flake checks passed: `desktop-behavior`, `hyprland-config`, `portable-syntax`, `neovim-startup`, and `tmux-startup`. All 25 custom package outputs passed the aggregate build. These checks cover the captured current code; they do not establish physical-session or private-account acceptance.

## Complete environment and workflow checks

The static Rust cluster agent passes all 58 fake SSH/Slurm workflow tests under ordinary user permissions, including mirror safety, submission, logs, protocol path checks, remote cache reuse, and the newly captured fetch command. Downloads preserve local-only files and remote originals; dry runs preserve the destination. Fixture executable paths were adapted only in the disposable test copy. No real cluster connection or job submission occurred.

The complete current Home Manager environment built successfully, including the full application collection, SDKs and TeX. It was not activated. Compiler link priorities keep GCC as the default; Playwright has lower profile-link priority for SDK-root metadata shared with Flutter, while its command retains its own package contents.

A disposable home with **1,015 managed links** passed Bash completion/FZF startup, primary Zsh autosuggestion/highlighting and vi keymap startup, Python **3.14.7** imports (PyGObject, Pillow, NumPy, Matplotlib, Poetry core and TerminalTextEffects), Rust **1.98.1** / Cargo **1.98.0** compilation and execution of an offline sample, and C++ compilation/execution. `uipro` reports 2.2.3 and Ghostty's configuration validator passes. VS Code lists exactly the recorded 142 extension IDs/versions; Cursor lists its three. No editor account was restored or used for these tests.

The `rust-desktop` development shell passes toolchain and pkg-config discovery for GTK4, layer-shell, Wayland, PipeWire, ALSA, Fontconfig and FreeType, and finds the declared workspace-slider font. The packaged desktop tools discover both GNOME interface and Nautilus settings schemas outside GNOME. An additional SOPS runtime-file declaration evaluates to owner `simon`, mode `0600`, and the expected shell-secrets path using a public placeholder source; no decryption, private file provisioning or SOPS activation occurred.

Evidence is retained under `.work/`: `current-final-components.{json,log}`, `current-home-manager-v2.{json,log}`, `current-home-profile-smoke-v2.log`, `current-cluster-workflow-final.log`, `current-rust-devshell-v2.log`, `current-gsettings-schemas.log`, `current-sops-declaration.json`, and the final parity audit. These are local records, not backups.

Historical integration checks established the compiler wrapper priorities, PulseAudio client availability, GNOME settings schema discovery, MIME defaults, generated session launcher syntax, coherent compositor/plugin selection, private SOPS exclusion from live profiles, and installation guards. They remain relevant but are not substitutes for current package builds or physical-session testing.

## Reproducing configuration checks

From this checkout on an x86_64 Nix-capable Linux system:

```sh
nix build .#checks.x86_64-linux.desktop-behavior \
  .#checks.x86_64-linux.hyprland-config \
  .#checks.x86_64-linux.portable-syntax \
  .#checks.x86_64-linux.neovim-startup \
  .#checks.x86_64-linux.tmux-startup
nix build .#nixosConfigurations.desktop.config.home-manager.users.simon.home.activationPackage
```

Building an activation package does not run it. Do not run its activation script during this phase. Installed NixOS system outputs remain guarded until the desktop's actual hardware, disk and backups are reviewed. Do not use a broad build of every flake package: the reserved image output belongs to a later phase.

The builder uses the pinned Nix Docker image, two CPUs and 4 GiB RAM, with `/src` read-only, `.work/` writable, and the separate `nixos-config-store` volume. Large builds run sequentially at reduced scheduling priority. Evaluate the Home Manager derivation path first and build that derivation separately to release evaluation memory. Logs and output JSON under `.work/` are local evidence, not independent backups.

## Compatibility and state still requiring acceptance

- Nixpkgs application versions can differ from Arch; test real projects and copied databases before relying on compatibility. Rust 1.98.1 and Python 3.14.7 match the current reference toolchains.
- CppTools' external-console debugger mode retains upstream/Nixpkgs limitations around hard-coded terminal paths. Test the actual project `launch.json` and terminal selection. The bundled old F# runtime also needs a real language-server session; passing native dependency checks does not establish functional compatibility.
- Retain unavailable vendor sources and the 15 cached VSIX archives using [VENDOR-SOURCES.md](VENDOR-SOURCES.md). Marketplace availability, extra extension downloads, Flatpak commits and remote services are outside a local package build.
- Secrets, SSH/GPG identities, browser/keyring/VPN authentication, histories, databases, projects and container volumes are recorded for deliberate encrypted transfer or fresh login. They have not been copied into Git or the Nix store. Optional SOPS declarations provide private runtime file destinations, without collecting values.
- Recreate Python virtual environments and native project outputs from project locks. The development shell supplies common Rust desktop dependencies; it does not turn all personal projects into Nix derivations or rewrite Python source into Rust.

## Real-hardware acceptance (pending stationary desktop inventory)

- Boot UEFI USB, working TTY, correct keyboard, encryption unlock and emergency login.
- Correct GPU/driver, both rendering APIs, refresh rates, scaling, monitor placement, hotplug, lid behavior where relevant.
- `hyprctl configerrors` empty; overview/Alt-Tab and all personal Lua rules/bindings behave as on the reference.
- Bar geometry, workspace slider placement, fonts, tray icons, launcher theme/providers, terminal and editor appearance match reference screenshots.
- Theme switching across dark/light themes; wallpaper grid, next image, per-output restoration; no writes to managed links.
- Wi-Fi/Ethernet, DNS before/after VPN, Bluetooth, speakers/headphones/microphone, PipeWire sharing portals, printing and discovery.
- Lock on automatic login, manual/idle lock, suspend/resume, screen power, user password and independent recovery authentication.
- Dictation start/stop/cancel, microphone, terminal paste, ducking/restore, private key loading; no key/log leakage.
- File/PDF picker, drag/drop, browser native messaging/extensions, screenshot/OCR, recording start/stop with valid saved audio/video.
- Neovim completion/snippets, exact language projects, TeX builds, Typst preview, Java/Haskell/Flutter tooling, terminal prompt/vi bindings.
- NordVPN/Twingate/Tailscale login, Hendrix SSH/MFA, cluster jobs, iPhone send/receive, Docker volumes/DNS, LocalSend, mail, Flatpaks and game launchers.
- Independent backup and sample restore; tested older Nix generation and console/live USB recovery.

No visual parity, hardware support, real account workflow, installation, restore, or rollback has yet been claimed as verified.
