"""Tests for hot online SQLite backups with rolling retention."""
from contextlib import closing
import os
from pathlib import Path
import sqlite3
import tempfile
import time
import unittest

from sickshift_dashboard.db_backup import backup_database


class DbBackupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="sickshift-backup-test-")
        self.root = Path(self.temp.name)
        self.db_path = self.root / "sickshift.db"
        self.backup_dir = self.root / "backups"

    def tearDown(self):
        self.temp.cleanup()

    def _create_sample_db(self):
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.execute("CREATE TABLE shows (id INTEGER PRIMARY KEY, name TEXT)")
            conn.execute("INSERT INTO shows (id, name) VALUES (1, 'South Park'), (2, 'Les Simpson')")
            conn.commit()

    def test_hot_backup_creates_valid_copy_and_skips_same_day_duplicate(self):
        self._create_sample_db()

        res1 = backup_database(self.db_path, backup_dir=self.backup_dir, keep_days=7)
        self.assertEqual("ok", res1["status"])
        self.assertTrue(res1["created"])
        backup_file = self.backup_dir / res1["backup_file"]
        self.assertTrue(backup_file.is_file())

        with closing(sqlite3.connect(backup_file)) as conn:
            rows = conn.execute("SELECT id, name FROM shows ORDER BY id").fetchall()
        self.assertEqual([(1, "South Park"), (2, "Les Simpson")], rows)

        # Second run on same day skips duplicate backup
        res2 = backup_database(self.db_path, backup_dir=self.backup_dir, keep_days=7)
        self.assertEqual("skipped", res2["status"])
        self.assertFalse(res2["created"])

    def test_rotation_prunes_backups_older_than_keep_days(self):
        self._create_sample_db()
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        old_backup = self.backup_dir / "sickshift-20200101.db"
        recent_backup = self.backup_dir / "sickshift-20990101.db"
        old_backup.write_bytes(b"old")
        recent_backup.write_bytes(b"recent")

        now = time.time()
        os.utime(old_backup, (now - 9 * 86400, now - 9 * 86400))
        os.utime(recent_backup, (now - 2 * 86400, now - 2 * 86400))

        res = backup_database(self.db_path, backup_dir=self.backup_dir, keep_days=7)
        self.assertEqual("ok", res["status"])
        self.assertEqual(1, res["pruned"])
        self.assertFalse(old_backup.exists())
        self.assertTrue(recent_backup.exists())

    def test_missing_or_invalid_db_is_skipped_safely(self):
        res = backup_database(self.db_path, backup_dir=self.backup_dir)
        self.assertEqual("skipped", res["status"])
        self.assertEqual("invalid_or_missing_db", res["reason"])


if __name__ == "__main__":
    unittest.main()
