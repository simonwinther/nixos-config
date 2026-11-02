"""Theme changes find matching images in bundled and shared wallpaper folders."""
from contextlib import contextmanager
import shutil
import subprocess
import unittest
from unittest.mock import patch

from desktop_support import make_desktop
import test_desktop as base


class ThemeWallpaperTests(unittest.TestCase):
    def setUp(self):
        base.DesktopTests.setUp(self)
        self.data.mkdir(parents=True)
        (self.data / "wallpapers").symlink_to(base.ROOT / "dotfiles/wallpapers/.local/share/wallpapers")
        self.desktop = make_desktop(self.home, config=self.config, state=self.state,
                                    data=self.data, runtime=self.runtime)

    tearDown = base.DesktopTests.tearDown

    @contextmanager
    def adapter(self, modular):
        component = self.desktop.appearance if modular else base.ctl
        processes = self.desktop.ctx.processes if modular else base.ctl
        services = self.desktop.services if modular else base.ctl
        wallpaper = self.desktop.wallpaper if modular else base.ctl
        with patch.object(processes, "run"), patch.object(services, "restart"), \
                patch.object(component, "apply_appearance"), patch.object(wallpaper, "wallpaper") as apply:
            yield component, apply

    def local_theme(self):
        source = self.data / "desktop/themes/custom"
        source.mkdir(parents=True)
        shutil.copyfile(self.config / "desktop/themes/tokyoled/colors.toml", source / "colors.toml")
        return source

    def test_shared_libraries_replace_a_previous_themes_wallpaper(self):
        for modular in (False, True):
            for name, image in (("tokyoled", "tokyoled/digital-art/background.png"),
                                ("forest-green", "forest-green/1-FG.jpg")):
                with self.subTest(modular=modular, theme=name), self.adapter(modular) as (component, apply):
                    base.ctl.save_state({"theme": "catppuccin-latte", "wallpaper": "/previous.png"})
                    component.theme(["set", name])
                    apply.assert_called_once_with(["set", str((self.data / "wallpapers" / image).resolve())])

    def test_existing_choice_in_a_nested_shared_folder_stays_selected(self):
        image = next((self.data / "wallpapers/tokyoled/space").iterdir()).resolve()
        for modular in (False, True):
            with self.subTest(modular=modular), self.adapter(modular) as (component, apply):
                base.ctl.save_state({"wallpaper": str(image)})
                component.theme(["set", "tokyoled"])
                apply.assert_called_once_with(["set", str(image)])

    def test_nested_bundled_images_are_found_and_metadata_is_ignored(self):
        source = self.local_theme()
        backgrounds = source / "backgrounds"
        nested = backgrounds / "landscapes"
        nested.mkdir(parents=True)
        (backgrounds / "0-readme.txt").write_text("Wallpaper credits")
        image = nested / "1-image.JPG"
        image.write_bytes(b"image fixture; renderer is mocked")
        for modular in (False, True):
            with self.subTest(modular=modular), self.adapter(modular) as (component, apply):
                base.ctl.save_state({"wallpaper": "/previous.png"})
                component.theme(["set", "custom"])
                apply.assert_called_once_with(["set", str(image)])

    def test_themes_without_images_keep_the_current_wallpaper(self):
        self.local_theme()
        for modular in (False, True):
            with self.subTest(modular=modular), self.adapter(modular) as (component, apply):
                base.ctl.save_state({"wallpaper": "/previous.png"})
                component.theme(["set", "custom"])
                apply.assert_not_called()
                self.assertEqual(base.ctl.state()["wallpaper"], "/previous.png")

    def test_preparation_does_not_apply_a_wallpaper(self):
        for modular in (False, True):
            for name in ("tokyoled", "forest-green", "catppuccin-latte"):
                with self.subTest(modular=modular, theme=name), self.adapter(modular) as (component, apply):
                    base.ctl.save_state({"wallpaper": "/previous.png"})
                    component.theme(["set", name, "--no-reload"])
                    apply.assert_not_called()
                    self.assertEqual(base.ctl.state()["wallpaper"], "/previous.png")

    @contextmanager
    def renderer(self, modular, replies, *, expire=False):
        component = self.desktop.wallpaper if modular else base.ctl
        processes = self.desktop.ctx.processes if modular else base.ctl
        clock = self.desktop.ctx.clock if modular else base.ctl.time
        replies = iter(replies)
        now = [0.0]
        latest = [""]
        queried = [False]

        def run(command, **kwargs):
            if command == ["awww", "query"]:
                latest[0] = next(replies, latest[0])
                if expire and not queried[0]:
                    now[0] += 10
                queried[0] = True
                return subprocess.CompletedProcess(command, 0, latest[0])
            return subprocess.CompletedProcess(command, 0, "")

        def sleep(seconds):
            now[0] += seconds

        with patch.object(processes, "run", side_effect=run) as calls, \
                patch.object(clock, "monotonic", side_effect=lambda: now[0]), \
                patch.object(clock, "sleep", side_effect=sleep):
            yield component, calls

    def test_renderer_waits_for_the_requested_image(self):
        old = ': eDP-1: 1600x900, scale: 1.2, currently displaying: image: /previous.png\n'
        current = old.replace('/previous.png', '/chosen.png')
        for modular in (False, True):
            with self.subTest(modular=modular), self.renderer(modular, [old, current]) as (component, calls):
                component.apply_wallpaper(["awww", "img", "--transition-type", "any"], "/chosen.png", None, 2)
                self.assertEqual(sum(call.args[0][1] == "img" for call in calls.call_args_list), 1)

    def test_renderer_retries_a_rejected_image_without_a_transition(self):
        old = ': eDP-1: 1600x900, scale: 1.2, currently displaying: image: /previous.png\n'
        current = old.replace('/previous.png', '/chosen.png')
        for modular in (False, True):
            with self.subTest(modular=modular), self.renderer(modular, [old, current], expire=True) as (component, calls):
                command = ["awww", "img", "--transition-type", "any"]
                component.apply_wallpaper(command, "/chosen.png", None, 2)
                self.assertEqual([call.args[0] for call in calls.call_args_list if call.args[0][1] == "img"],
                                 [[*command, "/chosen.png"], ["awww", "img", "--transition-type", "none", "/chosen.png"]])
                self.assertEqual(command[-1], "any")

    def test_renderer_checks_only_the_requested_output(self):
        outputs = (': eDP-1: 1600x900, scale: 1.2, currently displaying: image: /chosen.png\n'
                   ': HDMI-A-1: 1920x1080, scale: 1, currently displaying: image: /previous.png\n')
        for modular in (False, True):
            with self.subTest(modular=modular), self.renderer(modular, [outputs]) as (component, calls):
                component.apply_wallpaper(["awww", "img", "--transition-type", "any", "--outputs", "eDP-1"],
                                          "/chosen.png", "eDP-1", 2)
                self.assertEqual(sum(call.args[0][1] == "img" for call in calls.call_args_list), 1)

    def test_renderer_rejects_a_brief_success_followed_by_a_cached_old_image(self):
        old = ': eDP-1: 1600x900, scale: 1.2, currently displaying: image: /previous.png\n'
        current = old.replace('/previous.png', '/chosen.png')
        for modular in (False, True):
            with self.subTest(modular=modular), self.renderer(modular, [current, old]) as (component, _):
                with self.assertRaisesRegex(ValueError, "did not display"):
                    component.apply_wallpaper(["awww", "img", "--transition-type", "any"], "/chosen.png", None, 2)

    def test_renderer_reports_failure_when_an_output_keeps_the_old_image(self):
        outputs = (': eDP-1: 1600x900, scale: 1.2, currently displaying: image: /chosen.png\n'
                   ': HDMI-A-1: 1920x1080, scale: 1, currently displaying: image: /previous.png\n')
        for modular in (False, True):
            with self.subTest(modular=modular), self.renderer(modular, [outputs, outputs], expire=True) as (component, _):
                with self.assertRaisesRegex(ValueError, "did not display"):
                    component.apply_wallpaper(["awww", "img", "--transition-type", "any"], "/chosen.png", None, 2)

    def test_failed_render_does_not_publish_the_new_wallpaper(self):
        image = self.data / "wallpapers/tokyoled/digital-art/background.png"
        for modular in (False, True):
            component = self.desktop.wallpaper if modular else base.ctl
            processes = self.desktop.ctx.processes if modular else base.ctl
            with self.subTest(modular=modular), \
                    patch.object(processes, "run", return_value=subprocess.CompletedProcess([], 0, "")), \
                    patch.object(component, "apply_wallpaper", side_effect=ValueError("did not display")):
                base.ctl.save_state({"wallpaper": "/previous.png"})
                with self.assertRaisesRegex(ValueError, "did not display"):
                    component.wallpaper(["set", str(image)])
                self.assertEqual(base.ctl.state()["wallpaper"], "/previous.png")


if __name__ == "__main__":
    unittest.main()
