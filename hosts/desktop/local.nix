{ lib, ... }:
{
  # Reviewed on desktop-live, 2026-10-22. Preserve the existing encrypted
  # Arch installation and create separate @nixos-* subvolumes for NixOS.
  workstation = {
    hardwareReviewed = true;
    # Restic snapshot 0dcd2db6: complete read check plus 420-file sample restore.
    # Recovery material was independently decrypted using the reference laptop.
    backupsVerified = true;
    targetDisk = "/dev/disk/by-id/nvme-Samsung_SSD_960_EVO_500GB_S3X4NF0JB46224E";
    gpu = "nvidia";
    nvidiaOpen = false;
    storage.existingBtrfs = {
      luksUuid = "be24b376-7d0c-4e09-8239-6c8217f8df22";
      filesystemUuid = "2f607563-4f24-4b89-85b5-96c685ac8c38";
      espUuid = "9C33-2477";
      subvolumePrefix = "@nixos";
    };
  };

  # The installer was booted in BIOS mode. Install the UEFI fallback loader
  # without editing NVRAM; select the Samsung NVMe's UEFI entry in firmware.
  boot.loader.efi.canTouchEfiVariables = lib.mkForce false;
  boot.loader.systemd-boot = {
    configurationLimit = lib.mkForce 3;
    extraEntries."previous-arch.conf" = ''
      title Previous Arch system (preserved)
      sort-key z-previous-system
      efi /EFI/limine/limine_x64.efi
    '';
  };
}
