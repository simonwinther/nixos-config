#!/usr/bin/env python3
"""Update the pinned Neovim plugins, Tree-sitter parsers and blink.cmp lockfile.

Usage: python3 pkgs/neovim/update.py [--check]

Plugins follow the branch recorded in lazy-lock.json (or the upstream default
branch after a rename). SEMVER plugins follow their newest release tag, as
their lazy.nvim specs request with `version = "*"`. Parsers follow the
revisions recorded by the pinned nvim-treesitter, whose queries match them.
Each changed source is downloaded once with `nix store prefetch-file` to
record its hash. Files are only written after every query and download has
succeeded, so a failed run leaves the pins untouched.

When a LazyVim update changes NEWS.md, its new size is recorded in lazyvim.json
and the file's path is printed. Home Manager links lazyvim.json read-only, so
LazyVim cannot record that it showed the news and would reopen it at every
start. Stow installs therefore skip the news window and rely on the printout.

--check only reports pending updates and exits 1 if any. It still downloads
the pinned nvim-treesitter source into the Nix store to read its parser
registry, so its parser results are stale while nvim-treesitter is pending.
"""
import argparse
import concurrent.futures
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
PLUGINS = HERE / "plugins.json"
PARSERS = HERE / "parsers.json"
BLINK_LOCK = HERE / "blink-Cargo.lock"
NVIM_CONFIG = HERE.parents[1] / "dotfiles/nvim/.config/nvim"
LAZY_LOCK = NVIM_CONFIG / "lazy-lock.json"
LAZYVIM_JSON = NVIM_CONFIG / "lazyvim.json"
SEMVER = {"lazy.nvim", "LazyVim", "blink.cmp", "cppman.nvim", "nvim-surround", "screenkey.nvim"}
# Newer typst-preview.nvim needs tinymist >= 0.15; stable Nixpkgs ships 0.14.
HOLD = {"typst-preview.nvim"}
# A renamed or private repository must fail instead of waiting for credentials.
GIT_ENV = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
LS_REMOTE_TIMEOUT = 60
PREFETCH_TIMEOUT = 600
prefetched = {}


def run(subject, command, timeout, env=None):
    """Return the command's output, or exit with an error that names the subject."""
    try:
        return subprocess.run(
            command, check=True, capture_output=True, text=True,
            stdin=subprocess.DEVNULL, timeout=timeout, env=env,
        ).stdout
    except subprocess.TimeoutExpired:
        sys.exit(f"{subject}: {command[0]} timed out after {timeout} s")
    except subprocess.CalledProcessError as error:
        sys.exit(f"{subject}: {' '.join(command)} failed:\n{error.stderr.strip()}")


def remote_refs(name, owner, repo):
    output = run(
        name, ["git", "ls-remote", "--symref", f"https://github.com/{owner}/{repo}"],
        LS_REMOTE_TIMEOUT, GIT_ENV,
    )
    refs = {}
    for line in output.splitlines():
        value, ref = line.split("\t")
        refs[ref if not value.startswith("ref: ") else "symref:" + ref] = value.removeprefix("ref: ")
    return refs


def newest_tag(refs):
    tags = {}
    for name in refs:
        match = re.fullmatch(r"refs/tags/(v?(\d+)\.(\d+)\.(\d+))", name)
        if match:
            version = tuple(map(int, match.groups()[1:]))
            tags[version] = refs.get(name + "^{}", refs[name])
    return tags[max(tags)] if tags else None


def prefetch(subject, url):
    """Download an archive once per run and return its hash and unpacked source."""
    if url not in prefetched:
        output = run(
            subject, ["nix", "store", "prefetch-file", "--unpack", "--json", "--hash-type", "sha256", url],
            PREFETCH_TIMEOUT,
        )
        result = json.loads(output)
        prefetched[url] = result["hash"], pathlib.Path(result["storePath"])
    return prefetched[url]


def archive(spec, rev):
    return f"https://github.com/{spec['owner']}/{spec['repo']}/archive/{rev}.tar.gz"


def plugin_target(name, spec, lock_entry):
    refs = remote_refs(name, spec["owner"], spec["repo"])
    branch = lock_entry["branch"]
    if f"refs/heads/{branch}" not in refs:
        branch = refs["symref:HEAD"].removeprefix("refs/heads/")
    tag = newest_tag(refs) if name in SEMVER else None
    return name, branch, tag or refs[f"refs/heads/{branch}"]


def registry(source):
    """Read install_info from nvim-treesitter's lua/nvim-treesitter/parsers.lua."""
    text = (source / "lua/nvim-treesitter/parsers.lua").read_text()
    entries = {}
    for match in re.finditer(r"^  (\w+) = \{\n(.*?)^  \},", text, re.S | re.M):
        info = re.search(r"install_info = \{\n(.*?)^    \},", match.group(2), re.S | re.M)
        if info:
            entries[match.group(1)] = dict(re.findall(r"^      (\w+) = '([^']*)',$", info.group(1), re.M))
    return entries


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2) + "\n")


def write_lazy_lock(lock):
    lines = [
        f'  {json.dumps(name)}: {{ "branch": {json.dumps(entry["branch"])}, "commit": {json.dumps(entry["commit"])} }}'
        for name, entry in sorted(lock.items())
    ]
    LAZY_LOCK.write_text("{\n" + ",\n".join(lines) + "\n}\n")


def record_news(news):
    """Store the NEWS.md size that LazyVim compares with its last shown news."""
    settings = json.loads(LAZYVIM_JSON.read_text())
    size = str(news.stat().st_size)
    if settings.get("news", {}).get("NEWS.md") != size:
        settings.setdefault("news", {})["NEWS.md"] = size
        # LazyVim's own encoder sorts keys and indents by two spaces.
        LAZYVIM_JSON.write_text(json.dumps(settings, indent=2, sort_keys=True) + "\n")
        print(f"LazyVim news changed: {news}")


def update_plugins(plugins, lock, check, pending):
    """Move plugins to their target revisions and return the new unpacked sources."""
    sources = {}
    names = [name for name in plugins if name not in HOLD]
    with concurrent.futures.ThreadPoolExecutor(8) as pool:
        # map() cancels the queued queries when one of them fails.
        targets = pool.map(plugin_target, names, [plugins[n] for n in names], [lock[n] for n in names])
        for name, branch, rev in targets:
            spec = plugins[name]
            if (spec["rev"], lock[name]["branch"]) != (rev, branch):
                pending[name] = f"{name}: {spec['rev'][:12]} -> {rev[:12]} ({branch})"
                if not check:
                    spec["hash"], sources[name] = prefetch(name, archive(spec, rev))
                    spec["rev"] = rev
                    lock[name] = {"branch": branch, "commit": rev}
    return sources


def update_parsers(parsers, treesitter, check, pending):
    """Move parsers to the revisions recorded by the given nvim-treesitter."""
    _, source = prefetch("nvim-treesitter", archive(treesitter, treesitter["rev"]))
    known = registry(source)
    dropped = [spec["name"] for spec in parsers if spec["name"] not in known]
    if dropped:
        sys.exit(f"nvim-treesitter {treesitter['rev'][:12]} no longer lists parsers {', '.join(dropped)}; "
                 "nothing was written")
    for spec in parsers:
        name = spec["name"]
        info = known[name]
        current = (spec["url"], spec["revision"], spec.get("location"))
        wanted = (info["url"], info["revision"], info.get("location"))
        if current != wanted:
            pending[f"parser {name}"] = f"parser {name}: {spec['revision'][:12]} -> {info['revision'][:12]}"
            if not check:
                codeload = info["url"].replace("https://github.com/", "https://codeload.github.com/")
                spec["hash"], _ = prefetch(f"parser {name}", f"{codeload}/tar.gz/{info['revision']}")
                spec["url"], spec["revision"] = info["url"], info["revision"]
                if "location" in info:
                    spec["location"] = info["location"]
                else:
                    spec.pop("location", None)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="report pending updates without writing")
    check = parser.parse_args().check

    plugins = json.loads(PLUGINS.read_text())
    lock = json.loads(LAZY_LOCK.read_text())
    parsers = json.loads(PARSERS.read_text())
    assert set(plugins) == set(lock), "plugins.json and lazy-lock.json list different plugins"
    pending = {}
    sources = update_plugins(plugins, lock, check, pending)
    # Without --check, this registry already belongs to the updated nvim-treesitter.
    update_parsers(parsers, plugins["nvim-treesitter"], check, pending)

    print("\n".join(pending.values()) or "All Neovim pins are current.")
    if check:
        if "nvim-treesitter" in pending:
            print("Parsers were compared with the pinned nvim-treesitter registry, not the pending one.")
        sys.exit(1 if pending else 0)
    write_json(PLUGINS, plugins)
    write_json(PARSERS, parsers)
    write_lazy_lock(lock)
    if "blink.cmp" in sources:
        # The Rust build's cargoLock must match the pinned blink.cmp source.
        shutil.copyfile(sources["blink.cmp"] / "Cargo.lock", BLINK_LOCK)
    if "LazyVim" in sources:
        record_news(sources["LazyVim"] / "NEWS.md")


if __name__ == "__main__":
    main()
