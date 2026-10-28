"""Exercise the compiled Rust native host, shared cache, and launcher in isolation."""
import base64
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
BINARY = os.environ.get("PROJECT_PICKER_CORE_BINARY") or shutil.which("project-picker-core")
ORIGIN = "chrome-extension://lfiijailpfkonkfmfkcjfagnopohffge/"
MAX_MESSAGE = 4 * 1024 * 1024
FIRST = "g-p-" + "1" * 32
SECOND = "g-p-" + "2" * 32
HOME_ROW = "Open main page\thttps://chatgpt.com"


def project(project_id=FIRST, name="First"):
    return {"id": project_id, "name": name, "url": f"https://chatgpt.com/g/{project_id}/project"}


def snapshot(projects=None, workspace="personal", started=None):
    return {"version": 1, "complete": True, "account_id": "account-one", "workspace_id": workspace,
            "workspace_name": workspace, "started_at": started if started is not None else int(time.time() * 1000) - 10000,
            "projects": projects if projects is not None else [project()]}


def frame(value):
    data = json.dumps(value).encode()
    return struct.pack("=I", len(data)) + data


def context_key(value):
    return hashlib.sha256(json.dumps([value["account_id"], value["workspace_id"]]).encode()).hexdigest()


@unittest.skipUnless(BINARY, "Compiled project-picker-core is required")
class ProjectPickerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.path = self.root / "cache/project-picker/projects.json"
        self.tools = self.root / "tools"
        self.tools.mkdir()
        self.environment = {**os.environ, "HOME": str(self.root / "home"),
                            "XDG_CACHE_HOME": str(self.path.parents[1]),
                            "PATH": str(self.tools) + os.pathsep + os.defpath}
        self.launch = self.root / "launch.json"
        self.tool("desktopctl", f"""import json, os, sys
from pathlib import Path
Path({str(self.launch)!r}).write_text(json.dumps({{"argv": sys.argv[1:], "pid": os.getpid(), "sid": os.getsid(0)}}))
""")

    def tearDown(self):
        self.temp.cleanup()

    def tool(self, name, body):
        path = self.tools / name
        path.write_text(f"#!{sys.executable}\n" + body)
        path.chmod(0o755)
        return path

    def run_picker(self, *args):
        return subprocess.run([BINARY, *args], env=self.environment, capture_output=True, timeout=10)

    def native(self, value=None, *, data=None, origin=ORIGIN):
        result = subprocess.run([BINARY, "--native-host", origin], env=self.environment,
                                input=frame(value) if data is None else data,
                                capture_output=True, timeout=10)
        self.assertEqual(result.stderr, b"")
        self.assertGreaterEqual(len(result.stdout), 4)
        self.assertEqual(struct.unpack("=I", result.stdout[:4])[0], len(result.stdout) - 4)
        reply = json.loads(result.stdout[4:])
        self.assertEqual(result.returncode, 0 if reply["ok"] else 1)
        return reply

    def save(self, value):
        reply = self.native(value)
        self.assertTrue(reply["ok"], reply)
        return reply

    def records(self):
        result = self.run_picker("--list")
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.decode().splitlines()

    def cache(self):
        return json.loads(self.path.read_text())

    def wait_for_launch(self):
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            if self.launch.exists():
                try:
                    return json.loads(self.launch.read_text())
                except ValueError:
                    pass
            time.sleep(0.01)
        self.fail("Mock desktopctl did not record a launch")

    def test_complete_snapshots_apply_renames_removals_and_an_empty_list(self):
        value = snapshot([project(), project(SECOND, "Second")])
        self.save(value)
        value["started_at"] += 1
        value["projects"] = [project(SECOND, "Renamed")]
        self.save(value)
        self.assertEqual(self.records(), [HOME_ROW, "Renamed\t" + project(SECOND)["url"]])
        value["started_at"] += 1
        value["projects"] = []
        self.save(value)
        self.assertEqual(self.records(), [HOME_ROW])
        for path in [self.path, self.path.with_name("status.json"), self.path.with_name("sync.lock")]:
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.path.parent.stat().st_mode & 0o777, 0o700)
        self.assertEqual(list(self.path.parent.glob(".project-picker.*.tmp")), [])

    def test_invalid_updates_preserve_the_last_good_cache(self):
        self.save(snapshot())
        original = self.path.read_bytes()
        invalid_values = [None, [], {**snapshot(), "version": 2}, {**snapshot(), "complete": False},
                          {**snapshot(), "projects": [project(), project()]},
                          {**snapshot(), "projects": [{**project(), "url": "https://example.com/"}]},
                          {**snapshot(), "projects": [{**project(), "name": "\x1b\t\u202e\u200b"}]},
                          {**snapshot(), "projects": [project(name="x" * 1025)]},
                          {**snapshot(), "projects": [project(project_id=FIRST + "A")]},
                          {**snapshot(), "workspace_id": " "}, {**snapshot(), "account_id": None}]
        invalid_values.extend({**snapshot(), "started_at": stamp} for stamp in
                              [True, False, 0, -1, 1.5, "1000", None, int(time.time() * 1000) + 120000])
        for value in invalid_values:
            with self.subTest(value=value):
                self.assertFalse(self.native(value)["ok"])
                self.assertEqual(self.path.read_bytes(), original)

    def test_late_snapshots_do_not_overwrite_or_switch_workspaces(self):
        self.save(snapshot(started=1000))
        self.save(snapshot([project(name="Newer")], started=3000))
        self.assertEqual(self.save(snapshot([project(name="Older")], started=2000)),
                         {"ok": True, "updated": False})
        self.save(snapshot([project(name="Work")], workspace="work", started=4000))
        self.save(snapshot([project(name="Late")], started=3500))
        self.assertIn("Work", self.records()[1])
        contexts = self.cache()["contexts"]
        self.assertEqual(len(contexts), 2)
        self.assertEqual(next(v for v in contexts.values() if v["workspace_id"] == "personal")["projects"][0]["name"], "Late")

    def test_accounts_have_separate_caches_in_the_same_workspace(self):
        self.save(snapshot(started=1000))
        self.save({**snapshot(started=2000), "account_id": "account-two"})
        self.assertEqual(len(self.cache()["contexts"]), 2)

    def test_python_version_one_keys_survive_unicode_and_escape_characters(self):
        value = {**snapshot(started=1000), "account_id": 'account-Ø-😀-"-\\-\n-\x7f', "workspace_id": "工作"}
        key = context_key(value)
        self.path.parent.mkdir(parents=True)
        self.path.write_text(json.dumps({"version": 1, "active": key, "contexts": {
            key: {**value, "synced_at": 1100}}}))
        self.assertIn("First", self.records()[1])
        self.save({**value, "started_at": 2000, "projects": [project(name="Renamed")]})
        self.assertEqual(list(self.cache()["contexts"]), [key])
        self.assertEqual(self.cache()["active"], key)
        self.assertIn("Renamed", self.records()[1])

    def test_duplicate_names_sort_by_id_and_display_drops_terminal_controls(self):
        self.save(snapshot([project(SECOND, "Alpha"), project(FIRST, "Alpha")]))
        self.assertEqual(self.records()[1:], ["Alpha\t" + project()["url"], "Alpha\t" + project(SECOND)["url"]])
        self.save(snapshot([project(name="A\tB\n\x1b[31mC\u202e\u200b")], started=int(time.time() * 1000)))
        self.assertEqual(self.records()[1], "A B [31mC\t" + project()["url"])

    def test_missing_malformed_or_invalid_cached_projects_offer_only_the_main_page(self):
        self.assertEqual(self.records(), [HOME_ROW])
        self.save(snapshot())
        cache = self.cache()
        context = cache["contexts"][cache["active"]]
        for field, value in [("url", "https://example.com/"), ("id", "invalid"), ("name", "\x1b\u202e")]:
            old = context["projects"][0][field]
            context["projects"][0][field] = value
            self.path.write_text(json.dumps(cache))
            self.assertEqual(self.records(), [HOME_ROW])
            context["projects"][0][field] = old
        self.path.write_text("not JSON")
        self.assertEqual(self.records(), [HOME_ROW])

    def test_status_diagnostics_are_allowlisted_and_never_replace_projects(self):
        self.save(snapshot())
        original = self.path.read_bytes()
        self.assertTrue(self.native({"action": "status", "code": "network", "stage": "projects", "kind": "TypeError",
                                     "error": "not-for-disk", "accessToken": "not-for-disk"})["ok"])
        status = json.loads(self.path.with_name("status.json").read_text())
        self.assertEqual({k: v for k, v in status.items() if k != "at"},
                         {"code": "network", "stage": "projects", "kind": "TypeError"})
        self.assertEqual(self.path.read_bytes(), original)
        self.assertTrue(self.native({"action": "status", "code": "http_403", "stage": "secret", "kind": ["secret"]})["ok"])
        self.assertEqual(set(json.loads(self.path.with_name("status.json").read_text())), {"code", "at"})
        for code in ["secret-token", "http_099", "http_600", "http_403\n", None]:
            self.assertFalse(self.native({"action": "status", "code": code})["ok"])

    def test_native_round_trip_discards_unknown_fields_at_every_level(self):
        value = {**snapshot([{**project(), "accessToken": "not-for-disk"}]), "accessToken": "not-for-disk", "synced_at": 1}
        reply = self.save(value)
        self.assertEqual(reply, {"ok": True, "updated": True, "count": 1})
        self.assertNotIn("not-for-disk", self.path.read_text())
        context = next(iter(self.cache()["contexts"].values()))
        self.assertGreater(context["synced_at"], 1)
        # Chrome sendNativeMessage starts one process per request; consume only one.
        self.assertTrue(self.native(data=frame(snapshot(started=2000)) + frame({"bad": True}))["ok"])

    def test_native_rejects_truncated_oversized_invalid_json_and_wrong_origins(self):
        for data in [b"\x01", struct.pack("=I", 12) + b"{}", struct.pack("=I", 0),
                     struct.pack("=I", MAX_MESSAGE + 1), struct.pack("=I", 1) + b"{",
                     struct.pack("=I", 1) + b"\xff"]:
            with self.subTest(data=data):
                self.assertFalse(self.native(data=data)["ok"])
        for origin in ["", "chrome-extension://unexpected/", ORIGIN.rstrip("/"), ORIGIN + "extra"]:
            self.assertFalse(self.native(data=b"", origin=origin)["ok"])
        self.assertFalse(self.path.exists())

    def test_wrong_origin_is_rejected_without_waiting_for_stdin(self):
        process = subprocess.Popen([BINARY, "--native-host", "chrome-extension://unexpected/"],
                                   env=self.environment, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            self.assertEqual(process.wait(timeout=3), 1)
            self.assertFalse(json.loads(process.stdout.read()[4:])["ok"])
        finally:
            if process.poll() is None:
                process.kill()
            process.communicate()

    def test_exact_message_limit_and_project_count_limits(self):
        data = json.dumps(snapshot([])).encode()
        data += b" " * (MAX_MESSAGE - len(data))
        self.assertTrue(self.native(data=struct.pack("=I", len(data)) + data)["ok"])
        projects = [project(f"g-p-{i:032x}") for i in range(10000)]
        self.assertEqual(self.save(snapshot(projects, started=int(time.time() * 1000)))["count"], 10000)
        original = self.path.read_bytes()
        self.assertFalse(self.native(snapshot(projects + [project(FIRST)], started=int(time.time() * 1000)))["ok"])
        self.assertEqual(self.path.read_bytes(), original)

    def test_text_length_counts_unicode_characters(self):
        self.assertTrue(self.save(snapshot([project(name="😀" * 1024)]))["ok"])
        self.assertFalse(self.native(snapshot([project(name="😀" * 1025)]))["ok"])

    def test_concurrent_hosts_keep_all_contexts_and_the_newest_active_snapshot(self):
        values = [snapshot(workspace=f"workspace-{i}", started=1000 + i) for i in range(12)]
        with ThreadPoolExecutor(max_workers=6) as pool:
            replies = list(pool.map(self.native, values))
        self.assertTrue(all(reply["ok"] for reply in replies))
        cache = self.cache()
        self.assertEqual(len(cache["contexts"]), len(values))
        self.assertEqual(cache["contexts"][cache["active"]]["started_at"], 1011)

    def test_combined_cache_cannot_grow_past_the_read_limit(self):
        projects = [project(f"g-p-{i:032x}", "x" * 700) for i in range(3000)]
        self.save(snapshot(projects, started=1000))
        original = self.path.read_bytes()
        self.assertFalse(self.native(snapshot(projects, workspace="work", started=2000))["ok"])
        self.assertEqual(self.path.read_bytes(), original)

    def test_linked_cache_status_and_lock_are_refused(self):
        self.path.parent.mkdir(parents=True)
        target = self.root / "precious"
        target.write_text(json.dumps({"version": 1, "active": None, "contexts": {}}))
        original = target.read_bytes()
        for name in ["projects.json", "status.json", "sync.lock"]:
            path = self.path.with_name(name)
            if path.exists():
                path.unlink()
            path.symlink_to(target)
            self.assertFalse(self.native(snapshot())["ok"])
            self.assertEqual(target.read_bytes(), original)
            path.unlink()
        self.path.symlink_to(self.root / "missing")
        self.assertFalse(self.native(snapshot())["ok"])
        self.assertFalse((self.root / "missing").exists())

    def test_oversized_cache_and_special_files_are_refused_without_blocking(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_bytes(b" " * (MAX_MESSAGE + 1))
        self.assertFalse(self.native(snapshot())["ok"])
        self.assertEqual(self.records(), [HOME_ROW])
        self.path.unlink()
        os.mkfifo(self.path)
        self.assertEqual(self.records(), [HOME_ROW])
        self.assertFalse(self.native(snapshot())["ok"])

    def test_manifest_identity_matches_the_compiled_origin_allowlist(self):
        manifest = json.loads((ROOT / "dotfiles/chrome/.local/share/browser-extensions/project-picker/manifest.json").read_text())
        extension_id = "".join(chr(ord("a") + int(n, 16)) for n in hashlib.sha256(base64.b64decode(manifest["key"])).hexdigest()[:32])
        host = json.loads((ROOT / "dotfiles/chrome/.config/desktop/project-picker-native-host.json").read_text())
        self.assertEqual(host["allowed_origins"], [f"chrome-extension://{extension_id}/"])
        self.assertTrue(self.native({"action": "status", "code": "auth_required"}, origin=host["allowed_origins"][0])["ok"])

    def test_selection_opens_only_the_validated_url_in_a_detached_session(self):
        self.save(snapshot([project(name="$(not-a-command); `literal`")]))
        self.tool("project-picker-tui", f"print({FIRST!r})\n")
        result = self.run_picker("--choose")
        self.assertEqual(result.returncode, 0, result.stderr)
        launch = self.wait_for_launch()
        self.assertEqual(launch["argv"], ["launch", "webapp", project()["url"]])
        self.assertEqual(launch["pid"], launch["sid"])

    def test_deleted_or_invalid_projects_cannot_launch_from_an_old_selection(self):
        self.save(snapshot())
        self.tool("project-picker-tui", f"""import json
from pathlib import Path
p = Path({str(self.path)!r})
v = json.loads(p.read_text())
v["contexts"][v["active"]]["projects"] = []
p.write_text(json.dumps(v))
print({FIRST!r})
""")
        result = self.run_picker("--choose")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b"no longer available", result.stderr)
        self.assertFalse(self.launch.exists())

    def test_cancellation_empty_unknown_and_failed_results_never_launch(self):
        for body, code in [("raise SystemExit(130)", 0), ("", 0), ("print('999\\tunknown')", 1),
                           ("raise SystemExit(1)", 1), ("print('home\\nextra')", 1)]:
            self.tool("project-picker-tui", body + "\n")
            self.assertEqual(self.run_picker("--choose").returncode, code)
            self.assertFalse(self.launch.exists())

    def test_default_command_preserves_the_floating_terminal_invocation(self):
        result = self.run_picker()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.wait_for_launch()["argv"],
                         ["terminal", "--float", "--app-id", "project.picker", "project-picker", "--choose"])

    def test_portable_launchers_find_the_native_core_on_path(self):
        core = self.tools / "project-picker-core"
        shutil.copy2(BINARY, core)
        picker = ROOT / "dotfiles/desktop-tools/.local/bin/project-picker"
        result = subprocess.run(["sh", str(picker), "--list"], env=self.environment, capture_output=True, timeout=10)
        self.assertEqual(result.stdout.decode().strip(), HOME_ROW)
        host = picker.with_name("project-picker-host")
        result = subprocess.run(["sh", str(host), ORIGIN], env=self.environment,
                                input=frame(snapshot()), capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout[4:])["ok"])

    def test_portable_launcher_can_use_the_xdg_cache_binary(self):
        core = self.path.parent / "bin/project-picker-core"
        core.parent.mkdir(parents=True)
        shutil.copy2(BINARY, core)
        result = subprocess.run(["sh", str(ROOT / "dotfiles/desktop-tools/.local/bin/project-picker"), "--list"],
                                env=self.environment, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.decode().strip(), HOME_ROW)


if __name__ == "__main__":
    unittest.main()
