{ lib, ... }:
{
  workstation = {
    hardwareReviewed = true;
    # The verified stationary copy is the backup accepted by Simon.
    backupsVerified = true;
    targetDisk = "/dev/disk/by-id/nvme-SAMSUNG_MZVLB512HBJQ-000L7_S4ENNX0NA23022";
    gpu = "amd";
  };
  disko.devices.disk.system.content.partitions.root.content.passwordFile = "/run/lambda-luks.key";
  # Simon uses the stationary as his sole data fallback.
  services.snapper.configs = lib.mkForce { };
  services.snapper.snapshotRootOnBoot = lib.mkForce false;
  services.restic.backups = lib.mkForce { };
  users.users.simon.hashedPasswordFile = "/var/lib/private/lambda-simon-password-hash";
  users.users.root.hashedPasswordFile = "/var/lib/private/lambda-root-password-hash";
  users.users.simon.openssh.authorizedKeys.keys = [ "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIJvPjEiNHFmm+Z08iiyR5cqocvccwodvd4rLXIqgk7MN" ];
}
