{
  config,
  lib,
  pkgs,
  inputs,
  profile,
  ...
}:
let
  inventory = builtins.fromJSON (builtins.readFile ../../docs/inventory/flatpak.json);
in
{
  imports = [ inputs.nix-flatpak.homeManagerModules.nix-flatpak ];
  dconf.settings."org/gnome/desktop/interface" = {
    font-name = "Liberation Sans 11";
    monospace-font-name = "JetBrainsMono Nerd Font 11";
  };
  services.flatpak = lib.mkIf config.desktop.fullApplications {
    enable = true;
    uninstallUnmanaged = false;
    update.auto.enable = false;
    remotes = [
      {
        name = "flathub";
        location = "https://dl.flathub.org/repo/flathub.flatpakrepo";
      }
      {
        name = "GeForceNOW";
        location = "https://international.download.nvidia.com/GFNLinux/flatpak/geforcenow.flatpakrepo";
      }
    ];
    packages = map (row: {
      appId = "${row.appId}/${row.arch}/${row.branch}";
      inherit (row) commit;
      origin = row.origin;
    }) inventory;
  };
}
