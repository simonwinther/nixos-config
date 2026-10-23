{
  pkgs,
  packages,
  self,
}:
{
  storage-integration =
    let
      desktop = self.nixosConfigurations.desktop.config;
      live = self.nixosConfigurations.desktop-live.config;
      existing = desktop.workstation.storage.existingBtrfs;
      # Evaluation-only fixtures: these never run Disko or activate a system.
      fresh =
        (self.nixosConfigurations.desktop.extendModules {
          modules = [
            {
              workstation.storage.existingBtrfs = pkgs.lib.mkForce null;
              workstation.backupsVerified = pkgs.lib.mkForce true;
            }
          ];
        }).config;
      unreviewed =
        (self.nixosConfigurations.desktop.extendModules {
          modules = [
            {
              workstation.storage.existingBtrfs = pkgs.lib.mkForce null;
              workstation.backupsVerified = pkgs.lib.mkForce false;
            }
          ];
        }).config;
    in
    assert live.disko.devices.disk == { };
    assert unreviewed.disko.devices.disk == { };
    assert fresh.disko.devices.disk.system.device == desktop.workstation.targetDisk;
    assert existing == null || desktop.disko.devices.disk == { };
    assert
      existing == null
      || desktop.fileSystems."/".device == "/dev/disk/by-uuid/${existing.filesystemUuid}";
    assert
      existing == null
      || builtins.elem "subvol=${existing.subvolumePrefix}-root" desktop.fileSystems."/".options;
    assert
      existing == null
      || builtins.elem "subvol=${existing.subvolumePrefix}-home" desktop.fileSystems."/home".options;
    assert
      existing == null
      || desktop.boot.initrd.luks.devices.cryptroot.device == "/dev/disk/by-uuid/${existing.luksUuid}";
    pkgs.runCommand "storage-integration" { } ''
      touch "$out"
    '';
  walker-layout =
    pkgs.runCommand "walker-layout"
      {
        nativeBuildInputs = [
          (pkgs.python3.withPackages (p: [ p.pygobject3 ]))
          pkgs.xvfb-run
          pkgs.dbus
        ];
        GI_TYPELIB_PATH = pkgs.lib.makeSearchPath "lib/girepository-1.0" (
          map pkgs.lib.getLib (
            with pkgs;
            [
              gtk4
              pango
              harfbuzz
              gdk-pixbuf
              graphene
              glib
              gobject-introspection
            ]
          )
        );
        LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath (
          with pkgs;
          [
            gtk4
            pango
            harfbuzz
            gdk-pixbuf
            graphene
          ]
        );
        FONTCONFIG_FILE = pkgs.makeFontsConf { fontDirectories = [ pkgs.nerd-fonts.jetbrains-mono ]; };
      }
      ''
        export HOME="$TMPDIR/home" XDG_RUNTIME_DIR="$TMPDIR/runtime" GSK_RENDERER=cairo GDK_BACKEND=x11
        unset WAYLAND_DISPLAY HYPRLAND_INSTANCE_SIGNATURE
        mkdir -p "$HOME" "$XDG_RUNTIME_DIR"
        xvfb-run -a dbus-run-session --config-file=${pkgs.dbus}/share/dbus-1/session.conf -- python ${./walker-layout.py} ${../.} "$out"
      '';
  desktop-ring = packages.desktop-ring;
  ring-integration =
    let
      live = self.nixosConfigurations.desktop-live.config.home-manager.users.simon;
      laptop = self.nixosConfigurations.lambda.config.home-manager.users.simon;
    in
    assert live.desktop.ring.enable;
    assert !live.desktop.ring.settings.laptop;
    assert laptop.desktop.ring.settings.laptop;
    assert live.desktop.ring.settings.power;
    assert builtins.elem "desktop-session.target"
      live.systemd.user.services.desktop-hypridle.Install.WantedBy;
    assert live.home.pointerCursor.enable;
    assert live.home.pointerCursor.name == "Adwaita";
    assert live.home.pointerCursor.size == 24;
    assert !(builtins.hasAttr "desktop-monitor-watch" live.systemd.user.services);
    pkgs.runCommand "ring-integration" { nativeBuildInputs = [ pkgs.python3 ]; } ''
      python - <<'PYTEST'
      import json
      config = json.load(open("${live.xdg.configFile."desktop/ring.json".source}"))
      assert config["monitors"] and config["audio"] and config["bluetooth"] and config["power"]
      assert config["laptop"] is False
      assert "${live.desktop.ring.menuKey}" == "SUPER + R"
      PYTEST
      touch "$out"
    '';
  private-runtime-integration =
    let
      live = self.nixosConfigurations.desktop-live.config;
      home = live.home-manager.users.simon;
    in
    assert builtins.hasAttr "ku-vpn" live.systemd.services;
    assert (live.systemd.services.ku-vpn.wantedBy or [ ]) == [ ];
    assert !(builtins.hasAttr ".config/dictate/secrets.env" home.home.file);
    assert !(builtins.hasAttr ".config/hendrix/totp.json" home.home.file);
    assert home.programs.gh.enable;
    assert home.desktop.rebuild.action == "test";
    assert home.desktop.rebuild.target == "desktop-live";
    assert
      self.nixosConfigurations.lambda.config.home-manager.users.simon.desktop.rebuild.action == "switch";
    assert
      self.nixosConfigurations.lambda.config.home-manager.users.simon.desktop.rebuild.target == "lambda";
    assert !(builtins.hasAttr ".config/gh/hosts.yml" home.home.file);
    assert !(builtins.hasAttr ".netrc" home.home.file);
    pkgs.runCommand "private-runtime-integration" { nativeBuildInputs = [ pkgs.openssh ]; } ''
      grep -q HENDRIX_SPLIT_TUNNEL_V1 ${packages.hendrix-vpn}/bin/ku-vpn
      ssh -G -F ${home.home.file.".ssh/config".source} hendrix > config
      grep -qx 'hostname hendrixgate.unicph.domain' config
      grep -qx 'user zlp616' config
      grep -qx 'stricthostkeychecking true' config
      touch "$out"
    '';
  live-session-launcher =
    let
      launcher =
        self.nixosConfigurations.desktop-live.config.programs.uwsm.waylandCompositors.desktop.binPath;
    in
    pkgs.runCommand "live-session-launcher" { } ''
      # UWSM must be able to read its launcher as an unprivileged user.
      test -r ${launcher}
      test -x ${launcher}
      touch "$out"
    '';
  live-fonts =
    let
      live = self.nixosConfigurations.desktop-live.config;
    in
    assert live.fonts.fontconfig.enable;
    pkgs.runCommand "live-fonts"
      {
        nativeBuildInputs = [ pkgs.fontconfig ];
      }
      ''
        # Exercise the actual live system configuration without activating it.
        root="$TMPDIR/font-root"
        mkdir -p "$root/etc" "$root/nix" "$TMPDIR/config" "$TMPDIR/cache"
        ln -s /nix/store "$root/nix/store"
        ln -s ${live.environment.etc.fonts.source} "$root/etc/fonts"
        export FONTCONFIG_SYSROOT="$root"
        export FONTCONFIG_FILE=/etc/fonts/fonts.conf FONTCONFIG_PATH=/etc/fonts
        export XDG_CONFIG_HOME="$TMPDIR/config" XDG_CACHE_HOME="$TMPDIR/cache"
        for family in 'JetBrainsMono Nerd Font' 'Symbols Nerd Font'; do
          actual=$(fc-match --format '%{family[0]}' "$family")
          test "$actual" = "$family" || {
            echo "Expected $family, matched $actual" >&2
            exit 1
          }
        done
        test "$(fc-match --format '%{style[0]}' 'JetBrainsMono Nerd Font:weight=demibold')" = SemiBold
        touch "$out"
      '';
  hyprland-config =
    pkgs.runCommand "hyprland-config"
      {
        nativeBuildInputs = [
          pkgs.bash
          pkgs.stow
          pkgs.gnugrep
          packages.desktop-tools
          (pkgs.lib.getBin packages.hyprspace.compositor)
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
        mkdir -p "$HOME/.config/desktop"
        cp ${
          self.nixosConfigurations.desktop-live.config.home-manager.users.simon.xdg.configFile."desktop/ring-bindings.lua".source
        } "$HOME/.config/desktop/ring-bindings.lua"
        cp ${
          self.nixosConfigurations.desktop-live.config.home-manager.users.simon.xdg.configFile."desktop/cursor.lua".source
        } "$HOME/.config/desktop/cursor.lua"
        cp ${
          self.nixosConfigurations.desktop-live.config.home-manager.users.simon.xdg.configFile."desktop/rebuild-bindings.lua".source
        } "$HOME/.config/desktop/rebuild-bindings.lua"
        cp ${../hosts/desktop/monitors.lua} "$HOME/.config/desktop/monitors.lua"
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
          pkgs.fzf
          pkgs.nodejs
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
        node --test tests/project-picker.test.mjs
        mkdir -p "$TMPDIR/tools" "$TMPDIR/media"
        export TRANSCODE_TEST_CLIPBOARD="$TMPDIR/clipboard"
        cat > "$TMPDIR/tools/wl-copy" <<'SH'
        #!${pkgs.bash}/bin/bash
        cat > "$TRANSCODE_TEST_CLIPBOARD"
        SH
        cat > "$TMPDIR/tools/notify-send" <<'SH'
        #!${pkgs.bash}/bin/bash
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
