{
  config,
  lib,
  pkgs,
  packages,
  ...
}:
let
  vinegar = "${config.home.homeDirectory}/.var/app/org.vinegarhq.Vinegar";
  pluginDir = "${vinegar}/data/vinegar/prefixes/studio/drive_c/users/${config.home.username}/AppData/Local/Roblox/Plugins";
in
{
  config = lib.mkIf config.desktop.fullApplications {
    home = {
      packages = [
        packages.roblox-toolchain
        pkgs.vulkan-tools
      ];
      file = {
        ".config/hypr/windows.lua".source = lib.mkForce (
          pkgs.writeText "hypr-studio-windows.lua" ''
            -- Wine dialogs may repeatedly request activation after the pointer leaves.
            -- Keep normal initial/click focus without letting Studio pull it back.
            hl.window_rule({
                match = { class = "(?i)^robloxstudiobeta\\.exe$" },
                name = "studio-no-focus-stealing",
                focus_on_activate = false,
            })
            ${builtins.readFile ../../dotfiles/hypr/.config/hypr/windows.lua}
          ''
        );
        ".local/share/roblox-dev/globalTypes.d.luau".source =
          "${packages.roblox-editor-resources}/globalTypes.d.luau";
        ".local/share/roblox-dev/api-docs.json".source =
          "${packages.roblox-editor-resources}/api-docs.json";
        ".local/share/roblox-dev/nvim/parser/luau.so".source =
          "${packages.roblox-editor-resources}/parser/luau.so";
      };
      activation.robloxDevelopment = lib.hm.dag.entryAfter [ "linkGeneration" ] ''
        run mkdir -p "$HOME/roblox-builds" "${vinegar}/config/vinegar" "${pluginDir}"
        if [[ ! -e "${vinegar}/config/vinegar/config.toml" ]]; then
          run install -m600 "$HOME/.config/roblox-dev/vinegar.toml" "${vinegar}/config/vinegar/config.toml"
        fi
        if [[ ! -e "${pluginDir}/Rojo.rbxm" ]]; then
          run install -m644 ${packages.rojo-studio-plugin} "${pluginDir}/Rojo.rbxm"
        fi
      '';
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
  };
}
