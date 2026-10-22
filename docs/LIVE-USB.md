# Stationary desktop live USB

Simon approved building the current project and preparing the Cruzer USB on
2026-10-19. The installation target is the stationary desktop. The Arch laptop
remains the reference machine. Preparing this USB does not approve erasing any
desktop disk.

## Boot and try the desktop

1. Shut down the stationary desktop, insert the USB, and select its **UEFI USB**
   entry from the firmware boot menu. The current image requires Secure Boot to
   be disabled; it does not enroll signing keys.
2. Boot the default live entry. The personal Hyprland session logs in as `simon`.
   The live user has no password; this is temporary installation media.
3. Check graphics, monitors, keyboard, network, sound, the launcher and overview.
   Use Ethernet if available. The installer contains the core desktop; full
   applications, SDKs and Flatpaks still need internet during installation or
   first login. Private accounts and personal data require separate restoration.
4. If graphics do not start, switch to a text console with Ctrl+Alt+F2. Do not
   infer a graphics driver from the laptop: NVIDIA in particular needs its model
   reviewed before selecting the installed driver.

## Configuration and hardware inventory

The writable project is at `~/nixos-config`. An untouched source copy is at
`/etc/nixos-config`. Open this guide or `docs/MIGRATION.md` from that directory.
The writable project starts with all source files staged in a local Git
repository, so flakes include them. New host files must also be added to Git.

In a terminal:

```sh
cd ~/nixos-config
python3 scripts/inventory.py --output private/desktop-hardware.json
lsblk -o NAME,SIZE,MODEL,SERIAL,FSTYPE,MOUNTPOINTS
lspci -nnk
hyprctl configerrors
```

The inventory command only reads hardware information and writes a new private
report. It does not partition or mount a disk. Review the report and establish
independent backups before enabling installation in `hosts/desktop/local.nix`.
Follow `docs/MIGRATION.md` for the hardware review, backup verification, exact
disk selection, full system builds and eventual installation commands.

**The live home is temporary. Changes and inventory reports disappear on
shutdown unless saved to separate storage.** The USB contains no personal
documents, account logins, SSH keys or passwords from the laptop.

## Retained build downloads

The image includes NordVPN TUI and the 15 retained editor-extension
archives at `/etc/nixos-installer-sources`. They are already present in the live
Nix store, so building from the live session can use them without fetching their
original URLs. Other pinned inputs still require network access.

Preserve these archives on independent backup storage for later rebuilds; an
installed runtime closure does not automatically preserve its build sources.
Copy the files by following symlinks (`cp -L`), verify the manifest hashes, and
follow `docs/VENDOR-SOURCES.md` when importing them on another builder.
