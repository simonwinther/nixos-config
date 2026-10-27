{
  lib,
  rustPlatform,
  pkg-config,
  wrapGAppsHook4,
  makeWrapper,
  symlinkJoin,
  gtk4,
  sqlite,
  glib,
  fd,
  zathura,
  ghostty,
  wl-clipboard,
  libnotify,
  coreutils,
  bash,
  hyprland,
  xdg-utils,
  xdg-user-dirs,
}:
let
  native = rustPlatform.buildRustPackage {
    pname = "file-picker";
    version = "1.0.0";
    src = ../dotfiles/file-picker/.local/share/file-picker;
    cargoLock.lockFile = ../dotfiles/file-picker/.local/share/file-picker/Cargo.lock;
    nativeBuildInputs = [
      pkg-config
      wrapGAppsHook4
      makeWrapper
    ];
    buildInputs = [
      gtk4
      sqlite
    ];
    nativeCheckInputs = [
      fd
      bash
      coreutils
    ];
    buildFeatures = [ "drag" ];
    meta = {
      description = "SQLite-cached Ratatui file and PDF search with clipboard and drag support";
      mainProgram = "file-picker";
      platforms = lib.platforms.linux;
    };
  };
in
symlinkJoin {
  name = "file-picker-1.0.0";
  paths = [ native ];
  nativeBuildInputs = [ makeWrapper ];
  inherit (native) meta;
  passthru.unwrapped = native;
  postBuild = ''
    rm "$out/bin/file-picker-native"
    makeWrapper ${native}/bin/file-picker-native "$out/bin/file-picker-native" \
      --set FILE_PICKER_EXECUTABLE "$out/bin/file-picker-native" \
      --prefix PATH : ${
        lib.makeBinPath [
          fd
          (lib.getBin glib)
          zathura
          ghostty
          wl-clipboard
          libnotify
          coreutils
          bash
          hyprland
          xdg-utils
          xdg-user-dirs
        ]
      }
    makeWrapper "$out/bin/file-picker-native" "$out/bin/file-picker"
  '';
}
