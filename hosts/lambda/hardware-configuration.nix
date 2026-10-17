{ ... }:
{
  # Reference: ThinkPad L14 Gen 1, Ryzen 5 PRO 4650U, Radeon Renoir, AX200.
  # Generate a NixOS hardware module before any future laptop installation.
  boot.initrd.availableKernelModules = [
    "nvme"
    "xhci_pci"
    "usb_storage"
    "sd_mod"
  ];
  boot.kernelModules = [ "kvm-amd" ];
  hardware.cpu.amd.updateMicrocode = true;
}
