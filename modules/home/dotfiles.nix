{ ... }:
let
  root = ../../dotfiles;
  deployment = import ../../lib/dotfiles.nix { inherit root; };
in
{
  home.file = builtins.listToAttrs (
    map (item: {
      name = item.target;
      value.source = "${root}/${item.source}";
    }) deployment.files
  );
}
