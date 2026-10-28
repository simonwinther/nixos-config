{
  lib,
  rustPlatform,
  pkg-config,
  wrapGAppsHook4,
  makeWrapper,
  gtk4,
  gtk4-layer-shell,
  pulseaudio,
  libpulseaudio,
  dbus,
  systemd,
  libnotify,
}:
rustPlatform.buildRustPackage {
  pname = "desktop-ring";
  version = "0.1.0";
  src = ../dotfiles/desktop-ring/.local/share/desktop-ring;
  cargoLock.lockFile = ../dotfiles/desktop-ring/.local/share/desktop-ring/Cargo.lock;
  nativeBuildInputs = [
    pkg-config
    wrapGAppsHook4
    makeWrapper
  ];
  buildInputs = [
    gtk4
    gtk4-layer-shell
    libpulseaudio
  ];
  nativeCheckInputs = [
    dbus
    pulseaudio
  ];
  preCheck = "export TMPDIR=/tmp";
  cargoTestFlags = [ "--all-targets" ];
  postFixup = ''
    wrapProgram "$out/bin/desktop-ring" --prefix PATH : ${
      lib.makeBinPath [
        systemd
        libnotify
      ]
    }
  '';
  meta = {
    description = "Hardware-aware displays and a universal Wayland pie menu";
    mainProgram = "desktop-ring";
    platforms = lib.platforms.linux;
    license = lib.licenses.mit;
  };
}
