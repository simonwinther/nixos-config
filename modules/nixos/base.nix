{
  config,
  lib,
  pkgs,
  host,
  profile,
  ...
}:
{
  networking.hostName = lib.mkDefault host;
  time.timeZone = "Europe/Copenhagen";
  i18n.defaultLocale = "en_US.UTF-8";
  console.keyMap = "dk-latin1";
  services.xserver.xkb = {
    layout = "dk";
    variant = "nodeadkeys";
    options = "caps:swapescape";
  };
  nix.settings = {
    experimental-features = [
      "nix-command"
      "flakes"
    ];
    auto-optimise-store = true;
    max-jobs = 1;
    cores = 2;
    extra-substituters = [ "https://hyprland.cachix.org" ];
    extra-trusted-public-keys = [
      "hyprland.cachix.org-1:a7pgxzMz7+chwVL3/pzj6jIBMioiJM7ypFP8PwtkuGc="
    ];
  };
  nix.gc.automatic = false;
  system.autoUpgrade.enable = false;
  system.stateVersion = "26.05";
  users.groups.simon.gid = 1000;
  users.users.simon = {
    isNormalUser = true;
    uid = 1000;
    group = "simon";
    home = "/home/simon";
    description = "Simon";
    shell = pkgs.zsh;
    extraGroups = [
      "wheel"
      "docker"
      "network"
      "nordvpn"
    ];
  };
  users.groups.nordvpn = { };
  programs.zsh.enable = true;
  programs.bash.completion.enable = true;
  services.openssh = {
    enable = true;
    openFirewall = false;
    settings = {
      PasswordAuthentication = false;
      PermitRootLogin = "prohibit-password";
    };
  };
  services.timesyncd.enable = true;
  services.fstrim.enable = profile != "live";
  services.fwupd.enable = profile != "live";
  services.dbus.enable = true;
  security.polkit.enable = true;
  security.rtkit.enable = true;
  boot.kernel.sysctl = {
    "fs.inotify.max_user_watches" = 524288;
    "net.ipv4.tcp_mtu_probing" = 1;
  };
  hardware.enableRedistributableFirmware = true;
  boot.supportedFilesystems = [ "ntfs" ];
  environment.systemPackages = with pkgs; [
    git
    curl
    wget
    rsync
    restic
    cryptsetup
    btrfs-progs
    dosfstools
    exfatprogs
    parted
    efibootmgr
    jq
    ripgrep
    file
    usbutils
    pciutils
    lsof
    openssl
  ];
  zramSwap = {
    enable = lib.mkDefault true;
    memoryPercent = 25;
  };
  services.power-profiles-daemon.enable = true;
  services.logind.settings.Login.HandlePowerKey = "ignore";
  services.udev.extraRules = lib.optionalString config.workstation.laptop ''
    ACTION=="change", SUBSYSTEM=="power_supply", ATTR{type}=="Mains", RUN+="${pkgs.systemd}/bin/systemctl --no-block restart desktop-power-profile.service"
  '';
  systemd.services.desktop-power-profile = lib.mkIf config.workstation.laptop {
    description = "Select the power profile for the current power source";
    after = [ "power-profiles-daemon.service" ];
    path = [
      pkgs.power-profiles-daemon
      pkgs.coreutils
      pkgs.gnugrep
    ];
    serviceConfig.Type = "oneshot";
    script = ''
      if grep -q 1 /sys/class/power_supply/*/online 2>/dev/null; then
        powerprofilesctl set performance || powerprofilesctl set balanced
      else
        powerprofilesctl set balanced
      fi
    '';
    wantedBy = [ "multi-user.target" ];
  };
}
