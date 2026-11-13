"""Read-only database health checks with disposable SQLite files."""
import asyncio
from pathlib import Path
import sqlite3
import tempfile
from types import SimpleNamespace
import unittest

from sickshift_dashboard.routes import create_router, inspect_sqlite_file


class DashboardHealthTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="sickshift-health-")
        self.db = Path(self.temp.name) / "sickbeard.db"

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
        with sqlite3.connect(self.db) as conn:
            conn.execute("CREATE TABLE health_probe (id INTEGER PRIMARY KEY)")
        result = self.health()
        self.assertEqual("ok", result["status"])
        self.assertTrue(result["db_exists"])
        self.assertTrue(result["db_header_ok"])
        self.assertGreaterEqual(result["db_size_bytes"], 100)

    def test_valid_database_with_uninitialized_app_is_degraded(self):
        with sqlite3.connect(self.db) as conn:
            conn.execute("CREATE TABLE health_probe (id INTEGER PRIMARY KEY)")
        result = self.health(initialized=False)
        self.assertEqual("degraded", result["status"])
        self.assertTrue(result["db_header_ok"])


if __name__ == "__main__":
    unittest.main()
