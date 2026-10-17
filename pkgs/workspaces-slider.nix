{
  lib,
  rustPlatform,
  makeWrapper,
  fontconfig,
  nerd-fonts,
  findutils,
  wayland,
}:
rustPlatform.buildRustPackage {
  pname = "workspaces-slider";
  version = "0.1.0";
  src = ../dotfiles/waybar/.config/waybar/workspaces-slider-rs;
  cargoLock.lockFile = ../dotfiles/waybar/.config/waybar/workspaces-slider-rs/Cargo.lock;
  nativeBuildInputs = [
    makeWrapper
    findutils
  ];
  preBuild = ''
    export WORKSPACES_SLIDER_FONT="$(find ${nerd-fonts.jetbrains-mono}/share/fonts -name JetBrainsMonoNerdFont-Bold.ttf -print -quit)"
    test -r "$WORKSPACES_SLIDER_FONT"
  '';
  postFixup = ''
    wrapProgram "$out/bin/workspaces-slider" \
      --set-default WORKSPACES_SLIDER_FONT "$WORKSPACES_SLIDER_FONT" \
      --prefix PATH : ${lib.makeBinPath [ fontconfig ]} \
      --prefix LD_LIBRARY_PATH : ${lib.makeLibraryPath [ wayland ]}
  '';
  meta = {
    description = "Animated multi-monitor workspace indicators";
    mainProgram = "workspaces-slider";
    platforms = lib.platforms.linux;
  };
}
