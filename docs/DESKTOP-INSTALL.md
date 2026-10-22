# Stationary desktop installation

The selected drive is the Samsung 960 EVO 500 GB, serial `S3X4NF0JB46224E`,
500,107,862,016 bytes. The recovery SSD is a separate Samsung 840 EVO 120 GB,
serial `S1D5NSBF214670Z`. The Seagate and other SATA disks are not targets.

The NVMe already contains an encrypted Arch installation. It was opened and
mounted read-only to inspect projects, photos, documents, application state and
free space. SMART reports passed with no media errors; Btrfs reports no recorded
I/O, corruption or generation errors. There is no pending tree-log replay.

## Preserve the existing filesystem

`hosts/desktop/local.nix` selects `workstation.storage.existingBtrfs`. In this mode
the module declares mounts and initrd unlocking, and defines **no Disko disks**.
Do not repartition, run a formatting workflow, change the LUKS passphrase, delete
old subvolumes, or change the Btrfs default subvolume.

Create these new subvolumes once, after verifying independent backups:

| Subvolume | Mount |
| --- | --- |
| `@nixos-root` | `/` |
| `@nixos-home` | `/home` |
| `@nixos-nix` | `/nix` |
| `@nixos-log` | `/var/log` |
| `@nixos-snapshots` | `/.snapshots` |

Retain the old `@`, `@home`, `@log`, `@pkg` and snapshot subvolumes. Copy personal
folders into the new home with Btrfs reflinks, preserving the original copies.
Use a clean Home Manager configuration; do not copy old Stow-managed links or
Arch user-service enablement over it. The installed user has UID/GID 1000.

Before writing, verify the whole drive using `scripts/verify-target.py` and
independently check all three UUIDs against `hosts/desktop/local.nix`. Never treat
the `backupsVerified` option as a substitute for a restore test.

## Backup and private state

The independent recovery SSD holds an encrypted Restic repository under
`NixOS-install-recovery-20261022`. Its exact source paths and exclusions are
recorded alongside it. Projects, Git metadata, personal media, browser profiles,
virtual machines, credentials, Docker volumes, old system configuration, boot
files, partition metadata and the LUKS header are included. Only explicitly listed
downloaded games and regenerable caches/toolchains are excluded. Those files
remain on the NVMe.

The repository password is encrypted as `restic-password.age` to the existing
Hendrix SSH key. Recovery must work with the independent key on the reference
laptop. Require a successful complete `restic check --read-data` and sample
restores before marking backups verified.

Verified on 2026-10-22: snapshot
`0dcd2db6631582fe7a55d6a392a792f20b951967205e488de6d652d96bc0260d`,
709,043 files / 107,073,375,627 source bytes. The complete repository read check
passed. Sample restores compared 420 files and one symlink, including Git
metadata, a photo, large media, private credentials and a browser database;
content, ownership, permissions, timestamps and xattrs matched, and the database
integrity check passed. The password and system-metadata archives were also
decrypted with the independent key on the reference laptop without writing
plaintext there. Detailed evidence stays beside the encrypted repository.

Keep the current stationary's user password hash, Wi-Fi credentials, Tailscale
identity, SSH host keys and approved user credentials in private runtime files,
outside Git and the Nix store. Restore the stationary's own identity; never copy
the reference laptop's machine identity. Preserve ownership and restrictive
permissions. Keep the USB and recovery SSD until the installed system is accepted.

## Build and boot

Build the full desktop and console recovery closures before installing. The live
USB store is RAM-backed and too small, so import the built closures directly into
the mounted target store, then install the selected prebuilt system. Place a
committed repository checkout at `/home/simon/nixos-config`.

The current USB session was booted in legacy BIOS mode. This host deliberately
sets `boot.loader.efi.canTouchEfiVariables = false`, allowing systemd-boot to install
its UEFI fallback file without requiring firmware-variable access. Select the
Samsung NVMe's **UEFI** boot entry in firmware and put it before the USB. Secure
Boot must be disabled for these unsigned boot files. The existing disk-encryption
passphrase remains unchanged, with the Danish keymap loaded in the initrd.

The boot menu defaults to NixOS and also contains `Previous Arch system
(preserved)`, which chainloads the original Limine EFI application. Existing
Limine configuration and kernels are retained. Limit NixOS menu generations to
three to leave space for those recovery files in the existing 2 GiB ESP.

Acceptance requires booting from the NVMe without the USB, checking root/home/nix
subvolumes and the NVIDIA 580 driver, and confirming login, Tailscale, personal
files, monitor arrangement and desktop services. A build or successful installer
exit alone does not prove the installed machine boots.
