# Roblox development

The full workstation Home Manager profile installs `packages.roblox-toolchain`.
It contains Rojo 7.7.1, Lune 0.11.1, Selene 0.32.0, Luau LSP 1.70.1,
StyLua 2.6.0, Wally 0.3.2, Rokit 1.2.0 and the `roblox-studio` launcher.
Upstream release archives have fixed hashes; Nix supplies their ELF interpreter
and required libraries. Activation no longer downloads tools through Rokit.

Home Manager links `~/.local/bin/{rojo,lune,selene,stylua,wally,luau-lsp}` to
these builds instead of the portable Rokit wrappers, so project `rokit.toml`,
`aftman.toml` and `foreman.toml` pins are not consulted for those commands.
Spell's pins match; other manifests, such as rojo 7.4.x and the Quenty forks in
`RESOURCE_LIBRARY`, are no longer honoured. `rokit` stays installed. Activation
reinstalls the Rojo 7.7.1 Studio plugin whenever it differs. The Roblox types
come from luau-lsp commit `7a10f6d2`, whose SHA-256 Spell's typecheck verifies.
The `roblox-dev` dotfiles package also provides `roblox-studio-mcp`, Studio's MCP
bridge launcher. These links date from November 2026, after the validation below.
Stow hosts keep the Rokit setup in that package's `SETUP.txt`.

`devShells.x86_64-linux.roblox` provides the same tools, Python with Pillow and
the pinned Roblox types through `SPELL_ROBLOX_TYPES`. Enter with
`nix develop ~/nixos-config#roblox`; no activation is required to use that shell.

The launcher forwards files to the installed Vinegar Flatpak. The existing
Blender/Vinegar installations, Wine prefix, renderer and editor configuration
are retained. Use each game's guarded launcher to enforce its instance policy.
Vinegar forwards flags to Studio: do not use a help flag as a capability probe.

Validation on desktop, 24 October 2026: package build and binary version checks,
Home Manager generation build, Nix formatting/static checks, repository source
validation, and Spell Factory offline checks/place serialization passed.
No configuration activation or engine playtest is implied by these builds.
Apply through the normal approved desktop rebuild when ready.
