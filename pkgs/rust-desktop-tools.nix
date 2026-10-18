{ pkgs, hyprland }:
let
  inherit (pkgs) lib;
  dots = ../dotfiles;
  native =
    {
      pname,
      src,
      gui ? false,
      checkInputs ? [ ],
    }:
    pkgs.rustPlatform.buildRustPackage {
      inherit pname src;
      version = "1.0.0";
      cargoLock.lockFile = src + "/Cargo.lock";
      nativeBuildInputs = lib.optionals gui [
        pkgs.pkg-config
        pkgs.wrapGAppsHook4
      ];
      buildInputs = lib.optionals gui [ pkgs.gtk4 ];
      nativeCheckInputs = [
        pkgs.bash
        pkgs.coreutils
      ]
      ++ checkInputs;
      cargoTestFlags = [ "--all-targets" ];
      preCheck = ''
        export TMPDIR=/tmp
        if test -d tests; then
          substituteInPlace tests/*.rs \
            --replace-warn '/usr/bin:/bin' '${
              lib.makeBinPath (
                [
                  pkgs.bash
                  pkgs.coreutils
                ]
                ++ checkInputs
              )
            }'
        fi
      ''
      + lib.optionalString (pname == "dictation-volume-duck") ''
        substituteInPlace tests/commands.rs \
          --replace-fail '/bin/sleep' '${pkgs.coreutils}/bin/sleep' \
          --replace-fail '/bin/rm' '${pkgs.coreutils}/bin/rm'
      ''
      + lib.optionalString (pname == "iphone-transfer") ''
        substituteInPlace tests/transfers.rs \
          --replace-fail '/bin/cat' '${pkgs.coreutils}/bin/cat'
      '';
      meta.platforms = lib.platforms.linux;
    };
  wrapped =
    name: package: binary: dependencies:
    pkgs.symlinkJoin {
      inherit name;
      paths = [ package ];
      nativeBuildInputs = [ pkgs.makeWrapper ];
      passthru.unwrapped = package;
      postBuild = ''
        rm "$out/bin/${binary}"
        makeWrapper ${package}/bin/${binary} "$out/bin/${binary}" \
          ${lib.optionalString (dependencies != [ ]) "--prefix PATH : ${lib.makeBinPath dependencies}"} \
          --prefix LD_LIBRARY_PATH : ${lib.makeLibraryPath [ pkgs.wayland ]} \
          ${lib.optionalString (
            binary == "cluster-native"
          ) ''--run 'export PATH="$HOME/.local/bin:$PATH"' ''}
      '';
      meta = package.meta // {
        mainProgram = binary;
      };
    };
  duck = native {
    pname = "dictation-volume-duck";
    src = dots + "/chrome/.local/share/dictation-volume-duck";
  };
  text = native {
    pname = "text-picker";
    src = dots + "/text-picker/.local/share/text-picker";
    checkInputs = [ pkgs.fzf ];
  };
  plot = native {
    pname = "formula-plot";
    src = dots + "/bin/.local/share/plot";
    gui = true;
  };
  iphone = native {
    pname = "iphone-transfer";
    src = dots + "/iphone-transfer/.local/share/iphone-transfer";
  };
  cluster = pkgs.pkgsStatic.rustPlatform.buildRustPackage {
    pname = "cluster-tools";
    version = "1.0.0";
    src = dots + "/cluster/.local/share/cluster";
    cargoLock.lockFile = dots + "/cluster/.local/share/cluster/Cargo.lock";
    cargoTestFlags = [ "--all-targets" ];
    nativeCheckInputs = [
      pkgs.bash
      pkgs.coreutils
    ];
    preCheck = "export TMPDIR=/tmp";
    meta.platforms = lib.platforms.linux;
  };
in
{
  dictation-volume-duck = wrapped "dictation-volume-duck-1.0.0" duck "dictation-volume-duck-native" [
    pkgs.wireplumber
    pkgs.pulseaudio
    pkgs.coreutils
  ];
  text-picker = wrapped "text-picker-1.0.0" text "text-picker-native" [
    pkgs.fzf
    pkgs.wtype
    pkgs.ghostty
    pkgs.libnotify
    pkgs.bash
    hyprland
  ];
  formula-plot = wrapped "formula-plot-1.0.0" plot "plot-native" [ ];
  iphone-transfer = wrapped "iphone-transfer-1.0.0" iphone "iphone-transfer-native" [
    pkgs.tailscale
    pkgs.zenity
    pkgs.nautilus
    pkgs.file
    pkgs.libnotify
  ];
  # The ELF payload is static so setup can transfer it to a non-Nix remote host.
  cluster-tools = wrapped "cluster-tools-1.0.0" cluster "cluster-native" (
    with pkgs;
    [
      git
      openssh
      rsync
      bash
      coreutils
      findutils
      gnugrep
      gnused
      gawk
      gnutar
      gzip
      bzip2
      curl
      stow
      ncurses
    ]
  );
}
