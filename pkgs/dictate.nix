{
  lib,
  rustPlatform,
  pkg-config,
  wrapGAppsHook4,
  makeWrapper,
  symlinkJoin,
  gtk4,
  gtk4-layer-shell,
  pipewire,
  wireplumber,
  pulseaudio,
  wl-clipboard,
  ffmpeg,
  coreutils,
  procps,
  util-linux,
  bash,
  hyprland,
}:
let
  native = rustPlatform.buildRustPackage {
    pname = "dictate";
    version = "1.0.0";
    src = ../dotfiles/dictate/.local/share/dictate;
    cargoLock.lockFile = ../dotfiles/dictate/.local/share/dictate/Cargo.lock;
    nativeBuildInputs = [
      pkg-config
      wrapGAppsHook4
      makeWrapper
    ];
    buildInputs = [
      gtk4
      gtk4-layer-shell
    ];
    nativeCheckInputs = [
      bash
      coreutils
      procps
      util-linux
      ffmpeg
    ];
    buildFeatures = [ "overlay" ];
    cargoTestFlags = [ "--all-targets" ];
    meta = {
      description = "Streaming dictation with a native Wayland overlay";
      mainProgram = "dictate";
      platforms = lib.platforms.linux;
    };
  };
in
symlinkJoin {
  name = "dictate-1.0.0";
  paths = [ native ];
  nativeBuildInputs = [ makeWrapper ];
  inherit (native) meta;
  passthru.unwrapped = native;
  postBuild = ''
    rm "$out/bin/dictate"
    makeWrapper ${native}/bin/dictate "$out/bin/dictate" \
      --prefix PATH : ${
        lib.makeBinPath [
          pipewire
          wireplumber
          pulseaudio
          wl-clipboard
          ffmpeg
          coreutils
          procps
          util-linux
          bash
          hyprland
        ]
      }
  '';
}
