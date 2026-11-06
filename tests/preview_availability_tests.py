import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from sickshift_dashboard import preview_clip


class PreviewAvailabilityTests(unittest.TestCase):
    def setUp(self):
        self.previous = preview_clip._TOOLS_STATUS
        preview_clip._TOOLS_STATUS = None

    def tearDown(self):
        preview_clip._TOOLS_STATUS = self.previous

    def test_missing_tool_never_probes_or_extracts_media(self):
        with patch.object(preview_clip.shutil, 'which', side_effect=['ffmpeg', None]), patch.object(preview_clip, 'probe_file') as probe:
            self.assertIsNone(preview_clip.get_or_create_preview_clip(Path('not-read.mkv'), 1, 1, 1, 1))
        probe.assert_not_called()

    def test_unusable_executable_disables_previews(self):
        with tempfile.NamedTemporaryFile() as executable:
            for failure in [PermissionError('blocked'), subprocess.TimeoutExpired('ffmpeg', 3)]:
                with self.subTest(failure=type(failure).__name__):
                    preview_clip._TOOLS_STATUS = None
                    with patch.object(preview_clip.shutil, 'which', return_value=executable.name), patch.object(preview_clip.subprocess, 'run', side_effect=failure):
                        self.assertFalse(preview_clip.preview_tools_available())

    def test_working_tools_are_checked_once_then_cached(self):
        with tempfile.NamedTemporaryFile() as executable:
            with patch.object(preview_clip.shutil, 'which', return_value=executable.name), patch.object(preview_clip.subprocess, 'run', return_value=Mock(returncode=0)) as run:
                self.assertTrue(preview_clip.preview_tools_available())
                self.assertTrue(preview_clip.preview_tools_available())
                self.assertEqual(2, run.call_count)

    def test_failed_version_check_disables_previews(self):
        with tempfile.NamedTemporaryFile() as executable:
            with patch.object(preview_clip.shutil, 'which', return_value=executable.name), patch.object(preview_clip.subprocess, 'run', return_value=Mock(returncode=1)):
                self.assertFalse(preview_clip.preview_tools_available())


if __name__ == '__main__':
    unittest.main()
