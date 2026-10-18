{
  pkgs,
  packages,
  self,
}:
{
  hyprland-config =
    pkgs.runCommand "hyprland-config"
      {
        nativeBuildInputs = [
          pkgs.bash
          pkgs.stow
          pkgs.gnugrep
          packages.desktop-tools
          packages.hyprspace.compositor
        ];
      }
      ''
        mkdir -p "$TMPDIR/home"
        bash ${../.}/scripts/stow-portable "$TMPDIR/home" --apply > "$TMPDIR/stow.log" 2>&1
        export HOME="$TMPDIR/home"
        export XDG_CONFIG_HOME="$HOME/.config" XDG_STATE_HOME="$HOME/.local/state"
        export XDG_DATA_HOME="$HOME/.local/share" XDG_RUNTIME_DIR="$TMPDIR/runtime"
        export HYPRSPACE_PLUGIN=${packages.hyprspace}/lib/libhyprspace.so
        unset HYPRLAND_INSTANCE_SIGNATURE WAYLAND_DISPLAY DISPLAY
        mkdir -p "$XDG_RUNTIME_DIR"
        desktopctl theme init
        if ! Hyprland --verify-config --config "$HOME/.config/hypr/hyprland.lua" > "$TMPDIR/hyprland.log" 2>&1; then
          cat "$TMPDIR/hyprland.log"
          exit 1
        fi
        cat "$TMPDIR/hyprland.log"
        grep -F 'config ok' "$TMPDIR/hyprland.log"
        touch "$out"
      '';
  desktop-behavior =
    pkgs.runCommand "desktop-behavior"
      {
        nativeBuildInputs = [
          pkgs.python3
          pkgs.matugen
          pkgs.bash
          pkgs.imagemagick
          pkgs.file
        ];
      }
      ''
        cp -r ${../.} source
        chmod -R u+w source
        cd source
        export HOME="$TMPDIR/home" PYTHONDONTWRITEBYTECODE=1
        mkdir -p "$HOME"
        python -m unittest discover -s tests -v
        mkdir -p "$TMPDIR/tools" "$TMPDIR/media"
        export TRANSCODE_TEST_CLIPBOARD="$TMPDIR/clipboard"
        cat > "$TMPDIR/tools/wl-copy" <<'SH'
        #!/usr/bin/env bash
        cat > "$TRANSCODE_TEST_CLIPBOARD"
        SH
        cat > "$TMPDIR/tools/notify-send" <<'SH'
        #!/usr/bin/env bash
        exit 0
        SH
        chmod +x "$TMPDIR/tools/"*
        export PATH="$TMPDIR/tools:$PATH"
        magick -size 12x12 xc:blue "$TMPDIR/media/input file.png"
        before=$(sha256sum "$TMPDIR/media/input file.png")
        bash dotfiles/desktop-tools/.local/share/desktop-tools/transcode.sh "$TMPDIR/media/input file.png" jpg low
        test -s "$TMPDIR/media/input file-low.jpg"
        test "$before" = "$(sha256sum "$TMPDIR/media/input file.png")"
        test "$(cat "$TRANSCODE_TEST_CLIPBOARD")" = "file://$TMPDIR/media/input file-low.jpg"
        if bash dotfiles/desktop-tools/.local/share/desktop-tools/transcode.sh "$TMPDIR/media/input file.png" jpg low; then
          echo 'Transcode must not replace an existing output' >&2
          exit 1
        fi
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
