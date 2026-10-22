{
  config,
  lib,
  pkgs,
  inputs,
  packages,
  unstable,
  profile,
  ...
}:
{
  imports = [
    (
      {
        config,
        lib,
        pkgs,
        ...
      }:
      let
        upstream = import (inputs.unstable + "/nixos/modules/services/networking/nordvpn.nix") {
          inherit config lib pkgs;
        };
      in
      upstream
      // {
        # The 26.05 manual redirect index predates this newer module chapter.
        meta = builtins.removeAttrs (upstream.meta or { }) [ "doc" ];
      }
    )
  ];
  services.nordvpn = {
    enable =
      !(builtins.elem profile [
        "live"
        "recovery"
      ]);
    package = unstable.nordvpn;
  };
  services.twingate = {
    enable =
      !(builtins.elem profile [
        "live"
        "recovery"
      ]);
    package = unstable.twingate;
  };
  systemd.services.twingate.wantedBy = lib.mkIf config.services.twingate.enable (lib.mkForce [ ]);
  environment.systemPackages = [
    packages.hendrix-vpn
    pkgs.openconnect
  ];
  systemd.services.ku-vpn = {
    # A rebuild must not replay an expired authenticator code or drop an active tunnel.
    restartIfChanged = false;
    description = "KU split-tunnel VPN for Hendrix";
    wants = [ "network-online.target" ];
    after = [ "network-online.target" ];
    serviceConfig = {
      Type = "simple";
      ExecStart = "${packages.hendrix-vpn}/bin/ku-vpn";
      StandardInput = "file:/home/simon/.config/hendrix/password";
      KillSignal = "SIGINT";
      TimeoutStopSec = 15;
      Restart = "no";
    };
  };
  security.sudo.extraRules = [
    {
      users = [ "simon" ];
      commands = [
        {
          command = "${pkgs.systemd}/bin/systemctl start ku-vpn.service";
          options = [ "NOPASSWD" ];
        }
      ];
    }
  ];
}
