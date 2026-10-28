{
  config,
  lib,
  pkgs,
  host,
  profile,
  ...
}:
let
  cfg = config.desktop.rebuild;
  target = if profile == "live" then "${host}-live" else host;
  action = if profile == "live" then "test" else "switch";
  rebuild = pkgs.writeShellApplication {
    name = "nixos-rebuild-desktop";
    runtimeInputs = [
      pkgs.nixos-rebuild
      pkgs.nix
      pkgs.git
      pkgs.coreutils
      pkgs.util-linux
    ];
    text = ''
      repo=${lib.escapeShellArg cfg.repository}
      target=${lib.escapeShellArg target}
      activation_action=${lib.escapeShellArg action}
    ''
    + builtins.readFile ../../scripts/nixos-rebuild-desktop.sh;
  };
in
{
  options.desktop.rebuild = {
    key = lib.mkOption {
      type = lib.types.str;
      default = "SUPER + CTRL + ALT + N";
      description = "Open a terminal and build this machine's NixOS configuration without activation.";
    };
    repository = lib.mkOption {
      type = lib.types.str;
      default = "${config.home.homeDirectory}/nixos-config";
      description = "Clean, locked NixOS Git checkout to build.";
    };
    target = lib.mkOption {
      type = lib.types.str;
      readOnly = true;
      default = target;
    };
    action = lib.mkOption {
      type = lib.types.str;
      readOnly = true;
      default = action;
    };
  };
  config = {
    home.packages = [ rebuild ];
    xdg.configFile."desktop/rebuild-bindings.lua".text = ''
      hl.bind(${builtins.toJSON cfg.key}, hl.dsp.exec_cmd(${builtins.toJSON "${pkgs.ghostty}/bin/ghostty -e ${rebuild}/bin/nixos-rebuild-desktop build"}), { description = "Build NixOS (${target}; no activation)" })
    '';
  };
}
