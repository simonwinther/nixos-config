{
  config,
  lib,
  pkgs,
  packages,
  ...
}:
let
  data = "${config.xdg.dataHome}/roblox-dev";
  vinegar = "${config.home.homeDirectory}/.var/app/org.vinegarhq.Vinegar";
  pluginDir = "${vinegar}/data/vinegar/prefixes/studio/drive_c/users/${config.home.username}/AppData/Local/Roblox/Plugins";
in
{
  config = lib.mkIf config.desktop.fullApplications {
    home.packages = [
      packages.rokit
      pkgs.vulkan-tools
    ];
    home.file = {
      ".local/share/roblox-dev/globalTypes.d.luau".source =
        "${packages.roblox-editor-resources}/globalTypes.d.luau";
      ".local/share/roblox-dev/api-docs.json".source =
        "${packages.roblox-editor-resources}/api-docs.json";
      ".local/share/roblox-dev/nvim/parser/luau.so".source =
        "${packages.roblox-editor-resources}/parser/luau.so";
    };
    services.flatpak.overrides.settings = {
      "org.vinegarhq.Vinegar".Context.filesystems = [
        "!xdg-documents"
        "!xdg-pictures"
        "${config.home.homeDirectory}/dev/roblox"
        "${config.home.homeDirectory}/roblox-builds"
      ];
      "org.blender.Blender".Context.filesystems = [
        "!host"
        "${config.home.homeDirectory}/dev/roblox"
        "${config.home.homeDirectory}/roblox-builds"
      ];
    };
    home.activation.robloxDevelopment = lib.hm.dag.entryAfter [ "linkGeneration" ] ''
      run mkdir -p "$HOME/.rokit" "$HOME/roblox-builds" "${vinegar}/config/vinegar" "${pluginDir}"
      if [[ ! -e "$HOME/.rokit/rokit.toml" ]]; then
        run cp "${data}/rokit-tools.toml" "$HOME/.rokit/rokit.toml"
        run chmod u+w "$HOME/.rokit/rokit.toml"
      fi
      (
        cd "$HOME/.rokit"
        run ${packages.rokit}/bin/rokit trust rojo-rbx/rojo Kampfkarren/selene UpliftGames/wally lune-org/lune JohnnyMorganz/luau-lsp JohnnyMorganz/StyLua
        run ${packages.rokit}/bin/rokit install
      )
      if [[ ! -e "${vinegar}/config/vinegar/config.toml" ]]; then
        run install -m600 "$HOME/.config/roblox-dev/vinegar.toml" "${vinegar}/config/vinegar/config.toml"
      fi
      if [[ ! -e "${pluginDir}/Rojo.rbxm" ]]; then
        run install -m644 ${packages.rojo-studio-plugin} "${pluginDir}/Rojo.rbxm"
      fi
    '';
  };
}
