"""Check cancellation through the public desktop entry points in a private HOME."""
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

import test_desktop as base

ROOT = base.ROOT
SCRIPT = ROOT / "dotfiles/desktop-tools/.local/share/desktop-tools/transcode.sh"
WRAPPER = ROOT / "dotfiles/desktop-tools/.local/bin/desktop-transcode"
NATIVE = os.environ.get("TRANSCODE_TEST_NATIVE") or shutil.which("desktop-transcode-native")


class TranscodeRoutingTests(unittest.TestCase):
    def test_single_job_replaces_the_python_launcher(self):
        with patch.object(base.ctl, "executable", return_value="/mock/desktop-transcode"), \
                patch.object(base.ctl.os, "execv") as execute:
            base.ctl.transcode(["input.png", "jpg", "low"])
        execute.assert_called_once_with("/mock/desktop-transcode",
                                        ["/mock/desktop-transcode", "input.png", "jpg", "low"])


@unittest.skipUnless(NATIVE, "Set TRANSCODE_TEST_NATIVE or build the Nix desktop-transcode package")
class TranscodeEntryPointTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="transcode-entry-")
        self.root = Path(self.temp.name)
        self.tools = self.root / "tools"
        self.tools.mkdir()
        self.input = self.root / "input file.png"
        self.input.write_text("original")
        self.other = self.root / "other.png"
        self.other.write_text("other original")
        self.env = os.environ | {
            "HOME": str(self.root), "XDG_CONFIG_HOME": str(self.root / "config"),
            "XDG_CACHE_HOME": str(self.root / "cache"),
            "PATH": f"{self.tools}:{Path(NATIVE).parent}:{os.environ['PATH']}",
            "DESKTOP_DESKTOP_TRANSCODE_BIN": str(WRAPPER), "RUN": str(self.root),
        }
        self.tool("file", "printf 'image/png\\n'")
        self.tool("desktopctl", 'IFS= read -r choice; printf "%s\\n" "$choice"')
        self.tool("wl-copy", 'cat > "$RUN/clipboard"')
        self.tool("notify-send", 'printf "%s\\n" "$*" >> "$RUN/notices"')
        self.tool("magick", '''
printf '%s\\n' "$$" > "$RUN/encoder-pid"
printf partial > "${@: -1}"
printf 'started\\n' >> "$RUN/started"
touch "$RUN/ready"
while [[ ! -f "$RUN/go" ]]; do sleep 0.02; done
printf complete > "${@: -1}"
''')
        self.job = None

    def tool(self, name, body):
        path = self.tools / name
        path.write_text(f"#!{shutil.which('bash')}\nset -eu\n{body}\n")
        path.chmod(0o755)

    def tearDown(self):
        if self.job is not None and self.job.poll() is None:
            self.job.terminate()
            self.job.communicate(timeout=8)
        pid_file = self.root / "encoder-pid"
        if pid_file.exists():
            try:
                os.killpg(int(pid_file.read_text()), signal.SIGKILL)
            except ProcessLookupError:
                pass
        self.temp.cleanup()

    def wait_ready(self):
        deadline = time.monotonic() + 8
        while not (self.root / "ready").exists():
            if self.job.poll() is not None:
                self.fail(self.job.communicate()[1])
            self.assertLess(time.monotonic(), deadline, "Encoder did not start")
            time.sleep(.01)

    def start(self, command):
        self.job = subprocess.Popen(command, env=self.env, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, text=True)
        self.wait_ready()

    def assert_cancelled(self, signum):
        self.job.send_signal(signum)
        _, errors = self.job.communicate(timeout=8)
        self.assertEqual(self.job.returncode, 128 + signum, errors)
        self.assertEqual(self.input.read_text(), "original")
        self.assertEqual((self.root / "started").read_text().splitlines(), ["started"])
        self.assertFalse(list(self.root.glob(".desktop-transcode-*")))
        self.assertFalse(list(self.root.glob("*-low.jpg")))
        self.assertFalse(list(self.root.glob("*-high.jpg")))
        self.assertFalse((self.root / "clipboard").exists())

    def test_desktopctl_term_reaches_the_encoder(self):
        self.start([sys.executable, str(base.SCRIPT), "transcode", str(self.input), "jpg", "low"])
        self.assert_cancelled(signal.SIGTERM)

    def test_batch_cancellation_waits_for_cleanup_and_does_not_start_next_file(self):
        self.start([sys.executable, str(base.SCRIPT), "transcode", str(self.input), str(self.other)])
        self.assert_cancelled(signal.SIGTERM)
        self.assertEqual(self.other.read_text(), "other original")

    def test_wrapper_interrupt_reaches_the_encoder(self):
        self.start([str(WRAPPER), str(self.input), "jpg", "low"])
        self.assert_cancelled(signal.SIGINT)

    def test_cancelled_picker_starts_no_encoder(self):
        self.tool("desktopctl", "exit 130")
        result = subprocess.run(["bash", str(SCRIPT), str(self.input)], env=self.env,
                                capture_output=True, text=True, timeout=8)
        self.assertEqual(result.returncode, 130, result.stderr)
        self.assertFalse((self.root / "started").exists())
        self.assertFalse(list(self.root.glob(".desktop-transcode-*")))
