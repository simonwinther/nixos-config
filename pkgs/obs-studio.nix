{ pkgs, obs-studio }:
pkgs.symlinkJoin {
  name = "obs-studio-${obs-studio.version}-desktop";
  paths = [ obs-studio ];
  nativeBuildInputs = [ pkgs.makeWrapper ];
  postBuild = ''
    # Both OBS and its NVENC probe dlopen the installed NVIDIA driver. It must
    # precede build-time CUDA stubs on the GTX 1080 Ti's proprietary driver.
    wrapProgram "$out/bin/obs" --prefix LD_LIBRARY_PATH : /run/opengl-driver/lib
    wrapProgram "$out/bin/obs-nvenc-test" --prefix LD_LIBRARY_PATH : /run/opengl-driver/lib
  '';
  meta = obs-studio.meta;
}
