{
  config,
  lib,
  pkgs,
  packages,
  host,
  ...
}:
let
  defaults = ../../dotfiles/obs/.local/share/obs-defaults;
  sync = ../../dotfiles/obs/.local/share/obs-sync/sync.py;
in
{
  # OBS writes its scene collections and profiles itself. Only the reviewed
  # defaults are Home Manager links; the live configuration stays writable.
  config = lib.mkIf (host == "desktop" && config.desktop.fullApplications) {
    xdg.configFile."desktop/obs-bin".text = "${packages.obs-studio}/bin/obs\n";
    home.activation.obsDefaults = lib.hm.dag.entryAfter [ "linkGeneration" ] ''
      run ${pkgs.python3}/bin/python3 ${sync} --defaults ${defaults} --defer-if-running
    '';
    home.file.".local/share/fonts/obs".source = "${packages.obs-font}/share/fonts";
  };
}
