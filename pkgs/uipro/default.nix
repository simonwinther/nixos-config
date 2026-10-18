{
  lib,
  buildNpmPackage,
  makeWrapper,
  nodejs,
}:
buildNpmPackage {
  pname = "uipro";
  version = "2.2.3";
  src = lib.cleanSource ./.;
  npmDepsHash = "sha256-r97fydRjPNKVo3FiLfGLFAtBLQfh9DwvPkYoCMCCmgs=";
  nativeBuildInputs = [ makeWrapper ];
  dontNpmBuild = true;
  installPhase = ''
    runHook preInstall
    mkdir -p "$out/lib/uipro" "$out/bin"
    cp -r node_modules "$out/lib/uipro/"
    makeWrapper ${lib.getExe nodejs} "$out/bin/uipro" \
      --add-flags "$out/lib/uipro/node_modules/uipro-cli/dist/index.js"
    runHook postInstall
  '';
  meta = {
    description = "UI Pro CLI at the reference workstation version";
    license = lib.licenses.mit;
    mainProgram = "uipro";
  };
}
