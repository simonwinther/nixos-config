"""Exercise real disposable child trees, without desktop IPC or live state."""
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest

from test_desktop import ctl

processes = ctl.processes


class ProcessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="desktop-process-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.logs = self.root / "diagnostics"

    def command(self, source, *args):
        return [sys.executable, "-c", source, *map(str, args)]

    def run_code(self, source, *args, **kwargs):
        return processes.run(self.command(source, *args), log_directory=self.logs, capture=True, **kwargs)

    def wait_file(self, path):
        deadline = time.monotonic() + 5
        while not path.exists() and time.monotonic() < deadline:
            time.sleep(.01)
        self.assertTrue(path.exists(), f"Process did not publish {path.name}")

    def assert_stopped(self, pid):
        # A grandchild may briefly be a zombie awaiting the host's init reaper.
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            try:
                state = Path(f"/proc/{pid}/stat").read_text().rsplit(") ", 1)[1].split()[0]
            except FileNotFoundError:
                return
            if state == "Z":
                return
            time.sleep(.01)
        self.fail(f"Synthetic child {pid} survived cleanup")

    def log_text(self):
        return "".join(path.read_text() for path in self.logs.glob("processes.jsonl*"))

    def tree(self, path):
        return self.command('''
import json, os, signal, subprocess, sys, time
from pathlib import Path
signal.signal(signal.SIGTERM, signal.SIG_IGN)
grandchild = subprocess.Popen([sys.executable, "-c",
    "import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); time.sleep(60)"])
Path(sys.argv[1]).write_text(json.dumps([os.getpid(), grandchild.pid]))
print("partial stdout", flush=True)
print("diagnostic before stall", file=sys.stderr, flush=True)
time.sleep(60)
''', path)

    def test_binary_and_text_payloads_are_preserved_without_logging_them(self):
        source = "import sys; sys.stdout.buffer.write(sys.stdin.buffer.read())"
        data = b"private-stdin-stdout\x00\xff" * 10000
        result = self.run_code(source, input=data, text=False)
        self.assertEqual(result.stdout, data)
        self.assertEqual(result.stderr, b"")
        text = "Unicode input æøå\n" * 10000
        self.assertEqual(self.run_code(source, input=text).stdout, text)
        self.assertNotIn("private-stdin-stdout", self.log_text())

    def test_timeout_kills_and_reaps_a_tree_that_ignores_termination(self):
        path = self.root / "pids.json"
        started = time.monotonic()
        with self.assertRaises(processes.ProcessTimeout) as caught:
            processes.run(self.tree(path), log_directory=self.logs, capture=True, timeout=.5)
        self.assertLess(time.monotonic() - started, 4)
        for pid in json.loads(path.read_text()):
            self.assert_stopped(pid)
        self.assertIn(b"partial stdout", caught.exception.output)
        self.assertIn("diagnostic before stall", caught.exception.stderr)
        self.assertIn('"event": "timeout"', self.log_text())

    def test_cancellation_token_cleans_up_the_owned_tree(self):
        path = self.root / "pids.json"
        cancel = threading.Event()
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(processes.run, self.tree(path), log_directory=self.logs,
                                     capture=True, cancel=cancel)
            self.wait_file(path)
            cancel.set()
            with self.assertRaises(processes.Cancelled):
                future.result(timeout=4)
        for pid in json.loads(path.read_text()):
            self.assert_stopped(pid)

    def test_sigterm_cancels_foreground_work_without_a_traceback(self):
        path = self.root / "pids.json"
        source = '''
import json, sys
import desktop_process as p
try:
    with p.cancellation_signals():
        p.run(json.loads(sys.argv[1]), log_directory=sys.argv[2], capture=True)
except p.Cancelled as error:
    sys.exit(128 + error.signum)
'''
        env = {**os.environ, "PYTHONPATH": str(Path(processes.__file__).parent), "PYTHONDONTWRITEBYTECODE": "1"}
        with subprocess.Popen(self.command(source, json.dumps(self.tree(path)), self.logs),
                              env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as caller:
            self.wait_file(path)
            caller.terminate()
            stdout, stderr = caller.communicate(timeout=5)
        self.assertEqual(caller.returncode, 128 + signal.SIGTERM, stderr)
        self.assertEqual((stdout, stderr), (b"", b""))
        for pid in json.loads(path.read_text()):
            self.assert_stopped(pid)

    def test_success_removes_descendants_left_by_the_direct_child(self):
        path = self.root / "pid"
        self.run_code('''
import subprocess, sys
from pathlib import Path
child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
Path(sys.argv[1]).write_text(str(child.pid))
''', path)
        self.assert_stopped(int(path.read_text()))

    def test_noisy_concurrent_commands_have_bounded_private_logs_and_stderr(self):
        source = "import os,sys; os.write(2,b'x'*500000); os.write(2,b'last diagnostic'); sys.exit(7)"
        with ThreadPoolExecutor(max_workers=2) as executor:
            jobs = [executor.submit(self.run_code, source, "private-argument", check=False) for _ in range(2)]
            results = [job.result(timeout=10) for job in jobs]
        for result in results:
            self.assertEqual(result.returncode, 7)
            self.assertLessEqual(len(result.stderr.encode()), processes.TAIL_BYTES)
            self.assertTrue(result.stderr.endswith("last diagnostic"))
        logs = list(self.logs.glob("processes.jsonl*"))
        self.assertEqual(len(logs), processes.LOG_FILES)
        for log in logs:
            self.assertLessEqual(log.stat().st_size, processes.LOG_BYTES)
            self.assertEqual(log.stat().st_mode & 0o777, 0o600)
            for line in log.read_text().splitlines():
                json.loads(line)
        self.assertEqual(self.logs.stat().st_mode & 0o777, 0o700)
        self.assertNotIn("private-argument", self.log_text())

    def test_failure_reports_the_operation_and_diagnostics_path(self):
        with self.assertRaises(processes.ProcessError) as caught:
            self.run_code("import sys; print('backend failed',file=sys.stderr); sys.exit(3)", operation="image")
        self.assertIn("(image)", str(caught.exception))
        self.assertIn(str(self.logs / "processes.jsonl"), str(caught.exception))
        self.assertEqual(caught.exception.stderr.strip(), "backend failed")

    def test_background_stderr_is_bounded_and_failure_status_survives(self):
        job = processes.background(self.command("import os,sys; os.write(2,b'x'*600000); os.write(2,b'background failure'); sys.exit(9)"),
                                   log_directory=self.logs, operation="control")
        self.addCleanup(job.close)
        self.assertEqual(job.wait(timeout=5), 9)
        self.assertIn("background failure", self.log_text())
        self.assertLessEqual(sum(p.stat().st_size for p in self.logs.glob("processes.jsonl*")),
                             processes.LOG_BYTES * processes.LOG_FILES)

    def test_background_supervisor_outlives_the_launcher_and_enforces_its_deadline(self):
        path = self.root / "job-pid"
        source = '''
import sys
from pathlib import Path
import desktop_process as p
job = p.background([sys.executable, "-c", "import sys,time; time.sleep(.2); print('after launcher exit',file=sys.stderr,flush=True); time.sleep(60)"],
                   log_directory=sys.argv[1], operation="control", timeout=.6)
Path(sys.argv[2]).write_text(str(job.pid))
'''
        env = {**os.environ, "PYTHONPATH": str(Path(processes.__file__).parent), "PYTHONDONTWRITEBYTECODE": "1"}
        subprocess.run(self.command(source, self.logs, path), env=env, check=True, capture_output=True, timeout=5)
        pid = int(path.read_text())
        self.addCleanup(lambda: self.kill_synthetic(pid))
        self.assert_stopped(pid)
        self.assertIn("after launcher exit", self.log_text())
        self.assertIn('"event": "timeout"', self.log_text())

    def kill_synthetic(self, pid):
        with processes.contextlib.suppress(ProcessLookupError):
            os.killpg(pid, signal.SIGKILL)

    def test_background_input_is_bounded_while_selection_ownership_can_persist(self):
        path = self.root / "received"
        data = b"clipboard bytes" * 10000
        job = processes.background(self.command("import sys,time; from pathlib import Path; Path(sys.argv[1]).write_bytes(sys.stdin.buffer.read()); time.sleep(60)", path),
                                   log_directory=self.logs, operation="clipboard-owner", input=data)
        self.addCleanup(job.close)
        self.wait_file(path)
        self.assertEqual(path.read_bytes(), data)
        self.assertIsNone(job.poll())
        job.close()
        self.assert_stopped(job.pid)
        with self.assertRaisesRegex(ValueError, "input exceeded"):
            processes.background(self.command("import time; time.sleep(60)"), log_directory=self.logs,
                                 operation="clipboard-owner", input=b"x" * 1000000, input_timeout=.1)

    def test_lock_lifetime_is_explicit_and_context_cleanup_still_applies(self):
        with processes.ManagedProcess(self.command("import time; time.sleep(60)"),
                                      log_directory=self.logs, operation="lock") as child:
            self.assertIsNone(child.deadline)
            with self.assertRaises(subprocess.TimeoutExpired):
                child.wait(timeout=.05)
            self.assertIsNone(child.poll())
        self.assert_stopped(child.pid)

    def test_control_deadlines_cannot_be_disabled_accidentally(self):
        for seconds in (None, 0, -1, float("inf"), float("nan")):
            with self.subTest(timeout=seconds), self.assertRaises(ValueError):
                self.run_code("pass", timeout=seconds)
        self.assertEqual(processes.policy(["systemctl"]), ("service", 45))
        self.assertEqual(processes.policy(["grim"]), ("capture", 15))
        self.assertEqual(processes.policy(["slurp"]), ("selection", 900))


if __name__ == "__main__":
    unittest.main()
