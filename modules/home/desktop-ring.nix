{
  config,
  lib,
  pkgs,
  packages,
  host,
  ...
}:
let
  cfg = config.desktop.ring;
  json = pkgs.formats.json { };
  binary = "${packages.desktop-ring}/bin/desktop-ring";
  bind = key: command: description: ''
    hl.unbind(${builtins.toJSON key})
    hl.bind(${builtins.toJSON key}, hl.dsp.exec_cmd(${builtins.toJSON command}), { description = ${builtins.toJSON description} })
  '';
in
{
  options.desktop.ring = {
    enable = lib.mkEnableOption "the hardware-aware desktop control ring" // {
      default = true;
    };
    menuKey = lib.mkOption {
      type = lib.types.str;
      default = "SUPER + R";
      description = "Hyprland key for the universal pie menu.";
    };
    cycleKey = lib.mkOption {
      type = lib.types.str;
      default = "SUPER + CTRL + ALT + M";
      description = "Laptop-only layout cycle key.";
    };
    settings = lib.mkOption {
      type = json.type;
      default = { };
      description = "Declarative subsystem settings and fixed monitor profiles; runtime preferences are stored separately.";
    };
  };
  config = lib.mkIf cfg.enable {
    desktop.ring.settings = {
      monitors = lib.mkDefault true;
      laptop = lib.mkDefault (host == "lambda");
      audio = lib.mkDefault true;
      bluetooth = lib.mkDefault true;
      power = lib.mkDefault true;
      move_streams = lib.mkDefault false;
      internal_scale = lib.mkDefault (if host == "lambda" then 1.2 else 1.0);
      fixed_profiles = lib.mkDefault (
        builtins.fromJSON (builtins.readFile (../../hosts + "/${host}/monitor-profiles.json"))
      );
      laptop_preferences = lib.mkDefault (
        builtins.fromJSON (builtins.readFile (../../hosts + "/${host}/laptop-monitors.json"))
      );
      theme = {
        background = lib.mkDefault "#000000";
        foreground = lib.mkDefault "#a9b1d6";
        accent = lib.mkDefault "#7aa2f7";
        font = lib.mkDefault "Adwaita Sans";
        icon_font = lib.mkDefault "Symbols Nerd Font";
        radius = lib.mkDefault 214;
        animation_ms = lib.mkDefault 140;
        follow_desktop_palette = lib.mkDefault true;
      };
    };
    home.packages = [ packages.desktop-ring ];
    xdg.configFile."desktop/ring.json".source = json.generate "desktop-ring.json" cfg.settings;
    xdg.configFile."desktop/ring-bindings.lua".text =
      bind cfg.menuKey "${binary} menu" "Desktop control ring"
      + lib.optionalString cfg.settings.laptop (
        bind cfg.cycleKey "${binary} cycle" "Cycle laptop position"
      );
    systemd.user.services.desktop-ring = {
      Unit = {
        Description = "Hardware-aware displays and desktop control ring";
        PartOf = [ "desktop-session.target" ];
        After = [ "desktop-prepare.service" ];
      };
      Service = {
        Type = "exec";
        ExecStart = "${binary} daemon";
        ExecReload = "${binary} rescan";
        Restart = "on-failure";
        RestartSec = 2;
        UMask = "0077";
        Environment = [ "DESKTOP_RING_CONFIG=${config.xdg.configFile."desktop/ring.json".source}" ];
      };
      Install.WantedBy = [ "desktop-session.target" ];
    };
  };
}
