"""Native clipboard acceptance inside the bar's private Wayland compositor."""
import hashlib
import json
import os
import re
import signal
from pathlib import Path
import statistics
import subprocess
import time


def exercise(context):
    root, environment = context.root, dict(context.environment)
    environment["PATH"] = str(context.search.parent) + os.pathsep + environment["PATH"]
    environment.pop("NOTIFY_SOCKET", None)
    # The headless compositor, session bus, configuration and history are all private.
    search = context.start([str(context.search), "serve", "--no-compatibility"], "search", env=environment)
    canonical = Path(environment["XDG_RUNTIME_DIR"]) / "desktop-search/search.sock"
    context.wait_for(canonical.is_socket)

    def command(*arguments):
        result = subprocess.run([str(context.search), *arguments], env=environment, capture_output=True, text=True, timeout=15)
        assert result.returncode == 0, result.stderr
        return json.loads(result.stdout)

    def history(query=""):
        return command("query", "clipboard", query)

    def copy(data, mime="text/plain;charset=utf-8"):
        subprocess.run(["wl-copy", "--type", mime], env=environment, input=data, check=True, timeout=5)

    def payload(item):
        return Path(item["payload_path"]).read_bytes()

    imported = command("import-elephant")["imported"]
    assert imported["clipboard"] == 12 and imported["images"] == 1
    context.wait_for(lambda: len(history()) == 12)
    original = {item["identifier"]: hashlib.sha256(payload(item)).hexdigest() for item in history()}
    image = (root / "wallpaper-0.png").read_bytes()
    started = time.monotonic()
    copy(image, "image/png")
    context.wait_for(lambda: history()[0]["mimetype"] == "image/png")
    image_time = time.monotonic() - started
    assert payload(history()[0]) == image

    # This goes through the actual bar, shared payload reader and Wayland copy.
    context.panel("clipboard")
    context.wait_for(lambda: context.settled_height(464))
    context.send("key 29 1")
    context.send("key 15 1")  # All -> Images
    context.send("key 15 0")
    context.send("key 29 0")
    time.sleep(0.15)
    context.capture("search-native-clipboard")
    context.send("key 29 1")
    context.send("key 28 1")
    context.send("key 28 0")
    context.send("key 29 0")
    context.wait_for(context.no_backdrop)
    assert subprocess.check_output(["wl-paste", "--type", "image/png"], env=environment, timeout=5) == image

    # A long text preview stays bounded while copying preserves every byte.
    text = ("literal $HOME; æ <tag>\n" * 5000).encode()
    started = time.monotonic()
    copy(text)
    context.wait_for(lambda: any(payload(item) == text for item in history("literal")))
    text_time = time.monotonic() - started
    item = next(item for item in history("literal") if payload(item) == text)
    assert len(item["preview"].encode()) < len(text)
    command("activate", "clipboard", item["identifier"], "copy")
    assert subprocess.check_output(["wl-paste", "--no-newline"], env=environment, timeout=5) == text
    command("activate", "clipboard", item["identifier"], "pin")
    identifier = item["identifier"]

    # Password manager hints and paused collection must never enter history.
    private = b"synthetic-password-never-store"
    copy(private, "x-kde-passwordManagerHint")
    time.sleep(0.15)
    assert not history("synthetic-password-never-store")
    command("activate", "clipboard", "", "pause")
    copy(b"paused-content")
    time.sleep(0.15)
    assert not history("paused-content")
    command("activate", "clipboard", "", "unpause")
    context.wait_for(lambda: bool(history("paused-content")))

    # Rapid selections retain recency without accumulating decoded image data.
    for index in range(120):
        copy(f"burst-fixture-{index:03}".encode())
    context.wait_for(lambda: len(history()) == 100)
    context.wait_for(lambda: any(item["preview"] == "burst-fixture-119" for item in history()))
    items = history()
    assert items[0]["identifier"] == identifier and "pinned" in items[0]["state"]
    assert items[1]["preview"] == "burst-fixture-119"
    assert not (set(original) & {item["identifier"] for item in items})
    burst_count = sum(item["preview"].startswith("burst-fixture-") for item in items)
    assert burst_count == 99

    apps = Path(environment["XDG_DATA_HOME"]) / "applications"
    apps.mkdir(parents=True, exist_ok=True)
    (apps / "private-fixture.desktop").write_text('[Desktop Entry]\nType=Application\nName=Private Notes Fixture\nExec=never-execute-test-fixture\n')
    assert command("query", "desktopapplications", "Private Notes Fixture")
    queries = []
    for _ in range(20):
        started = time.monotonic()
        assert command("query", "desktopapplications", "Private Notes Fixture")
        queries.append(time.monotonic() - started)

    # Every provider and command-line picker shares the bar in both styles.
    def tap(key):
        context.send(f"key {key} 1")
        context.send(f"key {key} 0")

    def chord(modifier, key):
        context.send(f"key {modifier} 1")
        tap(key)
        context.send(f"key {modifier} 0")

    def log():
        return (root / "bar.log").read_text()

    def replies():
        return re.findall(r"bar-(?:search|filter) generation=\d+ revision=\d+ results=(\d+)", log())

    def native(provider, query="", allow_empty=False):
        previous = len(replies())
        context.panel("launcher/" + json.dumps({"providers": [provider], "query": query}))
        context.wait_for(lambda: len(replies()) > previous)
        if not allow_empty:
            assert int(replies()[-1]) > 0, (provider, query, log())
        context.wait_for(lambda: context.settled_height(352))
        time.sleep(0.05)

    (Path(environment["HOME"]) / "nixos-configuration.txt").write_text("private file fixture")
    checked = []
    fuzzy_times = []
    for style in ("native-motion", "native-clean"):
        context.style(style)
        context.move(context.width - 100, context.height - 100)
        context.panel("menu/main")
        context.wait_for(lambda: context.settled_height(352))
        for key in (48,38,22,18,46):  # bluec in the Go menu, as in the reported example.
            tap(key)
        time.sleep(0.1)
        context.capture("native-go-fuzzy-bluetooth-" + style)
        previous = log().count("bar-page Bluetooth")
        tap(28)
        context.wait_for(lambda: log().count("bar-page Bluetooth") > previous)
        tap(1)
        tap(1)
        context.wait_for(context.no_backdrop)
        for _ in range(5):
            previous = len(replies())
            started = time.monotonic()
            context.panel("launcher/" + json.dumps({"providers": [], "query": "bluec"}))
            context.wait_for(lambda: len(replies()) > previous)
            fuzzy_times.append(time.monotonic() - started)
            assert int(replies()[-1]) == 1, replies()
        context.capture("native-fuzzy-bluetooth-" + style)
        previous = log().count("bar-page Bluetooth")
        tap(28)
        context.wait_for(lambda: log().count("bar-page Bluetooth") > previous)
        tap(1)  # Return to the fuzzy result, preserving the parent.
        context.wait_for(lambda: context.settled_height(352))
        tap(1)
        context.wait_for(context.no_backdrop)

        for provider, query in (("files", "nxcfg"), ("runner", "printf"),
                                ("symbols", "rocket"), ("unicode", "U+2605"),
                                ("websearch", "private fixture"),
                                ("menus:repositories", "owner repo"),
                                ("providerlist", "bluetooth")):
            native(provider, query)
            context.capture("native-" + provider.replace(":", "-") + "-" + style)
            tap(1)
            context.wait_for(context.no_backdrop)
            checked.append(style + ":" + provider)

        native("calc", "2+3")
        previous = len(replies())
        chord(29, 21)  # Ctrl+Y copies the result without closing.
        context.wait_for(lambda: len(replies()) > previous)
        assert not context.no_backdrop()
        assert subprocess.check_output(["wl-paste", "--no-newline"], env=environment, timeout=5) == b"5"
        context.capture("native-calculator-" + style)
        tap(1)
        context.wait_for(context.no_backdrop)

        native("todo", allow_empty=True)
        chord(29, 24)  # Ctrl+O: provider actions, even when there are no tasks.
        for key in (49,18,17):  # new
            tap(key)
        tap(28)
        context.wait_for(lambda: any(item["identifier"] == "new" for item in command("query", "todo")))
        time.sleep(0.1)
        previous = len(replies())
        for key in (25,19,23,47,30,20,18,57,49,30,20,23,47,18,57,20,30,31,37):
            tap(key)  # private native task
        context.wait_for(lambda: len(replies()) > previous)
        time.sleep(0.1)
        tap(28)
        context.wait_for(lambda: any(item["identifier"] != "new" for item in command("query", "todo", "private native task")))
        context.capture("native-tasks-" + style)
        tap(1)
        context.wait_for(context.no_backdrop)

        # A literal row is returned to its caller; cancelling returns status 130.
        for cancelled in (False, True):
            picker = context.start([str(context.binary), "--dmenu", "--placeholder", "Private choices"],
                "native-dmenu-" + style + str(cancelled), env=environment, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            picker.stdin.write(b"First row\nLiteral $HOME; $(value)\n")
            picker.stdin.close()
            context.wait_for(lambda: context.settled_height(352) and not context.no_backdrop())
            time.sleep(0.15)
            if cancelled:
                tap(1)
            else:
                chord(29, 36)
                context.capture("native-dmenu-" + style)
                tap(28)
            assert picker.wait(timeout=5) == (130 if cancelled else 0)
            assert picker.stdout.read() == (b"" if cancelled else b"Literal $HOME; $(value)\n")
            context.wait_for(context.no_backdrop)

    # With the persistent bar stopped, hidden-bar preferences survive a native fallback.
    context.bar.send_signal(signal.SIGTERM)
    context.bar.wait(timeout=5)
    marker = Path(environment["XDG_STATE_HOME"]) / "desktop/toggles/bar-off"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.touch()
    fallback = context.start([str(context.binary), "--dmenu", "--placeholder", "Temporary native menu"],
        "native-dmenu-standalone", env=environment, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    fallback.stdin.write(b"Temporary choice\n")
    fallback.stdin.close()
    context.wait_for(lambda: not context.no_backdrop())
    time.sleep(0.7)
    context.capture("native-dmenu-standalone")
    tap(28)
    assert fallback.wait(timeout=5) == 0
    assert fallback.stdout.read() == b"Temporary choice\n"
    assert marker.exists()
    assert not (Path(environment["XDG_RUNTIME_DIR"]) / "desktop/bar.sock").exists()
    assert not (Path(environment["XDG_RUNTIME_DIR"]) / "desktop/menus.sock").exists()

    def memory():
        return {line.split()[0].rstrip(":"): int(line.split()[1])
                for line in Path(f"/proc/{search.pid}/smaps_rollup").read_text().splitlines()
                if line.startswith(("Rss:", "Pss:"))}

    def cpu():
        fields = Path(f"/proc/{search.pid}/stat").read_text().split(") ", 1)[1].split()
        return (int(fields[11]) + int(fields[12])) / os.sysconf("SC_CLK_TCK")

    time.sleep(0.3)
    resources = {name: len(list(Path(f"/proc/{search.pid}/{name}").iterdir())) for name in ("fd", "task")}
    initial = cpu()
    started = time.monotonic()
    time.sleep(5)
    idle_cpu = 100 * (cpu() - initial) / (time.monotonic() - started)
    assert search.poll() is None, (root / "search.log").read_text()
    assert not list((Path(environment["XDG_STATE_HOME"]) / "desktop-search/incoming").iterdir())
    return {"imported": imported, "image_capture_seconds": round(image_time, 4),
            "long_text_capture_seconds": round(text_time, 4), "retained_burst_items": burst_count,
            "query_with_process_median_seconds": round(statistics.median(queries), 4),
            "memory_kib": memory(), "resources": resources, "idle_cpu_percent_one_core": round(idle_cpu, 3),
            "native_modes_checked": checked, "fuzzy_request_median_seconds": round(statistics.median(fuzzy_times), 4), "standalone_picker_checked": True}
