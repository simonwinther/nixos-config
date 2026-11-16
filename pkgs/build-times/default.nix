{ lib, rustPlatform }:
rustPlatform.buildRustPackage {
  pname = "build-times";
  version = "1.0.0";
  src = ./source;
  cargoLock.lockFile = ./source/Cargo.lock;
  cargoTestFlags = [ "--all-targets" ];
  meta = {
    description = "Chart NixOS build and activation durations in the terminal";
    mainProgram = "build-times";
    platforms = lib.platforms.linux;
  };
}
