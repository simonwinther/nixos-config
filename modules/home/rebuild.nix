{
  config,
  lib,
  pkgs,
  host,
  profile,
  ...
}:
let
  cfg = config.desktop.rebuild;
  target = if profile == "live" then "${host}-live" else host;
  action = if profile == "live" then "test" else "switch";
  rebuild = pkgs.writeShellApplication {
    name = "nixos-rebuild-desktop";
    runtimeInputs = [
      pkgs.nixos-rebuild
      pkgs.nix
      pkgs.git
      pkgs.coreutils
      pkgs.util-linux
    ];
    text = ''
      umask 077
      repo=${lib.escapeShellArg cfg.repository}
      runtime_dir="''${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
      state_dir="''${XDG_STATE_HOME:-$HOME/.local/state}/nixos-rebuild"
      mkdir -p "$state_dir"
      exec 9>"$runtime_dir/nixos-rebuild-desktop.lock"
      if ! flock --nonblock 9; then
        echo "A NixOS rebuild is already running."
        if [[ -t 0 ]]; then read -r -p "Press Enter to close." _ || true; fi
        exit 1
      fi
      log="$state_dir/$(date -u +%Y%m%dT%H%M%SZ)-$$.log"
      printf '%s\n' "$log" > "$state_dir/last-log"
      finish() {
        status=$?
        trap - EXIT
        printf '%s\n' "$status" > "$state_dir/last-exit-code"
        if (( status == 0 )); then
          echo "NixOS ${target} applied successfully (${action})."
        else
          echo "Rebuild failed (exit $status). Details: $log"
        fi
        if [[ -t 0 ]]; then read -r -p "Press Enter to close." _ || true; fi
        exit "$status"
      }
      trap finish EXIT
      if [[ ! -f "$repo/flake.nix" || ! -f "$repo/flake.lock" ]]; then
        echo "Missing NixOS configuration or lock file: $repo" >&2
        exit 1
      fi
      cd "$repo"
      echo "Rebuilding $repo#${target} (${action}). Log: $log"
      ${lib.optionalString (
        profile == "live"
      ) ''echo "Live USB: changes apply to this session; persistent installation is separate."''}
      nixos-rebuild ${action} --flake "$repo#${target}" --sudo --max-jobs 1 --cores 4 2>&1 | tee "$log"
    '';
  };
in
{
  options.desktop.rebuild = {
    key = lib.mkOption {
      type = lib.types.str;
      default = "SUPER + CTRL + ALT + N";
      description = "Open a terminal and rebuild this machine's NixOS configuration.";
    };
    repository = lib.mkOption {
      type = lib.types.str;
      default = "${config.home.homeDirectory}/nixos-config";
      description = "Mutable, locked NixOS checkout to build.";
    };
    target = lib.mkOption {
      type = lib.types.str;
      readOnly = true;
      default = target;
    };
    action = lib.mkOption {
      type = lib.types.str;
      readOnly = true;
      default = action;
    };
  };
  config = {
    home.packages = [ rebuild ];
    xdg.configFile."desktop/rebuild-bindings.lua".text = ''
      hl.bind(${builtins.toJSON cfg.key}, hl.dsp.exec_cmd(${builtins.toJSON "${pkgs.ghostty}/bin/ghostty -e ${rebuild}/bin/nixos-rebuild-desktop"}), { description = "Rebuild NixOS (${target})" })
    '';
  };
}
