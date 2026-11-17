# Laptop keyboard recovery

## Recognize the recurring problem

Host: `lambda`, ThinkPad L14 Gen 1 AMD, type `20U6`, running NixOS.

Reports such as "my keyboard stopped working" or "my keybindings are fucked
again" may refer to this incident. The built-in keyboard becomes unresponsive
across applications while the desktop remains visible and SSH from a phone
continues to work. A key may appear permanently held. That phone SSH path is
Tailscale SSH, declared on `lambda` by `services.tailscale.extraSetFlags = [
"--ssh" ]` in `hosts/lambda/default.nix` and re-applied by
`tailscaled-set.service` at boot.

Confirm the actual symptom first. If ordinary typing still works and only a
shortcut fails, inspect the desktop bindings and input mode instead. A held key
or regular key repeat by itself is normal during gaming and does not justify
resetting the keyboard.

## Recover over SSH

When asked to fix this recurring lockup on the installed NixOS laptop:

1. Confirm the host and that the built-in keyboard is affected across
   applications. Keep the current desktop session running.
2. Inspect the kernel input-device list and Hyprland's device list. On this
   laptop, `/sys/bus/serio/devices/serio0/description` is `i8042 KBD port`, its
   driver is `atkbd`, and its input device is `AT Translated Set 2 keyboard`.
   Verify this mapping before using the command below. Event device numbers
   change after recovery; do not assume the keyboard remains `event0`.
3. Read the kernel journal and the keyboard's `err_count` attribute if useful.
   The original incident had receive errors, but a nonzero error count is not
   required to recognize the same symptoms. Avoid capturing typed text.
4. With sudo authentication, rescan only the confirmed built-in keyboard port:

   ```sh
   sudo sh -c 'printf rescan > /sys/bus/serio/devices/serio0/drvctl'
   ```

5. Confirm that the kernel registers the keyboard again and Hyprland detects
   it. Ask Simon to try ordinary typing and his shortcuts on the laptop.
   Recovery is complete when physical input works again.

This is the command that successfully restored the keyboard on 2026-11-12.
It disconnects and reattaches that keyboard's driver. No system rebuild,
desktop restart, logout, or reboot is needed for this recovery. Do not replace
the targeted rescan with a broad input-driver unload or repeated automatic
resets. If authentication is unavailable, obtain it through the current session;
credentials are not part of this runbook.

## Evidence from 2026-11-12

- Kernel: `6.18.56`; BIOS: `R19ET36W` / `1.20`.
- Linux and Hyprland both still detected the physical keyboard. The desktop
  believed W was held down, without stuck modifier keys.
- Keyboard IRQ 1 continued at about 30 signals per second: 916 signals in
  30 seconds. The keyboard driver had recorded seven receive errors.
- A software-generated test key reached a focused keyboard test window.
  Reloading Hyprland's configuration did not restore the physical keyboard.
- Rescanning `serio0` immediately restored physical typing. The continuous
  signal stream stopped, and the recreated keyboard's error count was zero.
- Simon confirmed that the keyboard worked after the rescan.

This localizes the fault to the physical keyboard/controller/driver path.
The precise trigger and underlying firmware or driver defect remain unknown;
the earlier receive errors alone do not establish the cause.

## Preventive workaround and verification

[The laptop hardware configuration](../hosts/lambda/hardware-configuration.nix)
declares `boot.kernelParams = [ "i8042.nomux=1" ];`. This skips probing for an
active PS/2 multiplexing controller. A
[ThinkPad L14 Gen 1 report](https://bugs.debian.org/1115112) describes similar
stuck keys and reports improvement with this setting; that report concerns
the Intel variant, so prevention on this AMD laptop remains to be verified.
See the [kernel parameter documentation](https://docs.kernel.org/admin-guide/kernel-parameters.html)
for the option's meaning.

On 2026-11-12, the same option was also added to the default boot entry,
`/boot/loader/entries/nixos-generation-34.conf`, so the next boot can use it
without activating unrelated pending source changes. The original entry is
backed up at
`/var/lib/keyboard-recovery/nixos-generation-34.conf.20261112-223537.bak`.
Other boot entries were unchanged. Nix evaluation confirmed the declared option.

The setting only takes effect after booting with it. Check `/proc/cmdline` for
`i8042.nomux=1` rather than assuming a reboot has happened. Later rebuilds should
retain the setting through the hardware configuration; no manual boot-entry
patch should normally be needed again.

If the lockup recurs, use the targeted recovery above, record whether this
parameter was active, and note any relation to wake from sleep, docking, gaming,
or keyboard LED changes. Retain the relevant kernel messages and investigate
the controller/firmware further. Do not treat the workaround as a proven cure
or repeatedly rewrite desktop bindings for a failure of all physical typing.
