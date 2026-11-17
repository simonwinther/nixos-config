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
  # Phone SSH over Tailscale is the keyboard lockup recovery path in
  # docs/KEYBOARD-RECOVERY.md, so declare it instead of relying on tailscaled state.
  services.tailscale.extraSetFlags = [ "--ssh" ];
}
