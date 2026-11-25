{ mako }:
# Notification history keeps each icon at its source resolution, so every
# screenshot notification held a full-size bitmap (about 47 MB for 41 of them).
mako.overrideAttrs (old: {
  patches = (old.patches or [ ]) ++ [ ./bounded-icon-memory.patch ];
})
