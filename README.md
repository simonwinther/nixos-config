# Personal NixOS desktop

An independent Hyprland desktop built from Simon's current laptop configuration. The first installation target is the stationary desktop; `lambda` remains the reference laptop until its own migration is scheduled. This repository has never been activated on the reference laptop.

The shared configuration retains the Lua bindings, Hyprspace overview, patched Walker/Elephant, patched Waybar tray, workspace sliders, Ghostty, Neovim/LazyVim, personal wallpapers and themes, browser extensions, dictation, file picker, Hendrix, cluster helpers, and iPhone workflows. The former distribution's commands are replaced by `desktopctl`, native applications, and declarative services. Credentials and account databases are deliberately separate.

The current phase is configuration parity with the reference Arch desktop: account for its settings, custom tools, plugins, development workflows, and private state before preparing installation media. Package builds and configuration checks are allowed without activation. ISO/live-system builds, USB preparation, activation, and installation await Simon's explicit approval. An earlier ISO was built prematurely; its existence does not establish configuration completeness or installation readiness.

Read [MIGRATION.md](docs/MIGRATION.md) before installing, [VALIDATION.md](docs/VALIDATION.md) for actual test results and remaining acceptance checks, and [RECOVERY.md](docs/RECOVERY.md) for recovery. The desktop's disk, GPU, monitor arrangement, and backup destination still require its own inventory. No disk is selected by default. The Disko device definition is also withheld until the hardware and backup flags are true and the GPU and persistent disk path are selected.

```text
flake.nix / flake.lock       pinned OS, Home Manager, compositor, plugin, services
hosts/desktop/              desktop hardware, monitors, reviewed local settings
hosts/lambda/               laptop hardware and its existing display arrangement
profiles/                   workstation, laptop, live USB, console recovery
modules/nixos/              boot/storage, hardware, networking, security, services
modules/home/               file ownership, packages, desktop services, applications
dotfiles/<package>/         standard GNU Stow tree; the sole source of plain configs
pkgs/                       native tools, compatibility patches, locked editor sources
docs/inventory/             reference provenance and complete explicit package decisions
scripts/                    read-only inventory, disk verification, Stow simulation
secrets/                    instructions only; private keys and plaintext are excluded
```

Home Manager links individual files from `dotfiles/` on NixOS. GNU Stow links the same files on another distribution. Mutable choices live in `~/.local/state/desktop`, generated CSS/configuration in `$XDG_RUNTIME_DIR/desktop`, and credentials in private runtime files. Neither theme changes nor helper programs rewrite Nix-managed files. Do not run Stow over Home Manager's targets. Keep the editable checkout at `~/nixos-config`; Neovim's dotfile-search bindings use its `dotfiles/` directory through `DOTFILES`. Change that session variable if you choose another checkout location.

NixOS 26.05 is the base. Selected applications use the separately pinned unstable input. Hyprland 0.56.2 and Hyprspace are pinned together; Walker 2.17.0 and Elephant 2.22.0 include the matching companion patches. Dependency updates are explicit changes to the lock files. The application map records a decision for every one of the reference system's 260 explicitly installed packages. Arch's base/package-management infrastructure and unused VirtualBox are excluded; their useful system functions are provided by NixOS modules. The five Flatpak applications retain their recorded commits and branches.

Build without activation from a Nix-capable Linux system:

```sh
nix build .#checks.x86_64-linux.desktop-behavior \
  .#checks.x86_64-linux.hyprland-config \
  .#checks.x86_64-linux.portable-syntax \
  .#checks.x86_64-linux.neovim-startup \
  .#checks.x86_64-linux.tmux-startup
nix build .#dictate .#file-picker .#workspaces-slider .#hyprspace
nix build .#nixosConfigurations.desktop.config.home-manager.users.simon.home.activationPackage
```

After completing the host review, run `nix flake check --no-build` as well. It intentionally reports the installed-profile guards while disk/hardware fields are unset. The current flake targets x86_64 Linux.

The current 25 package outputs, five checks and complete Home Manager environment build successfully without activation; see the dated validation record for workflow checks and limits. The Home Manager build includes the complete recorded application collection, SDKs, and TeX; it does not activate anything or restore private state. Installed system profiles intentionally fail their installation assertions before the hardware and backups are reviewed. The live profile is reserved for a later, separately approved media/testing phase.

For another distribution, first install the programs listed in the package map and use the same pinned compositor/plugin versions. Simulate deployment to an explicit target with `scripts/stow-portable TARGET`; use `--apply` only after resolving all conflicts and backing up that target. No `--adopt`, manual links, or overwrite flags are used. Native tool source and Cargo locks are included; their portable `*-build` helpers build into XDG cache. See [PORTABLE.md](docs/PORTABLE.md) for user services.

Do not publish the reference inventory without reviewing its personal paths and account names. The repository has no remote and contains no copied login credentials. Provenance is recorded in `docs/inventory/reference.json`; third-party license notices remain in their source trees and `docs/licenses/`.
