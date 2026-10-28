# Only listed packages are deployed. Literal exclusions are shared with deploy.py.
{
  root ? ../dotfiles,
}:
let
  manifest = builtins.fromJSON (builtins.readFile (root + "/packages.json"));
  entries = builtins.readDir root;
  validComponents =
    values:
    builtins.isList values
    && builtins.all (
      value:
      builtins.isString value
      && !(builtins.elem value [
        ""
        "."
        ".."
      ])
      && builtins.match "[^/\n\r]*" value != null
    ) values;
  valid =
    builtins.isAttrs manifest
    &&
      builtins.attrNames manifest == [
        "ignore"
        "packages"
        "version"
      ]
    && manifest.version == 1
    && builtins.isInt manifest.version
    && builtins.isList manifest.packages
    && manifest.packages != [ ]
    && builtins.all (
      name:
      builtins.isString name
      && builtins.match "[a-z0-9][a-z0-9-]*" name != null
      && (entries.${name} or null) == "directory"
    ) manifest.packages
    &&
      manifest.packages == builtins.attrNames (
        builtins.listToAttrs (
          map (name: {
            inherit name;
            value = null;
          }) manifest.packages
        )
      )
    && builtins.isAttrs manifest.ignore
    &&
      builtins.attrNames manifest.ignore == [
        "names"
        "rootNames"
        "suffixes"
      ]
    && builtins.all validComponents (builtins.attrValues manifest.ignore);
  packages =
    if valid then
      manifest.packages
    else
      throw "Invalid dotfiles/packages.json: require version 1, sorted unique existing package directories and literal ignore rules.";
  hasSuffix =
    suffix: value:
    let
      length = builtins.stringLength value;
      suffixLength = builtins.stringLength suffix;
    in
    length >= suffixLength && builtins.substring (length - suffixLength) suffixLength value == suffix;
  ignored =
    rel: name:
    builtins.elem name manifest.ignore.names
    || builtins.any (suffix: hasSuffix suffix name) manifest.ignore.suffixes
    || (rel == "" && builtins.elem name manifest.ignore.rootNames);
  leaves =
    package: dir: rel:
    let
      children = builtins.readDir dir;
    in
    builtins.concatMap (
      name:
      let
        child = if rel == "" then name else "${rel}/${name}";
      in
      if ignored rel name then
        [ ]
      else if children.${name} == "directory" then
        leaves package (dir + "/${name}") child
      else
        [
          {
            target = child;
            source = "${package}/${child}";
          }
        ]
    ) (builtins.attrNames children);
  files = builtins.concatMap (name: leaves name (root + "/${name}") "") packages;
  owners = builtins.listToAttrs (
    map (file: {
      name = file.target;
      value = file.source;
    }) files
  );
  parents =
    target:
    let
      parent = builtins.dirOf target;
    in
    if parent == "." then [ ] else [ parent ] ++ parents parent;
  conflicts = builtins.filter (
    file: builtins.any (parent: builtins.hasAttr parent owners) (parents file.target)
  ) files;
in
assert
  builtins.length files == builtins.length (builtins.attrNames owners)
  || throw "Two manifest packages own the same home file; resolve the conflict before activation.";
assert
  conflicts == [ ]
  || throw "Manifest packages have a file/directory target conflict: ${(builtins.head conflicts).target}";
{
  inherit packages files;
}
