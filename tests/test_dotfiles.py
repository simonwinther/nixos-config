"""Exercise package selection, real Stow behavior and the Nix deployment reader."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("dotfiles_parity", ROOT / "tests/dotfiles-parity.py")
parity = importlib.util.module_from_spec(spec)
spec.loader.exec_module(parity)


@unittest.skipUnless(shutil.which("stow"), "GNU Stow is required")
class DotfilesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="dotfiles-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.dots = self.root / "dotfiles"
        self.dots.mkdir()
        (self.root / "scripts").mkdir()
        shutil.copy(ROOT / "scripts/stow-portable", self.root / "scripts/stow-portable")
        shutil.copy(ROOT / "dotfiles/deploy.py", self.dots / "deploy.py")
        self.manifest = json.loads((ROOT / "dotfiles/packages.json").read_text())
        self.manifest["packages"] = ["a"]
        self.write("a/.config/tool/settings")
        self.save_manifest()

    def write(self, relative, text="content"):
        path = self.dots / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def save_manifest(self):
        (self.dots / "packages.json").write_text(json.dumps(self.manifest))

    def nix_files(self, success=True):
        if not shutil.which("nix-instantiate"):
            self.skipTest("Nix evaluator is required")
        expression = (f'(import {ROOT / "lib/dotfiles.nix"} '
                      f'{{ root = builtins.toPath {json.dumps(str(self.dots))}; }}).files')
        result = subprocess.run(["nix-instantiate", "--eval", "--strict", "--json", "--expr", expression],
                                text=True, capture_output=True)
        if success:
            self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("error:", result.stderr)

    def test_unlisted_directories_and_shared_literal_exclusions(self):
        for path in ["unlisted/.unexpected", "a/README.md", "a/tests/test.py", "a/AGENTS.md",
                     "a/.config/tool/AGENTS.md", "a/.config/tool/__pycache__/cache",
                     "a/.config/tool/compiled.pyc", "a/.config/tool/compiled.pyo",
                     "a/.config/tool/.gitignore", "a/.git/config", "a/ignored[1]"]:
            self.write(path)
        for path in ["a/.config/tool/README.md", "a/.config/tool/tests/example", "a/ignored1"]:
            self.write(path)
        self.manifest["ignore"]["names"].append("ignored[1]")
        self.save_manifest()
        actual = parity.stow_targets(self.root)
        self.assertEqual(set(actual), {".config/tool/settings", ".config/tool/README.md",
                                       ".config/tool/tests/example", "ignored1"})
        self.assertEqual(parity.differences(self.nix_files(), actual), [])

    def test_invalid_manifest_never_changes_target(self):
        (self.dots / "linked").symlink_to(self.dots / "a", target_is_directory=True)
        (self.dots / "z").mkdir()
        target = self.root / "target"
        target.mkdir()
        for packages in [[], ["a", "a"], ["missing"], ["../escape"], ["linked"], ["z", "a"]]:
            with self.subTest(packages=packages):
                self.manifest["packages"] = packages
                self.save_manifest()
                result = subprocess.run(["bash", str(self.root / "scripts/stow-portable"), str(target), "--apply"],
                                        capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("stow-portable:", result.stderr)
                self.assertEqual(list(target.iterdir()), [])
                self.nix_files(success=False)

    def test_exact_and_parent_target_conflicts_fail_before_linking(self):
        self.manifest["packages"] = ["a", "b"]
        self.save_manifest()
        for target in ["b/.config/tool/settings", "b/.config/tool"]:
            with self.subTest(target=target):
                self.write(target)
                self.nix_files(success=False)
                with self.assertRaisesRegex(RuntimeError, "Stow deployment failed"):
                    parity.stow_targets(self.root)
                shutil.rmtree(self.dots / "b")

    def test_package_local_ignore_drift_is_reported(self):
        self.write("a/.stow-local-ignore", "^/\\.config/tool/settings$\n")
        problems = parity.differences(self.nix_files(), parity.stow_targets(self.root))
        self.assertEqual(problems, ["Home Manager only: .config/tool/settings (a/.config/tool/settings)"])

    def test_dry_run_and_conflict_preserve_existing_files(self):
        target = self.root / "target"
        target.mkdir()
        command = ["bash", str(self.root / "scripts/stow-portable"), str(target)]
        env = {**os.environ, "HOME": str(self.root)}
        result = subprocess.run(command, env=env, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(list(target.iterdir()), [])
        precious = target / ".config/tool/settings"
        precious.parent.mkdir(parents=True)
        precious.write_text("preserve")
        self.write("a/.another")
        result = subprocess.run([*command, "--apply"], env=env, text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(precious.read_text(), "preserve")
        self.assertFalse((target / ".another").exists())

    def test_comparison_reports_extra_targets_and_wrong_sources(self):
        expected = [{"target": ".config/tool/settings", "source": "a/.config/tool/settings"}]
        actual = {".config/tool/settings": "b/.config/tool/settings", ".extra": "b/.extra"}
        problems = parity.differences(expected, actual)
        self.assertTrue(any("Stow only: .extra" in problem for problem in problems))
        self.assertTrue(any("Different source for .config/tool/settings" in problem for problem in problems))
        with self.assertRaisesRegex(ValueError, "duplicate destinations"):
            parity.differences(expected * 2, actual)


if __name__ == "__main__":
    unittest.main()
