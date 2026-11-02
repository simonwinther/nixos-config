"""Parse every bundled theme with Hyprland without starting a compositor."""
import os
import shutil
import subprocess
import unittest

import test_desktop as base


@unittest.skipUnless(shutil.which("Hyprland"), "The Lua-capable Hyprland parser is required")
class ThemeHyprlandTests(unittest.TestCase):
    setUp = base.DesktopTests.setUp
    tearDown = base.DesktopTests.tearDown

    def test_every_theme_loads_without_configuration_errors(self):
        (self.config / "hypr").symlink_to(base.ROOT / "dotfiles/hypr/.config/hypr")
        self.runtime.mkdir(parents=True)
        env = {**os.environ, "HOME": str(self.home), "XDG_CONFIG_HOME": str(self.config),
               "XDG_STATE_HOME": str(self.state.parent), "XDG_DATA_HOME": str(self.data),
               "XDG_RUNTIME_DIR": str(self.runtime.parent)}
        for name in ("WAYLAND_DISPLAY", "DISPLAY", "HYPRLAND_INSTANCE_SIGNATURE", "HYPRSPACE_PLUGIN"):
            env.pop(name, None)
        for source in sorted((self.config / "desktop/themes").iterdir()):
            with self.subTest(theme=source.name):
                base.ctl.theme(["set", source.name, "--no-reload"])
                result = subprocess.run(["Hyprland", "--verify-config", "--config",
                                         str(self.config / "hypr/hyprland.lua")],
                                        env=env, capture_output=True, text=True, timeout=10)
                output = result.stdout + result.stderr
                self.assertEqual(result.returncode, 0, output)
                self.assertIn("config ok", output)


if __name__ == "__main__":
    unittest.main()
