"""Theme publication and caching in disposable XDG homes, without live services."""
import hashlib
import json
import os
from pathlib import Path
import select
import shutil
import subprocess
import sys
import time
import unittest
from unittest.mock import patch

import test_desktop as base

ctl = base.ctl


class ThemeGenerationTests(unittest.TestCase):
    setUp = base.DesktopTests.setUp
    tearDown = base.DesktopTests.tearDown

    def local_theme(self, name="cache-test"):
        source = self.data / "desktop/themes" / name
        source.mkdir(parents=True)
        shutil.copyfile(self.config / "desktop/themes/tokyoled/colors.toml", source / "colors.toml")
        return source

    def published(self):
        return (self.state / "theme").resolve(strict=True)

    def snapshot(self, directory):
        return {str(path.relative_to(directory)): path.read_bytes()
                for path in directory.rglob("*") if path.is_file()}

    def worker(self, code, *args):
        env = {**os.environ, "HOME": str(self.home), "XDG_CONFIG_HOME": str(self.config),
               "XDG_STATE_HOME": str(self.state.parent), "XDG_RUNTIME_DIR": str(self.runtime.parent),
               "XDG_DATA_HOME": str(self.data), "PYTHONDONTWRITEBYTECODE": "1"}
        preamble = ("import importlib.util, sys\n"
                    "from pathlib import Path\n"
                    "sys.path.insert(0, str(Path(sys.argv[1]).parent))\n"
                    "spec = importlib.util.spec_from_file_location('desktopctl', sys.argv[1])\n"
                    "ctl = importlib.util.module_from_spec(spec)\n"
                    "spec.loader.exec_module(ctl)\n")
        child = subprocess.Popen([sys.executable, "-c", preamble + code, str(base.SCRIPT), *args],
                                 env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.addCleanup(self.stop_worker, child)
        return child

    @staticmethod
    def stop_worker(child):
        if child.poll() is None:
            child.kill()
        child.communicate(timeout=5)

    def test_repeated_launches_reuse_the_generation_without_writes(self):
        ctl.prepare_theme()
        generation = self.published()
        before = {path: (path.stat().st_ino, path.stat().st_mtime_ns)
                  for path in generation.rglob("*")}
        with patch.object(ctl, "_render_theme") as render, \
                patch.object(ctl, "atomic_write", wraps=ctl.atomic_write) as write, \
                patch.object(ctl.os, "replace", wraps=ctl.os.replace) as replace, \
                patch.object(ctl, "executable", return_value="/mock/walker"), \
                patch.object(ctl.os, "execv"):
            for _ in range(3):
                ctl.run_application(["walker"])
            render.assert_not_called()
            write.assert_not_called()
            replace.assert_not_called()
        self.assertEqual(self.published(), generation)
        self.assertEqual(before, {path: (path.stat().st_ino, path.stat().st_mtime_ns)
                                  for path in generation.rglob("*")})
        self.assertEqual(os.environ["XDG_CONFIG_DIRS"], str(self.runtime) + ":/etc/xdg")

    def test_palette_content_invalidates_cache_even_with_unchanged_size_and_mtime(self):
        source = self.local_theme()
        ctl.theme(["set", source.name, "--no-reload"])
        previous = self.published()
        palette = source / "colors.toml"
        metadata = palette.stat()
        background = ctl.colors(source)["background"]
        palette.write_text(palette.read_text().replace(background, "#010203"))
        os.utime(palette, ns=(metadata.st_atime_ns, metadata.st_mtime_ns))
        ctl.prepare_theme()
        self.assertNotEqual(self.published(), previous)
        self.assertIn("background = #010203", (self.state / "theme/ghostty.conf").read_text())
        self.assertEqual(ctl.colors(previous)["background"], background)

    def test_custom_files_and_optional_removals_publish_a_fresh_generation(self):
        source = self.local_theme()
        ctl.theme(["set", source.name, "--no-reload"])
        for filename, output, content in (("mako.ini", "mako.ini", "font=Old\n# custom mako\n"),
                                          ("walker.css", "walker.css", "/* custom walker */\n"),
                                          ("btop.theme", "current.theme", 'theme[main_bg]="#010203"\n'),
                                          ("eza.yml", "theme.yml", "filekinds: {}\n"),
                                          ("light.mode", "light.mode", "")):
            with self.subTest(filename=filename):
                previous = self.published()
                (source / filename).write_text(content)
                ctl.prepare_theme()
                self.assertNotEqual(self.published(), previous)
                expected = content.replace("font=Old", "font=JetBrainsMono Nerd Font 11")
                self.assertEqual((self.state / "theme" / output).read_text(), expected)
        (source / "eza.yml").unlink()
        (source / "light.mode").unlink()
        ctl.prepare_theme()
        self.assertFalse((self.state / "theme/theme.yml").exists())
        self.assertFalse((self.state / "theme/light.mode").exists())

    def test_walker_template_additions_edits_and_removals_invalidate_cache(self):
        templates = self.config / "walker/templates"
        templates.unlink()
        shutil.copytree(base.ROOT / "dotfiles/walker/.config/walker/templates", templates)
        ctl.prepare_theme()
        previous = self.published()
        custom = templates / "custom"
        custom.mkdir()
        (custom / "style.css").write_text("/* new view */\n")
        ctl.prepare_theme()
        self.assertNotEqual(self.published(), previous)
        runtime_view = self.runtime / "walker/themes/desktop-custom/style.css"
        self.assertIn("/* new view */", runtime_view.read_text())
        (custom / "style.css").write_text("/* edited view */\n")
        ctl.prepare_theme()
        self.assertIn("/* edited view */", runtime_view.read_text())
        (custom / "style.css").unlink()
        ctl.prepare_theme()
        self.assertFalse(runtime_view.exists())
        runtime_view.parent.rmdir()
        ctl.prepare_theme()
        self.assertTrue(runtime_view.parent.is_dir(), "missing empty views must invalidate the cache")
        custom.rmdir()
        ctl.prepare_theme()
        self.assertFalse(runtime_view.parent.exists())

    def test_font_and_terminal_preferences_invalidate_cache(self):
        ctl.theme(["init"])
        personal = self.published()
        self.assertNotIn("theme =", (personal / "ghostty.conf").read_text())
        with patch.object(ctl, "run", return_value=subprocess.CompletedProcess([], 0, "Cache Mono\n")):
            ctl.font(["set", "Cache Mono", "--no-reload"])
        font_generation = self.published()
        self.assertNotEqual(font_generation, personal)
        self.assertIn("Cache Mono", (self.state / "fontconfig.conf").read_text())
        self.assertIn("Cache Mono", (self.runtime / "walker/themes/desktop-rounded/style.css").read_text())
        with patch.object(ctl, "run"), patch.object(ctl, "restart"):
            ctl.appearance(["terminal-colors", "desktop"])
        self.assertNotEqual(self.published(), font_generation)
        self.assertIn("theme =\n", (self.state / "theme/ghostty.conf").read_text())
        ctl.prepare_theme()
        self.assertIn("Cache Mono", (self.state / "theme/ghostty.conf").read_text())

    def test_default_settings_and_renderer_changes_invalidate_cache(self):
        defaults = self.config / "desktop/settings.json"
        original = json.loads(defaults.read_text())
        defaults.unlink()
        defaults.write_text(json.dumps(original))
        ctl.prepare_theme()
        previous = self.published()
        defaults.write_text(json.dumps({**original, "defaultFont": "Default Cache Mono"}))
        ctl.prepare_theme()
        self.assertNotEqual(self.published(), previous)
        self.assertIn("Default Cache Mono", (self.state / "theme/ghostty.conf").read_text())
        previous = self.published()
        with patch.object(ctl, "THEME_RENDERER", "changed-renderer"):
            ctl.prepare_theme()
        self.assertNotEqual(self.published(), previous)

    def test_missing_or_corrupt_outputs_are_repaired_with_a_new_generation(self):
        ctl.prepare_theme()
        for filename, damage in (("ghostty.conf", "corrupt"),
                                  ("walker/themes/desktop-rounded/layout.xml", "missing"),
                                  (".generation.json", "corrupt")):
            with self.subTest(filename=filename):
                previous = self.published()
                output = previous / filename
                if damage == "missing":
                    output.unlink()
                else:
                    output.write_text("damaged")
                ctl.prepare_theme()
                self.assertNotEqual(self.published(), previous)
                self.assertTrue((self.published() / filename).is_file())
                self.assertNotEqual((self.published() / filename).read_text(), "damaged")

    def test_runtime_alias_is_restored_on_a_cache_hit(self):
        ctl.prepare_theme()
        previous = self.published()
        shutil.rmtree(self.runtime)
        with patch.object(ctl, "_render_theme") as render:
            ctl.prepare_theme()
        render.assert_not_called()
        self.assertEqual(self.published(), previous)
        self.assertEqual((self.runtime / "walker/themes").resolve(), previous / "walker/themes")

    def test_failed_staging_preserves_every_published_file_and_preferences(self):
        ctl.theme(["init"])
        previous = self.published()
        before = self.snapshot(previous)
        preferences = (self.state / "state.json").read_bytes()
        write = ctl.atomic_write

        def fail_walker(path, content, *args, **kwargs):
            if path.name == "style.css":
                # The terminal files have been staged, but no public file has changed.
                self.assertEqual(self.snapshot(previous), before)
                self.assertEqual(self.published(), previous)
                raise OSError("simulated full filesystem")
            return write(path, content, *args, **kwargs)

        with patch.object(ctl, "atomic_write", side_effect=fail_walker):
            for change in (lambda: ctl.theme(["set", "catppuccin-latte", "--no-reload"]),
                           lambda: ctl.font(["set", "Cache Mono", "--no-reload"]),
                           lambda: ctl.appearance(["terminal-colors", "desktop"])):
                with patch.object(ctl, "run", return_value=subprocess.CompletedProcess([], 0, "Cache Mono\n")), \
                        self.assertRaisesRegex(OSError, "simulated full filesystem"):
                    change()
                self.assertEqual(self.published(), previous)
                self.assertEqual((self.state / "state.json").read_bytes(), preferences)
                self.assertEqual(self.snapshot(previous), before)
                self.assertFalse(list((self.state / "theme-generations").glob(".staging-*")))

    def test_legacy_directories_migrate_without_losing_old_content_on_failure(self):
        target = self.state / "theme"
        target.mkdir(parents=True)
        (target / "name").write_text("legacy\n")
        (self.state / "fontconfig.conf").write_text("legacy font\n")
        old_walker = self.runtime / "walker/themes/desktop-rounded/style.css"
        old_walker.parent.mkdir(parents=True)
        old_walker.write_text("legacy walker\n")
        publish = ctl._publish_theme_link

        def fail_pointer(path, destination):
            if path == target:
                self.assertEqual((self.state / "fontconfig.conf").read_text(), "legacy font\n")
                self.assertEqual(old_walker.read_text(), "legacy walker\n")
                self.assertEqual((target / "name").read_text(), "legacy\n")
                raise OSError("simulated publication failure")
            publish(path, destination)

        with patch.object(ctl, "_publish_theme_link", side_effect=fail_pointer), self.assertRaises(OSError):
            ctl.prepare_theme()
        self.assertFalse(target.is_symlink())
        self.assertEqual((self.state / "fontconfig.conf").read_text(), "legacy font\n")
        self.assertEqual(old_walker.read_text(), "legacy walker\n")
        ctl.prepare_theme()
        self.assertTrue(target.is_symlink())
        self.assertEqual((self.state / "fontconfig.conf").resolve(), self.published() / "fontconfig.conf")
        self.assertEqual((self.runtime / "walker/themes").resolve(), self.published() / "walker/themes")
        self.assertNotIn("legacy", old_walker.read_text())

    def test_launch_preparation_waits_for_the_state_transaction(self):
        ctl.prepare_theme()
        previous = self.published()
        with ctl.state_lock():
            child = self.worker("print('ready', flush=True)\nctl.prepare_theme()\nprint('done', flush=True)\n")
            self.assertTrue(select.select([child.stdout], [], [], 5)[0], "worker did not start")
            self.assertEqual(child.stdout.readline(), "ready\n")
            self.assertFalse(select.select([child.stdout], [], [], 0.1)[0], "preparation bypassed the lock")
            self.assertIsNone(child.poll())
            self.assertEqual(self.published(), previous)
        stdout, stderr = child.communicate(timeout=10)
        self.assertEqual(child.returncode, 0, stderr)
        self.assertEqual(stdout, "done\n")

    def test_interrupted_legacy_copy_can_be_retried_without_publishing_partial_walker_files(self):
        target = self.state / "theme"
        target.mkdir(parents=True)
        (target / "name").write_text("legacy\n")
        old_walker = self.runtime / "walker/themes/desktop-rounded/style.css"
        old_walker.parent.mkdir(parents=True)
        old_walker.write_text("legacy walker\n")

        def interrupted_copy(source, destination, **kwargs):
            partial = destination / "desktop-rounded"
            partial.mkdir(parents=True)
            (partial / "style.css").write_text("incomplete copy")
            raise OSError("interrupted migration")

        with patch.object(ctl.shutil, "copytree", side_effect=interrupted_copy), self.assertRaises(OSError):
            ctl.prepare_theme()
        self.assertEqual(old_walker.read_text(), "legacy walker\n")
        self.assertFalse(target.is_symlink())
        publish = ctl._publish_theme_link

        def check_bootstrap(path, destination):
            if path == target:
                self.assertEqual(old_walker.read_text(), "legacy walker\n")
            publish(path, destination)

        with patch.object(ctl, "_publish_theme_link", side_effect=check_bootstrap):
            ctl.prepare_theme()
        self.assertTrue(target.is_symlink())
        self.assertNotIn("incomplete copy", old_walker.read_text())

    def test_concurrent_switches_publish_only_complete_immutable_snapshots(self):
        self.local_theme("cache-a")
        self.local_theme("cache-b")
        ctl.theme(["set", "cache-a", "--no-reload"])
        workers = [self.worker("for _ in range(4):\n    ctl.theme(['set', sys.argv[2], '--no-reload'])\n", name)
                   for name in ("cache-a", "cache-b")]
        deadline = time.monotonic() + 10
        observed = set()
        while any(child.poll() is None for child in workers):
            self.assertLess(time.monotonic(), deadline, "theme writers stalled")
            # Resolve once, as a reader needing a multi-file snapshot would.
            generation = self.published()
            observed.add(generation)
            manifest = json.loads((generation / ".generation.json").read_text())
            for path, digest in manifest["files"].items():
                self.assertEqual(hashlib.sha256((generation / path).read_bytes()).hexdigest(), digest)
            self.assertIn((generation / "name").read_text().strip(), ("cache-a", "cache-b"))
        for child in workers:
            _, stderr = child.communicate(timeout=5)
            self.assertEqual(child.returncode, 0, stderr)
        self.assertTrue(observed)
        self.assertEqual(ctl.selected_theme(), (self.state / "theme/name").read_text().strip())
        self.assertFalse(list((self.state / "theme-generations").glob(".staging-*")))


if __name__ == "__main__":
    unittest.main()
