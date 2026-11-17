# Vendor sources and pins

## NordVPN TUI source

The GitHub repository `simonwinther/nordvpn-tui` and its `v0.1.0` release archive (SHA-256 `dda52009790cc9996b597bcdd935e7c0a84b139948949dbb4d832d40c37962d2`) were deleted, and the archive is not in any store or backup on lambda. Since 2026-11-17 the package builds from the tagged source vendored in `pkgs/nordvpn-tui/source` (see the table below) with `buildGoModule`, so nixpkgs updates no longer need the archive.

## Private flake input

`ferry` is locked to `git+ssh://git@github.com/simonwinther/ferry` at `0ef83bbc5672c553fbc4cc40a3d27a424856d71c`. The repository is private; unauthenticated HTTPS returns 404. Evaluating a configuration that installs ferry (desktop and lambda) reads its `Cargo.lock` from that source, so a machine whose store lacks the locked source needs SSH access to the repository first. Flatpak commits have their own availability limits; see [MIGRATION.md](MIGRATION.md).

## Vendored source trees

| Tree | Upstream | Commit | `fetchFromGitHub` hash | Omitted files |
| --- | --- | --- | --- | --- |
| `pkgs/canvas-mcp/source` | `vishalsachdev/canvas-mcp` tag `v1.12.0` | `332fd057ab4cb0835f07cce65b6f608194fac371` | `sha256-d1KGsdly6vmD+BHserVIvsqb+VJBCo6r9cw93TYD8FA=` | `.github/`, `AGENTS.md`, `CLAUDE.md`, `config/overlays/*.env` |
| `pkgs/nordvpn-tui/source` | local checkout `~/dev/system/nordvpn-tui` tag `v0.1.0` (upstream deleted) | `f42fb74aca4a581aedc31665f351c6b8c578d072` | `nix hash path`: `sha256-jCI4JwxVcf8gGuFnvLjpwuNlqN3rTEqyKylMKqETLqg=` | `.github/`, `bin/` (prebuilt binary) |
| `pkgs/breakd/source` | `simonwinther/breakd` branch `migration/lambda-20261025` | `c69f9b013c96de40469586cfdf6dd863b38b950f` | `sha256-eeFDlMSrpAZentuNylxBGPC0UOUV9kMK5zLN+rGtCLM=` | `.github/`, `docs/` |

All other files match those commits. The original breakd capture, with per-file hashes, is the `vendorSourceCaptures` entry in [current-reference.json](inventory/current-reference.json). The `breakd` flake input pins the older commit `e912976` and does not build this package.

## Bumping binary pins

Edit the version, then hash the new download with `nix store prefetch-file --hash-type sha256 URL`; antigravity-cli uses `sha512`, and its URL also carries a build number in `wholeVersion`. `fetchurl` accepts the printed SRI hash, and `nix hash convert --to base16 HASH` gives the hex form most recipes use. The opencode and antigravity-cli overrides are only useful while unstable ships an older release. Keep the Roblox tool versions equal to the project `rokit.toml` files and Spell's version checks, and change the luau-lsp types URL and hash together with Spell's typecheck pin.

## Pinned editor archives

All 145 recorded VS Code/Cursor extension entries now have explicit versions, platform labels and source hashes in `pkgs/editor-extensions/sources.json`. Fifteen were supplied from the reference machine's existing download cache, recorded with `retainedArchive: true`; this does not imply every associated public URL is unavailable. Their exact archive filenames and hashes are in that manifest. The private copies were kept under `.work/editor-vsixs/` and the isolated Nix store during the migration; that directory does not exist on `lambda` (checked 17/11/2026). Include these archives in the independent encrypted transfer backup and verify their recorded hashes before relying on future rebuilds. They are not committed binaries.

Restore a cached VSIX with its manifest filename, then use `nix-store --add-fixed sha256 PATH_TO_VSIX` on the builder before building the environment. A tested private `nix copy` closure is another transfer option. The marketplace serves VSIX downloads with `Content-Encoding: gzip`, and the locked hashes cover the decoded archive, so `pkgs/editor-extensions` fetches with `curl --compressed`; without it every marketplace fetch fails its hash. Marketplace availability, extension-internal downloads and account/workspace state remain separate from source pinning.
