#!/usr/bin/env python3
"""Build and try desktop-bar without building or activating a Nix configuration."""

import argparse
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import time


ROOT = Path(__file__).resolve().parent.parent
CRATE = ROOT / "dotfiles/desktop-bar/.local/share/desktop-bar"
UNIT = "desktop-bar.service"


def run(*arguments, **options):
    return subprocess.run(list(map(str, arguments)), check=True, **options)


def service_property(name):
    return run("systemctl", "--user", "show", UNIT, "--property=" + name,
               "--value", capture_output=True, text=True).stdout.strip()


def reload_service():
    run("systemctl", "--user", "daemon-reload")
    run("systemctl", "--user", "try-restart", UNIT)


def preserve_clipboard(runtime):
    """Move a clipboard owner out of the service before restarting it."""
    group = service_property("ControlGroup")
    if not group:
        return
    processes = Path("/sys/fs/cgroup" + group, "cgroup.procs").read_text().split()
    owners = []
    for process in processes:
        try:
            if Path("/proc", process, "comm").read_text().strip() == "wl-copy":
                owners.append(process)
        except FileNotFoundError:
            pass
    if not owners:
        return
    types = run("wl-paste", "--list-types", capture_output=True, text=True).stdout.splitlines()
    preferred = ("image/png", "image/jpeg", "image/webp", "text/uri-list",
                 "text/plain;charset=utf-8", "text/plain")
    mime = next((value for value in preferred if value in types), types[0] if types else None)
    if mime is None:
        return
    payload = run("wl-paste", "--no-newline", "--type", mime,
                  capture_output=True, timeout=10).stdout
    with tempfile.NamedTemporaryFile(prefix="bar-dev-clipboard-", dir=runtime) as source:
        source.write(payload)
        source.flush()
        run("systemd-run", "--user", "--collect", "--quiet",
            "--property=Type=exec", "--property=StandardInput=file:" + source.name,
            "--setenv=WAYLAND_DISPLAY=" + os.environ["WAYLAND_DISPLAY"],
            "--setenv=XDG_RUNTIME_DIR=" + str(runtime),
            shutil.which("wl-copy"), "--foreground", "--type", mime)
        for _ in range(50):
            copied = run("wl-paste", "--no-newline", "--type", mime,
                         capture_output=True, timeout=10).stdout
            if copied == payload:
                return
            time.sleep(0.02)
    raise RuntimeError("Clipboard ownership could not be preserved")


def atomic_write(path, content, mode=0o600):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as temporary:
        temporary.write(content)
        temporary.flush()
        os.chmod(temporary.name, mode)
        Path(temporary.name).replace(path)


def apply(binary, executable, runtime, dropin):
    if service_property("ActiveState") != "active":
        raise RuntimeError("The bar is stopped; use preview or start the normal bar first")
    preserve_clipboard(runtime)
    # Systemd expands specifiers and command variables independently of quoting.
    command = str(binary).replace("%", "%%").replace("$", "$$")
    setting = "DESKTOP_DESKTOP_BAR_NATIVE_BIN=" + str(binary).replace("%", "%%")
    content = ("[Service]\nExecStart=\nExecStart=" + json.dumps(command) +
               "\nEnvironment=" + json.dumps(setting) + "\n")
    try:
        atomic_write(dropin, content)
        reload_service()
        for _ in range(100):
            pid = service_property("MainPID")
            try:
                if Path("/proc", pid, "exe").resolve() == executable.resolve():
                    print("Development bar is running. Use restore to return to the Nix package.")
                    return
            except FileNotFoundError:
                pass
            time.sleep(0.05)
        raise RuntimeError("The development bar did not start")
    except BaseException:
        dropin.unlink(missing_ok=True)
        reload_service()
        raise


def nix_shell(command):
    def quoted(value):
        return json.dumps(str(value)).replace("${", "\\${")

    expression = """let
      inputs = (builtins.getFlake %s).inputs;
      pkgs = import inputs.nixpkgs { system = builtins.currentSystem; config.allowUnfree = true; };
      unstable = import inputs.unstable { system = builtins.currentSystem; config.allowUnfree = true; };
      packages = import (builtins.toPath %s) { inherit inputs pkgs unstable; };
      libraries = packages.desktop-bar.buildInputs;
    in pkgs.mkShell {
      nativeBuildInputs = [ unstable.rustc unstable.cargo unstable.rustfmt pkgs.pkg-config pkgs.python3 pkgs.findutils pkgs.fontconfig ];
      buildInputs = libraries;
      LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath libraries;
      DESKTOP_BAR_FONT_ROOT = "${pkgs.nerd-fonts.jetbrains-mono}/share/fonts";
      DESKTOP_BAR_ICON_ROOT = "${pkgs.nerd-fonts.symbols-only}/share/fonts";
      DESKTOP_BAR_FONTCONFIG_BIN = "${pkgs.fontconfig}/bin";
    }""" % (quoted("git+file://" + str(ROOT) + "?submodules=1"), quoted(ROOT / "pkgs"))
    os.execvp("nix", ["nix", "develop", "--impure", "--expr", expression,
                      "--command", "python3", str(Path(__file__).resolve()),
                      "--in-shell", command])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", nargs="?", default="build",
                        choices=("build", "check", "test", "preview", "apply", "restore"))
    parser.add_argument("--in-shell", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    os.umask(0o077)
    runtime = Path(os.environ.get("XDG_RUNTIME_DIR", "/run/user/" + str(os.getuid())))
    dropin = runtime / "systemd/user/desktop-bar.service.d/zz-development.conf"
    if args.command == "restore":
        if dropin.exists():
            preserve_clipboard(runtime)
            dropin.unlink()
            reload_service()
            print("Restored the Nix bar service.")
        else:
            print("No development override is active.")
        return
    if not args.in_shell:
        nix_shell(args.command)

    cache = Path(os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache"))) / "desktop-bar/development"
    cache.mkdir(parents=True, exist_ok=True)
    environment = dict(os.environ)
    environment.update({
        "CARGO_TARGET_DIR": str(cache / "target"),
        "CARGO_PROFILE_RELEASE_LTO": "false",
        "CARGO_PROFILE_RELEASE_CODEGEN_UNITS": "16",
        "CARGO_PROFILE_RELEASE_INCREMENTAL": "true",
        "CARGO_BUILD_JOBS": os.environ.get("CARGO_BUILD_JOBS", str(min(4, os.cpu_count() or 1))),
    })
    for variable, root, filename in (
        ("DESKTOP_BAR_FONT", "DESKTOP_BAR_FONT_ROOT", "JetBrainsMonoNerdFont-SemiBold.ttf"),
        ("DESKTOP_BAR_ICON_FONT", "DESKTOP_BAR_ICON_ROOT", "SymbolsNerdFontMono-Regular.ttf"),
    ):
        environment[variable] = str(next(Path(environment[root]).rglob(filename)))

    started = time.monotonic()
    arguments = ["cargo", "build", "--release", "--bin", "desktop-bar"]
    if args.command == "check":
        arguments = ["cargo", "check", "--package", "desktop-bar", "--all-targets"]
    elif args.command == "test":
        arguments = ["cargo", "test", "--package", "desktop-bar", "--bin", "desktop-bar"]
    run(*arguments, "--locked", cwd=CRATE, env=environment)
    print(f"{args.command.capitalize()} completed in {time.monotonic() - started:.2f}s", flush=True)
    if args.command in ("check", "test"):
        return
    binary = cache / "target/release/desktop-bar"
    wrapper = cache / "bin/desktop-bar"
    exports = "\n".join("export " + key + "=" + shlex.quote(environment[key])
                        for key in ("DESKTOP_BAR_FONT", "DESKTOP_BAR_ICON_FONT", "LD_LIBRARY_PATH"))
    atomic_write(wrapper, "#!/bin/sh\n" + exports + "\nexport PATH=" +
                 shlex.quote(environment["DESKTOP_BAR_FONTCONFIG_BIN"]) +
                 ':"$PATH"\nexec ' + shlex.quote(str(binary)) + ' "$@"\n', 0o700)
    if args.command == "preview":
        run(wrapper, "--preview")
    elif args.command == "apply":
        apply(wrapper, binary, runtime, dropin)
    else:
        print("Development binary:", wrapper)


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print("desktop-bar-dev:", error, file=sys.stderr)
        sys.exit(1)
