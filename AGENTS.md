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

## Last updated

- Read [LAST_UPDATED](LAST_UPDATED) before project maintenance. It covers the Nix packages, host configurations, modules, profiles, scripts and repository infrastructure. Paths identify the file or directory covered by each entry.
- Portable projects have their own canonical dates in [dotfiles/LAST_UPDATED](dotfiles/LAST_UPDATED). Keep those dates there rather than duplicating them in the root tracker. A packaging-only change updates the root entry; a portable source change updates the appropriate dotfiles entry. Changes to both update both.
- Keep each tracker alphabetically sorted, with one `component: DD/MM/YYYY` line per component, using the local date. `unknown` means existing work had no reliable recorded date; do not invent one.
- After changing a component, update only its entry in the same change. Add entries for new projects and remove entries for deleted projects. Keep all package definitions and configuration areas covered when reorganizing the repository.
- Reading, auditing, building or testing a component alone does not reset its date. These are local source-maintenance dates, not upstream release dates or proof that updates and runtime checks have been completed.
- Preserve recorded historical dates when initializing or extending a tracker. Existing uncommitted work without a recorded date remains `unknown` until a substantive change establishes a date.
- Update tracker files as part of the work; commit only when explicitly requested.
