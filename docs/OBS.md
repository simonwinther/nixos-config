# OBS desktop settings

The source is the stationary desktop's preserved Arch home, read through a
read-only mount on 2026-10-23. The laptop's OBS collection was a separate minimal
setup and was not used to replace the desktop's scenes.

`dotfiles/obs/.local/share/obs-defaults` contains the reviewed preferences,
profile, encoder settings, scene collection, countdown script and original
Danish/English background images. OBS separates [output profiles](https://obsproject.com/kb/profiles)
from [scene collections and global audio sources](https://obsproject.com/kb/scene-collections);
both are included here.

The collection preserves all five scenes, source UUIDs, scene item transforms,
visibility, volume, tracks, monitoring, hotkeys and transitions. The microphone
uses the Scarlett Solo's original Mic1 source and its original filter order:

1. Noise Suppression, with its original OBS defaults.
2. 3-Band Equalizer: low +2.5, mid -2.0, high +2.0 dB.
3. Expander: 4:1, -35 dB threshold, 1 ms attack, 75 ms release.
4. Compressor: 3:1, 3 ms attack, 50 ms release, +4.5 dB output gain.
5. Limiter: -7 dB threshold.

Desktop audio retains its 20:1 sidechain compressor, triggered by `Mic/Aux`,
at -35 dB with 50 ms attack and 500 ms release. The profile retains 1080p60,
48 kHz stereo, advanced NVENC H.264 at 6,000 kbps, libfdk AAC and hybrid MP4.
Unspecified filter properties retain the original OBS defaults. These are
built-in filters; no third-party filter plugins are required. The countdown
uses the original five-minute Lua script, text styling and URW Bookman Demi
font. The Nix wrapper makes the installed NVIDIA driver visible to OBS and
its NVENC probe. The separately pinned unstable input provides OBS 32.2.2,
matching the source configuration's version and scene-collection format.

Home Manager links the defaults and helper, then materializes writable OBS
runtime files on the desktop. A content fingerprint avoids overwriting OBS UI
edits on unrelated rebuilds. Changed defaults are applied after a private backup;
an update is deferred if OBS is open. The portable OBS launcher applies pending
defaults on the next launch. Run `obs-config-sync` after closing OBS
to apply them explicitly, or `obs-config-sync --force` to deliberately restore
the declared settings. On another distribution, Stow the `obs` package and
provide OBS, Python 3 and URW Bookman.

The helper expands home/config/asset paths, preserves runtime service keys,
authentication sections, browser cookies, websocket passwords and existing
portal grants, and refuses managed links for writable OBS files. Runtime
credentials, portal tokens, logs, profiler data and downloaded plugin binaries
are excluded from the public defaults and Nix store. Backups live under
`~/.local/state/obs-sync/backups` with private permissions. Restoring a new
machine's streaming credentials is a separate private transfer; the public
defaults do not contain the Restream stream key.

Screen capture sources use the Wayland portal. Its grants are specific to the
running desktop session and must be verified there; the public scene collection
does not embed reusable screen-sharing authorization.

The original portal used compact 22-character restore IDs. The installed NixOS
portal 1.20.4 accepts UUIDs, so the private transfer remapped all three grants to
new UUIDs and preserved their original Hyprland restore data. The source names,
monitor selection, cursor settings and OBS application permission were retained.
The mapping and original files are in private migration backups under XDG state.
Copying only the old scene file would leave these captures black.

`tests/test_obs.py` covers the complete scene graph, audio chain, assets,
credential preservation, private backups, runtime-edit preservation, portal
grants and refusal to overwrite live/linked/malformed configurations. The
`obs-integration` Nix check also verifies the actual package and countdown font.

On the stationary desktop, OBS 32.2.2 loaded all five scenes, seven scene items,
six audio filters and all 97 declared profile parameters. All three PipeWire
captures reported 1920 × 1080. A short recording of the countdown scene, with
both live audio inputs muted for the test, passed H.264 1080p60 and 48 kHz stereo
AAC inspection. The original scene, recording directory and mute states were
restored after validation. The private Restream service settings were compared
without publishing them or starting a stream.
