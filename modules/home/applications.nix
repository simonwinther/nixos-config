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
  interface = builtins.fromJSON (
    builtins.readFile ../../dotfiles/desktop-settings/.config/desktop/interface.json
  );
  applications = builtins.fromJSON (
    builtins.readFile ../../dotfiles/desktop-settings/.config/desktop/applications.json
  );
in
{
  imports = [ inputs.nix-flatpak.homeManagerModules.nix-flatpak ];
  dconf.settings =
    lib.mapAttrs' (schema: values: {
      name = lib.replaceStrings [ "." ] [ "/" ] schema;
      value = values;
    }) applications
    // {
      "org/gnome/desktop/interface" = interface;
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
