#!/usr/bin/env python3
"""Read-only hardware and service inventory. Output can contain serials and local paths."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output", type=Path, help="Create a new private JSON file; existing files are never replaced")
args = parser.parse_args()

def read(command):
    if not shutil.which(command[0]):
        return {"unavailable": command[0]}
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as error:
        return {"error": str(error)}
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError:
        output = result.stdout.strip()
    return {"exitCode": result.returncode, "output": output, "error": result.stderr.strip()}

def read_file(path):
    try:
        return path.read_text().strip()
    except OSError as error:
        return {"unavailable": str(path), "error": str(error)}

def drm_connectors():
    connectors = {}
    for status in sorted(Path("/sys/class/drm").glob("*/status")):
        connector = status.parent
        details = {name: read_file(connector / name) for name in ("status", "enabled", "modes")}
        try:
            edid = (connector / "edid").read_bytes()
            if edid:
                details["edidSha256"] = hashlib.sha256(edid).hexdigest()
                details["edidHex"] = edid.hex()
        except OSError as error:
            details["edidError"] = str(error)
        connectors[connector.name] = details
    return connectors

report = {
    "recordedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "hostname": os.uname().nodename,
    "platform": {name: read_file(Path("/sys/class/dmi/id") / name) for name in (
        "sys_vendor", "product_name", "product_version", "board_name", "bios_version", "bios_date"
    )},
    "memory": read_file(Path("/proc/meminfo")),
    "drmConnectors": drm_connectors(),
    "commands": {name: read(command) for name, command in {
        "cpu": ["lscpu", "--json"],
        "devices": ["lspci", "-nnk"],
        "usb": ["lsusb"],
        "disks": ["lsblk", "--json", "--bytes", "--output", "NAME,PATH,TYPE,SIZE,FSTYPE,UUID,PARTUUID,MOUNTPOINTS,MODEL,SERIAL,TRAN,ROTA"],
        "filesystems": ["findmnt", "--json", "--real"],
        "diskIds": ["find", "/dev/disk/by-id", "-maxdepth", "1", "-type", "l", "-printf", "%f -> %l\n"],
        "bootEntries": ["efibootmgr", "-v"],
        "secureBoot": ["bootctl", "status", "--no-pager"],
        "monitors": ["hyprctl", "-j", "monitors", "all"],
        "services": ["systemctl", "list-unit-files", "--state=enabled", "--no-pager"],
        "userServices": ["systemctl", "--user", "list-unit-files", "--state=enabled", "--no-pager"],
        "networkLinks": ["ip", "-json", "link"],
    }.items()},
    "uefi": Path("/sys/firmware/efi").exists(),
}
text = json.dumps(report, indent=2) + "\n"
if args.output:
    args.output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        stream.write(text)
    print(args.output)
else:
    print(text, end="")
