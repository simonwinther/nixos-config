{ inputs }:
inputs.hyprspace.packages.x86_64-linux.hyprspace.overrideAttrs (old: {
  patches = (old.patches or [ ]) ++ [ ./desktop-bar.patch ];
})
