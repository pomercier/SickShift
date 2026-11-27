"""Comprehensive fault-injection and unit tests for SickShift sync, arbitration, and watchdog.

All Git tests execute inside isolated disposable tempfile directories and never mutate the live repository.
"""
from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile
import unittest

from scripts.arbitration import (
    ARBITRATION_LABEL,
    ARBITRATION_TITLE,
    authorize_actor,
    extract_arbitration_metadata,
    parse_arbitration_command,
    render_arbitration_issue_body,
    render_explain_comment,
)
from scripts.auto_sync_sickgear import compute_next_semver
from scripts.conflict_resolver import (
    apply_arbitration_option,
    normalize_code_identifiers,
    normalize_merged_files,
    resolve_deterministic_conflicts,
    shift_preserve_urls,
)
from scripts.sync_state import (
    SyncState,
    SyncStateMachine,
    classify_release_impact,
    retry_with_backoff,
    verify_critical_protections,
)
from scripts.watchdog import REQUIRED_WORKFLOWS, evaluate_watchdog_state


def _git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, check=check)


def _init_repo(path: Path) -> None:
    _git(path, "init", "-q", "-b", "main")
    _git(path, "config", "user.name", "Test Bot")
    _git(path, "config", "user.email", "test@example.invalid")


class SyncPipelineFaultInjectionTests(unittest.TestCase):
    # --- State machine & retry resilience ---
    def test_state_machine_valid_and_illegal_transitions(self):
        sm = SyncStateMachine()
        self.assertEqual(SyncState.UP_TO_DATE, sm.state)
        sm.transition(SyncState.UPSTREAM_CHANGED, "new commit")
        sm.transition(SyncState.SYNC_IN_PROGRESS, "merge")
        sm.transition(SyncState.AUTO_RESOLUTION_IN_PROGRESS, "diff3")
        sm.transition(SyncState.VALIDATION_IN_PROGRESS, "tests")
        sm.transition(SyncState.PUBLICATION_IN_PROGRESS, "push")
        sm.transition(SyncState.RELEASE_PENDING, "app changed")
        sm.transition(SyncState.DOCKER_BUILD_IN_PROGRESS, "build")
        sm.transition(SyncState.DOCKER_VALIDATION_IN_PROGRESS, "boot container")
        sm.transition(SyncState.PUBLICATION_IN_PROGRESS, "promote latest")
        sm.transition(SyncState.FULLY_VERIFIED, "verified")
        self.assertEqual(SyncState.FULLY_VERIFIED, sm.state)
        with self.assertRaises(ValueError):
            sm.transition(SyncState.DOCKER_BUILD_IN_PROGRESS, "illegal jump")

    def test_retry_with_backoff_recovers_from_transient_network_errors(self):
        calls = {"n": 0}
        sleeps: list[float] = []

        def flaky():
            calls["n"] += 1
            if calls["n"] < 3:
                raise RuntimeError("transient network timeout")
            return "recovered"

        res = retry_with_backoff(flaky, attempts=3, base_delay=1.0, sleep_fn=sleeps.append)
        self.assertEqual("recovered", res)
        self.assertEqual([1.0, 2.0], sleeps)

        with self.assertRaises(RuntimeError):
            retry_with_backoff(lambda: (_ for _ in ()).throw(RuntimeError("auth failed")), attempts=2, sleep_fn=lambda _: None)

    # --- Deterministic diff3 merge & large backlog fault injection ---
    def test_no_upstream_change_and_single_compatible_commit_and_300_commit_backlog(self):
        with tempfile.TemporaryDirectory(prefix="sickshift-sync-sim-") as tmp:
            root = Path(tmp)
            upstream = root / "upstream"
            fork = root / "fork"
            upstream.mkdir()
            fork.mkdir()
            _init_repo(upstream)

            # Base commit on upstream (multiple files & lines so Git detects rename identically to SickShift)
            body = "A = 1\nB = 2\nC = 3\nD = 4\nE = 5\n"
            (upstream / "sickgear").mkdir()
            (upstream / "sickgear/app.py").write_text(f"import sickgear\n{body}VERSION = 1\n", encoding="utf-8")
            (upstream / "sickgear/util1.py").write_text("def a(): return 1\n", encoding="utf-8")
            (upstream / "sickgear/util2.py").write_text("def b(): return 2\n", encoding="utf-8")
            _git(upstream, "add", "-A")
            _git(upstream, "commit", "-q", "-m", "base")

            # Clone into fork and rename sickgear -> sickshift
            _git(root, "clone", "-q", str(upstream), str(fork))
            _git(fork, "config", "user.name", "Test Bot")
            _git(fork, "config", "user.email", "test@example.invalid")
            _git(fork, "mv", "sickgear", "sickshift")
            (fork / "sickshift/app.py").write_text(f"import sickshift\n{body}VERSION = 1\n", encoding="utf-8")
            _git(fork, "add", "-A")
            _git(fork, "commit", "-q", "-m", "fork rename")

            # Scenario 1: No upstream change -> behind == 0
            _git(fork, "fetch", "-q", "origin", "main")
            behind = int(_git(fork, "rev-list", "--count", "HEAD..origin/main").stdout.strip())
            self.assertEqual(0, behind)

            # Scenario 2: Single compatible upstream commit importing sickgear (clean auto-merge!)
            (upstream / "sickgear/new_mod.py").write_text(
                "import sickgear\nURL = 'https://github.com/SickGear/SickGear'\n", encoding="utf-8"
            )
            _git(upstream, "add", "-A")
            _git(upstream, "commit", "-q", "-m", "add new_mod")

            _git(fork, "fetch", "-q", "origin", "main")
            merged = _git(fork, "-c", "merge.conflictStyle=diff3", "merge", "--no-commit", "--no-ff", "origin/main", check=False)
            if merged.returncode:
                resolve_deterministic_conflicts(fork)
            staged = _git(fork, "diff", "--cached", "--name-only", "--diff-filter=AM").stdout.splitlines()
            normalize_merged_files(fork, staged)
            _git(fork, "commit", "-q", "-m", "merge single")
            self.assertEqual(0, int(_git(fork, "rev-list", "--count", "HEAD..origin/main").stdout.strip()))
            new_mod = (fork / "sickshift/new_mod.py").read_text(encoding="utf-8")
            self.assertIn("import sickshift", new_mod)
            self.assertIn("https://github.com/SickGear/SickGear", new_mod)

            # Scenario 3: 250-commit upstream backlog with pure rename conflict
            for i in range(250):
                imp_line = "import sickgear, os" if i == 249 else "import sickgear"
                (upstream / "sickgear/app.py").write_text(f"{imp_line}\n{body}VERSION = {i + 2}\n", encoding="utf-8")
                _git(upstream, "add", "sickgear/app.py")
                _git(upstream, "commit", "-q", "-m", f"upstream commit {i}")

            _git(fork, "fetch", "-q", "origin", "main")
            self.assertEqual(250, int(_git(fork, "rev-list", "--count", "HEAD..origin/main").stdout.strip()))
            _git(fork, "-c", "merge.conflictStyle=diff3", "merge", "--no-commit", "--no-ff", "origin/main", check=False)
            auto_resolved, remaining = resolve_deterministic_conflicts(fork)
            self.assertEqual([], remaining)
            self.assertTrue(any("sickshift/app.py" in item for item in auto_resolved))
            _git(fork, "commit", "-q", "-m", "merge 250 commits")
            self.assertEqual(0, int(_git(fork, "rev-list", "--count", "HEAD..origin/main").stdout.strip()))
            self.assertIn("VERSION = 251", (fork / "sickshift/app.py").read_text(encoding="utf-8"))
            self.assertIn("import sickshift, os", (fork / "sickshift/app.py").read_text(encoding="utf-8"))

    def test_semantic_conflict_and_arbitration_options_A_B_C(self):
        for choice, expected_text in [
            ("A", "SICKSHIFT_CUSTOM = True"),
            ("B", "UPSTREAM_NEW = True"),
            ("C", "SICKSHIFT_CUSTOM = True"),
        ]:
            with self.subTest(choice=choice), tempfile.TemporaryDirectory(prefix=f"sickshift-arb-{choice}-") as tmp:
                root = Path(tmp)
                upstream = root / "upstream"
                fork = root / "fork"
                upstream.mkdir()
                fork.mkdir()
                _init_repo(upstream)
                (upstream / "gui").mkdir()
                (upstream / "gui/widget.py").write_text("# header\n", encoding="utf-8")
                _git(upstream, "add", "-A")
                _git(upstream, "commit", "-q", "-m", "base")

                _git(root, "clone", "-q", str(upstream), str(fork))
                _git(fork, "config", "user.name", "Test Bot")
                _git(fork, "config", "user.email", "test@example.invalid")

                # Fork adds SickShift customization
                (fork / "gui/widget.py").write_text("# header\nSICKSHIFT_CUSTOM = True\n", encoding="utf-8")
                _git(fork, "add", "-A")
                _git(fork, "commit", "-q", "-m", "fork custom")

                # Upstream adds conflicting line
                (upstream / "gui/widget.py").write_text("# header\nUPSTREAM_NEW = True\n", encoding="utf-8")
                _git(upstream, "add", "-A")
                _git(upstream, "commit", "-q", "-m", "upstream feature")

                _git(fork, "fetch", "-q", "origin", "main")
                _git(fork, "-c", "merge.conflictStyle=diff3", "merge", "--no-commit", "--no-ff", "origin/main", check=False)
                _auto, remaining = resolve_deterministic_conflicts(fork)
                self.assertEqual(["gui/widget.py"], remaining)

                resolved, failed = apply_arbitration_option(fork, choice)
                self.assertEqual(["gui/widget.py"], resolved)
                self.assertEqual([], failed)
                final = (fork / "gui/widget.py").read_text(encoding="utf-8")
                self.assertNotIn("<<<<<<< ", final)
                self.assertIn(expected_text, final)
                if choice == "C":
                    self.assertIn("UPSTREAM_NEW = True", final)

    def test_critical_protection_blocks_deletion_of_sickshift_workflows(self):
        with tempfile.TemporaryDirectory(prefix="sickshift-protect-") as tmp:
            repo = Path(tmp)
            _init_repo(repo)
            wf = repo / ".github/workflows/upstream-watch.yml"
            wf.parent.mkdir(parents=True)
            wf.write_text("name: sync\n", encoding="utf-8")
            _git(repo, "add", "-A")
            _git(repo, "commit", "-q", "-m", "init protected")

            # Simulate upstream merge attempting to delete protected workflow
            _git(repo, "rm", "-q", ".github/workflows/upstream-watch.yml")
            violations = verify_critical_protections(str(repo), base_ref="HEAD")
            self.assertTrue(violations)
            self.assertIn("upstream-watch.yml", violations[0])

    # --- Arbitration command parsing, email replies, authorization & stale checks ---
    def test_arbitration_command_parser_and_email_replies_and_auth(self):
        self.assertEqual("approve", parse_arbitration_command("/approve").command)
        self.assertEqual("approve", parse_arbitration_command("   /APPROVE   \n").command)
        # Direct email reply with quoted history
        email_reply = "\n  /Approve \n\nOn Thu, Nov 26, 2026 GitHub wrote:\n> **WHAT HAPPENED?**\n> reply /choose B\n"
        self.assertEqual("approve", parse_arbitration_command(email_reply).command)

        c = parse_arbitration_command(" /choose  c ")
        self.assertEqual(("choose", "C"), (c.command, c.option))
        self.assertEqual("retry", parse_arbitration_command("/RETRY").command)
        self.assertEqual("explain", parse_arbitration_command("/explain").command)

        # Reject invalid / injection attempts
        self.assertIsNone(parse_arbitration_command("/choose D"))
        self.assertIsNone(parse_arbitration_command("/approve && rm -rf /"))
        self.assertIsNone(parse_arbitration_command("Looks good to me"))

        # Strict owner authorization
        self.assertTrue(authorize_actor("pomercier", "OWNER"))
        self.assertFalse(authorize_actor("random-user", "NONE"))
        self.assertFalse(authorize_actor("contributor", "CONTRIBUTOR"))

    def test_arbitration_issue_format_metadata_and_explain(self):
        body, meta = render_arbitration_issue_body(
            local_sha="a" * 40,
            upstream_sha="b" * 40,
            merge_base="c" * 40,
            behind_count=4,
            conflicted_files=["gui/slick/interfaces/default/inc_displayShow.tmpl"],
            responsible_commits=["1234567 Add codec badge"],
            diff_excerpt="<<<<<<< HEAD\nfoo\n=======\nbar\n>>>>>>> upstream/main",
            run_url="https://github.com/pomercier/SickShift/actions/runs/1",
            revision=2,
        )
        for required_section in (
            "**WHAT HAPPENED?**",
            "**WHY DOES IT MATTER?**",
            "**WHAT SHOULD YOU DO?**",
            "**RECOMMENDED DECISION: C**",
            "**HOW TO APPROVE**",
            "`/approve`",
            "<details>",
            "Technical details (for reference)",
        ):
            self.assertIn(required_section, body)
        parsed_meta = extract_arbitration_metadata(body)
        self.assertEqual(meta, parsed_meta)
        self.assertEqual(2, parsed_meta["revision"])

        explanation = render_explain_comment(body)
        self.assertIn("inc_displayShow.tmpl", explanation)
        self.assertIn("/approve", explanation)

    # --- Watchdog fault injection (false success, disabled workflow, Docker mismatch, recovery) ---
    def test_watchdog_detects_false_success_disabled_workflow_and_docker_mismatch(self):
        active_wfs = [{"path": f".github/workflows/{name}", "state": "active"} for name in REQUIRED_WORKFLOWS]

        # Healthy state
        healthy = evaluate_watchdog_state(
            ahead=38,
            behind=0,
            local_sha="1" * 40,
            upstream_sha="2" * 40,
            workflows=active_wfs,
            sync_runs=[{"status": "completed", "conclusion": "success"}],
            open_issues=[],
            latest_release_tag="v1.3.0",
            release_docker_digest="sha256:aaa",
            latest_docker_digest="sha256:aaa",
        )
        self.assertTrue(healthy.healthy)

        # Fault 1: False success (behind > 0 despite sync reporting success)
        false_success = evaluate_watchdog_state(
            ahead=38,
            behind=5,
            local_sha="1" * 40,
            upstream_sha="2" * 40,
            workflows=active_wfs,
            sync_runs=[{"status": "completed", "conclusion": "success"}],
            open_issues=[],
            latest_release_tag="v1.3.0",
            release_docker_digest="sha256:aaa",
            latest_docker_digest="sha256:aaa",
        )
        self.assertFalse(false_success.healthy)
        self.assertTrue(any("False success" in a for a in false_success.alerts))

        # Fault 2: Primary workflow disabled + partial Docker publication (:latest mismatch)
        broken_wfs = [
            {**w, "state": "disabled_manually"} if w["path"].endswith("upstream-watch.yml") else w
            for w in active_wfs
        ]
        partial = evaluate_watchdog_state(
            ahead=38,
            behind=0,
            local_sha="1" * 40,
            upstream_sha="2" * 40,
            workflows=broken_wfs,
            sync_runs=[{"status": "completed", "conclusion": "failure"}] * 3,
            open_issues=[],
            latest_release_tag="v1.3.0",
            release_docker_digest="sha256:new",
            latest_docker_digest="sha256:old",
        )
        self.assertFalse(partial.healthy)
        self.assertEqual(["upstream-watch.yml"], partial.disabled_workflows)
        self.assertFalse(partial.docker_latest_matches_release)
        self.assertTrue(any("Docker inconsistency" in a for a in partial.alerts))

        # Open arbitration issue suppresses false-drift alert
        pending_arb = evaluate_watchdog_state(
            ahead=38,
            behind=3,
            local_sha="1" * 40,
            upstream_sha="2" * 40,
            workflows=active_wfs,
            sync_runs=[{"status": "completed", "conclusion": "failure"}],
            open_issues=[{"number": 99, "title": ARBITRATION_TITLE, "labels": [{"name": ARBITRATION_LABEL}]}],
            latest_release_tag="v1.3.0",
            release_docker_digest="sha256:aaa",
            latest_docker_digest="sha256:aaa",
        )
        self.assertTrue(pending_arb.healthy)

    # --- Versioning, release impact & namespace normalizer guards ---
    def test_semver_collision_avoidance_and_release_impact_and_url_preservation(self):
        self.assertEqual("v1.2.7", compute_next_semver(["v1.2.5", "v1.2.6"], bump="patch"))
        self.assertEqual("v1.3.0", compute_next_semver(["v1.2.5", "v1.2.6"], bump="minor"))
        self.assertEqual("none", classify_release_impact(["readme.md", "docs/UPSTREAM.md"]))
        self.assertEqual("patch", classify_release_impact(["sickshift/search.py"]))
        self.assertEqual("patch", classify_release_impact(["Dockerfile"]))

        # Preserve external URLs and intentional $.SickGear = $.SickShift; alias
        sample_tmpl = r"\$.SickShift = {}; \$.SickGear = \$.SickShift; #import sickgear" + "\nhttps://github.com/SickGear/SickGear"
        normed = normalize_code_identifiers(sample_tmpl, "gui/slick/interfaces/default/inc_top.tmpl")
        self.assertIn(r"\$.SickGear = \$.SickShift;", normed)
        self.assertIn("#import sickshift", normed)
        self.assertIn("https://github.com/SickGear/SickGear", normed)
        self.assertIn("https://sickgear.github.io/x", shift_preserve_urls("sickgear + https://sickgear.github.io/x"))


if __name__ == "__main__":
    unittest.main()
