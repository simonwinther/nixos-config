#!/usr/bin/env python3
"""Read reference metadata without activation; write a new private parity report.

No credential contents, application databases, or project contents are copied.
Presence of a managed target does not establish complete application coverage.
"""
import argparse
from collections import Counter
import datetime
import hashlib
import json
import os
from pathlib import Path
import socket


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference-home", type=Path, required=True)
    parser.add_argument("--reference-dotfiles", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    home = args.reference_home.resolve()
    source = args.reference_dotfiles.resolve()
    targets = {}
    for package in sorted((repo / "dotfiles").iterdir()):
        if not package.is_dir():
            continue
        for path in package.rglob("*"):
            rel = path.relative_to(package)
            if path.is_dir() or path.name in {"AGENTS.md", ".stow-local-ignore"}:
                continue
            if rel.parts[0] in {"tests", "README.md"} or "__pycache__" in rel.parts:
                continue
            targets.setdefault(str(rel), []).append(str(path.relative_to(repo)))

    expected = {}
    original = json.loads((repo / "docs/inventory/reference.json").read_text())
    for row in original["source_files"]:
        expected[row["source"]] = row
    for row in original.get("post_capture_changes_ported", []):
        expected[row["source"]] = row
    current_path = repo / "docs/inventory/current-reference.json"
    if current_path.exists():
        current = json.loads(current_path.read_text())
        for row in current["sourceFiles"]:
            expected[row["source"]] = row
        for row in current.get("sourceDeletions", []):
            expected.pop(row["source"], None)
    changes = []
    for rel, row in sorted(expected.items()):
        try:
            digest = hashlib.sha256((source / rel).read_bytes()).hexdigest()
            state = "unchanged_since_capture" if digest == row["sha256"] else "changed_since_capture"
        except FileNotFoundError:
            state = "missing_from_reference"
        except OSError:
            state = "unreadable_reference"
        if state != "unchanged_since_capture":
            changes.append({"source": rel, "status": state})

    preferences = {row["source"]: row for row in original.get("additional_preferences", [])}
    if current_path.exists():
        preferences.update({row["source"]: row for row in current.get("additionalPreferences", [])})
    for rel, row in sorted(preferences.items()):
        expected_hash = row.get("sha256", row.get("source_sha256"))
        if not expected_hash:
            continue  # Redacted private state is deliberately not hashed or read here.
        path = home / rel.removeprefix("~/") if rel.startswith("~/") else Path(rel)
        try:
            if hashlib.sha256(path.read_bytes()).hexdigest() != expected_hash:
                changes.append({"source": rel, "status": "preference_changed_since_capture"})
        except OSError:
            changes.append({"source": rel, "status": "unavailable_reference_preference"})
    if current_path.exists():
        for capture in current.get("vendorSourceCaptures", []):
            base = home / capture["sourceBase"].removeprefix("~/")
            for row in capture["files"]:
                try:
                    if hashlib.sha256((base / row["source"]).read_bytes()).hexdigest() != row["sha256"]:
                        changes.append({"source": f'{capture["sourceBase"]}/{row["source"]}', "status": "vendor_source_changed_since_capture"})
                except OSError:
                    changes.append({"source": f'{capture["sourceBase"]}/{row["source"]}', "status": "unavailable_vendor_reference"})

    # Also notice newly added files: comparing captured hashes alone would miss
    # an entirely new plugin, configuration file, or Rust source module.
    policy = json.loads((repo / "docs/inventory/reference-path-decisions.json").read_text())["rules"]
    known = set(expected)
    if current_path.exists():
        for row in current.get("sourceDeletions", []):
            known.add(row["source"])
            if (source / row["source"]).exists():
                changes.append({"source": row["source"], "status": "previously_deleted_source_reappeared"})
    other_reference_paths = []
    source_skip = {".git", "target", "node_modules", ".venv", "__pycache__", "build", ".cache"}
    for directory, folders, files in os.walk(source, followlinks=False):
        folders[:] = sorted(name for name in folders if name not in source_skip)
        for name in sorted(files):
            rel = str((Path(directory) / name).relative_to(source))
            if rel in known:
                continue
            match = next((rule for rule in policy if rel in rule.get("sources", [])
                          or any(rel.startswith(prefix) for prefix in rule.get("prefixes", []))), None)
            other_reference_paths.append({"source": rel, "disposition": match["disposition"] if match else "requires_review"})

    configs = []
    for path in sorted((home / ".config").iterdir()):
        prefix = f".config/{path.name}"
        managed = sorted(target for target in targets if target == prefix or target.startswith(prefix + "/"))
        status = "partial_sources_present" if managed else "review_configuration_or_private_state"
        if path.name in {"omarchy", "omarchy.ttf", "yay", "VirtualBox"}:
            status = "excluded_distribution_or_unused_infrastructure"
        configs.append({"path": prefix, "status": status, "managedTargets": managed})

    scripts = []
    for path in sorted((home / ".local/bin").iterdir()):
        if path.is_dir():
            continue
        target = f".local/bin/{path.name}"
        scripts.append({"path": target, "hasPortableSource": target in targets})

    home_dotfiles = []
    for path in sorted(home.iterdir()):
        if not path.name.startswith(".") or (path.is_dir() and not path.is_symlink()):
            continue
        home_dotfiles.append({
            "path": path.name,
            "managedSources": targets.get(path.name, []),
            "disposition": "managed_configuration" if path.name in targets else "private_state_history_or_runtime_metadata_for_selective_restoration",
        })

    manifests = []
    skipped = {".git", "target", "node_modules", ".venv", "venv", ".cache", ".direnv", "__pycache__", "build", "dist", ".mypy_cache", ".pytest_cache"}
    names = {"Cargo.toml", "Cargo.lock", "rust-toolchain", "rust-toolchain.toml", "pyproject.toml", "requirements.txt", "Pipfile", "poetry.lock", "uv.lock", "flake.nix", "shell.nix"}
    roots = [source, *(home / name for name in ["Projects", "dev", "Work", "Documents"])]
    for base in roots:
        if not base.is_dir():
            continue
        for directory, folders, files in os.walk(base, followlinks=False):
            folders[:] = sorted(name for name in folders if name not in skipped and not (Path(directory) / name).is_symlink())
            for name in sorted(set(files) & names):
                manifests.append(str((Path(directory) / name).relative_to(home)))

    private_paths = [".ssh", ".gnupg", ".password-store", ".aws", ".docker", ".mozilla", ".git-credentials", ".netrc", ".owm-key", ".codex", ".codex-accounts", ".claude", ".pi", ".gemini", ".local/share/keyrings", ".config/1Password", ".config/chromium", ".config/google-chrome", ".config/hendrix", ".config/dictate/secrets.env", ".config/zsh/secrets.zsh", ".config/fono/secrets.toml", ".config/kaggle", ".kaggle", ".var/app"]
    cargo_packages = []
    cargo_state = home / ".cargo/.crates2.json"
    if cargo_state.exists():
        for key in json.loads(cargo_state.read_text()).get("installs", {}):
            words = key.split()
            cargo_packages.append({"name": words[0], "version": words[1] if len(words) > 1 else "unknown"})

    command_map_path = repo / "docs/inventory/user-tools.json"
    decisions = {row["referenceCommand"]: row for row in json.loads(command_map_path.read_text())["commands"]} if command_map_path.exists() else {}
    report = {
        "recordedAtUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "referenceHost": socket.gethostname(),
        "scope": "Metadata and hashes of previously imported source only. No credential contents or project contents copied. Project search is limited to the listed roots; a managed target is partial evidence, not an acceptance result.",
        "projectSearchRoots": [str(path.relative_to(home)) for path in roots],
        "configuration": configs,
        "homeCommands": scripts,
        "homeDotfiles": home_dotfiles,
        "sourceChangesSinceCapture": changes,
        "otherReferencePaths": other_reference_paths,
        "unreviewedReferencePaths": [row["source"] for row in other_reference_paths if row["disposition"] == "requires_review"],
        "projectManifests": manifests,
        "cargoInstalledPackages": cargo_packages,
        "privateState": [{"path": path, "present": (home / path).exists(), "disposition": "encrypted_transfer_or_fresh_authentication_not_nix_source"} for path in private_paths],
        "summary": {
            "configurationTopLevels": len(configs),
            "configurationStatus": dict(Counter(row["status"] for row in configs)),
            "homeCommands": len(scripts),
            "homeDotfiles": len(home_dotfiles),
            "homeCommandsWithoutPortableSource": sum(not row["hasPortableSource"] for row in scripts),
            "unresolvedHomeCommands": [Path(row["path"]).name for row in scripts if Path(row["path"]).name not in decisions or decisions[Path(row["path"]).name]["kind"] == "needs_review"],
            "sourceChangesSinceCapture": len(changes),
            "unreviewedReferencePaths": sum(row["disposition"] == "requires_review" for row in other_reference_paths),
            "projectManifests": len(manifests),
            "cargoInstalledPackages": len(cargo_packages),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")
    print(json.dumps(report["summary"]))
    print(f"Private metadata report: {args.output}")


if __name__ == "__main__":
    main()
