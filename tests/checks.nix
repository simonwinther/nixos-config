{
  pkgs,
  packages,
  self,
}:
{
  desktop-behavior =
    pkgs.runCommand "desktop-behavior"
      {
        nativeBuildInputs = [
          pkgs.python3
          pkgs.matugen
        ];
      }
      ''
        cp -r ${../.} source
        chmod -R u+w source
        cd source
        export HOME="$TMPDIR/home" PYTHONDONTWRITEBYTECODE=1
        mkdir -p "$HOME"
        python -m unittest discover -s tests -v
        touch "$out"
      '';
  neovim-startup =
    pkgs.runCommand "neovim-startup"
      {
        nativeBuildInputs = [
          pkgs.neovim
          pkgs.git
          pkgs.coreutils
          pkgs.bash
          pkgs.ripgrep
          pkgs.fd
        ];
      }
      ''
        export HOME="$TMPDIR/home" NVIM_NIX_PLUGIN_ROOT=${packages.neovim-plugins}
        export NVIM_MIGRATION_PARSER_MANIFEST=${../pkgs/neovim/parsers.json}
        export XDG_CACHE_HOME="$(mktemp -d /tmp/nvim-migration.XXXXXX)"
        trap 'rm -rf -- "$XDG_CACHE_HOME"' EXIT
        mkdir -p "$HOME/.config"
        ln -s ${../dotfiles/nvim/.config/nvim} "$HOME/.config/nvim"
        ulimit -c 0
        ulimit -v 3145728
        timeout --signal=TERM --kill-after=5s 40s nvim --headless -i NONE \
          --cmd "luafile ${./neovim-pre.lua}" \
          -c "luafile ${./neovim-startup.lua}"
        touch "$out"
      '';
  tmux-startup =
    pkgs.runCommand "tmux-startup"
      {
        nativeBuildInputs = with pkgs; [
          tmux
          bash
          coreutils
          gnugrep
          gnused
          gawk
          procps
          gnutar
          gzip
        ];
      }
      ''
        export HOME="$TMPDIR/home" SHELL=${pkgs.bash}/bin/bash
        export TMUX_NIX_PLUGIN_CONF=${packages.tmux-plugins}/init.conf
        export TMUX_MIGRATION_CONFIG=${../dotfiles/tmux/.tmux.conf}
        mkdir -p "$HOME"
        timeout --signal=TERM --kill-after=5s 40s bash ${./tmux-startup.sh}
        touch "$out"
      '';
  portable-syntax =
    pkgs.runCommand "portable-syntax"
      {
        nativeBuildInputs = [
          pkgs.python3
          pkgs.bash
          pkgs.zsh
          pkgs.lua
          pkgs.stow
        ];
      }
      ''
        python ${./validate.py} ${../.}
        mkdir -p "$TMPDIR/stow-home"
        bash ${../.}/scripts/stow-portable "$TMPDIR/stow-home" > "$TMPDIR/stow.log" 2>&1
        touch "$out"
      '';
}
