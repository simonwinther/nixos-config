#!/usr/bin/env python3
"""Validate the selected physical disk against an inventory. Never partitions or mounts."""
import argparse
import json
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--disk", required=True, help="Exact persistent /dev/disk/by-id identifier")
parser.add_argument("--serial", required=True, help="Reviewed physical disk serial from inventory")
parser.add_argument("--bytes", required=True, type=int, help="Reviewed physical disk size in bytes")
args = parser.parse_args()
disk = Path(args.disk)
if not args.disk.startswith("/dev/disk/by-id/") or "-part" in disk.name or not disk.is_symlink():
    parser.error("Select a whole physical disk using its persistent by-id symlink")
result = subprocess.run(["lsblk", "--json", "--bytes", "--nodeps", "--output", "PATH,TYPE,SIZE,SERIAL", str(disk.resolve())], check=True, text=True, capture_output=True)
devices = json.loads(result.stdout)["blockdevices"]
if len(devices) != 1 or devices[0]["type"] != "disk":
    parser.error("Selected target is not one physical disk")
actual = devices[0]
if str(actual.get("serial", "")).strip() != args.serial.strip() or actual["size"] != args.bytes:
    parser.error("Disk serial or size differs from the reviewed inventory")
print(json.dumps({"verified": True, "persistentPath": str(disk), **actual}, indent=2))
print("Read-only verification passed. This does not verify backups or authorize formatting.")
