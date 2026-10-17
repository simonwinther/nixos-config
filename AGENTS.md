# Configuration rules

- Work only in this isolated repository. The active Arch configuration and original dotfiles are reference sources.
- Home Manager owns links on NixOS; GNU Stow owns links on other distributions. Never manage a target with both.
- Keep portable desktop tools and plain configuration in Stow packages under dotfiles/.
- Never run activation, reload, package installation, disk formatting, or service mutation on the reference laptop.
- Keep credentials and private recovery material outside Git and the Nix store.
- Commit dependency locks and source, never compiled binaries or caches.
- Installation requires a reviewed host hardware inventory and verified independent backups.
