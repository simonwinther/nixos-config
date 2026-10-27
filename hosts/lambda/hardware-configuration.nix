{ ... }:
{
  # Reviewed ThinkPad L14 Gen 1: Ryzen 5 PRO 4650U, Renoir, AX200, RTL8111.
  # Filesystems and LUKS are declared by the reviewed Disko configuration.
  boot.initrd.availableKernelModules = [
    "nvme" "xhci_pci" "usb_storage" "sd_mod" "rtsx_pci_sdmmc" "r8169"
  ];
  boot.kernelModules = [ "kvm-amd" ];
  hardware.cpu.amd.updateMicrocode = true;
}
