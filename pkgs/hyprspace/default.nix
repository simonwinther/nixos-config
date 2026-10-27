{ inputs }:
let
  # Build the vendored upstream revision recorded in source.json, including
  # independent spaces and the native Rust launch helper.
  outputs = (import ./source/flake.nix).outputs {
    hyprland = inputs.hyprland;
    self = outputs;
  };
in
outputs.packages.x86_64-linux.hyprspace
