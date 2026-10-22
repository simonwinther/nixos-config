{ ... }:
{
  # Authentication material remains mutable private state outside the Nix store.
  programs.ssh = {
    enable = true;
    enableDefaultConfig = false;
    includes = [ "~/.ssh/config.d/*.conf" ];
    settings."hendrix hendrixgate" = {
      HostName = "hendrixgate.unicph.domain";
      User = "zlp616";
      IdentityFile = "~/.ssh/hendrix_pc";
      IdentitiesOnly = true;
      StrictHostKeyChecking = "yes";
      CheckHostIP = true;
      UserKnownHostsFile = "~/.config/hendrix/known_hosts";
      ControlMaster = "auto";
      ControlPath = "~/.ssh/control-%C";
      ControlPersist = "10m";
      ServerAliveInterval = 30;
      ServerAliveCountMax = 3;
      ConnectTimeout = 12;
    };
  };
}
