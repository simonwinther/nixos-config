{
  lib,
  stdenvNoCC,
  fetchurl,
  buildFHSEnv,
  writeShellApplication,
  writeShellScript,
  coreutils,
  findutils,
  gnugrep,
  util-linux,
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
  # The launch marker's mtime records each release's last launch, and every
  # running instance holds a shared flock on it.
  launchMarker = ".slicer3d-launch";
  # Removes copied releases except the launching one and the most recently
  # launched other release (the rollback). Extensions and pip packages live in
  # each copy and match its revision; Slicer offers to reinstall bookmarked
  # extensions from ~/.config/slicer.org in a new release.
  cleanup = writeShellApplication {
    name = "slicer3d-cleanup";
    runtimeInputs = [
      coreutils
      findutils
      gnugrep
      util-linux
    ];
    text = ''
      data_root=$1
      current=$2
      renice -n 19 -p $$ >/dev/null || true
      ionice -c 3 -p $$ || true
      cd -- "$data_root"
      physical_root=$(pwd -P)
      shopt -s nullglob

      exec 7>.cleanup.lock
      flock -n 7 || exit 0

      retire() {
        local retired
        retired=$(mktemp -d .retired.XXXXXX)
        mv -- "$1" "$retired/"
      }

      launch_time() {
        local marker="$1/${launchMarker}"
        if [ -f "$marker" ] && [ ! -L "$marker" ]; then
          stat -c %Y -- "$marker"
        else
          stat -c %Y -- "$1"
        fi
      }

      is_in_use() {
        local marker="$1/${launchMarker}"
        if [ -L "$marker" ] || { [ -e "$marker" ] && [ ! -f "$marker" ]; }; then
          return 0
        fi
        if [ -f "$marker" ]; then
          exec 8<"$marker"
          if ! flock -xn 8; then
            exec 8<&-
            return 0
          fi
          exec 8<&-
        fi
        local executables
        executables=$(find /proc -mindepth 2 -maxdepth 2 -name exe -printf '%l\n' 2>/dev/null || true)
        grep -qF -e "$physical_root/$1/" -e "$data_root/$1/" <<<"$executables"
      }

      # Launchers create, copy and mark releases only while holding this lock.
      exec 9>.install.lock
      flock 9

      for staging in .[0-9]*.??????; do
        if [ -d "$staging" ] && [ ! -L "$staging" ]; then
          retire "$staging"
        fi
      done

      for release in [0-9]*; do
        if [[ $release =~ ^[0-9][0-9A-Za-z._+-]*$ ]] && [ "$release" != "$current" ] &&
          [ -d "$release" ] && [ ! -L "$release" ]; then
          printf '%s %s\n' "$(launch_time "$release")" "$release"
        fi
      done | sort -k1,1nr -k2,2Vr | tail -n +2 | while read -r _ release; do
        if is_in_use "$release"; then
          echo "slicer3d-cleanup: keeping $release, it is still running" >&2
        else
          retire "$release"
        fi
      done

      exec 9>&-
      for retired in .retired.*; do
        chmod -R u+w -- "$retired" 2>/dev/null || true
        rm -rf --one-file-system -- "$retired"
      done
    '';
  };
  launcher = writeShellScript "slicer3d-launch" ''
    set -eu
    dataRoot="''${XDG_DATA_HOME:-$HOME/.local/share}/slicer3d"
    app="$dataRoot/${version}"
    marker="$app/${launchMarker}"
    mkdir -p "$dataRoot"
    exec 9>"$dataRoot/.install.lock"
    flock 9
    # Slicer installs extensions and Python packages into its application tree.
    # Copy once per release; keep the pinned Nix store contents immutable.
    if [ ! -d "$app" ]; then
      staging=$(mktemp -d "$dataRoot/.${version}.XXXXXX")
      trap 'rm -rf "$staging"' EXIT
      cp -a --reflink=auto ${application}/. "$staging/"
      chmod -R u+w "$staging"
      mv -T "$staging" "$app"
      trap - EXIT
    fi
    touch "$marker"
    # Slicer inherits this descriptor, keeping the release marked in use.
    exec 8<"$marker"
    flock -s 8
    exec 9>&-
    ( exec ${cleanup}/bin/slicer3d-cleanup "$dataRoot" "${version}" 8<&- </dev/null >/dev/null & )
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
  passthru = {
    unwrapped = application;
    inherit cleanup launcher;
  };
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
