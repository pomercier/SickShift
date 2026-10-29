import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class ReleasePrivacyTests(unittest.TestCase):
    def test_runtime_files_and_credentials_are_blocked(self):
        source = Path(__file__).resolve().parents[1] / 'scripts/check_release.py'
        for name, content in [
            ('settings.db', b'private database'),
            ('.env', b'PASSWORD=private'),
            ('source.py', b'endpoint="https://' + b'account:secret@example.invalid/api"'),
        ]:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / 'scripts').mkdir()
                shutil.copy2(source, root / 'scripts/check_release.py')
                (root / name).write_bytes(content)
                subprocess.run(['git', 'init', '-q'], cwd=root, check=True)
                subprocess.run(['git', 'add', '-f', name], cwd=root, check=True)
                result = subprocess.run([sys.executable, 'scripts/check_release.py'], cwd=root,
                                        capture_output=True, text=True)
                self.assertEqual(1, result.returncode, result.stdout + result.stderr)
                self.assertIn('BLOCKED', result.stdout)


if __name__ == '__main__':
    unittest.main()
