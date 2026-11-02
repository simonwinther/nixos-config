"""Exercise the native backend with private state, sockets and literal commands."""
import json
import os
from pathlib import Path
import select
import socket
import sqlite3
import struct
import subprocess
import tempfile
import threading
import time
import unittest

BINARY = os.environ.get("DESKTOP_SEARCH_TEST_BINARY")
if BINARY:
    # Exercise the same executable while keeping command fixtures ahead of the
    # package wrapper's runtime dependencies in PATH.
    unwrapped = Path(BINARY).with_name(".desktop-search-wrapped")
    if unwrapped.is_file():
        BINARY = str(unwrapped)


def exact(connection, length):
    data = bytearray()
    while len(data) < length:
        part = connection.recv(length - len(data))
        if not part:
            raise EOFError()
        data.extend(part)
    return bytes(data)


def request(connection, kind, value, encoding=1):
    body = json.dumps(value).encode() if encoding else value
    connection.sendall(bytes([kind, encoding]) + struct.pack(">I", len(body)) + body)


def response(connection):
    header = exact(connection, 5)
    length = struct.unpack(">I", header[1:])[0]
    if length > 16 * 1024 * 1024:
        raise AssertionError("Unbounded response")
    return header[0], exact(connection, length)


def frame(connection, kind, value=None):
    body = b"" if value is None else json.dumps(value).encode()
    connection.sendall(bytes([kind]) + struct.pack(">I", len(body)) + body)


@unittest.skipUnless(BINARY, "Set DESKTOP_SEARCH_TEST_BINARY to the built backend")
class SearchTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="ds-", dir="/tmp")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.environment = {**os.environ, **{key: str(self.root / directory) for key, directory in (
            ("HOME", "home"), ("XDG_RUNTIME_DIR", "run"), ("XDG_CONFIG_HOME", "config"),
            ("XDG_DATA_HOME", "data"), ("XDG_CACHE_HOME", "cache"), ("XDG_STATE_HOME", "state"),
        )}}
        self.environment["XDG_DATA_DIRS"] = str(self.root / "empty-data")
        self.environment.pop("NOTIFY_SOCKET", None)
        self.environment.pop("DESKTOP_SEARCH_CONFIG_FILE", None)
        for key in ("HOME", "XDG_RUNTIME_DIR", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_CACHE_HOME", "XDG_STATE_HOME"):
            Path(self.environment[key]).mkdir(mode=0o700)
        config = self.root / "config/desktop-search"
        config.mkdir()
        (config / "config.toml").write_text('max_items=100\nrepository_owner="fixture-owner"\ntodo_categories=["Work","Home"]\n')
        apps = self.root / "data/applications"
        apps.mkdir()
        self.application = apps / "literal.desktop"
        self.application.write_text('[Desktop Entry]\nName=Fixture Notes $HOME; literal\nType=Application\nExec=never-execute-this-fixture\nKeywords=writing;notes;\n')
        tools = self.root / "bin"
        tools.mkdir()
        self.environment["PATH"] = str(tools) + os.pathsep + self.environment["PATH"]
        for name in ("uwsm-app", "wl-copy", "notify-send"):
            path = tools / name
            path.write_text('#!' + os.sys.executable + '\nimport json,sys\nfrom pathlib import Path\n'
                            + f'root=Path({str(self.root)!r})\n'
                            + f'with (root/{name!r}).open("a") as log: log.write(json.dumps(sys.argv[1:])+"\\n")\n'
                            + ('(root/"copied").write_bytes(sys.stdin.buffer.read())\n' if name == "wl-copy" else ''))
            path.chmod(0o700)
        self.log = (self.root / "service.log").open("w")
        self.addCleanup(self.log.close)
        self.process = None
        self.compatibility = False
        self.socket = self.root / "run/desktop-search/search.sock"
        self.start()
        self.addCleanup(self.stop)

    def start(self):
        arguments = [BINARY, "serve", "--no-collector"]
        if not self.compatibility:
            arguments.append("--no-compatibility")
        self.process = subprocess.Popen(arguments, env=self.environment, stdout=self.log, stderr=self.log)
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                self.fail((self.root / "service.log").read_text())
            if self.socket.is_socket():
                try:
                    self.query("clipboard")
                    return
                except (ConnectionRefusedError, FileNotFoundError):
                    pass
            time.sleep(0.01)
        self.fail("Backend did not become ready")

    def stop(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.process.wait(timeout=5)

    def connection(self):
        connection = socket.socket(socket.AF_UNIX)
        connection.settimeout(5)
        try:
            connection.connect(str(self.socket))
        except BaseException:
            connection.close()
            raise
        return connection

    def query(self, provider, query="", **fields):
        with self.connection() as connection:
            request(connection, 0, {"providers": [provider], "query": query, "maxresults": 1000, **fields})
            items = []
            while True:
                kind, body = response(connection)
                if kind == 255:
                    return items
                if kind == 0:
                    items.append(json.loads(body)["item"])

    def activate(self, provider, action, identifier="", query="", **fields):
        with self.connection() as connection:
            request(connection, 1, {"provider": provider, "action": action, "identifier": identifier, "query": query, **fields})
            kind, body = response(connection)
            self.assertEqual(kind, 2)
            result = json.loads(body) if body else {}
            self.assertNotIn("error", result, result)
            return result

    def test_providers_preserve_literals_and_bound_expensive_queries(self):
        menus = self.root / "menus.json"
        menus.write_text('{"fixture-runtime-menu":{"items":{}}}')
        listed = subprocess.check_output(
            [BINARY, "listproviders"],
            env={**self.environment, "DESKTOP_MENUS_FILE": str(menus)}, text=True,
        ).splitlines()
        self.assertIn("menus:fixture-runtime-menu", listed)
        entries = self.query("desktopapplications", "fxnts")
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["text"], "Fixture Notes $HOME; literal")
        self.assertEqual(entries[0]["identifier"], str(self.application))
        result = self.query("calc", "(12 + 8) / 4")
        self.assertEqual(result[0]["text"], "5")
        self.activate("calc", "save", result[0]["identifier"])
        self.assertEqual(self.query("calc")[0]["text"], "5")
        self.assertTrue(any("rocket" in item["text"].lower() for item in self.query("symbols", "rocket")))
        self.assertEqual(self.query("unicode", "U+1F680")[0]["identifier"], "🚀")
        self.assertEqual(self.query("unicode", "ROCKET")[0]["identifier"], "🚀")
        repo = self.query("menus:repositories", "owner repo")[0]
        self.assertEqual(repo["identifier"], "https://github.com/owner/repo")
        self.assertEqual(self.query("menus:repositories", "owner; bad"), [])
        url = self.query("websearch", "literal & å?")[0]["subtext"]
        self.assertIn("%26", url)
        self.assertIn("%C3%A5", url)
        self.assertEqual(self.query("missing-provider"), [])
        self.activate("desktopapplications", "start", str(self.application), context="fixture-context")
        deadline = time.monotonic() + 2
        while not (self.root / "uwsm-app").exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        arguments = json.loads((self.root / "uwsm-app").read_text().splitlines()[0])
        self.assertEqual(arguments, ["--", "hyprspace-launch", "--context", "fixture-context", "--", "desktopctl", "bar", "launch", str(self.application)])
        target = self.root / "home/literal $HOME; file.txt"
        target.write_text("fixture")
        self.assertTrue(any(item["identifier"] == str(target) for item in self.query("files", "literal")))

    def test_protobuf_and_cancelled_queries_share_a_persistent_connection(self):
        with self.connection() as connection:
            # Query fields: provider=calc, expression=2+3, maxresults=10.
            request(connection, 0, b"\x0a\x04calc\x12\x032+3\x18\x0a", encoding=0)
            kind, body = response(connection)
            self.assertEqual(kind, 0)
            self.assertIn(b"5", body)
            self.assertEqual(response(connection), (255, b""))
            for index in range(250):
                request(connection, 0, {"providers": ["unicode"], "query": f"cancelled-query-{index}", "maxresults": 1000})
            started = time.monotonic()
            request(connection, 0, {"providers": ["calc"], "query": "123+456", "maxresults": 10})
            while True:
                kind, body = response(connection)
                if kind == 0 and json.loads(body)["query"] == "123+456":
                    self.assertEqual(json.loads(body)["item"]["text"], "579")
                    break
            self.assertLess(time.monotonic() - started, 2)
        with self.connection() as connection:
            connection.sendall(b"\x00\x01\xff\xff\xff\xff")
            self.assertEqual(connection.recv(1), b"")
        self.assertEqual(self.query("calc", "1+1")[0]["text"], "2")

    def test_tasks_and_pause_state_survive_restart(self):
        self.activate("todo", "create")
        self.activate("todo", "save", query="in 10m > Literal $HOME; task !")
        item = self.query("todo")[0]
        self.assertEqual(item["text"], "Literal $HOME; task")
        self.assertIn("urgent", item["state"])
        self.activate("todo", "change_category", item["identifier"])
        self.activate("todo", "active", item["identifier"])
        self.assertIn("active", self.query("todo", "Work")[0]["state"])
        self.activate("clipboard", "pause")
        self.stop()
        self.start()
        self.assertEqual(self.query("todo")[0]["identifier"], item["identifier"])
        with self.connection() as connection:
            request(connection, 4, {"provider": "clipboard"})
            kind, body = response(connection)
            self.assertEqual(kind, 3)
            self.assertIn("paused", json.loads(body)["states"])
        self.activate("clipboard", "unpause")
        self.activate("todo", "done", item["identifier"])
        self.activate("todo", "clear")
        self.assertEqual(self.query("todo"), [])

    def test_import_keeps_full_text_images_pins_and_subscription_updates(self):
        legacy = self.root / "run/elephant"
        legacy.mkdir()
        server = socket.socket(socket.AF_UNIX)
        server.bind(str(legacy / "elephant.sock"))
        server.listen()
        server.settimeout(0.1)
        stopped = threading.Event()
        text = "long " * 12_000 + "needle-after-preview\næ $HOME"
        image = self.root / "saved.png"
        image.write_bytes(b"\x89PNG\r\n\x1a\nsynthetic exact image bytes")
        items = [
            {"identifier": "text", "preview": text, "preview_type": "text", "subtext": "original date", "state": ["pinned"]},
            {"identifier": "image", "preview": str(image), "preview_type": "file", "state": []},
            {"identifier": "file-list", "text": "photo%20one.png", "preview": "file:///tmp/photo%20one.png", "preview_type": "file", "state": []},
            {"identifier": "files", "text": "one.txt,two.txt", "preview": "file:///tmp/one.txt\nfile:///tmp/two.txt", "preview_type": "text", "state": []},
            {"identifier": "literal-uri", "text": "file:///tmp/literal", "preview": "file:///tmp/literal", "preview_type": "text", "state": []},
        ]
        def serve():
            while not stopped.is_set():
                try:
                    connection, _ = server.accept()
                except socket.timeout:
                    continue
                except OSError:
                    return
                with connection:
                    try:
                        header = exact(connection, 6)
                    except EOFError:
                        continue
                    value = json.loads(exact(connection, struct.unpack(">I", header[2:])[0]))
                    if header[0] == 4:
                        frame(connection, 3, {"states": ["show_images_only"]})
                        try:
                            frame(connection, 253)
                        except BrokenPipeError:
                            pass
                    elif header[0] == 1:
                        frame(connection, 2)
                    else:
                        for item in items:
                            frame(connection, 0, {"item": item})
                        frame(connection, 255)
        thread = threading.Thread(target=serve, daemon=True)
        thread.start()
        try:
            result = self.activate("desktop-search", "import-elephant")
            self.assertEqual(result["imported"]["clipboard"], 5)
            self.assertEqual(result["imported"]["pinned"], 1)
            entries = self.query("clipboard")
            self.assertEqual(entries[0]["identifier"], "text")
            self.assertLess(len(entries[0]["preview"]), len(text))
            self.assertEqual(Path(entries[0]["payload_path"]).read_bytes(), text.encode())
            self.assertEqual(Path(entries[1]["payload_path"]).read_bytes(), image.read_bytes())
            self.assertEqual(entries[2]["mimetype"], "text/uri-list")
            self.assertEqual(Path(entries[2]["payload_path"]).read_bytes(), b"file:///tmp/photo%20one.png")
            self.assertEqual(entries[3]["mimetype"], "text/uri-list")
            self.assertEqual(Path(entries[3]["payload_path"]).read_bytes(), b"file:///tmp/one.txt\nfile:///tmp/two.txt")
            self.assertEqual(entries[4]["mimetype"], "text/plain;charset=utf-8")
            self.assertEqual(self.query("clipboard", "needle")[0]["identifier"], "text")
            self.activate("clipboard", "show_images_only")
            self.assertEqual([item["identifier"] for item in self.query("clipboard")], ["image"])
            self.assertEqual(len(self.query("clipboard", mode="show_combined")), 5)
            self.activate("clipboard", "show_combined")
            self.activate("clipboard", "copy", "text")
            self.assertEqual((self.root / "copied").read_bytes(), text.encode())
            self.activate("clipboard", "edit", "text")
            deadline = time.monotonic() + 2
            while not (self.root / "uwsm-app").exists() and time.monotonic() < deadline:
                time.sleep(0.01)
            edit = Path(json.loads((self.root / "uwsm-app").read_text().splitlines()[-1])[-1])
            edit.write_text("edited-content-without-changing-original")
            edited = []
            while not edited and time.monotonic() < deadline:
                edited = self.query("clipboard", "edited-content")
                time.sleep(0.01)
            self.assertTrue(edited)
            self.assertEqual(Path(entries[0]["payload_path"]).read_bytes(), text.encode())
            self.activate("clipboard", "remove", edited[0]["identifier"])
            with self.connection() as subscription:
                request(subscription, 2, {"provider": "clipboard"})
                time.sleep(0.05)
                self.activate("clipboard", "unpin", "text")
                self.assertTrue(select.select([subscription], [], [], 2)[0])
                self.assertEqual(json.loads(response(subscription)[1]), {"value": "clipboard"})
            self.activate("clipboard", "remove", "text")
            self.assertFalse(Path(entries[0]["payload_path"]).exists())
            self.assertEqual(image.read_bytes(), b"\x89PNG\r\n\x1a\nsynthetic exact image bytes")
            stopped.set()
            thread.join(timeout=1)
            server.close()
            self.stop()
            self.compatibility = True
            self.start()
            self.assertEqual(self.query("clipboard")[0]["identifier"], "image")
            edit.write_text(text)
            deadline = time.monotonic() + 2
            while not self.query("clipboard", "needle") and time.monotonic() < deadline:
                time.sleep(0.01)
            self.assertLess(len(self.query("clipboard", "needle")[0]["preview"]), len(text))
            with socket.socket(socket.AF_UNIX) as old_client:
                old_client.settimeout(2)
                old_client.connect(str(legacy / "elephant.sock"))
                request(old_client, 0, {"providers": ["clipboard"], "maxresults": 1000})
                old_items = []
                while True:
                    kind, body = response(old_client)
                    if kind == 255:
                        break
                    if kind == 0:
                        old_items.append(json.loads(body)["item"])
            self.assertTrue(any(item["preview"] == text for item in old_items))
            with self.connection() as connection:
                request(connection, 1, {"provider": "desktop-search", "action": "import-elephant"})
                self.assertIn("legacy collector is no longer running", json.loads(response(connection)[1])["error"])
            database = self.root / "state/desktop-search/history.sqlite3"
            self.assertEqual(database.stat().st_mode & 0o777, 0o600)
            self.assertEqual(sqlite3.connect(database).execute("PRAGMA integrity_check").fetchone()[0], "ok")
        finally:
            stopped.set()
            thread.join(timeout=1)
            server.close()


if __name__ == "__main__":
    unittest.main()
