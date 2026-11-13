"""Safeguard the single-main upstream workflow and verified release publication."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class WorkflowPolicyTests(unittest.TestCase):
    def test_public_releases_are_manual_and_verified(self):
        published = (ROOT / ".github/workflows/publish-release.yml").read_text()
        self.assertIn("workflow_dispatch:", published)
        self.assertNotIn("  push:", published)
        self.assertIn("actions: read", published)
        self.assertIn('--commit "$sha"', published)
        self.assertIn("--status success", published)
        self.assertIn("sickshift-ci.yml bootstrap-platforms.yml", published)
        self.assertIn('gh release create "$VERSION"', published)
        self.assertIn('--target "$RELEASE_SHA"', published)

    def test_upstream_has_protected_two_stage_sync(self):
        upstream = (ROOT / ".github/workflows/upstream-watch.yml").read_text()
        self.assertIn("cron: '37 5 * * *'", upstream)
        self.assertIn("persist-credentials: false", upstream)
        self.assertIn("secrets.SICKSHIFT_SYNC_TOKEN", upstream)
        self.assertIn("needs.prepare.outputs.ready == 'true'", upstream)
        self.assertIn("scripts/auto_sync_sickgear.py prepare", upstream)
        self.assertIn("scripts/auto_sync_sickgear.py publish", upstream)

    def test_upstream_documentation_is_current(self):
        text = (ROOT / "docs/UPSTREAM.md").read_text()
        self.assertIn("05:37 UTC", text)
        self.assertIn("single-branch", text)
        self.assertIn("GitHub's own Actions failure emails", text)
        self.assertNotIn("The weekly workflow opens an issue", text)


if __name__ == "__main__":
    unittest.main()
