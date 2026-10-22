{
  config,
  pkgs,
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
  programs.gh.enable = true;
  home.packages = [ canvas ];
}
