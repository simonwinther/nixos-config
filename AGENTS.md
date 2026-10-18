# Configuration rules

- Work only in this isolated repository. The active Arch configuration and original dotfiles are reference sources.
- Home Manager owns links on NixOS; GNU Stow owns links on other distributions. Never manage a target with both.
- Keep portable desktop tools and plain configuration in Stow packages under dotfiles/.
- Never run activation, reload, package installation, disk formatting, or service mutation on the reference laptop.
- Keep credentials and private recovery material outside Git and the Nix store.
- Commit dependency locks and source, never compiled binaries or caches.
- The current task is configuration parity: reproduce the reference Arch experience in NixOS while replacing the old distribution's names, tools, and infrastructure.
- Do not build or rebuild an ISO/live image, write installation media, activate configurations, or install NixOS until Simon explicitly approves that phase. A prior image build is historical evidence, not approval to repeat it.
- Build and check individual packages, portable configuration, and the Home Manager environment without activation as needed. Keep source conversion, runtime acceptance, private-state transfer, and installation readiness separate in reports.
- Installation requires a reviewed host hardware inventory and verified independent backups.
