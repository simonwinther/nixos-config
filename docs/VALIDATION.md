# Validation record

Current reference: **2026-10-18**, including the newer Rust tools and dirty Hyprspace/Breakd working trees approved by Simon. Source provenance is in [current-reference.json](inventory/current-reference.json). The previous snapshot-only decision is superseded.

All builds run in an isolated checkout and Docker Nix store. The reference Arch configuration has not been activated or reloaded, and no host packages have been installed. On 2026-10-19 Simon approved building a fresh live image and preparing the Cruzer USB for the stationary desktop. Current media evidence belongs under `.work/usb-2026-10-19/`; the older ISO is historical output. Desktop installation and real-hardware acceptance remain pending.

## Current-source results

### GitHub synchronization and Hyprspace spaces — 2026-10-27

The configuration and dotfiles histories now include the latest shared `main`
and `master` changes alongside the local native clipboard picker, capture
shortcuts and password-manager removal. The native picker remains the Alt+V
action. The newer cached file picker and lambda host configuration are retained.
Both repositories were pushed to their shared default and `clipboard-shortcuts`
branches without rewriting history.

Hyprspace is pinned to upstream main commit
`4de74c8d5e3156b945319a76709e63e695aaddd7`, including independent spaces and the
newer controls. All 184 vendored files match that revision byte for byte;
[source.json](../pkgs/hyprspace/source.json) records the import. Existing workspace
exclusions and native Rust launcher fixes are present in the newer upstream code.
The root lock changed only the Hyprspace input; the compositor revision is retained.

Validation of source commit `40bc981` passes `desktop-behavior` (81 Python and
18 browser tests), `portable-syntax` (197 scripts, 808 unique text targets,
260 package decisions and 62 locked editor plugins), `file-picker-integration`,
and `hyprland-config` (`config ok` with the packaged plugin).
The matching Hyprland and Hyprspace 1.8.0 packages build successfully, alongside
the native clipboard picker. Hyprspace's existing C++ model suite reports
840,929 checks with zero failures; its Rust launch helper passes both tests.
The plugin output is `/nix/store/y3c5bci48a7qb8ym74v9rdcb7650mrh9-hyprspace-1.8.0`.
The imported file-picker package and runtime wrapper build, with all 33 native
tests passing. The weather helper now reads the portable desktop theme marker through
`XDG_STATE_HOME`; its package and tests pass. Changed Nix integration files pass
the pinned formatter, and no compiled output or cache is committed.

Runtime acceptance remains separate: this task has not activated a configuration
or loaded the new plugin into a running session. No private state was transferred.
Installation readiness is unchanged; no ISO, installation media or installation
was built or performed. Local build evidence is under `.work/sync-checks.*` and
`.work/hyprspace-unit-tests.log`.

### SQLite-cached Ratatui file picker — 2026-10-24

The shared file/PDF picker now loads cached metadata from SQLite and refreshes
changed, added and removed paths in the background. Both shortcuts use floating
Ratatui windows on the current workspace. One windowless Ghostty host replaces
the two prepared windows and their reserved special workspaces. The Nix package
supplies SQLite and all runtime helpers; Home Manager keeps ownership of links.

The locked Nix package builds with drag support and passes all 33 release tests
(25 library/TUI/index, six index CLI, two terminal-startup tests). Formatting and
Clippy with warnings denied also pass. `file-picker-integration` tests the installed
wrapper with an otherwise empty program path, verifies SQLite integrity, cache
updates/removals/renames and PDF scope isolation, and checks the rendered portable
unit. It also asserts the single startup service for both desktop and lambda.
`portable-syntax` passes 196 scripts, 793 unique text targets, all 260 package
decisions and 62 locked editor plugins. The pinned Hyprland/plugin parser reports
`config ok` for the complete staged configuration. Its generated command bindings
retain their exact Lua text without requiring unrelated executable builds.

Evidence is retained under `.work/file-picker-port/`. These are isolated source,
package and configuration checks. No configuration was activated or reloaded,
no host packages were installed and no installation media was built. Actual
NixOS session focus, clipboard and drag behavior still require runtime acceptance.

### OBS settings restoration — 2026-10-23

The OBS task worktree captures the stationary desktop's preserved configuration,
including all five scenes, six audio filters, output profile, countdown and both
backgrounds. Scene properties match the original after path/portal conversion;
the images and Lua script match byte for byte. See [OBS.md](OBS.md).

The OBS 32.2.2 package and original Bookman font build with the locked inputs.
Eight isolated migration checks pass, including credentials, private backups,
preservation of UI edits across Nix-store/portable source locations, and refusal
to overwrite a running OBS or managed links. Native desktop validation verifies
all 97 profile parameters, seven scene-item transforms, both audio inputs and
all six filter settings in order. The three private screen-sharing grants were
converted from compact IDs to the UUID format required by portal 1.20.4; all
three captures negotiate 1920 × 1080. A muted countdown recording passes H.264
1920 × 1080 at 60 fps and AAC 48 kHz stereo inspection. No stream was started.

The complete desktop Home Manager environment also builds without activation.
Only the OBS runtime files, launcher, font and private grants were restored on
the stationary desktop. Its previous OBS configuration has a private backup.
The reference laptop, other application configuration and installation media
were not activated or changed. Evidence is retained in the OBS worktree's
`.work/obs-check.*`, `.work/home-manager*` and `.work/runtime-verified.json`.

### Complete submenu audit — 2026-10-22

The followup compares every reference menu definition against the NixOS port. Install/Remove/Update stay absent; the resulting behavior and deliberate differences are listed in [DESKTOP-MENUS.md](DESKTOP-MENUS.md). Clipboard/file/folder sharing, visible reminder messages, About artwork, screensaver image/reset/automatic controls, declarative defaults and missing configuration entries are restored. Hardware menus omit absent touchpads and describe the supported display controls accurately. The Spotify focus shortcut, bounded input-only udev lookup and picker-workspace exclusions match the reference. No background service was added.

- All **46** isolated behavior tests pass, including real ImageMagick conversion of a synthetic transparent logo, private clipboard-export fixtures, visible reminder state, launch/focus and automatic-saver lock/duplicate guards.
- `walker-layout` renders **21 menu views and five clipboard cases**. Every static submenu and the dynamic Theme/Font/Configuration/Power profile views pass GTK CSS/geometry checks. The menu list labels use the same ellipsis behavior as Walker's native dmenu labels. Screenshots were visually inspected; long recording/appearance labels were shortened for readability. Hardware/font inputs are fixtures, not a physical-session capture.
- `portable-syntax` still passes 172 scripts, 745 text targets and 260 package decisions; pinned Hyprland reports `config ok`. The updated desktop-tools package and complete desktop Home Manager environment build without running activation.
- A disposable pseudo-terminal runs the actual Matrix worker with a fake Hyprland response. Both keypress and focus-loss exit pass; no real compositor is contacted.

Evidence is in `.work/build/submenu-final-checks.{json,log}`, `submenu-{behavior,layout,syntax,hyprland}.log`, `submenu-home-manager*` and `screensaver-smoke.log`; inspected renders are under `.work/qa-submenus/`. This audit did not read private clipboard data, send files, reload the laptop, activate the configuration or build installation media. Real stationary-PC focus/input, capture/recording, service integration, hardware sleep and resource usage remain acceptance tests. Boot-unlock artwork, webcam overlays and multi-output screensaver replication remain unported; defaults and monitor configuration use declarative source edits.

### Menu and clipboard followup — 2026-10-22

The `feat/nixos-menus-theme-clipboard` worktree adds the menu organization, appearance controls and clipboard changes described in [DESKTOP-MENUS.md](DESKTOP-MENUS.md), layered on `027f1fa` and its integrated Rust Desktop Ring, monitor profiles, scaling and sleep coordination. All edits stayed in this task's own worktree; the other worktrees were untouched.

- The patched Walker 2.17.0 and Elephant 2.22.0 packages build. Walker's two launch-context tests and Elephant's two new clipboard regressions pass. The latter cover burst trimming, pinned-entry retention, distinct image files and mode-0600 image permissions.
- `desktop-behavior` passes all **37** isolated tests, including Matugen integration, menu navigation/cancellation, arbitrary-input rejection, every terminal palette, font persistence, lock-background fallback, scaled clipboard sizing and imported light-bar CSS scaling. The existing capture/transcode, sleep coordination and Hendrix tests also pass.
- `portable-syntax` passes with 172 scripts, 745 unique text targets, all 260 package decisions and all locked editor sources. `hyprland-config` reports `config ok` with the pinned compositor/plugin and a disposable home. `ring-integration` also passes with the combined configuration.
- `walker-layout` passes six GTK render cases: the menu; dark clipboard text and image previews; stacked clipboard at 880 and 480 logical pixels; and the light clipboard palette. CSS parses and the requested window dimensions hold. Its Nix output contains preview PNGs. The minimal display has no accessibility-bus service; that test-session warning is not a target accessibility assessment.
- Packaged Ghostty 1.3.1 accepts the initial personal configuration and all **21** generated palette configurations in a disposable Stow home. The actual scaled Ghostty configuration from the combined Home Manager generation also validates with personal colors and the desktop light palette.
- The actual packaged Walker connects to an isolated Elephant fixture provider, renders the custom text preview and wraps a long URL. The native check exposed and corrected Walker's cancellation of fixed wrapper dimensions when scroll min/max flags are also provided. Its final preview is 1000 × 520 on a disposable 1280 × 800 X display. Upstream Wayland-layer-shell calls emit warnings in this X-only smoke test; it does not establish Wayland focus/input acceptance.
- The complete desktop Home Manager environment builds successfully with the combined controls, templates, scaling, sleep integration and patched native packages. Its activation script was not run. Evaluation and build were separated to release evaluation memory.

Evidence is under this worktree's `.work/build/`: `components.{json,log}`, `terminal-check.log`, `native-smoke.log`, `native-{walker,elephant}.log`, `native-clipboard.png`, `integrated-checks.{json,log}`, `integrated-home-manager-eval.log`, `integrated-home-manager.{json,log}` and `integrated-ghostty.log`. Extracted GTK renders are in `.work/qa-integrated/`. All history entries are synthetic; the reference clipboard and desktop services were untouched. Real Wayland copy/edit/filter actions, terminal reloads, screensaver interaction and multi-monitor appearance remain target-session checks. This worktree performed no ISO build, activation, private-state transfer or installation.

### Recorded baseline

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

Building an activation package does not run it. Do not run its activation script on the reference laptop. Installed NixOS system outputs remain guarded until the desktop's actual hardware, disk and backups are reviewed. The live image is built separately as `.#desktop-iso` for the approved USB preparation phase.

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
