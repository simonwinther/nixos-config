{
  lib,
  rustPlatform,
  makeWrapper,
  fd,
  wl-clipboard,
  xdg-utils,
  libnotify,
}:
rustPlatform.buildRustPackage {
  pname = "desktop-search";
  version = "0.1.0";
  src = lib.fileset.toSource {
    root = ../dotfiles;
    fileset = lib.fileset.unions [
      ../dotfiles/desktop-search/.local/share/desktop-search
      ../dotfiles/desktop-bar/.local/share/desktop-bar/src/process.rs
      ../dotfiles/desktop-bar/.local/share/desktop-bar/src/fuzzy.rs
    ];
  };
  sourceRoot = "source/desktop-search/.local/share/desktop-search";
  cargoLock.lockFile = ../dotfiles/desktop-search/.local/share/desktop-search/Cargo.lock;
  nativeBuildInputs = [ makeWrapper ];
  postFixup = ''
    wrapProgram "$out/bin/desktop-search" \
      --prefix PATH : ${
        lib.makeBinPath [
          fd
          wl-clipboard
          xdg-utils
          libnotify
        ]
      }
  '';
  meta = {
    description = "Native desktop search providers and clipboard history";
    mainProgram = "desktop-search";
    platforms = lib.platforms.linux;
  };
}
