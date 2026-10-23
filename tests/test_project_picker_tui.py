"""Exercise real keyboard input, live updates, and terminal restoration."""
import codecs
import fcntl
import json
import os
from pathlib import Path
import pty
import select
import shutil
import signal
import struct
import subprocess
import tempfile
import termios
import time
import unittest

try:
    import pyte
except ImportError:
    pyte = None

BINARY = os.environ.get("PROJECT_PICKER_TUI_BINARY") or shutil.which("project-picker-tui")
FIRST = "g-p-" + "1" * 32
SECOND = "g-p-" + "2" * 32


@unittest.skipUnless(BINARY and pyte, "Rust picker and terminal emulator are required")
class TerminalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "projects.json"
        self.save([(FIRST, "Alpha"), (SECOND, "Béta")])
        self.master, self.slave = pty.openpty()
        self.original = termios.tcgetattr(self.slave)
        self.process = None
        self.screen = pyte.Screen(64, 18)
        self.stream = pyte.Stream(self.screen)
        self.decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        self.resize(64, 18)

    def tearDown(self):
        if self.process:
            if self.process.poll() is None:
                self.process.kill()
            self.process.wait()
            self.process.stdout.close()
        os.close(self.master)
        os.close(self.slave)
        self.temp.cleanup()

    def save(self, projects):
        self.path.write_text(json.dumps({"version": 1, "active": "personal", "contexts": {"personal": {
            "complete": True, "workspace_name": "Personal", "synced_at": 100,
            "projects": [{"id": project_id, "name": name} for project_id, name in projects],
        }}}))

    def resize(self, columns, rows):
        fcntl.ioctl(self.slave, termios.TIOCSWINSZ, struct.pack("HHHH", rows, columns, 0, 0))
        if hasattr(self, "screen"):
            self.screen.resize(rows, columns)
        if self.process:
            os.kill(self.process.pid, signal.SIGWINCH)

    def start(self):
        def terminal_session():
            os.setsid()
            fcntl.ioctl(0, termios.TIOCSCTTY, 0)

        self.process = subprocess.Popen([BINARY, "--cache", str(self.path)], stdin=self.slave,
                                        stderr=self.slave, stdout=subprocess.PIPE,
                                        env={**os.environ, "TERM": "xterm-256color"}, preexec_fn=terminal_session)

    def wait_for(self, text):
        deadline = time.monotonic() + 4
        while time.monotonic() < deadline:
            if select.select([self.master], [], [], 0.1)[0]:
                self.stream.feed(self.decoder.decode(os.read(self.master, 65536)))
                if text in "\n".join(self.screen.display):
                    return
            if self.process.poll() is not None:
                break
        self.fail(f"Terminal did not display {text!r}: {self.screen.display}")

    def finish(self, expected):
        self.assertEqual(self.process.communicate(timeout=4)[0].decode().strip(), expected)
        self.assertEqual(self.process.returncode, 0)
        self.assertEqual(termios.tcgetattr(self.slave), self.original)

    def test_typing_unicode_filters_and_opens_the_selected_project(self):
        self.start()
        self.wait_for("Projects")
        os.write(self.master, "béta".encode())
        self.wait_for("1 / 3")
        os.write(self.master, b"\r")
        self.finish(SECOND)

    def test_open_picker_reflects_renames_and_removals(self):
        self.start()
        self.wait_for("Projects")
        os.write(self.master, b"alp")
        self.wait_for("1 / 3")
        self.save([(FIRST, "Alpine"), (SECOND, "Béta")])
        self.wait_for("Alpine")
        self.save([(SECOND, "Béta")])
        self.wait_for("No matching projects")
        os.write(self.master, b"\r\x1b")
        self.finish("")

    def test_cancel_restores_the_terminal_and_emits_no_selection(self):
        self.start()
        self.wait_for("Projects")
        os.write(self.master, b"\x03")
        self.finish("")

    def test_resize_recovers_from_a_tiny_terminal(self):
        self.resize(12, 4)
        self.start()
        self.wait_for("Resize")
        self.resize(64, 18)
        self.wait_for("Projects")
        os.write(self.master, b"\x1b")
        self.finish("")
