"""Run portable build wrappers in scratch checkouts with a fake Cargo toolchain."""
from dataclasses import dataclass
import fcntl
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest


DOTS = Path(__file__).resolve().parents[1] / "dotfiles"
HELPER = Path("bin/.local/share/dotfiles/rust-build.sh")
BASH = shutil.which("bash")


@dataclass(frozen=True)
class Tool:
    package: str
    name: str
    source: str
    binaries: tuple[str, ...]


TOOLS = (
    Tool("background-grid", "background-grid", ".local/share/background-grid", ("background-grid-native",)),
    Tool("bin", "plot", ".local/share/plot", ("plot-native",)),
    Tool("chrome", "dictation-volume-duck", ".local/share/dictation-volume-duck", ("dictation-volume-duck-native",)),
    Tool("cluster", "cluster", ".local/share/cluster", ("cluster-native",)),
    Tool("desktop-tools", "desktop-transcode", ".local/share/desktop-transcode", ("desktop-transcode-native",)),
    Tool("desktop-tools", "project-picker", ".local/share/desktop-tools/project-picker-tui", ("project-picker-core", "project-picker-tui")),
    Tool("dictate", "dictate", ".local/share/dictate", ("dictate", "dictate-overlay")),
    Tool("file-picker", "file-picker", ".local/share/file-picker", ("file-picker-native", "file-picker-drag")),
    Tool("iphone-transfer", "iphone-transfer", ".local/share/iphone-transfer", ("iphone-transfer-native",)),
    Tool("text-picker", "text-picker", ".local/share/text-picker", ("text-picker-native",)),
    Tool("waybar", "waybar-weather", ".local/share/waybar-weather", ("waybar-weather-native",)),
    Tool("waybar", "workspaces-slider", ".config/waybar/workspaces-slider-rs", ("workspaces-slider",)),
)


def tree(path):
    return {str(file.relative_to(path)): file.read_bytes()
            for file in path.rglob("*") if file.is_file()}


class RustBuildTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="rust-build-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        # Spaces exercise quoting in the wrappers and shared helper.
        self.repo = self.root / "dotfiles checkout"
        self.cache = self.root / "cache directory"
        self.commands = self.root / "commands"
        self.commands.mkdir()
        self.log = self.root / "cargo.jsonl"
        self.env = {key: value for key, value in os.environ.items()
                    if not key.startswith(("CARGO_", "RUST_TEST_"))
                    and key not in ("RUSTFLAGS", "CLUSTER_BUILD_TARGET")}
        self.env.update({
            "HOME": str(self.root / "home"),
            "XDG_CACHE_HOME": str(self.cache),
            "XDG_DATA_HOME": str(self.root / "unrelated data"),
            "XDG_CONFIG_HOME": str(self.root / "unrelated config"),
            "PATH": str(self.commands) + os.pathsep + os.environ["PATH"],
            "PYTHONDONTWRITEBYTECODE": "1",
            "RUST_TEST_LOG": str(self.log),
        })
        (self.repo / HELPER).parent.mkdir(parents=True)
        shutil.copy2(DOTS / HELPER, self.repo / HELPER)
        self.scripts = {}
        self.sources = {}
        for tool in TOOLS:
            script = self.repo / tool.package / ".local/bin" / (tool.name + "-build")
            script.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(DOTS / tool.package / ".local/bin" / script.name, script)
            source = self.repo / tool.package / tool.source
            for directory in ("src", "tests", "assets", ".cargo"):
                (source / directory).mkdir(parents=True)
            manifest = f'[package]\nname = "{tool.name}"\nversion = "0.1.0"\nedition = "2024"\n'
            manifest += ''.join(f'\n[[bin]]\nname = "{binary}"\npath = "src/main.rs"\n'
                                for binary in tool.binaries)
            (source / "Cargo.toml").write_text(manifest)
            (source / "Cargo.lock").write_text("version = 4\n")
            for name in ("src/main.rs", "tests/current.rs", "assets/current.txt",
                         ".cargo/config.toml", "dictionary.example.toml"):
                (source / name).write_text("fixture\n")
            (source / "generation").write_text("v1")
            self.scripts[tool.name] = script
            self.sources[tool.name] = source
        (self.repo / "cluster/tests").mkdir()
        (self.repo / "cluster/tests/test_fixture.py").write_text('''
import os
from pathlib import Path
import unittest

class BuildCheck(unittest.TestCase):
    def test_integration_receives_built_binary(self):
        self.assertTrue(Path(os.environ["CLUSTER_TEST_BINARY"]).is_file())
''')
        self.command("cargo", '''
import json
import os
from pathlib import Path
import sys
import tomllib

args = sys.argv[1:]
manifest = Path(args[args.index("--manifest-path") + 1])
generation = (manifest.parent / "generation").read_text()
with open(os.environ["RUST_TEST_LOG"], "a") as log:
    log.write(json.dumps({"args": args, "generation": generation,
                          "jobs": os.environ["CARGO_BUILD_JOBS"]}) + "\\n")
if os.environ.get("RUST_TEST_FAIL") == args[0]:
    sys.exit(23)
if args[0] == "build":
    target = Path(os.environ["CARGO_TARGET_DIR"])
    if "--target" in args:
        target /= args[args.index("--target") + 1]
    release = target / "release"
    release.mkdir(parents=True, exist_ok=True)
    if "--bin" in args:
        names = [args[args.index("--bin") + 1]]
    else:
        names = [entry["name"] for entry in tomllib.loads(manifest.read_text())["bin"]]
    for name in names:
        binary = release / name
        binary.write_text(generation)
        binary.chmod(0o755)
''')
        self.command("rustc", 'print("host: x86_64-unknown-linux-musl")\n')
        self.command("readelf", 'print("No dynamic section")\n')
        self.command("desktopctl", "raise SystemExit(1)\n")
        self.command("flock", f'''
import os
from pathlib import Path
import sys
if marker := os.environ.get("RUST_TEST_LOCK_ATTEMPT"):
    Path(marker).touch()
os.execv({shutil.which("flock")!r}, ["flock", *sys.argv[1:]])
''')

    def command(self, name, source):
        path = self.commands / name
        path.write_text(f"#!{sys.executable}\n" + source)
        path.chmod(0o755)

    def run_build(self, tool, *args, extra_env=None):
        return subprocess.run([BASH, self.scripts[tool], *args],
                              env=self.env | (extra_env or {}),
                              capture_output=True, text=True, timeout=15)

    def events(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()]

    def seed_cache(self, tool):
        cache = self.cache / tool.name
        for name in ("src/deleted.rs", "tests/deleted.rs", "assets/deleted.txt", "obsolete.toml"):
            old = cache / "build" / name
            old.parent.mkdir(parents=True, exist_ok=True)
            old.write_text("obsolete")
        (cache / "target").mkdir()
        (cache / "target/retained").write_text("compiler cache")
        (cache / "bin").mkdir()
        for binary in tool.binaries:
            (cache / "bin" / binary).write_text("old executable")
        return cache

    def test_all_helpers_replace_complete_snapshots_and_publish_after_checks(self):
        for tool in TOOLS:
            with self.subTest(tool=tool.name):
                original = tree(self.sources[tool.name])
                cache = self.seed_cache(tool)
                result = self.run_build(tool.name, "--check")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(tree(cache / "build"), original)
                self.assertEqual(tree(self.sources[tool.name]), original)
                self.assertEqual((cache / "target/retained").read_text(), "compiler cache")
                for name in tool.binaries:
                    binary = cache / "bin" / name
                    self.assertEqual(binary.read_text(), "v1")
                    self.assertTrue(os.access(binary, os.X_OK))
                self.assertEqual(list((cache / "bin").glob("*.new")), [])
                events = self.events()[-4:]
                self.assertEqual([event["args"][0] for event in events],
                                 ["fmt", "clippy", "test", "build"])
                for event in events:
                    args = event["args"]
                    self.assertEqual(args[args.index("--manifest-path") + 1],
                                     str(cache / "build/Cargo.toml"))
                    self.assertEqual(event["jobs"], "2")
                    if args[0] != "fmt":
                        self.assertIn("--locked", args)
                    if tool.name in ("file-picker", "dictate") and args[0] != "fmt":
                        self.assertEqual(args[args.index("--features") + 1],
                                         "drag" if tool.name == "file-picker" else "overlay")

    def test_invalid_arguments_never_change_the_cache(self):
        for tool in TOOLS:
            for args in (("--unknown",), ("--check", "extra")):
                with self.subTest(tool=tool.name, args=args):
                    result = self.run_build(tool.name, *args)
                    self.assertEqual(result.returncode, 2, result.stderr)
                    self.assertIn(f"Usage: {tool.name}-build [--check]", result.stderr)
                    self.assertFalse((self.cache / tool.name).exists())
        self.assertFalse(self.log.exists())

    def test_missing_source_lockfiles_preserve_previous_cache(self):
        for tool in TOOLS:
            with self.subTest(tool=tool.name):
                cache = self.seed_cache(tool)
                previous = tree(cache)
                (self.sources[tool.name] / "Cargo.lock").unlink()
                result = self.run_build(tool.name)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Missing source Cargo.lock", result.stderr)
                self.assertEqual(tree(cache), previous)
        self.assertFalse(self.log.exists())

    def test_copy_failure_keeps_previous_snapshot_and_executable(self):
        tool = next(tool for tool in TOOLS if tool.name == "project-picker")
        cache = self.seed_cache(tool)
        previous = tree(cache)
        self.command("cp", '''
from pathlib import Path
import sys
(Path(sys.argv[-1]) / "partial-copy").touch()
sys.exit(1)
''')
        result = self.run_build(tool.name)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(tree(cache / "build"),
                         {key.removeprefix("build/"): value for key, value in previous.items()
                          if key.startswith("build/")})
        self.assertEqual((cache / "bin/project-picker-tui").read_text(), "old executable")
        self.assertEqual(list(cache.glob("source.*")), [])
        self.assertFalse(self.log.exists())

    def test_failed_checks_and_builds_preserve_all_published_executables(self):
        tool = next(tool for tool in TOOLS if tool.name == "dictate")
        cache = self.seed_cache(tool)
        for index, stage in enumerate(("fmt", "clippy", "test", "build")):
            with self.subTest(stage=stage):
                result = self.run_build(tool.name, "--check", extra_env={"RUST_TEST_FAIL": stage})
                self.assertEqual(result.returncode, 23, result.stderr)
                for name in tool.binaries:
                    self.assertEqual((cache / "bin" / name).read_text(), "old executable")
                self.assertEqual([event["args"][0] for event in self.events()],
                                 ["fmt", "clippy", "test", "build"][:index + 1])
                self.log.unlink()

    def start_build(self, tool, extra_env):
        process = subprocess.Popen([BASH, self.scripts[tool]], env=self.env | extra_env,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   text=True, start_new_session=True)

        def cleanup():
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
            process.communicate(timeout=5)

        self.addCleanup(cleanup)
        return process

    def await_marker(self, marker, process):
        deadline = time.monotonic() + 10
        while not marker.exists():
            self.assertIsNone(process.poll(), "build exited before reaching the marker")
            self.assertLess(time.monotonic(), deadline, f"Timed out waiting for {marker}")
            time.sleep(0.01)

    def test_concurrent_builds_hold_lock_through_atomic_publication(self):
        tool = next(tool for tool in TOOLS if tool.name == "project-picker")
        cache = self.seed_cache(tool)
        paused = self.root / "publish-paused"
        release = self.root / "publish-release"
        attempted = self.root / "second-lock-attempt"
        self.command("mv", f'''
import os
from pathlib import Path
import sys
import time
if os.environ.get("RUST_TEST_PAUSE_PUBLISH") and sys.argv[-1] == {str(cache / "bin/project-picker-tui")!r}:
    Path({str(paused)!r}).touch()
    deadline = time.monotonic() + 10
    while not Path({str(release)!r}).exists():
        if time.monotonic() > deadline:
            sys.exit("Timed out waiting to publish")
        time.sleep(0.01)
os.execv({shutil.which("mv")!r}, ["mv", *sys.argv[1:]])
''')
        first = self.start_build(tool.name, {"RUST_TEST_PAUSE_PUBLISH": "1"})
        self.await_marker(paused, first)
        (self.sources[tool.name] / "generation").write_text("v2")
        second = self.start_build(tool.name, {"RUST_TEST_LOCK_ATTEMPT": str(attempted)})
        self.await_marker(attempted, second)
        with (cache / "build.lock").open("a") as lock:
            with self.assertRaises(BlockingIOError):
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        self.assertIsNone(second.poll())
        self.assertEqual((cache / "build/generation").read_text(), "v1")
        self.assertEqual((cache / "bin/project-picker-tui").read_text(), "old executable")
        self.assertEqual([event["generation"] for event in self.events()], ["v1"])
        release.touch()
        for process in (first, second):
            _, error = process.communicate(timeout=15)
            self.assertEqual(process.returncode, 0, error)
        self.assertEqual([event["generation"] for event in self.events()], ["v1", "v2"])
        self.assertEqual((cache / "build/generation").read_text(), "v2")
        self.assertEqual((cache / "bin/project-picker-tui").read_text(), "v2")

    def test_job_limit_can_be_overridden(self):
        result = self.run_build("project-picker", extra_env={"CARGO_BUILD_JOBS": "5"})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.events()[0]["jobs"], "5")

    def test_cluster_can_still_use_its_bundled_helper(self):
        helper = self.repo / HELPER
        shutil.copy2(helper, self.sources["cluster"] / "rust-build.sh")
        helper.unlink()
        result = self.run_build("cluster")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.cache / "cluster/bin/cluster-native").read_text(), "v1")

    def test_slider_launcher_runs_published_copy(self):
        tool = next(tool for tool in TOOLS if tool.name == "workspaces-slider")
        cache = self.seed_cache(tool)
        binary = cache / "bin/workspaces-slider"
        binary.write_text(f'#!{BASH}\nprintf "published\\n"\n')
        binary.chmod(0o755)
        result = subprocess.run([BASH, DOTS / "waybar/.local/bin/workspaces-slider"],
                                env=self.env, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "published\n")


if __name__ == "__main__":
    unittest.main()
