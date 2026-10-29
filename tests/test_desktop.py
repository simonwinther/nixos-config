"""Exercise state transitions without access to a compositor, system bus, or real HOME."""
from concurrent.futures import ThreadPoolExecutor
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "dotfiles/desktop-tools/.local/share/desktop-tools/desktopctl.py"
spec = importlib.util.spec_from_file_location("desktopctl_test", SCRIPT)
ctl = importlib.util.module_from_spec(spec)
with patch.object(sys, "path", [str(SCRIPT.parent), *sys.path]):
    spec.loader.exec_module(ctl)


class DesktopTests(unittest.TestCase):
    def test_break_reminders_start_without_a_private_coop_invite(self):
        target = self.config / "breakd/config.toml"
        target.parent.mkdir()
        target.write_text('[coop]\nmode = "host"\nroom_token = ""\n'
                          'relay_url = "ws://example.invalid/ws"\n[other]\nkeep = true\n')
        ctl.prepare_break_reminders()
        settings = ctl.tomllib.loads(target.read_text())
        self.assertEqual(settings["coop"]["mode"], "off")
        self.assertTrue(settings["other"]["keep"])
        self.assertEqual(target.stat().st_mode & 0o777, 0o600)

    def test_break_reminders_preserve_an_existing_private_invite(self):
        target = self.config / "breakd/config.toml"
        target.parent.mkdir()
        source = '[coop]\nmode = "guest"\nroom_token = "0123456789abcdef0123456789abcdef"\n'
        target.write_text(source)
        ctl.prepare_break_reminders()
        self.assertEqual(target.read_text(), source)

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

    def test_clipboard_routes_native_picker_to_original_window(self):
        self.runtime.mkdir(parents=True)
        (self.runtime / "clipboard-target.json").write_text(json.dumps({"address": "0x123"}))
        with patch.object(ctl, "remember_clipboard_target") as remember, \
                patch.object(ctl, "executable", return_value="/mock/clipboard-picker-native"), \
                patch.object(ctl, "run") as run, patch.object(ctl, "run_application") as launch:
            ctl.clipboard(["-m", "clipboard"])
        remember.assert_called_once()
        run.assert_called_once_with(["systemctl", "--user", "start", "desktop-elephant.service"], check=False)
        launch.assert_called_once_with(["/mock/clipboard-picker-native", "--target", "0x123"])

    def test_clipboard_keeps_existing_picker_until_native_is_installed(self):
        with patch.object(ctl, "remember_clipboard_target"), \
                patch.object(ctl, "executable", side_effect=ValueError("not installed")), \
                patch.object(ctl, "run", return_value=Mock(stdout="[]")), \
                patch.object(ctl, "run_application") as launch:
            ctl.clipboard(["-m", "clipboard"])
        self.assertEqual(launch.call_args.args[0][0], "walker")

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

    def test_seed_preferences_seeds_home_dotfiles_once(self):
        source = self.data / "desktop-defaults/home/.claude"
        source.mkdir(parents=True)
        (source / "settings.json").write_text('{"theme": "auto"}')
        ctl.seed_preferences()
        target = self.home / ".claude/settings.json"
        self.assertEqual(target.read_text(), '{"theme": "auto"}')
        target.write_text('{"theme": "light"}')
        ctl.seed_preferences()
        self.assertEqual(target.read_text(), '{"theme": "light"}')

    def test_theme_switch_uses_theme_background_unless_one_is_already_chosen(self):
        backgrounds = ctl.theme_path("catppuccin-latte") / "backgrounds"
        first = sorted(p.resolve() for p in backgrounds.glob("*") if p.is_file())[0]
        with patch.object(ctl, "run"), patch.object(ctl, "restart"), patch.object(ctl, "apply_appearance"), \
                patch.object(ctl, "wallpaper") as wallpaper:
            ctl.theme(["set", "catppuccin-latte"])
            wallpaper.assert_called_once_with(["set", str(first)])
            wallpaper.reset_mock()
            ctl.save_state({**ctl.state(), "wallpaper": str(first)})
            ctl.theme(["set", "catppuccin-latte"])
            wallpaper.assert_not_called()

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
        with ctl.state_lock("screen-lock"), patch.object(ctl, "prepare_theme") as prepare, \
                patch.object(ctl, "run") as run, patch.object(ctl, "background") as background, \
                patch.object(ctl.subprocess, "Popen") as popen, patch.object(ctl, "lock_config") as config:
            ctl.lock_worker(["--only"])
        prepare.assert_not_called()
        run.assert_not_called()
        background.assert_not_called()
        popen.assert_not_called()
        config.assert_not_called()

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
        with patch.object(ctl, "run", return_value=result) as binary, patch.object(ctl, "background", return_value=freezer), patch.object(ctl.time, "sleep"):
            ctl.capture(["screenshot", "region"])
        self.assertEqual(binary.call_count, 1)
        self.assertEqual(binary.call_args.args[0], ["slurp"])
        freezer.close.assert_called_once()
        self.assertFalse((self.home / "Pictures").exists())

    def test_copy_only_capture_keeps_freeze_until_pixels_are_read(self):
        events = []
        freezer = Mock()
        freezer.poll.return_value = None
        freezer.close.side_effect = lambda: events.append("thaw")
        def pixels(*args, **kwargs):
            events.append("pixels")
            return subprocess.CompletedProcess([], 0, b"image bytes")
        with patch.object(ctl, "background", return_value=freezer), patch.object(ctl.time, "sleep"), patch.object(ctl, "screenshot_geometry", return_value="0,0 100x100"), patch.object(ctl, "run", side_effect=pixels), patch.object(ctl, "copy_data") as copy:
            ctl.capture(["screenshot", "region", "copy"])
        self.assertEqual(events, ["pixels", "thaw"])
        copy.assert_called_once_with(b"image bytes", "image/png")
        self.assertFalse((self.home / "Pictures").exists())

    def test_save_only_capture_uses_reference_names_and_preserves_clipboard(self):
        with patch.object(ctl, "screenshot_geometry", return_value="0,0 100x100"), patch.object(ctl, "run", return_value=subprocess.CompletedProcess([], 0, b"image bytes")), patch.object(ctl, "copy_data") as copy:
            ctl.capture(["screenshot", "fullscreen", "save"])
        images = list((self.home / "Pictures").glob("screenshot-*.png"))
        self.assertEqual(len(images), 1)
        self.assertEqual(images[0].read_bytes(), b"image bytes")
        copy.assert_not_called()

    def test_same_second_captures_preserve_each_image_and_report_unique_paths(self):
        images = [b"first image", b"second image"]
        with patch.object(ctl, "screenshot_geometry", return_value="0,0 100x100"), \
                patch.object(ctl, "run", side_effect=[subprocess.CompletedProcess([], 0, image) for image in images]), \
                patch.object(ctl.time, "strftime", return_value="screenshot-2026-10-28_12-00-00"), \
                patch("sys.stdout", new_callable=io.StringIO) as stdout:
            for _ in images:
                ctl.capture(["screenshot", "fullscreen", "save"])
        outputs = [Path(line) for line in stdout.getvalue().splitlines()]
        self.assertEqual(len(set(outputs)), len(images))
        self.assertEqual([output.read_bytes() for output in outputs], images)
        self.assertEqual(set((self.home / "Pictures").iterdir()), set(outputs))
        for output in outputs:
            self.assertTrue(output.match("screenshot-*.png"))

    def test_screenshot_collisions_preserve_existing_files_and_symlinks(self):
        stem = "screenshot-2026-10-28_12-00-00"
        for kind in ("file", "symlink", "dangling-symlink"):
            with self.subTest(kind=kind):
                directory = self.home / kind
                directory.mkdir()
                existing = directory / f"{stem}-{'0' * 32}.png"
                target = self.home / f"{kind}-target"
                if kind == "file":
                    existing.write_bytes(b"previous capture")
                else:
                    if kind == "symlink":
                        target.write_bytes(b"keep linked content")
                    existing.symlink_to(target)
                with patch.object(ctl.time, "strftime", return_value=stem), \
                        patch.object(ctl.uuid, "uuid4", side_effect=[ctl.uuid.UUID(int=0), ctl.uuid.UUID(int=1)]):
                    output = ctl.save_screenshot(directory, b"new capture")
                self.assertNotEqual(output, existing)
                self.assertEqual(output.read_bytes(), b"new capture")
                self.assertEqual(set(directory.iterdir()), {existing, output})
                if kind == "file":
                    self.assertEqual(existing.read_bytes(), b"previous capture")
                else:
                    self.assertTrue(existing.is_symlink())
                    self.assertEqual(existing.readlink(), target)
                    if kind == "symlink":
                        self.assertEqual(target.read_bytes(), b"keep linked content")
                    else:
                        self.assertFalse(target.exists())

    def test_concurrent_screenshots_retry_a_shared_name_without_losing_images(self):
        directory = self.home / "Pictures"
        images = [f"capture {i}".encode() for i in range(4)]
        barrier = threading.Barrier(len(images))
        attempts = threading.local()
        random_uuid = ctl.uuid.uuid4

        def colliding_uuid():
            if not getattr(attempts, "started", False):
                attempts.started = True
                barrier.wait(timeout=10)
                return ctl.uuid.UUID(int=0)
            return random_uuid()

        with patch.object(ctl.time, "strftime", return_value="screenshot-2026-10-28_12-00-00"), \
                patch.object(ctl.uuid, "uuid4", side_effect=colliding_uuid), \
                ThreadPoolExecutor(max_workers=len(images)) as pool:
            outputs = list(pool.map(lambda image: ctl.save_screenshot(directory, image), images))
        self.assertEqual(len(set(outputs)), len(images))
        self.assertEqual([output.read_bytes() for output in outputs], images)
        self.assertEqual(set(directory.iterdir()), set(outputs))

    def test_screenshot_publication_exposes_only_complete_bytes(self):
        directory = self.home / "Pictures"
        image = b"complete screenshot bytes"
        fsync = ctl.os.fsync
        link = ctl.os.link

        def sync_before_publication(descriptor):
            self.assertEqual(list(directory.glob("screenshot-*.png")), [])
            fsync(descriptor)

        def publish(temporary, output):
            self.assertEqual(list(directory.glob("screenshot-*.png")), [])
            self.assertEqual(Path(temporary).read_bytes(), image)
            link(temporary, output)
            self.assertEqual(output.read_bytes(), image)

        with patch.object(ctl.os, "fsync", side_effect=sync_before_publication) as synced, \
                patch.object(ctl.os, "link", side_effect=publish) as published:
            output = ctl.save_screenshot(directory, image)
        synced.assert_called_once()
        published.assert_called_once()
        self.assertEqual(list(directory.iterdir()), [output])

    def test_failed_screenshot_saves_leave_no_published_or_temporary_files(self):
        for operation in ("fsync", "link"):
            with self.subTest(operation=operation):
                directory = self.home / operation
                with patch.object(ctl.os, operation, side_effect=OSError("save failed")), \
                        self.assertRaisesRegex(OSError, "save failed"):
                    ctl.save_screenshot(directory, b"image bytes")
                self.assertEqual(list(directory.iterdir()), [])


class LockTests(unittest.TestCase):
    tearDown = DesktopTests.tearDown

    def setUp(self):
        DesktopTests.setUp(self)
        target = self.config / "hypr/hyprlock.conf"
        target.parent.mkdir()
        target.symlink_to(ROOT / "dotfiles/hypr/.config/hypr/hyprlock.conf")
        self.child = Mock(args=["hyprlock"], **{"poll.return_value": None, "wait.return_value": 0})
        self.child.__enter__ = Mock(return_value=self.child)
        self.child.__exit__ = Mock(return_value=False)
        for name, mock in [
            ("run", Mock(return_value=subprocess.CompletedProcess([], 0))),
            ("background", Mock()),
            ("brightness", Mock()),
        ]:
            setattr(self, name, mock)
            patcher = patch.object(ctl, name, mock)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.popen = self.enterContext(patch.object(ctl, "managed", return_value=self.child))
        self.sleep = self.enterContext(patch.object(ctl.time, "sleep"))
        self.enterContext(patch.object(ctl.shutil, "which", return_value=None))
        self.stderr = self.enterContext(patch("sys.stderr", new_callable=io.StringIO))

    def assert_started(self):
        self.popen.assert_called_with(["hyprlock", "--config", str(self.runtime / "hyprlock.conf")], operation="lock")
        self.child.wait.assert_called_with()
        source = (self.runtime / "hyprlock.conf").read_text()
        self.assertNotIn("source =", source)
        for name in ("color", "inner_color", "outer_color", "font_color", "check_color"):
            self.assertIn(f"${name} = ", source)
        return source

    def test_login_starts_without_preparing_other_appearance_files(self):
        with patch.object(ctl, "prepare_theme", side_effect=ValueError("broken appearance")) as prepare, \
                patch.object(ctl, "state", side_effect=AssertionError("lock must not migrate or recover state")):
            self.assertEqual(ctl.main(["lock-worker", "--only"]), 0)
        prepare.assert_not_called()
        self.assertIn("$color = rgba(0,0,0,1.0)", self.assert_started())
        self.assertFalse((self.state / "theme").exists())
        self.sleep.assert_not_called()
        self.assertNotIn(["hyprctl", "dispatch", "dpms", "off"], [c.args[0] for c in self.run.call_args_list])

    def test_login_falls_back_for_invalid_appearance_state(self):
        for content in ("{", "[]", "null", '{"theme": "absent"}', '{"theme": 42}',
                        '{"font": []}', '{"font": ""}', '{"font": "bad\\nfont"}',
                        '{"font": "bad\\tfont"}', '{"font": "bad\\ud800font"}',
                        '{"lockBackground": {"path": "invalid"}}'):
            with self.subTest(state=content):
                ctl.atomic_write(self.state / "state.json", content)
                self.assertEqual(ctl.main(["lock-worker", "--only"]), 0)
                source = self.assert_started()
                self.assertIn("font_family = JetBrainsMono Nerd Font", source)
                self.assertIn("$color = rgba(000000ff)", source)
                self.assertEqual((self.state / "state.json").read_text(), content)
        self.assertIn("appearance", self.stderr.getvalue())

    def test_selected_theme_font_and_background_work_without_preparation(self):
        image = self.home / "lock image.png"
        image.write_bytes(b"image")
        ctl.save_state({"theme": "catppuccin-latte", "font": "Test Mono", "lockBackground": str(image)})
        self.assertEqual(ctl.main(["lock-worker", "--only"]), 0)
        source = self.assert_started()
        self.assertIn("$color = rgba(eff1f5ff)", source)
        self.assertIn("font_family = Test Mono", source)
        self.assertIn(str(self.state / "lock-background"), source)
        self.assertEqual((self.state / "lock-background").resolve(), image)
        self.assertFalse((self.state / "theme").exists())

    def test_login_falls_back_for_invalid_settings_and_palette(self):
        settings = self.config / "desktop/settings.json"
        settings.unlink()
        for content in ("{", "[]", '{"defaultFont": null}'):
            with self.subTest(settings=content):
                settings.write_text(content)
                self.assertEqual(ctl.main(["lock-worker", "--only"]), 0)
                self.assert_started()
        settings.write_text("{}")
        palette = self.data / "desktop/themes/broken/colors.toml"
        palette.parent.mkdir(parents=True)
        palette.write_text("not valid = [")
        ctl.save_state({"theme": "broken"})
        self.assertEqual(ctl.main(["lock-worker", "--only"]), 0)
        self.assert_started()

    def test_appearance_io_errors_do_not_abort_locking(self):
        with patch.object(ctl, "theme_path", side_effect=PermissionError("unreadable palette")):
            self.assertEqual(ctl.main(["lock-worker", "--only"]), 0)
        self.assert_started()
        image = self.home / "lock.png"
        image.write_bytes(b"image")
        ctl.save_state({"lockBackground": str(image)})
        precious = self.state / "lock-background"
        precious.write_text("preserve")
        self.assertEqual(ctl.main(["lock-worker", "--only"]), 0)
        self.assertIn(str(self.state / "background"), self.assert_started())
        self.assertEqual(precious.read_text(), "preserve")

    def test_suspend_request_fallback_locks_even_with_corrupt_state(self):
        ctl.atomic_write(self.state / "state.json", "{")
        self.run.return_value = subprocess.CompletedProcess([], 1, "")
        self.assertEqual(ctl.main(["lock", "--only"]), 0)
        self.assertEqual(self.run.call_args.args[0], ["systemctl", "--user", "start", "desktop-lock-only.service"])
        command = self.background.call_args.args[0]
        self.assertEqual(command[2:], ["lock-worker", "--only"])
        self.assertEqual(ctl.main(command[2:]), 0)
        self.assert_started()
        self.sleep.assert_not_called()

    def test_normal_lock_preserves_display_and_keyboard_power_behavior(self):
        ctl.atomic_write(self.state / "state.json", "{")
        self.assertEqual(ctl.main(["lock-worker"]), 0)
        self.assert_started()
        self.sleep.assert_called_once_with(3)
        self.assertEqual([c.args[0] for c in self.run.call_args_list], [
            ["hyprctl", "switchxkblayout", "all", "0"],
            ["hyprctl", "dispatch", "dpms", "off"],
            ["hyprctl", "dispatch", "dpms", "on"],
        ])
        self.assertEqual([c.args[0] for c in self.brightness.call_args_list],
                         [["keyboard", "off"], ["keyboard", "restore"]])

    def test_failed_locker_is_reported_and_does_not_blank_displays(self):
        self.child.poll.return_value = self.child.wait.return_value = 1
        self.child.returncode = 1
        for args in ([], ["--only"]):
            with self.subTest(args=args):
                self.assertEqual(ctl.main(["lock-worker", *args]), 1)
                self.assert_started()
        self.assertNotIn(["hyprctl", "dispatch", "dpms", "off"], [c.args[0] for c in self.run.call_args_list])
        self.assertIn("non-zero exit status 1", self.stderr.getvalue())

    def test_locker_launch_and_required_config_failures_are_reported(self):
        self.popen.side_effect = FileNotFoundError("hyprlock unavailable")
        self.assertEqual(ctl.main(["lock-worker", "--only"]), 1)
        self.child.wait.assert_not_called()
        self.popen.reset_mock()
        (self.config / "hypr/hyprlock.conf").unlink()
        self.assertEqual(ctl.main(["lock-worker", "--only"]), 1)
        self.popen.assert_not_called()


if __name__ == "__main__":
    unittest.main()
