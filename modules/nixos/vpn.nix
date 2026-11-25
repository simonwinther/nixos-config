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
    path = [ pkgs.systemd ];
    script = ''
      link=sdwan0
      # A read timeout on a pipe this shell holds open for writing waits without
      # forking sleep(1) every iteration.
      exec {idle_fd}<> <(:)
      while true; do
        if [ -e "/sys/class/net/$link" ] && read -r index <"/sys/class/net/$link/ifindex"; then
          # One D-Bus read replaces `resolvectl status` plus grep; a failed or
          # unexpected reply falls through to the idempotent reset.
          # resolved escapes the leading ifindex digit: 9 is link/_39, 12 is link/_312.
          state=$(busctl get-property org.freedesktop.resolve1 \
            "/org/freedesktop/resolve1/link/_3$index" org.freedesktop.resolve1.Link \
            DefaultRoute DNS 2>/dev/null) || state=
          if [ "$state" != $'b false\na(iay) 0' ]; then
            resolvectl default-route "$link" false || true
            resolvectl dns "$link" "" || true
          fi
        fi
        read -rt 2 -u "$idle_fd" || true
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
