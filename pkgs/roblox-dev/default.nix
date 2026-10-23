{
  lib,
  stdenv,
  fetchurl,
  unzip,
  autoPatchelfHook,
  runCommand,
  vimPlugins,
}:
let
  types = fetchurl {
    name = "roblox-globalTypes.d.luau";
    url = "https://luau-lsp.pages.dev/type-definitions/globalTypes.RobloxScriptSecurity.d.luau";
    sha256 = "71698e2454aacef1a144a498ffc1d7ea80654b9593025344672bc9106997bf6a";
    curlOptsList = [ "--user-agent" "nixos-config-runtime-audit" ];
  };
  docs = fetchurl {
    name = "roblox-api-docs.json";
    url = "https://raw.githubusercontent.com/MaximumADHD/Roblox-Client-Tracker/a020070e2758a71b5d61cf692eee3704a5793011/api-docs/en-us.json";
    sha256 = "5c0735595dd4c8b2cb81c29c83f4fb6ec4e39974cf462dc63f312b144698858a";
  };
in
{
  rokit = stdenv.mkDerivation {
    pname = "rokit";
    version = "1.2.0";
    src = fetchurl {
      url = "https://github.com/rojo-rbx/rokit/releases/download/v1.2.0/rokit-1.2.0-linux-x86_64.zip";
      sha256 = "951a7f3ec3d2a5e021fd1867d32f69f010ee4c2927f644b759578afc59c65fc0";
    };
    nativeBuildInputs = [ unzip autoPatchelfHook ];
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
