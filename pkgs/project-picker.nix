{
  lib,
  rustPlatform,
}:
rustPlatform.buildRustPackage {
  pname = "project-picker-tui";
  version = "0.1.0";
  src = ../dotfiles/desktop-tools/.local/share/desktop-tools/project-picker-tui;
  cargoLock.lockFile = ../dotfiles/desktop-tools/.local/share/desktop-tools/project-picker-tui/Cargo.lock;
  cargoTestFlags = [ "--all-targets" ];
  meta = {
    description = "Project picker, browser native host and shared cache protocol";
    mainProgram = "project-picker-tui";
    platforms = lib.platforms.linux;
  };
}
