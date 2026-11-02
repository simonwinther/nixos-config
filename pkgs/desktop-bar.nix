{
  lib,
  rustPlatform,
  makeWrapper,
  pkg-config,
  fontconfig,
  nerd-fonts,
  findutils,
  wayland,
  libpulseaudio,
  libxkbcommon,
  dbus,
}:
rustPlatform.buildRustPackage {
  pname = "desktop-bar";
  version = "0.1.0";
  src = lib.fileset.toSource {
    root = ../dotfiles;
    fileset = lib.fileset.unions [
      ../dotfiles/desktop-bar/.local/share/desktop-bar
      ../dotfiles/clipboard-picker/.local/share/clipboard-picker/core
      ../dotfiles/desktop-ring/.local/share/desktop-ring/vendor/libpulse-binding
    ];
  };
  sourceRoot = "source/desktop-bar/.local/share/desktop-bar";
  cargoLock.lockFile = ../dotfiles/desktop-bar/.local/share/desktop-bar/Cargo.lock;
  cargoTestFlags = [ "--workspace" ];
  nativeBuildInputs = [
    makeWrapper
    pkg-config
    findutils
  ];
  buildInputs = [
    libpulseaudio
    libxkbcommon
    wayland
  ];
  nativeCheckInputs = [ dbus ];
  preBuild = ''
    export DESKTOP_BAR_FONT="$(find ${nerd-fonts.jetbrains-mono}/share/fonts -name JetBrainsMonoNerdFont-SemiBold.ttf -print -quit)"
    export DESKTOP_BAR_ICON_FONT="$(find ${nerd-fonts.symbols-only}/share/fonts -name SymbolsNerdFontMono-Regular.ttf -print -quit)"
    test -r "$DESKTOP_BAR_FONT"
    test -r "$DESKTOP_BAR_ICON_FONT"
  '';
  postFixup = ''
    wrapProgram "$out/bin/desktop-bar" \
      --set-default DESKTOP_BAR_ICON_FONT "$DESKTOP_BAR_ICON_FONT" \
      --prefix PATH : ${lib.makeBinPath [ fontconfig ]} \
      --prefix LD_LIBRARY_PATH : ${
        lib.makeLibraryPath [
          wayland
          libpulseaudio
          libxkbcommon
        ]
      }
  '';
  meta = {
    description = "Morphing Notch Bar with native search and desktop controls";
    mainProgram = "desktop-bar";
    platforms = lib.platforms.linux;
  };
}
