{
  config,
  lib,
  pkgs,
  packages,
  ...
}:
{
  home.sessionVariables.TMUX_NIX_PLUGIN_CONF = "${packages.tmux-plugins}/init.conf";
  home.sessionVariables.BASH_COMPLETION_FILE = "${pkgs.bash-completion}/share/bash-completion/bash_completion";
  home.sessionVariables.FZF_SHELL_DIR = "${pkgs.fzf}/share/fzf";
  home.sessionVariables.NVIM_NIX_PLUGIN_ROOT = "${packages.neovim-plugins}";
  home.sessionVariables.ZSH_AUTOSUGGESTIONS_FILE = "${pkgs.zsh-autosuggestions}/share/zsh-autosuggestions/zsh-autosuggestions.zsh";
  home.sessionVariables.ZSH_SYNTAX_HIGHLIGHTING_FILE = "${pkgs.zsh-syntax-highlighting}/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh";
  home.sessionVariables.ANT_ARGS = lib.mkIf config.desktop.fullApplications "-lib ${packages.ant-contrib}/share/java/ant-contrib.jar";
  home.file = lib.mkIf config.desktop.fullApplications (
    builtins.listToAttrs (
      lib.concatMap
        (
          editor:
          map (
            extension:
            let
              spec = extension.migration;
              suffix =
                if
                  builtins.elem spec.platform [
                    "universal"
                    "undefined"
                  ]
                then
                  ""
                else
                  "-${spec.platform}";
              prefix = if editor == "vscode" then ".vscode" else ".cursor";
            in
            {
              name = "${prefix}/extensions/${lib.toLower spec.id}-${spec.version}${suffix}";
              value.source = "${extension}/share/vscode/extensions/${extension.vscodeExtUniqueId}";
            }
          ) packages.editor-extensions.${editor}
        )
        [
          "vscode"
          "cursor"
        ]
    )
  );
}
