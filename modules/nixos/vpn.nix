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
    (
      let
        # Set this to true before enabling the kill switch or auto-connect: those
        # settings only apply while nordvpnd runs, and nordvpnd now starts only when
        # a client (CLI, GUI or tray) first connects to its socket.
        nordvpnStartsAtBoot = false;
        runtimeDirectory = "/run/nordvpn";
        # nordvpnd writes this on every start so the tray can follow it on demand.
        # It must never be deleted while a session runs: deletion also triggers.
        daemonStartedMarker = "${runtimeDirectory}/daemon-started";
      in
      {
        config = lib.mkIf config.services.nordvpn.enable {
          # nordvpnd.socket (upstream) still listens at boot and activates the daemon.
          systemd.services.nordvpnd.wantedBy = lib.mkIf (!nordvpnStartsAtBoot) (lib.mkForce [ ]);
          # The socket unit creates its parent directory as root:root 0750, which
          # denies the nordvpn group until the daemon has run once and blocks the
          # first connection that should activate it.
          systemd.tmpfiles.settings.nordvpn.${runtimeDirectory}.d = {
            user = config.services.nordvpn.user;
            group = config.services.nordvpn.group;
            mode = "0750";
          };
          systemd.services.nordvpnd.serviceConfig = {
            # Removing the runtime directory on stop or restart would delete the
            # socket inode that nordvpnd.socket keeps listening on.
            RuntimeDirectoryPreserve = "yes";
            # "-": a failed marker write must not fail the VPN daemon.
            ExecStartPost = "-${pkgs.coreutils}/bin/touch ${daemonStartedMarker}";
          };

          # norduserd (tray, notifications) queries nordvpnd as soon as it starts,
          # so starting it at login would activate the daemon. Start it with the
          # daemon instead, and at login only if the daemon is already running.
          systemd.user.paths.norduserd = {
            description = "Start the NordVPN tray when nordvpnd starts";
            wantedBy = [ "default.target" ];
            pathConfig.PathChanged = daemonStartedMarker;
          };
          systemd.user.services.norduserd = {
            serviceConfig.ExecCondition = toString (
              pkgs.writeShellScript "nordvpnd-is-running" ''
                case "$(${pkgs.systemd}/bin/systemctl show --property=ActiveState --value nordvpnd.service)" in
                  active | activating | reloading) exit 0 ;;
                  *) exit 1 ;;
                esac
              ''
            );
          };
        };
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
      pkgs.dbus
    ];
    script = ''
      link=sdwan0
      safety_check_interval=60

      keep_dns_local() {
        local index state
        [ -e "/sys/class/net/$link" ] && read -r index <"/sys/class/net/$link/ifindex" || return 0
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
      }

      # Twingate configures DNS through resolved's D-Bus methods, and resolved
      # emits no change signal for per-link DNS. Watching those calls replaces
      # a busctl process every 2 s with work only when a link's DNS changes.
      manager="type='method_call',interface='org.freedesktop.resolve1.Manager'"
      exec {resolver_calls}< <(exec dbus-monitor --system --profile \
        "type='method_call',interface='org.freedesktop.resolve1.Link'" \
        "$manager,member='SetLinkDNS'" \
        "$manager,member='SetLinkDNSEx'" \
        "$manager,member='SetLinkDefaultRoute'" \
        "$manager,member='SetLinkDomains'" \
        "$manager,member='RevertLink'")

      keep_dns_local
      while true; do
        status=0
        read -r -t "$safety_check_interval" -u "$resolver_calls" _ || status=$?
        # Status 1 is end of file: the monitor died, so let systemd restart us.
        [ "$status" -ne 1 ] || exit 1
        if [ "$status" -eq 0 ]; then
          # Give resolved time to apply the call and fold a burst into one check.
          while read -r -t 0.5 -u "$resolver_calls" _; do :; done
        fi
        keep_dns_local
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
