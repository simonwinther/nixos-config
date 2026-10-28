# Using the Stow tree without Nix

`dotfiles/<package>/` is a conventional GNU Stow layout. Simulate first using `scripts/stow-portable /path/to/target`. The script applies no changes unless `--apply` is supplied, checks conflicts before linking, and never adopts or overwrites existing files. Use a backed-up target on the other distribution. NixOS uses Home Manager for these same files.

Install the corresponding native applications, Python 3.11+ for the remaining helpers, and the exact compatible Hyprland/Hyprspace/Walker/Elephant versions. The package map lists the application collection; system package names differ between distributions. Rust source and dependency locks are included for dictation, file picker, workspace slider, wallpaper grid, audio ducking, text picker, formula plotter, cluster tools, transcoding, and iPhone transfer. Their portable build scripts use XDG cache and do not change a system package. On NixOS the launchers use the packaged native executables. Waybar's Electron tray patch is in `waybar/.config/waybar/tray-fix/`; apply it to a matching 0.15.0 build if needed.

`desktop-transcode-build --check` builds and checks the [Rust transcoding supervisor](../dotfiles/desktop-tools/README.md). Conversion still uses FFmpeg/ImageMagick. Completed outputs appear atomically without replacing existing files; cancelling a job stops its encoder group and cleans up intermediate output.

`desktopctl` discovers independent native tools on PATH, skipping its own wrapper files. To override discovery, provide an optional `~/.config/desktop/paths.json` mapping tool names to absolute executables or set `DESKTOP_<TOOL>_BIN`. Do not point a tool's native path back at its own wrapper. Set `HYPRSPACE_PLUGIN` to the plugin shared library when it is not discoverable from the package configuration.

Provide a host monitor file at `~/.config/desktop/monitors.lua` and optional `bar-outputs.json` with `full` and `minimal` arrays. Without it Hyprland uses preferred modes and automatic placement. Workspace slider output selection can use `WORKSPACES_SLIDER_CONFIG` pointing to JSON containing an `output` string/list; `*` selects all enabled, unmirrored outputs.

NixOS declares all `desktop-*.service` units in Home Manager. Other distributions need equivalent user units; the portable helper `scripts/render-user-units.py TARGET` writes these to an explicit staging directory for inspection. After reviewing those units, Stow the generated `desktop-services` package from that staging directory or install the rendered units through your own service configuration. They use independent program names and your home path, with `graphical-session.target` ownership. Use UWSM or another session manager that exports Wayland/Hyprland environment variables to the user systemd manager before starting `desktop-session.target`.

Mutable theme, background, capture, and toggle state stays outside the Stow source. `desktopctl theme init` prepares it; the Hyprland startup hook starts `desktop-session.target`. Browser native messaging is generated with the current home path. Provision credentials separately. The helper never installs packages, pulls configuration updates, or depends on the former distribution.

The file and PDF shortcuts share a Ratatui picker backed by a local SQLite index. `desktop-file-picker.service` prepares one Ghostty host without creating a window; `desktop-pdf-picker.service` is no longer declared. The windows open on demand on your current workspace and close after selection or Escape. The index lives in `${XDG_CACHE_HOME:-~/.cache}/file-picker/index.sqlite3` and is rebuilt automatically; it is runtime cache, not configuration to commit or copy into the Nix store. See the [picker README](../dotfiles/file-picker/README.md) for keys and index maintenance.

The desktop menu, font/theme controls and clipboard shortcuts are documented in [DESKTOP-MENUS.md](DESKTOP-MENUS.md). Walker 2.17.0 additionally needs `pkgs/hyprspace-companions/clipboard-preview.patch`, and Elephant 2.22.0 needs `clipboard-history.patch`, after their existing Hyprspace companion patches. Nix applies both automatically. Plain Stow files alone do not patch the native binaries. The manual artwork screensaver requires Ghostty and TerminalTextEffects (`tte`); power-profile selection requires `powerprofilesctl`.

`application-state/.local/share/desktop-defaults/config` contains initial preferences for applications that edit their own settings. `desktopctl seed-preferences` copies only missing settings; existing files and links are preserved. It runs during Home Manager activation and desktop preparation. Idle locking remains opt-in each session through the existing toggle. The same Hypridle service always handles locking before sleep, using `hypridle-sleep.conf` without an idle listener when automatic locking is off. Installed login locking is independent of the idle listener. System-menu Sleep uses Desktop Ring's Rust capability and inhibitor checks.

Tmux keeps the ordinary TPM setup when `TMUX_NIX_PLUGIN_CONF` is unset. Install TPM and the three plugins declared in `.tmux.conf` on the target distribution. NixOS supplies pinned navigator/resurrect/continuum source through that environment variable and does not invoke TPM's installer or updater. Keep tmux resurrection/pane snapshots in the encrypted private transfer backup, outside Git.

The optional `nix develop .#rust-desktop` shell provides the reference Rust 1.98 toolchain, fd for picker tests, and the SQLite, GTK4, layer-shell, Wayland, PipeWire, ALSA, font and graphics libraries used by the desktop Rust projects. It does not rewrite project manifests or convert remaining Python programs. Project-specific dependency locks remain authoritative; recreate Python environments and native build outputs rather than treating an Arch virtual environment as a portable runtime.


Desktop visual sizing is declared in `modules/home/appearance.nix` and selected
per host in `hosts/*/home.nix`. `desktop.appearance.barScale` scales the bar's
text, icons, spacing, reserved height and Rust workspace overlay together;
`terminalScale` scales Ghostty's font and padding. Both hosts use 1.0 so the reference font sizes, spacing and padding remain
unchanged; monitor scaling stays separate.
The portrait ASUS uses the compact bar by its complete physical description;
changing its connector does not change its bar assignment. Workspace click
coordinates and Wayland buffer dimensions account for both UI and output scale.

The CPU bar glyphs explicitly use Noto Sans Mono, matching the reference font
fallback rather than depending on the installed font order.
