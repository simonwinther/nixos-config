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
      version = "1.5.10";
      wholeVersion = "${version}-5073323990843392";
    in
    {
      inherit version;
      src = pkgs.fetchurl {
        url = "https://storage.googleapis.com/antigravity-public/antigravity-cli/${wholeVersion}/linux-x64/cli_linux_x64.tar.gz";
        sha512 = "98d762e53511cd6a7a7a6369735a97ed63f6333e43b507fee31c7c945b8fb73d4e3f08785815271424e989e0dafb58cf75bc5ad4078ec4d522234ec316d0c745";
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
  canvas-mcp =
    let
      # FastMCP 3 is marked broken with MCP SDK 2; nixpkgs keeps SDK 1 as mcp_1.
      pythonPackages = unstable.python3Packages.overrideScope (final: _: { mcp = final.mcp_1; });
    in
    pythonPackages.buildPythonApplication {
      pname = "canvas-mcp";
      version = "1.12.0";
      pyproject = true;
      src = ./canvas-mcp/source;
      build-system = [ pythonPackages.hatchling ];
      dependencies = with pythonPackages; [
        fastmcp
        mcp
        httpx
        python-dotenv
        pydantic
        python-dateutil
        uvicorn
      ];
      doCheck = false;
      pythonImportsCheck = [
        "canvas_mcp"
        "canvas_mcp.server"
      ];
      meta.mainProgram = "canvas-mcp-server";
    };
  hendrix-vpn =
    let
      share = dots + "/hendrix/.local/share/hendrix";
      # Only the two scripts: with the whole dotfiles tree as input, unrelated
      # edits would change this path and every unit that references it.
      scripts = lib.fileset.toSource {
        root = share;
        fileset = lib.fileset.unions [
          (share + "/ku-vpn")
          (share + "/ku-vpn-routes")
        ];
      };
    in
    pkgs.runCommand "hendrix-vpn"
      {
        nativeBuildInputs = [ pkgs.makeWrapper ];
        # Home Manager links the native ssh launcher as ~/.local/bin/ssh. It
        # stays outside this output, so launcher changes leave the VPN unit alone.
        passthru.launcher = pkgs.rustPlatform.buildRustPackage {
          pname = "hendrix-ssh";
          version = "1.0.0";
          src = share + "/ssh";
          cargoLock.lockFile = share + "/ssh/Cargo.lock";
          meta = {
            description = "Native ssh wrapper that starts the KU VPN for Hendrix on demand";
            mainProgram = "hendrix-ssh";
            platforms = lib.platforms.linux;
          };
        };
      }
      ''
        mkdir -p "$out/bin"
        for name in ku-vpn ku-vpn-routes; do
          cp ${scripts}/"$name" "$out/bin/$name"
          chmod +x "$out/bin/$name"
          patchShebangs "$out/bin/$name"
          wrapProgram "$out/bin/$name" \
            --prefix PATH : ${
              lib.makeBinPath [
                pkgs.bash
                pkgs.coreutils
                pkgs.getent
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
    inherit (pkgs) clang-tools;
  };
  tmux-plugins = pkgs.callPackage ./tmux { };
}
