{
  config,
  lib,
  pkgs,
  host,
  profile,
  ...
}:
{
  imports = [
    ./dotfiles.nix
    ./packages.nix
    ./services.nix
    ./applications.nix
    ./editors.nix
    (../../hosts + "/${host}/home.nix")
  ];
  options.desktop.outputs = {
    full = lib.mkOption {
      type = lib.types.listOf lib.types.str;
      default = [ "*" ];
    };
    minimal = lib.mkOption {
      type = lib.types.listOf lib.types.str;
      default = [ ];
    };
  };
  options.desktop.fullApplications = lib.mkOption {
    type = lib.types.bool;
    default =
      !(builtins.elem profile [
        "live"
        "recovery"
      ]);
    description = "Install the complete recorded application collection, including TeX and SDKs.";
  };
  config = {
    home.username = "simon";
    home.homeDirectory = "/home/simon";
    home.stateVersion = "26.05";
    xdg.enable = true;
    home.sessionPath = [ "$HOME/.local/bin" ];
    home.sessionVariables = {
      DOTFILES =
        if profile == "live" then
          "${../../dotfiles}"
        else
          "${config.home.homeDirectory}/nixos-config/dotfiles";
      EDITOR = "nvim";
      VISUAL = "nvim";
      TERMINAL = "ghostty";
      BROWSER = "chromium";
      CHROME_EXECUTABLE = "chromium";
      EZA_CONFIG_DIR = "${config.xdg.stateHome}/desktop/theme";
    };
    systemd.user.sessionVariables = lib.filterAttrs (
      _: value: value != null
    ) config.home.sessionVariables;
    xdg.configFile."desktop/monitors.lua".source = ../../hosts + "/${host}/monitors.lua";
    xdg.configFile."desktop/bar-outputs.json".text = builtins.toJSON config.desktop.outputs;
    xdg.configFile."desktop/workspaces.json".text = builtins.toJSON {
      output = config.desktop.outputs.full;
    };
    home.activation.desktopStateDirectories = lib.hm.dag.entryAfter [ "writeBoundary" ] ''
      run mkdir -p "$HOME/.local/state/desktop" "$HOME/Pictures" "$HOME/Videos" "$HOME/From iPhone"
    '';
  };
}
