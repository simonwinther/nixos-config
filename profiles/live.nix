{ modulesPath, lib, ... }:
{
  imports = [ (modulesPath + "/installer/cd-dvd/installation-cd-minimal.nix") ];
  networking.hostName = lib.mkForce "desktop-live";
  workstation.secrets.enable = lib.mkForce false;
  users.users.simon.initialHashedPassword = "";
  # The installation-media profile already reserves UID 1000 for nixos.
  users.users.simon.uid = lib.mkForce 1001;
  users.groups.simon.gid = lib.mkForce 1001;
  services.getty.autologinUser = lib.mkForce "simon";
  image.baseName = lib.mkForce "hyprland-desktop-live";
  # Keep ISO packaging within the preparation container's memory budget.
  isoImage.squashfsCompression = "zstd -Xcompression-level 15 -mem 512M";
  boot.zfs.forceImportRoot = false;
  isoImage.volumeID = "DESKTOP_LIVE";
}
