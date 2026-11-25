"""Check that Slicer cleanup keeps the launching release and one rollback."""
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
import unittest

CLEANUP = os.environ.get("SLICER3D_CLEANUP")
LAUNCHER = os.environ.get("SLICER3D_LAUNCHER")
MARKER = ".slicer3d-launch"


def build(attribute):
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        ["nix", "build", f"{root}#slicer3d.{attribute}", "--no-link", "--print-out-paths"],
        check=True, capture_output=True, text=True,
    )
    return result.stdout.strip()


class Slicer3dCleanup(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cleanup = CLEANUP or f"{build('cleanup')}/bin/slicer3d-cleanup"

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.root = self.tmp / "slicer3d"
        self.root.mkdir()
        self.now = time.time()

    def tearDown(self):
        subprocess.run(["chmod", "-R", "u+w", str(self.tmp)], check=False)
        shutil.rmtree(self.tmp)

    def release(self, version, launched_minutes_ago=None, extensions=True):
        path = self.root / version
        (path / "bin").mkdir(parents=True)
        (path / "Slicer").write_text("")
        if extensions:
            ext = path / "slicer.org" / "Extensions-34645" / "SlicerIGT"
            ext.mkdir(parents=True)
            (ext / "module.py").write_text("")
        if launched_minutes_ago is not None:
            marker = path / MARKER
            marker.write_text("")
            stamp = self.now - launched_minutes_ago * 60
            os.utime(marker, (stamp, stamp))
        return path

    def run_cleanup(self, current):
        return subprocess.run(
            [self.cleanup, str(self.root), current],
            check=True, capture_output=True, text=True, timeout=60,
        )

    def remaining(self):
        return sorted(p.name for p in self.root.iterdir() if not p.name.endswith(".lock"))

    def test_keeps_current_and_most_recently_launched_rollback(self):
        self.release("5.12.4", launched_minutes_ago=0)
        # Lexical order would treat 5.9.0 as newest; launch time must win.
        self.release("5.10.0", launched_minutes_ago=60)
        self.release("5.9.0", launched_minutes_ago=600)
        self.release("5.8.1", launched_minutes_ago=6000)
        self.run_cleanup("5.12.4")
        self.assertEqual(self.remaining(), ["5.10.0", "5.12.4"])
        self.assertTrue((self.root / "5.10.0/slicer.org/Extensions-34645/SlicerIGT/module.py").exists())
        self.assertTrue((self.root / "5.12.4/slicer.org/Extensions-34645/SlicerIGT/module.py").exists())

    def test_rollback_after_downgrade_keeps_newer_release(self):
        self.release("5.10.0", launched_minutes_ago=0)
        self.release("5.12.4", launched_minutes_ago=5)
        self.release("5.8.1", launched_minutes_ago=50)
        self.run_cleanup("5.10.0")
        self.assertEqual(self.remaining(), ["5.10.0", "5.12.4"])

    def test_falls_back_to_directory_mtime_without_marker(self):
        self.release("5.12.4", launched_minutes_ago=0)
        old = self.release("5.6.2")
        recent = self.release("5.8.1")
        os.utime(old, (self.now - 9000, self.now - 9000))
        os.utime(recent, (self.now - 60, self.now - 60))
        self.run_cleanup("5.12.4")
        self.assertEqual(self.remaining(), ["5.12.4", "5.8.1"])

    def test_never_deletes_current_even_when_oldest(self):
        self.release("5.12.4", launched_minutes_ago=999)
        self.release("5.10.0", launched_minutes_ago=1)
        self.release("5.8.1", launched_minutes_ago=2)
        self.run_cleanup("5.12.4")
        self.assertEqual(self.remaining(), ["5.10.0", "5.12.4"])

    def test_skips_release_locked_by_running_launcher(self):
        self.release("5.12.4", launched_minutes_ago=0)
        self.release("5.10.0", launched_minutes_ago=10)
        locked = self.release("5.8.1", launched_minutes_ago=100)
        holder = subprocess.Popen(["flock", "-s", str(locked / MARKER), "sleep", "60"])
        try:
            deadline = time.time() + 10
            while subprocess.run(["flock", "-xn", str(locked / MARKER), "true"]).returncode == 0:
                self.assertLess(time.time(), deadline)
                time.sleep(0.05)
            result = self.run_cleanup("5.12.4")
        finally:
            holder.kill()
            holder.wait()
        self.assertEqual(self.remaining(), ["5.10.0", "5.12.4", "5.8.1"])
        self.assertIn("keeping 5.8.1", result.stderr)

    def test_skips_release_with_running_process(self):
        self.release("5.12.4", launched_minutes_ago=0)
        self.release("5.10.0", launched_minutes_ago=10)
        running = self.release("5.8.1")
        # Keep the name: coreutils may be a multi-call binary keyed on argv[0].
        sleep = running / "bin" / "sleep"
        shutil.copy(shutil.which("sleep"), sleep)
        os.utime(running, (self.now - 9000, self.now - 9000))
        process = subprocess.Popen([str(sleep), "60"])
        try:
            time.sleep(0.2)
            self.assertIsNone(process.poll())
            result = self.run_cleanup("5.12.4")
        finally:
            process.kill()
            process.wait()
        self.assertEqual(self.remaining(), ["5.10.0", "5.12.4", "5.8.1"])
        self.assertIn("keeping 5.8.1", result.stderr)

    def test_does_not_follow_symlinks_outside(self):
        outside = self.tmp / "outside"
        outside.mkdir()
        (outside / "keep").write_text("")
        self.release("5.12.4", launched_minutes_ago=0)
        self.release("5.10.0", launched_minutes_ago=10)
        old = self.release("5.8.1", launched_minutes_ago=100)
        (old / "link").symlink_to(outside)
        (self.root / "5.6.0").symlink_to(outside)
        self.run_cleanup("5.12.4")
        self.assertEqual(self.remaining(), ["5.10.0", "5.12.4", "5.6.0"])
        self.assertTrue((outside / "keep").exists())

    def test_removes_partial_copies_and_ignores_unrelated_entries(self):
        self.release("5.12.4", launched_minutes_ago=0)
        staging = self.root / ".5.14.0.Ab12Cd"
        (staging / "lib").mkdir(parents=True)
        (staging / "lib" / "readonly").mkdir()
        (staging / "lib" / "readonly" / "file").write_text("")
        (staging / "lib" / "readonly").chmod(0o500)
        leftover = self.root / ".retired.Zz9876"
        leftover.mkdir()
        (self.root / "notes").mkdir()
        self.run_cleanup("5.12.4")
        self.assertEqual(self.remaining(), ["5.12.4", "notes"])

    def test_handles_missing_current_release(self):
        self.release("5.10.0", launched_minutes_ago=10)
        self.release("5.8.1", launched_minutes_ago=100)
        self.run_cleanup("5.12.4")
        self.assertEqual(self.remaining(), ["5.10.0"])


class Slicer3dLauncher(unittest.TestCase):
    """Run the real launcher against a stand-in application tree."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.data = self.tmp / "data"
        self.root = self.data / "slicer3d"
        application = self.tmp / "application"
        application.mkdir()
        slicer = application / "Slicer"
        slicer.write_text(
            f"#!{shutil.which('bash')}\n"
            'marker="$(dirname "$0")/.slicer3d-launch"\n'
            'if flock -xn "$marker" true; then echo unlocked; else echo locked; fi\n'
        )
        slicer.chmod(0o555)
        source = Path(LAUNCHER or build("launcher")).read_text()
        source, count = re.subn(
            r"/nix/store/[a-z0-9]{32}-slicer3d-unwrapped-[^/]+", str(application), source
        )
        self.assertEqual(count, 1)
        self.version = re.search(r'^app="\$dataRoot/(.+)"$', source, re.M).group(1)
        self.launcher = self.tmp / "slicer3d-launch"
        self.launcher.write_text(source)
        self.launcher.chmod(0o555)

    def test_installs_marks_in_use_and_cleans_old_releases(self):
        for version, age in (("5.8.1", 100), ("5.10.0", 10), ("5.6.0", 1000)):
            path = self.root / version
            path.mkdir(parents=True)
            stamp = time.time() - age * 60
            os.utime(path, (stamp, stamp))
        (self.root / ".5.12.4.Stale1").mkdir()
        env = dict(os.environ, XDG_DATA_HOME=str(self.data))
        result = subprocess.run(
            [str(self.launcher)], env=env, check=True, capture_output=True, text=True, timeout=60
        )
        self.assertEqual(result.stdout.strip(), "locked")
        self.assertTrue((self.root / self.version / MARKER).is_file())
        deadline = time.time() + 30
        expected = sorted([self.version, "5.10.0"])
        while sorted(p.name for p in self.root.iterdir() if not p.name.endswith(".lock")) != expected:
            self.assertLess(time.time(), deadline, sorted(os.listdir(self.root)))
            time.sleep(0.05)


if __name__ == "__main__":
    unittest.main()
