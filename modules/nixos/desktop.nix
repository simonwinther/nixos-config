{
  config,
  lib,
  pkgs,
  inputs,
  packages,
  host,
  profile,
  ...
}:
let
  desktop = profile != "recovery";
  live = profile == "live";
  compositor = packages.hyprspace.compositor;
  # UWSM reads its launcher; the capability wrapper is intentionally execute-only.
  sessionLauncher = pkgs.writeShellScriptBin "Hyprland" ''
    exec /run/wrappers/bin/Hyprland "$@"
  '';
  lockOnLogin = pkgs.writeShellScript "desktop-lock-on-login" ''
    export PATH="${
      lib.makeBinPath [
        pkgs.hyprlock
        compositor
      ]
    }:$PATH"
    exec ${packages.desktop-tools}/bin/desktopctl lock-worker --only
  '';
in
{
  config = lib.mkIf desktop {
    programs.hyprland = {
      enable = true;
      package = compositor;
      portalPackage =
        inputs.hyprland.packages.${pkgs.stdenv.hostPlatform.system}.xdg-desktop-portal-hyprland;
      withUWSM = true;
      xwayland.enable = true;
    };
    programs.uwsm.waylandCompositors.desktop = {
      prettyName = "Hyprland Desktop";
      comment = "Personal Hyprland session managed by UWSM";
      binPath = "${sessionLauncher}/bin/Hyprland";
      extraArgs = lib.optionals (!live) [
        "--locked-cmd"
        "${lockOnLogin}"
      ];
    };
    services.displayManager = {
      defaultSession = "desktop-uwsm";
      autoLogin = {
        enable = true;
        user = "simon";
      };
      sddm = {
        enable = true;
        wayland.enable = true;
        theme = "breeze";
      };
    };
    security.pam.services.hyprlock = { };
    security.pam.services.sddm.enableGnomeKeyring = true;
    services.gnome.gnome-keyring.enable = true;
    programs.dconf.enable = true;
    services.gvfs.enable = true;
    services.udisks2.enable = true;
    services.upower.enable = true;
    services.blueman.enable = false;
    hardware.bluetooth = {
      enable = true;
      powerOnBoot = true;
    };
    services.pipewire = {
      enable = true;
      alsa = {
        enable = true;
        support32Bit = true;
      };
      pulse.enable = true;
      jack.enable = true;
      wireplumber.extraConfig."51-soft-mixer" = {
        "monitor.alsa.rules" = [
          {
            matches = [ { "device.name" = "~alsa_card.*"; } ];
            actions.update-props."api.alsa.soft-mixer" = true;
          }
        ];
      };
    };
    services.pulseaudio.enable = false;
    hardware.graphics = {
      enable = true;
      enable32Bit = true;
    };
    # Keep Mesa and its video drivers on the system package set so their
    # libva interface matches Chromium and the rest of the desktop.
    hardware.nvidia = lib.mkIf (config.workstation.gpu == "nvidia") {
      modesetting.enable = true;
      open = config.workstation.nvidiaOpen;
      nvidiaSettings = true;
      package = lib.mkDefault config.boot.kernelPackages.nvidiaPackages.stable;
    };
    services.xserver.videoDrivers = lib.mkIf (config.workstation.gpu == "nvidia") [ "nvidia" ];
    fonts = {
      enableDefaultPackages = true;
      packages = with pkgs; [
        nerd-fonts.jetbrains-mono
        nerd-fonts.caskaydia-mono
        nerd-fonts.symbols-only
        font-awesome
        liberation_ttf
        adwaita-fonts
        noto-fonts
        noto-fonts-cjk-sans
        noto-fonts-color-emoji
        ia-writer-mono
        ia-writer-duospace
        ia-writer-quattro
      ];
      fontconfig.defaultFonts = {
        monospace = [ "JetBrainsMono Nerd Font" ];
        sansSerif = [ "Liberation Sans" ];
        serif = [ "Liberation Serif" ];
        emoji = [ "Noto Color Emoji" ];
      };
    };
    xdg.portal = {
      enable = true;
      extraPortals = [ pkgs.xdg-desktop-portal-gtk ];
      config.common.default = [
        "hyprland"
        "gtk"
      ];
    };
    i18n.inputMethod = {
      enable = true;
      type = "fcitx5";
      fcitx5 = {
        addons = [ pkgs.fcitx5-gtk ];
        # Hyprland provides the native Wayland input-method frontend. Global
        # GTK/QT_IM_MODULE overrides bypass it and trigger Fcitx's warning.
        waylandFrontend = true;
      };
    };
    services.printing = {
      enable = true;
      browsing = true;
      browsed.enable = true;
      drivers = [
        pkgs.gutenprint
        pkgs.cups-filters
      ];
      cups-pdf.enable = !live;
    };
    services.avahi = {
      enable = true;
      nssmdns4 = true;
      openFirewall = true;
    };
    programs._1password.enable = !live;
    programs._1password-gui = {
      enable = !live;
      polkitPolicyOwners = [ "simon" ];
    };
    services.flatpak.enable = true;
    boot.kernelModules = lib.optional (!live) "ntsync";
    programs.nix-ld.libraries = lib.optionals (!live) [ pkgs.stdenv.cc.cc.lib pkgs.openssl pkgs.zlib ];
    # Home Manager waits for the initial Flatpak downloads. Android Studio alone
    # can exceed its upstream five-minute activation deadline.
    systemd.services.home-manager-simon.serviceConfig.TimeoutStartSec = lib.mkForce "30min";
    services.udev.packages = [ pkgs.brightnessctl ];
    programs.ydotool.enable = true;
    users.users.simon.extraGroups = [ config.programs.ydotool.group ];
    programs.gpu-screen-recorder.enable = true;
    programs.steam.enable = !live;
    programs.appimage = {
      enable = !live;
      binfmt = !live;
    };
    programs.nix-ld.enable = !live;
    qt = {
      enable = true;
      platformTheme = "gtk2";
      style = "adwaita-dark";
    };
    environment.sessionVariables = {
      NIXOS_OZONE_WL = "1";
      MOZ_ENABLE_WAYLAND = "1";
      NAUTILUS_4_EXTENSION_DIR = "${pkgs.nautilus-python}/lib/nautilus/extensions-4";
    };
  };
}
