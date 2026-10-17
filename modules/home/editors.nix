{
  config,
  lib,
  pkgs,
  packages,
  ...
}:
{
  home.sessionVariables.TMUX_NIX_PLUGIN_CONF = "${packages.tmux-plugins}/init.conf";
  home.sessionVariables.NVIM_NIX_PLUGIN_ROOT = "${packages.neovim-plugins}";
  home.sessionVariables.ZSH_AUTOSUGGESTIONS_FILE = "${pkgs.zsh-autosuggestions}/share/zsh-autosuggestions/zsh-autosuggestions.zsh";
  home.sessionVariables.ZSH_SYNTAX_HIGHLIGHTING_FILE = "${pkgs.zsh-syntax-highlighting}/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh";
  home.sessionVariables.ANT_ARGS = lib.mkIf config.desktop.fullApplications "-lib ${packages.ant-contrib}/share/java/ant-contrib.jar";
}
