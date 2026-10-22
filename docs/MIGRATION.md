# Desktop-first migration procedure

Current phase, approved by Simon on 2026-10-19: build the current project and prepare the Cruzer USB for live testing on the stationary desktop. See [LIVE-USB.md](LIVE-USB.md). This authorizes live-image building and USB preparation; installation still requires the desktop inventory, verified backups and explicit destructive-target selection described below.

## 1. Establish the target and preserve the reference

The inspected machine is `lambda`, a ThinkPad L14 Gen 1 with Ryzen 5 PRO 4650U/Renoir graphics, AX200 wireless, approximately 16 GB RAM, and Arch/Omarchy. It supplies the desired user experience; its disk layout is not the desktop's layout. No installation command in this document should be run on that laptop during the desktop migration.

The initial reference records 1,367 installed packages, 260 explicit packages, 46 foreign packages, four Flatpaks, 62 pinned Neovim plugins, and 203 registered Hyprland bindings. Plain source files, appearance assets, local tools, and their provenance were copied into this isolated repository. The original dotfiles were already dirty: `hypr/.config/hypr/monitors.lua` and `nvim/.config/nvim/lazy-lock.json` have user changes. Do not reset or overwrite them.

On the stationary desktop, run `python3 scripts/inventory.py --output private/desktop-hardware.json`. Review GPU PCI IDs, CPU, Wi-Fi, Ethernet, USB devices, disk serials/sizes, existing filesystems, UEFI/Secure Boot, available firmware, and monitor EDID/model/output names. Record all data-bearing disks, including separate home/game/media drives and dual-boot operating systems. Inventory intentionally avoids Wi-Fi passwords, API keys, and account databases.

Complete `hosts/desktop/hardware-configuration.nix` from that machine's generated hardware scan and adjust `monitors.lua`, bars, input devices, CPU microcode, GPU driver, and any hybrid graphics. Keep filesystem/boot ownership in the Disko module; do not import conflicting generated root/boot mounts. Do not guess the laptop's GPU or UUIDs onto the desktop. NVIDIA open-driver selection depends on its actual model. Secure Boot needs a separately designed and tested signing setup; the current configuration does not enroll keys.

## 2. Create independent, encrypted backups

Use a separate physical backup disk or remote encrypted repository. A Btrfs snapshot on the disk about to be erased is not an independent backup. Record the backup device's serial and keep it disconnected during partitioning. Keep a second copy of irreplaceable documents/photos and the encryption/recovery material.

Back up the desktop's entire home directories and relevant `/etc`, `/root`, `/var/lib`, existing boot files, package inventories, partition tables, and existing encryption metadata. Shut down databases, browsers, mail clients, containers, and game clients before their final copy. Back up Docker named volumes with application-consistent dumps; saving images or compose files alone does not preserve databases. Capture ACLs, xattrs, symlinks, numeric owners, and sparse files. Restic is suitable for encrypted file backups; a full disk image is the strongest route to restoring the exact old desktop installation.

Use the existing OS's disk tools to export its GPT/partition table and any existing LUKS header only after identifying the correct disk. A LUKS header contains sensitive keyslot material: encrypt it and store it apart from the machine. Record ESP contents and UEFI boot entries. Preserve existing recovery media and installation instructions for the old OS.

From the laptop, copy selected personal configuration and state into an encrypted transfer archive, separate from the desktop's full backup. Include documents/projects needed on the desktop, Neovim spell/snippet/undo state as desired, shell history, mail settings, wallpaper collections, browser extensions, game saves, and application preferences. Do not carry forward the old distribution's source tree, updater, package hooks, service units, branding, or generated shell prefixes. Do not restore the laptop's `/etc`, `/boot`, network identity, user authentication databases, VPN daemon identity, or hardware files onto the desktop.

List and verify backup contents, run the backup tool's integrity check, then restore representative documents, a project with Git metadata, a symlink, a large media file, and a database dump into a separate temporary directory. Compare hashes and permissions against the originals. Test decryption using recovery material independent of the laptop session. Record repository/snapshot ID, source hostname, timestamp, disk serials, verification command/results, and successful restore results in private storage. Only then set `backupsVerified = true`.

## 3. Review application/state compatibility

`inventory/package-map.json` covers every explicit Arch package. Most applications come from pinned Nixpkgs; system services replace package-only entries. Their versions can differ from Arch's rolling versions (for example, packaged Neovim is 0.12.4 versus reference 0.12.5); test representative projects and application databases before relying on compatibility. Proprietary applications are enabled deliberately through `allowUnfree`. The old NordVPN TUI release needs its exact retained archive: follow [VENDOR-SOURCES.md](VENDOR-SOURCES.md) to back up and import it before building on another machine. It is not committed here.

Flatpak commits can disappear from remote history. Archive application exports and required runtimes before migration if exact historical reinstall is essential. Flatpak files remain under `~/.var/app`; the four active IDs include Discord, Android Studio, GeForce NOW's `master` branch, and Sober. Declarative installation still requires internet and happens after login; a Nix build does not contain the Flatpak payloads. Do not disable existing apps until replacements are tested.

Nix store executables do not use `/usr/bin` paths. The portable wrappers, Hendrix service, font discovery, browser native-messaging manifest, and desktop tools account for that. Foreign binaries, SDKMAN/NVM/GHCup downloads, and language project toolchains may still require a project `devShell`, FHS environment, AppImage runtime, or `nix-ld`. The shell uses packaged Node when NVM is absent. Existing SDK directories are data to migrate deliberately, not reproducible inputs.

Neovim's 62 plugin sources and the 37 installed parser sources are hash-pinned. On NixOS, plugin downloads/builds and Mason installs are disabled; language servers/formatters and the native completion library are packaged. On other distributions the same config uses its normal Lazy workflow. Validate every active language project, especially Java, Haskell, Flutter, TeX, and Typst. Container evaluation cannot verify their interactive behavior.

VS Code and Cursor retain all 142 and three recorded extension entries respectively through hash-pinned VSIX sources and Nix-compatible native libraries. Headless discovery matches the recorded IDs and versions; interactive debugger/language-server behavior still needs the real projects. Retain the cached extension archives listed in [VENDOR-SOURCES.md](VENDOR-SOURCES.md); extension-managed downloads and private databases are restored separately.

Sign in to browsers, 1Password, mail, Spotify, Slack, Canvas, NordVPN, Twingate, Tailscale, and other services separately on the desktop. Browser profile import is optional and should be tested against a private copy because keyring-bound cookies/passwords may not transfer. Load unpacked extensions from `~/.local/share/browser-extensions`; extensions without a fixed manifest key can acquire new IDs. The dictation native host is generated for the target home directory. Provision private credentials as described in `../secrets/README.md`.

## 4. Build and review before installing

First finish the configuration/state coverage audit, resolve unaccounted custom tools and dependencies, and review the documented remaining runtime checks with Simon. Build individual packages and the complete Home Manager environment without activation. Do not equate a successful build with complete transfer of the reference home directory, credentials, or project environments.

Simon approved media preparation on 2026-10-19. The selected medium is the 8 GB SanDisk Cruzer Micro, serial `1738331DE8C11B00` (8,040,480,256 bytes). Fresh build and write-verification evidence is recorded under `.work/usb-2026-10-19/`. The earlier image at `.work/iso/hyprland-desktop-live.iso` is historical output and is not the current installation candidate. The USB is separate from the still-unselected desktop installation disk.

After approval, build the reviewed live configuration and export a fresh checksum record. From its directory, run `sha256sum -c SHA256SUMS` before use. Select an 8 GB or larger USB by its model, serial and size; back up its existing contents and unmount its partitions. Write the ISO as a whole-device image with verification enabled in the imaging tool, then safely eject it. Record the selected USB separately from the installation target and backup devices.

Review all inventory decisions, run the checks listed in `VALIDATION.md`, and build the live system. Boot the custom USB directly on the stationary desktop without mounting or modifying its system disk. Check both TTY and graphical login, actual Hyprland config errors, monitor scales/refresh rates, GPU acceleration, input, Wi-Fi/Ethernet, Bluetooth, sound/mic, portal screen sharing, suspend/resume, and the personal desktop acceptance checklist. Capture screenshots and compare them to the laptop at matching scale and theme. Correct host settings and rebuild the USB as needed.

The live image provides the core desktop package set. Complete application-specific shortcuts, SDKs, account workflows and private-data compatibility are validated using the installed profile and restored copies of data. Keep the live USB review focused on the hardware and desktop components it includes.

Copy `hosts/desktop/local.nix.example` to `local.nix`, select the reviewed whole disk by `/dev/disk/by-id/`, choose the actual GPU, and set the two review flags only when their evidence exists. Stage the file in Git so the flake sees it; disk identifiers are not secret, but review before publishing. No example contains a real target disk. Run `scripts/verify-target.py --disk ... --serial ... --bytes ...` on the desktop immediately before installation. Verify that the backup disk is absent from the target machine.

Now build both `.#nixosConfigurations.desktop.config.system.build.toplevel` and `.#nixosConfigurations.desktop-recovery.config.system.build.toplevel` without activation. Resolve all errors before formatting. Save their closures to the installation medium or arrange tested network access. Keep this repo and its lock file on independent storage. A successful evaluation alone is not a successful build.

## 5. Install on the stationary desktop

Proceed only after Simon explicitly approves installation, the complete preceding review, restored backups, live USB acceptance, final desktop-specific configuration, and explicit selection of the destructive target. Boot UEFI mode from NixOS installation media. Check the hostname/context and disk serial/size again. Keep the laptop and backup media separate. The following commands are the eventual manual installation workflow, not commands to run on the current laptop:

```sh
# From the reviewed repository on the stationary desktop's live system:
nix run --inputs-from . disko -- --help
# Use the LOCKED Disko input from this flake for the actual operation:
sudo nix run --inputs-from . disko -- --mode destroy,format,mount --flake .#desktop
sudo nixos-install --flake .#desktop
```

Disko will erase the selected disk and create a 2 GiB unencrypted EFI partition plus LUKS2-encrypted Btrfs containing `@root`, `@home`, `@nix`, `@log`, and `@snapshots`. Use a strong, recorded disk passphrase and verify keyboard layout before entering it. The current design has no TPM auto-unlock, hibernation/resume image, swapfile, or automatic repartitioning of other disks. Zram supplies compressed swap. LUKS discard passthrough is enabled and can be disabled if desired before installation.

Before rebooting, enter the installed system with `sudo nixos-enter --root /mnt` and set Simon's password with `passwd simon`. Confirm root recovery authentication as well. Verify `/mnt/boot` is the intended ESP, the boot entry exists, the root/home/nix mounts are encrypted as intended, the user owns its files, and the Home Manager activation completed. Back up the newly created LUKS header to encrypted external storage after installation. Keep passphrases and header recovery copies apart from the installed disk.

Commit the reviewed host configuration and place a local Git clone at `/mnt/home/simon/nixos-config` before rebooting, with ownership UID/GID 1000. Clone the reviewed repository's committed files and history; keep ignored build outputs, vendor archives and private transfer material on their separate backup media. Set the installed checkout's remote to the intended repository later if its initial source was the live USB. This checkout is needed for editing/rebuilding and for the `DOTFILES` search bindings; Nix-managed configuration links alone do not create it.

## 6. Restore and authenticate selectively

Boot the new system, unlock LUKS, and confirm automatic Hyprland login reaches a locked screen that Simon's new password unlocks. Log in through TTY too. Restore desktop data and selected laptop state with ownership UID/GID 1000, preserving metadata. Do not restore old managed `.config` files over Home Manager links: first compare them and move intended customizations into the repository. Do not restore the old distribution's user-service enablement directories or its PATH setup.

Authenticate services and provision secrets. GNOME Keyring may need one manual unlock after automatic login because the disk password is not the user PAM password. Test the secrets bootstrap and offline recovery before enabling immutable SOPS-managed user passwords. Enable no automatic package or system updates until the complete desktop is accepted.

## 7. Validate and stabilize

Complete every item in `VALIDATION.md` on real hardware. Compare launcher behavior, overview/Alt-Tab, workspace sliders, tray icons, custom terminal prompt and vi mode, all shortcuts, theme/background switching, window rules, notification actions, capture/OCR, screen recording, file picker, push-to-talk dictation, mail, code projects, VPN/SSH/cluster access, local discovery/printing, and iPhone transfer. Verify firewall and Docker DNS behavior with actual workloads; Docker-published ports require explicit review and are not automatically made private by a host firewall.

Run a fresh backup and repeat a sample restore. Keep old boot media and the full old-system backup until the new system has survived several reboots, suspend/resume cycles, and normal work. Nix generations restore software/configuration; they do not restore changed personal data. Home snapshots and Restic complement, but do not replace, that first independent backup.

## 8. Add the laptop later

Reuse shared modules and Stow sources. Inventory `lambda` again at that time, review its own target disk and backup proof, complete its hardware file, and run the same acceptance process. Its current display layout is included as a reference; do not erase it as part of the desktop rollout. Each machine retains separate authentication, machine IDs, and host-specific hardware settings.
