{
  lib,
  pkgs,
  profile,
  ...
}:
{
  networking = {
    useDHCP = false;
    useNetworkd = true;
    networkmanager.enable = lib.mkForce false;
    wireless.enable = lib.mkForce false;
    wireless.iwd = {
      enable = true;
      settings.General.EnableNetworkConfiguration = false;
    };
    firewall = {
      enable = true;
      checkReversePath = "loose";
      allowedTCPPorts = [ 53317 ];
      allowedUDPPorts = [ 53317 ];
      interfaces.tailscale0.allowedTCPPorts = [
        22
        8787
      ];
      interfaces.docker0.allowedUDPPorts = [ 53 ];
      interfaces.docker0.allowedTCPPorts = [ 53 ];
    };
  };
  systemd.network = {
    enable = true;
    wait-online.anyInterface = true;
    networks."20-wired" = {
      matchConfig.Name = "en* eth*";
      networkConfig = {
        DHCP = "yes";
        MulticastDNS = true;
      };
      dhcpV4Config.RouteMetric = 100;
      ipv6AcceptRAConfig.RouteMetric = 100;
      linkConfig.RequiredForOnline = "routable";
    };
    networks."30-wireless" = {
      matchConfig.Name = "wl*";
      networkConfig = {
        DHCP = "yes";
        MulticastDNS = true;
        # iwd drops the carrier for about half a second on every roam between
        # access points; keep the lease and routes instead of tearing them down.
        # Joining a different SSID still reconfigures the link.
        IgnoreCarrierLoss = "3s";
      };
      dhcpV4Config.RouteMetric = 600;
      ipv6AcceptRAConfig.RouteMetric = 600;
      linkConfig.RequiredForOnline = "routable";
    };
  };
  services.resolved = {
    enable = true;
    settings.Resolve = {
      MulticastDNS = false;
      # LLMNR multicasts single-label lookups to whatever LAN the laptop joins,
      # leaking the names it looks up. Avahi resolves .local and unicast DNS
      # the rest, so disabling it loses nothing.
      LLMNR = false;
      DNSStubListenerExtra = lib.optional (profile != "live") "172.17.0.1";
    };
  };
  services.tailscale = {
    enable = true;
    # Without Wi-Fi, Docker bridges and the Twingate/KU tunnels made tailscaled
    # assume a network and retry every few seconds, writing ~200 lines a minute.
    package = pkgs.tailscale.overrideAttrs (old: {
      patches = (old.patches or [ ]) ++ [ ./patches/tailscale-ignore-overlay-interfaces.patch ];
    });
    openFirewall = true;
    extraUpFlags = [ "--accept-dns=false" ];
    extraSetFlags = [
      "--operator=simon"
      "--accept-dns=false"
    ];
  };
  virtualisation.docker = lib.mkIf (profile != "live") {
    enable = true;
    daemon.settings = {
      log-driver = "json-file";
      log-opts = {
        max-size = "10m";
        max-file = "5";
      };
      dns = [ "172.17.0.1" ];
      bip = "172.17.0.1/16";
    };
  };
  # Docker still waits for network-online, but multi-user.target (and through
  # graphical.target the uwsm session) no longer waits for Docker: a target only
  # orders itself after wanted units with default dependencies. The defaults
  # that matter are restored so Docker still stops cleanly before shutdown.
  systemd.services.docker = lib.mkIf (profile != "live") {
    unitConfig.DefaultDependencies = false;
    requires = [ "sysinit.target" ];
    after = [
      "sysinit.target"
      "basic.target"
    ];
    conflicts = [ "shutdown.target" ];
    before = [ "shutdown.target" ];
  };
}
