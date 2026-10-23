# Personal NixOS desktop

An independent Hyprland desktop built from Simon's current laptop configuration. The first installation target is the stationary desktop; `lambda` remains the reference laptop until its own migration is scheduled. This repository has never been activated on the reference laptop.

The shared configuration retains the Lua bindings, Hyprspace overview, patched Walker/Elephant, patched Waybar tray, workspace sliders, Ghostty, Neovim/LazyVim, personal wallpapers and themes, browser extensions, dictation, file picker, Hendrix, cluster helpers, and iPhone workflows. The former distribution's commands are replaced by `desktopctl`, native applications, and declarative services. Credentials and account databases are deliberately separate.

On 2026-10-19 Simon approved building the current live image and preparing the 8 GB Cruzer USB for the stationary desktop. See [LIVE-USB.md](docs/LIVE-USB.md) for boot and inventory instructions. Desktop installation still requires its own reviewed hardware inventory, independent backups and explicit target selection. The earlier ISO is historical output; use the fresh build and its verification record.

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

The familiar Apps/Learn/Trigger/Style/Setup/About/System menus, interactive font/theme controls and dedicated clipboard view are documented in [DESKTOP-MENUS.md](docs/DESKTOP-MENUS.md). Open the desktop menu with Super + Alt + Space and clipboard history with Super + Ctrl + V. Package installation, removal and updates remain declarative.

NixOS 26.05 is the base. Selected applications use the separately pinned unstable input. Hyprland 0.56.2 and Hyprspace are pinned together; Walker 2.17.0 and Elephant 2.22.0 include the matching companion patches. Dependency updates are explicit changes to the lock files. The application map records a decision for every one of the reference system's 260 explicitly installed packages. Arch's base/package-management infrastructure and unused VirtualBox are excluded; their useful system functions are provided by NixOS modules. The six Flatpak applications, including Blender and Roblox Studio through Vinegar, install the current releases from their recorded remotes and branches; historical commits remain in the reference inventory.

Build without activation from a Nix-capable Linux system:

```sh
nix build .#checks.x86_64-linux.desktop-behavior \
  .#checks.x86_64-linux.walker-layout \
  .#checks.x86_64-linux.hyprland-config \
  .#checks.x86_64-linux.portable-syntax \
  .#checks.x86_64-linux.neovim-startup \
  .#checks.x86_64-linux.tmux-startup
nix build .#dictate .#file-picker .#workspaces-slider .#hyprspace
nix build .#nixosConfigurations.desktop.config.home-manager.users.simon.home.activationPackage
```

After completing the host review, run `nix flake check --no-build` as well. It intentionally reports the installed-profile guards while disk/hardware fields are unset. The current flake targets x86_64 Linux.

The recorded baseline covers 25 package outputs, five checks and the complete Home Manager environment without activation. The menu/clipboard followup adds the `walker-layout` check; see the dated validation record for its results and limits. The Home Manager build includes the complete recorded application collection, SDKs, and TeX; it does not activate anything or restore private state. Installed system profiles intentionally fail their installation assertions before the hardware and backups are reviewed. The live profile is approved for the current USB preparation and desktop testing phase.

For another distribution, first install the programs listed in the package map and use the same pinned compositor/plugin versions. Simulate deployment to an explicit target with `scripts/stow-portable TARGET`; use `--apply` only after resolving all conflicts and backing up that target. No `--adopt`, manual links, or overwrite flags are used. Native tool source and Cargo locks are included; their portable `*-build` helpers build into XDG cache. See [PORTABLE.md](docs/PORTABLE.md) for user services.

Do not publish the reference inventory without reviewing its personal paths and account names. The repository has no remote and contains no copied login credentials. Provenance is recorded in `docs/inventory/reference.json`; third-party license notices remain in their source trees and `docs/licenses/`.

## Repository checkout

The `dotfiles/` directory is a Git submodule of `https://github.com/simonwinther/dotfiles`, pinned to the shared `nixos-portable` branch. Home Manager consumes those Stow packages on NixOS.

```sh
git clone --recurse-submodules https://github.com/simonwinther/nixos-config
cd nixos-config
git submodule update --init --recursive
```

The flake enables submodule fetching, and the rebuild keybind initializes the pinned submodule before building. Commit dotfiles changes in their own repository, push that revision, then commit the updated submodule pointer here. Keep runtime credentials and private state outside both repositories.
