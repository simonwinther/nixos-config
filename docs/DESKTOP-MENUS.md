# Morphing Notch Bar, desktop menus and clipboard

Open the desktop menu with **Super + Alt + Space**, the power menu with **Super + Escape**, clipboard history with **Alt + V**, and screenshots with **Super + Q**. Print Screen also remains available. Apps, Learn, Trigger, Style, Setup, About and System retain the familiar organization. Escape returns from a submenu to its parent; opening a submenu directly makes Escape close it. Install, Remove and Update are absent. Packages and system updates remain part of the Nix configuration.

**Super + K** and **Learn → Keybindings** list described bindings from Hyprland's active `hyprctl -j binds` response, including generated Desktop Ring shortcuts and applied overrides. Lua keycodes missing from JSON are recovered from the compositor's `hyprctl binds` output. Undescribed events such as lid switches are omitted. Release and long-press triggers and submaps are labeled; keycodes and mouse bindings retain their Hyprland names. Opening or selecting a row only displays the shortcuts.

Both Clean and Motion use the native Rust **Morphing Notch Bar** menu surface.
Walker is absent from the package set and user services. Menu shortcuts enter the
Rust executable directly on NixOS, avoiding Python startup on opening. The launcher includes
desktop controls as well as installed apps: `bluec` finds Bluetooth controls with
Nucleo fuzzy matching. The Go menu searches controls too. Large catalogs and
provider queries run away from rendering; one pending query replaces obsolete
work without accumulating a queue.

Clean opens these menus at the center of the focused output, above fullscreen
applications, morphing from a small rounded square into the full menu. Reopening
during a close reverses the transition immediately. Its workspace group always
shows 1–9 and 0; Wi-Fi uses an icon with connection details in the tooltip. Motion
keeps menus attached to the notch.

Launcher prefixes: `/` modes, `.` files, `:` symbols, `=` calculator, `@` web,
`>` commands, `$` clipboard and `gh ` repositories. Unicode and tasks are also
available from modes. Ctrl+O opens the selected item's actions and provider
controls; Ctrl+Y activates while keeping the picker open. Selection dialogs used
by command-line tools also render here. With the bar stopped or hidden, a
transient native process opens only the requested menu and exits on dismissal.

## Fast local development

Use `python3 scripts/desktop-bar-dev.py apply` from this checkout while changing
the Rust bar. Nix supplies the pinned compiler and libraries, while Cargo builds
incrementally into the user cache. The development profile keeps optimizations
and skips whole-program link optimization. The first build prepares dependencies;
later edits reuse them. Applying restarts only the bar through a temporary user
service override. Managed home links and the search service stay in place.

The same command accepts `check`, `test`, `build` and `preview`. Preview opens an
additional bar without replacing the running one. `restore` removes only the
development override and returns to the packaged service. A failed development
startup also falls back to that service. Service-owned clipboard content is moved
to an independent owner before a restart.

Batch normal Nix package and configuration verification after a group of changes.
The development command does not build the system or activate a configuration.
Restore the packaged service after the approved final activation; the override
otherwise lasts until logout or reboot.

## Appearance

**Style → Theme** selects any of the 21 captured palettes or generates a palette from an image with Matugen. The selected palette applies to the launcher, notifications, lock screen, terminal imports, and bar accents. Theme changes select a matching wallpaper from the theme's `backgrounds` folder or its shared `wallpapers/<theme>` library, including nested folders. TokyoLED starts with the configured default wallpaper. A wallpaper already chosen from the selected theme stays selected; themes without images keep the current wallpaper. Existing personal wallpapers remain available in **Background**, including the wallpaper grid.

Ghostty initially retains SimonDark/SimonLight and follows the system's light/dark mode, matching the personal reference configuration. Selecting a desktop theme enables its terminal palette. **Style → Terminal colors → Personal light/dark** restores the personal Ghostty colors; **Follow desktop theme** enables the palette again. Kitty and Alacritty receive complete generated palette imports, including for themes that only supplied colors rather than terminal-specific files.

Theme changes signal running Ghostty and Kitty instances, including Nix-wrapped processes, and immediately update Neovim's Catppuccin light/dark appearance without waiting for focus. The bar, launcher, notifications and volume display refresh through their existing services. On NixOS, the desktop helper's packaged entry point supplies the tools and GSettings schemas for menu actions as well as service launches.

**Style → Font** lists installed monospace families. The choice applies to Ghostty, Kitty, Alacritty, Mako, SwayOSD, desktop bar text, Hyprlock and Fontconfig's monospace alias. It persists across session preparation and rebuilds. The integrated workspace labels use the selected desktop font; application-specific fonts remain their existing preferences. Font/theme reloads are requested on the target when using these controls; a terminal can still require reopening for some font changes.

**Style → Bar style** switches the Rust desktop bar between **Clean** and **Motion**. The same process renders the workspace slider and tray on every selected output, including the minimal clock where configured. Changing styles signals that process for a live reload. `desktopctl bar next` cycles the two styles. The choice persists in desktop state; theme, font, scale, light mode, and hidden-bar preferences apply to both styles. Retired layout selections fall back to Clean.

Motion uses a compact top-center notch, with numbered workspaces on the left, a clock, quick sound control, Wi-Fi signal and battery, followed by a separator and active system-tray icons. Each monitor shows only its current workspace and occupied local workspaces. General hover or **Super+Ctrl+D** opens the Controls dashboard; the shortcut toggles it closed. Its footer shows CPU, memory and home-filesystem storage usage. A media row appears below the controls when a real track is available, with artwork, track/artist and previous/play/next controls. Paused tracks remain available to resume; no empty player card is shown. Playback follows MPRIS players as they appear, change tracks and disappear, and the dashboard morphs as the row appears or disappears. Artwork downloads and decoding are bounded, cached privately and run off the rendering thread.

Sound, battery and Wi-Fi have direct hover panels. The compact speaker opens output and microphone volume sliders; Sound in the dashboard opens the full mixer. The dashboard gives access to apps, clipboard, themes, wallpapers, sound, Bluetooth, desktop settings and power controls. Tray icons retain their application actions and context menus. A short dwell avoids opening panels while passing across icons. Leaving a hover panel springs it closed without taking keyboard focus. The same persistent surface stays attached to the monitor’s top edge, preserving spring velocity while expanding, collapsing or changing panels.

Workspace 10 is labeled **0** in both styles. Motion keeps its compact resting size;
status targets span its full height and the gaps belong to the nearest control.
Hovering preserves the compact bar's resting appearance.

Background data invalidates only the views that display it. Hidden CPU, memory and audio levels do not repaint the compact notch or static catalogs, and its static urgent-workspace marker does not keep an animation loop running. Visible dashboard metrics and status panels continue refreshing. Read-only catalog, thumbnail and artwork helpers have output limits and deadlines; changing providers or preview selection cancels obsolete catalog and thumbnail commands, including their child processes. Image reads and decoded PNG dimensions are bounded before allocating previews.

The closing morph uses the current workspace strip, tray, clock and status values. Updates while a menu is open invalidate its compact snapshot without repainting the hidden notch; opening and closing frames refresh it when visible. Changes during closing retarget the existing springs rather than jumping to an outdated width.

Tray, media and network workers subscribe to the bus signals they use. Playback position and seek-only changes do not refetch track metadata. Media queries and playback actions have a three-second total deadline; network status queries are also bounded. Track changes cancel obsolete artwork helpers so the current cover can load immediately. Wi-Fi status clears when its service disappears and refreshes when it returns. The tray reconnects after a failed connection or disconnect, preserving its current icon color and discarding actions queued during the outage.

Native notification, Bluetooth, Wi-Fi and audio discovery queries have a three-second total deadline and cancel when their panel is replaced. Pairing and authentication actions retain their longer response window. The audio event listener retries a stalled initial connection rather than waiting indefinitely. Opening the system monitor focuses an existing instance or launches it through the independent application scope.

Applications preload on an independent worker and reopen immediately from the in-memory catalog. After one minute, the previous results remain visible during refresh. Icon discovery checks existing search directories once per scan. Static menus such as Go and Style read the shared JSON directly in Rust, preserving item order and literal command arguments; menus that query live system settings still use the controller.

Volume and mute commands share an ordered worker. Consecutive pending slider values for the same device collapse to the newest value; wheel steps, mute toggles and changes between devices retain their order.
Native audio controls apply the same rule independently to each consecutive slider burst, including bursts after another control or action. Panel generations and non-volume actions remain ordering barriers.

The application catalog, browser and terminal launchers, and custom focus-or-launch commands use independent app scopes so a bar restart leaves their applications running. The launcher prefers UWSM and falls back to a user systemd scope; explicitly scoped commands retain their existing wrapper. Ctrl+Space or Super+Space opens the application launcher; Tab moves between apps, themes, wallpapers, clipboard, controls and bar styles. Ctrl+J/K and arrows navigate while search retains focus; Ctrl+D/U move half a page. The dashboard opens in navigation mode: h/j/k/l move across its tiles, while /, Ctrl+L or clicking search enters text input. Escape leaves search without changing the filter. Keyboard hints are omitted from the footer. Press ? for a compact help view containing only the current page's controls; Escape or ? returns with its state intact. Theme and wallpaper cards show previews. Continuous touchpad movement accumulates before advancing, wheel steps use one event resolution, and stop frames do not navigate. Escape returns through nested panels with their search and selection intact, then closes at the root. An outside click dismisses the whole panel and releases focus.

Super+K opens searchable keybindings and Super+N opens current and historical Mako notifications inside the notch. Enter invokes an active notification; expired notifications open their text. Delete dismisses an active notification. Super+Ctrl+A opens native audio controls with playback, recording, outputs, inputs and profiles. Sliders and Left/Right adjust levels, Enter toggles mute, and Ctrl+Enter chooses a default output or input. Super+Ctrl+B opens Bluetooth devices, radio and discovery controls. Super+Ctrl+W opens Wi-Fi networks, radio and scanning. Authentication and pairing requests use the same surface; passwords remain in memory. Device data refreshes only while its panel is visible, and actions run off the rendering thread.

Static desktop menus, installed fonts, configuration choices, hardware, power profiles and reminder entry open within both styles. Reminder entry accepts minutes followed by the message. Actions that open an application, editor or file chooser retain their application flow. Clean uses the same native menus, including its clipboard grid and device controls.

Super+Ctrl+Alt+Space opens the bar style chooser in either style. Super+Alt+Space retains the main menu and its Style submenu inside Motion. Extra named actions can be declared in `~/.config/desktop/bar-actions.json` using desktopctl argument lists. Native panels can also be opened through `desktopctl bar panel NAME`. The unused Super+Alt+Period snippet shortcut and its wrapper have been removed.

Weather settings live in `~/.config/desktop/weather.json`; the credential remains in `~/.owm-key`. The weather shortcut calls `desktopctl weather`, which prints a reading through the same Rust application.

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
| Style | Theme, font, bar style, background, Hyprland appearance, lock screen, screensaver and About artwork |
| Setup | Desktop controls, native devices, power profile, monitor/input/bindings, defaults and configuration |
| System | Screensaver, lock, guarded sleep, log out, restart and shut down |

LocalSend still requires choosing a recipient in its UI. Clipboard exports use unique mode-0600 files under the user runtime directory and remain until logout so GUI handoff cannot invalidate a pending transfer. File selection uses the chooser rather than scanning the entire home directory. No share action was executed against real user data during validation.

Install/Remove/Update and their submenus stay absent. Arch DNS/security provisioning, boot and sudo mutation, and imperative hibernation setup are omitted. Boot-unlock artwork remains separate from desktop styling. Direct monitor scale cycling/mirroring is replaced by explicit host configuration and Desktop Ring's supported controls; entries do not promise unsupported toggle actions. Webcam picture-in-picture recording remains unported because the current backend has no validated overlay integration. These differences remain visible here rather than being described as exact parity.

The Spotify focus-or-launch shortcut accepts its original one-argument form and matches window class/title without case sensitivity. Input-device discovery is bounded to avoid configuration-reload stalls, and prepared file/PDF picker workspaces stay out of the overview. These restore reference behavior without adding background daemons.

## Clipboard

**Alt+V**, **Trigger → Clipboard**, and the Clipboard tab open the native
four-column history grid in both styles. Motion expands the notch; Clean opens
at the screen center. The grid starts focused, so p previews immediately. `/`,
`i`, or clicking search enters text input; Escape returns to the grid. Plain
h/j/k/l and p remain searchable while editing.

| Key | Action |
| --- | --- |
| h/j/k/l or Ctrl+H/J/K/L | Left, down a row, up a row, right |
| Ctrl+D / Ctrl+U | Half a page down / up |
| Ctrl+Tab / Ctrl+Shift+Tab | Next / previous clipboard category |
| Tab / Shift+Tab | Next / previous menu page |
| Space | Select items in order |
| p / Ctrl+Space | Toggle full text or image preview |
| Enter | Paste selected items into the original window |
| Ctrl+Enter | Copy selection |
| Ctrl+Shift+Enter | Copy selected images as file links |
| Ctrl+A / Ctrl+Shift+A | Select filtered items / clear selection |
| Ctrl+P / Delete | Pin or unpin / remove an unpinned item |
| Ctrl+R | Refresh history |
| Ctrl+I / Ctrl+T | Filter images / text |
| ? | Show this page's bindings |

Control navigation also works from search and returns focus to the grid.
Ctrl+L moves right in the clipboard grid; `/` and `i` enter search.

The bar and standalone GTK picker share the Rust history and guarded paste
backend. The standalone picker remains available for direct use, with its own
[documented bindings](../dotfiles/clipboard-picker/README.md). Its palette is
`theme/clipboard.css`; it requires no launcher templates or legacy frontend.

The native desktop-search service collects history directly from Wayland. Full
payloads stay in private files, bounded previews keep catalog memory predictable,
and thumbnails preserve the entire image. Decoded previews are released on
close. The default history limit is 100 entries, with pinned items protected
from eviction. OCR stays off and password-manager hints are ignored.

Batch paste waits for copying to succeed and the picker to release focus. It
checks the original destination before each item, uses Ctrl+Shift+V for terminals
and Ctrl+V for other apps, and stops if focus changes. If the target changed, the
item remains copied. Super+V continues to paste normally. Image exports use
private cache files so history eviction cannot invalidate a file-list copy.

SQLite transactions serialize history changes. Selection order is assigned
before transfers finish, so a slow source cannot reorder newer selections.
Capture, query cancellation, pause/resume and subscriptions share the same
backend; no second collector runs alongside it. The `$` launcher prefix also
searches clipboard history.

## State and verification

The native panels share the same menu definitions. `DESKTOP_MENUS_FILE` can select an alternate JSON file for a session preview while the installed `~/.config/desktop/menus.json` remains managed by Home Manager.

Theme/font choices, custom screensaver/About artwork and lock-screen background choices live under `$XDG_STATE_HOME/desktop` (normally `~/.local/state/desktop`). Complete appearance generations live in its `theme-generations/` directory. The `theme/` and Fontconfig paths point into the current generation; bar/lock launch configurations live under `$XDG_RUNTIME_DIR/desktop`. Home Manager owns the portable source files. Menu actions do not edit the Nix store or perform package installation, system activation, or repository updates.

Theme preparation shares the state lock with preference changes. It fingerprints the palette, optional theme files, font, terminal-color preference and generator source, and verifies cached output before reuse. Unchanged launches skip rendering and writes. Changed inputs render privately before one pointer switch publishes all files together; failed rendering preserves the previous generation and preference choices. Runtime bar configuration is restored after logout without rerendering. Completed generations remain available for readers that resolve the theme path once before opening multiple files.

The lock worker reads only the selected lock-screen appearance and embeds it in its runtime configuration, so login and suspend locking do not require desktop theme preparation. Missing or invalid appearance state falls back to built-in colors and the configured default font, with a diagnostic on stderr. Hyprlock startup and exit failures still report failure.

Recording commands serialize start and stop. The controller verifies the recorder's boot, process start time, owner, executable and exact command before interrupting it through a [Linux process handle](https://docs.python.org/3/library/signal.html#signal.pidfd_send_signal). Stop waits up to 30 seconds for process exit before clearing `recording.json`; a timeout retains that state, and selecting a recording entry again waits without sending another interrupt. Recorder output and session metadata remain private under `$XDG_STATE_HOME/desktop/recordings/`, including failed starts and abandoned sessions. Legacy PID-only or mismatched state refuses signals and stays available for inspection. A stopped process still requires target-session validation of the saved audio/video.

Clipboard history and original payloads are private runtime state under `$XDG_STATE_HOME/desktop-search`, normally `~/.local/state/desktop-search`. Directories use mode 0700 and files use mode 0600. The explicit `import-elephant` operation transfers old text, images, pins, saved calculations and tasks while retaining the old state and a private backup. Verify payloads before retiring the old collector. Reference-laptop state transfer remains a separate operation. Never put history or backups in Git or a Nix derivation.

`desktop-behavior` checks menu navigation/cancellation, terminal palettes, font persistence, login/suspend lock failure paths, lock-background fallbacks and scaled clipboard sizing. The desktop-search package and integration check exercise storage, pins, transfer limits, both wire encodings, provider actions, import and persistence with private fixtures. The bar's private Wayland harness checks nested navigation, quick audio controls, half-page movement, native clipboard copying, fuzzy launcher controls, provider actions and command-line selection dialogs. Physical login/suspend behavior, terminal reloads, screensaver interaction and multi-monitor appearance still require target-session acceptance. These checks do not activate or install a system.
