{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.desktop.appearance;
  scaled = n: toString (n * cfg.terminalScale);
  padding = n: toString (builtins.floor (n * cfg.terminalScale + 0.5));
  ghostty =
    builtins.replaceStrings
      [ "font-size = 14" "window-padding-x = 6, 6" "window-padding-y = 0, 6" ]
      [
        "font-size = ${scaled 14}"
        "window-padding-x = ${padding 6}, ${padding 6}"
        "window-padding-y = 0, ${padding 6}"
      ]
      (builtins.readFile ../../dotfiles/ghostty/.config/ghostty/config);
in
{
  options.desktop.appearance = {
    barScale = lib.mkOption {
      type = lib.types.numbers.between 0.75 2.0;
      default = 1.0;
      description = "Additional Waybar and workspace pill sizing, independent of display scaling.";
    };
    terminalScale = lib.mkOption {
      type = lib.types.numbers.between 0.75 2.0;
      default = 1.0;
      description = "Size multiplier for Ghostty's personal font and padding.";
    };
  };
  config = {
    home.file.".config/ghostty/config".source = lib.mkForce (pkgs.writeText "ghostty-config" ghostty);
    # Also make a size-only rebuild restart the already running bar processes.
    systemd.user.services.desktop-waybar.Service.Environment = lib.mkAfter [
      "DESKTOP_BAR_SCALE=${toString cfg.barScale}"
    ];
    systemd.user.services.desktop-waybar-minimal.Service.Environment = lib.mkAfter [
      "DESKTOP_BAR_SCALE=${toString cfg.barScale}"
    ];
    systemd.user.services.desktop-workspaces.Service.Environment = lib.mkAfter [
      "DESKTOP_BAR_SCALE=${toString cfg.barScale}"
    ];
  };
}
