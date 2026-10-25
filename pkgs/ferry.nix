{ lib, rustPlatform, source, copyDesktopItems, makeDesktopItem }:
rustPlatform.buildRustPackage {
  pname = "ferry";
  version = "0.1.0";
  src = source;
  cargoLock.lockFile = "${source}/Cargo.lock";
  nativeBuildInputs = [ copyDesktopItems ];
  desktopItems = [ (makeDesktopItem {
    name = "ferry";
    desktopName = "Ferry";
    comment = "Move recent downloads with fuzzy folder search";
    exec = "ferry %F";
    icon = "folder-download";
    terminal = true;
    categories = [ "Utility" "FileTools" ];
  }) ];
  cargoTestFlags = [ "--all-targets" ];
  meta = {
    description = "Safe download sorting with fuzzy destinations";
    mainProgram = "ferry";
    platforms = lib.platforms.linux;
  };
}
