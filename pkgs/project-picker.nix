{
  lib,
  rustPlatform,
}:
rustPlatform.buildRustPackage {
  pname = "project-picker-tui";
  version = "0.1.0";
  src = ../dotfiles/desktop-tools/.local/share/desktop-tools/project-picker-tui;
  cargoLock.lockFile = ../dotfiles/desktop-tools/.local/share/desktop-tools/project-picker-tui/Cargo.lock;
  meta = {
    description = "Compact project picker with live search and browser sync";
    mainProgram = "project-picker-tui";
    platforms = lib.platforms.linux;
  };
}
