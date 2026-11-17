{
  lib,
  rustPlatform,
  pkg-config,
  wrapGAppsHook4,
  makeBinaryWrapper,
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
    preCheck = ''
      # Session fixtures otherwise exceed Linux's Unix-domain socket path limit.
      export TMPDIR=/tmp
    '';
    postPatch = ''
      substituteInPlace tests/sessions.rs \
        --replace-fail '/usr/bin:/bin' '${
          lib.makeBinPath [
            bash
            coreutils
            procps
            util-linux
            ffmpeg
          ]
        }'
    '';
    # Only the overlay loads GTK; the CLI and its recording worker run unwrapped.
    dontWrapGApps = true;
    postFixup = ''
      wrapGApp "$out/bin/dictate-overlay"
    '';
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
  nativeBuildInputs = [ makeBinaryWrapper ];
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
          hyprland
        ]
      }
    ln -s dictate "$out/bin/dictate-native"
  '';
}
