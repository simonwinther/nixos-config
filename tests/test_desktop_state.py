"""State migrations and recovery use temporary homes, never the live desktop."""
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_desktop as base

ctl = base.ctl


class DesktopStateTests(unittest.TestCase):
    setUp = base.DesktopTests.setUp
    tearDown = base.DesktopTests.tearDown

    def put_state(self, value):
        self.state.mkdir(parents=True, exist_ok=True)
        raw = value if isinstance(value, bytes) else json.dumps(value).encode()
        (self.state / "state.json").write_bytes(raw)
        return raw

    def backups(self):
        return sorted(self.state.glob("state.json.invalid-*.json"))

    def process_environment(self):
        return {**os.environ, "HOME": str(self.home), "XDG_CONFIG_HOME": str(self.config),
                "XDG_STATE_HOME": str(self.state.parent), "XDG_DATA_HOME": str(self.data),
                "XDG_RUNTIME_DIR": str(self.runtime.parent), "PYTHONDONTWRITEBYTECODE": "1"}

    def test_missing_state_uses_defaults_without_creating_a_state_file(self):
        self.assertEqual(ctl.selected_theme(), "tokyoled")
        self.assertEqual(ctl.selected_font(), "JetBrainsMono Nerd Font")
        self.assertFalse((self.state / "state.json").exists())
        self.assertEqual(self.backups(), [])

    def test_legacy_migrations_preserve_all_choices_and_extension_fields(self):
        original = {"theme": "catppuccin-latte", "font": "Test Mono", "terminalTheme": False,
                    "desktopTheme": True, "aboutArt": False, "screensaver": "matrix",
                    "wallpaper": "/images/a b.png", "lockBackground": "~/Pictures/lock.png",
                    "wallpapers": {"*": "/images/a b.png", "HDMI-A-1": "/images/other.png"},
                    "extension": {"retained": [1, "text", None]}}
        for version in (None, 0):
            with self.subTest(version=version):
                legacy = dict(original)
                if version is not None:
                    legacy["schemaVersion"] = version
                self.put_state(legacy)
                expected = {**original, "schemaVersion": ctl.STATE_VERSION}
                self.assertEqual(ctl.state(), expected)
                path = self.state / "state.json"
                self.assertEqual(json.loads(path.read_bytes()), expected)
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)
                before = path.stat().st_mtime_ns
                self.assertEqual(ctl.state(), expected)
                self.assertEqual(path.stat().st_mtime_ns, before)
                self.assertEqual(self.backups(), [])

    def test_malformed_json_is_preserved_exactly_and_recovered_only_once(self):
        cases = [(b'{\n"theme":', "line 2, column"), (b'\xff', "UTF-8 at byte"),
                 (b'{"theme":"private-value","theme":"other"}', "duplicate object key"),
                 (b'{"extension": NaN}', "non-finite"), (b'{"extension": Infinity}', "non-finite"),
                 (b'{"extension": 1e999}', "non-finite"), (b'', "invalid JSON"),
                 (b'[' * 2000 + b']' * 2000, "nesting")]
        for raw, diagnostic in cases:
            with self.subTest(raw=raw[:80]):
                self.put_state(raw)
                previous = set(self.backups())
                errors = io.StringIO()
                with contextlib.redirect_stderr(errors):
                    self.assertEqual(ctl.selected_theme(), "tokyoled")
                    self.assertEqual(ctl.selected_font(), "JetBrainsMono Nerd Font")
                added = set(self.backups()) - previous
                self.assertEqual(len(added), 1)
                backup = added.pop()
                self.assertEqual(backup.read_bytes(), raw)
                self.assertEqual(backup.stat().st_mode & 0o777, 0o600)
                self.assertIn(str(backup), errors.getvalue())
                self.assertIn(diagnostic, errors.getvalue())
                self.assertNotIn("private-value", errors.getvalue())
                self.assertEqual(errors.getvalue().count("recovered invalid state"), 1)
                self.assertEqual(json.loads((self.state / "state.json").read_bytes()),
                                 {"schemaVersion": ctl.STATE_VERSION})

    def test_invalid_root_types_recover_to_defaults(self):
        for value in ([], ["theme"], None, True, 12, "theme"):
            with self.subTest(value=value):
                self.put_state(value)
                with contextlib.redirect_stderr(io.StringIO()) as errors:
                    self.assertEqual(ctl.state(), {"schemaVersion": ctl.STATE_VERSION})
                self.assertIn("$: expected a JSON object", errors.getvalue())

    def test_bad_fields_do_not_discard_valid_choices_or_monitor_selections(self):
        raw = self.put_state({"theme": "catppuccin-latte", "font": [], "terminalTheme": "false",
                              "wallpapers": {"HDMI-A-1": "/keep.png", "eDP-1": None, "": "/bad.png"},
                              "extension": {"keep": True}})
        with contextlib.redirect_stderr(io.StringIO()) as errors:
            value = ctl.state()
        self.assertEqual(value, {"schemaVersion": ctl.STATE_VERSION, "theme": "catppuccin-latte",
                                 "wallpapers": {"HDMI-A-1": "/keep.png"}, "extension": {"keep": True}})
        self.assertEqual(self.backups()[0].read_bytes(), raw)
        for field in ("$.font", "$.terminalTheme", "$.wallpapers"):
            self.assertIn(field, errors.getvalue())
        self.assertEqual(ctl.selected_font(), "JetBrainsMono Nerd Font")

    def test_schema_rejects_wrong_types_and_values_before_saving(self):
        self.put_state({"schemaVersion": ctl.STATE_VERSION, "theme": "tokyoled"})
        original = (self.state / "state.json").read_bytes()
        cases = {"schemaVersion": [True, -1, 1.0, "1", None],
                 "theme": [[], None, "../escape", "Name", ""],
                 "font": [False, [], "\nfont_family injected", "\ud800", "  "],
                 "wallpaper": [{}, None, "", "path\x00.png"],
                 "lockBackground": [[], 42, "path\n.png"],
                 "terminalTheme": ["false", 0, 1, None],
                 "desktopTheme": ["true", 0, None], "aboutArt": ["true", 1, None],
                 "screensaver": [[], "absent", None],
                 "wallpapers": [[], None, {"eDP-1": []}, {"": "/a.png"}, {3: "/a.png"}]}
        for field, values in cases.items():
            for value in values:
                with self.subTest(field=field, value=value), self.assertRaisesRegex(ValueError, r"\$\." + field):
                    ctl.save_state({"schemaVersion": ctl.STATE_VERSION, field: value})
                self.assertEqual((self.state / "state.json").read_bytes(), original)
                self.assertEqual(self.backups(), [])

    def test_invalid_schema_metadata_recovers_without_losing_valid_preferences(self):
        for version in (True, -1, "1", None, 1.0):
            with self.subTest(version=version):
                self.put_state({"schemaVersion": version, "theme": "tokyoled"})
                with contextlib.redirect_stderr(io.StringIO()) as errors:
                    self.assertEqual(ctl.state(), {"schemaVersion": ctl.STATE_VERSION, "theme": "tokyoled"})
                self.assertIn("$.schemaVersion", errors.getvalue())

    def test_newer_schemas_fail_with_a_path_and_never_change_state(self):
        original = self.put_state({"schemaVersion": ctl.STATE_VERSION + 1, "theme": "tokyoled"})
        output, errors = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            self.assertEqual(ctl.main(["theme", "current"]), 1)
        self.assertEqual(output.getvalue(), "")
        self.assertIn(str(self.state / "state.json"), errors.getvalue())
        self.assertIn("newer than supported", errors.getvalue())
        with self.assertRaises(ctl.UnsupportedStateVersion):
            ctl.save_state({"font": "Test Mono"})
        self.assertEqual((self.state / "state.json").read_bytes(), original)
        self.assertEqual(self.backups(), [])

    def test_state_symlinks_are_never_followed_or_replaced(self):
        self.state.mkdir(parents=True)
        target = self.home / "precious"
        for raw in (b'{"theme":"tokyoled"}', b'{broken'):
            with self.subTest(raw=raw):
                target.write_bytes(raw)
                link = self.state / "state.json"
                link.symlink_to(target)
                with self.assertRaisesRegex(ValueError, "linked desktop state"):
                    ctl.state()
                self.assertEqual(target.read_bytes(), raw)
                self.assertTrue(link.is_symlink())
                self.assertEqual(self.backups(), [])
                link.unlink()
        (self.state / "state.json").symlink_to(self.home / "absent")
        with self.assertRaisesRegex(ValueError, "linked desktop state"):
            ctl.save_state({"theme": "tokyoled"})

    def test_backup_failure_leaves_original_state_untouched(self):
        original = self.put_state(b'{broken')
        with patch.object(ctl.tempfile, "mkstemp", side_effect=PermissionError("test backup denied")):
            with self.assertRaisesRegex(OSError, "state recovery failed"):
                ctl.state()
        self.assertEqual((self.state / "state.json").read_bytes(), original)
        self.assertEqual(self.backups(), [])

    def test_replacement_failure_preserves_original_and_recovery_copy(self):
        original = self.put_state(b'{broken')
        with patch.object(ctl.os, "replace", side_effect=OSError("test replacement denied")):
            with self.assertRaisesRegex(OSError, "state recovery failed.*recovery copy"):
                ctl.state()
        self.assertEqual((self.state / "state.json").read_bytes(), original)
        self.assertEqual(len(self.backups()), 1)
        self.assertEqual(self.backups()[0].read_bytes(), original)

    def test_read_errors_do_not_reset_state(self):
        original = self.put_state({"theme": "tokyoled"})
        with patch.object(Path, "read_bytes", side_effect=PermissionError("test read denied")):
            with self.assertRaisesRegex(PermissionError, "test read denied"):
                ctl.state()
        self.assertEqual((self.state / "state.json").read_bytes(), original)
        self.assertEqual(self.backups(), [])

    def test_read_only_configuration_gets_diagnostics_without_recovery(self):
        path = self.home / "settings.json"
        for raw, diagnostic in ((b'{\ninvalid', "line 2, column"), (b'[]', "expected a JSON object")):
            with self.subTest(raw=raw):
                path.write_bytes(raw)
                with self.assertRaisesRegex(ValueError, diagnostic) as raised:
                    ctl.read_json(path)
                self.assertIn(str(path), str(raised.exception))
                self.assertEqual(path.read_bytes(), raw)
                self.assertEqual(self.backups(), [])

    def test_multiple_commands_use_recovered_state_and_keep_stdout_clean(self):
        for arguments, expected in ((["theme", "current"], "tokyoled"),
                                    (["font", "current"], "JetBrainsMono Nerd Font"),
                                    (["screensaver", "current"], "naruto"),
                                    (["wallpaper", "current"], "~/.local/share/wallpapers/tokyoled/digital-art/background.png")):
            with self.subTest(arguments=arguments):
                self.put_state(b'{"wallpapers": []}')
                result = subprocess.run([sys.executable, "-B", str(base.SCRIPT), *arguments],
                                        env=self.process_environment(), capture_output=True, text=True, timeout=10)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.strip(), expected)
                self.assertIn("$.wallpapers", result.stderr)

    def test_concurrent_commands_recover_once_and_preserve_each_others_updates(self):
        original = self.put_state(b'{broken')
        script = '''import importlib.util, sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.argv[1]).parent))
spec = importlib.util.spec_from_file_location("desktopctl", sys.argv[1])
ctl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ctl)
for _ in range(15):
    with ctl.state_lock():
        value = ctl.state()
        value[sys.argv[2]] = sys.argv[3]
        ctl.save_state(value)
'''
        processes = []
        try:
            for field, choice in (("theme", "catppuccin-latte"), ("font", "Test Mono")):
                processes.append(subprocess.Popen([sys.executable, "-B", "-c", script, str(base.SCRIPT), field, choice],
                                                  env=self.process_environment(), stdout=subprocess.PIPE,
                                                  stderr=subprocess.PIPE, text=True))
            diagnostics = []
            for process in processes:
                stdout, stderr = process.communicate(timeout=10)
                self.assertEqual(process.returncode, 0, stderr)
                self.assertEqual(stdout, "")
                diagnostics.append(stderr)
        finally:
            for process in processes:
                if process.poll() is None:
                    process.kill()
                process.wait()
        self.assertEqual(ctl.state(), {"schemaVersion": ctl.STATE_VERSION,
                                       "theme": "catppuccin-latte", "font": "Test Mono"})
        self.assertEqual(len(self.backups()), 1)
        self.assertEqual(self.backups()[0].read_bytes(), original)
        self.assertEqual("".join(diagnostics).count("recovered invalid state"), 1)


if __name__ == "__main__":
    unittest.main()
