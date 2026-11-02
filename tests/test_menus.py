"""Desktop navigation and appearance state, with synthetic clipboard/display data."""
import json
import os
from pathlib import Path
import shutil
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

    def test_menu_routes_to_native_stack_without_dispatching_a_selection(self):
        self.install_menus()
        with patch.object(ctl.bar_config, "open_panel", return_value=True) as opened, patch.object(ctl, "dispatch") as dispatch:
            ctl.menu([])
        self.assertEqual(opened.call_args.args[1], "menu/main")
        dispatch.assert_not_called()

    def test_direct_submenu_uses_native_surface_when_bar_is_not_running(self):
        self.install_menus()
        with patch.object(ctl, "run_application") as launch, patch.object(ctl, "dispatch") as dispatch:
            ctl.menu(["style"])
        launch.assert_called_once_with(["desktop-bar-native", "--menu", "menu/style"])
        dispatch.assert_not_called()

    def test_unknown_menu_does_not_execute_commands(self):
        self.install_menus()
        with patch.object(ctl, "run_application") as launch, patch.object(ctl, "dispatch") as dispatch:
            with self.assertRaisesRegex(ValueError, "Unknown menu"):
                ctl.menu(["exec unwanted command"])
        launch.assert_not_called()
        dispatch.assert_not_called()

    def test_theme_chooser_uses_the_native_carousel(self):
        with patch.object(ctl, "run_application") as launch:
            ctl.menu(["theme"])
        launch.assert_called_once_with(["desktop-bar-native", "--menu", "themes"])

    def test_all_menu_destinations_exist_and_package_mutation_is_absent(self):
        menus = json.loads((ROOT / "dotfiles/desktop-settings/.config/desktop/menus.json").read_text())
        dynamic = {"background", "reminder-set", "theme", "font", "bar", "config", "power-profile"}
        for group in menus.values():
            for command in group["items"].values():
                if command[0] == "menu":
                    self.assertIn(command[1], set(menus) | dynamic)
                self.assertNotIn(command[0], ("install", "remove", "update", "rebuild"))

    def test_active_keybindings_query_live_overrides_instead_of_source(self):
        bindings = [{"modmask": 68, "key": "SPACE", "description": "Wallpaper grid"}]
        with patch.object(ctl, "run", return_value=subprocess.CompletedProcess([], 0, json.dumps(bindings))) as run:
            self.assertEqual(ctl.active_keybindings(), bindings)
        run.assert_called_once_with(["hyprctl", "-j", "binds"], capture=True)

    def test_keybindings_open_native_panel_without_launching_a_picker(self):
        with patch.object(ctl.bar_config, "open_panel", return_value=True) as opened, patch.object(ctl, "run") as run:
            ctl.keybindings()
        self.assertEqual(opened.call_args.args[1], "keybindings")
        run.assert_not_called()

    def test_keybindings_recover_lua_keycodes_from_live_text_by_identity(self):
        bindings = [
            {"modmask": 64, "submap": "", "key": "", "keycode": 0,
             "description": "Desktop display controls", "dispatcher": "__lua", "arg": "10"},
            {"modmask": 64, "submap": "", "key": "", "keycode": 0,
             "description": "Desktop display controls", "dispatcher": "__lua", "arg": "11"},
            {"modmask": 0, "key": "PRINT", "description": "Screenshot"},
        ]
        # Reverse the live text records and keep their descriptions identical.
        text = ('bindd\n\tmodmask: 64\n\tsubmap: \n\tkey: SUPER + code:11\n'
                '\tkeycode: 0\n\tcatchall: false\n\tdescription: Desktop display controls\n'
                '\tdispatcher: __lua\n\targ: 11\n\n'
                'bindd\n\tmodmask: 64\n\tsubmap: \n\tkey: SUPER + code:10\n'
                '\tkeycode: 0\n\tcatchall: false\n\tdescription: Desktop display controls\n'
                '\tdispatcher: __lua\n\targ: 10\n\n')
        replies = [subprocess.CompletedProcess([], 0, json.dumps(bindings)),
                   subprocess.CompletedProcess([], 0, text), subprocess.CompletedProcess([], 130)]
        with patch.object(ctl, "executable", return_value="/mock/desktop-bar-native"), patch.object(ctl, "run", side_effect=replies) as run:
            bindings = ctl.active_keybindings()
        self.assertEqual(run.call_args_list[1].args[0], ["hyprctl", "binds"])
        self.assertEqual([binding.get("display_key") for binding in bindings[:2]], ["SUPER + code:10", "SUPER + code:11"])

    def test_keybindings_reject_missing_or_ambiguous_live_keycodes(self):
        bindings = [{"modmask": 64, "submap": "", "key": "", "keycode": 0,
                     "description": "Workspace 1", "dispatcher": "__lua", "arg": "10"}]
        record = ('bindd\n\tmodmask: 64\n\tsubmap: \n\tkey: SUPER + code:10\n'
                  '\tdescription: Workspace 1\n\tdispatcher: __lua\n\targ: 10\n\n')
        for text in ("", record.replace("arg: 10", "arg: 11"), record + record.replace("code:10", "code:11")):
            replies = [subprocess.CompletedProcess([], 0, json.dumps(bindings)), subprocess.CompletedProcess([], 0, text)]
            with self.subTest(text=text), patch.object(ctl, "run", side_effect=replies) as run, patch.object(ctl, "prepare_theme") as theme:
                with self.assertRaisesRegex(ValueError, "unambiguous key"):
                    bindings = ctl.active_keybindings()
                self.assertEqual(run.call_count, 2)
                theme.assert_not_called()

    def test_keybinding_inspection_propagates_live_query_failures(self):
        for reply, error in [(subprocess.CalledProcessError(1, ["hyprctl"]), subprocess.CalledProcessError),
                             (subprocess.CompletedProcess([], 0, "invalid json"), ValueError)]:
            with patch.object(ctl, "run", side_effect=[reply]):
                with self.assertRaises(error):
                    ctl.active_keybindings()

    def test_focus_shortcut_launches_default_command_or_matches_title_without_case(self):
        with patch.object(ctl, "run", return_value=subprocess.CompletedProcess([], 0, "[]")), \
                patch.object(ctl.shutil, "which", return_value="uwsm-app"), \
                patch.object(ctl.os, "execvp") as execute:
            ctl.launch(["focus", "spotify"])
        execute.assert_called_once_with("uwsm-app", ["uwsm-app", "--", "spotify"])
        windows = [{"class": "electron", "title": "Spotify", "address": "0x123"}]
        with patch.object(ctl, "run", side_effect=[subprocess.CompletedProcess([], 0, json.dumps(windows)), subprocess.CompletedProcess([], 0)]) as run, patch.object(ctl.os, "execvp") as execute:
            ctl.launch(["focus", "spotify"])
        self.assertIn("address:0x123", run.call_args.args[0][-1])
        execute.assert_not_called()

    def test_hardware_catalog_omits_touchpad_on_stationary_desktop(self):
        import bar_catalog
        from unittest.mock import patch
        import io
        from contextlib import redirect_stdout
        self.install_menus()
        result = subprocess.CompletedProcess([], 0, '{"mice": []}')
        with patch.object(bar_catalog.subprocess, "run", return_value=result), redirect_stdout(io.StringIO()) as output:
            ctl.bar(["catalog", "menu/hardware"])
        commands = [entry["command"] for entry in json.loads(output.getvalue())]
        self.assertNotIn(["toggle", "touchpad"], commands)
        self.assertIn(["exec", "desktop-ring", "menu"], commands)

    def test_reminders_show_messages_and_clear_with_visible_feedback(self):
        with patch.object(ctl, "run", return_value=subprocess.CompletedProcess([], 0, "")) as run, patch.object(ctl, "notify") as notify:
            ctl.reminder(["5", "Check the oven"])
            ctl.reminder(["show"])
            self.assertEqual(notify.call_args.args[0], "Upcoming reminders")
            self.assertIn("Check the oven", notify.call_args.args[1])
            self.assertIn("5 min", notify.call_args.args[1])
            ctl.reminder(["clear"])
            self.assertFalse(list((self.runtime / "reminders").glob("*.json")))
            ctl.reminder(["show"])
            notify.assert_called_with("Upcoming reminders", "No outstanding reminders")
        self.assertEqual(run.call_args_list[0].args[0][-1], "Check the oven")

    def test_share_selection_can_cancel_and_paths_remain_single_arguments(self):
        with patch.object(ctl, "run", return_value=subprocess.CompletedProcess([], 1, "")) as run:
            ctl.share(["file"])
        self.assertEqual(run.call_count, 1)
        path = self.home / "a file with spaces.txt"
        path.write_text("synthetic share")
        with patch.object(ctl, "run") as run:
            ctl.share(["file", str(path)])
        run.assert_called_once_with(["localsend", "--headless", "send", str(path)])

    def test_shared_clipboard_image_is_private_and_survives_gui_handoff(self):
        def fake_copy(command, **kwargs):
            kwargs["stdout"].write(b"synthetic image")
            return subprocess.CompletedProcess(command, 0)
        def share_run(command, **kwargs):
            if command[:2] == ["wl-paste", "--list-types"]:
                return subprocess.CompletedProcess(command, 0, "image/png\n")
            if command[0] == "wl-paste":
                return fake_copy(command, **kwargs)
            return subprocess.CompletedProcess(command, 0)
        with patch.object(ctl, "run", side_effect=share_run) as run:
            ctl.share(["clipboard"])
        path = Path(run.call_args.args[0][-1])
        self.assertEqual(path.suffix, ".png")
        self.assertEqual(path.read_bytes(), b"synthetic image")
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_about_art_can_be_edited_previewed_and_reset_without_managed_writes(self):
        with patch.object(ctl, "launch") as editor:
            ctl.about(["edit"])
        editor.assert_called_once_with(["editor", str(self.state / "about.txt")])
        (self.state / "about.txt").write_text("synthetic artwork")
        with patch.object(ctl, "terminal") as terminal:
            ctl.about([])
        self.assertIn("--logo-type file-raw", terminal.call_args.args[0][-1])
        with patch.object(ctl, "notify"):
            ctl.about(["reset"])
        with patch.object(ctl, "terminal") as terminal:
            ctl.about([])
        self.assertNotIn("--logo", terminal.call_args.args[0][-1])
        self.assertEqual((self.state / "about.txt").read_text(), "synthetic artwork")

    def test_automatic_saver_preserves_disabled_preference_and_uses_common_worker(self):
        ctl.atomic_write(self.state / "toggles/screensaver-off", "")
        with patch.object(ctl.os, "execvp") as execute:
            ctl.screensaver(["idle"])
        execute.assert_not_called()
        with patch.object(ctl, "notify"):
            ctl.toggle(["screensaver"])
        ctl.screensaver(["set", "matrix"])
        with patch.object(ctl, "run", side_effect=[subprocess.CompletedProcess([], 1, ""), subprocess.CompletedProcess([], 0, "[]")]), patch.object(ctl.os, "execvp") as execute:
            ctl.screensaver(["idle"])
        self.assertIn("screensaver-worker", execute.call_args.args[1])
        self.assertNotIn("cmatrix", execute.call_args.args[1])
        for replies in ([subprocess.CompletedProcess([], 0, "123")],
                        [subprocess.CompletedProcess([], 1, ""), subprocess.CompletedProcess([], 0, '[{"class":"org.desktop.screensaver"}]')]):
            with patch.object(ctl, "run", side_effect=replies), patch.object(ctl.os, "execvp") as execute:
                ctl.screensaver(["idle"])
            execute.assert_not_called()

    def test_new_configuration_entries_resolve_to_editable_source(self):
        with patch.dict(os.environ, {"DOTFILES": str(ROOT / "dotfiles")}), patch.object(ctl, "launch") as editor:
            for name in ("Application launchers", "Default terminal", "File and URL handlers", "SwayOSD", "XCompose", "Hyprland configuration"):
                ctl.edit_config([name])
                path = Path(editor.call_args.args[0][-1])
                self.assertTrue(path.is_file(), path)
                self.assertTrue(path.is_relative_to(ROOT / "dotfiles"))

    @unittest.skipUnless(shutil.which("magick"), "Image conversion runs in the Nix check")
    def test_image_art_preserves_source_and_generates_bounded_braille(self):
        image = self.home / "white logo with spaces.png"
        subprocess.run(["magick", "-size", "80x40", "xc:none", "-fill", "white", "-draw", "rectangle 10,5 60,35", str(image)], check=True)
        before = image.read_bytes()
        with patch.object(ctl, "notify"):
            ctl.screensaver(["image", str(image)])
            ctl.about(["image", str(image)])
        self.assertEqual(image.read_bytes(), before)
        self.assertEqual(ctl.state()["screensaver"], "custom")
        for path, width in ((self.state / "screensaver.txt", 80), (self.state / "about.txt", 54)):
            art = path.read_text()
            self.assertTrue(any(0x2800 < ord(char) <= 0x28ff for char in art))
            self.assertLessEqual(len(art.splitlines()), 26)
            self.assertLessEqual(max(map(len, art.splitlines())), width)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        with patch.object(ctl, "run", return_value=subprocess.CompletedProcess([], 1, "")):
            self.assertIsNone(ctl.image_art([]))

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

    def test_all_palettes_generate_terminal_imports_and_clipboard_colors(self):
        for source in (self.config / "desktop/themes").iterdir():
            with self.subTest(theme=source.name):
                ctl.theme(["set", source.name, "--no-reload"])
                parsed = tomllib.loads((self.state / "theme/alacritty.toml").read_text())
                self.assertEqual(parsed["colors"]["primary"]["background"], ctl.colors(source)["background"])
                self.assertIn("font_family JetBrainsMono Nerd Font", (self.state / "theme/kitty.conf").read_text())
                self.assertIn("@define-color text", (self.state / "theme/clipboard.css").read_text())
                self.assertFalse((self.runtime / "walker").exists())
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


    def test_fallback_clipboard_uses_the_same_native_surface(self):
        with patch.object(ctl, "remember_clipboard_target"), patch.object(ctl, "run"), patch.object(ctl, "run_application") as launch:
            ctl.launcher(["-m", "clipboard"])
        launch.assert_called_once_with(["desktop-bar-native", "--menu", "clipboard"])

    def test_dmenu_passes_literal_input_to_native_request_response_picker(self):
        with patch.object(ctl, "run_application") as launch, patch.object(ctl, "remember_clipboard_target") as remember:
            ctl.launcher(["--dmenu", "--placeholder", "Literal $HOME; title"])
        launch.assert_called_once_with(["desktop-bar-native", "--dmenu", "--placeholder", "Literal $HOME; title"])
        remember.assert_not_called()

    def test_clipboard_paste_waits_for_picker_and_uses_terminal_shortcut(self):
        ctl.atomic_write(self.runtime / "clipboard-target.json", '{"address":"0x123"}')
        layers = {"monitor": {"levels": {"3": [{"namespace": "desktop-bar-panel-eDP-1"}]}}}
        replies = [subprocess.CompletedProcess([], 0, json.dumps(layers)),
                   subprocess.CompletedProcess([], 0, "{}"),
                   subprocess.CompletedProcess([], 0, '{"address":"0x123","class":"com.mitchellh.ghostty"}'),
                   subprocess.CompletedProcess([], 0)]
        with patch.object(ctl, "run", side_effect=replies) as run, patch.object(ctl.time, "sleep") as sleep:
            ctl.clipboard_paste([])
        sleep.assert_called_once_with(0.02)
        self.assertEqual(run.call_args.args[0], ["hyprctl", "eval", 'hl.dispatch(hl.dsp.send_shortcut({ mods = "CTRL SHIFT", key = "V", window = "address:0x123" }))'])

    def test_clipboard_paste_uses_ctrl_v_for_gui_and_refuses_changed_focus(self):
        ctl.atomic_write(self.runtime / "clipboard-target.json", '{"address":"0x123"}')
        for address in ("0x123", "0x456"):
            replies = [subprocess.CompletedProcess([], 0, "{}"),
                       subprocess.CompletedProcess([], 0, json.dumps({"address": address, "class": "chromium"})),
                       subprocess.CompletedProcess([], 0)]
            with patch.object(ctl, "run", side_effect=replies) as run:
                if address == "0x123":
                    ctl.clipboard_paste([])
                    self.assertEqual(run.call_args.args[0], ["hyprctl", "eval", 'hl.dispatch(hl.dsp.send_shortcut({ mods = "CTRL", key = "V", window = "address:0x123" }))'])
                else:
                    with self.assertRaisesRegex(ValueError, "target changed"):
                        ctl.clipboard_paste([])
                    self.assertEqual(run.call_count, 2)

    def test_clipboard_paste_timeout_never_sends_keys(self):
        ctl.atomic_write(self.runtime / "clipboard-target.json", '{"address":"0x123"}')
        layers = {"monitor": {"levels": {"3": [{"namespace": "clipboard-picker"}]}}}
        with patch.object(ctl, "run", return_value=subprocess.CompletedProcess([], 0, json.dumps(layers))) as run, \
                patch.object(ctl.time, "monotonic", side_effect=[0, 0, 3]), patch.object(ctl.time, "sleep"):
            with self.assertRaisesRegex(ValueError, "still has focus"):
                ctl.clipboard_paste([])
        self.assertEqual(run.call_args.args[0], ["hyprctl", "-j", "layers"])

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
