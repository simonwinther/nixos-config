{
  lib,
  runCommand,
  fetchFromGitHub,
  makeWrapper,
  bash,
  coreutils,
  gawk,
  gnugrep,
  gnused,
  procps,
  tmux,
  gnutar,
  gzip,
}:
let
  specs = builtins.fromJSON (builtins.readFile ./plugins.json);
  order = [
    "vim-tmux-navigator"
    "tmux-resurrect"
    "tmux-continuum"
  ];
  runtime = lib.makeBinPath [
    bash
    coreutils
    gawk
    gnugrep
    gnused
    procps
    tmux
    gnutar
    gzip
  ];
in
runCommand "locked-tmux-plugins" { nativeBuildInputs = [ makeWrapper ]; } ''
  mkdir -p "$out/bin" "$out/lib/tmux-plugins"
  touch "$out/init.conf"
  ${lib.concatMapStringsSep "\n" (
    name:
    let
      spec = specs.${name};
      source = fetchFromGitHub {
        inherit (spec)
          owner
          repo
          rev
          hash
          ;
      };
    in
    ''
      cp -R ${source} "$out/lib/tmux-plugins/${name}"
      chmod -R u+w "$out/lib/tmux-plugins/${name}"
      patchShebangs "$out/lib/tmux-plugins/${name}"
      makeWrapper ${bash}/bin/bash "$out/bin/init-${name}" \
        --add-flags "$out/lib/tmux-plugins/${name}/${spec.entry}" \
        --prefix PATH : ${runtime}
      printf 'run-shell "%s"\n' "$out/bin/init-${name}" >> "$out/init.conf"
    ''
  ) order}
''
