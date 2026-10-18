# Preserving unavailable vendor downloads

Two installer archives were recovered read-only from the laptop's existing package cache and imported into the isolated Docker Nix store. They were not committed to Git, installed, or executed on the laptop.

| Archive | SHA-256 | Current situation |
| --- | --- | --- |
| `Boosteroid-1.10.22-x86_64.deb` | `58a26a24ef0bd642a9f5f57a3d151b4bfc686e1861989522101ff84dae940848` | Vendor URL rejects automated fetching in this environment; installer also has a moving URL |
| `nordvpn-tui_0.1.0_linux_amd64.tar.gz` | `dda52009790cc9996b597bcdd935e7c0a84b139948949dbb4d832d40c37962d2` | Recorded GitHub repository/release returns 404, including through the existing authenticated CLI |

The exact bytes are retained under `.work/vendor/` in this repository's private working area, and as fixed-output source objects in `nixos-config-store`. These files are dependencies, not credentials. Add them to the independent encrypted transfer backup before any migration; an ignored working directory and a Docker volume alone are not backups.

On another Nix machine, restore the archives using the exact filenames above, verify the hashes, and import them with `nix-store --add-fixed sha256 PATH_TO_ARCHIVE` before building. This supplies the source object requested by the hash-pinned recipes without relying on the vanished download. Alternatively, transfer a tested runtime closure with `nix copy` through a private binary cache. Retain the source archives as well so future rebuilds remain possible.

Do not replace a hash with the hash of a different current installer simply to make a build succeed. Review the new application version and its runtime compatibility first. The remainder of the flake uses locked public sources or copied, licensed source code. Flatpak commits and editor marketplace extensions have their own availability limits; archive those artifacts separately as described in the migration runbook.

## Pinned editor archives

All 145 recorded VS Code/Cursor extension entries now have explicit versions, platform labels and source hashes in `pkgs/editor-extensions/sources.json`. Fifteen were supplied from the reference machine's existing download cache, recorded with `retainedArchive: true`; this does not imply every associated public URL is unavailable. Their exact archive filenames and hashes are in that manifest. The private copies are under `.work/editor-vsixs/` and the isolated Nix store. Include these archives in the independent encrypted transfer backup and verify their recorded hashes before relying on future rebuilds. They are not committed binaries.

Restore a cached VSIX with its manifest filename, then use `nix-store --add-fixed sha256 PATH_TO_VSIX` on the builder before building the environment. A tested private `nix copy` closure is another transfer option. Marketplace availability, extension-internal downloads and account/workspace state remain separate from source pinning.
