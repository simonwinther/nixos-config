"""Recording lifecycle checks with real, disposable processes and no desktop access."""
from concurrent.futures import ThreadPoolExecutor
import errno
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "dotfiles/desktop-tools/.local/share/desktop-tools/desktopctl.py"
spec = importlib.util.spec_from_file_location("recording_ctl_test", SCRIPT)
ctl = importlib.util.module_from_spec(spec)
with patch.object(sys, "path", [str(SCRIPT.parent), *sys.path]):
    spec.loader.exec_module(ctl)


@unittest.skipUnless(hasattr(os, "pidfd_open") and hasattr(signal, "pidfd_send_signal"),
                     "Linux pidfds are required for recording control")
class RecordingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.state = self.home / "state/desktop"
        self.config = self.home / "config"
        self.events = self.home / "events.jsonl"
        self.recorder = self.home / "fake-recorder"
        self.recorder.write_text(f"#!{sys.executable}\n" + '''
import json
import os
from pathlib import Path
import signal
import sys
import time

def event(name):
    with Path(os.environ["FAKE_RECORD_EVENTS"]).open("a") as stream:
        stream.write(json.dumps({"event": name, "pid": os.getpid(), "args": sys.argv[1:]}) + "\\n")

def stop(*_):
    event("interrupt")
    time.sleep(float(os.environ.get("FAKE_RECORD_DELAY", "0")))
    Path(sys.argv[-1]).write_bytes(b"finalized recording")
    print("encoder finalized", flush=True)
    event("finalized")
    sys.exit(0)

signal.signal(signal.SIGINT, stop)
print("encoder ready", flush=True)
if os.environ.get("FAKE_RECORD_FAIL"):
    print("encoder startup failure", file=sys.stderr, flush=True)
    sys.exit(23)
event("ready")
while True:
    time.sleep(.01)
''')
        self.recorder.chmod(0o700)
        self.children = []
        self.real_popen = subprocess.Popen
        def spawn(*args, **kwargs):
            child = self.real_popen(*args, **kwargs)
            self.children.append(child)
            return child
        self.patches = [
            patch.multiple(ctl, HOME=self.home, CONFIG=self.config, STATE=self.state),
            patch.object(ctl, "notify"),
            patch.object(ctl, "executable", return_value=str(self.recorder)),
            patch.object(ctl.subprocess, "Popen", side_effect=spawn),
            patch.dict(os.environ, {"FAKE_RECORD_EVENTS": str(self.events), "FAKE_RECORD_DELAY": "0",
                                    "FAKE_RECORD_FAIL": ""}),
        ]
        for replacement in self.patches:
            replacement.start()
            self.addCleanup(replacement.stop)
        self.addCleanup(self.reap_children)

    def reap_children(self):
        for child in self.children:
            if child.poll() is None:
                child.kill()
            child.wait(timeout=3)

    def events_named(self, name):
        if not self.events.exists():
            return []
        return [row for line in self.events.read_text().splitlines()
                if (row := json.loads(line))["event"] == name]

    def wait_event(self, name, pid=None):
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            if any(pid is None or event["pid"] == pid for event in self.events_named(name)):
                return
            time.sleep(.01)
        self.fail(f"Recorder did not emit {name}")

    def current(self):
        return json.loads((self.state / "recording.json").read_text())

    def archives(self):
        return [json.loads(path.read_text()) for path in (self.state / "recordings").glob("*.json")]

    def toggle(self, *args):
        count = len(self.children)
        ctl.capture(["record", *args])
        if len(self.children) > count:
            self.wait_event("ready", self.children[-1].pid)

    def test_stop_waits_for_finalization_before_clearing_state(self):
        with patch.dict(os.environ, {"FAKE_RECORD_DELAY": ".3"}):
            self.toggle()
        current = self.current()
        log = Path(current["log"])
        self.assertEqual(log.stat().st_mode & 0o777, 0o600)
        self.assertEqual((self.state / "recording.json").stat().st_mode & 0o777, 0o600)
        with ThreadPoolExecutor() as executor, patch.object(ctl.os, "kill") as numeric_kill:
            stopping = executor.submit(self.toggle)
            self.wait_event("interrupt")
            self.assertFalse(stopping.done())
            self.assertEqual(self.current()["status"], "stopping")
            self.assertFalse(Path(current["output"]).exists())
            stopping.result(timeout=3)
            numeric_kill.assert_not_called()
        self.assertFalse((self.state / "recording.json").exists())
        self.assertEqual(Path(current["output"]).read_bytes(), b"finalized recording")
        self.assertIn("encoder finalized", log.read_text())
        self.assertEqual(self.archives()[0]["status"], "stopped")

    def test_timeout_retains_state_and_retry_does_not_interrupt_twice(self):
        with patch.dict(os.environ, {"FAKE_RECORD_DELAY": ".4"}):
            self.toggle()
        with patch.object(ctl, "RECORDING_STOP_TIMEOUT", .02), \
                self.assertRaisesRegex(ValueError, "still finalizing.*log:"):
            self.toggle()
        current = self.current()
        self.assertEqual(current["status"], "stopping")
        self.assertTrue(Path(current["log"]).is_file())
        self.assertEqual(self.archives(), [])
        self.toggle()
        self.assertEqual(len(self.events_named("interrupt")), 1)
        self.assertFalse((self.state / "recording.json").exists())
        self.assertEqual(self.archives()[0]["status"], "stopped")

    def test_retry_after_finalization_cleans_up_without_a_new_recording(self):
        with patch.dict(os.environ, {"FAKE_RECORD_DELAY": ".15"}):
            self.toggle()
        with patch.object(ctl, "RECORDING_STOP_TIMEOUT", .01), self.assertRaises(ValueError):
            self.toggle()
        self.children[0].wait(timeout=3)
        self.toggle()
        self.assertEqual(len(self.children), 1)
        self.assertEqual(self.archives()[0]["status"], "stopped")
        self.assertFalse((self.state / "recording.json").exists())

    def test_process_identity_mismatch_and_legacy_state_never_signal(self):
        self.toggle()
        original = self.current()
        for field, replacement in [("start_time", -1), ("boot_id", "previous-boot"),
                                   ("uid", -1), ("executable", [0, 0]),
                                   ("command_sha256", "incorrect")]:
            with self.subTest(field=field):
                changed = {**original, "identity": {**original["identity"], field: replacement}}
                ctl.atomic_write(self.state / "recording.json", json.dumps(changed))
                with self.assertRaisesRegex(ValueError, "unverified recorder"):
                    self.toggle()
                self.assertEqual(self.current(), changed)
                self.assertIsNone(self.children[0].poll())
        legacy = {"pid": original["pid"], "output": original["output"]}
        ctl.atomic_write(self.state / "recording.json", json.dumps(legacy))
        with self.assertRaisesRegex(ValueError, "unverified recorder"):
            self.toggle()
        self.assertEqual(self.events_named("interrupt"), [])
        ctl.atomic_write(self.state / "recording.json", json.dumps(original))
        self.toggle()

    def test_dead_recording_is_archived_without_starting_another(self):
        self.toggle()
        current = self.current()
        self.children[0].terminate()
        self.children[0].wait(timeout=3)
        with self.assertRaisesRegex(ValueError, "no longer running.*log:"):
            self.toggle()
        self.assertFalse((self.state / "recording.json").exists())
        self.assertEqual(len(self.children), 1)
        self.assertEqual(self.archives()[0]["status"], "failed")
        self.assertTrue(Path(current["log"]).is_file())

    def test_startup_failure_keeps_stderr_and_exit_status(self):
        with patch.dict(os.environ, {"FAKE_RECORD_FAIL": "1"}), \
                self.assertRaisesRegex(ValueError, "failed to start.*log:"):
            self.toggle()
        self.assertFalse((self.state / "recording.json").exists())
        archived = self.archives()[0]
        self.assertEqual(archived["status"], "failed")
        self.assertEqual(archived["returncode"], 23)
        self.assertIn("encoder startup failure", Path(archived["log"]).read_text())

    def test_state_publication_failure_stops_the_spawned_recorder(self):
        write = ctl.atomic_write
        def fail_active_state(path, *args, **kwargs):
            if path == self.state / "recording.json":
                raise OSError("cannot publish active recording")
            return write(path, *args, **kwargs)
        with patch.object(ctl, "atomic_write", side_effect=fail_active_state), \
                self.assertRaisesRegex(ValueError, "failed to start.*cannot publish.*log:"):
            self.toggle()
        self.assertIsNotNone(self.children[0].poll())
        self.assertFalse((self.state / "recording.json").exists())
        self.assertEqual(self.archives()[0]["status"], "failed")

    def test_archive_failure_keeps_active_state_and_logs_for_retry(self):
        self.toggle()
        write = ctl.atomic_write
        def fail_archive(path, *args, **kwargs):
            if path.parent == self.state / "recordings":
                raise OSError("cannot archive recording")
            return write(path, *args, **kwargs)
        with patch.object(ctl, "atomic_write", side_effect=fail_archive), \
                self.assertRaisesRegex(OSError, "cannot archive"):
            self.toggle()
        self.assertEqual(self.current()["status"], "stopping")
        self.assertTrue(Path(self.current()["log"]).is_file())
        self.toggle()
        self.assertFalse((self.state / "recording.json").exists())
        self.assertEqual(len(self.events_named("interrupt")), 1)
        self.assertEqual(self.archives()[0]["status"], "stopped")

    def test_signal_failure_preserves_recording_and_can_be_retried(self):
        self.toggle()
        with patch.object(ctl.signal, "pidfd_send_signal", side_effect=PermissionError("denied")), \
                self.assertRaisesRegex(PermissionError, "denied"):
            self.toggle()
        self.assertEqual(self.current()["status"], "recording")
        self.assertEqual(self.events_named("interrupt"), [])
        self.assertEqual(self.archives(), [])
        self.toggle()
        self.assertFalse((self.state / "recording.json").exists())

    def test_corrupt_or_invalid_state_blocks_new_recorders(self):
        for contents in ["broken json", "[]", "{}", '{"pid": -1}', '{"pid": true}']:
            with self.subTest(contents=contents):
                ctl.atomic_write(self.state / "recording.json", contents)
                with self.assertRaises(ValueError):
                    self.toggle()
                self.assertEqual((self.state / "recording.json").read_text(), contents)
        self.assertEqual(self.children, [])

    def test_missing_kernel_support_fails_before_spawning(self):
        with patch.object(ctl.os, "pidfd_open", side_effect=OSError(errno.ENOSYS, "unsupported")), \
                self.assertRaises(OSError):
            self.toggle()
        self.assertEqual(self.children, [])
        self.assertFalse((self.state / "recording.json").exists())

    def test_cross_process_request_waits_for_start_and_then_stops_it(self):
        env = {**os.environ, "HOME": str(self.home), "XDG_CONFIG_HOME": str(self.config),
               "XDG_STATE_HOME": str(self.home / "state"),
               "DESKTOP_GPU_SCREEN_RECORDER_BIN": str(self.recorder),
               "PATH": str(self.home)}
        notifier = self.home / "notify-send"
        notifier.write_text(f"#!{sys.executable}\n")
        notifier.chmod(0o700)
        with ctl.state_lock("recording"):
            waiter = self.real_popen([sys.executable, str(SCRIPT), "capture", "record"],
                                     env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            def reap_waiter():
                if waiter.poll() is None:
                    waiter.kill()
                waiter.communicate(timeout=3)
            self.addCleanup(reap_waiter)
            time.sleep(.1)
            self.assertIsNone(waiter.poll())
            ctl.start_recording(["record"])
            self.wait_event("ready", self.children[-1].pid)
        stdout, stderr = waiter.communicate(timeout=3)
        self.assertEqual(waiter.returncode, 0, stdout + stderr)
        self.assertFalse((self.state / "recording.json").exists())
        self.assertEqual(len(self.events_named("ready")), 1)
        self.assertEqual(len(self.events_named("interrupt")), 1)

    def test_capture_modes_and_audio_options_preserve_unique_outputs(self):
        outputs = []
        for args, expected in [([], ["-a", "default_output"]),
                               (["screen", "--silent"], []),
                               (["region", "--microphone"], ["-a", "default_output", "-a", "default_input"])]:
            with self.subTest(args=args), \
                    patch.object(ctl, "screenshot_geometry", return_value="-10,20 120x80"), \
                    patch.object(ctl.time, "strftime", return_value="same-second"):
                self.toggle(*args)
                current = self.current()
                command = current["command"]
                audio = [item for index, item in enumerate(command)
                         if item == "-a" or (index and command[index - 1] == "-a")]
                self.assertEqual(audio, expected)
                if args and args[0] == "region":
                    self.assertEqual(command[command.index("-region") + 1], "120x80+-10+20")
                else:
                    self.assertEqual(command[command.index("-w") + 1], "portal")
                outputs.append(Path(current["output"]))
                self.toggle()
        self.assertEqual(len(set(outputs)), 3)
        self.assertTrue(all(output.read_bytes() == b"finalized recording" for output in outputs))


if __name__ == "__main__":
    unittest.main()
