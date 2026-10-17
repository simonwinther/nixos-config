{
  lib,
  stdenvNoCC,
  python3,
  makeWrapper,
  wrapGAppsHook4,
  gobject-introspection,
  gtk4,
  gdk-pixbuf,
  glib,
  pango,
}:
let
  python = python3.withPackages (p: [
    p.pygobject3
    p.pillow
  ]);
in
stdenvNoCC.mkDerivation {
  pname = "background-grid";
  version = "1.0.0";
  dontUnpack = true;
  dontBuild = true;
  nativeBuildInputs = [
    makeWrapper
    wrapGAppsHook4
    gobject-introspection
  ];
  buildInputs = [
    gtk4
    gdk-pixbuf
    glib
    pango
  ];
  installPhase = ''
    mkdir -p "$out/bin" "$out/share/background-grid"
    cp ${../dotfiles/background-grid/.config/background-grid/picker.py} "$out/share/background-grid/picker.py"
    cp ${../dotfiles/background-grid/.config/background-grid/style.css} "$out/share/background-grid/style.css"
    makeWrapper ${python}/bin/python3 "$out/bin/background-grid-native" \
      --add-flags "$out/share/background-grid/picker.py"
  '';
  meta = {
    platforms = lib.platforms.linux;
    mainProgram = "background-grid-native";
  };
}
