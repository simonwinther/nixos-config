# Validation record

Validation uses a dedicated Docker container and Nix store. No NixOS profile has been activated, no host package has been installed, no active desktop component has been reloaded, and no disk/partition/service configuration has been changed on the reference laptop. The original dotfiles remain the reference; the later changes listed in [reference-drift.json](inventory/reference-drift.json) are excluded by the user's snapshot choice.

Source checks, Nix evaluation, package builds, complete environment/system builds, and real-hardware acceptance are separate gates. Passing one does not establish the next. Build logs and JSON output records are retained under the ignored `.work/` directory; they contain local build paths and are not independent backups.

## Verified in isolation

| Check | Result and scope |
| --- | --- |
| Package coverage | All 260 explicit Arch packages have an installation, service, replacement, or exclusion decision; 1,367 total packages and 46 foreign packages were inventoried. |
| Stow ownership and source syntax | Unique home targets, shell/Lua/Python syntax, required executable sources, and inventory/editor pin consistency passed. GNU Stow also created 694 valid links in a disposable home. |
| Desktop behavior | Nine tests cover the 21 retained theme palettes, image-derived Matugen colors, atomic state links, light-mode state, cancelled captures, monitor safeguards, and duplicate locks. |
| Hyprland and Hyprspace | The pinned compositor and matching plugin built; `Hyprland --verify-config` reported `config ok` with both the base configuration and the plugin enabled. This is a parser check without a running display server. |
| Ghostty | Packaged Ghostty's `+validate-config` passed. Rendering, scaling and keyboard input still require the physical session. |
| Neovim | All 62 locked plugin sources and 37 locked parsers built. The repeatable startup check passed LuaSnip and completion setup, loaded the native fuzzy library, discovered all parsers, and parsed Lua/Python/C/LaTeX/Typst samples. No plugin/Mason installation ran. |
| Tmux | The pinned navigator/resurrect/continuum sources built. A private server passed startup, navigation binding, modified-key, session-save and pane-capture checks; no existing tmux server was contacted. |
| Native helpers | Dictation passed 26 Rust tests; file picker passed six; workspace slider passed three with the packaged font. Patched Waybar built and reported its version. |
| Launcher and break reminders | Patched Walker passed two tests. Breakd passed 96 tests with one upstream test ignored; the socket fixture uses a short temporary directory under Nix. |
| Desktop runtime dependencies | The packaged tools discover the GNOME interface settings schema outside GNOME. Chromium MIME defaults include both Arch's and NixOS's desktop-entry names. |
| Merged application profile | GCC supplies `cc`/`c++`; named Clang and Fortran commands remain available. A C++ program compiled and ran from the merged profile, and the PulseAudio client command reported its version. Compiler wrapper priorities and a redundant PulseAudio library entry were corrected after complete builds exposed conflicts. |
| NixOS integration | Unset home variables are filtered before exporting the systemd environment. The explicit UWSM session uses the NixOS compositor wrapper. NordVPN's newer documentation chapter is excluded from the 26.05 manual's redirect index while its pinned runtime module and option documentation are retained. |
| Installed session launcher | The generated desktop entry passes `desktop-file-validate`. Its lock helper is one executable argument with packaged locker/compositor tools on PATH; the helper passes Bash syntax validation. The selected NixOS compositor exactly matches the plugin's compositor. The live session has no lock command. |
| Proprietary artifacts | Boosteroid's retained Debian archive built with patched interpreter/libraries and corrected launcher path. Its historical archive and the NordVPN TUI archive require the separate retention procedure in [VENDOR-SOURCES.md](VENDOR-SOURCES.md). |
| Installation guards | Live configuration has no failed assertions. Installed desktop/recovery profiles intentionally reject missing hardware review, backup verification, disk selection, GPU selection and root filesystem; the laptop also remains guarded. Supplying only a disk path yields no Disko disk definitions. The live profile forces private SOPS provisioning off even if host settings request it. |

## Complete builds

| Output | Status |
| --- | --- |
| Custom native packages | Passed: all 18 outputs, including the compositor plugin, launcher/provider patches, editor and tmux sources, desktop helpers, and retained vendor applications. |
| Complete installed Home Manager environment | Passed, including the full application collection and TeX formats; no activation performed. |
| Live system and ISO | Passed. Exported `.work/iso/hyprland-desktop-live.iso` (5.04 GiB), with `SHA256SUMS` and `build.json` alongside it. Host/store SHA-256 values match. The image reports BIOS and UEFI boot entries and the `DESKTOP_LIVE` volume ID. No USB boot performed. |
| Installed desktop and console recovery systems | Await the desktop's actual hardware, disk selection and verified backup. The guards remain enabled. |

## Repeatable checks

From this checkout on an x86_64 Nix-capable Linux system:

```sh
nix build .#checks.x86_64-linux.desktop-behavior \
  .#checks.x86_64-linux.portable-syntax \
  .#checks.x86_64-linux.neovim-startup \
  .#checks.x86_64-linux.tmux-startup
nix build .#nixosConfigurations.desktop.config.home-manager.users.simon.home.activationPackage
nix build .#desktop-iso
```

The Home Manager command builds its activation package without running it. Keep the historical vendor archives available before reproducing the complete installed application environment. After completing the actual host review, build the installed workstation and recovery `system.build.toplevel` outputs as described in [MIGRATION.md](MIGRATION.md). A full `nix flake check` intentionally encounters the installed-profile guards until that review is complete.

On a memory-constrained builder, release Nix's evaluation memory before ISO packaging:

```sh
desktop_iso_drv=$(nix eval --raw .#desktop-iso.drvPath)
nix build "$desktop_iso_drv^out"
```

The container uses `nixos/nix@sha256:377d4887aca98f0dfa12971c1ea6d6a625a435d8b610d4c95a436843da6fbfd1`, two CPUs and 4 GiB RAM, with the repository mounted read-only and only `.work/` writable. Run large builds sequentially at that limit: overlapping Home Manager evaluation and Rust compilation exceeded it. The default ISO compressor also exceeded it; this profile uses Zstd level 15 with a 512 MiB compression cache and the separate evaluation/build steps above. Its isolated Nix sandbox setting does not alter the installed system's Nix policy. The build cache is the dedicated `nixos-config-store` Docker volume.

The ISO contains the core desktop package set and personal configuration. The complete application collection, SDKs, TeX, and NordVPN/Twingate/Tailscale services belong to the installed profile. Private account state is restored or created separately. Complete application-specific acceptance follows the installed-profile build and selective restoration.

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
