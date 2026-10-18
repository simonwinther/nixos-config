{ inputs }:
let
  # Preserve the current working source, including the Rust launch helper and
  # uncommitted overview fixes, rather than rebuilding only the last Git commit.
  outputs = (import ./source/flake.nix).outputs {
    hyprland = inputs.hyprland;
    self = outputs;
  };
in
outputs.packages.x86_64-linux.hyprspace
