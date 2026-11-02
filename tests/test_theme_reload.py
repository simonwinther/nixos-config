"""Deliver reload signals to disposable children with portable and Nix names."""
import os
from pathlib import Path
import select
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch

from desktop_support import make_desktop
import test_desktop as base


@unittest.skipUnless(sys.platform == "linux" and shutil.which("pkill"), "Linux procps is required")
class ThemeReloadTests(unittest.TestCase):
    setUp = base.DesktopTests.setUp
    tearDown = base.DesktopTests.tearDown

    def stop_child(self, child):
        if child.poll() is None:
            child.kill()
        child.communicate(timeout=5)

    def read_child(self, child):
        self.assertTrue(select.select([child.stdout], [], [], 5)[0], "Reload signal did not arrive")
        return child.stdout.readline().strip()

    def test_reload_reaches_plain_and_nix_wrapped_processes(self):
        desktop = make_desktop(self.home, config=self.config, state=self.state,
                               data=self.data, runtime=self.runtime)
        for component, target in ((base.ctl, base.ctl), (desktop.appearance, desktop.ctx.processes)):
            for name, signum in (("ghostty", "USR2"), ("kitty", "USR1"), ("nvim", "USR1")):
                for process_name in (name, f".{name}-wrapped"):
                    with self.subTest(component=type(component).__name__, process_name=process_name):
                        child = subprocess.Popen([sys.executable, "-c", """
import ctypes, signal, sys
ctypes.CDLL(None).prctl(15, sys.argv[1].encode(), 0, 0, 0)
signal.signal(getattr(signal, 'SIG' + sys.argv[2]), lambda *_: print('reloaded', flush=True))
print('ready', flush=True)
while True:
    signal.pause()
""", process_name, signum], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                        self.addCleanup(self.stop_child, child)
                        self.assertEqual(self.read_child(child), "ready")
                        self.assertEqual(Path(f"/proc/{child.pid}/comm").read_text().strip(), process_name[:15])

                        def signal_children(command, **kwargs):
                            # Restrict even a broken pattern to this test's own children.
                            scoped = [*command[:-1], "-P", str(os.getpid()), command[-1]]
                            result = subprocess.run(scoped, capture_output=True, text=True, **kwargs)
                            self.assertEqual(result.returncode, 0, result.stderr)
                            return result

                        with patch.object(target, "run", side_effect=signal_children):
                            component.signal_application(name, signum)
                        self.assertEqual(self.read_child(child), "reloaded")
                        self.stop_child(child)

    def test_theme_font_and_terminal_color_changes_request_live_reloads(self):
        desktop = make_desktop(self.home, config=self.config, state=self.state,
                               data=self.data, runtime=self.runtime)
        for component, process_target, service_target, wallpaper_target in (
                (base.ctl, base.ctl, base.ctl, base.ctl),
                (desktop.appearance, desktop.ctx.processes, desktop.services, desktop.wallpaper)):
            terminals = {("ghostty", "USR2"), ("kitty", "USR1")}
            actions = (("theme", ["set", "catppuccin-latte"], terminals | {("nvim", "USR1")}),
                       ("font", ["set", "Test Mono"], terminals),
                       ("appearance", ["terminal-colors", "personal"], terminals))
            for method, args, expected in actions:
                with self.subTest(component=type(component).__name__, action=method), \
                        patch.object(process_target, "run", return_value=subprocess.CompletedProcess([], 0, "Test Mono\n")), \
                        patch.object(service_target, "restart"), patch.object(wallpaper_target, "wallpaper"), \
                        patch.object(component, "signal_application") as reload:
                    getattr(component, method)(args)
                    self.assertEqual({call.args for call in reload.call_args_list}, expected)
                    self.assertTrue((self.state / "theme/ghostty.conf").is_file())
            for method, args in (("theme", ["set", "tokyoled", "--no-reload"]),
                                 ("font", ["set", "Test Mono", "--no-reload"])):
                with self.subTest(component=type(component).__name__, action=method, reload=False), \
                        patch.object(process_target, "run", return_value=subprocess.CompletedProcess([], 0, "Test Mono\n")), \
                        patch.object(component, "signal_application") as reload:
                    getattr(component, method)(args)
                    reload.assert_not_called()


if __name__ == "__main__":
    unittest.main()
