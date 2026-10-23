"""OBS migration checks use disposable homes and synthetic credentials."""

import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
DEFAULTS = ROOT / "dotfiles/obs/.local/share/obs-defaults"
spec = importlib.util.spec_from_file_location("obs_sync", ROOT / "dotfiles/obs/.local/share/obs-sync/sync.py")
obs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(obs)


class ObsMigration(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.home = Path(self.directory.name) / 'a "quoted" home'
        self.config = self.home / ".config"
        self.state = self.home / ".local/state"
        self.target = self.config / "obs-studio"
        self.data = self.home / ".local/share"
        self.defaults = self.data / "obs-defaults"
        shutil.copytree(DEFAULTS, self.defaults)
        self.defaults.chmod(0o700)
        for path in self.defaults.rglob("*"):
            path.chmod(0o700 if path.is_dir() else 0o600)
        self.running = patch.object(obs, "obs_running", return_value=False)
        self.running.start()
        self.addCleanup(self.running.stop)

    def write(self, relative, content):
        path = self.target / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def sync(self, **kwargs):
        return obs.synchronize(self.defaults, self.home, self.config, self.data, self.state, **kwargs)

    def test_restores_complete_scene_graph_audio_and_assets(self):
        self.sync()
        scene = json.loads((self.target / "basic/scenes/Untitled.json").read_text())
        self.assertEqual([s["name"] for s in scene["scene_order"]], [
            "Scene", "Scene 2", "Stream starter snart", "Stream starrting soon", "Record Specific Thing"])
        mic = scene["AuxAudioDevice1"]
        self.assertEqual([f["name"] for f in mic["filters"]], [
            "Noise Suppression", "3-Band Equalizer", "Expander", "Compressor", "Limiter"])
        self.assertEqual(mic["filters"][1]["settings"], {"low": 2.5, "mid": -2.0, "high": 2.0})
        duck = scene["DesktopAudioDevice1"]["filters"][0]["settings"]
        self.assertEqual(duck["sidechain_source"], mic["name"])
        self.assertEqual(duck["ratio"], 20.0)
        self.assertEqual(duck["threshold"], -35.0)
        sources = {s["uuid"]: s for s in scene["sources"]}
        for source in sources.values():
            for item in source["settings"].get("items", []):
                self.assertIn(item["source_uuid"], sources)
            if source["id"] == "image_source":
                self.assertTrue(Path(source["settings"]["file"]).is_file())
        script = scene["modules"]["scripts-tool"][0]
        self.assertTrue(Path(script["path"]).is_file())
        self.assertEqual(script["settings"]["duration"], 5)
        profile = obs.ini((self.target / "basic/profiles/Untitled/basic.ini").read_text())
        self.assertEqual(profile["Video"]["FPSCommon"], "60")
        self.assertEqual(profile["Video"]["OutputCX"], "1920")
        self.assertEqual(profile["AdvOut"]["Encoder"], "obs_nvenc_h264_tex")

    def test_preserves_credentials_unmanaged_files_and_private_backups(self):
        relative = "basic/profiles/Untitled/service.json"
        private = '{"settings":{"key":"synthetic-stream-key","password":"synthetic-password"}}'
        self.write(relative, private)
        self.write("user.ini", "[Auth]\nAccessToken=synthetic-token\n[Panels]\nCookieId=synthetic-cookie\n")
        unrelated = self.write("basic/scenes/Other.json", '{"name":"Keep this collection"}')
        self.sync()
        service = self.target / relative
        live = json.loads(service.read_text())["settings"]
        self.assertEqual(live["key"], "synthetic-stream-key")
        self.assertEqual(live["service"], "Restream.io")
        self.assertEqual(live["password"], "synthetic-password")
        current = obs.ini((self.target / "user.ini").read_text())
        self.assertEqual(current["Auth"]["AccessToken"], "synthetic-token")
        self.assertEqual(current["Panels"]["CookieId"], "synthetic-cookie")
        self.assertTrue(unrelated.exists())
        backups = list((self.state / "obs-sync/backups").glob("*/" + relative))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(), private)
        self.assertEqual(service.stat().st_mode & 0o777, 0o600)
        self.assertEqual(backups[0].stat().st_mode & 0o777, 0o600)

    def test_rebuild_keeps_ui_edits_and_changed_defaults_preserve_portal_grants(self):
        self.sync()
        live = self.target / "basic/scenes/Untitled.json"
        edited = json.loads(live.read_text())
        edited["transition_duration"] = 1234
        screen = next(s for s in edited["sources"] if s["id"] == "pipewire-screen-capture-source")
        screen["settings"]["RestoreToken"] = "synthetic-local-grant"
        live.write_text(json.dumps(edited))
        self.sync()
        self.assertEqual(json.loads(live.read_text())["transition_duration"], 1234)
        # Home Manager reads the Nix store; the launcher reads the Stow target.
        # Merely changing that source location must not erase runtime edits.
        alternate = Path(self.directory.name) / "nix-store-source"
        shutil.copytree(self.defaults, alternate)
        obs.synchronize(alternate, self.home, self.config, self.data, self.state)
        self.assertEqual(json.loads(live.read_text())["transition_duration"], 1234)
        source = self.defaults / "config/basic/scenes/Untitled.json"
        declared = json.loads(source.read_text())
        declared["transition_duration"] = 400
        source.write_text(json.dumps(declared))
        self.sync()
        updated = json.loads(live.read_text())
        self.assertEqual(updated["transition_duration"], 400)
        self.assertEqual(next(s for s in updated["sources"] if s["uuid"] == screen["uuid"])["settings"]["RestoreToken"], "synthetic-local-grant")

    def test_refuses_live_obs_and_defers_home_manager_updates(self):
        with patch.object(obs, "obs_running", return_value=True):
            with self.assertRaisesRegex(RuntimeError, "Close OBS"):
                self.sync(force=True)
            self.assertIn("deferred", self.sync(defer=True))
        self.assertFalse(self.target.exists())
        self.assertFalse((self.state / "obs-sync/applied.json").exists())

    def test_invalid_runtime_json_changes_no_configuration(self):
        profile = self.write("basic/profiles/Untitled/basic.ini", "[General]\nName=Preserve\n")
        self.write("basic/scenes/Untitled.json", "malformed private JSON")
        with self.assertRaises(ValueError):
            self.sync()
        self.assertEqual(profile.read_text(), "[General]\nName=Preserve\n")
        self.assertFalse((self.state / "obs-sync/backups").exists())

    def test_refuses_home_manager_or_stow_owned_live_configuration(self):
        profile = self.target / "basic/profiles/Untitled/basic.ini"
        profile.parent.mkdir(parents=True)
        source = self.defaults / "config/basic/profiles/Untitled/basic.ini"
        original = source.read_bytes()
        profile.symlink_to(source)
        with self.assertRaisesRegex(RuntimeError, "managed links"):
            self.sync()
        self.assertEqual(source.read_bytes(), original)
        self.assertFalse((self.state / "obs-sync/applied.json").exists())

    def test_public_defaults_exclude_credentials_and_machine_grants(self):
        for file in (DEFAULTS / "config").rglob("*"):
            if not file.is_file():
                continue
            text = file.read_text()
            for private_key in ["RestoreToken", "server_password", "CookieId", "AccessToken", "RefreshToken"]:
                self.assertNotIn(private_key, text, str(file))
        service = json.loads((DEFAULTS / "config/basic/profiles/Untitled/service.json").read_text())
        self.assertNotIn("key", service["settings"])

    def test_launcher_skips_itself_and_preserves_arguments(self):
        directory = self.home / "native programs"
        directory.mkdir(parents=True)
        native = directory / "obs"
        native.write_text(f"#!{sys.executable}\nimport json,sys\nprint(json.dumps(sys.argv[1:]))\n")
        native.chmod(0o700)
        launcher = ROOT / "dotfiles/obs/.local/bin/obs"
        environment = dict(os.environ, HOME=str(self.home), XDG_DATA_HOME=str(self.home / "data"),
                           XDG_CONFIG_HOME=str(self.config),
                           PATH=f"{launcher.parent}:{directory}:{os.environ['PATH']}")
        environment.pop("DESKTOP_OBS_BIN", None)
        result = subprocess.run(["bash", str(launcher), "--profile", "Profile with spaces"],
                                env=environment, text=True, capture_output=True, check=True)
        self.assertEqual(json.loads(result.stdout), ["--profile", "Profile with spaces"])
        selection = self.config / "desktop/obs-bin"
        selection.parent.mkdir(parents=True)
        selection.write_text(str(native) + "\n")
        result = subprocess.run(["bash", str(launcher), "--collection", "Collection with spaces"],
                                env=environment, text=True, capture_output=True, check=True)
        self.assertEqual(json.loads(result.stdout), ["--collection", "Collection with spaces"])


if __name__ == "__main__":
    unittest.main()
