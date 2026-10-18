{ config, lib, ... }:
let
  cfg = config.workstation.secrets;
in
{
  config = lib.mkIf cfg.enable {
    assertions = [
      {
        assertion = cfg.file != null;
        message = "Supply an actual SOPS-encrypted secrets file before enabling secrets.";
      }
    ];
    sops = {
      defaultSopsFile = if cfg.file == null then throw "Missing encrypted secrets file" else cfg.file;
      age.keyFile = "/var/lib/sops-nix/key.txt";
      secrets = {
        simon-password-hash.neededForUsers = true;
        dictate-env = {
          owner = "simon";
          mode = "0600";
          path = "/home/simon/.config/dictate/secrets.env";
        };
        weather-key = {
          owner = "simon";
          mode = "0600";
          path = "/home/simon/.config/desktop/secrets/weather-key";
        };
      }
      // cfg.additionalFiles;
    };
    users.mutableUsers = false;
    users.users.simon.hashedPasswordFile = config.sops.secrets.simon-password-hash.path;
  };
}
