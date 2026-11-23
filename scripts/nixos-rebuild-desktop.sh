#!/usr/bin/env bash
# The Home Manager wrapper supplies these values; tests use temporary repositories.
set -euo pipefail
repo=${repo:?Missing repository}
target=${target:?Missing NixOS target}
activation_action=${activation_action:?Missing activation action}

usage() {
  cat <<'HELP'
Usage: nixos-rebuild-desktop [build|sync|activate|update|times]
  build     Build the clean, pinned checkout without activation (default).
  sync      Initialize/check out recorded submodule revisions; no pull or build.
  activate  Apply the last successful build, only if its source still matches.
  update    Fast-forward main, sync pinned sources, build and switch this host.
  times     Chart successful build durations (table when piped).
HELP
}

plot_times() {
  if ! grep -Eq ',build,[0-9]+,0(,|$)' "$times" 2>/dev/null; then
    echo "No successful timed builds yet: $times" >&2
    return 1
  fi
  # Interactive terminals get the chart; pipes and logs get the plain table.
  if [[ -t 0 && -t 1 ]] && command -v build-times >/dev/null; then
    build-times "$times"
    return
  fi
  local color=0
  if [[ -t 1 ]]; then color=1; fi
  gawk -F, -v cols="$(tput cols 2>/dev/null || echo 100)" -v color="$color" -v data="$times" '
    function span(s) {
      if (s < 60) return sprintf("%ds", s)
      if (s < 3600) return sprintf("%dm %02ds", s / 60, s % 60)
      return sprintf("%dh %02dm", s / 3600, (s % 3600) / 60)
    }
    function paint(code, text) { return color ? "\033[" code "m" text "\033[0m" : text }
    # Eighth-block characters give the bars sub-cell resolution.
    function bar(value, width,   cells, full, part, out, i) {
      cells = value / longest * width
      full = int(cells)
      part = int((cells - full) * 8)
      for (i = 0; i < full; i++) out = out "█"
      if (part > 0) out = out substr("▏▎▍▌▋▊▉", part, 1)
      return out
    }
    $2 == "build" {
      pending = ($4 == 0) ? ++n : 0
      if (pending) {
        gsub(/[-T:Z]/, " ", $1)
        when[n] = strftime("%a %d %b  %H:%M", mktime($1, 1))
        build[n] = $3
        activate[n] = ""
        if ($3 > longest) longest = $3
      }
      next
    }
    $2 == "activate" && $4 == 0 && pending && activate[pending] == "" { activate[pending] = $3 }
    END {
      width = cols - 46
      if (width > 60) width = 60
      if (width < 10) width = 10
      print paint("1", "NixOS build times") paint("2", "  ·  " n " successful builds, oldest first")
      print ""
      printf "%s%s%s\n", paint("2", sprintf("%-19s", "")), paint("2", sprintf("%-" width "s", "")), paint("2", sprintf("  %8s  %8s", "build", "activate"))
      for (i = 1; i <= n; i++) {
        sorted[i] = build[i]
        line = sprintf("%-" width "s", bar(build[i], width))
        printf "%s %s  %8s  %8s\n", paint("2", sprintf("%-18s", when[i])), paint("32", line), span(build[i]), activate[i] == "" ? paint("2", "—") : span(activate[i])
      }
      asort(sorted)
      median = (n % 2) ? sorted[(n + 1) / 2] : (sorted[n / 2] + sorted[n / 2 + 1]) / 2
      print ""
      print paint("2", "median ") span(median) paint("2", " · fastest ") span(sorted[1]) paint("2", " · slowest ") span(sorted[n]) paint("2", " · last ") span(build[n])
      print paint("2", "Data: " data)
    }
  ' "$times"
}

operation=${1:-build}
case "$operation" in
  -h|--help) usage; exit 0 ;;
  build|sync|activate|update|times) ;;
  *) usage >&2; exit 2 ;;
esac
if (( $# > 1 )); then usage >&2; exit 2; fi

umask 077
runtime_dir="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
state_dir="${XDG_STATE_HOME:-$HOME/.local/state}/nixos-rebuild"
mkdir -p "$state_dir"
times="$state_dir/times.csv"
if [[ "$operation" == times ]]; then
  plot_times
  exit
fi
exec 9>"$runtime_dir/nixos-rebuild-desktop.lock"
if ! flock --nonblock 9; then
  echo "Another NixOS source/build/activation action is already running." >&2
  if [[ -t 0 ]]; then read -r -p "Press Enter to close." _ || true; fi
  exit 1
fi
started=$(date -u +%Y-%m-%dT%H:%M:%SZ)
SECONDS=0
log="$state_dir/${started//[-:]/}-$$.log"
printf '%s\n' "$log" > "$state_dir/last-log"
finish() {
  status=$?
  trap - EXIT
  printf '%s\n' "$status" > "$state_dir/last-exit-code"
  printf '%s,%s,%s,%s\n' "$started" "$operation" "$SECONDS" "$status" >> "$times"
  if (( status == 0 )); then
    echo "NixOS $target: $operation completed. Log: $log" | tee -a "$log"
  else
    echo "NixOS $target: $operation failed (exit $status). Details: $log" | tee -a "$log"
  fi
  # The action is recorded; free the lock while this window waits for Enter.
  exec 9>&-
  if [[ -t 0 ]]; then read -r -p "Press Enter to close." _ || true; fi
  exit "$status"
}
trap finish EXIT

source_revision() {
  printf 'Repository: %s\nTarget: %s\nActivation: %s\n' "$repo" "$target" "$activation_action"
  printf 'Revision: %s\n' "$(git rev-parse --verify HEAD)"
  printf 'Lock SHA256: %s\n' "$(sha256sum flake.lock)"
  echo 'Submodules (space = pinned, + = different, - = missing, U = conflict):'
  git submodule status --recursive
}

check_clean() {
  local changes
  # A clean submodule at a different commit is allowed for sync. Staged gitlink
  # changes and all tracked/untracked file edits are refused, including nested ones.
  changes=$(git status --porcelain=v1 --untracked-files=all --ignore-submodules=all)
  if [[ -n "$changes" ]]; then
    printf 'Dirty repository; commit or stash changes first:\n%s\n' "$changes" >&2
    return 1
  fi
  if ! git diff --cached --quiet --ignore-submodules=none; then
    echo 'Staged changes (including submodule pointers); commit or stash them first.' >&2
    git diff --cached --name-status --ignore-submodules=none >&2
    return 1
  fi
  # The expressions below are evaluated by each submodule's shell.
  # shellcheck disable=SC2016
  git submodule foreach --quiet --recursive '
    changes=$(git status --porcelain=v1 --untracked-files=all --ignore-submodules=all) || exit
    if test -n "$changes"; then
      printf "Dirty submodule %s; commit or stash changes first:\n%s\n" "$displaypath" "$changes" >&2
      exit 1
    fi
    if ! git diff --cached --quiet --ignore-submodules=none; then
      printf "Staged changes in submodule %s; commit or stash them first.\n" "$displaypath" >&2
      exit 1
    fi
  '
}

check_pinned() {
  local revisions line
  revisions=$(git submodule status --recursive)
  while IFS= read -r line; do
    if [[ -n "$line" && ${line:0:1} != ' ' ]]; then
      echo 'Submodules are missing, conflicted or at different revisions. Run nixos-rebuild-desktop sync separately.' >&2
      return 1
    fi
  done <<< "$revisions"
}

build_record() {
  source_revision
  printf 'System: %s\n' "$closure"
}

main() {
  local revision result record closure
  result="$state_dir/$target-result"
  record="$state_dir/$target-build"
  echo "NixOS $target: $operation. Log: $log"
  if [[ "$operation" == build || "$operation" == update ]]; then
    # Any failed build attempt must make the previous build ineligible.
    rm -f -- "$record"
  fi
  if [[ ! -f "$repo/flake.nix" || ! -f "$repo/flake.lock" ]]; then
    echo "Missing NixOS configuration or lock file: $repo" >&2
    return 1
  fi
  cd -P -- "$repo"
  repo=$(pwd -P)
  if [[ $(git rev-parse --show-toplevel) != "$repo" ]]; then
    echo 'The configured repository must be the root of a Git checkout.' >&2
    return 1
  fi
  source_revision
  check_clean

  if [[ "$operation" == update ]]; then
    if [[ "$activation_action" != switch || "$(git branch --show-current)" != main ]]; then
      echo 'Update requires an installed host and a checkout on main.' >&2
      return 1
    fi
    git fetch --no-recurse-submodules origin refs/heads/main
    if ! git merge-base --is-ancestor HEAD FETCH_HEAD; then
      echo 'Local main has unpublished commits. Publish or reconcile them before updating.' >&2
      return 1
    fi
    git -c submodule.recurse=false merge --ff-only FETCH_HEAD
  fi

  if [[ "$operation" == sync || "$operation" == update ]]; then
    # Explicit checkout mode overrides any per-submodule merge/rebase setting.
    git submodule update --init --recursive --checkout
    check_clean
    check_pinned
    echo 'Synchronized source revisions:'
    source_revision
    if [[ "$operation" == sync ]]; then return; fi
  fi

  check_pinned
  revision=$(source_revision)
  if [[ "$operation" == build || "$operation" == update ]]; then
    nix build "$repo#nixosConfigurations.$target.config.system.build.toplevel" \
      --no-update-lock-file --no-write-lock-file \
      --out-link "$result" --max-jobs 1 --cores 4
    check_clean
    check_pinned
    if [[ $(source_revision) != "$revision" ]]; then
      echo 'Source revisions changed during the build; build again before activation.' >&2
      return 1
    fi
    closure=$(readlink -e -- "$result")
    build_record > "$record"
    echo "Built system: $closure"
    if [[ "$operation" == build ]]; then
      echo 'To apply this build separately: nixos-rebuild-desktop activate'
      return
    fi
  fi
  if [[ ! -f "$record" || ! -L "$result" ]]; then
    echo 'No successful recorded build. Run nixos-rebuild-desktop build first.' >&2
    return 1
  fi
  closure=$(readlink -e -- "$result")
  if [[ $(cat "$record") != "$(build_record)" ]]; then
    echo 'Source revisions or build output differ from the recorded build. Build again before activation.' >&2
    return 1
  fi
  echo "Activating recorded system: $closure ($activation_action)"
  if [[ "$activation_action" == test ]]; then
    echo 'Live session only; persistent installation is separate.'
  fi
  # A prebuilt closure needs no re-exec, which would require <nixpkgs> on NIX_PATH.
  nixos-rebuild "$activation_action" --store-path "$closure" --sudo --no-reexec
}

main 2>&1 | tee "$log"
