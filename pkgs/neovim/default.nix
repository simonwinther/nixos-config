{
  lib,
  runCommand,
  fetchFromGitHub,
  fetchzip,
  stdenv,
  rustPlatform,
  tree-sitter,
  nodejs,
  neovim-unwrapped,
}:
let
  sources = builtins.fromJSON (builtins.readFile ./plugins.json);
  sourcesByName = lib.mapAttrs (
    name: spec:
    fetchFromGitHub {
      inherit (spec) owner repo rev;
      hash = spec.hash or (throw "Missing source hash for Neovim plugin ${name}");
    }
  ) sources;
  blink = rustPlatform.buildRustPackage {
    pname = "blink-cmp-fuzzy";
    version = sources."blink.cmp".rev;
    src = sourcesByName."blink.cmp";
    cargoLock.lockFile = ./blink-Cargo.lock;
    postPatch = ''
      cat > build.rs <<'RS'
      fn main() {
          std::fs::create_dir_all("target/release").unwrap();
          std::fs::write("target/release/version", "${sources."blink.cmp".rev}").unwrap();
      }
      RS
    '';
    doCheck = false; # mlua's module mode links to LuaJIT in Neovim, not a standalone test executable.
    installPhase = ''
      mkdir -p "$out/target/release"
      cp -r ${sourcesByName."blink.cmp"}/. "$out/"
      cp target/${stdenv.hostPlatform.rust.rustcTarget}/release/libblink_cmp_fuzzy.so target/release/version "$out/target/release/"
    '';
  };
  parserSpecs = builtins.fromJSON (builtins.readFile ./parsers.json);
  parser =
    spec:
    stdenv.mkDerivation {
      pname = "neovim-parser-${spec.name}";
      version = spec.revision;
      src = fetchzip {
        extension = "tar.gz";
        url = "${
          lib.replaceStrings [ "https://github.com/" ] [ "https://codeload.github.com/" ] spec.url
        }/tar.gz/${spec.revision}";
        inherit (spec) hash;
      };
      nativeBuildInputs = [ tree-sitter ] ++ lib.optional (spec.requiresNode or false) nodejs;
      buildPhase = ''
        runHook preBuild
        ${lib.optionalString (spec ? location) "cd ${lib.escapeShellArg spec.location}"}
        export RAYON_NUM_THREADS=1
        if ! test -f src/parser.c; then
          if test -f src/grammar.json; then tree-sitter generate src/grammar.json;
          else tree-sitter generate; fi
        fi
        $CC -O2 -fPIC -Isrc -c src/parser.c -o parser.o
        if test -f src/scanner.c; then
          $CC -O2 -fPIC -Isrc -c src/scanner.c -o scanner.o
        elif test -f src/scanner.cc; then
          $CXX -O2 -fPIC -Isrc -c src/scanner.cc -o scanner.o
        fi
        $CXX -shared parser.o $(test ! -f scanner.o || echo scanner.o) -o ${spec.name}.so
        runHook postBuild
      '';
      installPhase = ''install -Dm755 ${spec.name}.so "$out/parser/${spec.name}.so"'';
    };
  grammars = builtins.listToAttrs (
    map (spec: {
      name = spec.name;
      value = parser spec;
    }) parserSpecs
  );
  parsers = builtins.attrValues grammars;
  plugins = sourcesByName // {
    "blink.cmp" = blink;
  };
in
runCommand "locked-neovim-plugins"
  {
    passthru = {
      inherit grammars;
      fuzzy = blink;
    };
  }
  ''
    mkdir -p "$out"
    ${lib.concatStringsSep "\n" (
      lib.mapAttrsToList (name: path: ''ln -s ${path} "$out/${name}"'') plugins
    )}
    mkdir -p "$out/runtime/parser" "$out/runtime/queries"
    ${lib.concatMapStringsSep "\n" (path: ''ln -s ${path}/parser/* "$out/runtime/parser/"'') parsers}
  ''
