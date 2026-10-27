{
  lib,
  stdenv,
  fetchurl,
  unzip,
  autoPatchelfHook,
  runCommand,
  symlinkJoin,
  versionCheckHook,
  openssl,
  zlib,
  writeShellApplication,
  flatpak,
  vimPlugins,
}:
let
  mkTool =
    {
      pname,
      version,
      owner,
      tag,
      archive,
      hash,
      extraLibraries ? [ ],
      license ? lib.licenses.mpl20,
    }:
    stdenv.mkDerivation {
      inherit pname version;
      src = fetchurl {
        url = "https://github.com/${owner}/${pname}/releases/download/${tag}/${archive}";
        inherit hash;
      };
      nativeBuildInputs = [
        unzip
        autoPatchelfHook
      ];
      buildInputs = [ stdenv.cc.cc.lib ] ++ extraLibraries;
      unpackPhase = ''unzip "$src"'';
      dontBuild = true;
      installPhase = ''install -Dm755 ${pname} "$out/bin/${pname}"'';
      nativeInstallCheckInputs = [ versionCheckHook ];
      doInstallCheck = true;
      versionCheckProgram = "${placeholder "out"}/bin/${pname}";
      meta = {
        description = "Pinned ${pname} for Roblox development";
        homepage = "https://github.com/${owner}/${pname}";
        inherit license;
        platforms = [ "x86_64-linux" ];
        mainProgram = pname;
      };
    };
  types = fetchurl {
    name = "roblox-globalTypes.d.luau";
    url = "https://luau-lsp.pages.dev/type-definitions/globalTypes.RobloxScriptSecurity.d.luau";
    sha256 = "71698e2454aacef1a144a498ffc1d7ea80654b9593025344672bc9106997bf6a";
    curlOptsList = [
      "--user-agent"
      "nixos-config-runtime-audit"
    ];
  };
  docs = fetchurl {
    name = "roblox-api-docs.json";
    url = "https://raw.githubusercontent.com/MaximumADHD/Roblox-Client-Tracker/a020070e2758a71b5d61cf692eee3704a5793011/api-docs/en-us.json";
    sha256 = "5c0735595dd4c8b2cb81c29c83f4fb6ec4e39974cf462dc63f312b144698858a";
  };
in
rec {
  rojo = mkTool {
    pname = "rojo";
    version = "7.7.1";
    owner = "rojo-rbx";
    tag = "v7.7.1";
    archive = "rojo-7.7.1-linux-x86_64.zip";
    hash = "sha256:00feb4fa0829a1dd72b49df2639da519a352bfe13cadcd83969e2ba2bb5693c4";
    license = lib.licenses.mpl20;
  };
  lune = mkTool {
    pname = "lune";
    version = "0.11.1";
    owner = "lune-org";
    tag = "v0.11.1";
    archive = "lune-0.11.1-linux-x86_64.zip";
    hash = "sha256:39859282ce677fce19e6eb45c37596a90a25c324c95b4e7e02d428b6cae294a1";
  };
  selene = mkTool {
    pname = "selene";
    version = "0.32.0";
    owner = "Kampfkarren";
    tag = "0.32.0";
    archive = "selene-0.32.0-linux.zip";
    hash = "sha256:d3773393578580074386e69337d35b7acddfbaa9fc38964c07fa3e28436ade9b";
  };
  luau-lsp = mkTool {
    pname = "luau-lsp";
    version = "1.70.1";
    owner = "JohnnyMorganz";
    tag = "1.70.1";
    archive = "luau-lsp-linux-x86_64.zip";
    hash = "sha256:1a2ea1ae4f98f8946cefd970a4b54853e11ab4775e6932faa7f60cf920346567";
    license = lib.licenses.mit;
  };
  stylua = mkTool {
    pname = "stylua";
    version = "2.6.0";
    owner = "JohnnyMorganz";
    tag = "v2.6.0";
    archive = "stylua-linux-x86_64.zip";
    hash = "sha256:a485f72bbfa22e4642e77a84b5edc2611a5cab7477b34e2e709dd8f78e919895";
  };
  wally = mkTool {
    pname = "wally";
    version = "0.3.2";
    owner = "UpliftGames";
    tag = "v0.3.2";
    archive = "wally-v0.3.2-linux.zip";
    hash = "sha256-If27U9/uOX/SHKf90gjbZc/w+H8P0EXNtZS5UZgb1z8=";
    extraLibraries = [
      openssl
      zlib
    ];
    license = lib.licenses.mpl20;
  };
  rokit = stdenv.mkDerivation {
    pname = "rokit";
    version = "1.2.0";
    src = fetchurl {
      url = "https://github.com/rojo-rbx/rokit/releases/download/v1.2.0/rokit-1.2.0-linux-x86_64.zip";
      sha256 = "951a7f3ec3d2a5e021fd1867d32f69f010ee4c2927f644b759578afc59c65fc0";
    };
    nativeBuildInputs = [
      unzip
      autoPatchelfHook
    ];
    buildInputs = [ stdenv.cc.cc.lib ];
    unpackPhase = ''unzip "$src"'';
    dontBuild = true;
    installPhase = ''install -Dm755 rokit "$out/bin/rokit"'';
    meta = {
      description = "Roblox toolchain manager, matching the reference installation";
      homepage = "https://github.com/rojo-rbx/rokit";
      license = lib.licenses.mit;
      platforms = [ "x86_64-linux" ];
      mainProgram = "rokit";
    };
  };
  roblox-toolchain = symlinkJoin {
    name = "roblox-toolchain";
    paths = [
      rojo
      lune
      selene
      luau-lsp
      stylua
      wally
      rokit
      roblox-studio
    ];
  };
  roblox-studio = writeShellApplication {
    name = "roblox-studio";
    runtimeInputs = [ flatpak ];
    text = ''
      exec flatpak run --file-forwarding org.vinegarhq.Vinegar @@ "$@" @@
    '';
  };
  rojo-studio-plugin = fetchurl {
    name = "Rojo-7.7.1.rbxm";
    url = "https://github.com/rojo-rbx/rojo/releases/download/v7.7.1/Rojo.rbxm";
    sha256 = "50a8d83db87deab4d65fd6100eb74396de232355b1ae89c641035d02c49db6f4";
  };
  roblox-editor-resources = runCommand "roblox-editor-resources" { } ''
    mkdir -p "$out/parser"
    ln -s ${types} "$out/globalTypes.d.luau"
    ln -s ${docs} "$out/api-docs.json"
    ln -s ${vimPlugins.nvim-treesitter-parsers.luau}/parser/luau.so "$out/parser/luau.so"
  '';
}
