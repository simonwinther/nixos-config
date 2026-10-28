{
  lib,
  stdenvNoCC,
  makeWrapper,
  python3,
  bash,
  coreutils,
  procps,
  systemd,
  findutils,
  jq,
  libnotify,
  fontconfig,
  power-profiles-daemon,
  glib,
  dconf,
  nautilus,
  gsettings-desktop-schemas,
  ffmpeg,
  imagemagick,
  file,
  wl-clipboard,
  fd,
  project-picker-tui,
  desktop-transcode,
}:
stdenvNoCC.mkDerivation {
  pname = "desktop-tools";
  version = "1.0.0";
  src = ../dotfiles/desktop-tools/.local/share/desktop-tools;
  nativeBuildInputs = [ makeWrapper ];
  dontBuild = true;
  installPhase = ''
    mkdir -p "$out/share/desktop-tools" "$out/bin"
    cp desktopctl.py desktop_process.py transcode.sh "$out/share/desktop-tools/"
    makeWrapper ${project-picker-tui}/bin/project-picker-core "$out/bin/project-picker" \
      --prefix PATH : "${lib.makeBinPath [ project-picker-tui ]}:$out/bin"
    makeWrapper ${project-picker-tui}/bin/project-picker-core "$out/bin/project-picker-host" \
      --add-flags "--native-host"
    makeWrapper ${bash}/bin/bash "$out/bin/desktop-transcode" \
      --add-flags "$out/share/desktop-tools/transcode.sh" \
      --prefix PATH : ${
        lib.makeBinPath [
          bash
          desktop-transcode
          coreutils
          findutils
          ffmpeg
          imagemagick
          file
          wl-clipboard
          libnotify
          fd
        ]
      }:"$out/bin"
    makeWrapper ${python3}/bin/python3 "$out/bin/desktopctl" \
      --add-flags "$out/share/desktop-tools/desktopctl.py" \
      --set-default XDG_DATA_DIRS /usr/local/share:/usr/share \
      --prefix XDG_DATA_DIRS : "${gsettings-desktop-schemas}/share/gsettings-schemas/${gsettings-desktop-schemas.name}" \
      --prefix XDG_DATA_DIRS : "${nautilus}/share/gsettings-schemas/${nautilus.name}" \
      --prefix PATH : ${
        lib.makeBinPath [
          bash
          coreutils
          procps
          systemd
          findutils
          jq
          libnotify
          fontconfig
          power-profiles-daemon
          imagemagick
          glib
          dconf
        ]
      }
  '';
  meta = {
    description = "Independent portable Hyprland desktop utilities";
    mainProgram = "desktopctl";
    platforms = lib.platforms.linux;
  };
}
