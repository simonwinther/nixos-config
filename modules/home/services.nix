{
  config,
  lib,
  pkgs,
  packages,
  osConfig,
  profile,
  ...
}:
let
  ctl = "${packages.desktop-tools}/bin/desktopctl";
  environment = [
    "PATH=/run/wrappers/bin:${config.home.profileDirectory}/bin:/run/current-system/sw/bin:/home/simon/.local/bin"
    "HYPRSPACE_PLUGIN=${packages.hyprspace}/lib/libhyprspace.so"
    "HENDRIX_VPN_RUNNER=${packages.hendrix-vpn}/bin/ku-vpn"
    "HENDRIX_VPN_ROUTES=${packages.hendrix-vpn}/bin/ku-vpn-routes"
    "DESKTOP_SSH_BIN=${pkgs.openssh}/bin/ssh"
  ];
  service = description: command: {
    Unit = {
      Description = description;
      PartOf = [ "desktop-session.target" ];
      After = [ "desktop-prepare.service" ];
    };
    Service = {
      Type = "exec";
      ExecStart = command;
      Restart = "on-failure";
      RestartSec = 2;
      Environment = environment;
    };
    Install.WantedBy = [ "desktop-session.target" ];
  };
  visibleBar =
    unit:
    unit
    // {
      Unit = unit.Unit // {
        ConditionPathExists = "!${config.xdg.stateHome}/desktop/toggles/bar-off";
      };
    };
  pickerTerminal = {
    Unit = {
      Description = "Prepare the windowless file and PDF picker terminal";
      PartOf = [ "desktop-session.target" ];
      StartLimitIntervalSec = 60;
      StartLimitBurst = 3;
      After = [ "desktop-prepare.service" ];
    };
    Service = {
      Type = "oneshot";
      RemainAfterExit = true;
      ExecStart = "${packages.file-picker}/bin/file-picker --prepare-terminal";
      Environment = environment;
      TimeoutStartSec = 20;
      Restart = "on-failure";
      RestartSec = 2;
    };
    # Start pickers on demand through their shortcuts instead of preloading at login.
    Install = { };
  };
in
{
  # The portable launcher would bypass the package's PATH and GSettings schemas.
  home.file.".local/bin/desktopctl".source = lib.mkForce "${packages.desktop-tools}/bin/desktopctl";
  # Menu shortcuts enter the resident Rust process directly.
  home.file.".local/bin/desktop-bar".source = lib.mkForce "${packages.desktop-bar}/bin/desktop-bar";
  xdg.configFile."desktop/paths.json".text = builtins.toJSON {
    desktop-search-native = "${packages.desktop-search}/bin/desktop-search";
    dictate = "${packages.dictate}/bin/dictate";
    file-picker-native = "${packages.file-picker}/bin/file-picker-native";
    hyprspace = "${packages.hyprspace}/lib/libhyprspace.so";
    mako = "${pkgs.mako}/bin/mako";
    swayosd-server = "${pkgs.swayosd}/bin/swayosd-server";
    background-grid-native = "${packages.background-grid}/bin/background-grid-native";
    dictation-volume-duck-native = "${packages.dictation-volume-duck}/bin/dictation-volume-duck-native";
    clipboard-picker-native = "${packages.clipboard-picker}/bin/clipboard-picker-native";
    plot-native = "${packages.formula-plot}/bin/plot-native";
    cluster-native = "${packages.cluster-tools}/bin/cluster-native";
    iphone-transfer-native = "${packages.iphone-transfer}/bin/iphone-transfer-native";
    desktop-bar-native = "${packages.desktop-bar}/bin/desktop-bar";
    btop = "${pkgs.btop}/bin/btop";
    desktop-transcode = "${packages.desktop-tools}/bin/desktop-transcode";
  };
  systemd.user.targets.desktop-session.Unit = {
    Description = "Personal Hyprland desktop";
    # Home Manager restarts preparation during updates. A Requires dependency
    # would stop this target and its unchanged services, including the monitor
    # manager, without bringing them back when preparation starts again.
    Wants = [ "desktop-prepare.service" ];
    After = [ "desktop-prepare.service" ];
    BindsTo = [ "graphical-session.target" ];
    PartOf = [ "graphical-session.target" ];
  };
  systemd.user.services = {
    desktop-file-picker = pickerTerminal;
    desktop-prepare = {
      Unit = {
        Description = "Prepare writable appearance and browser integration";
        Before = [ "desktop-session.target" ];
        PartOf = [ "desktop-session.target" ];
      };
      Service = {
        Type = "oneshot";
        RemainAfterExit = true;
        ExecStart = "${ctl} prepare";
        Environment = environment;
      };
    };
    desktop-search = service "Desktop search and clipboard providers" "${packages.desktop-search}/bin/desktop-search serve";
    desktop-bar =
      let
        unit = visibleBar (service "Morphing Notch Bar" "${packages.desktop-bar}/bin/desktop-bar");
      in
      unit
      // {
        Unit = unit.Unit // {
          After = [
            "desktop-prepare.service"
            "desktop-search.service"
          ];
          Wants = [ "desktop-search.service" ];
        };
        Service = unit.Service // {
          ExecReload = "${pkgs.coreutils}/bin/kill -USR2 $MAINPID";
        };
      };
    # Why Chromium always uses RAM: a cold start takes 2-3 s before ChatGPT even
    # begins loading. Kept running without windows (about 650 MB idle), project
    # windows open in about 0.6 s. The project-picker extension's background
    # permission keeps it alive after the last window closes. Never restarted by
    # rebuilds, which would close open browser windows.
    desktop-browser = (service "Background browser" "${pkgs.chromium}/bin/chromium --no-startup-window") // {
      Unit = {
        Description = "Background browser";
        PartOf = [ "desktop-session.target" ];
        After = [ "desktop-prepare.service" ];
        X-RestartIfChanged = false;
      };
    };
    desktop-mako = service "Notifications" "${ctl} run mako";
    desktop-awww = service "Wallpaper daemon" "${pkgs.awww}/bin/awww-daemon --no-cache";
    desktop-swayosd = service "Volume and brightness display" "${ctl} run swayosd-server";
    # Keep logind/Wayland sleep coordination running even when idle locking is off.
    # The worker selects the idle listener only when opted in for this session.
    desktop-hypridle = service "Idle and suspend coordination" "${ctl} idle-worker";
    desktop-hyprsunset = (service "Night light" "${pkgs.hyprsunset}/bin/hyprsunset") // {
      Install = { };
    };
    desktop-polkit = service "Privilege prompts" "${pkgs.hyprpolkitagent}/libexec/hyprpolkitagent";
    desktop-fcitx5 = service "Keyboard input method" "${osConfig.i18n.inputMethod.package}/bin/fcitx5 --disable notificationitem";
    desktop-wallpaper = (service "Restore wallpapers" "${ctl} wallpaper restore") // {
      Unit = {
        Description = "Restore wallpapers";
        PartOf = [
          "desktop-session.target"
          "desktop-awww.service"
        ];
        After = [
          "desktop-prepare.service"
          "desktop-awww.service"
        ];
        Requires = [ "desktop-awww.service" ];
      };
      Service = {
        Type = "oneshot";
        RemainAfterExit = true;
        ExecStart = "${ctl} wallpaper restore";
        Environment = environment;
      };
    };
    desktop-lock = {
      Unit.Description = "Lock session and turn displays off";
      Service = {
        Type = "exec";
        ExecStart = "${ctl} lock-worker";
        Environment = environment;
      };
    };
    desktop-lock-only = {
      Unit.Description = "Lock session";
      Service = {
        Type = "exec";
        ExecStart = "${ctl} lock-worker --only";
        Environment = environment;
      };
    };
    desktop-battery = {
      Unit.Description = "Low battery notifications";
      Service = {
        Type = "oneshot";
        ExecStart = "${ctl} battery --notify";
        Environment = environment;
      };
    };
    breakd = lib.mkIf (profile != "live" && profile != "recovery") (
      service "Break reminders and posture coaching" "${packages.breakd}/bin/breakd daemon"
    );
    canvas-mcp = lib.mkIf (profile != "live" && profile != "recovery") {
      Unit = {
        Description = "Canvas MCP HTTP server (on demand, loopback only)";
        ConditionPathExists = "/home/simon/.config/canvas-mcp/http-environment";
      };
      Service = {
        Type = "exec";
        ExecStart = "${packages.canvas-mcp}/bin/canvas-mcp-server --transport streamable-http --host 127.0.0.1 --port 8819";
        EnvironmentFile = "/home/simon/.config/canvas-mcp/http-environment";
        Environment = environment;
        Restart = "on-failure";
      };
    };
    taildrop-receive = lib.mkIf (profile != "live" && profile != "recovery") (
      (service "Receive and sort iPhone Taildrop files" "${packages.iphone-transfer}/bin/iphone-transfer-native receive")
      // {
        Service = {
          Type = "exec";
          ExecStart = "${packages.iphone-transfer}/bin/iphone-transfer-native receive";
          Restart = "always";
          RestartSec = 5;
          UMask = "0077";
          Environment = environment;
        };
      }
    );
  };
  systemd.user.timers.desktop-battery = {
    Unit = {
      Description = "Monitor battery level";
      PartOf = [ "desktop-session.target" ];
    };
    Timer = {
      OnBootSec = "2m";
      OnUnitActiveSec = "1m";
    };
    Install.WantedBy = [ "desktop-session.target" ];
  };
}
