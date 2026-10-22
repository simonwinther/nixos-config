{
  modulesPath,
  lib,
  pkgs,
  inputs,
  packages,
  ...
}:
let
  editorSources = builtins.fromJSON (builtins.readFile ../pkgs/editor-extensions/sources.json);
  retainedEditors = builtins.filter (source: source.retainedArchive or false) (
    builtins.attrValues editorSources
  );
  installerSources = pkgs.linkFarm "nixos-installer-sources" (
    [
      {
        name = "nordvpn-tui_0.1.0_linux_amd64.tar.gz";
        path = packages.nordvpn-tui.src;
      }
    ]
    ++ map (source: {
      name = source.archiveName;
      path = pkgs.fetchurl {
        name = source.archiveName;
        inherit (source) url hash;
      };
    }) retainedEditors
  );
in
{
  imports = [ (modulesPath + "/installer/cd-dvd/installation-cd-minimal.nix") ];
  # The minimal installer disables Fontconfig; the graphical live session needs it.
  fonts.fontconfig.enable = true;
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

  # Carry the reviewed source and otherwise unavailable build inputs with the USB.
  # The flake source excludes .git, ignored private material and build artifacts.
  environment.etc."nixos-config".source = inputs.self.outPath;
  environment.etc."nixos-installer-sources".source = installerSources;
  home-manager.users.simon = { lib, ... }: {
    home.activation.desktopLiveCheckout = lib.hm.dag.entryAfter [ "writeBoundary" ] ''
      if [ ! -e "$HOME/nixos-config" ]; then
        run ${pkgs.coreutils}/bin/cp -r ${inputs.self.outPath} "$HOME/nixos-config"
        run ${pkgs.coreutils}/bin/chmod -R u+w "$HOME/nixos-config"
        run ${pkgs.git}/bin/git -C "$HOME/nixos-config" init -q
        run ${pkgs.git}/bin/git -C "$HOME/nixos-config" add .
      fi
    '';
  };
}
