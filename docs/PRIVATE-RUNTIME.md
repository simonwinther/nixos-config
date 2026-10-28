# Private runtime credentials

Existing credentials are reused outside the repository and Nix store. Never add
these files to a Stow package, Nix path literal, environment-variable declaration
or source archive.

- `~/.config/dictate/secrets.env`: existing `OPENAI_API_KEY`, mode 0600.
- `~/.config/hendrix/ku-password`: existing KU password, mode 0600.
- `~/.config/hendrix/totp.json`: selected existing Netiq token (secret, issuer,
  type, algorithm, digits and period), mode 0600. No browser profile is required.
- `~/.config/hendrix/vpn-auth.json`: mode `totp` and last used time counter.
- `~/.ssh/hendrix_pc` and `.pub`: existing Hendrix SSH identity. Keep the private
  key 0600 and `.ssh` 0700. The alias is declared in `modules/home/hendrix.nix`.

`ssh hendrix` uses the portable wrapper, starts the on-demand KU VPN if needed,
then logs in with the existing identity / saved KU password. Only Hendrix and
KU DNS subnets enter the tunnel. Public DNS and the default route stay on the
normal network. SSH inspection (`-G`, `-O`) does not activate the VPN.

The KU service and its narrowly scoped start permission also exist in the live
profile. It has no startup dependency on missing credentials and is not enabled
at boot. The live filesystem remains temporary: restore private state separately
before relying on a reboot. Any recovery copy of credentials on the project SSD
must be encrypted, separate from the public source archive.

The encrypted private recovery bundle is addressed to the existing Hendrix SSH
key. Preserve that original private key independently before erasing Arch; it is
needed to unlock the bundle. The public source archive cannot restore credentials.
The encrypted bundle contains no browser profile or unrelated SSH identities.

Hendrix distributes logins across three gateways. Initial public host keys were
enrolled separately for 10.84.3.160, .168 and .176 through the authenticated KU
VPN, preserving the first accepted .176 key. The shared hostname accepts these
three pinned keys, with strict checking and per-IP checks enabled. They are public
configuration in `hendrix/.config/hendrix/known_hosts`. A later changed key or new
gateway requires review; it is never silently substituted. DIKU documents the
random gateway selection at https://diku-dk.github.io/wiki/slurm-cluster .

Additional approved credentials reuse their existing identities:

- `~/.config/zsh/secrets.zsh`: existing W&B shell key, private mode 0600.
- `~/.netrc`: existing W&B login, private mode 0600.
- `~/.config/gh/hosts.yml`: active GitHub CLI token extracted from the existing
  Arch keyring, mode 0600. The portable Git configuration already delegates
  GitHub and Gist HTTPS authentication to `gh auth git-credential`.
- `~/.config/canvas-mcp/environment`: existing Canvas token and settings, mode
  0600. `canvas-mcp-stdio` loads this private environment for local MCP clients.
  The separately configured, on-demand HTTP service keeps its own environment;
  it does not load the personal stdio token. No background service is added.

Unrelated production SSH identities and browser sessions are not transferred.

The Home Manager `desktop.rebuild` module adds **Super+Ctrl+Alt+N**. It opens
Ghostty and runs `nixos-rebuild-desktop build` against `~/nixos-config`, without
activation. The command has three separate actions:

- `nixos-rebuild-desktop sync` initializes or checks out the submodule commits
  recorded in Git, recursively. It permits clean submodules at different commits,
  reports the before/after revisions, and never pulls branches or updates inputs.
- `nixos-rebuild-desktop build` (also the default with no arguments) requires all
  submodules to match their recorded commits. It builds the selected system
  toplevel, refuses lock-file updates and writes a result link and source record.
- `nixos-rebuild-desktop activate` applies that exact recorded output without
  evaluating or building again. It refuses missing/failed builds, changed source
  revisions, or a changed result link. It uses `test` for `desktop-live` and
  `switch` for installed hosts. Run it only on an approved target.

Every action refuses staged, unstaged or untracked file changes in the checkout
and initialized submodules, including nested ones and changes hidden by Git's
submodule-ignore settings. Commit or stash changes before proceeding; there is
no dirty-tree override. A clean submodule revision mismatch must be resolved by
the separate `sync` action or by committing the intended pointer. Builds also
check for source changes before recording their result. A failed build leaves
no output eligible for activation until another build succeeds.

Private logs under `${XDG_STATE_HOME:-~/.local/state}/nixos-rebuild` include the
repository path and commit, lock SHA256, submodule revisions and all phase output,
including preflight failures. `last-log` and `last-exit-code` record the latest
action. Per-target `*-result` links keep successful outputs alive in the Nix
store, and `*-build` files associate them with their source. Concurrent sync,
build and activation actions are blocked. The terminal keeps the result visible
until Enter is pressed. These commands do not generate an ISO, install NixOS or
write installation media. Customize `desktop.rebuild.key` or `.repository`
declaratively if needed.

Waybar uses the existing OpenWeatherMap credential at
`~/.config/desktop/secrets/weather-key` (0600), copied from the reference machine
without changing it. The credential is private runtime state and belongs only in
the encrypted recovery bundle.
