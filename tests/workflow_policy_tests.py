"""Safeguard the single-main upstream workflow, arbitration, watchdog, Docker, and verified releases."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class WorkflowPolicyTests(unittest.TestCase):
    def test_public_releases_are_verified_with_docker_before_release(self):
        published = (ROOT / ".github/workflows/publish-release.yml").read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", published)
        self.assertNotIn("\n  push:", published)
        self.assertIn("actions: read", published)
        self.assertIn('--commit "$sha"', published)
        self.assertIn("--status success", published)
        self.assertIn("sickshift-ci.yml bootstrap-platforms.yml", published)
        self.assertIn("validate-and-push-docker", published)
        self.assertIn("needs: [prepare-release, validate-and-push-docker]", published)
        self.assertIn('gh release create "$VERSION"', published)
        self.assertIn('--target "$RELEASE_SHA"', published)
        self.assertIn("docker buildx imagetools create", published)

    def test_upstream_has_protected_three_stage_sync(self):
        upstream = (ROOT / ".github/workflows/upstream-watch.yml").read_text(encoding="utf-8")
        self.assertIn("cron: '*/15 * * * *'", upstream)
        self.assertIn("persist-credentials: false", upstream)
        self.assertIn("secrets.SICKSHIFT_SYNC_TOKEN", upstream)
        self.assertIn("needs.detect.outputs.needs_sync == 'true'", upstream)
        self.assertIn("needs.prepare.outputs.ready == 'true'", upstream)
        self.assertIn("scripts/auto_sync_sickgear.py detect", upstream)
        self.assertIn("scripts/auto_sync_sickgear.py prepare", upstream)
        self.assertIn("scripts/auto_sync_sickgear.py publish", upstream)

    def test_arbitration_and_watchdog_workflows_exist_and_are_protected(self):
        arb = (ROOT / ".github/workflows/arbitration-handler.yml").read_text(encoding="utf-8")
        self.assertIn("issue_comment:", arb)
        self.assertIn("persist-credentials: false", arb)
        self.assertIn("scripts/auto_sync_sickgear.py handle-comment", arb)
        self.assertIn("scripts/auto_sync_sickgear.py prepare-arbitration", arb)
        self.assertIn("scripts/auto_sync_sickgear.py publish", arb)

        wd = (ROOT / ".github/workflows/sync-watchdog.yml").read_text(encoding="utf-8")
        self.assertIn("cron: '17 */2 * * *'", wd)
        self.assertIn("scripts/watchdog.py", wd)

    def test_docker_workflow_validates_container_before_promoting_latest(self):
        docker_wf = (ROOT / ".github/workflows/docker-publish.yml").read_text(encoding="utf-8")
        self.assertIn("ghcr.io/pomercier/sickshift", docker_wf)
        self.assertIn("linux/amd64,linux/arm64", docker_wf)
        self.assertIn("needs: validate", docker_wf)
        self.assertIn("/dashboard/health", docker_wf)
        self.assertIn("sickbeard.db", docker_wf)
        self.assertIn("docker pull", docker_wf)

    def test_upstream_documentation_is_current(self):
        text = (ROOT / "docs/UPSTREAM.md").read_text(encoding="utf-8")
        self.assertIn("15 minutes", text)
        self.assertIn("single-branch", text)
        self.assertIn("GitHub's own Actions failure emails", text)
        self.assertIn("/approve", text)
        self.assertIn("sync-watchdog.yml", text)


if __name__ == "__main__":
    unittest.main()
