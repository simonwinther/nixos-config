{ ... }:
{
  # Reviewed ThinkPad L14 Gen 1: Ryzen 5 PRO 4650U, Renoir, AX200, RTL8111.
  # Filesystems and LUKS are declared by the reviewed Disko configuration.
  boot.initrd.availableKernelModules = [
    "nvme" "xhci_pci" "usb_storage" "sd_mod" "rtsx_pci_sdmmc" "r8169"
  ];
  boot.kernelModules = [ "kvm-amd" ];
  # Work around intermittent stuck keys reported on the ThinkPad L14 Gen 1.
  # https://bugs.debian.org/1115112
  boot.kernelParams = [ "i8042.nomux=1" ];
  hardware.cpu.amd.updateMicrocode = true;
}
