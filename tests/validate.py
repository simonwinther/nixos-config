"""Check portable sources, ownership, dependency locks, and package inventory coverage."""
import ast
import json
from pathlib import Path
import re
import subprocess
import sys

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
dots = root / "dotfiles"
targets = {}
checked = 0
for package in sorted(dots.iterdir()):
    if not package.is_dir():
        continue
    for file in package.rglob("*"):
        assert "omarchy" not in str(file.relative_to(dots)).lower(), f"Legacy asset or path: {file}"
        if not file.is_file() or file.suffix in (".png", ".jpg", ".jpeg", ".webp", ".avif", ".pyc"):
            continue
        rel = file.relative_to(package)
        if rel.parts[0] in ("tests", "README.md", ".stow-local-ignore"):
            continue
        assert str(rel) not in targets, f"Duplicate Stow target {rel}: {targets.get(str(rel))} and {file}"
        targets[str(rel)] = file
        try:
            text = file.read_text()
        except UnicodeDecodeError:
            continue
        if file.suffix != ".md":
            assert not re.search(r"omarchy", text, re.I), f"Legacy runtime reference: {file}"
        if file.suffix == ".py":
            ast.parse(text, filename=str(file))
            checked += 1
        elif file.name in (".bashrc", ".bash_profile", ".bash_logout") or (package.name == "bash" and file.suffix == "" and file.name != "inputrc"):
            subprocess.run(["bash", "-n", file], check=True)
            checked += 1
        elif file.suffix == ".lua":
            subprocess.run(["luac", "-p", file], check=True)
            checked += 1
        elif file.suffix == ".zsh" or file.name in (".zshrc", ".zshenv"):
            subprocess.run(["zsh", "-n", file], check=True)
            checked += 1
        elif text.startswith("#!/") and ("bash" in text.splitlines()[0] or text.splitlines()[0].endswith(" sh")):
            subprocess.run(["bash", "-n", file], check=True)
            checked += 1
mapping = json.loads((root / "docs/inventory/package-map.json").read_text())
reference = [line.split()[0] for line in (root / "docs/inventory/arch-explicit.txt").read_text().splitlines() if line.strip()]
assert sorted(reference) == sorted(row["arch"] for row in mapping), "Package inventory coverage differs"
assert all(row["kind"] in ("package", "custom", "module", "excluded") for row in mapping)
plugins = json.loads((root / "pkgs/neovim/plugins.json").read_text())
assert all(p.get("hash", "").startswith("sha256-") for p in plugins.values()), "Unpinned editor source"
assert "sha256-AAAA" not in (root / "pkgs/hyprspace-companions/default.nix").read_text()
editor_source = root / "pkgs/editor-extensions/sources.json"
if editor_source.exists():
    editor_sources = json.loads(editor_source.read_text())
    assert all(row.get("hash", "").startswith("sha256-") for row in editor_sources.values()), "Unpinned editor extension"
    for editor in ["vscode", "cursor"]:
        recorded = json.loads((root / f"docs/inventory/{editor}-extensions.json").read_text())
        expected = sorted((row["id"], row["version"], row["platform"] or "universal") for row in recorded)
        actual = sorted((row["id"], row["version"], row["platform"]) for row in editor_sources.values() if editor in row["editors"])
        assert expected == actual, f"Missing or changed {editor} extension source"
print(f"Validated {checked} scripts, {len(targets)} unique text targets, {len(mapping)} package decisions, {len(plugins)} locked editor plugins")
