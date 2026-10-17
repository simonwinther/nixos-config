{
  inputs,
  pkgs,
  unstable,
}:
let
  inherit (pkgs) lib;
  dots = ../dotfiles;
  tools = pkgs.callPackage ./desktop-tools.nix { };
  companions = import ./hyprspace-companions { inherit inputs pkgs unstable; };
in
(import ./extra-apps.nix { inherit pkgs unstable; })
// {
  desktop-tools = tools;
  background-grid = pkgs.callPackage ./background-grid.nix { };
  dictate = pkgs.callPackage ./dictate.nix {
    hyprland = inputs.hyprspace.packages.${pkgs.stdenv.hostPlatform.system}.hyprspace.compositor;
  };
  file-picker = pkgs.callPackage ./file-picker.nix {
    hyprland = inputs.hyprspace.packages.${pkgs.stdenv.hostPlatform.system}.hyprspace.compositor;
  };
  workspaces-slider = pkgs.callPackage ./workspaces-slider.nix { };
  walker = companions.walker;
  elephant = companions.elephant;
  hyprspace = inputs.hyprspace.packages.${pkgs.stdenv.hostPlatform.system}.hyprspace;
  waybar = pkgs.waybar.overrideAttrs (old: {
    patches = (old.patches or [ ]) ++ [
      (dots + "/waybar/.config/waybar/tray-fix/electron-properties.patch")
    ];
  });
  breakd = (unstable.callPackage ./breakd/source/packaging/nix/package.nix { }).overrideAttrs (old: {
    # Unix-domain socket fixtures exceed SUN_LEN under Nix's long build paths.
    preCheck = (old.preCheck or "") + ''
      export TMPDIR=/tmp
    '';
  });
  canvas-mcp = unstable.python3Packages.buildPythonApplication {
    pname = "canvas-mcp";
    version = "1.12.0";
    pyproject = true;
    src = ./canvas-mcp/source;
    build-system = [ unstable.python3Packages.hatchling ];
    dependencies = with unstable.python3Packages; [
      fastmcp
      mcp
      httpx
      python-dotenv
      pydantic
      python-dateutil
      uvicorn
    ];
    nativeBuildInputs = [ unstable.python3Packages.pythonRelaxDepsHook ];
    pythonRelaxDeps = true;
    doCheck = false;
    pythonImportsCheck = [
      "canvas_mcp"
      "canvas_mcp.server"
    ];
    meta.mainProgram = "canvas-mcp-server";
  };
  hendrix-vpn =
    pkgs.runCommand "hendrix-vpn"
      {
        nativeBuildInputs = [ pkgs.makeWrapper ];
      }
      ''
        mkdir -p "$out/bin"
        for name in ku-vpn ku-vpn-routes; do
          cp ${dots}/hendrix/.local/share/hendrix/"$name" "$out/bin/$name"
          chmod +x "$out/bin/$name"
          patchShebangs "$out/bin/$name"
          wrapProgram "$out/bin/$name" \
            --prefix PATH : ${
              lib.makeBinPath [
                pkgs.bash
                pkgs.coreutils
                pkgs.glibc.bin
                pkgs.openconnect
                pkgs.systemd
                pkgs.iproute2
                pkgs.gnugrep
                pkgs.gawk
                pkgs.gnused
              ]
            }:"$out/bin" \
            --set VPNC_SCRIPT ${pkgs.vpnc-scripts}/bin/vpnc-script
        done
      '';
  neovim-plugins = pkgs.callPackage ./neovim { };
  tmux-plugins = pkgs.callPackage ./tmux { };
}
