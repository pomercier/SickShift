"""Read-only database health checks with disposable SQLite files."""
import asyncio
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
from types import SimpleNamespace
import unittest

from sickshift_dashboard.routes import create_router, inspect_sqlite_file


class DashboardHealthTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="sickshift-health-")
        self.db = Path(self.temp.name) / "sickshift.db"

    def tearDown(self):
        self.temp.cleanup()

    def health(self, initialized=True):
        mock_state = SimpleNamespace(
            config=SimpleNamespace(
                db_path=str(self.db),
                webp_enabled=False,
                mount_prefix="/dashboard",
            ),
            initialized=initialized,
            redis=None,
            snapshot_manager=None,
        )
        router = create_router(app_state=mock_state)
        handler = next(route.endpoint for route in router.routes if route.path == "/health")
        return asyncio.run(handler())

    def test_missing_database_is_degraded(self):
        self.assertEqual((False, 0, False), inspect_sqlite_file(self.db))
        result = self.health()
        self.assertEqual("degraded", result["status"])
        self.assertFalse(result["db_exists"])
        self.assertNotIn("db_path", result)
        self.assertFalse(result["db_header_ok"])

    def test_zero_byte_database_is_degraded_even_when_initialized(self):
        self.db.touch()
        self.assertEqual((True, 0, False), inspect_sqlite_file(self.db))
        result = self.health()
        self.assertEqual("degraded", result["status"])
        self.assertTrue(result["db_exists"])
        self.assertEqual(0, result["db_size_bytes"])

    def test_invalid_nonempty_file_is_degraded(self):
        self.db.write_bytes(b"not an sqlite database" * 16)
        result = self.health()
        self.assertEqual("degraded", result["status"])
        self.assertGreater(result["db_size_bytes"], 100)
        self.assertFalse(result["db_header_ok"])

    def test_valid_sqlite_header_and_ready_app_are_healthy(self):
        with closing(sqlite3.connect(self.db)) as conn:
            conn.execute("CREATE TABLE health_probe (id INTEGER PRIMARY KEY)")
            conn.commit()
        result = self.health()
        self.assertEqual("ok", result["status"])
        self.assertTrue(result["db_exists"])
        self.assertTrue(result["db_header_ok"])
        self.assertGreaterEqual(result["db_size_bytes"], 100)

    def test_valid_database_with_uninitialized_app_is_degraded(self):
        with closing(sqlite3.connect(self.db)) as conn:
            conn.execute("CREATE TABLE health_probe (id INTEGER PRIMARY KEY)")
            conn.commit()
        result = self.health(initialized=False)
        self.assertEqual("degraded", result["status"])
        self.assertTrue(result["db_header_ok"])

    def test_diagnostics_omits_db_path_and_clears_preview_cache(self):
        import json
        from unittest.mock import patch
        from sickshift_dashboard import preview_clip

        with closing(sqlite3.connect(self.db)) as conn:
            conn.execute("CREATE TABLE health_probe (id INTEGER PRIMARY KEY)")
            conn.commit()
        mock_state = SimpleNamespace(
            config=SimpleNamespace(
                db_path=str(self.db),
                webp_enabled=False,
                webp_cache_dir="",
                mount_prefix="/dashboard",
            ),
            initialized=True,
            redis=None,
            snapshot_manager=None,
        )
        router = create_router(app_state=mock_state)
        diag_handler = next(r.endpoint for r in router.routes if r.path == "/api/diagnostics")
        clear_handler = next(r.endpoint for r in router.routes if r.path == "/api/cache/previews/clear")

        with tempfile.TemporaryDirectory(prefix="sickshift-pv-cache-") as pv_dir:
            pv_path = Path(pv_dir)
            (pv_path / "clip_v3_test.mp4").write_bytes(b"0" * 2048)
            with patch.object(preview_clip, "CACHE_DIR", pv_path):
                diag_resp = asyncio.run(diag_handler())
                diag_data = json.loads(diag_resp.body)
                self.assertEqual("ok", diag_data["status"])
                self.assertEqual("sickshift.db", diag_data["db_name"])
                self.assertNotIn("db_path", diag_data)
                self.assertEqual(1, diag_data["preview_cache"]["files"])
                self.assertEqual(2048, diag_data["preview_cache"]["size_bytes"])

                clear_resp = asyncio.run(clear_handler())
                clear_data = json.loads(clear_resp.body)
                self.assertEqual("ok", clear_data["status"])
                self.assertEqual(1, clear_data["removed_files"])
                self.assertEqual(2048, clear_data["freed_bytes"])
                self.assertEqual(0, preview_clip.get_preview_cache_stats()["files"])

    def test_audio_selection_respects_sys_lang_and_cache_pruning(self):
        import os
        from unittest.mock import patch
        from sickshift_dashboard import preview_clip
        from sickshift_dashboard.config import Settings

        streams = [
            {"index": 1, "tags": {"language": "eng", "title": "English"}},
            {"index": 2, "tags": {"language": "fre", "title": "VFQ"}},
        ]
        s_fr, reason_fr, _, _ = preview_clip.select_audio_stream(streams, sys_lang="fr")
        self.assertEqual(2, s_fr["index"])
        self.assertEqual("fr_qc", reason_fr)

        s_en, reason_en, _, _ = preview_clip.select_audio_stream(streams, sys_lang="en")
        self.assertEqual(1, s_en["index"])
        self.assertEqual("en_std", reason_en)

        with tempfile.TemporaryDirectory(prefix="sickshift-prune-") as pv_dir:
            import time as _time
            pv_path = Path(pv_dir)
            expired_clip = pv_path / "clip_v3_expired.mp4"
            fresh_clip = pv_path / "clip_v3_fresh.mp4"
            expired_clip.write_bytes(b"a" * 1000)
            fresh_clip.write_bytes(b"b" * 1000)
            now = _time.time()
            # 1h05m old -> must be auto-purged by default 1-hour TTL
            os.utime(expired_clip, (now - 3900, now - 3900))
            # 30m old -> must be kept
            os.utime(fresh_clip, (now - 1800, now - 1800))
            with patch.object(preview_clip, "CACHE_DIR", pv_path):
                stats = preview_clip.get_preview_cache_stats()
                self.assertEqual(3600, stats["max_age_seconds"])
                self.assertEqual(1, stats["files"])
                self.assertFalse(expired_clip.exists())
                self.assertTrue(fresh_clip.exists())

                # LRU size quota eviction still works for fresh clips
                extra_clip = pv_path / "clip_v3_extra.mp4"
                extra_clip.write_bytes(b"c" * 1000)
                removed = preview_clip.prune_preview_cache(max_bytes=1200)
                self.assertGreaterEqual(removed, 1)
                self.assertFalse(fresh_clip.exists())
                self.assertTrue(extra_clip.exists())

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("SICKSHIFT_REDIS_URL", None)
            self.assertFalse(Settings().redis_enabled)


if __name__ == "__main__":
    unittest.main()
