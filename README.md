# Personal NixOS desktop

An independent Hyprland desktop built from Simon's former Arch laptop configuration. The laptop, `lambda`, runs NixOS from `nixosConfigurations.lambda` (installation configured in 969f3f4 on 2026-10-25); the stationary desktop is `nixosConfigurations.desktop`. Agents never activate configurations; Simon does.

The shared configuration retains the Lua bindings, Hyprspace overview, Morphing Notch Bar with native Rust menus, search, workspaces and tray, Ghostty, Neovim/LazyVim, personal wallpapers and themes, browser extensions, dictation, file picker, Hendrix, cluster helpers, and iPhone workflows. The former distribution's commands are replaced by `desktopctl`, native applications, and declarative services. Credentials and account databases are deliberately separate.

On 2026-10-19 Simon approved building the current live image and preparing the 8 GB Cruzer USB for the stationary desktop. See [LIVE-USB.md](docs/LIVE-USB.md) for boot and inventory instructions. Each host records its reviewed hardware, disk, GPU and backup decision in `hosts/<host>/local.nix`. The earlier ISO is historical output; use the fresh build and its verification record.

Read [MIGRATION.md](docs/MIGRATION.md) before installing, [VALIDATION.md](docs/VALIDATION.md) for actual test results and remaining acceptance checks, and [RECOVERY.md](docs/RECOVERY.md) for recovery. Without a `local.nix`, a host selects no disk, and the Disko device definition is withheld until the hardware and backup flags are true and the GPU and persistent disk path are selected.

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

[LAST_UPDATED](LAST_UPDATED) records local maintenance dates for the Nix projects
and configuration areas. [dotfiles/LAST_UPDATED](dotfiles/LAST_UPDATED) tracks the
portable projects. [AGENTS.md](AGENTS.md) defines how changes maintain both;
these dates do not imply that upstream dependencies are current or runtime
validation has been completed.

Home Manager links individual files from `dotfiles/` on NixOS. GNU Stow links the same files on another distribution. Mutable choices live in `~/.local/state/desktop`, generated CSS/configuration in `$XDG_RUNTIME_DIR/desktop`, and credentials in private runtime files. Neither theme changes nor helper programs rewrite Nix-managed files. Do not run Stow over Home Manager's targets. Keep the editable checkout at `~/nixos-config`; Neovim's dotfile-search bindings use its `dotfiles/` directory through `DOTFILES`. Change that session variable if you choose another checkout location.

The familiar Apps/Learn/Trigger/Style/Setup/About/System menus, interactive font/theme controls and dedicated clipboard view are documented in [DESKTOP-MENUS.md](docs/DESKTOP-MENUS.md). Open the desktop menu with Super + Alt + Space, clipboard history with Alt + V, and screenshots with Super + Q. Package installation, removal and updates remain declarative.

NixOS 26.05 is the base. Selected applications use the separately pinned unstable input. Hyprland 0.56.2 and Hyprspace are pinned together. Morphing Notch Bar and the Rust desktop-search service provide native menus and search without Walker. Dependency updates are explicit changes to the lock files. NixOS hosts take their package set from `flake.nix` (`nixpkgs.pkgs = pkgs`), so `nixpkgs.config` settings such as `allowUnfree` belong in its `import nixpkgs { config = ...; }`; a `nixpkgs.config` definition in a NixOS module fails evaluation, while `nixpkgs.overlays` still works. The application map records a decision for every one of the reference system's 260 explicitly installed packages. Arch's base/package-management infrastructure and unused VirtualBox are excluded; their useful system functions are provided by NixOS modules. The six Flatpak applications, including Blender and Roblox Studio through Vinegar, install the current releases from their recorded remotes and branches; historical commits remain in the reference inventory.

Build without activation from a Nix-capable Linux system. `nix flake show` lists every check and package; for example:

```sh
nix build --max-jobs 1 --cores 4 .#checks.x86_64-linux.desktop-behavior \
  .#checks.x86_64-linux.hyprland-config \
  .#checks.x86_64-linux.portable-syntax \
  .#checks.x86_64-linux.neovim-startup \
  .#checks.x86_64-linux.tmux-startup
nix build --max-jobs 1 --cores 4 .#dictate .#file-picker .#desktop-bar .#hyprspace
nix eval --raw .#nixosConfigurations.desktop.config.home-manager.users.simon.home.activationPackage.drvPath
nix build --max-jobs 1 --cores 4 .#nixosConfigurations.desktop.config.home-manager.users.simon.home.activationPackage
```

The `drvPath` evaluation is a cheap first step; only the build catches build failures. `nix flake check --no-build` evaluates the live image and every system in one process, at about 2.5 GiB per system. Both installed profiles pass their installation guards because their reviewed `local.nix` files are tracked. Run the Python suites through the flake checks: host runs pick up installed binaries from `PATH`. The current flake targets x86_64 Linux.

Dated results, including native menu and search checks, are in [VALIDATION.md](docs/VALIDATION.md). The Home Manager build includes the complete recorded application collection, SDKs, and TeX; it does not activate anything or restore private state. The live profile is approved for the current USB preparation and desktop testing phase. [AUDIT-2026-11.md](docs/AUDIT-2026-11.md) records the November 2026 performance, reliability and security audit and the recommendations still awaiting Simon's decision.

For another distribution, first install the programs listed in the package map and use the same pinned compositor/plugin versions. Simulate deployment to an explicit target with `scripts/stow-portable TARGET`; use `--apply` only after resolving all conflicts and backing up that target. No `--adopt`, manual links, or overwrite flags are used. Native tool source and Cargo locks are included; their portable `*-build` helpers build into XDG cache. See [PORTABLE.md](docs/PORTABLE.md) for user services.

Do not publish the reference inventory without reviewing its personal paths and account names. Both repositories have a GitHub remote (`origin`). Their working trees contain no copied login credentials; [AUDIT-2026-11.md](docs/AUDIT-2026-11.md) lists credentials that remain in the dotfiles history and need rotation. Provenance is recorded in `docs/inventory/reference.json`; third-party license notices remain in their source trees and `docs/licenses/`.

## Repository checkout

The `dotfiles/` directory is a Git submodule of `https://github.com/simonwinther/dotfiles`, pinned to an exact commit from the shared `master` branch. Home Manager consumes those Stow packages on NixOS.

```sh
git clone --recurse-submodules https://github.com/simonwinther/nixos-config
cd nixos-config
git submodule update --init --recursive
```

On the installed laptop or stationary, run `rebuild` to fast-forward the local
main branch to the published revision, check out its pinned dotfiles, build this
host and switch to the result. It stops on local edits, unpublished commits or
a failed build. Publish shared changes from the machine where you made them
before running it on the other machine.

The flake enables submodule fetching. **Super+Ctrl+Alt+N** only builds the clean,
locked checkout; it never synchronizes source or activates the result. Use
`nixos-rebuild-desktop sync` separately to initialize or check out the recorded
submodule revisions. After reviewing a successful build, explicitly run
`nixos-rebuild-desktop activate` on the approved target to apply that exact output.
All actions refuse staged, unstaged or untracked file changes, including nested
submodules, and log the repository revision, lock hash and submodule revisions.
See [PRIVATE-RUNTIME.md](docs/PRIVATE-RUNTIME.md) for the workflow.

`nixos-rebuild-desktop times` charts build and activation durations. Its own
builds and activations are recorded, and Home Manager wraps `nh` so that
`nh os build`, `switch`, `boot` and `test` are recorded too, tagged `nh`. Pinned
builds run with `--max-jobs 1 --cores 4` while `nh` uses the Nix defaults, so
compare durations within the same tool.

Commit dotfiles changes in their own repository, push that revision, then commit
the updated submodule pointer here. Keep runtime credentials and private state
outside both repositories.
