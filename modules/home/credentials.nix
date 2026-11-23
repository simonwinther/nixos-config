{
  config,
  pkgs,
  host,
  profile,
  lib,
  packages,
  ...
}:
let
  canvas = pkgs.writeShellApplication {
    name = "canvas-mcp-stdio";
    text = ''
      credentials="''${XDG_CONFIG_HOME:-$HOME/.config}/canvas-mcp/environment"
      if [[ ! -r "$credentials" ]]; then
        echo "Canvas credentials are missing: $credentials" >&2
        exit 1
      fi
      set -a
      # shellcheck source=/dev/null
      source "$credentials"
      set +a
      exec ${packages.canvas-mcp}/bin/canvas-mcp-server "$@"
    '';
  };
in
{
  # Authentication stays in mutable private files, never in a derivation.
  home.activation.restoreWorkstationKeys = lib.mkIf (host == "desktop" && profile == "workstation") (
    lib.hm.dag.entryAfter [ "linkGeneration" ] ''
      identity="$HOME/.config/workstation-keys/identity.txt"
      if [[ -f "$identity" ]]; then
        run ${pkgs.coreutils}/bin/env PATH=${lib.makeBinPath [ pkgs.age ]} \
          ${pkgs.python3}/bin/python3 ${../../dotfiles/bin/.local/bin/workstation-keys} \
          restore --identity "$identity"
      fi
    ''
  );
  programs.gh.enable = true;
  home.packages = [ canvas ];
}
