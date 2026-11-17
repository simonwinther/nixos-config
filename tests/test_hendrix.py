"""Private token handling and SSH inspection without real credentials or network."""
import importlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "dotfiles/hendrix"
SHARE = PACKAGE / ".local/share/hendrix"
sys.path.insert(0, str(SHARE))
import firefox_totp
import saved_totp
import hendrix

TOKEN = {"issuer": "Netiq", "type": "totp", "algorithm": "SHA1",
         "secret": "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ", "period": 30, "digits": 6}
# The native launcher's unit tests read the same cases.
CASES = SHARE / "ssh/destinations.txt"


def destination_cases():
    for line in CASES.read_text().splitlines():
        if line.strip() and not line.startswith("#"):
            expected, *args = line.split()
            yield args, None if expected == "-" else expected


class HendrixTests(unittest.TestCase):
    def test_rfc6238_and_private_saved_token(self):
        self.assertEqual(firefox_totp.generate(TOKEN["secret"], timestamp=59, digits=8), "94287082")
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "totp.json"
            path.write_text(json.dumps(TOKEN)); path.chmod(0o600)
            self.assertEqual(saved_totp.read_entry(path), TOKEN)
            path.chmod(0o644)
            with self.assertRaises(PermissionError): saved_totp.read_entry(path)

    def test_wrong_issuer_or_encrypted_tokens_are_rejected(self):
        for changes in [{"issuer": "unrelated"}, {"encrypted": True}, {"type": "hotp"}, {"algorithm": "SHA512"}]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                firefox_totp.validate_entry(TOKEN | changes)

    def test_portable_credentials_use_existing_password_and_private_output(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            password, vpn_input, auth = root / "ku-password", root / "password", root / "vpn-auth.json"
            password.write_text("test-password\n"); auth.write_text(json.dumps({"mode": "totp"}))
            with patch.multiple(hendrix, CONFIG=root, PASSWORD=password, VPN_PASSWORD=vpn_input, VPN_AUTH=auth), \
                 patch.object(saved_totp, "read_entry", return_value=TOKEN), patch("time.time", return_value=1000):
                self.assertEqual(hendrix.prepare_vpn_credentials(), "totp")
            expected = firefox_totp.generate(TOKEN["secret"], timestamp=1000)
            self.assertEqual(vpn_input.read_text(), "test-password&" + expected + "\n")
            self.assertEqual(vpn_input.stat().st_mode & 0o777, 0o600)
            self.assertEqual(auth.stat().st_mode & 0o777, 0o600)
            self.assertEqual(json.loads(auth.read_text())["last_auth_counter"], 33)

    def test_ssh_inspection_and_other_hosts_do_not_start_the_vpn(self):
        for args in [["-G", "hendrix"], ["-O", "check", "hendrix"], ["example.com"], ["other@hendrix"]]:
            self.assertIsNone(hendrix.destination(args))
        self.assertEqual(hendrix.destination(["-p", "22", "hendrix", "true"]), "hendrix")

    def test_python_and_native_launchers_share_destination_cases(self):
        cases = list(destination_cases())
        self.assertGreater(len(cases), 20)
        for args, expected in cases:
            with self.subTest(args=args):
                self.assertEqual(hendrix.destination(args), expected)


class LauncherTests(unittest.TestCase):
    """Run the ssh entry points against a fake OpenSSH that records its call."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="hendrix-ssh-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.log = self.root / "ssh.json"
        fake = self.command(Path("openssh"), "openssh")
        (self.root / "data").mkdir()
        (self.root / "data/hendrix").symlink_to(SHARE, target_is_directory=True)
        # No ku-password exists, so even Hendrix must not probe or start the VPN.
        self.env = {
            "PATH": os.environ["PATH"],
            "HOME": str(self.root / "home"),
            "XDG_CACHE_HOME": str(self.root / "cache"),
            "XDG_CONFIG_HOME": str(self.root / "config"),
            "XDG_DATA_HOME": str(self.root / "data"),
            "DESKTOP_SSH_BIN": str(fake),
            "PYTHONDONTWRITEBYTECODE": "1",
        }
        self.wrapper = [shutil.which("sh") or "/bin/sh", str(PACKAGE / ".local/bin/ssh")]

    def command(self, relative, label):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"#!{sys.executable}\n"
                        "import json, os, sys\n"
                        f"with open({str(self.log)!r}, 'w') as log:\n"
                        f"    json.dump([{label!r}, sys.argv[1:], os.environ.get('SSH_ASKPASS')], log)\n")
        path.chmod(0o755)
        return path

    def run_ssh(self, program, *args):
        self.log.unlink(missing_ok=True)
        result = subprocess.run([*program, *args], env=self.env, capture_output=True,
                                text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(self.log.read_text())

    def test_portable_wrapper_falls_back_to_python(self):
        for args in (["example.com", "true"], ["-G", "hendrix"], ["hendrix", "true"]):
            with self.subTest(args=args):
                self.assertEqual(self.run_ssh(self.wrapper, *args), ["openssh", args, None])

    def test_portable_wrapper_prefers_the_built_launcher(self):
        self.command(Path("cache/hendrix/bin/hendrix-ssh"), "native")
        self.assertEqual(self.run_ssh(self.wrapper, "-p", "22", "hendrix"),
                         ["native", ["-p", "22", "hendrix"], None])

    @unittest.skipUnless(os.environ.get("HENDRIX_SSH_BINARY"), "HENDRIX_SSH_BINARY selects the native launcher")
    def test_native_launcher_runs_plain_ssh_without_python(self):
        launcher = [os.environ["HENDRIX_SSH_BINARY"]]
        self.env["PATH"] = str(self.root / "empty")
        for args in (["example.com", "true"], ["-G", "hendrix"], ["hendrix", "true"]):
            with self.subTest(args=args):
                self.assertEqual(self.run_ssh(launcher, *args), ["openssh", args, None])
