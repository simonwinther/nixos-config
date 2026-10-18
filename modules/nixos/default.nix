{
  config,
  lib,
  host,
  profile,
  ...
}:
let
  inherit (lib) mkOption types;
  live = profile == "live";
in
{
  imports = [
    ./base.nix
    ./desktop.nix
    ./network.nix
    ./storage.nix
    ./secrets.nix
    ./vpn.nix
  ];
  options.workstation = {
    hardwareReviewed = mkOption {
      type = types.bool;
      default = false;
    };
    backupsVerified = mkOption {
      type = types.bool;
      default = false;
    };
    targetDisk = mkOption {
      type = types.nullOr types.str;
      default = null;
    };
    gpu = mkOption {
      type = types.enum [
        "unreviewed"
        "amd"
        "intel"
        "nvidia"
      ];
      default = "unreviewed";
    };
    nvidiaOpen = mkOption {
      type = types.bool;
      default = false;
    };
    laptop = mkOption {
      type = types.bool;
      default = host == "lambda";
    };
    secrets.enable = mkOption {
      type = types.bool;
      default = false;
    };
    secrets.file = mkOption {
      type = types.nullOr types.path;
      default = null;
    };
    secrets.additionalFiles = mkOption {
      default = { };
      description = "Additional named SOPS entries to provision as private runtime files.";
      type = types.attrsOf (
        types.submodule {
          options = {
            path = mkOption { type = types.str; };
            owner = mkOption {
              type = types.str;
              default = "simon";
            };
            mode = mkOption {
              type = types.str;
              default = "0600";
            };
          };
        }
      );
    };
    backup.repository = mkOption {
      type = types.nullOr types.str;
      default = null;
    };
    backup.passwordFile = mkOption {
      type = types.nullOr types.str;
      default = null;
    };
  };
  config = {
    assertions = lib.optionals (!live) [
      {
        assertion = config.workstation.hardwareReviewed;
        message = "${host}: hardware inventory has not been reviewed; installation is deliberately disabled.";
      }
      {
        assertion = config.workstation.backupsVerified;
        message = "${host}: independent backup restoration has not been verified.";
      }
      {
        assertion = config.workstation.targetDisk != null;
        message = "${host}: select the physical target using /dev/disk/by-id after reviewing its serial and size.";
      }
      {
        assertion =
          config.workstation.targetDisk == null
          || lib.hasPrefix "/dev/disk/by-id/" config.workstation.targetDisk;
        message = "The installation disk must use a persistent /dev/disk/by-id identifier.";
      }
      {
        assertion = config.workstation.gpu != "unreviewed";
        message = "${host}: select and validate the graphics driver from the hardware inventory.";
      }
    ];
  };
}
