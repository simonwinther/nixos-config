{ pkgs, ... }:
let
  inherit (pkgs) lib;
in
{
  tobi-try = pkgs.stdenvNoCC.mkDerivation {
    pname = "tobi-try";
    version = "1.10.1";
    src = pkgs.fetchzip {
      extension = "tar.gz";
      url = "https://codeload.github.com/tobi/try/tar.gz/refs/tags/v1.10.1";
      hash = "sha256-ZSt6LSp0AQTbdN86lJGJPWcx6oFR63AFi4s8Vjr5a5o=";
    };
    nativeBuildInputs = [ pkgs.makeWrapper ];
    dontBuild = true;
    installPhase = ''
      install -Dm755 try.rb "$out/share/try/try.rb"
      makeWrapper ${pkgs.ruby}/bin/ruby "$out/bin/try" --add-flags "$out/share/try/try.rb"
    '';
    meta = {
      license = lib.licenses.mit;
      mainProgram = "try";
    };
  };
  ant-contrib = pkgs.stdenvNoCC.mkDerivation {
    pname = "ant-contrib";
    version = "1.0b3";
    src = pkgs.fetchurl {
      url = "https://repo.maven.apache.org/maven2/ant-contrib/ant-contrib/1.0b3/ant-contrib-1.0b3.jar";
      hash = "sha256-vjOmmBgxC1xV5B3BHUjNiV9fEp2ksNKML0xsPhy88/w=";
    };
    dontUnpack = true;
    dontBuild = true;
    installPhase = ''install -Dm444 "$src" "$out/share/java/ant-contrib.jar"'';
    meta.license = lib.licenses.asl20;
  };
}
