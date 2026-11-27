#!/usr/bin/env python3
"""Permanent SickShift upstream sync engine: fast detect, diff3 prepare, arbitration, and isolated publish.

Design invariants:
- Single permanent remote branch: main (zero branches or PRs created).
- True Git merge history preserved (--no-ff, never squashed or force-pushed).
- Publishing credentials (SICKSHIFT_SYNC_TOKEN) exist ONLY in the isolated publish job.
- Deterministic Level-3 diff3 conflict resolution + post-merge namespace normalization.
- Critical SickShift infrastructure files cannot be silently deleted by upstream merges.
- Plain-English GitHub arbitration issues with /approve, /choose A|B|C, /retry, /explain.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.arbitration import (
    ARBITRATION_LABEL,
    ARBITRATION_TITLE,
    OWNER,
    REPO,
    authorize_actor,
    create_or_update_arbitration_issue,
    extract_arbitration_metadata,
    parse_arbitration_command,
    render_explain_comment,
)
from scripts.conflict_resolver import (
    apply_arbitration_option,
    normalize_merged_files,
    resolve_deterministic_conflicts,
)
from scripts.sync_state import (
    SyncState,
    SyncStateMachine,
    classify_release_impact,
    retry_with_backoff,
    verify_critical_protections,
)

UPSTREAM_URL = "https://github.com/SickGear/SickGear.git"
PUBLIC_BLOBS: tuple[tuple[str, str], ...] = (
    ("lib/certifi/cacert.pem", "lib/certifi/cacert.pem"),
    ("sickshift/dateutil-zoneinfo.tar.gz", "sickgear/dateutil-zoneinfo.tar.gz"),
)
VALIDATION_TEST_MODULES: tuple[str, ...] = (
    "tests.preview_clip_tests",
    "tests.release_privacy_tests",
    "tests.bootstrap_dependencies_tests",
    "tests.preview_availability_tests",
    "tests.workflow_policy_tests",
    "tests.network_logo_tests",
    "tests.dashboard_health_tests",
    "tests.frontend_sanity_tests",
    "tests.db_backup_tests",
    "tests.sync_pipeline_tests",
)
SEMVER_TAG_RE = re.compile(r"^v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")


def run(*args: str, check: bool = True, text: bool = True, env: Optional[dict[str, str]] = None, cwd: Optional[Path] = None):
    command = [str(a) for a in args]
    result = subprocess.run(command, check=False, text=text, capture_output=True, env=env, cwd=cwd)
    if result.stdout:
        print(result.stdout if text else f"<{len(result.stdout)} bytes>", end="" if text else "\n")
    if result.stderr:
        print(result.stderr if text else f"<{len(result.stderr)} bytes stderr>", file=sys.stderr, end="" if text else "\n")
    if check and result.returncode:
        raise subprocess.CalledProcessError(result.returncode, command)
    return result


def git(*args: str, check: bool = True, cwd: Optional[Path] = None):
    return run("git", *args, check=check, cwd=cwd)


def revparse(rev: str, cwd: Optional[Path] = None) -> str:
    return git("rev-parse", "--verify", rev, cwd=cwd).stdout.strip()


def output(**items: Any) -> None:
    path = os.environ.get("GITHUB_OUTPUT")
    if not path:
        print("OUTPUT:", items)
        return
    with open(path, "a", encoding="utf-8") as fh:
        for key, value in items.items():
            fh.write(f"{key}={value}\n")


def unchanged(cwd: Optional[Path] = None) -> bool:
    return not git("status", "--porcelain", "--untracked-files=no", cwd=cwd).stdout.strip()


def compute_next_semver(existing_tags: list[str], bump: str = "patch") -> str:
    """Compute next non-colliding vMAJOR.MINOR.PATCH tag."""
    parsed: list[tuple[int, int, int]] = []
    for tag in existing_tags:
        m = SEMVER_TAG_RE.match(tag.strip())
        if m:
            parsed.append((int(m.group(1)), int(m.group(2)), int(m.group(3))))
    if not parsed:
        return "v1.0.0"
    major, minor, patch = max(parsed)
    if bump == "minor":
        candidate = (major, minor + 1, 0)
    elif bump == "major":
        candidate = (major + 1, 0, 0)
    else:
        candidate = (major, minor, patch + 1)
    while candidate in parsed:
        candidate = (candidate[0], candidate[1], candidate[2] + 1)
    return f"v{candidate[0]}.{candidate[1]}.{candidate[2]}"


def update_public_hashes(upstream_sha: str, repo_root: Path = Path(".")) -> None:
    """Refresh verified public upstream SHA256 allowlist and upstream commit marker."""
    checker = repo_root / "scripts/check_release.py"
    source = checker.read_text(encoding="utf-8")
    marker_begin = "# sickshift-sync: PUBLIC-UPSTREAM-SHA256-BEGIN"
    marker_end = "# sickshift-sync: PUBLIC-UPSTREAM-SHA256-END"
    if source.count(marker_begin) != 1 or source.count(marker_end) != 1:
        raise RuntimeError("Missing PUBLIC-UPSTREAM-SHA256 markers in scripts/check_release.py")

    hashes: dict[str, str] = {}
    for local_rel, upstream_rel in PUBLIC_BLOBS:
        upstream = run("git", "show", f"{upstream_sha}:{upstream_rel}", check=False, text=False, cwd=repo_root)
        local_path = repo_root / local_rel
        if upstream.returncode != 0 or not local_path.is_file():
            continue
        if upstream.stdout != local_path.read_bytes():
            raise RuntimeError(f"Public upstream dependency modified outside upstream: {local_rel}")
        hashes[local_rel] = hashlib.sha256(upstream.stdout).hexdigest()

    if not hashes:
        raise RuntimeError("No verified public upstream blobs found during hash refresh")

    entries = "\n".join(f"    {path!r}: {digest!r}," for path, digest in sorted(hashes.items()))
    replacement = (
        marker_begin + "\n"
        "# Verified byte-for-byte against SickGear/main.\n"
        f"PUBLIC_UPSTREAM_COMMIT = {upstream_sha!r}\n"
        "PUBLIC_UPSTREAM_SHA256 = {\n" + entries + "\n}\n"
        "def trusted_public_upstream_blob(name, content):\n"
        "    expected = PUBLIC_UPSTREAM_SHA256.get(name)\n"
        "    return expected is not None and hashlib.sha256(content).hexdigest() == expected\n"
        + marker_end
    )
    updated = re.sub(
        re.escape(marker_begin) + r".*?" + re.escape(marker_end),
        lambda _: replacement,
        source,
        count=1,
        flags=re.DOTALL,
    )
    if updated != source:
        checker.write_text(updated, encoding="utf-8")
        git("add", "--", "scripts/check_release.py", cwd=repo_root)
        print("Refreshed verified upstream dependency hashes in scripts/check_release.py.")


def _run_validations(repo_root: Path, base_sha: str) -> None:
    """Run all non-negotiable pre-publish quality, security, and protection gates."""
    violations = verify_critical_protections(str(repo_root), base_ref=base_sha)
    if violations:
        raise RuntimeError("Critical SickShift protection check failed:\n - " + "\n - ".join(violations))

    print("Running privacy check...")
    run(sys.executable, "scripts/check_release.py", cwd=repo_root)

    print("Running syntax compilation check...")
    run(sys.executable, "-m", "compileall", "-q", "sickshift", "sickshift_dashboard", "scripts", cwd=repo_root)

    print("Verifying package imports...")
    imp_env = os.environ.copy()
    imp_env["PYTHONPATH"] = f"{repo_root / 'lib'}{os.pathsep}{repo_root}"
    run(sys.executable, "-c", "import sickshift; import sickshift_dashboard", env=imp_env, cwd=repo_root)

    print("Running SickShift regression tests...")
    available_modules = [
        mod for mod in VALIDATION_TEST_MODULES
        if (repo_root / (mod.replace(".", "/") + ".py")).is_file()
    ]
    run(sys.executable, "-m", "unittest", *available_modules, "-v", cwd=repo_root)


def _collect_conflict_context(repo_root: Path, base_sha: str, upstream_sha: str, files: list[str]) -> tuple[str, int, list[str], str]:
    merge_base = git("merge-base", base_sha, upstream_sha, cwd=repo_root).stdout.strip()
    behind_str = git("rev-list", "--count", f"{base_sha}..{upstream_sha}", cwd=repo_root).stdout.strip()
    behind_count = int(behind_str or "0")
    commits = git("log", "--oneline", "-n", "15", f"{merge_base}..{upstream_sha}", cwd=repo_root).stdout.splitlines()

    excerpts: list[str] = []
    for rel in files[:5]:
        p = repo_root / rel
        if not p.is_file():
            continue
        try:
            lines = p.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue
        for idx, line in enumerate(lines):
            if line.startswith("<<<<<<< "):
                end = idx + 1
                while end < len(lines) and not lines[end].startswith(">>>>>>> "):
                    end += 1
                snippet = "\n".join(lines[max(0, idx - 2):min(len(lines), end + 3)])
                excerpts.append(f"--- {rel} ---\n{snippet}")
                break
    return merge_base, behind_count, commits, "\n\n".join(excerpts)


def _export_bundle(base: str, target: str, upstream_sha: str, release_impact: str, arbitration_issue: str = "", arbitration_option: str = "") -> None:
    temp = Path(os.environ.get("RUNNER_TEMP", "/tmp")) / "sickshift-merge"
    temp.mkdir(parents=True, exist_ok=True)
    bundle = temp / "integration.bundle"
    git("bundle", "create", str(bundle), "HEAD", f"^{base}")
    metadata = {
        "base": base,
        "target": target,
        "upstream": upstream_sha,
        "release_impact": release_impact,
        "arbitration_issue": arbitration_issue,
        "arbitration_option": arbitration_option,
    }
    (temp / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")


def detect() -> None:
    """Fast upstream drift detection (seconds) without installing heavy dependencies."""
    sm = SyncStateMachine()
    retry_with_backoff(lambda: git("fetch", "--no-tags", UPSTREAM_URL, "+main:refs/remotes/upstream/main"), attempts=3)
    upstream_sha = revparse("refs/remotes/upstream/main")
    local_sha = revparse("HEAD")
    counts = git("rev-list", "--left-right", "--count", f"{local_sha}...{upstream_sha}").stdout.strip().split()
    ahead, behind = int(counts[0]), int(counts[1])
    print(f"SickShift main={local_sha[:12]} | SickGear main={upstream_sha[:12]} | ahead={ahead} behind={behind}")
    if behind == 0:
        sm.transition(SyncState.FULLY_VERIFIED, "Already up to date with SickGear/main")
        output(needs_sync="false", behind="0", ahead=str(ahead), upstream_sha=upstream_sha, state=sm.state.value)
        return
    sm.transition(SyncState.UPSTREAM_CHANGED, f"{behind} upstream commits pending")
    output(needs_sync="true", behind=str(behind), ahead=str(ahead), upstream_sha=upstream_sha, state=sm.state.value)


def prepare(arbitration_option: str = "", expected_upstream_sha: str = "", arbitration_issue: str = "") -> None:
    """Prepare and validate an upstream merge without publishing credentials."""
    sm = SyncStateMachine()
    gh_token = os.environ.pop("GH_TOKEN", "")
    repo_root = Path.cwd()
    if not unchanged(repo_root):
        raise RuntimeError("Checkout has unexpected tracked modifications before sync")

    git("config", "user.name", "SickShift Upstream Sync")
    git("config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
    git("config", "rerere.enabled", "false")

    retry_with_backoff(lambda: git("fetch", "--no-tags", UPSTREAM_URL, "+main:refs/remotes/upstream/main"), attempts=3)
    upstream_sha = revparse("refs/remotes/upstream/main")
    base = revparse("HEAD")

    if expected_upstream_sha and expected_upstream_sha != upstream_sha:
        print(f"Stale arbitration: expected upstream {expected_upstream_sha[:12]}, current is {upstream_sha[:12]}.")
        output(ready="false", conflict="false", stale="true", upstream_sha=upstream_sha)
        return

    print(f"SickShift base: {base}")
    print(f"SickGear upstream: {upstream_sha}")
    if git("merge-base", "--is-ancestor", upstream_sha, "HEAD", check=False).returncode == 0:
        print("Already synchronized with all upstream SickGear commits.")
        sm.transition(SyncState.FULLY_VERIFIED, "Already synchronized")
        output(ready="false", conflict="false", state=sm.state.value)
        return

    sm.transition(SyncState.UPSTREAM_CHANGED, f"New upstream {upstream_sha[:12]}")
    sm.transition(SyncState.SYNC_IN_PROGRESS, "Starting true Git merge with diff3")

    merged = git(
        "-c", "merge.renameLimit=99999",
        "-c", "diff.renameLimit=99999",
        "-c", "merge.conflictStyle=diff3",
        "merge", "--no-commit", "--no-ff", upstream_sha,
        check=False,
    )

    if merged.returncode:
        initial_unmerged = git("diff", "--name-only", "--diff-filter=U").stdout.splitlines()
        if not initial_unmerged:
            sm.transition(SyncState.SYNC_FAILED, "Merge failed without unmerged index entries")
            raise RuntimeError("Git merge failed without conflict entries; inspect workflow logs")

        sm.transition(SyncState.AUTO_RESOLUTION_IN_PROGRESS, f"Analyzing {len(initial_unmerged)} conflicted file(s)")
        auto_resolved, remaining = resolve_deterministic_conflicts(repo_root)
        if auto_resolved:
            print(f"Deterministically resolved {len(auto_resolved)} file(s).")

        if remaining and arbitration_option:
            print(f"Applying owner-approved arbitration option {arbitration_option} to {len(remaining)} file(s)...")
            applied, failed = apply_arbitration_option(repo_root, arbitration_option)
            print(f"Arbitration applied to: {applied}; failed: {failed}")
            remaining = git("diff", "--name-only", "--diff-filter=U").stdout.splitlines()

        if remaining:
            sm.transition(SyncState.ARBITRATION_REQUIRED, f"Unresolved semantic conflicts: {remaining}")
            merge_base, behind_count, commits, excerpt = _collect_conflict_context(repo_root, base, upstream_sha, remaining)
            run_id = os.environ.get("GITHUB_RUN_ID", "")
            run_url = (
                f"https://github.com/{REPO}/actions/runs/{run_id}"
                if run_id
                else f"https://github.com/{REPO}/actions/workflows/upstream-watch.yml"
            )
            res = create_or_update_arbitration_issue(
                gh_token=gh_token,
                local_sha=base,
                upstream_sha=upstream_sha,
                merge_base=merge_base,
                behind_count=behind_count,
                conflicted_files=remaining,
                responsible_commits=commits,
                diff_excerpt=excerpt,
                run_url=run_url,
            )
            sm.transition(SyncState.ARBITRATION_PENDING, f"Arbitration issue {res.get('action')}")
            print("Human arbitration required:", res)
            output(ready="false", conflict="true", state=sm.state.value)
            return

    # Always normalize stray upstream sickgear imports/JS refs in files touched by the merge
    staged_files = git("diff", "--cached", "--name-only", "--diff-filter=AM").stdout.splitlines()
    normalized = normalize_merged_files(repo_root, staged_files)
    if normalized:
        print(f"Post-merge namespace normalization updated {len(normalized)} file(s).")

    update_public_hashes(upstream_sha, repo_root=repo_root)

    sm.transition(SyncState.VALIDATION_IN_PROGRESS, "Running privacy, compile, import, and regression tests")
    _run_validations(repo_root, base_sha=base)

    all_changed = git("diff", "--cached", "--name-only").stdout.splitlines()
    release_impact = classify_release_impact(all_changed)

    msg = f"Merge upstream SickGear {upstream_sha[:12]} into SickShift"
    if arbitration_option:
        msg += f" (arbitration option {arbitration_option})"
    git("commit", "-m", msg)
    target = revparse("HEAD")
    if not unchanged(repo_root):
        raise RuntimeError("Unexpected modified files left after merge commit")

    _export_bundle(
        base=base,
        target=target,
        upstream_sha=upstream_sha,
        release_impact=release_impact,
        arbitration_issue=arbitration_issue,
        arbitration_option=arbitration_option,
    )
    sm.transition(SyncState.PUBLICATION_IN_PROGRESS, "Validated bundle exported for isolated publish")
    print(f"Merge validated (release_impact={release_impact}); bundle ready for isolated publication.")
    output(ready="true", conflict="false", release_impact=release_impact, target=target, state=sm.state.value)


def publish() -> None:
    """Publish the exact validated merge bundle to main using SICKSHIFT_SYNC_TOKEN."""
    sm = SyncStateMachine(state=SyncState.PUBLICATION_IN_PROGRESS)
    secret = os.environ.get("SICKSHIFT_PUSH_TOKEN", "").strip()
    if not secret:
        raise RuntimeError("Missing GitHub secret SICKSHIFT_SYNC_TOKEN")

    temp = Path(os.environ.get("RUNNER_TEMP", "/tmp")) / "sickshift-merge"
    info = json.loads((temp / "metadata.json").read_text(encoding="utf-8"))
    bundle = temp / "integration.bundle"
    for key in ("base", "target", "upstream"):
        if not re.fullmatch(r"[0-9a-f]{40}", info.get(key, "")):
            raise RuntimeError(f"Invalid commit metadata for {key}")

    retry_with_backoff(lambda: git("fetch", "--no-tags", "origin", "main"), attempts=3)
    current = revparse("FETCH_HEAD")
    if current != info["base"]:
        raise RuntimeError("main changed during validation; retry on next scheduled cycle")

    git("bundle", "verify", str(bundle))
    git("fetch", str(bundle), "HEAD")
    if revparse("FETCH_HEAD") != info["target"]:
        raise RuntimeError("Bundle HEAD does not match validated commit SHA")
    if git("merge-base", "--is-ancestor", info["base"], info["target"], check=False).returncode:
        raise RuntimeError("Prepared commit is not a descendant of main")
    if git("merge-base", "--is-ancestor", info["upstream"], info["target"], check=False).returncode:
        raise RuntimeError("Prepared commit does not include upstream SickGear ancestry")

    basic = base64.b64encode(f"x-access-token:{secret}".encode("utf-8")).decode("ascii")
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GIT_CONFIG_COUNT"] = "2"
    env["GIT_CONFIG_KEY_0"] = "credential.helper"
    env["GIT_CONFIG_VALUE_0"] = ""
    env["GIT_CONFIG_KEY_1"] = "http.https://github.com/.extraheader"
    env["GIT_CONFIG_VALUE_1"] = f"AUTHORIZATION: basic {basic}"

    def _do_push() -> None:
        pushed = run(
            "git", "push",
            f"https://github.com/{REPO}.git",
            f"{info['target']}:refs/heads/main",
            check=False,
            env=env,
        )
        if pushed.returncode:
            raise RuntimeError(
                "Push to main failed: verify that GitHub secret SICKSHIFT_SYNC_TOKEN is valid, non-expired, and allowed to push to main."
            )

    retry_with_backoff(_do_push, attempts=3, base_delay=3.0)

    # Post-push remote verification: confirm origin/main == target and behind == 0
    retry_with_backoff(lambda: git("fetch", "--no-tags", "origin", "+main:refs/remotes/origin/main"), attempts=3)
    remote_main = revparse("refs/remotes/origin/main")
    if remote_main != info["target"]:
        raise RuntimeError(f"Remote main verification mismatch: expected {info['target']}, got {remote_main}")

    gh_env = os.environ.copy()
    gh_env["GH_TOKEN"] = secret

    # Close any open arbitration issue now that main is verified at 0 behind
    arb_issue = str(info.get("arbitration_issue") or "").strip()
    if arb_issue.isdigit():
        run(
            "gh", "issue", "close", arb_issue, "-R", REPO,
            "--comment",
            f"Synchronization succeeded and was verified on `main` (`{info['target'][:12]}`, 0 commits behind upstream `{info['upstream'][:12]}`). Closing this arbitration issue.",
            check=False,
            env=gh_env,
        )
    else:
        open_raw = run(
            "gh", "issue", "list", "-R", REPO, "--state", "open", "--limit", "20", "--json", "number,title,labels",
            check=False,
            env=gh_env,
        ).stdout
        for item in json.loads(open_raw or "[]"):
            if item.get("title") == ARBITRATION_TITLE or any(
                lbl.get("name") == ARBITRATION_LABEL for lbl in (item.get("labels") or [])
            ):
                run(
                    "gh", "issue", "close", str(item["number"]), "-R", REPO,
                    "--comment",
                    f"Automatically resolved and verified on `main` (`{info['target'][:12]}`).",
                    check=False,
                    env=gh_env,
                )

    # Trigger downstream automated release & Docker publication if runtime/Docker files changed
    if info.get("release_impact") in {"patch", "minor"}:
        sm.transition(SyncState.RELEASE_PENDING, f"Triggering automated release ({info['release_impact']})")
        run(
            "gh", "workflow", "run", "publish-release.yml", "-R", REPO,
            "--ref", "main",
            "-f", f"bump={info['release_impact']}",
            check=False,
            env=gh_env,
        )

    sm.transition(SyncState.FULLY_VERIFIED, f"Published and verified {info['target'][:12]}")
    print(f"SUCCESS: main published and verified at {info['target']}; zero branches created.")
    output(published_sha=info["target"], release_impact=info.get("release_impact", "none"), state=sm.state.value)


def handle_arbitration_comment() -> None:
    """Parse and validate an issue comment from arbitration-handler.yml."""
    gh_token = os.environ.get("GH_TOKEN", "").strip()
    actor = os.environ.get("COMMENT_AUTHOR", "").strip()
    assoc = os.environ.get("COMMENT_AUTHOR_ASSOCIATION", "").strip()
    comment_body = os.environ.get("COMMENT_BODY", "")
    issue_number = os.environ.get("ISSUE_NUMBER", "").strip()
    issue_body = os.environ.get("ISSUE_BODY", "")

    parsed = parse_arbitration_command(comment_body)
    if parsed is None:
        print("Comment does not contain a recognized arbitration command; ignoring.")
        output(action="ignore")
        return

    gh_env = os.environ.copy()
    gh_env["GH_TOKEN"] = gh_token

    if not authorize_actor(actor, assoc):
        run(
            "gh", "issue", "comment", issue_number, "-R", REPO,
            "--body",
            f"@{actor} Only the repository owner (`@{OWNER}`) is authorized to execute arbitration commands.",
            check=False,
            env=gh_env,
        )
        output(action="unauthorized")
        return

    if parsed.command == "explain":
        explanation = render_explain_comment(issue_body)
        run("gh", "issue", "comment", issue_number, "-R", REPO, "--body", explanation, check=True, env=gh_env)
        output(action="explained")
        return

    meta = extract_arbitration_metadata(issue_body)
    if parsed.command == "retry":
        run(
            "gh", "issue", "comment", issue_number, "-R", REPO,
            "--body",
            "Retry requested. Automatic synchronization and validation have started. No further action is required unless a conflict persists.",
            check=True,
            env=gh_env,
        )
        output(action="retry", option="", expected_upstream_sha="")
        return

    if not meta:
        run(
            "gh", "issue", "comment", issue_number, "-R", REPO,
            "--body",
            "Arbitration metadata is missing from this issue. Reply `/retry` to regenerate a fresh arbitration summary.",
            check=True,
            env=gh_env,
        )
        output(action="invalid")
        return

    chosen = meta.get("recommended", "A") if parsed.command == "approve" else (parsed.option or "")
    allowed = meta.get("allowed_options") or ["A", "B"]
    if chosen not in allowed:
        run(
            "gh", "issue", "comment", issue_number, "-R", REPO,
            "--body",
            f"Option `{chosen}` is not available for this arbitration (allowed options: {', '.join(allowed)}). No changes were applied.",
            check=True,
            env=gh_env,
        )
        output(action="invalid")
        return

    run(
        "gh", "issue", "comment", issue_number, "-R", REPO,
        "--body",
        f"Decision received: Option {chosen}. Synchronization and validation have started. No further action is required unless a new conflict occurs.",
        check=True,
        env=gh_env,
    )
    output(
        action="apply",
        option=chosen,
        expected_upstream_sha=str(meta.get("upstream_sha", "")),
        issue_number=issue_number,
    )


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) >= 2 else ""
    try:
        if mode == "detect":
            detect()
        elif mode == "prepare":
            prepare()
        elif mode == "prepare-arbitration":
            option = os.environ.get("ARBITRATION_OPTION", "").strip().upper()
            expected_sha = os.environ.get("EXPECTED_UPSTREAM_SHA", "").strip()
            issue_num = os.environ.get("ISSUE_NUMBER", "").strip()
            prepare(arbitration_option=option, expected_upstream_sha=expected_sha, arbitration_issue=issue_num)
        elif mode == "publish":
            publish()
        elif mode == "handle-comment":
            handle_arbitration_comment()
        elif mode == "next-version":
            bump = sys.argv[2] if len(sys.argv) >= 3 else "patch"
            tags = git("tag", "--list").stdout.splitlines()
            print(compute_next_semver(tags, bump=bump))
        else:
            print(
                "Usage: auto_sync_sickgear.py <detect|prepare|prepare-arbitration|publish|handle-comment|next-version>",
                file=sys.stderr,
            )
            return 2
        return 0
    except Exception as exc:
        print(f"SYNC ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
