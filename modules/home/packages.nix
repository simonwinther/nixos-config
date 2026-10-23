{
  config,
  lib,
  pkgs,
  unstable,
  packages,
  profile,
  ...
}:
let
  inventory = builtins.fromJSON (builtins.readFile ../../docs/inventory/package-map.json);
  select =
    row:
    if row.kind == "custom" then
      packages.${row.attribute}
    else
      lib.attrByPath (lib.splitString "." row.attribute)
        (throw "Unmapped application ${row.arch}: ${row.attribute}")
        (if row.source == "unstable" then unstable else pkgs);
  applications =
    map
      (
        row:
        # Compiler wrappers also provide cc/c++; retain GCC as the default.
        if row.arch == "gcc-fortran" then
          lib.setPrio 30 (select row)
        else if row.arch == "clang" then
          lib.setPrio 20 (select row)
        else
          select row
      )
      (
        builtins.filter (
          row:
          builtins.elem row.kind [
            "package"
            "custom"
          ]
        ) inventory
      );
  python = unstable.python3.withPackages (
    p: with p; [
      pygobject3
      pillow
      numpy
      matplotlib
      pip
      poetry-core
      terminaltexteffects
    ]
  );
in
{
  home.packages = lib.unique (
    (with pkgs; [
      ghostty
      starship
      neovim
      chromium
      nautilus
      nautilus-python
      hypridle
      hyprlock
      hyprsunset
      hyprpicker
      mako
      swayosd
      awww
      xdg-utils
      xdg-terminal-exec
      wl-clipboard
      brightnessctl
      grim
      slurp
      satty
      tesseract
      imagemagick
      ffmpeg
      gpu-screen-recorder
      playerctl
      wireplumber
      pulseaudio
      libnotify
      fzf
      atuin
      fd
      ripgrep
      jq
      eza
      zoxide
      oh-my-posh
      zsh-autosuggestions
      zsh-syntax-highlighting
      stow
      tmux
      impala
      bluetui
      wiremix
      btop
      fastfetch
      git
      delta
      lazygit
      yaru-theme
      gnome-themes-extra
      adwaita-icon-theme
      matugen
      wtype
      socat
      python
      zenity
      cmatrix
      glib
      dbus
    ])
    ++ [ unstable.hyprland-preview-share-picker ]
    ++ (with packages; [
      desktop-tools
      project-picker-tui
      background-grid
      hyprspace
      walker
      elephant
      waybar
      workspaces-slider
      dictate
      file-picker
      dictation-volume-duck
      text-picker
      formula-plot
      cluster-tools
      iphone-transfer
    ])
    ++ lib.optionals config.desktop.fullApplications applications
    ++ lib.optionals config.desktop.fullApplications [ packages.uipro ]
    ++ lib.optionals config.desktop.fullApplications (
      with pkgs;
      [
        alacritty
        kitty
        nodejs
        jdk
        maven
        ant
        gnumake
        gcc
        pkg-config
        unzip
        zip
        cargo-watch
        shellcheck
        stylua
        shfmt
        black
        isort
        basedpyright
        clang-tools
        lua-language-server
        typescript-language-server
        vscode-langservers-extracted
        nil
        nixfmt
        texlab
        haskell-language-server
        marksman
        yaml-language-server
        cmake-language-server
        bash-language-server
        ruff
        taplo
        tinymist
        sops
        age
        restic
        rclone
      ]
    )
    ++ lib.optionals config.desktop.fullApplications (
      with unstable;
      [
        codex
        antigravity-cli
        cargo
        rustfmt
        clippy
        rust-analyzer
        claude-code
        github-copilot-cli
        gemini-cli
        ghui
        pi-coding-agent
        kaggle
        dotenv-linter
        # Preserve Flutter's SDK-root documentation in the merged profile;
        # Playwright's executable uses its own immutable package contents.
        (lib.lowPrio playwright)
      ]
    )
    ++ lib.optionals (profile != "live" && profile != "recovery") (
      with packages;
      [
        breakd
        canvas-mcp
        hendrix-vpn
      ]
    )
  );
}
