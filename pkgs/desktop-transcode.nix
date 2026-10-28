{
  lib,
  rustPlatform,
  bash,
  coreutils,
}:
rustPlatform.buildRustPackage {
  pname = "desktop-transcode";
  version = "1.0.0";
  src = ../dotfiles/desktop-tools/.local/share/desktop-transcode;
  cargoLock.lockFile = ../dotfiles/desktop-tools/.local/share/desktop-transcode/Cargo.lock;
  cargoTestFlags = [ "--all-targets" ];
  nativeCheckInputs = [
    bash
    coreutils
  ];
  preCheck = ''
    export TMPDIR=/tmp
    substituteInPlace tests/jobs.rs \
      --replace-fail '/usr/bin:/bin' '${
        lib.makeBinPath [
          bash
          coreutils
        ]
      }'
  '';
  meta = {
    description = "Cancellable FFmpeg and ImageMagick supervisor with atomic output publication";
    mainProgram = "desktop-transcode-native";
    platforms = lib.platforms.linux;
  };
}
