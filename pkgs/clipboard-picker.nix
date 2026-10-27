{
  lib,
  rustPlatform,
  pkg-config,
  wrapGAppsHook4,
  gtk4,
  gtk4-layer-shell,
  makeWrapper,
  wl-clipboard,
  hyprland,
}:
rustPlatform.buildRustPackage {
  pname = "clipboard-picker";
  version = "1.0.0";
  src = ../dotfiles/clipboard-picker/.local/share/clipboard-picker;
  cargoLock.lockFile = ../dotfiles/clipboard-picker/.local/share/clipboard-picker/Cargo.lock;
  nativeBuildInputs = [
    pkg-config
    wrapGAppsHook4
    makeWrapper
  ];
  buildInputs = [
    gtk4
    gtk4-layer-shell
  ];
  cargoTestFlags = [ "--all-targets" ];
  postFixup = ''
    wrapProgram "$out/bin/clipboard-picker-native" \
      --prefix PATH : ${
        lib.makeBinPath [
          wl-clipboard
          hyprland
        ]
      }
  '';
  meta = {
    description = "Native clipboard history with ordered image selection and batch paste";
    mainProgram = "clipboard-picker-native";
    platforms = lib.platforms.linux;
  };
}
