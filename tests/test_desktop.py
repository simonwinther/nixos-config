"""Exercise state transitions without access to a compositor, system bus, or real HOME."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "dotfiles/desktop-tools/.local/share/desktop-tools/desktopctl.py"
spec = importlib.util.spec_from_file_location("desktopctl_test", SCRIPT)
ctl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ctl)


class DesktopTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)
        self.config = self.home / ".config"
        self.state = self.home / ".local/state/desktop"
        self.runtime = self.home / "runtime/desktop"
        self.data = self.home / ".local/share"
        self.config.mkdir()
        for source, target in [
            ("appearance/.config/desktop/themes", "desktop/themes"),
            ("appearance/.config/desktop/settings.json", "desktop/settings.json"),
            ("walker/.config/walker/templates", "walker/templates"),
        ]:
            destination = self.config / target
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.symlink_to(ROOT / "dotfiles" / source)
        self.globals = patch.multiple(ctl, HOME=self.home, CONFIG=self.config, STATE=self.state,
                                      RUNTIME=self.runtime, DATA=self.data)
        self.globals.start()
        self.env = patch.dict(os.environ, {"HOME": str(self.home), "XDG_CONFIG_DIRS": "/etc/xdg"})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.globals.stop()
        self.temp.cleanup()

    def test_native_host_integration_registers_both_helpers_without_overwriting_links(self):
        directory = self.config / "desktop"
        directory.mkdir(exist_ok=True)
        for template, name in [("native-host.json", "audio"), ("project-picker-native-host.json", "projects")]:
            (directory / template).write_text(json.dumps({"name": name, "type": "stdio"}))
        linked = self.config / "chromium/NativeMessagingHosts/projects.json"
        linked.parent.mkdir(parents=True)
        precious = self.home / "precious"
        precious.write_text("preserve")
        linked.symlink_to(precious)
        with patch.object(ctl, "seed_preferences"), patch.object(ctl, "seed_application_preferences"), \
                patch.object(ctl.shutil, "which", side_effect=lambda name: "/mock/bin/" + name):
            ctl.integrate()
        self.assertEqual(precious.read_text(), "preserve")
        self.assertEqual(json.loads((self.config / "google-chrome/NativeMessagingHosts/projects.json").read_text())["path"],
                         "/mock/bin/project-picker-host")
        self.assertEqual(json.loads((linked.parent / "audio.json").read_text())["path"],
                         "/mock/bin/chatgpt-dictate-audio-duck-host")

    def test_application_defaults_preserve_existing_dconf_and_seed_once(self):
        target = self.config / "desktop/applications.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps({"org.gnome.nautilus.preferences": {"default-folder-viewer": "list-view"},
                                      "org.gnome.nautilus.icon-view": {"default-zoom-level": "small"}}))
        def fake_run(command, **kwargs):
            if command[:2] == ["dconf", "read"]:
                return Mock(returncode=0, stdout="'icon-view'" if command[-1].endswith("default-folder-viewer") else "")
            return Mock(returncode=0)
        with patch.object(ctl.shutil, "which", return_value="/mock/tool"), patch.object(ctl, "run", side_effect=fake_run) as calls:
            ctl.seed_application_preferences()
            settings = [call.args[0] for call in calls.call_args_list if call.args[0][0] == "gsettings"]
            self.assertEqual(settings, [["gsettings", "set", "org.gnome.nautilus.icon-view", "default-zoom-level", '\"small\"']])
            calls.reset_mock()
            ctl.seed_application_preferences()
            calls.assert_not_called()

    def test_every_palette_renders_without_modifying_managed_files(self):
        themes = self.config / "desktop/themes"
        for theme in sorted(themes.iterdir()):
            with self.subTest(theme=theme.name):
                colors_before = (theme / "colors.toml").read_bytes()
                ctl.theme(["set", theme.name, "--no-reload"])
                self.assertEqual(ctl.selected_theme(), theme.name)
                self.assertTrue((self.state / "theme/hyprland.conf").is_file())
                self.assertTrue((self.runtime / "walker/themes/desktop-rounded/style.css").is_file())
                self.assertEqual((theme / "colors.toml").read_bytes(), colors_before)

    def test_light_marker_tracks_switches(self):
        ctl.theme(["set", "catppuccin-latte", "--no-reload"])
        self.assertTrue((self.state / "theme/light.mode").exists())
        ctl.theme(["set", "tokyoled", "--no-reload"])
        self.assertFalse((self.state / "theme/light.mode").exists())

    @unittest.skipUnless(shutil.which("matugen"), "Matugen integration runs in the Nix check")
    def test_image_palette_is_generated_outside_managed_configuration(self):
        image = ROOT / "dotfiles/wallpapers/.local/share/wallpapers/tokyoled/digital-art/background.png"
        ctl.theme(["generate", str(image), "--no-reload"])
        name = ctl.selected_theme()
        self.assertTrue(name.startswith("generated-"))
        self.assertEqual(ctl.theme_path(name).parent, self.data / "desktop/themes")
        self.assertEqual(ctl.colors(ctl.theme_path(name))["background"], ctl.colors(self.state / "theme")["background"])

    def test_atomic_write_does_not_follow_links(self):
        source = self.home / "precious"
        source.write_text("preserve")
        target = self.home / "link"
        target.symlink_to(source)
        with self.assertRaises(ValueError):
            ctl.atomic_write(target, "replace")
        self.assertEqual(source.read_text(), "preserve")

    def test_bad_theme_name_never_escapes_theme_roots(self):
        for name in ["../../etc", "/etc", "absent"]:
            with self.subTest(name=name), self.assertRaises(ValueError):
                ctl.theme(["set", name, "--no-reload"])

    def test_seed_preferences_preserves_existing_and_linked_settings(self):
        source = self.data / "desktop-defaults/config/htop"
        source.mkdir(parents=True)
        (source / "htoprc").write_text("initial preference")
        ctl.seed_preferences()
        target = self.config / "htop/htoprc"
        self.assertEqual(target.read_text(), "initial preference")
        target.write_text("interactive preference")
        ctl.seed_preferences()
        self.assertEqual(target.read_text(), "interactive preference")
        target.unlink()
        destination = self.home / "precious"
        destination.write_text("keep linked content")
        target.symlink_to(destination)
        ctl.seed_preferences()
        self.assertEqual(destination.read_text(), "keep linked content")

    def test_initial_state_does_not_restore_a_deliberately_removed_toggle(self):
        source = self.data / "desktop-defaults/state/toggles"
        source.mkdir(parents=True)
        (source / "suspend-off").write_text("")
        ctl.seed_preferences()
        target = self.state / "toggles/suspend-off"
        self.assertTrue(target.exists())
        target.unlink()
        ctl.seed_preferences()
        self.assertFalse(target.exists())

    def test_bar_toggle_preserves_visibility_choice(self):
        disabled = self.state / "toggles/waybar-off"
        with patch.object(ctl, "run", return_value=subprocess.CompletedProcess([], 0)):
            ctl.toggle(["bar"])
        self.assertTrue(disabled.exists())
        with patch.object(ctl, "run", return_value=subprocess.CompletedProcess([], 1)):
            ctl.toggle(["bar"])
        self.assertFalse(disabled.exists())

    def test_notification_mode_matches_theme_rules(self):
        with patch.object(ctl, "run") as run:
            ctl.toggle(["notifications"])
        run.assert_called_once_with(["makoctl", "mode", "-t", "do-not-disturb"])

    def test_refuses_to_disable_only_monitor(self):
        result = subprocess.CompletedProcess([], 0, json.dumps([{"name": "eDP-1", "disabled": False}]))
        with patch.object(ctl, "run", return_value=result), self.assertRaises(ValueError):
            ctl.display(["internal", "off"])
        self.assertFalse((self.state / "toggles/hypr/internal-display.conf").exists())

    def test_duplicate_lock_request_does_not_wait_and_relock_after_unlock(self):
        with ctl.state_lock("screen-lock"), patch.object(ctl, "prepare_theme") as prepare:
            ctl.lock_worker(["--only"])
        prepare.assert_not_called()

    def test_idle_toggle_leaves_sleep_coordinator_running(self):
        marker = self.runtime / "idle-enabled"
        with patch.object(ctl, "run") as calls:
            ctl.toggle(["idle"])
            self.assertTrue(marker.exists())
            ctl.toggle(["idle"])
            self.assertFalse(marker.exists())
        self.assertEqual([c.args[0] for c in calls.call_args_list],
                         [["systemctl", "--user", "restart", "desktop-hypridle.service"]] * 2)

    def test_session_recovers_only_failed_graphics_services(self):
        failed = "● desktop-awww.service loaded failed failed Wallpaper\nku-vpn.service loaded failed failed VPN\ndesktop-lock.service loaded failed failed Lock\n"
        with patch.object(ctl, "run", return_value=subprocess.CompletedProcess([], 0, failed)) as calls:
            ctl.recover_graphics_services()
        self.assertEqual([c.args[0] for c in calls.call_args_list][1:], [
            ["systemctl", "--user", "reset-failed", "desktop-awww.service"],
            ["systemctl", "--user", "start", "desktop-awww.service"]])

    def test_idle_worker_chooses_sleep_only_unless_explicitly_enabled(self):
        with patch.object(ctl, "executable", return_value="/mock/hypridle"), patch.object(ctl.os, "execv") as execute:
            ctl.idle_worker([])
            self.assertTrue(execute.call_args.args[1][-1].endswith("hypridle-sleep.conf"))
            ctl.atomic_write(self.runtime / "idle-enabled", "")
            ctl.idle_worker([])
            self.assertTrue(execute.call_args.args[1][-1].endswith("/hypridle.conf"))

    def test_system_sleep_uses_guarded_rust_action_and_propagates_failure(self):
        with patch.object(ctl, "executable", return_value="/mock/desktop-ring"), \
             patch.object(ctl, "run", return_value=subprocess.CompletedProcess([], 0)) as calls:
            ctl.dispatch("power", ["suspend"])
            calls.assert_called_once_with(["/mock/desktop-ring", "action", '{"kind":"suspend"}'], check=False, capture=True)
        with patch.object(ctl, "executable", return_value="/mock/desktop-ring"), \
             patch.object(ctl, "run", return_value=subprocess.CompletedProcess([], 1, "", "Lock protection unavailable")), \
             self.assertRaisesRegex(ValueError, "Lock protection unavailable"):
            ctl.dispatch("power", ["suspend"])

    def test_cancelled_screenshot_has_no_side_effects(self):
        result = subprocess.CompletedProcess([], 1, "")
        freezer = Mock()
        freezer.poll.return_value = None
        with patch.object(ctl, "run", return_value=result), patch.object(ctl.subprocess, "run") as binary, patch.object(ctl, "background", return_value=freezer), patch.object(ctl.time, "sleep"):
            ctl.capture(["screenshot", "region"])
        binary.assert_not_called()
        freezer.terminate.assert_called_once()
        self.assertFalse((self.home / "Pictures").exists())

    def test_copy_only_capture_keeps_freeze_until_pixels_are_read(self):
        events = []
        freezer = Mock()
        freezer.poll.return_value = None
        freezer.terminate.side_effect = lambda: events.append("thaw")
        def pixels(*args, **kwargs):
            events.append("pixels")
            return subprocess.CompletedProcess([], 0, b"image bytes")
        with patch.object(ctl, "background", return_value=freezer), patch.object(ctl.time, "sleep"), patch.object(ctl, "screenshot_geometry", return_value="0,0 100x100"), patch.object(ctl.subprocess, "run", side_effect=pixels), patch.object(ctl, "copy_data") as copy:
            ctl.capture(["screenshot", "region", "copy"])
        self.assertEqual(events, ["pixels", "thaw"])
        copy.assert_called_once_with(b"image bytes", "image/png")
        self.assertFalse((self.home / "Pictures").exists())

    def test_save_only_capture_uses_reference_names_and_preserves_clipboard(self):
        with patch.object(ctl, "screenshot_geometry", return_value="0,0 100x100"), patch.object(ctl.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, b"image bytes")), patch.object(ctl, "copy_data") as copy:
            ctl.capture(["screenshot", "fullscreen", "save"])
        images = list((self.home / "Pictures").glob("screenshot-*.png"))
        self.assertEqual(len(images), 1)
        self.assertEqual(images[0].read_bytes(), b"image bytes")
        copy.assert_not_called()


if __name__ == "__main__":
    unittest.main()
