{
  config,
  lib,
  profile,
  ...
}:
{
  imports = [
    ./hardware-configuration.nix
  ]
  ++ lib.optional (builtins.pathExists ./local.nix) ./local.nix;
  workstation = {
    laptop = false;
    gpu = lib.mkIf (profile == "workstation") (lib.mkDefault "nvidia");
    # The desktop's GP102 / GTX 1080 Ti requires the proprietary kernel module.
    nvidiaOpen = lib.mkDefault false;
  };
  # R580 is the final NVIDIA branch supporting Pascal cards.
  hardware.nvidia.package = lib.mkIf (
    profile != "recovery" && config.workstation.gpu == "nvidia"
  ) config.boot.kernelPackages.nvidiaPackages.legacy_580;
}
