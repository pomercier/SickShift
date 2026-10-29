"""Exercise preview encoding with real FFmpeg, including 4K HDR sources."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from sickshift_dashboard import preview_clip


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg required")
class PreviewClipTests(unittest.TestCase):
    def test_browser_compatible_previews_and_cache(self):
        cases = [
            ("sdr", "640x360", "yuv420p", "bt709"),
            ("sdr10", "640x360", "yuv420p10le", "bt709"),
            ("hdr10", "3840x2160", "yuv420p10le", "smpte2084"),
            ("hlg", "3840x2160", "yuv420p10le", "arib-std-b67"),
        ]
        with tempfile.TemporaryDirectory(prefix="sg-preview-test-") as directory:
            root = Path(directory)
            cache = root / "cache"
            cache.mkdir()
            with patch.object(preview_clip, "CACHE_DIR", cache):
                for episode, (name, size, pixel_format, transfer) in enumerate(cases, 1):
                    with self.subTest(source=name):
                        source = root / (name + ".mkv")
                        hdr = transfer != "bt709"
                        subprocess.run([
                            "ffmpeg", "-v", "error", "-f", "lavfi", "-i",
                            f"color=c=orange:size={size}:rate=2:duration=1",
                            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "0",
                            "-threads", "2", "-pix_fmt", pixel_format,
                            "-vf", (
                                f"setparams=color_trc={transfer}:"
                                f"color_primaries={'bt2020' if hdr else 'bt709'}:"
                                f"colorspace={'bt2020nc' if hdr else 'bt709'}"
                            ), str(source),
                        ], check=True, capture_output=True, timeout=30)

                        # An old incompatible cache entry must never bypass conversion.
                        legacy = cache / f"clip_1_1_s01e{episode:02d}_a0_0_1.mp4"
                        legacy.write_bytes(b"legacy high-10 clip")
                        clip = preview_clip.get_or_create_preview_clip(
                            source, 1, 1, 1, episode, clip_len=1,
                        )
                        self.assertIsNotNone(clip)
                        result = subprocess.run([
                            "ffprobe", "-v", "error", "-show_streams", "-of", "json",
                            str(clip["clip_path"]),
                        ], check=True, capture_output=True, text=True, timeout=10)
                        video = json.loads(result.stdout)["streams"][0]
                        self.assertEqual("h264", video["codec_name"])
                        self.assertEqual("yuv420p", video["pix_fmt"])
                        self.assertLessEqual(video["width"], 854)
                        self.assertLessEqual(video["height"], 480)
                        self.assertEqual("bt709", video["color_transfer"])
                        self.assertEqual("no_audio", clip["audio_reason"])

                        # Cache hits must avoid encoding; replacement sources must miss.
                        with patch.object(preview_clip.subprocess, "run", side_effect=AssertionError("cache miss")):
                            cached = preview_clip.get_or_create_preview_clip(source, 1, 1, 1, episode, clip_len=1)
                        self.assertEqual(clip["clip_path"], cached["clip_path"])
                        with source.open("ab") as handle:
                            handle.write(b"\0")
                        self.assertIsNotNone(preview_clip.probe_file(source))
                        with self.assertLogs(preview_clip.logger, level="ERROR"):
                            with patch.object(preview_clip.subprocess, "run", side_effect=RuntimeError("changed source")) as run:
                                self.assertIsNone(preview_clip.get_or_create_preview_clip(source, 1, 1, 1, episode, clip_len=1))
                        run.assert_called_once()


if __name__ == "__main__":
    unittest.main()
