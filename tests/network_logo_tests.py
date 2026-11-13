"""Integration-style tests for network-logo path handling in the Tornado bridge."""
from pathlib import Path
import tempfile
import unittest

from sickshift_dashboard.bridge import resolve_network_logo


class NetworkLogoPathTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="sickshift-logo-test-")
        self.root = Path(self.tmp.name)
        self.logos = self.root / "network"
        self.logos.mkdir()
        self.good = self.logos / "Channel + HD.png"
        self.good.write_bytes(b"dummy PNG bytes")
        self.private = self.root / "private.png"
        self.private.write_bytes(b"private content")

    def tearDown(self):
        self.tmp.cleanup()

    def test_valid_and_encoded_logo_names(self):
        for name in (
            "Channel + HD.png",
            "Channel%20%2B%20HD.png",
            "channel + hd.png",
        ):
            with self.subTest(name=name):
                self.assertEqual(self.good, resolve_network_logo(name, [self.logos]))

    def test_untrusted_paths_never_escape_network_logo_directory(self):
        attacks = (
            "../private.png",
            "%2e%2e%2fprivate.png",
            "..%5cprivate.png",
            "subfolder/another.png",
            "/private.png",
            r"C:\private.png",
            "\x00evil.png",
            "private.txt",
            ".",
            "",
            "%FF.png",
        )
        for name in attacks:
            with self.subTest(name=name):
                self.assertIsNone(resolve_network_logo(name, [self.logos]))

    def test_symlink_to_private_file_is_rejected(self):
        fake = self.logos / "fake.png"
        try:
            fake.symlink_to(self.private)
        except (OSError, NotImplementedError):
            self.skipTest("Symlinks unavailable on this platform")
        self.assertIsNone(resolve_network_logo(fake.name, [self.logos]))

    def test_symlink_inside_approved_directory_is_allowed(self):
        linked = self.logos / "alias.png"
        try:
            linked.symlink_to(self.good)
        except (OSError, NotImplementedError):
            self.skipTest("Symlinks unavailable on this platform")
        self.assertEqual(linked, resolve_network_logo(linked.name, [self.logos]))

    def test_only_approved_logo_directories_are_searched(self):
        self.assertIsNone(resolve_network_logo("private.png", [self.logos]))
        self.assertEqual(self.private, resolve_network_logo("private.png", [self.root]))

    def test_filename_length_is_limited(self):
        self.assertIsNone(resolve_network_logo("A" * 256 + ".png", [self.logos]))


if __name__ == "__main__":
    unittest.main()
