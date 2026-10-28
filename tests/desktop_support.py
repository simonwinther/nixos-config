"""Construct desktop components with disposable paths and guarded processes."""
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "dotfiles/desktop-tools/.local/share/desktop-tools"
if str(SOURCE) not in sys.path:
    sys.path.insert(0, str(SOURCE))

from desktop_control.app import Desktop
from desktop_control.context import Context, Paths, SystemClock
from desktop_control.processes import SystemProcesses


class GuardedProcesses(SystemProcesses):
    """Only local image conversion may run unless a test injects an operation."""
    def run(self, argv, **kwargs):
        if Path(str(argv[0])).name not in {"matugen", "magick"}:
            raise AssertionError(f"Unexpected desktop process in isolated test: {argv}")
        return super().run(argv, **kwargs)

    def run_bytes(self, argv, **kwargs):
        if Path(str(argv[0])).name != "magick":
            raise AssertionError(f"Unexpected binary process in isolated test: {argv}")
        return super().run_bytes(argv, **kwargs)

    def spawn(self, argv, **kwargs):
        raise AssertionError(f"Unexpected child in isolated test: {argv}")

    def managed(self, argv, **kwargs):
        raise AssertionError(f"Unexpected managed child in isolated test: {argv}")

    def background(self, argv, **kwargs):
        raise AssertionError(f"Unexpected detached child in isolated test: {argv}")

    def execv(self, executable, argv):
        raise AssertionError(f"Unexpected exec in isolated test: {argv}")

    execvp = execv


def make_desktop(home, *, config=None, state=None, data=None, runtime=None, env=None):
    paths = Paths(home, config or home / ".config", data or home / ".local/share",
                  state or home / ".local/state/desktop", runtime or home / "runtime/desktop")
    environment = {**os.environ, "HOME": str(home), "XDG_CONFIG_HOME": str(paths.config),
                   "XDG_STATE_HOME": str(paths.state.parent), "XDG_DATA_HOME": str(paths.data),
                   "XDG_RUNTIME_DIR": str(paths.runtime.parent), "XDG_CONFIG_DIRS": "/etc/xdg",
                   **(env or {})}
    for name in ("DISPLAY", "WAYLAND_DISPLAY", "DBUS_SESSION_BUS_ADDRESS", "HYPRLAND_INSTANCE_SIGNATURE"):
        environment.pop(name, None)
    processes = GuardedProcesses(environment, paths.state / "processes")
    return Desktop(Context(paths, environment, processes, SystemClock(), SOURCE / "desktopctl.py", os.getuid()))
