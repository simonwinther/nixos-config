{
  config,
  lib,
  pkgs,
  inputs,
  profile,
  ...
}:
let
  cfg = config.workstation;
  live = profile == "live";
  existing = cfg.storage.existingBtrfs;
  subvolumes = {
    root = "/";
    home = "/home";
    nix = "/nix";
    log = "/var/log";
    snapshots = "/.snapshots";
  };
  diskReady =
    cfg.hardwareReviewed
    && cfg.backupsVerified
    && cfg.gpu != "unreviewed"
    && cfg.targetDisk != null
    && lib.hasPrefix "/dev/disk/by-id/" cfg.targetDisk;
in
{
  # Use the configured Danish keyboard at the disk-unlock prompt too.
  console.earlySetup = lib.mkIf (!live) true;
  boot.loader = lib.mkIf (!live) {
    systemd-boot = {
      enable = true;
      configurationLimit = 10;
    };
    efi.canTouchEfiVariables = true;
    timeout = 5;
  };
  boot.plymouth = lib.mkIf (!live) {
    enable = true;
    theme = "bgrt";
  };
  # Reusing an existing filesystem must never generate Disko formatting commands.
  disko.devices = lib.mkIf (!live && diskReady && existing == null) {
    disk.system = {
      type = "disk";
      device = cfg.targetDisk;
      content = {
        type = "gpt";
        partitions = {
          ESP = {
            size = "2G";
            type = "EF00";
            content = {
              type = "filesystem";
              format = "vfat";
              mountpoint = "/boot";
              mountOptions = [ "umask=0077" ];
            };
          };
          root = {
            size = "100%";
            content = {
              type = "luks";
              name = "cryptroot";
              settings.allowDiscards = true;
              content = {
                type = "btrfs";
                extraArgs = [
                  "-L"
                  "nixos"
                ];
                subvolumes =
                  lib.mapAttrs
                    (_: mountpoint: {
                      inherit mountpoint;
                      mountOptions = [
                        "compress=zstd:3"
                        "noatime"
                      ];
                    })
                    {
                      "@root" = "/";
                      "@home" = "/home";
                      "@nix" = "/nix";
                      "@log" = "/var/log";
                      "@snapshots" = "/.snapshots";
                    };
              };
            };
          };
        };
      };
    };
  };
  fileSystems = lib.mkIf (!live && existing != null) (
    lib.mapAttrs' (
      name: mountpoint:
      lib.nameValuePair mountpoint {
        device = "/dev/disk/by-uuid/${existing.filesystemUuid}";
        fsType = "btrfs";
        options = [
          "subvol=${existing.subvolumePrefix}-${name}"
          "compress=zstd:3"
          "noatime"
        ];
      }
    ) subvolumes
    // {
      "/boot" = {
        device = "/dev/disk/by-uuid/${existing.espUuid}";
        fsType = "vfat";
        options = [ "umask=0077" ];
      };
    }
  );
  boot.initrd.luks.devices = lib.mkIf (!live && existing != null) {
    cryptroot = {
      device = "/dev/disk/by-uuid/${existing.luksUuid}";
      allowDiscards = true;
    };
  };
  # Snapper needs a nested Btrfs subvolume before its first timeline snapshot.
  systemd.tmpfiles.rules = lib.mkIf (!live && cfg.targetDisk != null) [
    "v /home/.snapshots 0750 root root -"
  ];
  services.snapper.configs.home = lib.mkIf (!live && cfg.targetDisk != null) {
    SUBVOLUME = "/home";
    ALLOW_USERS = [ "simon" ];
    TIMELINE_CREATE = true;
    TIMELINE_CLEANUP = true;
    TIMELINE_LIMIT_HOURLY = 0;
    TIMELINE_LIMIT_DAILY = 7;
    TIMELINE_LIMIT_WEEKLY = 4;
    TIMELINE_LIMIT_MONTHLY = 0;
    TIMELINE_LIMIT_YEARLY = 0;
  };
  services.restic.backups.workstation =
    lib.mkIf (!live && cfg.backup.repository != null && cfg.backup.passwordFile != null)
      {
        repository = cfg.backup.repository;
        passwordFile = cfg.backup.passwordFile;
        paths = [ "/home" ];
        exclude = [
          "/home/*/.cache"
          "/home/*/.local/share/Trash"
          "/home/.snapshots"
        ];
        initialize = true;
        timerConfig = {
          OnCalendar = "daily";
          Persistent = true;
        };
        pruneOpts = [
          "--keep-daily 7"
          "--keep-weekly 4"
          "--keep-monthly 6"
        ];
      };
}
