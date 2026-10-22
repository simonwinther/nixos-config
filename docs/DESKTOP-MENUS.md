# Desktop menus, appearance and clipboard

Open the desktop menu with **Super + Alt + Space**, the power menu with **Super + Escape**, and clipboard history with **Super + Ctrl + V**. Apps, Learn, Trigger, Style, Setup, About and System retain the familiar organization. Escape returns from a submenu to its parent; opening a submenu directly makes Escape close it. Install, Remove and Update are absent. Packages and system updates remain part of the Nix configuration.

## Appearance

**Style → Theme** selects any of the 21 captured palettes or generates a palette from an image with Matugen. The selected palette applies to the launcher, notifications, lock screen, terminal imports, and bar accents. Existing personal wallpapers remain available in **Background**, including the wallpaper grid. A theme change keeps the chosen wallpaper; changing colors does not silently replace a per-monitor background.

Ghostty initially retains SimonDark/SimonLight and follows the system's light/dark mode, matching the personal reference configuration. Selecting a desktop theme enables its terminal palette. **Style → Terminal colors → Personal light/dark colors** restores the personal Ghostty colors; **Follow desktop theme** enables the palette again. Kitty and Alacritty receive complete generated palette imports, including for themes that only supplied colors rather than terminal-specific files.

**Style → Font** lists installed monospace families. The choice applies to Ghostty, Kitty, Alacritty, Walker, Mako, SwayOSD, Waybar text, Hyprlock and Fontconfig's monospace alias. It persists across session preparation and rebuilds. The workspace slider's own bundled font and application-specific fonts remain their existing preferences. Font/theme reloads are requested on the target when using these controls; a terminal can still require reopening for some font changes.

**Style → Lock screen** chooses a separate background, restores following the wallpaper, or locks immediately. If the chosen image disappears, locking falls back to the wallpaper. The reference menu's “Unlock” edits Arch Plymouth's disk-unlock artwork; it is not a desktop setting. This menu provides Hyprlock controls instead. Boot and disk-unlock appearance belong to the declarative boot configuration and are not changed by a desktop theme selection.

**Style → Screensaver** retains the Naruto and Tomoe Sharingan artwork and offers Matrix or editable custom text. Start runs the selected artwork in a fullscreen Ghostty window on the focused output, using TerminalTextEffects at 30 fps. A key or loss of focus exits the artwork animation. This is a manually started visual; idle locking remains controlled separately. It does not lock the session or replace Hyprlock. Multi-output replication and image-to-text artwork conversion are not implemented.

**Setup → Desktop controls** opens the existing Rust Desktop Ring for displays, audio, Bluetooth and power; Super + R remains its direct shortcut. System-menu Sleep uses its guarded suspend action and the existing Hypridle sleep coordinator. Configuration entries open editable repository source under `$DOTFILES`, including the host's monitor file. Rebuild the target after editing declarative configuration. Power profiles and hardware tools use the installed native services. Learn links to the local desktop guide, keybindings, and relevant upstream manuals. The desktop's declared bar and terminal size multipliers are preserved; scaled light-bar CSS keeps its imported base rules.

## Clipboard

**Super + Ctrl + V**, **Trigger → Clipboard**, and `desktopctl clipboard` open the same dedicated history view. It has an opaque theme background, selected-row cards, timestamps, pinned markers, and a separate scrollable text/image preview. Long URLs wrap; the original copied content is unchanged. The list summary flattens whitespace, and file entries retain their filenames. Narrow or scaled outputs use a stacked layout; sizing uses the focused output's logical dimensions.

| Key | Action |
| --- | --- |
| Enter | Copy selected item and close |
| Ctrl + Y | Copy and keep the picker open |
| Ctrl + P | Pin/unpin |
| Ctrl + D | Remove an unpinned item |
| Ctrl + I | Cycle available text/image/pinned filters |
| Ctrl + O | Edit selected content |
| Ctrl + Shift + P | Pause/resume collection |
| Alt + J | Show available actions |
| Escape | Close |

The existing patched Rust Walker renders the UI; Elephant remains the only history collector. There is no additional resident clipboard service or rewrite with a second database. The history limit remains 100, with pinned items protected from eviction; explicitly pinning more than 100 items is an exception to that limit. OCR stays off. Symbols are retained, and pinned entries appear first. A local native patch enforces trimming after a burst of copies and uses unique, mode-0600 image files so rapid copies cannot overwrite each other's originals. The existing history format remains compatible. These changes are not a measured memory or latency benchmark.

The `$` prefix inside the general app launcher continues to search clipboard history with its general launcher layout. The dedicated shortcut above uses the improved, monitor-sized layout.

## State and verification

Theme/font choices, custom screensaver text and lock-screen background choices live under `$XDG_STATE_HOME/desktop` (normally `~/.local/state/desktop`). Walker's generated themes and bar/lock configurations live under `$XDG_RUNTIME_DIR/desktop`. Home Manager owns the portable source files. Menu actions do not edit the Nix store or perform package installation, system activation, or repository updates.

Clipboard history is private runtime state, normally `~/.cache/elephant/clipboard.gob` and `~/.cache/elephant/clipboardimages/`. The collector stores that history on the target; this task does not read or import the laptop's existing history. If retaining it is desired, transfer both together through the private-state backup process with the collector stopped. Do not put them in Git or a Nix derivation.

`desktop-behavior` checks menu navigation/cancellation, all terminal palettes, font persistence, lock-background fallbacks and scaled clipboard sizing without accessing a real display or clipboard. The Elephant package runs native regression tests for trimming and image retention. `walker-layout` renders the actual GTK templates with synthetic history in a disposable X display, checks CSS and geometry, and emits preview PNGs. Physical Wayland focus, real clipboard copy/edit/filter actions, terminal reloads, screensaver interaction and multi-monitor appearance still require target-session acceptance. No live image, activation or installation is part of these checks.
