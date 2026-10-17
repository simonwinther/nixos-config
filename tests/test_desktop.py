"""Exercise state transitions without access to a compositor, system bus, or real HOME."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

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

    def test_cancelled_screenshot_has_no_side_effects(self):
        result = subprocess.CompletedProcess([], 1, "")
        with patch.object(ctl, "run", return_value=result), patch.object(ctl.subprocess, "run") as binary:
            ctl.capture(["screenshot", "region"])
        binary.assert_not_called()
        self.assertFalse((self.home / "Pictures").exists())


if __name__ == "__main__":
    unittest.main()
