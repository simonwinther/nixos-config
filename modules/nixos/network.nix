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
      DNSStubListenerExtra = lib.optional (profile != "live") "172.17.0.1";
    };
  };
  services.tailscale = {
    enable = profile != "live";
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
}
