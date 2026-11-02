#!/usr/bin/env python3
"""Deterministic catalogs and recorded actions for the private compositor."""

import json
import os
from pathlib import Path
import signal
import struct
import sys
import time
import zlib

root = Path(os.environ["DESKTOP_BAR_TEST_ROOT"])
args = sys.argv[1:]
if args[:2] == ["bar", "catalog"] and (root / ("stall-catalog-" + args[2])).exists():
    (root / "stalled-catalog-pid").write_text(str(os.getpid()))
    time.sleep(30)
if args[:2] == ["bar", "thumbnail"] and (root / "stall-thumbnail").exists():
    (root / "stalled-thumbnail-pid").write_text(str(os.getpid()))
    time.sleep(30)
if args[:2] == ["bar", "cover"] and (root / "stall-cover").exists():
    (root / "stalled-cover-pid").write_text(str(os.getpid()))
    time.sleep(30)


def image(index):
    target = root / f"wallpaper-{index}.png"
    if not target.exists():
        def chunk(kind, data):
            return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
        rows = b"".join(b"\0" + bytes((40 + index * 40, 65 + y // 3, 120 + index * 20)) * 320 for y in range(180))
        target.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 320, 180, 8, 2, 0, 0, 0))
                           + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b""))
    return str(target)


if args[:2] == ["bar", "catalog"]:
    kind = args[2]
    if kind == "apps":
        with (root / "application-requests.jsonl").open("a") as stream:
            stream.write(json.dumps({"started": time.monotonic()}) + "\n")
        time.sleep(0.6)
        entries = [{"id": name, "name": name, "detail": detail, "image": image(i),
                    "command": ["bar", "launch", f"/test/{name}.desktop"]}
                   for i, (name, detail) in enumerate((
                       ("Alpha Writer", "Text editor"), ("File Manager", "Browse files"),
                       ("Zebra Terminal", "Terminal emulator")))]
    elif kind == "themes":
        entries = [{"id": name, "name": name, "selected": i == 1,
                    "colors": ["#60a5fa", "#a778fa", "#4ade80", "#eab308", "#f87171", "#94a3b8"],
                    "command": ["theme", "set", name]}
                   for i, name in enumerate(("Forest", "Tokyoled", "Catppuccin", "Lumon"))]
    elif kind == "wallpapers":
        entries = [{"id": str(i), "name": f"Wallpaper {i + 1}", "image": image(i), "selected": i == 1,
                    "command": ["wallpaper", "set", image(i)]} for i in range(4)]
    elif kind == "menu/system":
        entries = [{"id": "lock", "name": "Lock", "command": ["lock"]},
                   {"id": "sleep", "name": "Sleep", "command": ["power", "suspend"]}]
    else:
        entries = []
    print(json.dumps(entries))
elif args[:2] == ["bar", "cover"]:
    print(image(3 if args[2].endswith("current-cover") else 0))
elif args[:2] == ["bar", "thumbnail"]:
    with (root / "thumbnail-requests.jsonl").open("a") as stream:
        stream.write(json.dumps(args[2]) + "\n")
    time.sleep(0.12)
    print(args[2])
else:
    with (root / "shell-actions.jsonl").open("a") as stream:
        stream.write(json.dumps(args) + "\n")
    if args[:2] == ["bar", "set"]:
        path = Path(os.environ["XDG_RUNTIME_DIR"]) / "desktop/bar-theme.json"
        value = json.loads(path.read_text())
        value["style"] = args[2]
        path.write_text(json.dumps(value))
        os.kill(int((root / "bar.pid").read_text()), signal.SIGUSR2)
