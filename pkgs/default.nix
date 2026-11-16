{
  inputs,
  pkgs,
  unstable,
}:
let
  inherit (pkgs) lib;
  dots = ../dotfiles;
  projectPicker = pkgs.callPackage ./project-picker.nix { };
  transcode = pkgs.callPackage ./desktop-transcode.nix { };
  tools = pkgs.callPackage ./desktop-tools.nix {
    project-picker-tui = projectPicker;
    desktop-transcode = transcode;
  };
  hyprspace = import ./hyprspace { inherit inputs; };
  search = pkgs.callPackage ./desktop-search.nix { rustPlatform = unstable.rustPlatform; };
  compositor = hyprspace.compositor;
in
(import ./extra-apps.nix { inherit pkgs unstable; })
// (pkgs.callPackage ./roblox-dev { })
// (import ./rust-desktop-tools.nix { inherit pkgs; })
// {
  antigravity-cli = unstable.antigravity-cli.overrideAttrs (
    old:
    let
      version = "1.5.5";
      wholeVersion = "${version}-6740358537805824";
    in
    {
      inherit version;
      src = pkgs.fetchurl {
        url = "https://storage.googleapis.com/antigravity-public/antigravity-cli/${wholeVersion}/linux-x64/cli_linux_x64.tar.gz";
        sha512 = "746a2bd73f83b65d9b44f2fc55d0f0f511ff7f89702846213eeabd76d06bc9c98576b424c2babc7b947f15e518447b946ba02dca260b778363c55c07a7f7a277";
      };
      passthru = old.passthru // {
        inherit wholeVersion;
      };
      meta = old.meta // {
        platforms = [ "x86_64-linux" ];
      };
    }
  );
  slicer3d = pkgs.callPackage ./slicer3d.nix { };
  opencode = pkgs.callPackage ./opencode.nix { };
  desktop-tools = tools;
  desktop-search = search;
  desktop-bar = pkgs.callPackage ./desktop-bar.nix { rustPlatform = unstable.rustPlatform; };
  clipboard-picker = pkgs.callPackage ./clipboard-picker.nix { hyprland = compositor; };
  desktop-transcode = transcode;
  obs-font = pkgs.callPackage ./obs-font.nix { };
  obs-studio = import ./obs-studio.nix {
    inherit pkgs;
    obs-studio = unstable.obs-studio;
  };
  project-picker-tui = projectPicker;
  desktop-ring = pkgs.callPackage ./desktop-ring.nix { rustPlatform = unstable.rustPlatform; };
  uipro = pkgs.callPackage ./uipro { };
  ferry = pkgs.callPackage ./ferry.nix { source = inputs.ferry; };
  background-grid = pkgs.callPackage ./background-grid.nix { hyprland = compositor; };
  dictate = pkgs.callPackage ./dictate.nix {
    hyprland = compositor;
  };
  file-picker = pkgs.callPackage ./file-picker.nix {
    hyprland = compositor;
  };
  inherit hyprspace;
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
            --set HENDRIX_SPLIT_TUNNEL_V1 1 \
            --set VPNC_SCRIPT ${pkgs.vpnc-scripts}/bin/vpnc-script
        done
      '';
  neovim-plugins = pkgs.callPackage ./neovim { };
  editor-extensions = import ./editor-extensions {
    inherit lib;
    pkgs = unstable;
  };
  tmux-plugins = pkgs.callPackage ./tmux { };
}
