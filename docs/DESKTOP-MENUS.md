# Desktop menus, appearance and clipboard

Open the desktop menu with **Super + Alt + Space**, the power menu with **Super + Escape**, clipboard history with **Alt + V**, and screenshots with **Super + Q**. Print Screen also remains available. Apps, Learn, Trigger, Style, Setup, About and System retain the familiar organization. Escape returns from a submenu to its parent; opening a submenu directly makes Escape close it. Install, Remove and Update are absent. Packages and system updates remain part of the Nix configuration.

**Super + K** and **Learn → Keybindings** list described bindings from Hyprland's active `hyprctl -j binds` response, including generated Desktop Ring shortcuts and applied overrides. Lua keycodes missing from JSON are recovered from the compositor's `hyprctl binds` output. Undescribed events such as lid switches are omitted. Release and long-press triggers and submaps are labeled; keycodes and mouse bindings retain their Hyprland names. Opening or selecting a row only displays the shortcuts.

## Appearance

**Style → Theme** selects any of the 21 captured palettes or generates a palette from an image with Matugen. The selected palette applies to the launcher, notifications, lock screen, terminal imports, and bar accents. Existing personal wallpapers remain available in **Background**, including the wallpaper grid. A theme change keeps the chosen wallpaper; changing colors does not silently replace a per-monitor background.

Ghostty initially retains SimonDark/SimonLight and follows the system's light/dark mode, matching the personal reference configuration. Selecting a desktop theme enables its terminal palette. **Style → Terminal colors → Personal light/dark** restores the personal Ghostty colors; **Follow desktop theme** enables the palette again. Kitty and Alacritty receive complete generated palette imports, including for themes that only supplied colors rather than terminal-specific files.

**Style → Font** lists installed monospace families. The choice applies to Ghostty, Kitty, Alacritty, Walker, Mako, SwayOSD, Waybar text, Hyprlock and Fontconfig's monospace alias. It persists across session preparation and rebuilds. The workspace slider's own bundled font and application-specific fonts remain their existing preferences. Font/theme reloads are requested on the target when using these controls; a terminal can still require reopening for some font changes.

**Style → Lock screen** chooses a separate background, restores following the wallpaper, or locks immediately. If the chosen image disappears, locking falls back to the wallpaper. The reference menu's “Unlock” edits Arch Plymouth's disk-unlock artwork; it is not a desktop setting. This menu provides Hyprlock controls instead. Boot and disk-unlock appearance belong to the declarative boot configuration and are not changed by a desktop theme selection.

**Style → Screensaver** retains Naruto and Tomoe Sharingan, Matrix, editable text, image-to-Braille conversion and Restore default. Start runs the selected artwork in a fullscreen Ghostty window on the focused output; TerminalTextEffects runs at 30 fps. Both artwork and Matrix use the same key/focus exit worker. The captured automatic-screensaver preference starts disabled. Enable it in this submenu or **Trigger → Toggle** to start the visual after 150 seconds of inactivity, using the existing Hypridle service. It skips a locked session or an existing screensaver. Idle locking remains a separate opt-in setting; when enabled, the existing 152-second lock still follows. The screensaver does not replace Hyprlock. Multi-output replication is not implemented.

**Style → About** customizes the system information artwork: edit text, convert an image, restore the NixOS logo, or preview. The main **About** entry still opens system information. Both artwork converters preserve the original image and store private, bounded text in desktop state.

**Setup → Desktop controls** opens the existing Rust Desktop Ring for displays, audio, Bluetooth and power; Super + R remains its direct shortcut. System-menu Sleep uses its guarded suspend action and the existing Hypridle sleep coordinator. Configuration entries open editable repository source under `$DOTFILES`, including the host's monitor file, full Hyprland configuration, SwayOSD and XCompose. **Setup → Defaults** opens the browser/editor launcher settings, terminal preference list or MIME handlers. These are declarative source edits, followed by a target rebuild; shell session defaults are separately declared in `modules/home/default.nix`. Power profiles and hardware tools use the installed native services. Learn links to the local desktop guide, keybindings, and relevant upstream manuals. The desktop's declared bar and terminal size multipliers are preserved; scaled light-bar CSS keeps its imported base rules.

## Submenu audit

All reference menu definitions were compared read-only with the port; the supplied screenshots establish the main/Style/clipboard appearance. The GTK layout check renders every static submenu plus Theme, Font, Configuration and Power profile with disposable hardware/font fixtures, so the target menus can be inspected without changing the laptop.

| Reference workflow | NixOS behavior |
| --- | --- |
| Learn | Keybindings, local guide and upstream manuals; NixOS replaces Arch links |
| Trigger / Reminder | Set, show messages and remaining minutes, clear; visible notification feedback |
| Capture / Screenrecord | Screenshot, region/window/output, edit, OCR, color; recording with desktop and microphone audio or without audio |
| Share | Clipboard text/image, file or folder through LocalSend, plus existing iPhone actions |
| Toggle | Screensaver, night light, idle lock, notifications, bar, layout, gaps and window ratio; monitor settings open editable source |
| Hardware | Desktop Ring display controls and native audio/network/Bluetooth tools; touchpad shown only when detected |
| Style | Theme, font, background, Hyprland appearance, lock screen, screensaver and About artwork |
| Setup | Desktop controls, native devices, power profile, monitor/input/bindings, defaults and configuration |
| System | Screensaver, lock, guarded sleep, log out, restart and shut down |

LocalSend still requires choosing a recipient in its UI. Clipboard exports use unique mode-0600 files under the user runtime directory and remain until logout so GUI handoff cannot invalidate a pending transfer. File selection uses the chooser rather than scanning the entire home directory. No share action was executed against real user data during validation.

Install/Remove/Update and their submenus stay absent. Arch DNS/security provisioning, boot and sudo mutation, and imperative hibernation setup are omitted. Boot-unlock artwork remains separate from desktop styling. Direct monitor scale cycling/mirroring is replaced by explicit host configuration and Desktop Ring's supported controls; entries do not promise unsupported toggle actions. Webcam picture-in-picture recording remains unported because the current backend has no validated overlay integration. These differences remain visible here rather than being described as exact parity.

The Spotify focus-or-launch shortcut accepts its original one-argument form and matches window class/title without case sensitivity. Input-device discovery is bounded to avoid configuration-reload stalls, and prepared file/PDF picker workspaces stay out of the overview. These restore reference behavior without adding background daemons.

## Clipboard

**Alt + V**, **Trigger → Clipboard**, and `desktopctl clipboard` open the same dedicated history view. It has an opaque theme background, selected-row cards, timestamps, pinned markers, and a separate scrollable text/image preview. Long URLs wrap; the original copied content is unchanged. The list summary flattens whitespace, and file entries retain their filenames. Narrow or scaled outputs use a stacked layout; sizing uses the focused output's logical dimensions.

| Key | Action |
| --- | --- |
| Enter | Copy selected item, close, and paste into the originating app |
| Ctrl + Enter | Copy selected item and close without pasting |
| Ctrl + Y | Copy and keep the picker open |
| Ctrl + P | Pin/unpin |
| Ctrl + D / Ctrl + U | Page down / up |
| Delete | Remove an unpinned item |
| Ctrl + I | Cycle available text/image/pinned filters |
| Ctrl + O | Edit selected content |
| Ctrl + Shift + P | Pause/resume collection |
| Alt + J | Show available actions |
| Escape | Close |

Autopaste waits for the clipboard copy to succeed and for Walker to release focus. It uses Ctrl + Shift + V for terminals and Ctrl + V for other apps. If the originating window is no longer active, it leaves the item copied without sending keys. Super + V continues to paste normally.

The existing patched Rust Walker renders the UI; Elephant remains the only history collector. There is no additional resident clipboard service or rewrite with a second database. The history limit remains 100, with pinned items protected from eviction; explicitly pinning more than 100 items is an exception to that limit. OCR stays off. Symbols are retained, and pinned entries appear first. A local native patch enforces trimming after a burst of copies and uses unique, mode-0600 image files so rapid copies cannot overwrite each other's originals. The existing history format remains compatible. These changes are not a measured memory or latency benchmark.

History saves reuse the lock already held by pin, unpin and delete actions. Collection coalesces pending save notifications without blocking while holding that lock. This prevents a running collector from becoming unresponsive and leaving Walker's history view blank.

The `$` prefix inside the general app launcher continues to search clipboard history with its general launcher layout. The dedicated shortcut above uses the improved, monitor-sized layout.

## State and verification

Theme/font choices, custom screensaver/About artwork and lock-screen background choices live under `$XDG_STATE_HOME/desktop` (normally `~/.local/state/desktop`). Complete appearance generations live in its `theme-generations/` directory. The existing `theme/`, Fontconfig and runtime Walker paths point into the current generation; bar/lock launch configurations live under `$XDG_RUNTIME_DIR/desktop`. Home Manager owns the portable source files. Menu actions do not edit the Nix store or perform package installation, system activation, or repository updates.

Theme preparation shares the state lock with preference changes. It fingerprints the palette, optional theme files, font, terminal-color preference, Walker templates and generator source, and verifies cached output before reuse. Unchanged launches skip rendering and writes. Changed inputs render privately before one pointer switch publishes all files together; failed rendering preserves the previous generation and preference choices. Runtime Walker links are restored after logout without rerendering. Completed generations remain available for readers that resolve the theme path once before opening multiple files.

The lock worker reads only the selected lock-screen appearance and embeds it in its runtime configuration, so login and suspend locking do not require desktop theme preparation. Missing or invalid appearance state falls back to built-in colors and the configured default font, with a diagnostic on stderr. Hyprlock startup and exit failures still report failure.

Recording commands serialize start and stop. The controller verifies the recorder's boot, process start time, owner, executable and exact command before interrupting it through a [Linux process handle](https://docs.python.org/3/library/signal.html#signal.pidfd_send_signal). Stop waits up to 30 seconds for process exit before clearing `recording.json`; a timeout retains that state, and selecting a recording entry again waits without sending another interrupt. Recorder output and session metadata remain private under `$XDG_STATE_HOME/desktop/recordings/`, including failed starts and abandoned sessions. Legacy PID-only or mismatched state refuses signals and stays available for inspection. A stopped process still requires target-session validation of the saved audio/video.

Clipboard history is private runtime state, normally `~/.cache/elephant/clipboard.gob` and `~/.cache/elephant/clipboardimages/`. The collector stores that history on the target; this task does not read or import the laptop's existing history. If retaining it is desired, transfer both together through the private-state backup process with the collector stopped. Do not put them in Git or a Nix derivation.

`desktop-behavior` checks menu navigation/cancellation, all terminal palettes, font persistence, login/suspend lock failure paths, lock-background fallbacks and scaled clipboard sizing without accessing a real display or clipboard. The Elephant package runs native regression tests for trimming, image retention, copy/paste ordering and history locking. `walker-layout` renders the actual GTK templates with synthetic history in a disposable X display, checks CSS and geometry, and emits preview PNGs. Physical login/suspend lock confirmation, Wayland focus, real clipboard copy/edit/filter actions, terminal reloads, screensaver interaction and multi-monitor appearance still require target-session acceptance. No live image, activation or installation is part of these checks.
