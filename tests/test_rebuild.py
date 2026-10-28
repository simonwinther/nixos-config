"""Exercise rebuild safety with disposable Git repos and mocked Nix commands."""
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(os.environ.get(
    "REBUILD_SCRIPT",
    Path(__file__).resolve().parents[1] / "scripts/nixos-rebuild-desktop.sh",
))


class RebuildTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="rebuild-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / "checkout with spaces"
        self.tools = self.root / "tools"
        self.runtime = self.root / "runtime"
        self.state = self.root / "state"
        self.home = self.root / "home"
        for folder in (self.tools, self.runtime, self.home):
            folder.mkdir()
        self.env = os.environ | {
            "HOME": str(self.home),
            "XDG_STATE_HOME": str(self.state),
            "XDG_RUNTIME_DIR": str(self.runtime),
            "PATH": str(self.tools) + os.pathsep + os.environ["PATH"],
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_ALLOW_PROTOCOL": "file",
            "GIT_TERMINAL_PROMPT": "0",
            "repo": str(self.repo),
            "target": "desktop",
            "activation_action": "switch",
            "FAKE_COMMANDS": str(self.root / "commands.jsonl"),
            "FAKE_CLOSURE": str(self.root / "closure"),
        }
        self.init_repo(self.repo)
        (self.repo / "flake.nix").write_text("{}\n")
        (self.repo / "flake.lock").write_text("{}\n")
        self.commit(self.repo)
        self.origin = self.root / "submodule-origin"
        self.init_repo(self.origin)
        (self.origin / "config").write_text("first\n")
        self.commit(self.origin)
        self.pinned = self.git(self.origin, "rev-parse", "HEAD")
        self.git(self.repo, "submodule", "add", "--quiet", str(self.origin), "dotfiles")
        self.commit(self.repo)
        self.submodule = self.repo / "dotfiles"
        (self.origin / "config").write_text("second\n")
        self.commit(self.origin)
        self.newer = self.git(self.origin, "rev-parse", "HEAD")
        self.git(self.submodule, "fetch", "--quiet")

        # Neither stub executes a closure or contacts the Nix daemon.
        stub = f"#!{sys.executable}\n" + '''import json, os, pathlib, subprocess, sys
name = pathlib.Path(sys.argv[0]).name
args = sys.argv[1:]
with open(os.environ["FAKE_COMMANDS"], "a") as log:
    log.write(json.dumps([name, *args]) + "\\n")
print(name + " fixture output", flush=True)
if name == "nix":
    if os.environ.get("FAKE_BUILD_EXIT"):
        sys.exit(int(os.environ["FAKE_BUILD_EXIT"]))
    closure = pathlib.Path(os.environ["FAKE_CLOSURE"])
    closure.mkdir(exist_ok=True)
    result = pathlib.Path(args[args.index("--out-link") + 1])
    result.unlink(missing_ok=True)
    result.symlink_to(closure)
    if os.environ.get("FAKE_SOURCE_CHANGE"):
        repo = pathlib.Path(os.environ["repo"])
        (repo / "flake.lock").write_text("changed during build\\n")
        if os.environ["FAKE_SOURCE_CHANGE"] == "commit":
            subprocess.run(["git", "-C", str(repo), "-c", "user.name=Fixture",
                "-c", "user.email=fixture@example.invalid", "commit", "-qam", "concurrent change"], check=True)
else:
    sys.exit(int(os.environ.get("FAKE_ACTIVATE_EXIT", "0")))
'''
        for name in ("nix", "nixos-rebuild"):
            path = self.tools / name
            path.write_text(stub)
            path.chmod(0o755)

    def git(self, repo, *args):
        return subprocess.run(
            ["git", "-C", str(repo), "-c", "user.name=Fixture",
             "-c", "user.email=fixture@example.invalid", "-c", "commit.gpgsign=false",
             *args], env=self.env, check=True, text=True, capture_output=True,
        ).stdout.strip()

    def init_repo(self, repo):
        repo.mkdir()
        self.git(repo, "init", "--quiet")

    def commit(self, repo):
        self.git(repo, "add", "--all")
        self.git(repo, "commit", "--quiet", "-m", "fixture")

    def run_helper(self, *args, ok=True, **env):
        result = subprocess.run(
            ["bash", str(SCRIPT), *args], env=self.env | env,
            text=True, capture_output=True, stdin=subprocess.DEVNULL, timeout=30,
        )
        if ok:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def commands(self):
        path = Path(self.env["FAKE_COMMANDS"])
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def log(self):
        pointer = self.state / "nixos-rebuild/last-log"
        return Path(pointer.read_text().strip()).read_text()

    def test_default_build_only_reports_revisions_and_locks_inputs(self):
        head = self.git(self.repo, "rev-parse", "HEAD")
        self.run_helper()
        commands = self.commands()
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0][:3], [
            "nix", "build", f"{self.repo}#nixosConfigurations.desktop.config.system.build.toplevel",
        ])
        self.assertIn("--no-update-lock-file", commands[0])
        self.assertIn("--no-write-lock-file", commands[0])
        self.assertNotIn("--sudo", commands[0])
        self.assertIn(head, self.log())
        self.assertIn(self.pinned, self.log())
        self.assertIn("Lock SHA256:", self.log())
        self.assertNotIn("applied", self.log())
        self.assertEqual(self.git(self.repo, "status", "--porcelain"), "")
        self.assertEqual((self.state / "nixos-rebuild/last-exit-code").read_text(), "0\n")
        self.assertEqual(Path((self.state / "nixos-rebuild/last-log").read_text().strip()).stat().st_mode & 0o777, 0o600)

    def test_dirty_parent_blocks_all_actions_and_is_logged(self):
        for kind in ("tracked", "staged", "untracked"):
            for action in ("sync", "build", "activate"):
                with self.subTest(kind=kind, action=action):
                    path = self.repo / ("new-file" if kind == "untracked" else "flake.nix")
                    path.write_text("local edit\n")
                    if kind == "staged":
                        self.git(self.repo, "add", str(path))
                    result = self.run_helper(action, ok=False)
                    self.assertIn("Dirty repository", result.stdout)
                    self.assertIn("local edit", path.read_text())
                    self.assertIn("Dirty repository", self.log())
                    self.git(self.repo, "reset", "--quiet", "HEAD", "--", str(path))
                    if kind == "untracked":
                        path.unlink()
                    else:
                        self.git(self.repo, "checkout", "--", str(path))
        self.assertEqual(self.commands(), [])

    def test_dirty_submodule_blocks_all_actions_even_if_git_ignores_it(self):
        self.git(self.repo, "config", "submodule.dotfiles.ignore", "all")
        for kind in ("tracked", "staged", "untracked"):
            for action in ("sync", "build", "activate"):
                with self.subTest(kind=kind, action=action):
                    path = self.submodule / ("new-file" if kind == "untracked" else "config")
                    path.write_text("submodule edit\n")
                    if kind == "staged":
                        self.git(self.submodule, "add", str(path))
                    result = self.run_helper(action, ok=False)
                    self.assertIn("Dirty submodule dotfiles", result.stdout)
                    self.assertIn("submodule edit", path.read_text())
                    self.git(self.submodule, "reset", "--quiet", "HEAD", "--", str(path))
                    if kind == "untracked":
                        path.unlink()
                    else:
                        self.git(self.submodule, "checkout", "--", str(path))
        self.assertEqual(self.commands(), [])

    def test_staged_submodule_pointer_is_never_synchronized(self):
        self.git(self.submodule, "checkout", "--quiet", self.newer)
        self.git(self.repo, "add", "dotfiles")
        result = self.run_helper("sync", ok=False)
        self.assertIn("Staged changes", result.stdout)
        self.assertEqual(self.git(self.submodule, "rev-parse", "HEAD"), self.newer)
        self.assertEqual(self.commands(), [])

    def test_build_refuses_clean_revision_mismatch_and_sync_restores_pin(self):
        self.git(self.submodule, "checkout", "--quiet", self.newer)
        result = self.run_helper("build", ok=False)
        self.assertIn("sync separately", result.stdout)
        self.assertEqual(self.git(self.submodule, "rev-parse", "HEAD"), self.newer)
        self.assertEqual(self.commands(), [])
        self.git(self.repo, "config", "submodule.dotfiles.update", "rebase")
        self.run_helper("sync")
        self.assertEqual(self.git(self.submodule, "rev-parse", "HEAD"), self.pinned)
        self.assertIn(self.newer, self.log())
        self.assertIn(self.pinned, self.log())
        self.assertEqual(self.commands(), [])

    def test_missing_submodule_requires_explicit_sync(self):
        self.git(self.repo, "submodule", "deinit", "--quiet", "dotfiles")
        self.run_helper("build", ok=False)
        self.assertFalse((self.submodule / "config").exists())
        self.assertEqual(self.commands(), [])
        self.run_helper("sync")
        self.assertEqual(self.git(self.submodule, "rev-parse", "HEAD"), self.pinned)
        self.assertEqual(self.commands(), [])

    def add_nested_submodule(self):
        self.git(self.submodule, "submodule", "add", "--quiet", str(self.origin), "nested")
        self.commit(self.submodule)
        self.commit(self.repo)
        return self.submodule / "nested"

    def test_nested_submodule_dirt_is_refused(self):
        nested = self.add_nested_submodule()
        (nested / "untracked").write_text("preserve me\n")
        self.git(self.submodule, "config", "submodule.nested.ignore", "all")
        self.run_helper("sync", ok=False)
        self.assertEqual((nested / "untracked").read_text(), "preserve me\n")
        self.assertIn("dotfiles/nested", self.log())
        self.assertEqual(self.commands(), [])

    def test_staged_nested_pointer_is_refused(self):
        nested = self.add_nested_submodule()
        self.git(nested, "checkout", "--quiet", self.pinned)
        self.git(self.submodule, "add", "nested")
        self.run_helper("sync", ok=False)
        self.assertIn("Staged changes in submodule", self.log())
        self.assertEqual(self.git(nested, "rev-parse", "HEAD"), self.pinned)

    def test_activation_uses_recorded_closure_without_building(self):
        self.run_helper("build")
        self.run_helper("activate")
        self.assertEqual(self.commands()[1], [
            "nixos-rebuild", "switch", "--store-path", self.env["FAKE_CLOSURE"], "--sudo",
        ])
        self.assertEqual(len(self.commands()), 2)

    def test_live_activation_is_separate_and_uses_test(self):
        env = {"target": "desktop-live", "activation_action": "test"}
        self.run_helper("build", **env)
        self.assertEqual(len(self.commands()), 1)
        self.run_helper("activate", **env)
        self.assertEqual(self.commands()[1][1], "test")
        self.assertIn("Live session only", self.log())

    def test_activation_requires_a_successful_build(self):
        self.run_helper("activate", ok=False)
        self.assertEqual(self.commands(), [])

    def test_changed_revision_refuses_activation(self):
        self.run_helper("build")
        (self.repo / "flake.lock").write_text('{"new": true}\n')
        self.commit(self.repo)
        result = self.run_helper("activate", ok=False)
        self.assertIn("differ from the recorded build", result.stdout)
        self.assertEqual(len(self.commands()), 1)

    def test_changed_output_refuses_activation(self):
        self.run_helper("build")
        other = self.root / "different-closure"
        other.mkdir()
        result = self.state / "nixos-rebuild/desktop-result"
        result.unlink()
        result.symlink_to(other)
        self.run_helper("activate", ok=False)
        self.assertEqual(len(self.commands()), 1)

    def test_failed_build_invalidates_previous_build_and_preserves_exit_code(self):
        self.run_helper("build")
        failed = self.run_helper("build", ok=False, FAKE_BUILD_EXIT="23")
        self.assertEqual(failed.returncode, 23)
        self.assertIn("nix fixture output", self.log())
        self.assertIn("build failed (exit 23)", self.log())
        self.assertEqual((self.state / "nixos-rebuild/last-exit-code").read_text(), "23\n")
        self.run_helper("activate", ok=False)
        self.assertEqual([command[0] for command in self.commands()], ["nix", "nix"])

    def test_failed_preflight_also_invalidates_previous_build(self):
        self.run_helper("build")
        (self.repo / "flake.nix").write_text("dirty\n")
        self.run_helper("build", ok=False)
        self.git(self.repo, "checkout", "--", "flake.nix")
        self.run_helper("activate", ok=False)
        self.assertEqual(len(self.commands()), 1)

    def test_source_changes_during_build_prevent_activation(self):
        for kind in ("dirty", "commit"):
            with self.subTest(kind=kind):
                self.run_helper("build", ok=False, FAKE_SOURCE_CHANGE=kind)
                if kind == "dirty":
                    self.git(self.repo, "checkout", "--", "flake.lock")
                self.run_helper("activate", ok=False)
        self.assertTrue(all(command[0] == "nix" for command in self.commands()))

    def test_activation_failure_is_reported(self):
        self.run_helper("build")
        failed = self.run_helper("activate", ok=False, FAKE_ACTIVATE_EXIT="42")
        self.assertEqual(failed.returncode, 42)
        self.assertIn("activate failed (exit 42)", self.log())

    def test_lock_blocks_concurrent_actions(self):
        with (self.runtime / "nixos-rebuild-desktop.lock").open("w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.run_helper("sync", ok=False)
        self.assertEqual(self.commands(), [])

    def test_help_and_invalid_arguments_never_run_commands(self):
        self.run_helper("--help")
        self.run_helper("switch", ok=False)
        self.run_helper("build", "--impure", ok=False)
        self.assertEqual(self.commands(), [])


if __name__ == "__main__":
    unittest.main()
