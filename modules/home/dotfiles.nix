{ lib, ... }:
let
  root = ../../dotfiles;
  storeRoot = "${root}";
  ignored =
    rel: name:
    name == ".stow-local-ignore"
    || name == "__pycache__"
    || lib.hasSuffix ".pyc" name
    || name == "AGENTS.md"
    || (
      rel == ""
      && (builtins.elem name [
        "README.md"
        "tests"
      ])
    );
  leaves =
    package: dir: rel:
    lib.concatMap (
      name:
      let
        child = if rel == "" then name else "${rel}/${name}";
        kind = (builtins.readDir dir).${name};
      in
      if ignored rel name then
        [ ]
      else if kind == "directory" then
        leaves package (dir + "/${name}") child
      else
        [
          {
            target = child;
            source = "${storeRoot}/${package}/${child}";
          }
        ]
    ) (builtins.attrNames (builtins.readDir dir));
  packages = builtins.filter (name: (builtins.readDir root).${name} == "directory") (
    builtins.attrNames (builtins.readDir root)
  );
  files = lib.concatMap (name: leaves name (root + "/${name}") "") packages;
  targets = map (item: item.target) files;
in
{
  assertions = [
    {
      assertion = builtins.length targets == builtins.length (lib.unique targets);
      message = "Two Stow packages own the same home file; resolve the conflict before activation.";
    }
  ];
  home.file = builtins.listToAttrs (
    map (item: {
      name = item.target;
      value.source = item.source;
    }) files
  );
}
