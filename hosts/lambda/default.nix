{ lib, ... }:
{
  imports = [
    ./hardware-configuration.nix
  ]
  ++ lib.optional (builtins.pathExists ./local.nix) ./local.nix;
  workstation = {
    laptop = true;
    gpu = "amd";
  };
}
