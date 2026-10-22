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
  # Adwaita is also the reference laptop's default XCursor theme.
  home.pointerCursor = {
    enable = true;
    package = pkgs.adwaita-icon-theme;
    name = interface.cursor-theme;
    size = interface.cursor-size;
    gtk.enable = true;
    x11.enable = true;
  };
  gtk.enable = true;
  xdg.configFile."desktop/cursor.lua".text = ''
    hl.env("XCURSOR_THEME", ${builtins.toJSON interface.cursor-theme})
    hl.env("XCURSOR_SIZE", ${builtins.toJSON (toString interface.cursor-size)})
    hl.env("XCURSOR_PATH", ${builtins.toJSON "${config.home.profileDirectory}/share/icons:${config.xdg.dataHome}/icons"})
    -- Adwaita provides XCursor assets; use them instead of Hyprland's fallback.
    hl.config({ cursor = { enable_hyprcursor = false } })
  '';
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
