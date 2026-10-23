"""Exercise cache transactions, native framing, and launcher behavior in isolation."""
import base64
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "dotfiles/desktop-tools/.local/share/desktop-tools"
sys.path.insert(0, str(SOURCE))
spec = importlib.util.spec_from_file_location("project_picker_test", SOURCE / "project_picker.py")
picker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(picker)
sys.path.pop(0)
FIRST = "g-p-" + "1" * 32
SECOND = "g-p-" + "2" * 32


def project(project_id=FIRST, name="First"):
    return {"id": project_id, "name": name, "url": f"https://chatgpt.com/g/{project_id}/project"}


def snapshot(projects=None, workspace="personal", started=None):
    return {"version": 1, "complete": True, "account_id": "account-one", "workspace_id": workspace,
            "workspace_name": workspace, "started_at": started or int(time.time() * 1000) - 10000,
            "projects": projects if projects is not None else [project()]}


class ProjectPickerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "cache/project-picker/projects.json"
        self.environment = patch.dict(os.environ, {"XDG_CACHE_HOME": str(self.path.parents[1])})
        self.environment.start()

    def tearDown(self):
        self.environment.stop()
        self.temp.cleanup()

    def test_complete_snapshots_apply_renames_and_removals_and_allow_an_empty_list(self):
        value = snapshot([project(), project(SECOND, "Second")])
        picker.save_snapshot(value)
        value["started_at"] += 1
        value["projects"] = [project(SECOND, "Renamed")]
        picker.save_snapshot(value)
        records, header = picker.entries()
        self.assertEqual([record["name"] for record in records], ["Open main page", "Renamed"])
        self.assertIn("Last sync:", header)
        value["started_at"] += 1
        value["projects"] = []
        picker.save_snapshot(value)
        self.assertEqual(len(picker.entries()[0]), 1)
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)

    def test_invalid_updates_preserve_the_last_good_cache(self):
        picker.save_snapshot(snapshot())
        original = self.path.read_bytes()
        for invalid in [
            {**snapshot(), "complete": False},
            {**snapshot(), "projects": [project(), project()]},
            {**snapshot(), "projects": [{**project(), "url": "https://example.com/"}]},
            {**snapshot(), "projects": [{**project(), "name": "\x1b\t"}]},
            {**snapshot(), "started_at": True},
        ]:
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                picker.save_snapshot(invalid)
            self.assertEqual(self.path.read_bytes(), original)

    def test_late_snapshots_do_not_overwrite_newer_projects_or_switch_workspaces(self):
        picker.save_snapshot(snapshot(started=1000))
        picker.save_snapshot(snapshot([project(name="Newer")], started=3000))
        picker.save_snapshot(snapshot([project(name="Older")], started=2000))
        picker.save_snapshot(snapshot([project(name="Work")], workspace="work", started=4000))
        picker.save_snapshot(snapshot([project(name="Late")], started=3500))
        self.assertEqual(picker.entries()[0][1]["name"], "Work")
        cache = picker.read_cache(self.path)
        self.assertEqual(len(cache["contexts"]), 2)
        self.assertEqual(next(value for value in cache["contexts"].values()
                              if value["workspace_id"] == "personal")["projects"][0]["name"], "Late")

    def test_accounts_have_separate_caches_even_in_the_same_workspace(self):
        picker.save_snapshot(snapshot(started=1000))
        picker.save_snapshot({**snapshot(started=2000), "account_id": "account-two"})
        self.assertEqual(len(picker.read_cache(self.path)["contexts"]), 2)

    def test_duplicate_names_keep_distinct_urls_and_sort_without_terminal_controls(self):
        picker.save_snapshot(snapshot([project(SECOND, "Alpha"), project(FIRST, "Alpha")]))
        records, _ = picker.entries()
        self.assertEqual([record["id"] for record in records[1:]], [FIRST, SECOND])
        self.assertEqual(picker.label("A\tB\n\x1b[31mC"), "A B [31mC")

    def test_missing_and_malformed_cache_still_offer_the_main_page(self):
        self.assertIn("No sync yet", picker.entries()[1])
        self.path.parent.mkdir(parents=True)
        self.path.write_text("not JSON")
        records, header = picker.entries()
        self.assertEqual([record["url"] for record in records], [picker.MAIN_PAGE])
        self.assertIn("unreadable", header)

    def test_sync_errors_show_in_the_picker_without_replacing_projects_or_saving_credentials(self):
        picker.save_status({"code": "http_403", "accessToken": "not-for-disk"})
        self.assertIn("HTTP 403", picker.entries()[1])
        self.assertFalse(self.path.exists())
        self.assertNotIn("not-for-disk", self.path.with_name("status.json").read_text())
        picker.save_snapshot(snapshot())
        original = self.path.read_bytes()
        with patch.object(picker.time, "time", return_value=time.time() + 1):
            picker.save_status({"code": "invalid_response"})
        records, header = picker.entries()
        self.assertEqual(records[1]["id"], FIRST)
        self.assertIn("unsupported project list", header)
        self.assertEqual(self.path.read_bytes(), original)
        with self.assertRaises(ValueError):
            picker.save_status({"code": "secret-token-or-arbitrary-message"})

    def test_error_diagnostics_allow_only_request_stages_and_error_types(self):
        picker.save_status({"code": "network", "stage": "projects", "kind": "TypeError",
                            "error": "must-not-be-stored"})
        self.assertIn("projects / TypeError", picker.entries()[1])
        self.assertNotIn("must-not-be-stored", self.path.with_name("status.json").read_text())
        picker.save_status({"code": "network", "stage": "secret", "kind": "secret"})
        self.assertNotIn("secret", self.path.with_name("status.json").read_text())

    def test_native_status_message_produces_an_actionable_header(self):
        data = json.dumps({"action": "status", "code": "auth_required"}).encode()
        destination = io.BytesIO()
        self.assertEqual(picker.native_host(picker.EXTENSION_ORIGIN,
                         io.BytesIO(struct.pack("=I", len(data)) + data), destination), 0)
        self.assertTrue(json.loads(destination.getvalue()[4:])["ok"])
        self.assertIn("Sign in", picker.entries()[1])

    def test_atomic_update_refuses_a_linked_cache(self):
        self.path.parent.mkdir(parents=True)
        target = Path(self.temp.name) / "precious"
        target.write_text(json.dumps({"version": 1, "active": None, "contexts": {}}))
        self.path.symlink_to(target)
        original = target.read_bytes()
        with self.assertRaises(ValueError):
            picker.save_snapshot(snapshot())
        self.assertEqual(target.read_bytes(), original)

    def test_native_protocol_round_trip_uses_one_framed_reply_and_persists_no_credentials(self):
        data = json.dumps({**snapshot(), "accessToken": "must-not-be-stored"}).encode()
        result = subprocess.run([sys.executable, str(SOURCE / "project_picker.py"), "--native-host",
                                 picker.EXTENSION_ORIGIN], input=struct.pack("=I", len(data)) + data,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        size = struct.unpack("=I", result.stdout[:4])[0]
        self.assertEqual(size, len(result.stdout) - 4)
        self.assertEqual(json.loads(result.stdout[4:])["count"], 1)
        self.assertNotIn("must-not-be-stored", self.path.read_text())
        self.assertEqual(result.stderr, b"")

    def test_native_protocol_rejects_truncated_oversized_and_wrong_origin_messages(self):
        for data, origin in [(b"\x01", picker.EXTENSION_ORIGIN),
                             (struct.pack("=I", 12) + b"{}", picker.EXTENSION_ORIGIN),
                             (struct.pack("=I", picker.MAX_MESSAGE + 1), picker.EXTENSION_ORIGIN),
                             (b"", "chrome-extension://unexpected/")]:
            destination = io.BytesIO()
            self.assertEqual(picker.native_host(origin, io.BytesIO(data), destination), 1)
            self.assertFalse(json.loads(destination.getvalue()[4:])["ok"])
        self.assertFalse(self.path.exists())

    def test_manifest_identity_matches_native_host_allowlist(self):
        manifest = json.loads((ROOT / "dotfiles/chrome/.local/share/browser-extensions/project-picker/manifest.json").read_text())
        key = base64.b64decode(manifest["key"])
        extension_id = "".join(chr(ord("a") + int(n, 16)) for n in hashlib.sha256(key).hexdigest()[:32])
        host = json.loads((ROOT / "dotfiles/chrome/.config/desktop/project-picker-native-host.json").read_text())
        self.assertEqual(host["allowed_origins"], [f"chrome-extension://{extension_id}/"])
        self.assertEqual(picker.EXTENSION_ORIGIN, host["allowed_origins"][0])

    def test_selection_opens_its_url_without_interpreting_project_names(self):
        picker.save_snapshot(snapshot([project(name="$(not-a-command); `literal`")]))
        row = FIRST + "\n"
        with patch.object(picker.shutil, "which", return_value="project-picker-tui"), \
                patch.object(picker.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, row)), \
                patch.object(picker, "open_project") as launch:
            picker.choose()
        launch.assert_called_once_with(project()["url"])

    def test_a_deleted_project_cannot_launch_from_an_old_selection(self):
        value = snapshot()
        picker.save_snapshot(value)

        def remove_project(*args, **kwargs):
            picker.save_snapshot({**value, "started_at": value["started_at"] + 1, "projects": []})
            return subprocess.CompletedProcess([], 0, FIRST + "\n")

        with patch.object(picker.shutil, "which", return_value="project-picker-tui"), \
                patch.object(picker.subprocess, "run", side_effect=remove_project), \
                patch.object(picker, "open_project") as launch:
            with self.assertRaisesRegex(ValueError, "no longer available"):
                picker.choose()
        launch.assert_not_called()

    def test_web_app_launch_detaches_from_the_picker_terminal(self):
        with patch.object(picker.subprocess, "Popen") as launch:
            picker.open_project(project()["url"])
        self.assertEqual(launch.call_args.args[0], ["desktopctl", "launch", "webapp", project()["url"]])
        self.assertTrue(launch.call_args.kwargs["start_new_session"])

    def test_cancellation_or_unknown_results_never_launch_a_window(self):
        for result in [subprocess.CompletedProcess([], 130, ""), subprocess.CompletedProcess([], 0, "999\tunknown\n")]:
            with patch.object(picker.shutil, "which", return_value="project-picker-tui"), \
                    patch.object(picker.subprocess, "run", return_value=result), \
                    patch.object(picker, "open_project") as launch:
                if result.returncode:
                    picker.choose()
                else:
                    with self.assertRaises(ValueError):
                        picker.choose()
                launch.assert_not_called()

if __name__ == "__main__":
    unittest.main()
