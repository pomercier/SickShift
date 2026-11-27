#!/usr/bin/env python3
"""Independent watchdog for SickShift upstream sync, releases, and official Docker image.

Detects:
- Persistent behind commits without open arbitration (including false-success workflows).
- Disabled or missing critical workflows.
- Repeated consecutive sync failures.
- Mismatches between latest GitHub release and official GHCR Docker tags/digests.
- Attempts safe idempotent recovery (re-enabling workflows or dispatching sync) before alerting.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any, Optional
import urllib.request

from scripts.arbitration import ARBITRATION_LABEL, ARBITRATION_TITLE, OWNER, REPO
from scripts.sync_state import SyncState, SyncStateMachine

UPSTREAM_URL = "https://github.com/SickGear/SickGear.git"
DOCKER_REPO = "pomercier/sickshift"
WATCHDOG_LABEL = "watchdog-alert"
WATCHDOG_TITLE = "[WATCHDOG ALERT] SickShift automation requires attention"
REQUIRED_WORKFLOWS = (
    "upstream-watch.yml",
    "arbitration-handler.yml",
    "sync-watchdog.yml",
    "sickshift-ci.yml",
    "bootstrap-platforms.yml",
    "publish-release.yml",
    "docker-publish.yml",
)


@dataclass
class WatchdogReport:
    ahead: int = 0
    behind: int = 0
    local_sha: str = ""
    upstream_sha: str = ""
    missing_workflows: list[str] = field(default_factory=list)
    disabled_workflows: list[str] = field(default_factory=list)
    open_arbitration_issues: list[int] = field(default_factory=list)
    consecutive_sync_failures: int = 0
    latest_release_tag: str = ""
    docker_tag_present: Optional[bool] = None
    docker_latest_matches_release: Optional[bool] = None
    recoveries_attempted: list[str] = field(default_factory=list)
    alerts: list[str] = field(default_factory=list)

    @property
    def healthy(self) -> bool:
        return not self.alerts


def _run(cmd: list[str], env: Optional[dict[str, str]] = None, check: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, check=check, env=env)


def fetch_ghcr_manifest_digest(tag: str, image: str = DOCKER_REPO) -> Optional[str]:
    """Query the public GHCR OCI Registry v2 API for a tag's manifest digest."""
    try:
        token_url = f"https://ghcr.io/token?scope=repository:{image}:pull"
        with urllib.request.urlopen(token_url, timeout=15) as resp:
            token = json.loads(resp.read().decode("utf-8")).get("token", "")
        if not token:
            return None
        manifest_url = f"https://ghcr.io/v2/{image}/manifests/{tag}"
        req = urllib.request.Request(
            manifest_url,
            method="HEAD",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": (
                    "application/vnd.oci.image.index.v1+json, "
                    "application/vnd.docker.distribution.manifest.list.v2+json, "
                    "application/vnd.docker.distribution.manifest.v2+json"
                ),
            },
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.headers.get("Docker-Content-Digest")
    except Exception:
        return None


def compute_ahead_behind(repo_root: Path, upstream_url: str = UPSTREAM_URL) -> tuple[int, int, str, str]:
    """Return (ahead, behind, local_sha, upstream_sha) using real remote refs."""
    _run(["git", "-C", str(repo_root), "fetch", "--no-tags", "origin", "+main:refs/remotes/origin/main"], check=True)
    _run(["git", "-C", str(repo_root), "fetch", "--no-tags", upstream_url, "+main:refs/remotes/upstream/main"], check=True)
    local_sha = _run(["git", "-C", str(repo_root), "rev-parse", "refs/remotes/origin/main"], check=True).stdout.strip()
    upstream_sha = _run(["git", "-C", str(repo_root), "rev-parse", "refs/remotes/upstream/main"], check=True).stdout.strip()
    counts = _run(
        ["git", "-C", str(repo_root), "rev-list", "--left-right", "--count", f"{local_sha}...{upstream_sha}"],
        check=True,
    ).stdout.strip().split()
    return int(counts[0]), int(counts[1]), local_sha, upstream_sha


def evaluate_watchdog_state(
    *,
    ahead: int,
    behind: int,
    local_sha: str,
    upstream_sha: str,
    workflows: list[dict[str, Any]],
    sync_runs: list[dict[str, Any]],
    open_issues: list[dict[str, Any]],
    latest_release_tag: str,
    release_docker_digest: Optional[str],
    latest_docker_digest: Optional[str],
) -> WatchdogReport:
    """Pure evaluation logic (fully unit-testable with fault injection)."""
    report = WatchdogReport(
        ahead=ahead,
        behind=behind,
        local_sha=local_sha,
        upstream_sha=upstream_sha,
        latest_release_tag=latest_release_tag,
    )

    by_path = {Path(w.get("path", "")).name: w for w in workflows}
    for req_wf in REQUIRED_WORKFLOWS:
        wf = by_path.get(req_wf)
        if not wf:
            report.missing_workflows.append(req_wf)
            report.alerts.append(f"Required workflow missing on GitHub: {req_wf}")
        elif wf.get("state") != "active":
            report.disabled_workflows.append(req_wf)
            report.alerts.append(f"Required workflow is not active ({wf.get('state')}): {req_wf}")

    arb_issues = [
        int(i["number"])
        for i in open_issues
        if i.get("title") == ARBITRATION_TITLE
        or any(lbl.get("name") == ARBITRATION_LABEL for lbl in (i.get("labels") or []))
    ]
    report.open_arbitration_issues = arb_issues

    consecutive_failures = 0
    for run in sync_runs:
        if run.get("status") != "completed":
            continue
        if run.get("conclusion") == "failure":
            consecutive_failures += 1
        else:
            break
    report.consecutive_sync_failures = consecutive_failures

    # Detect false success or unaddressed behind drift
    if behind > 0 and not arb_issues:
        latest_completed = next((r for r in sync_runs if r.get("status") == "completed"), None)
        if latest_completed and latest_completed.get("conclusion") == "success":
            report.alerts.append(
                f"False success detected: main is {behind} commit(s) behind SickGear ({upstream_sha[:12]}) "
                "despite the last sync workflow reporting success."
            )
        else:
            report.alerts.append(
                f"Unresolved upstream drift: main is {behind} commit(s) behind SickGear ({upstream_sha[:12]}) "
                "with no open arbitration issue."
            )

    if consecutive_failures >= 3 and not arb_issues:
        report.alerts.append(
            f"Primary sync workflow failed {consecutive_failures} consecutive times without opening an arbitration issue."
        )

    # Verify release <-> Docker consistency
    if latest_release_tag:
        report.docker_tag_present = bool(release_docker_digest)
        if not release_docker_digest:
            report.alerts.append(
                f"Docker inconsistency: GitHub release {latest_release_tag} has no matching GHCR image tag."
            )
        elif latest_docker_digest and release_docker_digest != latest_docker_digest:
            report.docker_latest_matches_release = False
            report.alerts.append(
                f"Docker inconsistency: ghcr.io/{DOCKER_REPO}:latest digest does not match release {latest_release_tag}."
            )
        else:
            report.docker_latest_matches_release = bool(latest_docker_digest)

    return report


def run_watchdog(repo_root: Path, gh_token: str, dispatch_token: str = "", repo: str = REPO) -> WatchdogReport:
    """Execute live watchdog checks, attempt safe recovery, and alert on unresolved issues."""
    sm = SyncStateMachine()
    ahead, behind, local_sha, upstream_sha = compute_ahead_behind(repo_root)
    env = os.environ.copy()
    env["GH_TOKEN"] = gh_token

    wf_raw = _run(["gh", "api", f"repos/{repo}/actions/workflows", "--jq", ".workflows"], env=env).stdout
    workflows = json.loads(wf_raw or "[]")

    runs_raw = _run(
        [
            "gh", "run", "list", "-R", repo,
            "--workflow", "upstream-watch.yml",
            "--limit", "10",
            "--json", "databaseId,status,conclusion,createdAt,headSha",
        ],
        env=env,
    ).stdout
    sync_runs = json.loads(runs_raw or "[]")

    issues_raw = _run(
        ["gh", "issue", "list", "-R", repo, "--state", "open", "--limit", "50", "--json", "number,title,labels"],
        env=env,
    ).stdout
    open_issues = json.loads(issues_raw or "[]")

    rel_res = _run(["gh", "release", "list", "-R", repo, "--limit", "1", "--json", "tagName"], env=env)
    rel_list = json.loads(rel_res.stdout or "[]") if rel_res.returncode == 0 else []
    latest_release = rel_list[0]["tagName"] if rel_list else ""

    rel_ver = latest_release.lstrip("v") if latest_release else ""
    rel_digest = fetch_ghcr_manifest_digest(rel_ver) if rel_ver else None
    latest_digest = fetch_ghcr_manifest_digest("latest") if rel_ver else None

    report = evaluate_watchdog_state(
        ahead=ahead,
        behind=behind,
        local_sha=local_sha,
        upstream_sha=upstream_sha,
        workflows=workflows,
        sync_runs=sync_runs,
        open_issues=open_issues,
        latest_release_tag=latest_release,
        release_docker_digest=rel_digest,
        latest_docker_digest=latest_digest,
    )

    # Safe automatic recovery attempts using dispatch_token (or gh_token)
    act_env = os.environ.copy()
    act_env["GH_TOKEN"] = (dispatch_token or gh_token).strip()

    for disabled in report.disabled_workflows:
        re_enable = _run(["gh", "workflow", "enable", disabled, "-R", repo], env=act_env)
        if re_enable.returncode == 0:
            report.recoveries_attempted.append(f"Re-enabled workflow {disabled}")

    if behind > 0 and not report.open_arbitration_issues and act_env["GH_TOKEN"]:
        sm.transition(SyncState.WATCHDOG_ALERT, "Unresolved upstream drift detected")
        sm.transition(SyncState.RECOVERY_IN_PROGRESS, "Dispatching upstream-watch.yml recovery")
        disp = _run(["gh", "workflow", "run", "upstream-watch.yml", "-R", repo, "--ref", "main"], env=act_env)
        if disp.returncode == 0:
            report.recoveries_attempted.append("Dispatched upstream-watch.yml recovery run")

    if latest_release and (not rel_digest or (latest_digest and rel_digest != latest_digest)) and act_env["GH_TOKEN"]:
        disp_docker = _run(
            ["gh", "workflow", "run", "docker-publish.yml", "-R", repo, "--ref", latest_release],
            env=act_env,
        )
        if disp_docker.returncode == 0:
            report.recoveries_attempted.append(f"Dispatched docker-publish.yml recovery for {latest_release}")

    # Manage deduplicated watchdog alert issue
    existing_alert = next(
        (
            i for i in open_issues
            if i.get("title") == WATCHDOG_TITLE
            or any(lbl.get("name") == WATCHDOG_LABEL for lbl in (i.get("labels") or []))
        ),
        None,
    )

    if report.healthy:
        if existing_alert:
            _run(
                [
                    "gh", "issue", "close", str(existing_alert["number"]), "-R", repo,
                    "--comment",
                    f"Watchdog verified system healthy: `main` is `{ahead}` ahead / `{behind}` behind upstream, "
                    f"all required workflows are active, and release `{latest_release}` matches Docker.",
                ],
                env=env,
            )
    else:
        _run(
            [
                "gh", "label", "create", WATCHDOG_LABEL, "-R", repo,
                "--color", "b60205",
                "--description", "Independent watchdog alert for SickShift sync/release/Docker",
                "--force",
            ],
            env=env,
        )
        body = (
            f"@{OWNER}\n\n"
            "**SickShift Independent Watchdog Alert**\n\n"
            f"- **Ahead / Behind upstream:** `{ahead}` ahead / `{behind}` behind\n"
            f"- **Local `main`:** `{local_sha[:12]}` | **Upstream:** `{upstream_sha[:12]}`\n"
            f"- **Latest release:** `{latest_release or 'none'}`\n\n"
            "**Detected anomalies:**\n"
            + "".join(f"- {a}\n" for a in report.alerts)
            + ("\n**Automatic recovery actions attempted:**\n" + "".join(f"- {r}\n" for r in report.recoveries_attempted)
               if report.recoveries_attempted else "")
            + f"\n[View Watchdog runs](https://github.com/{repo}/actions/workflows/sync-watchdog.yml)\n"
        )
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".md") as fh:
            fh.write(body)
            fh.flush()
            if existing_alert:
                _run(["gh", "issue", "edit", str(existing_alert["number"]), "-R", repo, "--body-file", fh.name], env=env)
            else:
                _run(
                    [
                        "gh", "issue", "create", "-R", repo,
                        "--title", WATCHDOG_TITLE,
                        "--body-file", fh.name,
                        "--assignee", OWNER,
                        "--label", WATCHDOG_LABEL,
                    ],
                    env=env,
                )

    return report


def main() -> int:
    gh_token = os.environ.get("GH_TOKEN", "").strip()
    dispatch_token = os.environ.get("SICKSHIFT_SYNC_TOKEN", "").strip()
    if not gh_token:
        print("GH_TOKEN is required for watchdog execution.", file=sys.stderr)
        return 2
    report = run_watchdog(Path.cwd(), gh_token=gh_token, dispatch_token=dispatch_token)
    print(json.dumps(report.__dict__, indent=2))
    if not report.healthy:
        print("::error title=Watchdog Alert::One or more SickShift sync/Docker invariants failed.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
