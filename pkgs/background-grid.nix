{
  lib,
  rustPlatform,
  pkg-config,
  wrapGAppsHook4,
  makeWrapper,
  gtk4,
  awww,
  uwsm,
  procps,
  coreutils,
  bash,
  hyprland,
}:
rustPlatform.buildRustPackage {
  pname = "background-grid";
  version = "1.0.0";
  src = ../dotfiles/background-grid/.local/share/background-grid;
  cargoLock.lockFile = ../dotfiles/background-grid/.local/share/background-grid/Cargo.lock;
  nativeBuildInputs = [
    pkg-config
    wrapGAppsHook4
    makeWrapper
  ];
  buildInputs = [ gtk4 ];
  nativeCheckInputs = [
    bash
    coreutils
  ];
  cargoTestFlags = [ "--all-targets" ];
  preCheck = ''
    export TMPDIR=/tmp
    substituteInPlace tests/commands.rs \
      --replace-fail '/usr/bin:/bin' '${
        lib.makeBinPath [
          bash
          coreutils
        ]
      }'
  '';
  postFixup = ''
    wrapProgram "$out/bin/background-grid-native" \
      --prefix PATH : ${
        lib.makeBinPath [
          awww
          uwsm
          procps
          coreutils
          bash
          hyprland
        ]
      }
  '';
  meta = {
    description = "Native Rust wallpaper grid and wallpaper controller";
    platforms = lib.platforms.linux;
    mainProgram = "background-grid-native";
  };
}
