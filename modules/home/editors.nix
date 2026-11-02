{
  config,
  lib,
  pkgs,
  packages,
  ...
}:
let
  neovimEnvironment = {
    NVIM_NIX_PLUGIN_ROOT = "${packages.neovim-plugins}";
    NVIM_SQLITE_LIBRARY = "${pkgs.sqlite.out}/lib/libsqlite3.so";
    NVIM_COPILOT_SERVER = lib.getExe pkgs.copilot-language-server;
    NVIM_CPPMAN_INDEX = "${pkgs.cppman}/${pkgs.python3.sitePackages}/cppman/lib/index.db";
  };
  editorTools = lib.optionals config.desktop.fullApplications (
    with pkgs;
    [
      ghostscript
      mermaid-cli
      chafa
      viu
      prettier
      jdt-language-server
      fish
      haskellPackages.cabal-fmt
      haskellPackages.fourmolu
      typstyle
      xdotool
      psmisc
      sqlite
      copilot-language-server
    ]
  );
in
{
  home.sessionVariables.TMUX_NIX_PLUGIN_CONF = "${packages.tmux-plugins}/init.conf";
  home.sessionVariables.BASH_COMPLETION_FILE = "${pkgs.bash-completion}/share/bash-completion/bash_completion";
  home.sessionVariables.FZF_SHELL_DIR = "${pkgs.fzf}/share/fzf";
  home.sessionVariables.NVIM_NIX_PLUGIN_ROOT = neovimEnvironment.NVIM_NIX_PLUGIN_ROOT;
  home.sessionVariables.NVIM_SQLITE_LIBRARY = neovimEnvironment.NVIM_SQLITE_LIBRARY;
  home.sessionVariables.NVIM_COPILOT_SERVER = neovimEnvironment.NVIM_COPILOT_SERVER;
  home.sessionVariables.NVIM_CPPMAN_INDEX = neovimEnvironment.NVIM_CPPMAN_INDEX;
  home.sessionVariables.ZSH_AUTOSUGGESTIONS_FILE = "${pkgs.zsh-autosuggestions}/share/zsh-autosuggestions/zsh-autosuggestions.zsh";
  home.sessionVariables.ZSH_SYNTAX_HIGHLIGHTING_FILE = "${pkgs.zsh-syntax-highlighting}/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh";
  home.sessionVariables.ANT_ARGS = lib.mkIf config.desktop.fullApplications "-lib ${packages.ant-contrib}/share/java/ant-contrib.jar";
  home.packages = editorTools;
  home.file = {
    ".config/nvim/nix-env.lua".text =
      lib.concatStringsSep "\n" (
        lib.mapAttrsToList (name: value: "vim.env.${name} = ${builtins.toJSON value}") neovimEnvironment
      )
      + lib.optionalString (editorTools != [ ]) ''

        vim.env.PATH = ${builtins.toJSON (lib.makeBinPath editorTools)} .. ":" .. (vim.env.PATH or "")
      '';
    ".local/share/nvim/site/parser".source = "${packages.neovim-plugins}/runtime/parser";
    ".local/share/nvim/site/queries".source = "${packages.neovim-plugins}/runtime/queries";
  }
  // lib.optionalAttrs config.desktop.fullApplications (
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
        ]
    )
  );
}
