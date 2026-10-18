{ lib, pkgs }:
let
  sources = builtins.fromJSON (builtins.readFile ./sources.json);
  extensions = lib.mapAttrs (
    _: spec:
    let
      archive = pkgs.fetchurl {
        name = spec.archiveName;
        inherit (spec) url hash;
      };
    in
    if
      builtins.elem spec.id [
        "ms-vscode.cpptools"
        "ms-vscode.vscode-speech"
      ]
    then
      # Reuse the pinned Nixpkgs compatibility work: cpptools has its own musl
      # loader and .NET debugger; speech loads its audio library with dlopen.
      pkgs.vscode-extensions.${spec.publisher}.${spec.name}.overrideAttrs (old: {
        version = spec.version;
        src = archive;
        passthru = (old.passthru or { }) // {
          migration = spec;
        };
      })
    else
      pkgs.vscode-utils.buildVscodeMarketplaceExtension {
        mktplcRef = {
          inherit (spec) publisher name version;
        };
        vsix = archive;
        dontPatchELF = false;
        nativeBuildInputs = [ pkgs.autoPatchelfHook ];
        buildInputs =
          with pkgs;
          [
            stdenv.cc.cc.lib
            zlib
            openssl
            icu
            libsecret
            libunwind
            glib
            libuuid
            krb5
            cyrus_sasl
            ncurses
            expat
            libxcrypt-legacy
          ]
          ++ lib.optionals (spec.id == "redhat.java") (
            with pkgs;
            [
              libx11
              libxext
              libxrender
              libxtst
              libxi
              alsa-lib
            ]
          )
          ++ lib.optionals (spec.id == "georgewfraser.fsharp-language-server") [
            pkgs.lttng-ust
            pkgs.curl
          ];
        postPatch = lib.optionalString (spec.id == "georgewfraser.fsharp-language-server") ''
          # Apply the same .NET tracing ABI adaptation used by Nixpkgs cpptools.
          find . -name libcoreclrtraceptprovider.so -exec \
            patchelf --replace-needed liblttng-ust.so.0 liblttng-ust.so.1 {} \;
        '';
        postInstall = lib.optionalString (spec.id == "ms-toolsai.jupyter") ''
          # This target uses glibc; retain its Node bindings and omit the unused
          # Alpine/musl variants before checking the native dependencies.
          find "$out" -name '*.musl.node' -delete
        '';
        passthru.migration = spec;
      }
  ) sources;
  forEditor =
    editor:
    builtins.filter (extension: builtins.elem editor extension.migration.editors) (
      builtins.attrValues extensions
    );
  vscode = forEditor "vscode";
  cursor = forEditor "cursor";
in
pkgs.runCommand "locked-editor-extensions"
  {
    passthru = { inherit vscode cursor; };
  }
  ''
    mkdir -p "$out/vscode" "$out/cursor"
    ${lib.concatMapStringsSep "\n" (extension: ''
      ln -s ${extension}/share/vscode/extensions/${extension.vscodeExtUniqueId} \
        "$out/vscode/${extension.vscodeExtUniqueId}"
    '') vscode}
    ${lib.concatMapStringsSep "\n" (extension: ''
      ln -s ${extension}/share/vscode/extensions/${extension.vscodeExtUniqueId} \
        "$out/cursor/${extension.vscodeExtUniqueId}"
    '') cursor}
  ''
