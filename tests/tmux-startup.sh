#!/usr/bin/env bash
set -euo pipefail

unset TMUX TMUX_PANE
socket_dir=$(mktemp -d /tmp/tmux-migration.XXXXXX)
cleanup() {
  tmux -S "$socket_dir/socket" kill-server 2>/dev/null || true
  rm -rf -- "$socket_dir"
}
trap cleanup EXIT
trap 'exit 143' TERM
export TMUX_TMPDIR="$socket_dir"

private_tmux() {
  tmux -S "$socket_dir/socket" "$@"
}

private_tmux -f "$TMUX_MIGRATION_CONFIG" new-session -d -s migration 'sleep 60'
# Plugin initialization is queued by tmux; wait for all three to finish.
for _ in {1..100}; do
  navigator=$(private_tmux list-keys -T root | grep -E '^bind-key[[:space:]]+-T root[[:space:]]+C-h[[:space:]]' || true)
  resurrect=$(private_tmux show-options -gqv @resurrect-save-script-path)
  continuum=$(private_tmux show-options -gqv status-right)
  if [[ "$navigator" == *'select-pane -L'* && "$resurrect" == */scripts/save.sh && "$continuum" == *continuum_save.sh* ]]; then
    break
  fi
  sleep 0.1
done
[[ "$navigator" == *'select-pane -L'* ]]
[[ "$resurrect" == */scripts/save.sh ]]
[[ "$continuum" == *continuum_save.sh* ]]
[[ $(private_tmux show-options -gqv prefix) == C-Space ]]
[[ $(private_tmux show-options -sqv extended-keys) == on ]]

private_tmux set-option -g @resurrect-dir "$HOME/restore-test"
private_tmux run-shell "$resurrect quiet"
test -s "$HOME/restore-test/last"
grep -q 'migration' "$HOME/restore-test/last"
test -s "$HOME/restore-test/pane_contents.tar.gz"
printf 'tmux startup, navigation, session save, and pane capture passed\n'
