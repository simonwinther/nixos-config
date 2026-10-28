#!/usr/bin/env python3
"""Measure desktopctl startup and theme rendering in disposable XDG directories.

Only read-only queries and `theme init` are executed. PATH and session addresses
are cleared so a benchmark cannot reach desktop services or native tools.
"""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import platform
import shutil
import statistics
import subprocess
import sys
import tempfile
import time


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "dotfiles/desktop-tools/.local/share/desktop-tools/desktopctl.py"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--script", type=Path, default=SOURCE)
    parser.add_argument("--baseline", type=Path, help="Optional preserved entry point for paired measurements")
    parser.add_argument("--iterations", type=int, default=30)
    args = parser.parse_args()
    if args.iterations < 2:
        parser.error("--iterations must be at least 2")
    scripts = {"candidate": args.script.resolve()}
    if args.baseline:
        scripts["baseline"] = args.baseline.resolve()
    for script in scripts.values():
        if not script.is_file():
            parser.error(f"Missing entry point: {script}")

    with tempfile.TemporaryDirectory(prefix="desktopctl-benchmark-") as directory:
        home = Path(directory)
        config = home / ".config"
        for source, target in (
            ("appearance/.config/desktop/themes", "desktop/themes"),
            ("walker/.config/walker/templates", "walker/templates"),
        ):
            shutil.copytree(ROOT / "dotfiles" / source, config / target)
        shutil.copy2(ROOT / "dotfiles/appearance/.config/desktop/settings.json", config / "desktop/settings.json")
        env = {
            "HOME": str(home), "XDG_CONFIG_HOME": str(config),
            "XDG_STATE_HOME": str(home / "state"), "XDG_DATA_HOME": str(home / "data"),
            "XDG_RUNTIME_DIR": str(home / "runtime"), "XDG_CONFIG_DIRS": "/nonexistent",
            "XDG_CACHE_HOME": str(home / "cache"), "PATH": "", "PYTHONDONTWRITEBYTECODE": "1",
            "LANG": os.environ.get("LANG", "C.UTF-8"),
        }
        samples = {}
        for name, command in (("read-current", ["theme", "current"]), ("render-init-unchanged", ["theme", "init"])):
            timings = {label: [] for label in scripts}
            # Warm imports/filesystem caches and seed identical rendered output.
            for script in scripts.values():
                subprocess.run([sys.executable, "-B", str(script), *command], env=env, check=True, capture_output=True)
            for iteration in range(args.iterations):
                # Alternate order to reduce drift between baseline and candidate.
                order = list(scripts) if iteration % 2 == 0 else list(reversed(scripts))
                for label in order:
                    start = time.perf_counter_ns()
                    subprocess.run([sys.executable, "-B", str(scripts[label]), *command], env=env, check=True, capture_output=True)
                    timings[label].append((time.perf_counter_ns() - start) / 1_000_000)
            samples[name] = {
                label: {"median_ms": round(statistics.median(values), 3),
                        "p95_ms": round(sorted(values)[math.ceil(len(values) * .95) - 1], 3)}
                for label, values in timings.items()
            }
    print(json.dumps({"python": platform.python_version(), "iterations": args.iterations,
                      "scope": "warm subprocess startup; isolated XDG state; no desktop IPC", "samples": samples}, indent=2))


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as error:
        print(error.stderr.decode(errors="replace"), file=sys.stderr, end="")
        raise SystemExit(error.returncode)
