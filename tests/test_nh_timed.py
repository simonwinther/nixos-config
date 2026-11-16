"""Check that the nh wrapper records rebuild durations without changing nh."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(os.environ.get(
    "NH_SCRIPT",
    Path(__file__).resolve().parents[1] / "scripts/nh-timed.sh",
))

# Creates the out-link like a finished build when FAKE_BUILT is set, then
# relinks the system like activation unless the run is dry.
FAKE_NH = f"#!{sys.executable}\n" + '''import json, os, pathlib, sys
args = sys.argv[1:]
with open(os.environ["FAKE_COMMANDS"], "a") as log:
    log.write(json.dumps(args) + "\\n")
if os.environ.get("FAKE_BUILT"):
    link = next((a.split("=", 1)[1] for a in args if a.startswith("--out-link=")), None)
    for flag in ("-o", "--out-link"):
        if flag in args:
            link = args[args.index(flag) + 1]
    closure = pathlib.Path(os.environ["FAKE_CLOSURE"])
    closure.mkdir(exist_ok=True)
    pathlib.Path(link).unlink(missing_ok=True)
    pathlib.Path(link).symlink_to(closure)
    verb = args[args.index("os") + 1]
    marker = {"switch": "current_system", "test": "current_system", "boot": "system_profile"}.get(verb)
    if marker and "--dry" not in args:
        path = pathlib.Path(os.environ[marker])
        path.unlink()
        path.symlink_to(closure)
sys.exit(int(os.environ.get("FAKE_EXIT", "0")))
'''


class TimedNhTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="nh-timed-test-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.state = self.root / "state"
        fake = self.root / "nh"
        fake.write_text(FAKE_NH)
        fake.chmod(0o755)
        self.env = os.environ | {
            "real_nh": str(fake),
            "HOME": str(self.root),
            "XDG_STATE_HOME": str(self.state),
            "FAKE_COMMANDS": str(self.root / "commands.jsonl"),
            "FAKE_CLOSURE": str(self.root / "closure"),
            "current_system": str(self.root / "current-system"),
            "system_profile": str(self.root / "system"),
        }
        # Both links predate every run, as after an earlier activation.
        for name in ("current_system", "system_profile"):
            link = Path(self.env[name])
            link.symlink_to(self.root / "old-closure")
            os.utime(link, (0, 0), follow_symlinks=False)

    def run_nh(self, *args, **env):
        return subprocess.run(
            ["bash", str(SCRIPT), *args], env=self.env | env, cwd=self.root,
            text=True, capture_output=True, stdin=subprocess.DEVNULL, timeout=30,
        )

    def commands(self):
        path = Path(self.env["FAKE_COMMANDS"])
        return [json.loads(line) for line in path.read_text().splitlines()]

    def rows(self):
        path = self.state / "nixos-rebuild/times.csv"
        if not path.exists():
            return []
        return [line.split(",") for line in path.read_text().splitlines()]

    def operations(self):
        return [(row[1], row[3], row[4]) for row in self.rows()]

    def test_switch_records_build_and_activation(self):
        result = self.run_nh("os", "switch", "--ask", FAKE_BUILT="1")
        self.assertEqual(result.returncode, 0, result.stderr)
        link = str(self.state / "nixos-rebuild/nh-result")
        self.assertEqual(self.commands(), [["os", "switch", "--out-link", link, "--ask"]])
        self.assertEqual(self.operations(), [("build", "0", "nh"), ("activate", "0", "nh")])
        for row in self.rows():
            self.assertRegex(row[0], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
            self.assertTrue(row[2].isdigit())

    def test_build_only_records_the_build(self):
        self.run_nh("os", "build", FAKE_BUILT="1")
        self.assertEqual(self.operations(), [("build", "0", "nh")])

    def test_boot_is_not_counted_as_activation(self):
        self.run_nh("os", "boot", FAKE_BUILT="1")
        self.assertEqual(self.operations(), [("build", "0", "nh"), ("boot", "0", "nh")])

    def test_failed_build_keeps_the_exit_code(self):
        result = self.run_nh("os", "switch", FAKE_EXIT="23")
        self.assertEqual(result.returncode, 23)
        self.assertEqual(self.operations(), [("build", "23", "nh")])

    def test_failed_activation_follows_a_successful_build(self):
        result = self.run_nh("os", "switch", FAKE_BUILT="1", FAKE_EXIT="4")
        self.assertEqual(result.returncode, 4)
        self.assertEqual(self.operations(), [("build", "0", "nh"), ("activate", "4", "nh")])

    def test_successful_run_without_a_build_is_not_recorded(self):
        self.run_nh("os", "switch", "--dry")
        self.assertEqual(self.rows(), [])

    def test_dry_switch_records_its_build_but_no_activation(self):
        result = self.run_nh("os", "switch", "--dry", FAKE_BUILT="1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.operations(), [("build", "0", "nh")])

    def test_callers_out_link_is_reused(self):
        for spelling in (["-o", "custom"], ["--out-link", "custom"], ["--out-link=custom"]):
            with self.subTest(spelling=spelling):
                Path(self.env["FAKE_COMMANDS"]).unlink(missing_ok=True)
                self.run_nh("-v", "os", "test", *spelling, FAKE_BUILT="1")
                self.assertEqual(self.commands(), [["-v", "os", "test", *spelling]])
        self.assertEqual(len(self.rows()), 6)

    def test_other_commands_pass_through_untimed(self):
        for args in (["clean", "all"], ["search", "ripgrep"], ["os", "info"], ["os"], []):
            with self.subTest(args=args):
                Path(self.env["FAKE_COMMANDS"]).unlink(missing_ok=True)
                result = self.run_nh(*args, FAKE_EXIT="3")
                self.assertEqual(result.returncode, 3)
                self.assertEqual(self.commands(), [args])
        self.assertEqual(self.rows(), [])


if __name__ == "__main__":
    unittest.main()
