"""Compare evaluated Home Manager destinations/sources with real GNU Stow links."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def stow_targets(root):
    dots = (root / "dotfiles").resolve()
    with tempfile.TemporaryDirectory(prefix="dotfiles-parity-") as directory:
        scratch = Path(directory)
        target = scratch / "target"
        target.mkdir()
        isolated_home = scratch / "home"
        isolated_home.mkdir()
        result = subprocess.run(
            ["bash", str(root / "scripts/stow-portable"), str(target), "--apply"],
            cwd=scratch, text=True, capture_output=True,
            env={**os.environ, "HOME": str(isolated_home), "PYTHONDONTWRITEBYTECODE": "1"},
        )
        if result.returncode:
            raise RuntimeError(f"Stow deployment failed:\n{result.stdout}{result.stderr}")
        links = {}
        for directory, dirs, files in os.walk(target, followlinks=False):
            for name in dirs + files:
                path = Path(directory) / name
                if path.is_symlink():
                    # Preserve the package source path, including source symlinks.
                    source = Path(os.path.abspath(path.parent / os.readlink(path)))
                    links[str(path.relative_to(target))] = str(source.relative_to(dots))
                elif name in files:
                    raise RuntimeError(f"Stow created a non-link target: {path.relative_to(target)}")
        return links


def differences(expected, actual):
    files = {file["target"]: file["source"] for file in expected}
    if len(files) != len(expected):
        raise ValueError("Evaluated Home Manager files have duplicate destinations")
    problems = []
    for target in sorted(files.keys() - actual.keys()):
        problems.append(f"Home Manager only: {target} ({files[target]})")
    for target in sorted(actual.keys() - files.keys()):
        problems.append(f"Stow only: {target} ({actual[target]})")
    for target in sorted(files.keys() & actual.keys()):
        if files[target] != actual[target]:
            problems.append(f"Different source for {target}: Home Manager={files[target]}, Stow={actual[target]}")
    return problems


def main():
    root = Path(sys.argv[1]).resolve()
    homes = json.loads(Path(sys.argv[2]).read_text())
    actual = stow_targets(root)
    failed = False
    for host, expected in homes.items():
        problems = differences(expected, actual)
        if problems:
            failed = True
            print(f"{host}:\n" + "\n".join(problems), file=sys.stderr)
        else:
            print(f"{host}: {len(actual)} deployment targets and sources match GNU Stow")
    return int(failed)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, RuntimeError) as error:
        print(error, file=sys.stderr)
        sys.exit(1)
