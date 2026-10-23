{
  lib,
  stdenvNoCC,
  fetchFromGitHub,
}:
stdenvNoCC.mkDerivation {
  pname = "obs-bookman-font";
  version = "20200910";
  src = fetchFromGitHub {
    owner = "ArtifexSoftware";
    repo = "urw-base35-fonts";
    rev = "c15105598aa7eb256b1ebfcecd3d078801521e73";
    hash = "sha256-YQl5IDtodcbTV3D6vtJi7CwxVtHHl58fG6qCAoSaP4U=";
  };
  dontBuild = true;
  installPhase = ''
    runHook preInstall
    install -Dm644 fonts/URWBookman-*.otf -t "$out/share/fonts/opentype"
    install -Dm644 LICENSE COPYING -t "$out/share/doc/obs-bookman-font"
    runHook postInstall
  '';
  meta = {
    description = "Original URW Bookman font used by the OBS countdown";
    homepage = "https://github.com/ArtifexSoftware/urw-base35-fonts";
    # The upstream LICENSE additionally permits embedding in documents.
    license = lib.licenses.agpl3Only;
    platforms = lib.platforms.all;
  };
}
