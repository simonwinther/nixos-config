{
  lib,
  rustPlatform,
  pkg-config,
  wrapGAppsHook4,
  makeWrapper,
  symlinkJoin,
  gtk4,
  fd,
  fzf,
  zathura,
  ghostty,
  wl-clipboard,
  libnotify,
  coreutils,
  bash,
  hyprland,
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
    buildInputs = [ gtk4 ];
    nativeCheckInputs = [ fd ];
    buildFeatures = [ "drag" ];
    meta = {
      description = "Prepared file and PDF search with clipboard and drag support";
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
          fzf
          zathura
          ghostty
          wl-clipboard
          libnotify
          coreutils
          bash
          hyprland
        ]
      }
    makeWrapper "$out/bin/file-picker-native" "$out/bin/file-picker"
  '';
}
