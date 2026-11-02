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
  systemd.services.twingate-dns-guard = lib.mkIf config.services.twingate.enable {
    # Twingate routes all DNS (~.) to sdwan0, which breaks name resolution
    # until sign-in finishes. Resources are reached by IP, so keep DNS local.
    description = "Keep Twingate from taking over system DNS";
    wantedBy = [ "twingate.service" ];
    partOf = [ "twingate.service" ];
    after = [ "twingate.service" ];
    path = [
      pkgs.systemd
      pkgs.iproute2
      pkgs.gnugrep
    ];
    script = ''
      while true; do
        if ip link show sdwan0 >/dev/null 2>&1; then
          status=$(resolvectl status sdwan0)
          if grep -qE '\+DefaultRoute|DNS Servers:' <<<"$status"; then
            resolvectl default-route sdwan0 false
            resolvectl dns sdwan0 ""
          fi
        fi
        sleep 2
      done
    '';
    serviceConfig.Restart = "on-failure";
  };
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
