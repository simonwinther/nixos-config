{
  inputs,
  pkgs,
  unstable,
  source ? inputs.hyprspace,
}:
let
  providers = [
    "bluetooth"
    "calc"
    "clipboard"
    "desktopapplications"
    "files"
    "menus"
    "providerlist"
    "runner"
    "symbols"
    "todo"
    "unicode"
    "websearch"
  ];
  elephant = (unstable.elephant.override { enabledProviders = providers; }).overrideAttrs (old: {
    patches = (old.patches or [ ]) ++ [
      (source + "/companion/elephant-2.22.0.patch")
      ./clipboard-history.patch
      ./clipboard-paste.patch
      ./clipboard-locking.patch
    ];
    postCheck = (old.postCheck or "") + ''
      go test ./internal/providers/clipboard -run '^TestClipboard' -count=1
    '';
  });
  walkerSource = pkgs.fetchzip {
    extension = "tar.gz";
    url = "https://codeload.github.com/abenz1267/walker/tar.gz/refs/tags/v2.17.0";
    hash = "sha256-gxHJsrJZo2qbKK47Kf/9ho3i/HhRwkL8XvPnczGPd9E=";
  };
  walker = unstable.walker.overrideAttrs (old: {
    version = "2.17.0";
    src = walkerSource;
    cargoDeps = unstable.rustPlatform.importCargoLock { lockFile = ./walker-Cargo.lock; };
    patches = (old.patches or [ ]) ++ [
      (source + "/companion/walker-2.17.0.patch")
      ./clipboard-preview.patch
    ];
    nativeBuildInputs = (old.nativeBuildInputs or [ ]) ++ [ pkgs.makeWrapper ];
    postFixup = (old.postFixup or "") + ''
      wrapProgram "$out/bin/walker" \
        --prefix PATH : ${elephant}/bin \
        --set ELEPHANT_PROVIDER_DIR ${elephant}/lib/elephant/providers
    '';
  });
in
{
  inherit walker elephant;
}
