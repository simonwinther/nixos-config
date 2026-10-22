"""Desktop navigation and appearance state, with synthetic clipboard/display data."""
import json
from pathlib import Path
import subprocess
import tomllib
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

import test_desktop as base

ctl = base.ctl
ROOT = base.ROOT


class MenuTests(unittest.TestCase):
    setUp = base.DesktopTests.setUp
    tearDown = base.DesktopTests.tearDown

    def install_menus(self):
        (self.config / "desktop/menus.json").symlink_to(ROOT / "dotfiles/desktop-settings/.config/desktop/menus.json")

    def test_menu_returns_to_parent_and_dispatches_only_selected_action(self):
        self.install_menus()
        replies = [subprocess.CompletedProcess([], 0, "  Style\n"),
                   subprocess.CompletedProcess([], 130, ""),
                   subprocess.CompletedProcess([], 0, "󰀻  Apps\n")]
        with patch.object(ctl, "executable", return_value="/mock/walker"), patch.object(ctl, "run", side_effect=replies) as run, patch.object(ctl, "dispatch") as dispatch:
            ctl.menu([])
        dispatch.assert_called_once_with("launcher", [])
        self.assertEqual([c.kwargs["input"].splitlines()[0] for c in run.call_args_list],
                         ["󰀻  Apps", "󰸌  Theme", "󰀻  Apps"])

    def test_direct_submenu_cancel_exits_without_dispatch(self):
        self.install_menus()
        with patch.object(ctl, "executable", return_value="/mock/walker"), patch.object(ctl, "run", return_value=subprocess.CompletedProcess([], 130, "")) as run, patch.object(ctl, "dispatch") as dispatch:
            ctl.menu(["style"])
        self.assertEqual(run.call_count, 1)
        dispatch.assert_not_called()

    def test_menu_does_not_execute_typed_commands(self):
        self.install_menus()
        with patch.object(ctl, "executable", return_value="/mock/walker"), patch.object(ctl, "run", return_value=subprocess.CompletedProcess([], 0, "exec unwanted command")), patch.object(ctl, "dispatch") as dispatch:
            ctl.menu([])
        dispatch.assert_not_called()

    def test_theme_menu_can_select_a_noncurrent_theme(self):
        with patch.object(ctl, "executable", return_value="/mock/walker"), patch.object(ctl, "run", return_value=subprocess.CompletedProcess([], 0, "○  Catppuccin Latte\n")), patch.object(ctl, "dispatch") as dispatch:
            ctl.menu(["theme"])
        dispatch.assert_called_once_with("theme", ["set", "catppuccin-latte"])

    def test_all_menu_destinations_exist_and_package_mutation_is_absent(self):
        menus = json.loads((ROOT / "dotfiles/desktop-settings/.config/desktop/menus.json").read_text())
        dynamic = {"background", "reminder-set", "theme", "font", "config", "power-profile"}
        for group in menus.values():
            for command in group["items"].values():
                if command[0] == "menu":
                    self.assertIn(command[1], set(menus) | dynamic)
                self.assertNotIn(command[0], ("install", "remove", "update", "rebuild"))

    def test_default_ghostty_colors_remain_personal_until_theme_is_selected(self):
        ctl.theme(["init"])
        overlay = self.state / "theme/ghostty.conf"
        self.assertNotIn("theme =", overlay.read_text())
        ctl.theme(["set", "catppuccin-latte", "--no-reload"])
        self.assertIn("theme =\n", overlay.read_text())
        self.assertIn("background = #eff1f5", overlay.read_text())
        ctl.theme(["init"])
        self.assertIn("background = #eff1f5", overlay.read_text())
        with patch.object(ctl, "run"), patch.object(ctl, "restart"):
            ctl.appearance(["terminal-colors", "personal"])
        self.assertNotIn("theme =", overlay.read_text())

    def test_all_palettes_generate_terminal_imports_and_all_walker_views(self):
        for source in (self.config / "desktop/themes").iterdir():
            with self.subTest(theme=source.name):
                ctl.theme(["set", source.name, "--no-reload"])
                parsed = tomllib.loads((self.state / "theme/alacritty.toml").read_text())
                self.assertEqual(parsed["colors"]["primary"]["background"], ctl.colors(source)["background"])
                self.assertIn("font_family JetBrainsMono Nerd Font", (self.state / "theme/kitty.conf").read_text())
                for view in ("rounded", "menu", "clipboard", "clipboard-compact"):
                    directory = self.runtime / "walker/themes" / ("desktop-" + view)
                    self.assertTrue((directory / "style.css").is_file())
                    ET.parse(directory / "layout.xml")
                ET.parse(self.state / "fontconfig.conf")

    def test_font_choice_survives_prepare_and_never_changes_managed_sources(self):
        source = ROOT / "dotfiles/ghostty/.config/ghostty/config"
        before = source.read_bytes()
        with patch.object(ctl, "run", return_value=subprocess.CompletedProcess([], 0, "Test Mono\nJetBrainsMono Nerd Font\n")) as run:
            ctl.font(["set", "Test Mono", "--no-reload"])
        self.assertEqual(run.call_count, 1)
        ctl.prepare_theme()
        self.assertEqual(ctl.selected_font(), "Test Mono")
        self.assertIn('font-family = "Test Mono"', (self.state / "theme/ghostty.conf").read_text())
        self.assertIn("font=Test Mono 11", (self.state / "theme/mako.ini").read_text())
        self.assertIn("Test Mono", (self.state / "fontconfig.conf").read_text())
        self.assertEqual(source.read_bytes(), before)

    def test_unknown_font_does_not_create_state(self):
        with patch.object(ctl, "run", return_value=subprocess.CompletedProcess([], 0, "Test Mono\n")), self.assertRaises(ValueError):
            ctl.font(["set", "unavailable"])
        self.assertFalse((self.state / "state.json").exists())

    def test_scaled_light_bar_keeps_imported_base_rules_outside_managed_files(self):
        directory = self.config / "waybar"
        directory.mkdir()
        base = directory / "style.css"
        light = directory / "style-light.css"
        base.write_text("* { font-size: 13px; padding: 4px; }\n")
        light.write_text('@import "style.css";\n@define-color text #4c4f69;\n')
        before = (base.read_bytes(), light.read_bytes())
        css = ctl.bar_stylesheet(light, 1.5)
        self.assertIn("font-size: 19.5px", css)
        self.assertIn("padding: 6px", css)
        self.assertIn("#4c4f69", css)
        self.assertNotIn("@import", css)
        self.assertIn(str(light), ctl.bar_stylesheet(light, 1.0))
        self.assertEqual((base.read_bytes(), light.read_bytes()), before)

    def test_clipboard_uses_monitor_logical_size_and_keeps_the_existing_binding(self):
        monitor = {"focused": True, "width": 1920, "height": 1080, "scale": 2}
        with patch.object(ctl, "run", return_value=subprocess.CompletedProcess([], 0, json.dumps([monitor]))), patch.object(ctl, "run_application") as launch:
            ctl.launcher(["-m", "clipboard"])
        argv = launch.call_args.args[0]
        self.assertIn("desktop-clipboard-compact", argv)
        self.assertEqual(argv[argv.index("--width") + 1], "880")
        self.assertEqual(argv[argv.index("--height") + 1], "380")
        # Walker cancels fixed wrapper sizing when scroll min/max flags appear.
        self.assertNotIn("--maxheight", argv)
        self.assertNotIn("--minheight", argv)
        self.assertNotIn("--maxwidth", argv)
        self.assertEqual(argv.count("clipboard"), 1)

    def test_explicit_walker_theme_is_not_shadowed_by_default_theme(self):
        with patch.object(ctl, "prepare_theme", return_value=(None, {}, False)), patch.object(ctl, "executable", return_value="/mock/walker"), patch.object(ctl.os, "execv") as execute:
            ctl.run_application(["walker", "--theme", "desktop-clipboard"])
        argv = execute.call_args.args[1]
        self.assertEqual(argv.count("--theme"), 1)
        self.assertEqual(argv[-1], "desktop-clipboard")

    def test_lock_background_falls_back_when_file_is_missing_or_reset(self):
        target = self.config / "hypr"
        target.mkdir()
        (target / "hyprlock.conf").symlink_to(ROOT / "dotfiles/hypr/.config/hypr/hyprlock.conf")
        image = self.home / "lock image.png"
        image.write_bytes(b"synthetic image")
        ctl.appearance(["lock-background", str(image)])
        self.assertIn(str(self.state / "lock-background"), ctl.lock_config())
        image.unlink()
        self.assertIn(str(self.state / "background"), ctl.lock_config())
        ctl.appearance(["lock-background", "reset"])
        self.assertNotIn("lockBackground", ctl.state())

    def test_screensaver_choice_is_persistent_and_custom_art_is_writable(self):
        artwork = self.data / "screensavers"
        artwork.mkdir(parents=True)
        (artwork / "naruto.txt").write_text("synthetic art")
        with patch.object(ctl, "launch") as editor:
            ctl.screensaver(["edit"])
        self.assertEqual(ctl.state()["screensaver"], "custom")
        self.assertEqual((self.state / "screensaver.txt").read_text(), "synthetic art")
        editor.assert_called_once_with(["editor", str(self.state / "screensaver.txt")])
        ctl.screensaver(["set", "tomoe-sharingan"])
        self.assertEqual(ctl.state()["screensaver"], "tomoe-sharingan")


if __name__ == "__main__":
    unittest.main()
