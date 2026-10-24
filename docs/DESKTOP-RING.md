# Desktop Ring

Rust control utility integrated into the existing NixOS / Home Manager desktop.
The daemon owns monitor layouts; the transient GTK4 + gtk4-layer-shell UI renders
an actual annular pie menu from a generic, recursive menu model. No extra audio,
Bluetooth, or desktop policy daemon is installed.

## Everyday use

- **Super + R**: open the universal ring on the monitor under the pointer. Press
  again to dismiss. Root categories: Displays, Audio Output, Microphone,
  Bluetooth, Volume Controls, System.
- **System → Sleep**: lock the session, then suspend to RAM. Waking requires the
  account password. The action checks logind's current capability and requires
  the running Hypridle service's sleep inhibitor; it refuses an unprotected
  suspend. The existing system menu's Sleep entry uses this same Rust backend.
  The ring closes before any privilege dialog needs keyboard input; authorization
  stays outside the daemon's event loop. Failures produce a desktop notification
  and remain in diagnostic state.
  Real suspend/resume still requires physical acceptance on each host.
- Move into a sector and left-click. Click the center, right-click, or press
  Backspace to go back. Escape closes. Tab / arrows select, Enter activates.
  More than eight entries are paginated into another circular submenu.
- Active devices / arrangements have an accent dot. Unavailable audio routes
  remain visible and disabled. Device names and explanatory status appear in
  the center when selected.
- Selecting an audio default or laptop arrangement applies it and closes the
  ring. Volume changes and Bluetooth operations stay open for repeated controls
  and progress / error feedback. Volumes change in 5% steps and are capped at 100%.
- **Super + Ctrl + Alt + M**: cycle Left → Right → Below on NixOS laptop hosts.
  The stationary intentionally has no layout cycling or laptop-position menu.
- Existing Super + / display-scale shortcuts now open the control ring. Direct
  scale and persisted internal-display toggles were competing layout writers;
  the legacy display entry point delegates to the manager when enabled. Lid
  events request reevaluation rather than disabling the panel.

## Desktop hardware

Physical identities were read from the running stationary and read-only laptop
reference. Connector names below describe the observation, never profile keys.

| Display | Serial | Mode | Desktop role |
| --- | --- | --- | --- |
| Microstep MSI MP273A | PB4HA75503387 | 1920×1080 @ 100 Hz | left, when reconnected |
| AOC 32G2WG3 | 0x00000568 | 1920×1080 @ 165 Hz | middle / left with two displays |
| Ancor Communications Inc VG248 | J5LMQS024117 | 1920×1080 @ 144 Hz | right, transform 3, portrait |

The recorded desktop arrangement is preserved: all top edges at y=0, scale 1.
With three displays the x positions are 0, 1920, 3840. With only the AOC and ASUS
they are 0 and 1920. Subset profiles keep the same order, modes and rotation
when any other display is unplugged, including the portrait ASUS alone.
The portrait display occupies 1080×1920 logical pixels.
The MSI has been reconnected to the stationary on HDMI-A-2. The full three-screen
profile was verified against the live compositor: all native modes, positions,
scales and portrait rotation match the declared layout. Waybar, workspace
overlays and wallpaper surfaces are present on all three outputs.
Only advertised modes are applied. A missing / incompatible member never causes
an arbitrary different display on the same port to inherit its profile.

## Declarative configuration

- `modules/home/desktop-ring.nix`: service, package, JSON configuration and
  Hyprland bindings. `desktop.ring.enable`, `menuKey`, `cycleKey`, and `settings`
  are Home Manager options. Module booleans: `monitors`, `laptop`, `audio`,
  `bluetooth`, `power`; `move_streams` defaults false.
- `hosts/<host>/monitor-profiles.json`: fixed named hardware sets. Each role
  has an identity (`make`, `model`, optional `serial` / EDID SHA-256), an explicit
  supported mode, scale, transform and logical x/y coordinates.
- `hosts/<host>/laptop-monitors.json`: optional physical-monitor mode / scale /
  rotation preferences, independent of the selectable laptop position. The
  observed home MSI retains 100 Hz. AI Pioneer identifiers are not fabricated.
- `hosts/<host>/monitors.lua`: only the safe catch-all startup fallback. Do not
  add competing connector-specific rules here. The old monitor-watch service
  has been replaced by `desktop-ring.service`.
- `~/.config/desktop/ring.json` and `ring-bindings.lua`: generated immutable
  configuration, managed by Home Manager.
- `~/.local/state/desktop-ring/preferences.json`: atomic runtime preferences,
  versioned and keyed by a SHA-256 of the connected physical identities. This
  is private user state and is not placed in Git or the Nix store. Preserve it
  when moving an existing laptop installation.
- The theme defaults to the existing desktop palette at menu-open time, read
  from `~/.local/state/desktop/theme/colors.toml`. Set
  `settings.theme.follow_desktop_palette = false` to use declarative
  background / foreground / accent colors instead. The main controls use drawn
  outline icons; other symbols use the configured fallback font (`icon_font`).
  Text font (`font`), logical radius and
  animation duration remain declarative. Defaults use Adwaita Sans / Symbols Nerd
  Font, a 214-pixel radius and 140 ms transitions. The charcoal gradients, thin
  sector borders, accent selection arc and deep backdrop keep labels readable
  over desktop content. Animation callbacks stop once opening / hover transitions finish.

A laptop with one internal panel and one external display offers Left / Right /
Below. Geometry accounts for transform and scale, centers the touching edges,
and restores the last selection for that particular hardware set. A single
internal panel retains the configured laptop scale (1.2 for lambda). Additional
complex arrangements can use explicit fixed profiles. Unknown external screens
use their advertised current / preferred mode. No location services are used.

## Cursor consistency

`desktop-settings/.config/desktop/interface.json` declares Adwaita at 24 pixels,
matching the reference laptop's default cursor inheritance. Home Manager owns
cursor assets, default-theme links, GTK settings, X11 resources and session
variables. Generated `desktop/cursor.lua` selects the XCursor backend in Hyprland
because Adwaita ships XCursor assets rather than a Hyprcursor manifest. The
session environment import also forwards cursor theme / search paths to services.
This prevents Hyprland's blue fallback cursor while keeping applications aligned.

## Identity and safety policy

Serial numbers are preferred, placeholder values rejected, and EDID SHA-256
used when no usable serial exists. EDID blocks must have valid checksums.
Connector collisions across GPUs do not produce guessed EDID associations.
Unique assignments are solved across all profile roles. A specific physical
profile wins over a generic model profile; equal matches are rejected. Two
indistinguishable serialless monitors preserve their current arrangement and
cannot overwrite another setup's saved position. Add unique EDIDs if available.

Unknown active displays retain their working settings. Disabled connected
outputs are re-enabled to the right with an advertised mode. Every planned mode,
transform and scale is validated before any write. The manager never emits a
disable rule, so it cannot intentionally turn every connected screen off.
Unchanged rules are skipped; explicit IPC rejection restores the previous
active rules and is not repeatedly retried for the same plan.

## Backends and lifecycle

- Hyprland: direct command socket and event socket; startup, hotplug and config
  reload trigger reconciliation. A new compositor instance can be rediscovered
  after EOF. logind `PrepareForSleep(false)` triggers reevaluation after resume.
- Audio: PipeWire's existing PulseAudio-compatible API via structured `pactl`
  JSON and its long-lived subscription. Rust invokes argument arrays directly;
  there is no shell parsing. WirePlumber remains the policy / persistence owner.
  Persistent device properties and node names are separate from temporary node
  indices. Input-monitor loopbacks are excluded. Optional existing application
  stream moves use fresh stream indices; they are off by default.
- Bluetooth: zbus talks directly to BlueZ ObjectManager, Adapter1 and Device1.
  Paired devices only; no background scanning or pairing agent. Signals update
  the model. Connect and default-audio selection are separate operations; a
  successful Bluetooth connection does not silently reroute sound. A missing
  adapter is reported without repeatedly trying to activate BlueZ.
- Idle: no discovery timer and no UI process while closed. Only disconnected
  backends use capped exponential reconnect backoff. Request / operation
  deadlines protect against stalled IPC; there are no startup sleep sequences.
- Sleep: the existing Hypridle service stays active for logind sleep/lock
  coordination. It releases the delay inhibitor only after Wayland lock
  notification (`inhibit_sleep = 3`), as described in the
  [Hypridle documentation](https://wiki.hypr.land/hypr-ecosystem/user/hypridle/).
  Automatic idle locking remains opt-in through the existing toggle; turning it
  off removes the idle listener without stopping sleep protection. No automatic
  suspend, hibernation, lid policy, or extra power daemon is added.
- Private control socket: `$XDG_RUNTIME_DIR/desktop-ring/control.sock`, containing
  directory mode 0700 and socket mode 0600. One daemon and any transient menu / CLI
  clients share snapshots. Slow device operations stay outside GTK's input loop.

Source: `dotfiles/desktop-ring/.local/share/desktop-ring/` with separate `core/`,
`ui/`, `monitors/`, `audio/`, `bluetooth/`, and `profiles/` modules. To extend it,
add a backend state / event / action and produce `Menu` / `Entry` values in the
menu-model builder. GTK rendering and navigation contain no subsystem-specific
commands. Recursive entries support arbitrary depth.

## Diagnostics and validation

`desktop-ring status` prints identities, modes, matched profile, selected
position, devices, current defaults and errors as JSON. `desktop-ring rescan`
reloads settings and reevaluates devices; changing module booleans requires a
service restart so watcher lifetimes match the new configuration. Use
`journalctl --user -u desktop-ring` for IPC / backend errors.

Build with `nix build .#desktop-ring`. Tests run during the Nix package build;
`nix develop .#rust-desktop` also supplies cargo / clippy / rustfmt. Flake checks
include `desktop-ring`, `ring-integration`, the real generated Lua bindings in
`hyprland-config`, and existing portable / desktop behavior checks.

Real stationary acceptance includes portrait placement / mode readback, audio
output and microphone selection, volume / mute round trips with original
settings restored, live subscription delivery, layer-shell display placement,
and keyboard selection / automatic dismissal. BlueZ API integration is tested
against a private D-Bus fixture because this stationary currently exposes no
Bluetooth adapter. The full three-monitor stationary hotplug has also been physically verified.
Laptop topology is covered by tests / observed identifiers; laptop hotplug and
suspend acceptance still require those real hardware sessions. The Arch reference is
never activated or modified.
