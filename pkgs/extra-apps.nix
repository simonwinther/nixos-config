{ pkgs, unstable }:
let
  inherit (pkgs) lib;
in
{
  nordvpn-tui = pkgs.stdenvNoCC.mkDerivation {
    pname = "nordvpn-tui";
    version = "0.1.0";
    src = pkgs.fetchurl {
      url = "https://github.com/simonwinther/nordvpn-tui/releases/download/v0.1.0/nordvpn-tui_0.1.0_linux_amd64.tar.gz";
      sha256 = "dda52009790cc9996b597bcdd935e7c0a84b139948949dbb4d832d40c37962d2";
    };
    sourceRoot = ".";
    nativeBuildInputs = [ pkgs.makeWrapper ];
    dontBuild = true;
    installPhase = ''
      install -Dm755 nordvpn-tui "$out/bin/nordvpn-tui"
      install -Dm444 LICENSE "$out/share/doc/nordvpn-tui/LICENSE"
      wrapProgram "$out/bin/nordvpn-tui" --prefix PATH : ${unstable.nordvpn}/bin
    '';
    meta = {
      license = lib.licenses.mit;
      platforms = [ "x86_64-linux" ];
      mainProgram = "nordvpn-tui";
    };
  };
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
