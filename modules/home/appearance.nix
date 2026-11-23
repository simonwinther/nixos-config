{
  config,
  lib,
  pkgs,
  packages,
  ...
}:
let
  cfg = config.desktop.appearance;
  wallpaper = "${config.xdg.dataHome}/wallpapers/forest-green/7-FG.jpg";
  preferences = pkgs.writeText "desktop-appearance.json" (
    builtins.toJSON {
      bar = "native-motion";
      theme = "forest-green";
      terminalTheme = true;
      desktopTheme = true;
      inherit wallpaper;
      wallpapers."*" = wallpaper;
    }
  );
  applyPreferences = pkgs.writeText "apply-desktop-appearance.py" ''
    import json
    import sys
    from pathlib import Path

    sys.path.insert(0, "${packages.desktop-tools}/share/desktop-tools")
    import desktopctl

    with desktopctl.state_lock():
        state = desktopctl.load_state()
        state.update(json.loads(Path("${preferences}").read_text()))
        desktopctl.save_state(state)
  '';
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
      description = "Desktop bar sizing, independent of display scaling.";
    };
    terminalScale = lib.mkOption {
      type = lib.types.numbers.between 0.75 2.0;
      default = 1.0;
      description = "Size multiplier for Ghostty's personal font and padding.";
    };
  };
  config = {
    home.activation.desktopAppearance =
      lib.hm.dag.entryBetween [ "reloadSystemd" ] [ "linkGeneration" ]
        ''
          run ${pkgs.python3}/bin/python3 -I ${applyPreferences}
        '';
    systemd.user.services = lib.genAttrs [ "desktop-prepare" "desktop-bar" "desktop-wallpaper" ] (
      name:
      {
        Unit.X-Restart-Triggers = [
          "${preferences}"
          (toString config.xdg.configFile."desktop/bar-outputs.json".source)
        ];
      }
      // lib.optionalAttrs (name == "desktop-bar") {
        Service.Environment = lib.mkAfter [ "DESKTOP_BAR_SCALE=${toString cfg.barScale}" ];
      }
    );
    home.file.".config/ghostty/config".source = lib.mkForce (pkgs.writeText "ghostty-config" ghostty);
  };
}
