{
  lib,
  stdenvNoCC,
  fetchurl,
  buildFHSEnv,
  writeShellScript,
  makeDesktopItem,
}:
let
  version = "5.12.4";
  application = stdenvNoCC.mkDerivation {
    pname = "slicer3d-unwrapped";
    inherit version;
    src = fetchurl {
      name = "Slicer-${version}-linux-amd64.tar.gz";
      url = "https://slicer-packages.kitware.com/api/v1/item/6aa1beb7ce9de556d3010204/download";
      hash = "sha256-MRo9KlIEazRMRMFgpyMtl317c81JYd1Sle6hh5xqo3A=";
    };
    dontConfigure = true;
    dontBuild = true;
    dontPatchELF = true;
    dontStrip = true;
    installPhase = ''
      runHook preInstall
      mkdir -p "$out"
      cp -a . "$out/"
      runHook postInstall
    '';
  };
  launcher = writeShellScript "slicer3d-launch" ''
    set -eu
    dataRoot="''${XDG_DATA_HOME:-$HOME/.local/share}/slicer3d"
    app="$dataRoot/${version}"
    mkdir -p "$dataRoot"
    # Slicer installs extensions and Python packages into its application tree.
    # Copy once per release; keep the pinned Nix store contents immutable.
    (
      flock 9
      if [ ! -d "$app" ]; then
        staging=$(mktemp -d "$dataRoot/.${version}.XXXXXX")
        trap 'rm -rf "$staging"' EXIT
        cp -a --reflink=auto ${application}/. "$staging/"
        chmod -R u+w "$staging"
        mv -T "$staging" "$app"
      fi
    ) 9>"$dataRoot/.install.lock"
    # Use Slicer's bundled Qt plugins under XWayland, without host Qt plugins.
    unset QT_PLUGIN_PATH QT_QPA_PLATFORMTHEME QT_STYLE_OVERRIDE QML2_IMPORT_PATH QML_IMPORT_PATH
    export QT_QPA_PLATFORM=xcb
    exec "$app/Slicer" "$@"
  '';
  desktopItem = makeDesktopItem {
    name = "slicer3d";
    desktopName = "3D Slicer";
    genericName = "Medical image analysis";
    comment = "Visualize, segment, and analyze medical images";
    exec = "slicer3d %F";
    icon = "slicer3d";
    categories = [
      "Science"
      "MedicalSoftware"
    ];
  };
in
buildFHSEnv {
  pname = "slicer3d";
  inherit version;
  multiArch = false;
  targetPkgs =
    pkgs: with pkgs; [
      coreutils
      util-linux
      libGL
      libGLU
      glib
      dbus
      fontconfig
      freetype
      alsa-lib
      libpulseaudio
      nss
      nspr
      zlib
      pcre2
      expat
      libx11
      libxext
      libxrender
      libxi
      libxt
      libxtst
      libxcursor
      libxfixes
      libxrandr
      libxcomposite
      libxdamage
      libsm
      libice
      libxcb
      libxkbcommon
      libxcb-util
      libxcb-image
      libxcb-keysyms
      libxcb-render-util
      libxcb-wm
      libxcb-cursor
    ];
  runScript = launcher;
  extraInstallCommands = ''
    mkdir -p "$out/share"
    ln -s ${desktopItem}/share/applications "$out/share/applications"
    install -Dm444 ${application}/Slicer.png "$out/share/icons/hicolor/128x128/apps/slicer3d.png"
  '';
  passthru.unwrapped = application;
  meta = {
    description = "Medical image visualization, segmentation, and analysis";
    homepage = "https://www.slicer.org";
    license = {
      shortName = "Slicer";
      fullName = "3D Slicer Contribution and Software License Agreement";
      url = "https://github.com/Slicer/Slicer/blob/v${version}/License.txt";
      free = true;
    };
    platforms = [ "x86_64-linux" ];
    mainProgram = "slicer3d";
    sourceProvenance = [ lib.sourceTypes.binaryNativeCode ];
  };
}
