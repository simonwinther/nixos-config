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
    max-jobs = 2;
    cores = 4;
    extra-substituters = [ "https://hyprland.cachix.org" ];
    extra-trusted-public-keys = [
      "hyprland.cachix.org-1:a7pgxzMz7+chwVL3/pzj6jIBMioiJM7ypFP8PwtkuGc="
    ];
  };
  nix.gc.automatic = false;
  programs.nh = {
    enable = true;
    flake = "${config.users.users.simon.home}/nixos-config";
  };
  # Builds slow down under memory pressure instead of freezing the desktop;
  # past the hard limit only the build is killed.
  systemd.services.nix-daemon.serviceConfig = {
    MemoryHigh = "60%";
    MemoryMax = "75%";
  };
  # The kernel OOM killer reacts only after zram thrashing has frozen the
  # session. earlyoom acts first and sacrifices compilers before the desktop.
  services.earlyoom = {
    enable = true;
    freeMemThreshold = 5;
    freeSwapThreshold = 10;
    enableNotifications = true;
    extraArgs = [
      "--prefer"
      "^(rustc|cargo|cc1|cc1plus|ld|ld\\.lld|mold|clang|nix|nix-daemon|node|tsc)$"
      "--avoid"
      "^(Hyprland|systemd|systemd-.*|dbus-.*|pipewire.*|wireplumber|greetd|desktop-bar|hyprlock)$"
    ];
  };
  system.autoUpgrade.enable = false;
  system.stateVersion = "26.05";
  environment.etc."codex/config.toml".text = ''
    model_context_window = 516000
    ${lib.optionalString (builtins.elem host [ "lambda" "desktop" ]) ''
      [mcp_servers.canvas]
      command = "/etc/profiles/per-user/${config.users.users.simon.name}/bin/canvas-mcp-stdio"
    ''}
  '';
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
      "nordvpn"
    ];
  };
  users.groups.nordvpn = { };
  programs.zsh = {
    enable = true;
    # The Home Manager zsh dotfiles run their own cached compinit and set the
    # oh-my-posh prompt; the system-wide versions only slow every shell down.
    enableGlobalCompInit = lib.mkIf (profile != "recovery") false;
    promptInit = lib.mkIf (profile != "recovery") "";
  };
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
  boot.kernel.sysctl = lib.mkMerge [
    {
      "fs.inotify.max_user_watches" = 524288;
      "net.ipv4.tcp_mtu_probing" = 1;
    }
    # Faulting a page back from zram takes microseconds, far less than
    # rereading it from the encrypted disk. Prefer compressing idle anonymous
    # memory over evicting page cache, skip swap readahead and let kswapd
    # reclaim before allocations stall (kernel vm sysctl docs, ArchWiki zram).
    (lib.mkIf config.zramSwap.enable {
      "vm.swappiness" = lib.mkDefault 180;
      "vm.page-cluster" = lib.mkDefault 0;
      "vm.watermark_boost_factor" = lib.mkDefault 0;
      "vm.watermark_scale_factor" = lib.mkDefault 125;
    })
  ];
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
  # zstd packs lambda's idle memory about 4:1, and the former 25% cap stayed
  # full. The module default lets zram hold up to half the RAM.
  zramSwap.enable = lib.mkDefault true;
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
