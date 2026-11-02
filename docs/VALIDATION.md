# Validation record

Current reference: **2026-10-18**, including the newer Rust tools and dirty Hyprspace/Breakd working trees approved by Simon. Source provenance is in [current-reference.json](inventory/current-reference.json). The previous snapshot-only decision is superseded.

Initial validation used an isolated checkout and Docker Nix store. Dated follow-ups record subsequent repository and package checks. The reference Arch configuration has not been activated or reloaded, and no host packages have been installed. On 2026-10-19 Simon approved building a fresh live image and preparing the Cruzer USB for the stationary desktop. Current media evidence belongs under `.work/usb-2026-10-19/`; the older ISO is historical output. Desktop installation and real-hardware acceptance remain pending.

## Current-source results

### Final source synchronization — 2026-10-28

The latest shared configuration and dotfiles commits were fast-forwarded before
applying the desktop improvements. The shared native clipboard picker and shell
reload fix are retained. The deployment manifest includes the clipboard package,
and Hyprspace uses the shared GitHub revision rather than a laptop-local path.

The combined Python suite passes **169 tests**, with **32 skipped** because the
optional native test binaries or terminal emulator are unavailable in this check.
All **16 shell tests** pass. Portable validation checks **227 scripts, 911 unique
text targets, 260 package decisions and 62 locked editor plugins**. Changed Nix
files pass formatting. The desktop Home Manager generation and Desktop Ring,
desktop-tools, transcode, project-picker and Hyprspace package derivations evaluate.
These are source and evaluation checks; they do not add a new environment build
or interactive desktop acceptance result. No private state was transferred and
installation readiness is unchanged. No configuration was activated or reloaded,
and no ISO or installation media was built. Local evidence is in
`.work/pre-push-*`.

### File-picker cache waits and shutdown — 2026-10-28

The file/PDF index feed now waits on Linux cache-file notifications, refresh
process handles, diagnostics and output-pipe closure. It retains the existing
30-second scan schedule and a 100 ms polling fallback when kernel facilities
are unavailable or a writer is still publishing its transaction. A nonblocking
SQLite writer-lock check prevents a WAL notification received before commit
from leaving the feed asleep with an old snapshot. Refresh diagnostics are
drained continuously, retained up to 16 KiB, and reported once on failure.

All **51 default-target Rust tests** pass, including watch replacement/loss,
unavailable process handles, large-error backpressure, concurrent commit
publication and prompt idle-reader shutdown. Formatting and Clippy with warnings
denied pass. The native Nix derivation evaluates successfully with the root lock;
a fresh release build with the GTK drag feature was not run in this final pass.

A controlled one-file fixture recorded **12 → 0 voluntary context switches**
over 1.2 seconds while the feed was idle. Both samples used less than one CPU
clock tick at the 10 ms accounting resolution. After its consumer closed, the
old reader remained live past the 1.5-second observation limit; the new reader
exited successfully in about **32 ms**, including observer overhead. This
measures the index feed, not whole-desktop CPU usage or GUI startup time.

The existing truncated-cache recovery test also failed against the captured
baseline: SQLite changed the original shared-memory sidecar before quarantine.
Rejecting nonempty files shorter than the 100-byte SQLite header before opening
SQLite preserves those bytes. The same recovery test passes with the fix.

Evidence and the unchanged baseline source/binary are under
`.work/file-picker-wait/`. The kernel interfaces are documented by
[poll](https://man7.org/linux/man-pages/man2/poll.2.html),
[inotify](https://man7.org/linux/man-pages/man7/inotify.7.html) and
[pidfd_open](https://man7.org/linux/man-pages/man2/pidfd_open.2.html); the minimum
header follows [SQLite's file format](https://sqlite.org/fileformat.html#the_database_header).

Source checks and disposable runtime fixtures are complete. Interactive desktop
acceptance remains separate. No private state was transferred, and installation
readiness is unchanged. No activation, reload, package installation, ISO build
or installation-media work was performed.

### Persistent native audio connection — 2026-10-28

Desktop Ring now uses one libpulse connection for discovery, actions and
subscriptions, replacing its subscription child and four short-lived `pactl`
processes per ordinary action. The worker has bounded request/connection waits,
reconnect backoff, cancellation, and joined shutdown on SIGINT/SIGTERM. Source
and dependency locks are in the portable desktop-ring package; Nix links
libpulseaudio and provides the private-server test dependencies.

The headless build passes all **37 tests**, including nine audio integration
tests against private PulseAudio sockets and null devices. They cover volume
limits, mute/default readback, monitor-source filtering, hotplug, server restart,
stalled setup/operations, shutdown, optional stream moves and native callback
ownership. The audio fixture uses no host audio or D-Bus connection. Its trap
and stable native client index verify no audio subprocesses and context reuse.

The complete GTK Nix package builds and passes all **40 release tests** (ten
library/geometry, nine audio, twenty behavior, one private BlueZ fixture). The
installed wrapper's help command loads successfully. Its output store path
matches evaluation of the current source with the root lock's nixpkgs/unstable
inputs through the same `callPackage` definition used by the flake. This package
check does not evaluate or build any system or ISO output.

A cancellation regression fails against the published libpulse-binding 2.30.1
source because its callback is never freed. The checked-in source patch makes
cancellation free it exactly once and protects an already completed callback
from a second free. Original dependency licenses and source provenance remain
beside it, and the same patch applies to Nix and portable builds.

Rust formatting and Clippy with warnings denied for Desktop Ring pass. The
vendored upstream binding retains three existing `noop_method_call` warnings;
they are outside the cancellation patch. Nix formatting passes. Portable source
validation passes 226 scripts, 904 unique text targets, all 260 package decisions
and 62 locked editor plugins.

Evidence is under `.work/audio-native/`, including the failing unpatched
regression, passing reviewed headless tests and final `package-patched.log`.
These are isolated source/package checks. Runtime acceptance against the actual
PipeWire/WirePlumber session and physical audio devices is still pending.

No private state was transferred. Installation readiness is unchanged: host
review and independent backup requirements still apply. No configuration was
activated or reloaded, no host packages were installed, and no installation
image or media was built.

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

## Desktop bar and native search — 2 November 2026

Individual packages built for the bar, search backend, Walker frontend, desktop
controller and standalone clipboard picker. The bar workspace and search Rust
tests passed, along with the packaged search integration check. Both desktop and
lambda Home Manager configurations evaluate with desktop-search replacing the
old provider service and Walker starting on demand. Portable unit rendering
preserves the same service dependency and startup policy.

Private Wayland acceptance covered the compact speaker, nested Escape and Back,
half-page movement, footer rendering, native image/text copying, paused
collection, protected pins and 120 rapid selections. The patched Walker rendered
applications, clipboard, calculator, symbols, tasks and repository views against
the new backend. Warm queries including CLI startup had a 7.6 ms median in this
fixture; animation duration is separate from that measurement.

The current desktop session uses runtime units and drop-ins. The installed user
configuration links retained their original targets and contents. The transfer
verified 100 clipboard payloads, including 43 images, before retiring the old
collector. Original state and a private migration backup remain available.
Subsequent checks verified the database, payload hashes, remaining imported
images against the backup, and the standalone picker's connection. Collection
continues to rotate unpinned entries at the configured 100-item limit. The actual
patched Walker executable was verified before leaving its service stopped for
on-demand use; the old provider compatibility unit has no resident process.

After warming application and history queries, a ten-second idle sample measured
6402 KiB PSS for search and 12592 KiB for the bar, totaling about 18.5 MiB. The
previous collector, resident Walker and bar totaled about 60.1 MiB PSS in the
baseline sample. Search recorded no CPU time during the final sample; the bar
used 0.1% of one core. These are session measurements, with the fallback frontend
closed, rather than a guarantee for every workload. Source conversion and this
runtime acceptance remain separate from full configuration activation and the
stationary desktop's hardware/install acceptance above.

Keyboard follow-up passed real-input checks in both Clean and Motion: plain
dashboard h/j/k/l navigation, explicit search with literal navigation letters,
immediate clipboard p preview, literal p while searching, and page-specific ?
help that restores selection, search focus and preview state. The new
Super+Ctrl+D dashboard toggle was exercised in the private compositor and
registered in the current session. Rendered help and preview views were visually
checked. The matching optimized package passed its workspace tests and replaced
only the running bar; the search backend kept its process and managed
configuration links retained their original contents and targets.

### Native menus and fuzzy search completion

Both Clean and Motion now use Morphing Notch Bar for the remaining launcher
modes, desktop menu lists and command-line selection dialogs. Home Manager
evaluation confirms that Walker is absent from packages, services and managed
configuration. Individual optimized bar, search and controller packages built
successfully; no full configuration activation was run.

Nucleo matching runs inside the Rust processes with reusable scratch storage.
The application catalog and Go menu both resolve `bluec` to Bluetooth controls.
A synthetic optimized benchmark matched and ranked 10,001 entries across 150
queries with a 2.055 ms median and 2.883 ms 95th percentile. This measures the
matching function, excluding process startup, provider work and animation; it
does not establish a universal comparison with other fuzzy finders.

Rust unit tests, controller routing, portable build wrappers, package manifests
and packaged backend integration passed. Optimized private Wayland checks passed
in both styles for fuzzy controls, files, commands, symbols, Unicode, web search,
repositories, tasks, calculator copy without dismissal, literal selection-dialog
responses, cancellation and the temporary native menu when the bar is hidden.
Keyboard regression covered dashboard navigation, contextual help and clipboard
preview. The clipboard collector also passed image and long-text copying, pause,
pin protection and 120 rapid selections at the 100-item retention limit.

The running session was updated through its existing runtime units and shortcut
bridge. All 100 current history entries retained their payload hashes and pins;
managed home links retained their targets and contents. The 22 direct native
menu shortcuts are registered, and neither Walker nor Elephant has a resident
process. After warming menus, a ten-second idle sample measured 13,801 KiB PSS
for the bar and 6,008 KiB for search, about 19.3 MiB combined. CPU usage was 0.1%
and 0% of one core respectively. These are current-session observations, separate
from persistent configuration activation and hardware acceptance.

### Clean placement and incremental development

Clean now keeps all ten workspace numbers visible and uses an icon for Wi-Fi.
Its native launcher, keybindings, notifications and clipboard use centered
overlay surfaces; drawing and pointer hit areas share that position. Private
Wayland acceptance covered both styles, native provider modes, fullscreen menu
visibility, keyboard dismissal and outside clicks. Rendered centered application
and clipboard views were inspected.

The development helper supplies the pinned Rust dependencies through Nix, then
uses an optimized incremental Cargo build in the user cache. It updates only a
temporary bar service override and preserves a service-owned clipboard before
restarting. Its first dependency build took 202 seconds; a warm recompilation
took 4.65 seconds. A subsequent source edit compiled in 24.02 seconds. Applying
the already-built program took 0.46 seconds of Cargo work, followed by the
service restart. The centered version is running through
this development override; the final Nix build and activation remain separate.

Clean's opening and closing morph between a small rounded square and the menu.
The earlier capsule seed was removed after it visibly lingered between openings.
Close and reopen now commit a painted frame immediately rather than waiting for
an unchanged surface's next frame callback. Clean closes once the remaining
geometry is within one pixel of the seed, avoiding a pause while springs settle.
Keyboard focus belongs to the visible menu; the backdrop only catches clicks.
Private keyboard acceptance checks Ctrl+K, Escape and Ctrl+K at four delays,
including an interrupted close, with the pointer over the menu, and verifies
navigation in the reopened menu. Live checks also verified shortcut opening,
Escape dismissal and reopening. All 54 Rust bar tests passed. Opening, closing
and reopening frames were visually checked. Motion retains its existing notch
dimensions and transition.

### Maintenance tracking and retired frontend cleanup

The root `LAST_UPDATED` covers 70 Nix and repository components. Portable dates
remain canonical in `dotfiles/LAST_UPDATED`, covering all 36 deployed packages
and the existing deployment and PDF-picker entries. Coverage, sorting and date
formats were checked. Recorded dates were retained; 15 pre-existing components
without reliable dates use `unknown`. Both instruction files define how future
changes maintain the trackers without treating a read or test as an update.

Unused first-party Walker and Elephant configuration, launcher wrappers,
templates, companion build patches and the obsolete layout check were removed.
Theme preparation no longer renders launcher views or creates their runtime
aliases. The standalone clipboard palette is now `clipboard.css`. History import,
wire compatibility tests and historical benchmark records remain available;
private history and backups were not changed.

Clipboard Ctrl+H/L now moves left/right, including from search, alongside
Ctrl+J/K. `/` and `i` enter clipboard search. Help and documentation reflect the
change. All 55 Rust bar tests and 122 relevant Python checks passed. Private
Wayland acceptance covered the control keys, literal search text, preview,
contextual help, rapid reopening and both bar styles. The bar update is live
through the development helper; source cleanup awaits the normal Nix build and
activation. The search service retained its process.

### Compact notch pointer targets — 2026-11-02

Motion retains its compact width, height and icon positions. Its status targets
span the full notch height and divide the gaps by the nearest control. The
outer control also gains six pixels of invisible padding. The hover tint was
removed after the visual trial; the resting appearance stays unchanged. Workspace
10 is labeled `0` in both styles while retaining its original destination.

All 57 current Rust bar tests passed. Private Wayland acceptance exercised real pointer
input at the top and bottom edges, the sound/Wi-Fi gap, the Wi-Fi/battery gap and
the battery's outer padding, with a tray present. Clicking `0` selected workspace
10. Resting, hover and expanded sound renders were visually checked. The bar
update is running through the development helper; no full system rebuild or
activation was performed for this change.

### Clipboard shortcut routing — 2026-11-02

The default Alt+V binding still launched the standalone GTK clipboard picker.
It now calls the native bar's clipboard menu directly. Keyboard acceptance loads
the actual portable binding file instead of substituting a test-only shortcut;
real Alt+V input opened the clipboard in Motion and in Clean over a fullscreen
window. The live binding was also updated and checked with a real key press,
without opening the standalone picker. The source correction is saved for the
next normal Nix configuration activation. The requested hover tint removal is
live through the bar development update; the wider hit targets remain.
