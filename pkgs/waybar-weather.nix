{ lib, rustPlatform }:
rustPlatform.buildRustPackage {
  pname = "waybar-weather";
  version = "1.0.0";
  src = ../dotfiles/waybar/.local/share/waybar-weather;
  cargoLock.lockFile = ../dotfiles/waybar/.local/share/waybar-weather/Cargo.lock;
  cargoTestFlags = [ "--all-targets" ];
  meta = {
    description = "Cached Copenhagen weather for Waybar";
    mainProgram = "waybar-weather-native";
    platforms = lib.platforms.linux;
  };
}
