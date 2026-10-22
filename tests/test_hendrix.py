"""Private token handling and SSH inspection without real credentials or network."""
import importlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "dotfiles/hendrix/.local/share/hendrix"))
import firefox_totp
import saved_totp
import hendrix

TOKEN = {"issuer": "Netiq", "type": "totp", "algorithm": "SHA1",
         "secret": "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ", "period": 30, "digits": 6}


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
