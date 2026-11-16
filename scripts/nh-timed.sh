#!/usr/bin/env bash
# Records `nh os` rebuilds in the times.csv that nixos-rebuild-desktop keeps, so
# build-times charts every rebuild. The Home Manager wrapper supplies these
# values; tests use temporary paths.
set -euo pipefail
real_nh=${real_nh:?Missing nh executable}
current_system=${current_system:?Missing current system link}
system_profile=${system_profile:?Missing system profile link}

args=("$@")
command_index=0
while (( command_index < ${#args[@]} )) && [[ ${args[command_index]} == -* ]]; do
  command_index=$((command_index + 1))
done
verb_index=$((command_index + 1))
if [[ ${args[command_index]:-} != os || ! ${args[verb_index]:-} =~ ^(build|switch|boot|test)$ ]]; then
  exec "$real_nh" "$@"
fi
verb=${args[verb_index]}

state_dir="${XDG_STATE_HOME:-$HOME/.local/state}/nixos-rebuild"
mkdir -p "$state_dir"
times="$state_dir/times.csv"

# The build ends when Nix creates the out-link, so its mtime splits a switch
# into build and activation time. A link the caller chose is reused.
link=
for ((i = verb_index + 1; i < ${#args[@]}; i++)); do
  case ${args[i]} in
    --) break ;;
    -o | --out-link) link=${args[i + 1]:-} ;;
    --out-link=*) link=${args[i]#--out-link=} ;;
    -o?*) link=${args[i]#-o} ;;
  esac
done
if [[ -z $link ]]; then
  link="$state_dir/nh-result"
  args=("${args[@]:0:verb_index+1}" --out-link "$link" "${args[@]:verb_index+1}")
fi

modified_since() {
  local modified
  modified=$(stat -c %Y -- "$2" 2>/dev/null) || return 1
  (( modified >= $1 ))
}

record() {
  printf '%s,%s,%s,%s,nh\n' "$(date -u -d "@$1" +%Y-%m-%dT%H:%M:%SZ)" "$2" "$3" "$4" >> "$times"
}

start=$(date +%s)
status=0
"$real_nh" "${args[@]}" || status=$?
end=$(date +%s)
built=$(stat -c %Y -- "$link" 2>/dev/null) || built=0

if (( built >= start )); then
  record "$start" build $((built - start)) 0
  # Activation relinks the current system and boot relinks the profile; a
  # successful run that changed neither stopped early, such as --dry.
  case $verb in
    switch | test) operation=activate marker=$current_system ;;
    boot) operation=boot marker=$system_profile ;;
    *) operation= ;;
  esac
  if [[ -n $operation ]] && { (( status != 0 )) || modified_since "$built" "$marker"; }; then
    record "$built" "$operation" $((end - built)) "$status"
  fi
elif (( status != 0 )); then
  record "$start" build $((end - start)) "$status"
fi
exit "$status"
