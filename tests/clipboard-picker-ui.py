#!/usr/bin/env python3
"""Opt-in compositor smoke test with synthetic history and mocked paste commands.

Shows the picker briefly on the current Wayland session. It never changes the
real clipboard or history. Run inside the rust-desktop development shell.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import struct
import subprocess
import tempfile
import threading
import time
import zlib


def png(path, color):
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
    rows = bytearray()
    for y in range(140):
        rows.append(0)
        for x in range(240):
            pixel = (15, 18, 23)
            if y < 14:
                pixel = (28, 32, 40)
            elif x < 35:
                pixel = (20, 24, 31)
            elif 45 < x < 190 - (y // 11 % 5) * 19 and 24 < y < 83 and y % 11 < 3:
                pixel = tuple(int(value * .58) for value in color)
            elif 45 < x < 224 and 94 < y < 129:
                pixel = (22, 27, 35)
                if abs(y - (112 + ((x // 8 + color[0]) % 5 - 2) * 4)) < 2:
                    pixel = color
            rows.extend(pixel)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 240, 140, 8, 2, 0, 0, 0))
                     + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b""))


def exact(connection, length):
    data = b""
    while len(data) < length:
        part = connection.recv(length - len(data))
        if not part:
            raise EOFError()
        data += part
    return data


def frame(connection, kind, value):
    data = json.dumps(value).encode()
    connection.sendall(bytes([kind]) + struct.pack(">I", len(data)) + data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", type=Path)
    parser.add_argument("screenshot", type=Path)
    args = parser.parse_args()
    args.screenshot.parent.mkdir(parents=True, exist_ok=True)
    real_hyprctl = shutil.which("hyprctl")
    with tempfile.TemporaryDirectory(prefix="clipboard-ui-") as temporary:
        root = Path(temporary)
        (root / "elephant").mkdir()
        (root / "bin").mkdir()
        events = root / "events.jsonl"
        fake = """#!/usr/bin/env python3
import hashlib,json,os,sys
from pathlib import Path
name=Path(sys.argv[0]).name
record={'command':name,'args':sys.argv[1:]}
if name=='wl-copy':
 data=sys.stdin.buffer.read();record['bytes']=len(data);record['sha256']=hashlib.sha256(data).hexdigest()
with open(os.environ['PICKER_TEST_EVENTS'],'a') as out:out.write(json.dumps(record)+'\\n')
if name=='hyprctl':
 print(json.dumps({'address':'0xtest','class':'test.receiver'}) if sys.argv[1:]==['-j','activewindow'] else 'ok')
"""
        for name in ["hyprctl", "wl-copy"]:
            path = root / "bin" / name
            path.write_text(fake)
            path.chmod(0o755)
        items = []
        for index, color in enumerate([(72, 128, 195), (215, 131, 71), (85, 156, 128),
                                       (135, 114, 190), (176, 158, 88), (72, 155, 175),
                                       (187, 96, 129), (127, 147, 181)]):
            path = root / f"image-{index}.png"
            png(path, color)
            items.append({"identifier": f"image-{index}", "text": "", "preview": str(path),
                          "preview_type": "file", "subtext": "Mon, 26 Oct 2026 16:00:00 +0100",
                          "actions": ["copy", "pin", "remove"]})
        for index, text in enumerate(["services.desktop = {\n  enable = true;\n  theme = \"tokyoled\";\n};",
                                       "cargo build --release\n\nFinished release profile", "<tag> & literal text; hjkl",
                                       "A useful clipboard note.\nThe full text stays intact."]):
            items.append({"identifier": f"text-{index}", "text": text, "preview": text,
                          "preview_type": "text", "actions": ["copy", "pin", "remove"]})
        server = socket.socket(socket.AF_UNIX)
        server.bind(str(root / "elephant/elephant.sock"))
        server.listen()
        server.settimeout(0.2)
        stopped = threading.Event()
        def history():
            try:
                while not stopped.is_set():
                    try:
                        connection, _ = server.accept()
                    except socket.timeout:
                        continue
                    with connection:
                        header = exact(connection, 6)
                        exact(connection, struct.unpack(">I", header[2:])[0])
                        for item in items:
                            frame(connection, 0, {"item": item})
                        frame(connection, 255, {})
            finally:
                server.close()
        threading.Thread(target=history, daemon=True).start()
        env = os.environ.copy()
        display = Path(env["WAYLAND_DISPLAY"])
        if not display.is_absolute():
            display = Path(env["XDG_RUNTIME_DIR"]) / display
        env.update(XDG_RUNTIME_DIR=str(root), WAYLAND_DISPLAY=str(display),
                   XDG_CACHE_HOME=str(root / "cache"),
                   PATH=str(root / "bin") + ":" + env["PATH"], PICKER_TEST_EVENTS=str(events))

        def picker_layers():
            layers = json.loads(subprocess.check_output([real_hyprctl, "-j", "layers"]))
            return [layer for monitor in layers.values() for level in monitor["levels"].values()
                    for layer in level if layer["namespace"] == "clipboard-picker"]

        assert not picker_layers(), "Close the existing picker before running the UI test"

        def scenario(name, exercise, expected, screenshots=False):
            log = root / f"{name}.log"
            before = len(events.read_text().splitlines()) if events.exists() else 0
            with log.open("w") as output:
                child = subprocess.Popen([str(args.binary.resolve()), "--target", "0xtest", "--delay-ms", "200"],
                                         env=env, stdout=output, stderr=output)
                try:
                    deadline = time.monotonic() + 12
                    while time.monotonic() < deadline:
                        assert child.poll() is None, log.read_text()
                        layers = picker_layers()
                        if any(layer["pid"] == child.pid for layer in layers):
                            break
                        time.sleep(0.1)
                    else:
                        raise AssertionError("Picker did not appear")
                    time.sleep(0.5)

                    def send(*keys, ctrl=False, shift=False):
                        layers = picker_layers()
                        assert len(layers) == 1 and layers[0]["pid"] == child.pid, layers
                        command = ["wtype"]
                        modifiers = (["ctrl"] if ctrl else []) + (["shift"] if shift else [])
                        for modifier in modifiers:
                            command += ["-M", modifier]
                        for key in keys:
                            command += ["-k", key]
                        for modifier in reversed(modifiers):
                            command += ["-m", modifier]
                        subprocess.run(command, check=True)
                        time.sleep(0.08)

                    def type_text(text):
                        assert [layer["pid"] for layer in picker_layers()] == [child.pid]
                        subprocess.run(["wtype", "--", text], check=True)
                        time.sleep(0.3)

                    def capture(suffix):
                        layer = picker_layers()[0]
                        assert layer["pid"] == child.pid
                        rectangle = f"{layer['x']},{layer['y']} {layer['w']}x{layer['h']}"
                        path = args.screenshot.with_stem(args.screenshot.stem + suffix)
                        subprocess.run(["grim", "-g", rectangle, str(path.resolve())], check=True)

                    exercise(send, type_text)
                    if screenshots:
                        capture("")
                        send("p")
                        time.sleep(0.2)
                        capture("-preview")
                        send("Escape")
                        send("comma", ctrl=True)
                        capture("-menu")
                        send("Escape")
                    send("Return")
                    child.wait(timeout=8)
                    assert child.returncode == 0, log.read_text()
                    records = [json.loads(line) for line in events.read_text().splitlines()[before:]]
                    copies = [r for r in records if r["command"] == "wl-copy"]
                    pastes = [r for r in records if r["command"] == "hyprctl" and r["args"][0] == "eval"]
                    expected_hashes = []
                    for index in expected:
                        item = items[index]
                        payload = Path(item["preview"]).read_bytes() if item["preview_type"] == "file" else item["preview"].encode()
                        expected_hashes.append(hashlib.sha256(payload).hexdigest())
                    assert [r["sha256"] for r in copies] == expected_hashes, (name, expected, records)
                    assert len(pastes) == len(expected), (name, records)
                    assert all('address:0xtest' in r["args"][1] for r in pastes), records
                    assert not any(marker in log.read_text() for marker in ["panicked", "CRITICAL", "WARNING"]), log.read_text()
                    print(f"Passed {name}: exact selected payloads {expected}, in order.")
                finally:
                    if child.poll() is None:
                        child.terminate()
                        child.wait(timeout=5)

        def movement(send, _):
            send("j", ctrl=True)  # Leave search at the first card.
            send("space", "l", "space", "j", "space", "h", "space", "k", "space")
            send("j", ctrl=True)
            send("space")
            send("k", ctrl=True)
            send("space")

        def categories(send, _):
            send("Tab")  # Category cycling works while search has focus.
            send("j", ctrl=True)
            send("j", "space")  # Images: image 4.
            send("Tab", "l", "space")  # Text: text 1.
            send("Tab")  # Text -> All, wrapping forward.
            send("Tab", shift=True)
            send("h", "space")  # Text: text 0.
            send("Tab", shift=True)
            send("l", "space")  # Images: image 1.
            send("Tab", shift=True)
            send("Tab", shift=True)  # All -> Text, wrapping backward.
            send("l", "l", "space")  # Text: text 2.
            send("space", ctrl=True)
            send("space", ctrl=True)
            for key in ["i", "i", "t", "t"]:
                send(key, ctrl=True)

        def paging(send, _):
            send("d", ctrl=True)  # Half-page movement also leaves search.
            send("space")
            send("d", ctrl=True)
            send("space")
            send("u", ctrl=True)
            send("k", ctrl=True)
            send("space", "Page_Down", "Page_Up")

        def search(send, type_text):
            type_text("hjkl")  # Vim letters must remain literal in search.
            send("Escape", "h", "j", "k", "l", "space")
            send("slash")
            send("a", ctrl=True)
            type_text("cargo")
            send("Escape", "space", "i")
            send("a", ctrl=True)
            type_text("note")
            send("j", ctrl=True)
            send("space", "slash")
            send("a", ctrl=True)
            type_text("does-not-exist")
            send("Escape", "slash")  # Empty results must not trap search focus.
            send("a", ctrl=True)
            type_text("literal")
            send("j", ctrl=True)
            send("space", ctrl=True)
            send("Escape")

        def preview_navigation(send, _):
            send("space", ctrl=True)  # Preview also works directly from search.
            send("l", "j", "h", "k")
            send("d", ctrl=True)
            send("Escape", "Tab", "p", "Tab")  # Category change leaves preview.
            send("space", ctrl=True)
            send("l", "Escape")

        try:
            scenario("vim-movement", movement, [1, 5, 0], screenshots=True)
            scenario("category-cycling", categories, [4, 9, 8, 1, 10])
            scenario("half-page-movement", paging, [4, 8, 0])
            scenario("search-and-escape", search, [10, 9, 11])
            scenario("preview-navigation", preview_navigation, [9])
            print("GTK keyboard checks passed; real clipboard and history were untouched.")
            print(args.screenshot.resolve())
        finally:
            stopped.set()


if __name__ == "__main__":
    main()
