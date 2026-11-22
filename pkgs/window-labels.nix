{
  lib,
  rustPlatform,
  makeWrapper,
  fontconfig,
  nerd-fonts,
  findutils,
}:
rustPlatform.buildRustPackage {
  pname = "window-labels";
  version = "0.1.0";
  src = ../dotfiles/window-labels/.local/share/window-labels;
  cargoLock.lockFile = ../dotfiles/window-labels/.local/share/window-labels/Cargo.lock;
  nativeBuildInputs = [
    makeWrapper
    findutils
  ];
  postFixup = ''
    font="$(find ${nerd-fonts.jetbrains-mono}/share/fonts -name JetBrainsMonoNerdFont-Bold.ttf -print -quit)"
    symbols="$(find ${nerd-fonts.symbols-only}/share/fonts -name SymbolsNerdFontMono-Regular.ttf -print -quit)"
    test -r "$font"
    test -r "$symbols"
    wrapProgram "$out/bin/window-labels" \
      --set-default WINDOW_LABELS_FONT "$font" \
      --set-default WINDOW_LABELS_SYMBOL_FONT "$symbols" \
      --prefix PATH : ${lib.makeBinPath [ fontconfig ]}
  '';
  meta = {
    description = "Click-through name labels on visible Hyprland windows";
    mainProgram = "window-labels";
    platforms = lib.platforms.linux;
  };
}
