"""Exercise the installed Nix wrapper and staged units without a desktop session."""
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile


binary, renderer = sys.argv[1:]
with tempfile.TemporaryDirectory() as temporary:
    home = Path(temporary)
    root = home / "files"
    root.mkdir()
    database = home / "cache/index.sqlite3"
    environment = {
        "HOME": str(home),
        "PATH": "/no-system-programs",
        "FILE_PICKER_INDEX": str(database),
    }

    def run(*args):
        return subprocess.check_output(
            [binary, "--root", str(root), *args], env=environment
        )

    first = root / "ø quoted ' file\n.pdf"
    first.write_text("fixture")
    hidden = root / ".hidden"
    hidden.write_text("hidden fixture")
    assert json.loads(run("--index-update"))["added"] == 1
    assert run("--cached-list") == os.fsencode(first) + b"\0"
    with sqlite3.connect(database) as connection:
        assert connection.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert connection.execute("SELECT COUNT(*) FROM files").fetchone() == (1,)
    run("--index-remove", str(first))
    assert first.exists() and run("--cached-list") == b""
    run("--index-update")
    second = root / "renamed.pdf"
    first.rename(second)
    result = json.loads(run("--index-update"))
    assert result["added"] == result["removed"] == 1
    assert run("--cached-list") == os.fsencode(second) + b"\0"
    assert json.loads(run("--pdf", "--index-update"))["added"] == 1
    run("--index-clear")
    assert run("--cached-list") == b""
    assert run("--pdf", "--cached-list") == os.fsencode(second) + b"\0"
    assert second.exists() and hidden.exists()

    staging = home / "units"
    subprocess.run([sys.executable, renderer, str(staging)], check=True)
    units = staging / "desktop-services/.config/systemd/user"
    assert not (units / "desktop-pdf-picker.service").exists()
    terminal = (units / "desktop-file-picker.service").read_text()
    assert " --prepare-terminal\n" in terminal and "--warm" not in terminal

print("Packaged SQLite cache and windowless startup units passed")
