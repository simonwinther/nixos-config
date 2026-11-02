#!/usr/bin/env python3
"""Exercise a bar in a private compositor without connecting to desktop sockets."""

import argparse
import json
import os
from pathlib import Path
import re
import select
import shlex
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time


def wait_for(predicate, timeout=15):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(0.05)
    raise AssertionError("Timed out waiting for the private compositor")


def reply(process):
    if not select.select([process.stdout], [], [], 5)[0]:
        raise AssertionError("Virtual input fixture did not reply")
    return process.stdout.readline().strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", type=Path)
    parser.add_argument(
        "display_host", type=Path, help="Hyprspace test-headless fixture"
    )
    parser.add_argument("pointer", type=Path, help="Hyprspace test-pointer fixture")
    parser.add_argument("--idle-seconds", type=int, default=60)
    parser.add_argument("--search-binary", type=Path, help="Exercise native search and clipboard collection")
    parser.add_argument("--trace", action="store_true")
    parser.add_argument("--keyboard-only", action="store_true", help="Check Vim navigation, contextual help and dashboard shortcut")
    parser.add_argument("--compact-only", action="store_true", help="Check compact notch status targets and workspace zero")
    parser.add_argument("--profile-only", action="store_true", help="Measure idle notch and panel redraws")
    parser.add_argument("--check-idle", action="store_true", help="Check that hidden metrics leave static views idle")
    parser.add_argument("--morph-state-only", action="store_true", help="Check workspace updates while opening and closing")
    parser.add_argument("--bus-load-only", action="store_true", help="Measure unrelated signals and player position updates")
    parser.add_argument("--check-bus-load", action="store_true", help="Check that position changes do not refetch metadata")
    parser.add_argument("--network-recovery-only", action="store_true", help="Check Wi-Fi service disappearance and return")
    parser.add_argument("--media-recovery-only", action="store_true", help="Check stalled players and playback action recovery")
    parser.add_argument("--delayed-session-bus", action="store_true", help="Check reconnection after a delayed session bus")
    parser.add_argument("--cover-recovery-only", action="store_true", help="Check cancellation of an obsolete artwork request")
    parser.add_argument(
        "--hyprspace",
        action="store_true",
        help="Use active-space metadata and namespace-checked workspace commands",
    )
    parser.add_argument(
        "--tray",
        action="store_true",
        help="Exercise menus with the dbus-next tray fixture",
    )
    args = parser.parse_args()
    root = Path(tempfile.mkdtemp(prefix="db."))
    root.chmod(0o700)
    environment = dict(os.environ)
    for key in (
        "DISPLAY",
        "WAYLAND_DISPLAY",
        "WAYLAND_SOCKET",
        "DBUS_SESSION_BUS_ADDRESS",
        "HYPRLAND_INSTANCE_SIGNATURE",
        "DESKTOP_BAR_SCALE",
        "XDG_ACTIVATION_TOKEN",
        "HL_INITIAL_WORKSPACE_TOKEN",
    ):
        environment.pop(key, None)
    for key, name in (
        ("HOME", "home"),
        ("XDG_CONFIG_HOME", "config"),
        ("XDG_STATE_HOME", "state"),
        ("XDG_DATA_HOME", "data"),
        ("XDG_CACHE_HOME", "cache"),
        ("XDG_RUNTIME_DIR", "r"),
    ):
        path = root / name
        path.mkdir(mode=0o700)
        environment[key] = str(path)
    environment.pop("XCOMPOSEFILE", None)
    environment["XCOMPOSEFILE"] = str(root / "empty-compose")
    (root / "empty-compose").write_text('<Multi_key> <a> <e> : "æ"\n')
    tools = root / "bin"
    tools.mkdir()
    controller = tools / "desktopctl"
    controller.write_text(
        f"#!{sys.executable}\n" + Path(__file__).with_name("desktop-bar-catalog-fixture.py").read_text()
    )
    controller.chmod(0o700)
    bar_command = tools / "desktop-bar"
    bar_command.write_text("#!/bin/sh\nexec " + shlex.quote(str(args.binary.resolve())) + ' "$@"\n')
    bar_command.chmod(0o700)
    menu_file = Path(environment["XDG_CONFIG_HOME"]) / "desktop/menus.json"
    menu_file.parent.mkdir(parents=True)
    menu_file.write_text(json.dumps({
        "main": {"items": {"Applications": ["panel", "apps"], "Style": ["menu", "style"]}},
        "style": {"items": {"Bar style": ["menu", "bar"], "Back": ["menu", "main"]}},
        "system": {"items": {"Lock": ["lock"], "Sleep": ["power", "suspend"]}},
    }))
    environment["DESKTOP_MENUS_FILE"] = str(menu_file)
    audio_control = tools / "wpctl"
    audio_control.write_text(f"#!{sys.executable}\nimport json,os,sys\nfrom pathlib import Path\nwith (Path(os.environ['DESKTOP_BAR_TEST_ROOT'])/'audio-actions.jsonl').open('a') as log: log.write(json.dumps(sys.argv[1:])+'\\n')\n")
    audio_control.chmod(0o700)
    environment["PATH"] = str(tools) + os.pathsep + environment["PATH"]
    environment["DESKTOP_BAR_TEST_ROOT"] = str(root)
    environment["DESKTOP_BAR_TRACE_FRAMES"] = "1"
    environment.update(
        {
            "LIBSEAT_BACKEND": "seatd",
            "SEATD_SOCK": str(root / "no-seatd"),
            "PULSE_SERVER": "unix:" + str(root / "no-pulse"),
            "PIPEWIRE_REMOTE": str(root / "no-pipewire"),
        }
    )
    processes = []
    bus_listener = None
    logs = []
    stop_sampling = threading.Event()
    sampler = None
    peak = {"Rss": 0, "Pss": 0}
    startup_peak = {"Rss": 0, "Pss": 0}
    startup = True

    def memory(pid):
        values = {}
        for line in Path(f"/proc/{pid}/smaps_rollup").read_text().splitlines():
            if line.startswith(("Rss:", "Pss:")):
                key, value, _ = line.split()
                values[key.rstrip(":")] = int(value)
        return values

    def sample(pid):
        while not stop_sampling.is_set():
            try:
                for key, value in memory(pid).items():
                    peak[key] = max(peak[key], value)
                    if startup:
                        startup_peak[key] = max(startup_peak[key], value)
            except (FileNotFoundError, ProcessLookupError):
                return
            stop_sampling.wait(0.05)

    def start(command, name, env=environment, **kwargs):
        log = (root / (name + ".log")).open("w")
        logs.append(log)
        process = subprocess.Popen(
            command,
            env=env,
            stdout=kwargs.pop("stdout", log),
            stderr=log,
            start_new_session=True,
            **kwargs,
        )
        processes.append(process)
        return process

    def capture(name, output=None):
        subprocess.run(
            ["grim", "-o", output or monitor, str(root / (name + ".png"))],
            env=environment,
            check=True,
            timeout=10,
        )

    def pixel(output, x, y):
        raw = subprocess.check_output(["grim", "-t", "ppm", "-o", output, "-"], env=environment, timeout=10)
        header, pixels = raw.split(b"\n255\n", 1)
        width = int(header.split()[1])
        offset = (y * width + x) * 3
        return tuple(pixels[offset:offset + 3])

    def control(*command):
        result = subprocess.run(
            ["hyprctl", *command],
            env=environment,
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        return result.stdout

    try:
        parent = root / "parent"
        parent.mkdir(mode=0o700)
        start(
            [str(args.display_host.resolve())],
            "parent",
            env={**environment, "XDG_RUNTIME_DIR": str(parent)},
        )
        wait_for(lambda: (parent / "background").is_socket())
        environment["WAYLAND_DISPLAY"] = str(parent / "background")
        config = root / "hyprland.lua"
        config.write_text(
            'hl.monitor({output="",mode="1920x1080@60",position="auto",scale=1})\n'
            "hl.config({misc={disable_hyprland_logo=true,disable_splash_rendering=true},"
            "animations={enabled=false},input={follow_mouse=1},debug={disable_logs=false}})\n"
        )
        boot = (
            "import os,sys;from pathlib import Path;"
            'Path(sys.argv[1]).write_text(os.environ["DBUS_SESSION_BUS_ADDRESS"]);'
            'os.execvp("Hyprland",["Hyprland","--config",sys.argv[2]])'
        )
        bus_config = root / "bus.conf"
        bus_config.write_text(
            "<busconfig><type>session</type><listen>unix:tmpdir=/tmp</listen>"
            '<auth>EXTERNAL</auth><policy context="default">'
            '<allow send_destination="*"/><allow receive_sender="*"/>'
            '<allow own="*"/></policy></busconfig>'
        )
        start(
            [
                "dbus-run-session",
                "--config-file=" + str(bus_config),
                "--",
                "python3",
                "-c",
                boot,
                str(root / "bus"),
                str(config),
            ],
            "compositor",
        )
        runtime = Path(environment["XDG_RUNTIME_DIR"])
        display = wait_for(
            lambda: next((p for p in runtime.glob("wayland-*") if p.is_socket()), None)
        )
        ipc = wait_for(lambda: next(iter(runtime.glob("hypr/*/.socket.sock")), None))
        environment.update(
            {
                "WAYLAND_DISPLAY": display.name,
                "HYPRLAND_INSTANCE_SIGNATURE": ipc.parent.name,
                "DBUS_SESSION_BUS_ADDRESS": (root / "bus").read_text(),
                "DBUS_SYSTEM_BUS_ADDRESS": (root / "bus").read_text(),
            }
        )
        subprocess.run([str(controller), "bar", "catalog", "wallpapers"], env=environment,
                       stdout=subprocess.DEVNULL, check=True)
        start([sys.executable, str(Path(__file__).with_name("desktop-bar-state-fixture.py"))], "state")
        wait_for(lambda: (root / "state-ready").exists())
        # Serve either explicit native compatibility or the active-space schema.
        # Space summaries deliberately have no nested workspace array.
        compatibility = socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        compatibility.bind(str(ipc.parent / "hyprspace.sock"))
        compatibility.listen()

        def serve_namespace():
            while True:
                try:
                    connection, _ = compatibility.accept()
                    with connection:
                        message = connection.recv(65536)
                        with (root / "namespace.log").open("ab") as log:
                            log.write(message + b"\n")
                        if not args.hyprspace:
                            response = {"schema": 1, "type": "spaces", "enabled": False}
                        elif message.startswith(b"workspace "):
                            selection = json.loads(message.split(b" ", 1)[1])
                            assert selection["space"] == "fixture-space"
                            assert selection["workspace"] in [
                                str(n) for n in range(1, 11)
                            ] + ["e+1", "e-1"]
                            control(
                                "eval",
                                "hl.dispatch(hl.dsp.focus({ monitor = "
                                + json.dumps(selection["monitor"])
                                + " })); hl.dispatch(hl.dsp.focus({ workspace = "
                                + json.dumps(selection["workspace"])
                                + " }))",
                            )
                            response = {"success": True}
                        else:
                            assert message == b"spaces"
                            monitors = json.loads(control("-j", "monitors"))
                            workspaces = json.loads(control("-j", "workspaces"))
                            response = {
                                "schema": 1,
                                "type": "spaces",
                                "enabled": True,
                                "active": "fixture-space",
                                "spaces": [
                                    {
                                        "id": "fixture-space",
                                        "active": True,
                                        "occupied_workspaces": len(workspaces),
                                    }
                                ],
                                "monitors": [
                                    {
                                        "name": m["name"],
                                        "number": m["activeWorkspace"]["id"],
                                    }
                                    for m in monitors
                                ],
                                "workspaces": [
                                    {
                                        "number": w["id"],
                                        "native_id": w["id"],
                                        "monitor": w["monitor"],
                                        "occupied": True,
                                        "special": w["id"] < 1,
                                    }
                                    for w in workspaces
                                ],
                            }
                            occupancy = root / "workspace-occupancy.json"
                            if occupancy.is_file():
                                response["workspaces"] = json.loads(occupancy.read_text())
                        connection.sendall(json.dumps(response).encode())
                except OSError:
                    return

        threading.Thread(target=serve_namespace, daemon=True).start()
        output = wait_for(lambda: json.loads(control("-j", "monitors")))[0]
        monitor = output["name"]
        if args.hyprspace:
            # Keep empty destinations alive so relative scrolling has several
            # existing workspaces to cycle through in this windowless fixture.
            for number in (1, 5, 10):
                control(
                    "eval",
                    f'hl.workspace_rule({{workspace="{number}",monitor={json.dumps(monitor)},persistent=true}})',
                )
        screen_width = round(output["width"] / output["scale"])
        screen_height = round(output["height"] / output["scale"])
        control("dismissnotify", "-1")
        settings = {
            "style": "native-motion" if args.compact_only or args.keyboard_only or args.search_binary or args.profile_only or args.morph_state_only or args.bus_load_only or args.network_recovery_only or args.media_recovery_only or args.delayed_session_bus or args.cover_recovery_only else "native-clean",
            "scale": 1.0,
            "outputs": {"full": [monitor], "minimal": []},
        }
        theme = runtime / "desktop/bar-theme.json"
        theme.parent.mkdir()
        theme.write_text(json.dumps(settings))
        if args.keyboard_only:
            (root / "media-state.json").write_text(json.dumps({"available": False}))
        command = [str(args.binary.resolve())]
        if args.trace:
            command = [
                "strace",
                "-f",
                "-tt",
                "-e",
                "trace=epoll_wait,epoll_pwait,poll,ppoll,clock_nanosleep",
                "-o",
                str(root / "idle.trace"),
                *command,
            ]
        bar_env = {**environment, "WAYLAND_DEBUG": "client"} if args.profile_only or os.environ.get("DESKTOP_BAR_WAYLAND_DEBUG") else environment
        if args.delayed_session_bus:
            bar_env = {**bar_env, "DBUS_SESSION_BUS_ADDRESS": "unix:path=" + str(root / "delayed-bus")}
        bar = start(command, "bar", env=bar_env)
        pid = bar.pid
        if args.trace:
            child = wait_for(
                lambda: (
                    Path(f"/proc/{bar.pid}/task/{bar.pid}/children").read_text().strip()
                )
            )
            pid = int(child.split()[0])
        sampler = threading.Thread(target=sample, args=(pid,), daemon=True)
        (root / "bar.pid").write_text(str(pid))
        sampler.start()
        wait_for(lambda: "desktop-bar-" in control("-j", "layers"))
        if args.delayed_session_bus:
            # Relay only this bar's private bus connections after its first
            # connection attempts have failed. Fixtures keep their healthy bus.
            time.sleep(0.3)
            bus_listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            bus_listener.bind(str(root / "delayed-bus"))
            bus_listener.listen()
            address = environment["DBUS_SESSION_BUS_ADDRESS"].split(",", 1)[0]
            destination = address.removeprefix("unix:path=") if address.startswith("unix:path=") else "\0" + address.removeprefix("unix:abstract=")
            def forward(incoming):
                upstream = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                try:
                    upstream.connect(destination)
                    while True:
                        if (root / "drop-session-bus").exists():
                            return
                        ready, _, _ = select.select([incoming, upstream], [], [], 0.1)
                        for stream in ready:
                            data = stream.recv(65536)
                            if not data:
                                return
                            (upstream if stream is incoming else incoming).sendall(data)
                except OSError:
                    pass
                finally:
                    incoming.close()
                    upstream.close()
            def accept():
                while True:
                    try:
                        incoming, _ = bus_listener.accept()
                    except OSError:
                        return
                    if (root / "drop-session-bus").exists():
                        incoming.close()
                    else:
                        threading.Thread(target=forward, args=(incoming,), daemon=True).start()
            threading.Thread(target=accept, daemon=True).start()
            def watcher_ready():
                query = subprocess.run(["dbus-send", "--session", "--print-reply", "--dest=org.freedesktop.DBus",
                    "/org/freedesktop/DBus", "org.freedesktop.DBus.NameHasOwner", "string:org.kde.StatusNotifierWatcher"],
                    env=environment, capture_output=True, text=True, check=True)
                return "boolean true" in query.stdout
            wait_for(watcher_ready, timeout=7)
        tray_events = root / "tray-events.jsonl"
        if args.tray:
            start(
                [
                    sys.executable,
                    str(Path(__file__).with_name("desktop-bar-tray-fixture.py")),
                    str(tray_events),
                ],
                "tray",
            )
            wait_for(
                lambda: tray_events.is_file() and '"ready"' in tray_events.read_text()
            )
        input_process = start(
            [str(args.pointer.resolve())],
            "pointer",
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
        )
        assert reply(input_process) == "ready"
        # The nested parent's first configure may replace its initial mode.
        time.sleep(0.5)
        control(
            "eval",
            f'hl.monitor({{output="{monitor}",mode="1920x1080@60",position="0x0",scale=1}})',
        )
        time.sleep(0.3)
        output = json.loads(control("-j", "monitors"))[0]
        screen_width = round(output["width"] / output["scale"])
        screen_height = round(output["height"] / output["scale"])

        def send(command):
            input_process.stdin.write(command + "\n")
            input_process.stdin.flush()
            assert reply(input_process) == "ok"

        def move(x, y):
            send(f"absolute {round(x)} {round(y)} {screen_width} {screen_height}")

        def click():
            send("272 1")
            send("272 0")

        def panel(name):
            subprocess.run([str(args.binary.resolve()), "--panel", name], env=environment, check=True, timeout=5)

        def no_backdrop():
            return "desktop-bar-panel-" not in control("-j", "layers")

        def settled_height(height):
            frames = re.findall(r"bar-frame .* height=([\d.]+)", (root / "bar.log").read_text())
            return bool(frames) and abs(float(frames[-1]) - height) < 0.02

        if args.compact_only:
            assert args.hyprspace, "Compact acceptance requires the workspace namespace fixture"
            wait_for(lambda: "visible=[1, 5, 10]" in (root / "bar.log").read_text())
            move(screen_width / 2, screen_height / 2)
            core_width = 182 + 3 * 22
            body_left = (screen_width - core_width - (36 if args.tray else 0)) / 2
            capture("compact-resting")
            # Displayed 0 must still select workspace 10.
            move(body_left + 18 + 2 * 22 + 11, 16)
            click()
            wait_for(lambda: json.loads(control("-j", "monitors"))[0]["activeWorkspace"]["id"] == 10)
            move(screen_width / 2, screen_height / 2)
            time.sleep(0.4)
            capture("compact-workspace-zero")
            network_x = body_left + core_width - 64
            cases = [("volume-gap", network_x - 1, 190),
                     ("network-left", network_x, 200)]
            if any(path.read_text().strip() == "Battery" for path in Path("/sys/class/power_supply").glob("*/type")):
                cases += [("network-right-gap", network_x + 25, 200),
                          ("battery-left", network_x + 26, 160),
                          ("battery-padding", network_x + 56, 160)]
            for name, x, height in cases:
                for y in (0, 31):
                    panel("close")
                    wait_for(no_backdrop)
                    time.sleep(0.4)
                    move(x, y)
                    wait_for(lambda: not no_backdrop())
                    wait_for(lambda: settled_height(height))
                    capture(f"compact-{name}-{y}")
                    move(screen_width / 2 + 500, screen_height / 2)
                    wait_for(no_backdrop)
            print("Compact status gaps, full-height targets and workspace zero passed")
            return

        if args.keyboard_only:
            from types import SimpleNamespace
            from desktop_bar_keyboard import exercise
            def switch_style(name):
                settings["style"] = name
                theme.write_text(json.dumps(settings))
                os.kill(pid, signal.SIGUSR2)
                time.sleep(0.3)
            exercise(SimpleNamespace(
                root=root, binary=args.binary.resolve(), send=send, move=move,
                panel=panel, capture=capture, control=control, pixel=pixel,
                wait_for=wait_for, no_backdrop=no_backdrop, settled_height=settled_height,
                width=screen_width, height=screen_height,
                style=switch_style,
                start=start,
                fullscreen_client=args.pointer.resolve().with_name("test-capture-client"),
            ))
            print("Dashboard navigation, contextual help, immediate preview and shortcut passed")
            return

        if args.search_binary:
            def switch_style(name):
                settings["style"] = name
                theme.write_text(json.dumps(settings))
                os.kill(pid, signal.SIGUSR2)
                time.sleep(0.3)
            from types import SimpleNamespace
            from desktop_search_wayland import exercise
            result = exercise(SimpleNamespace(
                root=root, environment=environment, start=start, panel=panel,
                send=send, move=move, capture=capture, control=control,
                wait_for=wait_for, no_backdrop=no_backdrop, settled_height=settled_height,
                search=args.search_binary.resolve(), binary=args.binary.resolve(), bar=bar,
                style=switch_style,
                width=screen_width, height=screen_height,
            ))
            (root / "search-results.json").write_text(json.dumps(result, indent=2) + "\n")
            print(json.dumps(result))
            return

        def check_network_recovery():
            left = screen_width / 2 - (248 + (36 if args.tray else 0)) / 2
            def strength():
                return max(pixel(monitor, round(left + 200), 17))
            wait_for(lambda: strength() > 120)
            started = time.monotonic()
            presence = root / "wifi-presence.json"
            presence.write_text('{"available": false}')
            wait_for(lambda: strength() < 80, timeout=2)
            lost = round(time.monotonic() - started, 3)
            started = time.monotonic()
            presence.write_text('{"available": true}')
            wait_for(lambda: strength() > 120, timeout=2)
            restored = round(time.monotonic() - started, 3)
            capture("network-service-recovered")
            return {"lost_seconds": lost, "restored_seconds": restored}

        def check_media_recovery():
            previous_presence = (root / "media-state.json").read_text() if (root / "media-state.json").exists() else None
            (root / "media-state.json").write_text('{"available": true}')
            panel("controls")
            wait_for(lambda: settled_height(376))
            events = root / "media-actions.jsonl"
            original = events.read_text().count('"Next"') if events.exists() else 0
            flag = root / "stall-media"
            flag.touch()
            move(screen_width / 2 + 229, 296)
            click()
            (root / "media-title").write_text("Stalled Fixture Song")
            started = time.monotonic()
            wait_for((root / "stalled-media").exists)
            wait_for(lambda: settled_height(312), timeout=4.5)
            timeout = round(time.monotonic() - started, 3)
            flag.unlink()
            (root / "media-title").write_text("Recovered Fixture Song")
            wait_for(lambda: settled_height(376), timeout=2)
            started = time.monotonic()
            move(screen_width / 2 + 229, 296)
            click()
            wait_for(lambda: events.exists() and events.read_text().count('"Next"') > original, timeout=2)
            recovery = round(time.monotonic() - started, 3)
            capture("media-service-recovered")
            if previous_presence is not None:
                (root / "media-state.json").write_text(previous_presence)
                if not json.loads(previous_presence)["available"]:
                    wait_for(lambda: settled_height(312))
            panel("close")
            move(screen_width / 2, screen_height / 2)
            wait_for(no_backdrop)
            return {"stalled_read_seconds": timeout, "playback_recovery_seconds": recovery}

        def check_cover_recovery():
            previous_presence = (root / "media-state.json").read_text() if (root / "media-state.json").exists() else None
            (root / "media-state.json").write_text('{"available": true}')
            panel("controls")
            wait_for(lambda: settled_height(376))
            flag = root / "stall-cover"
            flag.touch()
            (root / "media-cover").write_text("file:///obsolete-cover")
            (root / "media-title").write_text("Obsolete cover")
            marker = root / "stalled-cover-pid"
            wait_for(marker.exists)
            flag.unlink()
            started = time.monotonic()
            (root / "media-cover").write_text("file:///current-cover")
            (root / "media-title").write_text("Current cover")
            def current_cover():
                red, _, blue = pixel(monitor, screen_width // 2 - 232, 296)
                return abs(red - 160) <= 2 and abs(blue - 180) <= 2
            wait_for(current_cover, timeout=1.5)
            elapsed = round(time.monotonic() - started, 3)
            wait_for(lambda: not Path("/proc/" + marker.read_text()).exists())
            capture("cover-service-recovered")
            panel("close")
            move(screen_width / 2, screen_height / 2)
            wait_for(no_backdrop)
            if previous_presence is not None:
                (root / "media-state.json").write_text(previous_presence)
            (root / "media-cover").unlink()
            (root / "media-title").unlink()
            return {"current_artwork_seconds": elapsed}

        def check_dynamic_morph():
            assert args.hyprspace, "Morph state checks require the private namespace fixture"
            measured = {}
            for count, during_close in ((10, False), (3, True)):
                panel("apps")
                wait_for(lambda: settled_height(352))
                if during_close:
                    panel("close")
                occupancy = root / "workspace-occupancy.json"
                numbers = list(range(1, 11)) if count == 10 else [1, 5, 10]
                occupancy.write_text(json.dumps([
                    {"number": n, "native_id": n, "monitor": monitor, "occupied": True, "special": False}
                    for n in numbers
                ]))
                offset = len((root / "bar.log").read_text())
                target = "5" if count == 10 else "10"
                control("eval", f'hl.dispatch(hl.dsp.focus({{workspace="{target}"}}))')
                wait_for(lambda: f"visible={numbers}" in (root / "bar.log").read_text()[offset:])
                if not during_close:
                    panel("close")
                wait_for(no_backdrop)
                capture("morph-current-" + str(count))
                actual = float(re.findall(r"bar-frame .* width=([\d.]+)", (root / "bar.log").read_text())[-1])
                # An unchanged reopen gives the current compact endpoint independently
                # of the update path exercised above.
                panel("apps")
                wait_for(lambda: settled_height(352))
                panel("close")
                wait_for(no_backdrop)
                expected = float(re.findall(r"bar-frame .* width=([\d.]+)", (root / "bar.log").read_text())[-1])
                measured[str(count)] = {"updated_endpoint": actual, "reopen_endpoint": expected}
                assert abs(actual - expected) < 0.1, f"Closing used stale notch geometry: {measured}"
                occupancy.unlink()
            if args.tray:
                for status in ("Passive", "Active"):
                    panel("apps")
                    wait_for(lambda: settled_height(352))
                    status_offset = len(tray_events.read_text())
                    (root / "tray-status").write_text(status)
                    wait_for(lambda: {"action": "StatusRead", "status": status} in [
                        json.loads(line) for line in tray_events.read_text()[status_offset:].splitlines()
                    ])
                    time.sleep(0.1)
                    panel("close")
                    wait_for(no_backdrop)
                    actual = float(re.findall(r"bar-frame .* width=([\d.]+)", (root / "bar.log").read_text())[-1])
                    panel("apps")
                    wait_for(lambda: settled_height(352))
                    panel("close")
                    wait_for(no_backdrop)
                    expected = float(re.findall(r"bar-frame .* width=([\d.]+)", (root / "bar.log").read_text())[-1])
                    measured["tray-" + status] = {"updated_endpoint": actual, "reopen_endpoint": expected}
                    assert abs(actual - expected) < 0.1, f"Closing used stale tray geometry: {measured}"
            return measured

        move(screen_width / 2, screen_height / 2)
        time.sleep(0.5)
        startup = False
        if args.cover_recovery_only:
            result = check_cover_recovery()
            (root / "cover-recovery.json").write_text(json.dumps(result, indent=2))
            print(json.dumps(result))
            return
        if args.delayed_session_bus:
            panel("controls")
            wait_for(lambda: settled_height(376))
            capture("delayed-bus-recovered")
            def bus_resources():
                return {name: len(list(Path(f"/proc/{pid}/{name}").iterdir())) for name in ("fd", "task")}
            before = bus_resources()
            (root / "drop-session-bus").touch()
            wait_for(lambda: not watcher_ready(), timeout=2)
            wait_for(lambda: settled_height(312), timeout=2)
            (root / "drop-session-bus").unlink()
            wait_for(watcher_ready, timeout=7)
            wait_for(lambda: '"Reregistered"' in tray_events.read_text(), timeout=2)
            wait_for(lambda: settled_height(376), timeout=7)
            after = wait_for(lambda: bus_resources() if all(
                value <= before[name] + 2 for name, value in bus_resources().items()
            ) else None, timeout=5)
            result = {"tray_recovered": True, "media_recovered": True,
                      "tray_restart_recovered": True, "media_restart_recovered": True,
                      "resources_before": before, "resources_after": after}
            (root / "session-bus-recovery.json").write_text(json.dumps(result, indent=2))
            print(json.dumps(result))
            return
        if args.media_recovery_only:
            result = check_media_recovery()
            (root / "media-recovery.json").write_text(json.dumps(result, indent=2))
            print(json.dumps(result))
            return
        if args.network_recovery_only:
            result = check_network_recovery()
            (root / "network-recovery.json").write_text(json.dumps(result, indent=2))
            print(json.dumps(result))
            return
        if args.bus_load_only:
            panel("apps")
            time.sleep(1.2)
            def bus_activity():
                stat = Path(f"/proc/{pid}/stat").read_text().rsplit(") ", 1)[1].split()
                return {
                    "cpu_seconds": (int(stat[11]) + int(stat[12])) / os.sysconf("SC_CLK_TCK"),
                    "damage_calls": (root / "bar.log").read_text().count(".damage_buffer("),
                    **json.loads((root / "bus-stats.json").read_text()),
                }
            results = {}
            for name in ("quiet", "noise", "position", "controls-quiet", "controls-noise", "controls-position"):
                if name == "controls-quiet":
                    panel("controls")
                    time.sleep(1.2)
                (root / "bus-load").write_text(name.removeprefix("controls-"))
                time.sleep(0.3)
                before = bus_activity()
                time.sleep(args.idle_seconds)
                assert bar.poll() is None, (root / "bar.log").read_text()
                after = bus_activity()
                results[name] = {key: round(after[key] - before[key], 4) for key in before}
                results[name]["seconds"] = args.idle_seconds
            (root / "bus-load").unlink()
            (root / "bus-load.json").write_text(json.dumps(results, indent=2))
            print(json.dumps(results))
            if args.check_bus_load:
                assert results["position"]["position_sent"] > args.idle_seconds * 10
                assert results["position"]["media_reads"] == 0, "Position updates refetched invisible metadata"
                assert all(results[name]["damage_calls"] == 0 for name in ("quiet", "noise", "position")), "Bus traffic repainted static Apps"
                assert results["controls-position"]["media_reads"] == 0, "Position changes refetched dashboard metadata"
                assert results["controls-position"]["damage_calls"] < results["controls-position"]["position_sent"] / 10, "Position changes repainted the dashboard"
            return
        if args.morph_state_only:
            result = check_dynamic_morph()
            (root / "morph-state.json").write_text(json.dumps(result, indent=2))
            print(json.dumps(result))
            return
        if args.profile_only:
            def activity():
                stat = Path(f"/proc/{pid}/stat").read_text().rsplit(") ", 1)[1].split()
                return {
                    "cpu_seconds": (int(stat[11]) + int(stat[12])) / os.sysconf("SC_CLK_TCK"),
                    "damage_calls": (root / "bar.log").read_text().count(".damage_buffer("),
                }

            results = {}
            for name in ("notch", "apps", "controls"):
                if name != "notch":
                    subprocess.run([str(args.binary.resolve()), "--panel", name], env=environment, check=True, timeout=5)
                time.sleep(1.2)
                capture("profile-" + name)
                before = activity()
                for _ in range(args.idle_seconds):
                    time.sleep(1)
                    assert bar.poll() is None, (root / "bar.log").read_text()
                after = activity()
                results[name] = {key: round(after[key] - before[key], 4) for key in before}
                results[name]["seconds"] = args.idle_seconds
                results[name]["memory_kib"] = memory(pid)
            (root / "profile.json").write_text(json.dumps(results, indent=2) + "\n")
            print(json.dumps(results))
            if args.check_idle:
                # Battery and minute changes can legitimately redraw the notch.
                status_budget = (args.idle_seconds + 9) // 10 + (args.idle_seconds + 59) // 60 + 1
                assert results["notch"]["damage_calls"] <= status_budget, "Hidden metrics repainted the compact notch"
                assert results["apps"]["damage_calls"] == 0, "Background data repainted the static application menu"
                assert results["controls"]["damage_calls"] > 0, "Visible dashboard metrics stopped refreshing"
            return
        capture("clean-initial")
        if args.tray:
            def open_tray_menu(x=screen_width - 31, y=33):
                before = tray_events.read_text().count('"action": "AboutToShow"')
                move(x, y)
                send("273 1")
                send("273 0")
                wait_for(
                    lambda: tray_events.read_text().count('"action": "AboutToShow"')
                    > before
                )
                time.sleep(0.4)

            # A compositor-dismissed popup receives no further frame callbacks.
            # Reopening must work after outside clicks as well as Escape.
            for dismissal in ("outside", "escape", "outside"):
                open_tray_menu()
                if dismissal == "escape":
                    send("key 1 1")
                    send("key 1 0")
                else:
                    move(screen_width / 2, screen_height / 2)
                    click()
                time.sleep(0.4)

            open_tray_menu()
            capture("tray-menu")
            move(screen_width - 160, 81)
            click()
            wait_for(lambda: '"id": 7' in tray_events.read_text())
            time.sleep(0.4)
            move(screen_width - 31, 33)
            send("273 1")
            send("273 0")
            time.sleep(0.5)
            move(screen_width - 160, 165)
            click()
            time.sleep(0.5)
            capture("tray-submenu")
            move(screen_width - 160, 81)
            click()
            wait_for(lambda: '"id": 21' in tray_events.read_text())
            events = [json.loads(line) for line in tray_events.read_text().splitlines()]
            assert (
                len([event for event in events if event["action"] == "AboutToShow"])
                == 6
            )
            assert all(
                event["time"] > 0 for event in events if event["action"] == "Event"
            )
            time.sleep(0.4)
        move(screen_width / 2, 33)
        (root / "pointer-position.json").write_text(control("-j", "cursorpos"))
        click()
        (root / "monitors-click.json").write_text(control("-j", "monitors"))
        wait_for(
            lambda: (
                json.loads(control("-j", "monitors"))[0]["activeWorkspace"]["id"] == 5
            )
        )
        capture("workspace-moving")
        time.sleep(0.4)
        capture("workspace-settled")
        if args.hyprspace:
            assert '"workspace":"5"' in (root / "namespace.log").read_text()
            # The last label is 0, but its destination remains workspace 10.
            move(screen_width / 2 + 30, 33)
            click()
            wait_for(
                lambda: (
                    json.loads(control("-j", "monitors"))[0]["activeWorkspace"]["id"]
                    == 10
                )
            )
            time.sleep(0.4)
            capture("workspace-zero")
            move(screen_width / 2, 33)
            click()
            wait_for(
                lambda: (
                    json.loads(control("-j", "monitors"))[0]["activeWorkspace"]["id"]
                    == 5
                )
            )
            send("axis 0 -15 -1 0")
            wait_for(
                lambda: (
                    json.loads(control("-j", "monitors"))[0]["activeWorkspace"]["id"]
                    == 1
                )
            )
            assert '"workspace":"e-1"' in (root / "namespace.log").read_text()
            time.sleep(0.4)
            capture("workspace-scrolled")
        move(90, 32)
        time.sleep(0.4)
        capture("hover")
        settings["style"] = "native-motion"
        theme.write_text(json.dumps(settings))
        os.kill(pid, signal.SIGUSR2)
        time.sleep(0.5)
        capture("motion-initial")
        tray_width = 36 if args.tray else 0
        core_left = screen_width / 2 - (256 + tray_width) / 2
        move(core_left + 51, 18)
        click()
        wait_for(lambda: json.loads(control("-j", "monitors"))[0]["activeWorkspace"]["id"] == 5)
        move(core_left + 73, 18)
        click()
        wait_for(lambda: json.loads(control("-j", "monitors"))[0]["activeWorkspace"]["id"] == 10)
        move(screen_width / 2, screen_height / 2)
        time.sleep(0.5)
        capture("motion")
        if args.hyprspace:
            occupancy = root / "workspace-occupancy.json"
            occupancy.write_text(json.dumps([
                {"number": n, "native_id": n, "monitor": monitor, "occupied": True, "special": False}
                for n in range(1, 11)
            ]))
            control("eval", 'hl.dispatch(hl.dsp.focus({workspace="5"}))')
            wait_for(lambda: "visible=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]" in (root / "bar.log").read_text())
            time.sleep(0.5)
            capture("motion-many-workspaces")
            occupancy.unlink()
            offset = len((root / "bar.log").read_text())
            control("eval", 'hl.dispatch(hl.dsp.focus({workspace="10"}))')
            wait_for(lambda: "visible=[1, 5, 10]" in (root / "bar.log").read_text()[offset:])
            time.sleep(0.4)

        morph_state = check_dynamic_morph() if args.hyprspace else {}
        network_recovery = check_network_recovery() if args.hyprspace else {}

        if args.tray:
            open_tray_menu(core_left + 268, 18)
            capture("motion-tray")
            assert pixel(monitor, screen_width // 2, 2) == (0, 0, 0)
            panel("close")
            wait_for(no_backdrop)

        (root / "media-state.json").write_text(json.dumps({"available": False}))
        time.sleep(0.3)
        for name, x, height in (("controls", core_left + 128, 312),
                                ("volume", core_left + 181, 190),
                                ("network", core_left + 204, 200)):
            move(screen_width / 2, screen_height / 2)
            wait_for(no_backdrop)
            time.sleep(0.4)
            move(x, 30)
            wait_for(lambda: not no_backdrop())
            wait_for(lambda: settled_height(height))
            capture("hover-" + name)
            assert pixel(monitor, screen_width // 2, 2) == (0, 0, 0), "Status hover detached its notch"
            move(screen_width / 2 + 500, screen_height / 2)
            wait_for(no_backdrop)

        # Restore nested parents and selection without rebuilding the surface.
        panel("controls")
        wait_for(lambda: settled_height(312))
        before = control("-j", "layers")
        move(screen_width / 2 + 193, 90)
        click()
        wait_for(lambda: settled_height(382))
        capture("nested-audio")
        send("key 1 1")
        send("key 1 0")
        wait_for(lambda: settled_height(312))
        capture("nested-audio-back")
        send("key 28 1")
        send("key 28 0")
        wait_for(lambda: settled_height(382))
        send("key 1 1")
        send("key 1 0")
        wait_for(lambda: settled_height(312))
        send("key 102 1")
        send("key 102 0")
        time.sleep(0.12)
        first_tile = pixel(monitor, screen_width // 2 - 250, 70)
        send("key 29 1")
        send("key 32 1")  # Ctrl+D moves half a grid page.
        send("key 32 0")
        send("key 29 0")
        wait_for(lambda: pixel(monitor, screen_width // 2 - 250, 70) != first_tile)
        capture("controls-half-page-down")
        send("key 29 1")
        send("key 22 1")  # Ctrl+U returns to the first tile.
        send("key 22 0")
        send("key 29 0")
        wait_for(lambda: pixel(monitor, screen_width // 2 - 250, 70) == first_tile)
        move(screen_width / 2 - 65, 225)  # Network tile.
        click()
        wait_for(lambda: settled_height(200))
        move(screen_width / 2, 149)  # Complete Wi-Fi settings.
        click()
        wait_for(lambda: settled_height(352))
        send("key 1 1")
        send("key 1 0")
        wait_for(lambda: settled_height(200))
        send("key 1 1")
        send("key 1 0")
        wait_for(lambda: settled_height(312))
        assert control("-j", "layers") == before, "Back navigation recreated the surface"
        move(screen_width / 2 + 193, 90)
        click()
        wait_for(lambda: settled_height(382))
        for _ in range(2):
            send("key 1 1")
            send("key 1 0")
        move(screen_width / 2 + 500, screen_height / 2)
        wait_for(no_backdrop)

        panel("menu/main")
        wait_for(lambda: settled_height(352))
        time.sleep(0.15)
        send("key 108 1")  # Main -> Style.
        send("key 108 0")
        send("key 28 1")
        send("key 28 0")
        time.sleep(0.3)
        send("key 108 1")  # Style -> Back.
        send("key 108 0")
        send("key 28 1")
        send("key 28 0")
        time.sleep(0.3)
        send("key 1 1")
        send("key 1 0")
        wait_for(no_backdrop)
        move(screen_width / 2 + 500, screen_height / 2)
        time.sleep(0.4)
        move(screen_width / 2, 18)
        wait_for(lambda: not no_backdrop())
        wait_for(lambda: settled_height(312))
        capture("controls-idle")
        before = control("-j", "layers")
        (root / "media-state.json").write_text(json.dumps({"available": True}))
        wait_for(lambda: settled_height(376))
        capture("controls-media")
        assert control("-j", "layers") == before, "Music appearing recreated the notch surface"
        move(screen_width / 2 + 199, 296)
        click()
        media_events = root / "media-actions.jsonl"
        wait_for(lambda: media_events.exists() and '"PlayPause"' in media_events.read_text())
        move(screen_width / 2 + 229, 296)
        click()
        wait_for(lambda: '"Next"' in media_events.read_text())
        time.sleep(0.2)
        capture("media-next")
        (root / "media-state.json").write_text(json.dumps({"available": False}))
        wait_for(lambda: settled_height(312))
        capture("controls-media-closed")
        assert control("-j", "layers") == before, "Music disappearing recreated the notch surface"
        move(screen_width / 2 + 193, 28)  # Clipboard tab in Controls.
        click()
        wait_for(lambda: settled_height(464))
        assert control("-j", "layers") == before, "Overview navigation recreated the notch surface"
        panel("close")
        move(screen_width / 2 + 500, screen_height / 2)
        wait_for(no_backdrop)
        for name in ("keybindings", "notifications", "bluetooth", "wifi"):
            panel(name)
            time.sleep(0.6)
            wait_for(lambda: settled_height(352))
            capture("native-" + name)
            if name == "notifications":
                send("key 28 1")
                send("key 28 0")
                event_log = root / "notification-actions.jsonl"
                wait_for(lambda: event_log.exists() and '[42, "default"]' in event_log.read_text())
            if name == "bluetooth":
                send("key 29 1")
                send("key 36 1")  # Ctrl+J
                send("key 36 0")
                send("key 36 1")
                send("key 36 0")
                send("key 29 0")
                send("key 28 1")
                send("key 28 0")
                event_log = root / "bluetooth-actions.jsonl"
                wait_for(lambda: event_log.exists() and '"connect"' in event_log.read_text())
                wait_for(lambda: settled_height(352))
                time.sleep(0.15)
                send("key 29 1")
                send("key 36 1")
                send("key 36 0")
                send("key 29 0")
                send("key 28 1")
                send("key 28 0")
                wait_for(lambda: settled_height(166))
                capture("native-pairing")
                send("key 28 1")
                send("key 28 0")
                wait_for(lambda: '"paired"' in event_log.read_text())
                wait_for(lambda: settled_height(352))
            if name == "wifi":
                send("key 29 1")
                for _ in range(3):
                    send("key 36 1")
                    send("key 36 0")
                send("key 29 0")
                send("key 28 1")
                send("key 28 0")
                wait_for(lambda: settled_height(166))
                before = control("-j", "layers")
                for key in (20, 18, 31, 20):  # test password in a private bus fixture.
                    send(f"key {key} 1")
                    send(f"key {key} 0")
                time.sleep(0.15)
                capture("native-password")
                send("key 28 1")
                send("key 28 0")
                event_log = root / "wifi-actions.jsonl"
                wait_for(lambda: event_log.exists() and '"accepted": true' in event_log.read_text())
                wait_for(lambda: settled_height(352))
                assert control("-j", "layers") == before
                send("key 28 1")
                send("key 28 0")
                wait_for(lambda: settled_height(166))
                send("key 1 1")
                send("key 1 0")
                wait_for(lambda: '"cancelled": true' in event_log.read_text())
                wait_for(lambda: settled_height(352))
            panel("close")
            wait_for(no_backdrop)
        media_recovery = check_media_recovery()
        cover_recovery = check_cover_recovery()
        for _ in range(2):
            move(screen_width / 2, 18)
            wait_for(lambda: not no_backdrop())
            time.sleep(0.1)
            move(screen_width / 2 + 500, screen_height / 2)
            time.sleep(0.18)
            move(screen_width / 2, 18)
            time.sleep(0.2)
            assert not no_backdrop()
            move(screen_width / 2 + 500, screen_height / 2)
            wait_for(no_backdrop)
        panel("calendar")
        time.sleep(0.1)
        capture("notch-growing")
        time.sleep(0.5)
        assert "desktop-bar-panel-" in control("-j", "layers")
        capture("calendar")
        send("key 1 1")
        send("key 1 0")
        wait_for(no_backdrop)
        capture("escaped")
        # A keyboard-triggered panel must survive reopening while the previous
        # shape is still collapsing and the pointer remains outside.
        panel("volume")
        time.sleep(0.1)
        panel("close")
        time.sleep(0.06)
        panel("calendar")
        time.sleep(0.6)
        assert not no_backdrop(), "Keyboard reopening inherited stale hover state"
        panel("close")
        wait_for(no_backdrop)
        panel("volume")
        time.sleep(0.6)
        capture("sound")
        move(screen_width / 2 - 100, 75)
        send("axis 0 -15 -1 0")
        move(screen_width / 2 - 100, 130)
        send("axis 0 15 1 0")
        audio_actions = root / "audio-actions.jsonl"
        wait_for(lambda: audio_actions.exists() and audio_actions.read_text().count("set-volume") == 2)
        assert [json.loads(line) for line in audio_actions.read_text().splitlines()] == [
            ["set-volume", "@DEFAULT_SINK@", "10%+"], ["set-volume", "@DEFAULT_SOURCE@", "5%-"]]
        send("key 1 1")
        send("key 1 0")
        wait_for(no_backdrop)
        panel("calendar")
        time.sleep(0.5)
        move(screen_width / 2, screen_height / 2)
        click()
        wait_for(no_backdrop)
        capture("outside-close")
        panel("styles")
        time.sleep(0.5)
        capture("style-picker")
        # Tab changes providers without destroying/recreating the focus owner.
        before = control("-j", "layers")
        send("key 15 1")
        send("key 15 0")
        time.sleep(0.5)
        assert control("-j", "layers") == before
        capture("launcher")
        # Reopening uses the warmed entries even if a new scan would stall.
        application_requests = root / "application-requests.jsonl"
        requests_before = application_requests.read_text().splitlines()
        (root / "stall-catalog-apps").touch()
        application_reopens = []
        def application_icon_visible():
            red, _, blue = pixel(monitor, screen_width // 2 - 196, 80)
            return abs(red - 40) <= 2 and abs(blue - 120) <= 2
        for _ in range(3):
            panel("close")
            wait_for(no_backdrop)
            started = time.monotonic()
            panel("apps")
            wait_for(application_icon_visible)
            application_reopens.append(round(time.monotonic() - started, 3))
        (root / "stall-catalog-apps").unlink()
        assert max(application_reopens) < 0.6, "Reopening Apps waited for another scan"
        assert application_requests.read_text().splitlines() == requests_before
        for key in (44, 18, 48, 19, 30):  # zebra
            send(f"key {key} 1")
            send(f"key {key} 0")
        time.sleep(0.6)
        capture("launcher-search")
        send("key 28 1")
        send("key 28 0")
        actions = root / "shell-actions.jsonl"
        wait_for(lambda: actions.is_file() and "Zebra Terminal.desktop" in actions.read_text())
        wait_for(no_backdrop)
        (root / "thumbnail-requests.jsonl").unlink(missing_ok=True)
        panel("themes")
        time.sleep(0.6)
        capture("theme-picker")
        before = control("-j", "layers")
        panel("wallpapers")
        time.sleep(0.2)
        # Thumbnail decoding deliberately pauses in the fixture. Rapid gallery
        # navigation must skip obsolete work and still display the current image.
        for key in (106, 105) * 6 + (106, 106):
            send(f"key {key} 1")
            send(f"key {key} 0")
        preview_started = time.monotonic()
        def selected_preview_visible():
            red, _, blue = pixel(monitor, screen_width // 2, 100)
            return abs(red - 160) <= 2 and abs(blue - 180) <= 2
        wait_for(selected_preview_visible)
        preview_latency = time.monotonic() - preview_started
        assert preview_latency < 2.5, "Outdated thumbnail jobs delayed the selected preview"
        def neighboring_preview_visible():
            red, _, blue = pixel(monitor, screen_width // 2 - 180, 100)
            return abs(red - 120) <= 2 and abs(blue - 160) <= 2
        wait_for(neighboring_preview_visible)
        assert control("-j", "layers") == before
        capture("wallpaper-picker")
        thumbnails = root / "thumbnail-requests.jsonl"
        wait_for(lambda: thumbnails.is_file() and thumbnails.read_text().strip())
        assert str(root / "wallpaper-3.png") in map(json.loads, thumbnails.read_text().splitlines())
        move(screen_width / 2, 100)
        send("axis 0 0 0 1")
        for _ in range(8):
            send("axis 0 -4 0 1")
        time.sleep(0.35)
        assert selected_preview_visible(), "Tiny deltas or a stop frame jumped the gallery"
        send("axis 0 -4 0 1")
        def scrolled_preview_visible():
            red, _, blue = pixel(monitor, screen_width // 2, 100)
            return abs(red - 120) <= 2 and abs(blue - 160) <= 2
        wait_for(scrolled_preview_visible)
        capture("gallery-scrolled")
        send("key 106 1")
        send("key 106 0")
        wait_for(selected_preview_visible)
        send("key 105 1")  # previous wallpaper
        send("key 105 0")
        send("key 28 1")
        send("key 28 0")
        wait_for(lambda: '"wallpaper", "set"' in actions.read_text())
        wait_for(no_backdrop)

        recoveries = {}
        for provider, flag_name, marker_name in (
            ("themes", "stall-catalog-themes", "stalled-catalog-pid"),
            ("wallpapers", "stall-thumbnail", "stalled-thumbnail-pid"),
        ):
            flag = root / flag_name
            flag.touch()
            marker = root / marker_name
            panel(provider)
            wait_for(marker.exists)
            started = time.monotonic()
            panel("apps")

            wait_for(application_icon_visible)
            recoveries[provider] = round(time.monotonic() - started, 3)
            assert recoveries[provider] < 1.5, "A stale helper blocked the next menu"
            wait_for(lambda: not Path("/proc/" + marker.read_text()).exists())
            capture("recovered-" + provider)
            flag.unlink()
            panel("close")
            wait_for(no_backdrop)

        native_deadlines = {}
        def resources():
            return {name: len(list(Path(f"/proc/{pid}/{name}").iterdir())) for name in ("fd", "task")}
        native_resources_before = resources()
        for provider in ("notifications", "bluetooth", "wifi"):
            flag = root / ("stall-native-" + provider)
            flag.touch()
            marker = root / ("stalled-native-" + provider)
            panel(provider)
            wait_for(marker.exists)
            started = time.monotonic()
            panel("apps")
            wait_for(application_icon_visible)
            recoveries["native-" + provider] = round(time.monotonic() - started, 3)
            assert recoveries["native-" + provider] < 1.5, "A native service blocked the next menu"
            started = time.monotonic()
            query = subprocess.run([str(args.binary.resolve()), "--catalog", provider], env=environment,
                                   capture_output=True, text=True, timeout=5)
            native_deadlines[provider] = round(time.monotonic() - started, 3)
            assert query.returncode != 0 and "Desktop service did not respond" in query.stderr
            assert 2.9 <= native_deadlines[provider] < 4.5, "A native catalog exceeded its total deadline"
            flag.unlink()
            query = subprocess.run([str(args.binary.resolve()), "--catalog", provider], env=environment,
                                   capture_output=True, text=True, check=True, timeout=5)
            assert json.loads(query.stdout), "The native catalog did not recover after the service resumed"
            panel("close")
            wait_for(no_backdrop)

        time.sleep(0.5)
        native_resources_after = resources()
        assert all(native_resources_after[name] <= count + 2 for name, count in native_resources_before.items()), "Cancelled native reads leaked connections or threads"

        # A connected Pulse socket that never completes authentication must not
        # trap either native audio discovery or the following menu request.
        pulse_socket = socket.socket(socket.AF_UNIX)
        pulse_socket.bind(str(root / "no-pulse"))
        pulse_socket.listen(8)
        pulse_socket.settimeout(0.1)
        pulse_stop = threading.Event()
        pulse_connections = []
        def accept_pulse():
            while not pulse_stop.is_set():
                try:
                    connection, _ = pulse_socket.accept()
                    pulse_connections.append(connection)
                except socket.timeout:
                    pass
                except OSError:
                    break
        pulse_thread = threading.Thread(target=accept_pulse, daemon=True)
        pulse_thread.start()
        try:
            panel("audio")
            wait_for(lambda: bool(pulse_connections))
            time.sleep(0.2)
            started = time.monotonic()
            panel("apps")
            wait_for(application_icon_visible)
            recoveries["native-audio"] = round(time.monotonic() - started, 3)
            assert recoveries["native-audio"] < 1.5, "A stalled audio connection blocked the next menu"
            started = time.monotonic()
            query = subprocess.run([str(args.binary.resolve()), "--catalog", "audio"], env=environment,
                                   capture_output=True, text=True, timeout=5)
            native_deadlines["audio"] = round(time.monotonic() - started, 3)
            assert query.returncode != 0 and "Audio service did not respond" in query.stderr
            assert 2.9 <= native_deadlines["audio"] < 4.5
        finally:
            pulse_stop.set()
            pulse_socket.close()
            pulse_thread.join(timeout=1)
            for connection in pulse_connections:
                connection.close()
            (root / "no-pulse").unlink(missing_ok=True)
        panel("close")
        wait_for(no_backdrop)

        panel("clipboard")
        clipboard_log = root / "clipboard-requests.jsonl"
        wait_for(lambda: clipboard_log.exists() and clipboard_log.read_text().strip())
        wait_for(lambda: settled_height(464))
        time.sleep(0.5)
        capture("clipboard")
        for grid_focus in (False, True):
            if not grid_focus:
                send("key 53 1")  # Enter search explicitly.
                send("key 53 0")
            send("key 15 1")  # Plain Tab always advances to the Controls panel.
            send("key 15 0")
            wait_for(lambda: settled_height(312) or settled_height(376))
            send("key 42 1")  # Shift+Tab returns to Clipboard.
            send("key 15 1")
            send("key 15 0")
            send("key 42 0")
            wait_for(lambda: settled_height(464))
        # Only synthetic content enters the private compositor's clipboard.
        send("key 57 1")  # select first text
        send("key 57 0")
        for _ in range(2):
            send("key 106 1")
            send("key 106 0")
        send("key 57 1")
        send("key 57 0")
        time.sleep(0.2)
        capture("clipboard-selected")
        send("key 29 1")  # Ctrl+Enter copies the ordered text selection
        send("key 28 1")
        send("key 28 0")
        send("key 29 0")
        wait_for(no_backdrop)
        copied = subprocess.check_output(["wl-paste", "--no-newline"], env=environment, timeout=5).decode()
        assert copied == "\n".join(f"Clipboard fixture {index}\nLiteral text with symbols: <tag> & /path" for index in (0, 2))

        panel("clipboard")
        time.sleep(0.5)
        send("key 29 1")  # Ctrl+Shift+Tab wraps All -> Text without leaving Clipboard.
        send("key 42 1")
        send("key 15 1")
        send("key 15 0")
        send("key 42 0")
        send("key 29 0")
        time.sleep(0.2)
        capture("clipboard-text")
        send("key 29 1")  # Ctrl+Tab: Text -> All -> Images.
        for _ in range(2):
            send("key 15 1")
            send("key 15 0")
        send("key 29 0")
        time.sleep(0.4)
        capture("clipboard-images")
        send("key 29 1")  # Ctrl+Space: image preview
        send("key 57 1")
        send("key 57 0")
        send("key 29 0")
        time.sleep(0.3)
        capture("clipboard-preview")
        send("key 1 1")
        send("key 1 0")
        send("key 29 1")  # Ctrl+Tab: next category, Text.
        send("key 15 1")
        send("key 15 0")
        send("key 29 0")
        send("key 106 1")
        send("key 106 0")
        send("key 29 1")  # pin the focused text, retaining focus after sorting
        send("key 25 1")
        send("key 25 0")
        send("key 29 0")
        wait_for(lambda: '"action": "pin"' in clipboard_log.read_text())
        time.sleep(0.2)
        send("key 29 1")
        send("key 25 1")
        send("key 25 0")
        send("key 29 0")
        wait_for(lambda: '"action": "unpin"' in clipboard_log.read_text())
        time.sleep(0.2)
        send("key 111 1")  # remove the now unpinned item
        send("key 111 0")
        wait_for(lambda: '"action": "remove"' in clipboard_log.read_text())
        panel("close")
        wait_for(no_backdrop)
        panel("styles")
        time.sleep(0.5)
        send("key 105 1")  # left: Clean
        send("key 105 0")
        send("key 28 1")
        send("key 28 0")
        wait_for(lambda: json.loads(theme.read_text())["style"] == "native-clean")
        wait_for(no_backdrop)
        assert bar.poll() is None
        capture("style-switched")
        panel("styles")
        time.sleep(0.5)
        send("key 106 1")  # right: Motion
        send("key 106 0")
        send("key 28 1")
        send("key 28 0")
        wait_for(lambda: json.loads(theme.read_text())["style"] == "native-motion")
        wait_for(no_backdrop)
        panel("controls")
        time.sleep(0.6)
        capture("controls")
        before = control("-j", "layers")
        panel("menu/system")
        time.sleep(0.6)
        assert control("-j", "layers") == before
        capture("native-desktop-menu")
        panel("close")
        wait_for(no_backdrop)
        # A vertically offset second monitor must own its notch origin, local
        # destinations and popup input, including keyboard-triggered panels.
        original_outputs = {m["name"] for m in json.loads(control("-j", "monitors"))}
        control("output", "create", "headless")
        second = wait_for(lambda: next((m["name"] for m in json.loads(control("-j", "monitors")) if m["name"] not in original_outputs), None))
        control("eval", f'hl.monitor({{output={json.dumps(second)},mode="1280x720@60",position="160x1080",scale=1}})')
        settings["style"] = "native-motion"
        settings["outputs"] = {"full": [monitor, second], "minimal": []}
        theme.write_text(json.dumps(settings))
        os.kill(pid, signal.SIGUSR2)
        wait_for(lambda: "desktop-bar-" + second in control("-j", "layers"))
        control("eval", f'hl.dispatch(hl.dsp.focus({{monitor={json.dumps(second)}}}))')
        time.sleep(0.5)
        capture("offset-monitor-closed", second)
        panel("controls")
        wait_for(lambda: "desktop-bar-panel-" + second in control("-j", "layers"))
        time.sleep(0.7)
        capture("offset-monitor-open", second)
        assert pixel(second, 640, 2) == (0, 0, 0)
        assert pixel(second, 636, 180) == (0, 0, 0)
        panel("close")
        wait_for(no_backdrop)
        control("output", "remove", second)
        control("eval", f'hl.dispatch(hl.dsp.focus({{monitor={json.dumps(monitor)}}}))')
        settings["outputs"] = {"full": [monitor], "minimal": []}
        settings["style"] = "native-clean"
        theme.write_text(json.dumps(settings))
        os.kill(pid, signal.SIGUSR2)
        time.sleep(0.5)
        assert bar.poll() is None, (root / "bar.log").read_text()
        capture("clean")
        control(
            "eval",
            f'hl.monitor({{output="{monitor}",mode="preferred",position="0x0",scale=1.2}})',
        )
        time.sleep(0.5)
        capture("fractional")
        control(
            "eval",
            f'hl.monitor({{output="{monitor}",mode="1920x1080@60",position="0x0",scale=1}})',
        )
        time.sleep(0.5)
        # Minimal output selection must replace the full bar in the same process.
        settings["outputs"] = {"full": [], "minimal": [monitor]}
        theme.write_text(json.dumps(settings))
        os.kill(pid, signal.SIGUSR2)
        time.sleep(0.5)
        capture("minimal")
        settings["outputs"] = {"full": [monitor], "minimal": []}
        settings["style"] = "native-motion"
        theme.write_text(json.dumps(settings))
        os.kill(pid, signal.SIGUSR2)
        started = time.monotonic()
        samples = []
        while time.monotonic() - started < args.idle_seconds:
            assert bar.poll() is None, (root / "bar.log").read_text()
            samples.append(memory(pid))
            time.sleep(1)
        stop_sampling.set()
        sampler.join(timeout=1)
        result = {
            "pid": pid,
            "idle_seconds": args.idle_seconds,
            "memory_kib": samples[-1] if samples else {},
            "idle_peak_kib": {
                key: max(s[key] for s in samples) for key in ("Rss", "Pss")
            }
            if samples
            else {},
            "startup_and_animation_peak_kib": peak,
            "startup_peak_kib": startup_peak,
            "logical_size": [screen_width, screen_height],
            "gallery_preview_seconds": round(preview_latency, 3),
            "application_reopen_seconds": application_reopens,
            "morph_state": morph_state,
            "network_recovery": network_recovery,
            "media_recovery": media_recovery,
            "cover_recovery": cover_recovery,
            "helper_recovery_seconds": recoveries,
            "native_deadline_seconds": native_deadlines,
            "native_resources": {"before": native_resources_before, "after": native_resources_after},
        }
        frames = [tuple(map(float, match)) for match in re.findall(
            r"bar-frame dt_ms=([\d.]+) render_ms=([\d.]+) width=([\d.]+)",
            (root / "bar.log").read_text(),
        )]
        renders = sorted(render for _, render, width in frames if width >= 300)
        if renders:
            result["panel_render_ms"] = {
                "frames": len(renders),
                "median": renders[len(renders) // 2],
                "p95": renders[min(len(renders) - 1, int(len(renders) * 0.95))],
                "max": max(renders),
            }
        (root / "results.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result))
    finally:
        stop_sampling.set()
        if sampler:
            sampler.join(timeout=1)
        for process in reversed(processes):
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        for process in processes:
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=3)
        for log in logs:
            log.close()
        if bus_listener is not None:
            bus_listener.close()
        print("Artifacts:", root)


if __name__ == "__main__":
    main()
