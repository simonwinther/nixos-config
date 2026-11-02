"""Native bar styles and renderer handoff use disposable desktop state."""

import contextlib
import io
import json
import os
from pathlib import Path
import socket
import shutil
import struct
import subprocess
import unittest
from unittest.mock import patch

import test_desktop as base
from desktop_support import make_desktop

ctl = base.ctl


class NativeBarTests(unittest.TestCase):
    setUp = base.DesktopTests.setUp
    tearDown = base.DesktopTests.tearDown

    def frontends(self):
        desktop = make_desktop(
            self.home,
            config=self.config,
            state=self.state,
            data=self.data,
            runtime=self.runtime,
        )
        return (
            (ctl.bar, ctl, "run"),
            (desktop.appearance.bar, desktop.ctx.processes, "run"),
        )

    def test_only_native_styles_are_available_in_both_frontends(self):
        legacy = self.config / "waybar/bars/classic"
        legacy.mkdir(parents=True)
        (legacy / "config.jsonc").write_text("{}")
        for command, processes, method in self.frontends():
            for old in ("clean", "classic", "removed"):
                ctl.save_state({"bar": old})
                with contextlib.redirect_stdout(io.StringIO()) as output:
                    command(["current"])
                self.assertEqual(output.getvalue(), "native-clean\n")
            with contextlib.redirect_stdout(io.StringIO()) as output:
                command(["list"])
            self.assertEqual(output.getvalue(), "native-clean\nnative-motion\n")
            with patch.object(processes, method) as run:
                for old in ("clean", "classic"):
                    with self.assertRaises(ValueError):
                        command(["set", old])
            run.assert_not_called()

    def test_bar_restart_targets_only_one_service(self):
        desktop = make_desktop(
            self.home,
            config=self.config,
            state=self.state,
            data=self.data,
            runtime=self.runtime,
        )
        for restart, processes in (
            (ctl.restart, ctl),
            (desktop.services.restart, desktop.ctx.processes),
        ):
            with patch.object(
                processes, "run", return_value=subprocess.CompletedProcess([], 0)
            ) as run:
                restart("bar")
            run.assert_called_once_with(
                ["systemctl", "--user", "try-restart", "desktop-bar.service"],
                check=False,
            )

    def test_native_style_swap_signals_the_service_and_writes_theme_data(self):
        (self.config / "desktop/bar-outputs.json").write_text(
            '{"full":["DP-2"],"minimal":["eDP-1"],"scale":1.2}'
        )
        for command, processes, method in self.frontends():
            with self.subTest(command=command):
                ctl.save_state(
                    {
                        "bar": "native-clean",
                        "font": "Test Mono",
                        "theme": "catppuccin-latte",
                    }
                )
                with patch.object(
                    processes, method, return_value=subprocess.CompletedProcess([], 0)
                ) as run:
                    command(["set", "native-motion"])
                run.assert_called_once_with(
                    [
                        "systemctl",
                        "--user",
                        "kill",
                        "--kill-whom=main",
                        "--signal=SIGUSR2",
                        "desktop-bar.service",
                    ],
                    check=False,
                )
                value = json.loads((self.runtime / "bar-theme.json").read_text())
                self.assertEqual(value["style"], "native-motion")
                self.assertEqual(value["font"], "Test Mono")
                self.assertEqual(value["scale"], 1.2)
                self.assertTrue(value["light"])
                self.assertEqual(
                    value["outputs"], {"full": ["DP-2"], "minimal": ["eDP-1"]}
                )
                self.assertEqual(
                    value["palette"], ctl.colors(ctl.theme_path("catppuccin-latte"))
                )

    def test_hidden_bar_changes_preferences_without_starting_services(self):
        disabled = self.state / "toggles/bar-off"
        disabled.parent.mkdir(parents=True)
        disabled.touch()
        for command, processes, method in self.frontends():
            ctl.save_state({"bar": "clean"})
            with patch.object(processes, method) as run:
                command(["set", "native-motion"])
            run.assert_not_called()
            self.assertTrue(disabled.exists())
            self.assertEqual(ctl.selected_bar(), "native-motion")

    def test_theme_preparation_refreshes_runtime_data_on_cache_hits(self):
        ctl.theme(["set", "catppuccin-latte", "--no-reload"])
        path = self.runtime / "bar-theme.json"
        self.assertTrue(json.loads(path.read_text())["light"])
        path.unlink()
        ctl.prepare_theme()
        self.assertTrue(path.is_file())
        ctl.theme(["set", "tokyoled", "--no-reload"])
        self.assertFalse(json.loads(path.read_text())["light"])

    def test_invalid_scale_falls_back_and_removed_variants_use_default(self):
        import bar_config

        for scale in (False, "large", 0, 99):
            result = bar_config.theme_data(
                {"bar": "removed"}, {}, {}, False, {"scale": scale}
            )
            self.assertEqual(result["style"], "native-clean")
            self.assertEqual(result["scale"], 1.15)

    def test_hidden_legacy_bar_migrates_without_copying_the_old_marker(self):
        for command, processes, method in self.frontends():
            marker = self.state / "toggles/bar-off"
            marker.unlink(missing_ok=True)
            legacy = self.state / "toggles/waybar-off"
            legacy.parent.mkdir(parents=True, exist_ok=True)
            legacy.touch()
            with patch.object(processes, method) as run:
                command(["set", "native-motion"])
            run.assert_not_called()
            self.assertTrue(marker.exists())
            self.assertFalse(legacy.exists())

    def test_weather_shortcut_uses_the_native_application(self):
        desktop = make_desktop(
            self.home,
            config=self.config,
            state=self.state,
            data=self.data,
            runtime=self.runtime,
        )
        with patch.object(ctl.os, "execvp") as execute:
            ctl.main(["weather", "--refresh"])
        execute.assert_called_once_with(
            "desktop-bar", ["desktop-bar", "--weather", "--refresh"]
        )

        with patch.object(desktop.ctx.processes, "execvp") as execute:
            desktop.applications.weather(["--refresh"])
        execute.assert_called_once_with(
            "desktop-bar", ["desktop-bar", "--weather", "--refresh"]
        )

    def test_motion_routes_both_launchers_and_style_menu_to_the_running_bar(self):
        desktop = make_desktop(self.home, config=self.config, state=self.state,
                               data=self.data, runtime=self.runtime)
        ctl.save_state({"bar": "native-motion"})
        self.runtime.mkdir(parents=True, exist_ok=True)
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as server:
            server.bind(str(self.runtime / "bar.sock"))
            server.settimeout(1)
            for launcher, processes in ((ctl.launcher, ctl),
                                        (desktop.clipboard.launcher, desktop.ctx.processes)):
                with patch.object(processes, "run") as run:
                    launcher([])
                self.assertEqual(server.recv(128), b"apps")
                run.assert_not_called()
            ctl.save_state({"bar": "native-clean"})
            with patch.object(ctl, "run") as run:
                ctl.menu(["bar"])
            self.assertEqual(server.recv(128), b"styles")
            run.assert_not_called()

    def test_desktop_device_and_information_menus_use_the_notch(self):
        desktop = make_desktop(self.home, config=self.config, state=self.state,
                               data=self.data, runtime=self.runtime)
        ctl.save_state({"bar": "native-motion"})
        self.runtime.mkdir(parents=True, exist_ok=True)
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as server:
            server.bind(str(self.runtime / "bar.sock"))
            server.settimeout(1)
            for component, processes in ((ctl, ctl), (desktop.applications, desktop.ctx.processes)):
                for panel in ("audio", "bluetooth", "wifi"):
                    with patch.object(processes, "run") as run, patch.object(component, "terminal") as terminal:
                        component.launch([panel])
                    self.assertEqual(server.recv(128), panel.encode())
                    terminal.assert_not_called()
                    run.assert_not_called()
            for component in (ctl, desktop.menus):
                component.keybindings()
                self.assertEqual(server.recv(128), b"keybindings")
            for launcher in (ctl.launcher, desktop.clipboard.launcher):
                launcher(["-m", "menus:notifications", "-p", "Search notifications"])
                self.assertEqual(server.recv(128), b"notifications")

    @unittest.skipUnless(shutil.which("magick"), "Image conversion requires ImageMagick")
    def test_media_artwork_is_bounded_private_and_cached(self):
        import bar_catalog
        source = self.home / "album art.png"
        subprocess.run(["magick", "-size", "320x180", "xc:#123456", str(source)], check=True)
        cover = Path(bar_catalog.cover(source.as_uri(), self.home / "cache"))
        contents = cover.read_bytes()
        self.assertEqual(struct.unpack(">II", contents[16:24]), (128, 128))
        self.assertEqual(cover.stat().st_mode & 0o777, 0o600)
        self.assertEqual(cover.parent.stat().st_mode & 0o777, 0o700)
        with patch.object(bar_catalog.subprocess, "run", side_effect=AssertionError("Repeated conversion")):
            self.assertEqual(bar_catalog.cover(source.as_uri(), self.home / "cache"), str(cover))
        with self.assertRaises(ValueError):
            bar_catalog.cover("ftp://example.invalid/cover.png", self.home / "cache")
        source.write_bytes(b"0" * (8 * 1024 * 1024 + 1))
        with self.assertRaises(ValueError):
            bar_catalog.cover(source.as_uri() + "?oversized", self.home / "cache")

    def test_disconnected_native_shell_uses_existing_picker_fallback(self):
        import bar_config
        ctl.save_state({"bar": "native-motion"})
        self.assertFalse(bar_config.open_panel(self.runtime, "apps", ctl.state()))
        self.assertFalse(bar_config.open_panel(self.runtime, "apps", {"bar": "native-clean"}))

    def test_motion_clipboard_uses_the_running_notch_in_both_frontends(self):
        desktop = make_desktop(self.home, config=self.config, state=self.state,
                               data=self.data, runtime=self.runtime)
        ctl.save_state({"bar": "native-motion"})
        self.runtime.mkdir(parents=True, exist_ok=True)
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as server:
            server.bind(str(self.runtime / "bar.sock"))
            server.settimeout(1)
            for component, processes, applications in ((ctl, ctl, ctl),
                    (desktop.clipboard, desktop.ctx.processes, desktop.applications)):
                with patch.object(component, "remember_clipboard_target") as remember, \
                        patch.object(processes, "run") as run, \
                        patch.object(applications, "run_application") as launch:
                    component.clipboard([])
                remember.assert_called_once_with()
                run.assert_called_once_with(["systemctl", "--user", "start", "desktop-search.service"], check=False)
                launch.assert_not_called()
                self.assertEqual(server.recv(128), b"clipboard")

    def test_all_provider_modes_use_the_native_surface_in_both_styles(self):
        desktop = make_desktop(self.home, config=self.config, state=self.state,
                               data=self.data, runtime=self.runtime)
        search = self.runtime.parent / "desktop-search/search.sock"
        search.parent.mkdir(parents=True, exist_ok=True)
        search.touch()
        self.runtime.mkdir(parents=True, exist_ok=True)
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as server:
            server.bind(str(self.runtime / "bar.sock"))
            server.settimeout(1)
            for style in ("native-clean", "native-motion"):
                ctl.save_state({"bar": style})
                for component, processes, application in ((ctl, ctl, ctl),
                        (desktop.clipboard, desktop.ctx.processes, desktop.applications)):
                    for provider in ("symbols", "unicode", "files", "calc", "runner", "websearch", "todo", "providerlist", "menus:repositories"):
                        with patch.object(processes, "run") as run, patch.object(application, "run_application") as launch:
                            component.launcher(["-m", provider, "--search", "literal $HOME; æ"])
                        request = server.recv(16384).decode()
                        self.assertTrue(request.startswith("launcher/"))
                        self.assertEqual(json.loads(request[9:]), {"providers": [provider], "query": "literal $HOME; æ"})
                        run.assert_not_called()
                        launch.assert_not_called()

    def test_invalid_launcher_options_fail_before_opening_any_surface(self):
        import bar_config
        for arguments in (["--modules"], ["--query"], ["--modules", "missing"], ["--search", "x" * 4097]):
            with self.subTest(arguments=arguments), self.assertRaises(ValueError):
                bar_config.launcher_panel(arguments)

    def test_catalogs_preserve_palette_selection_and_custom_action_arguments(self):
        for command, _, _ in self.frontends():
            ctl.save_state({"bar": "native-motion", "theme": "tokyoled"})
            with contextlib.redirect_stdout(io.StringIO()) as output:
                command(["catalog", "themes"])
            entries = json.loads(output.getvalue())
            selected = next(entry for entry in entries if entry["selected"])
            self.assertEqual(selected["id"], "tokyoled")
            self.assertEqual(selected["command"], ["theme", "set", "tokyoled"])
            self.assertEqual(len(selected["colors"]), 6)
            custom = [{"name": "My action", "command": ["exec", "tool", "one argument with spaces"]}]
            (self.config / "desktop/bar-actions.json").write_text(json.dumps(custom))
            with contextlib.redirect_stdout(io.StringIO()) as output:
                command(["catalog", "controls"])
            self.assertEqual(json.loads(output.getvalue()), custom)

    def test_static_desktop_menus_keep_their_structured_actions(self):
        items = {"Open input settings": ["config", "Input"], "Themes": ["menu", "theme"]}
        (self.config / "desktop/menus.json").write_text(json.dumps({"setup": {"items": items}}))
        for command, _, _ in self.frontends():
            with contextlib.redirect_stdout(io.StringIO()) as output:
                command(["catalog", "menu/setup"])
            self.assertEqual([entry["command"] for entry in json.loads(output.getvalue())], list(items.values()))

    def test_menu_override_exposes_style_choice_in_both_native_styles(self):
        installed = self.config / "desktop/menus.json"
        installed.write_text('{"style":{"items":{"Themes":["menu","theme"]}}}')
        original = installed.read_bytes()
        override = base.ROOT / "dotfiles/desktop-settings/.config/desktop/menus.json"
        desktop = make_desktop(self.home, config=self.config, state=self.state, data=self.data, runtime=self.runtime)
        self.runtime.mkdir(parents=True, exist_ok=True)
        with patch.dict(os.environ, {"DESKTOP_MENUS_FILE": str(override)}), socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as server:
            server.bind(str(self.runtime / "bar.sock"))
            server.settimeout(1)
            for style in ("native-clean", "native-motion"):
                ctl.save_state({"bar": style})
                for menu in (ctl.menu, desktop.menus.menu):
                    menu(["style"])
                    self.assertEqual(server.recv(128), b"menu/style")
                for command, _, _ in self.frontends():
                    with contextlib.redirect_stdout(io.StringIO()) as output:
                        command(["catalog", "menu/style"])
                    self.assertIn(["menu", "bar"], [entry["command"] for entry in json.loads(output.getvalue())])
        self.assertEqual(installed.read_bytes(), original)

    def test_application_launches_leave_the_bars_service(self):
        import bar_catalog
        desktop = self.home / "Launch probe.desktop"
        desktop.write_text("[Desktop Entry]\nType=Application\nName=Launch probe\nExec=true\n")
        for command, _, _ in self.frontends():
            for available, prefix in (({"uwsm-app"}, ["uwsm-app", "--"]),
                    ({"systemd-run"}, ["systemd-run", "--user", "--scope", "--collect", "--quiet", "--"])):
                with patch.object(bar_catalog.shutil, "which", side_effect=lambda name: name if name in available else None), \
                        patch.object(bar_catalog.subprocess, "Popen") as launch:
                    command(["launch", str(desktop)])
                self.assertEqual(launch.call_args.args[0], [*prefix, "gio", "launch", str(desktop)])

    def test_browser_terminal_and_custom_focus_launches_use_application_scopes(self):
        import bar_catalog
        desktop = make_desktop(self.home, config=self.config, state=self.state,
                               data=self.data, runtime=self.runtime)
        url = "https://example.invalid/a?value=literal$(text)&next=two words"
        for launcher, terminal, processes, executor, settings, cwd_owner in (
            (ctl.launch, ctl.terminal, ctl, ctl.os, ctl, ctl),
            (desktop.applications.launch, desktop.applications.terminal,
             desktop.ctx.processes, desktop.ctx.processes, desktop.store, desktop.applications),
        ):
            for available, prefix in (
                ({"uwsm-app"}, ["uwsm-app", "--"]),
                ({"systemd-run"}, ["systemd-run", "--user", "--scope", "--collect", "--quiet", "--"]),
                (set(), []),
            ):
                with patch.object(bar_catalog.shutil, "which", side_effect=lambda name: name if name in available else None), \
                        patch.object(settings, "settings", return_value={"browser": "test-browser"}), \
                        patch.object(processes, "run", return_value=subprocess.CompletedProcess([], 0, "[]")):
                    for arguments, command in (
                        (["browser", "--private", url], ["test-browser", "--incognito", url]),
                        (["webapp", url], ["test-browser", "--app=" + url]),
                        (["focus", "missioncenter"], ["missioncenter"]),
                        (["focus", "Window", "app --title 'literal spaces'"], ["app", "--title", "literal spaces"]),
                        (["focus", "Window", "app", "--title", "literal spaces"], ["app", "--title", "literal spaces"]),
                    ):
                        with patch.object(executor, "execvp") as execute:
                            launcher(arguments)
                        expected = [*prefix, *command]
                        execute.assert_called_once_with(expected[0], expected)
                    with patch.object(cwd_owner, "cwd", return_value="/working directory"), \
                            patch.object(executor, "execvp") as execute:
                        terminal(["--app-id", "org.test.Terminal", "nvim", "file with spaces"])
                    expected = [*prefix, "xdg-terminal-exec", "--dir=/working directory", "--app-id=org.test.Terminal",
                                "-e", "nvim", "file with spaces"]
                    execute.assert_called_once_with(expected[0], expected)
        explicit = ["/bin/uwsm-app", "--", "app", "literal spaces"]
        with patch.object(bar_catalog.shutil, "which", side_effect=AssertionError("Already scoped")):
            self.assertEqual(bar_catalog.application_command(explicit), explicit)
        with self.assertRaises(ValueError):
            bar_catalog.application_command([])

    def test_application_catalog_respects_xdg_overrides_and_desktop_visibility(self):
        import bar_catalog
        system = self.home / "system-share"
        user_apps = self.data / "applications"
        system_apps = system / "applications"
        user_apps.mkdir(parents=True, exist_ok=True)
        system_apps.mkdir(parents=True)
        (system_apps / "hidden.desktop").write_text("[Desktop Entry]\nType=Application\nName=Hidden override\nExec=true\n")
        (user_apps / "hidden.desktop").write_text("[Desktop Entry]\nHidden=true\n")
        (user_apps / "other.desktop").write_text("[Desktop Entry]\nName=Other desktop\nExec=true\nOnlyShowIn=KDE;\n")
        (user_apps / "unavailable.desktop").write_text("[Desktop Entry]\nName=Missing\nExec=true\nTryExec=/no/such/app\n")
        (user_apps / "valid.desktop").write_text("[Desktop Entry]\nName=Terminal\nGenericName=Command line\nExec=terminal --title 'One argument'\nOnlyShowIn=Hyprland;\n")
        with patch.dict(os.environ, {"XDG_DATA_DIRS": str(system), "XDG_CURRENT_DESKTOP": "Hyprland"}):
            entries = bar_catalog.application_entries(self.data)
        self.assertEqual([entry["name"] for entry in entries], ["Terminal"])
        self.assertEqual(entries[0]["command"], ["bar", "launch", str((user_apps / "valid.desktop").resolve())])

    def test_application_icons_preserve_xdg_precedence_and_refresh_between_scans(self):
        import bar_catalog
        system = self.home / "system-icons"
        user_icons = self.data / "icons/hicolor/scalable/apps"
        system_icons = system / "icons/hicolor/48x48/apps"
        pixmaps = system / "pixmaps"
        for directory in (user_icons, system_icons, pixmaps):
            directory.mkdir(parents=True)
        user_icon = user_icons / "shared.svg"
        system_icon = system_icons / "shared.png"
        pixmap = pixmaps / "fallback.png"
        for path in (user_icon, system_icon, pixmap):
            path.write_bytes(b"icon")
        with patch.dict(os.environ, {"XDG_DATA_DIRS": str(system)}):
            icons = bar_catalog.IconLookup(self.data)
            self.assertEqual(icons.path("shared"), str(user_icon))
            self.assertEqual(icons.path("fallback"), str(pixmap))
            self.assertEqual(icons.path(str(system_icon)), str(system_icon))
            self.assertEqual(icons.path("missing"), "")
            user_icon.unlink()
            self.assertEqual(bar_catalog.IconLookup(self.data).path("shared"), str(system_icon))

    @unittest.skipUnless(shutil.which("magick"), "Image conversion requires ImageMagick")
    def test_wallpaper_thumbnails_decode_to_bounded_pngs_and_reuse_the_cache(self):
        import bar_catalog

        source = self.home / "wall paper ü.jpg"
        subprocess.run(
            ["magick", "-size", "2400x1600", "gradient:#123456-#abcdef", str(source)],
            check=True,
        )
        cache = self.home / "cache"
        preview = bar_catalog.thumbnail(source, cache)
        content = Path(preview).read_bytes()
        self.assertEqual(content[:8], b"\x89PNG\r\n\x1a\n")
        self.assertEqual(struct.unpack(">II", content[16:24]), (320, 180))
        with patch.object(bar_catalog.subprocess, "run", side_effect=AssertionError("Unexpected conversion")):
            self.assertEqual(bar_catalog.thumbnail(source, cache), preview)
        subprocess.run(
            ["magick", "-size", "2400x1600", "gradient:#abcdef-#123456", str(source)],
            check=True,
        )
        self.assertNotEqual(bar_catalog.thumbnail(source, cache), preview)

    @unittest.skipUnless(shutil.which("magick"), "Image conversion requires ImageMagick")
    def test_clipboard_thumbnail_preserves_the_whole_portrait_and_private_permissions(self):
        import bar_catalog
        source = self.home / "portrait.png"
        subprocess.run(["magick", "-size", "100x400", "xc:red", str(source)], check=True)
        cache = self.home / "cache"
        preview = Path(bar_catalog.thumbnail(source, cache, fit=True))
        self.assertNotEqual(str(preview), bar_catalog.thumbnail(source, cache))
        self.assertEqual(preview.stat().st_mode & 0o777, 0o600)
        self.assertEqual(preview.parent.stat().st_mode & 0o777, 0o700)
        pixels = subprocess.check_output(["magick", str(preview), "-format", "%[pixel:p{0,90}]|%[pixel:p{160,90}]", "info:"]).decode()
        edge, center = pixels.split("|")
        self.assertIn("0)", edge)
        self.assertNotEqual(edge, center)

    def test_theme_reload_uses_the_single_bar_service(self):
        desktop = make_desktop(
            self.home,
            config=self.config,
            state=self.state,
            data=self.data,
            runtime=self.runtime,
        )
        for restart, processes in (
            (ctl.restart, ctl),
            (desktop.services.restart, desktop.ctx.processes),
        ):
            with patch.object(
                processes, "run", return_value=subprocess.CompletedProcess([], 0)
            ) as run:
                restart("theme")
            command = run.call_args.args[0]
            self.assertIn("try-reload-or-restart", command)
            self.assertIn("desktop-bar.service", command)
            self.assertEqual(
                command,
                [
                    "systemctl",
                    "--user",
                    "try-reload-or-restart",
                    "desktop-swayosd.service",
                    "desktop-bar.service",
                ],
            )


if __name__ == "__main__":
    unittest.main()
