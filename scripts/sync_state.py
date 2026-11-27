#!/usr/bin/env python3
"""Operational state machine, retry helpers, and critical-path protection for SickShift sync."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import subprocess
import time
from typing import Callable, Iterable, Optional, Sequence, TypeVar

T = TypeVar("T")


class SyncState(str, Enum):
    UP_TO_DATE = "UP_TO_DATE"
    UPSTREAM_CHANGED = "UPSTREAM_CHANGED"
    SYNC_IN_PROGRESS = "SYNC_IN_PROGRESS"
    AUTO_RESOLUTION_IN_PROGRESS = "AUTO_RESOLUTION_IN_PROGRESS"
    VALIDATION_IN_PROGRESS = "VALIDATION_IN_PROGRESS"
    ARBITRATION_REQUIRED = "ARBITRATION_REQUIRED"
    ARBITRATION_PENDING = "ARBITRATION_PENDING"
    ARBITRATION_RECEIVED = "ARBITRATION_RECEIVED"
    RELEASE_PENDING = "RELEASE_PENDING"
    DOCKER_BUILD_IN_PROGRESS = "DOCKER_BUILD_IN_PROGRESS"
    DOCKER_VALIDATION_IN_PROGRESS = "DOCKER_VALIDATION_IN_PROGRESS"
    PUBLICATION_IN_PROGRESS = "PUBLICATION_IN_PROGRESS"
    PUBLICATION_FAILED = "PUBLICATION_FAILED"
    RECOVERY_IN_PROGRESS = "RECOVERY_IN_PROGRESS"
    SYNC_FAILED = "SYNC_FAILED"
    WATCHDOG_ALERT = "WATCHDOG_ALERT"
    FULLY_VERIFIED = "FULLY_VERIFIED"


ALLOWED_TRANSITIONS: dict[SyncState, set[SyncState]] = {
    SyncState.UP_TO_DATE: {
        SyncState.UPSTREAM_CHANGED,
        SyncState.WATCHDOG_ALERT,
        SyncState.FULLY_VERIFIED,
    },
    SyncState.UPSTREAM_CHANGED: {
        SyncState.SYNC_IN_PROGRESS,
        SyncState.ARBITRATION_PENDING,
        SyncState.SYNC_FAILED,
    },
    SyncState.SYNC_IN_PROGRESS: {
        SyncState.AUTO_RESOLUTION_IN_PROGRESS,
        SyncState.VALIDATION_IN_PROGRESS,
        SyncState.ARBITRATION_REQUIRED,
        SyncState.SYNC_FAILED,
        SyncState.UP_TO_DATE,
    },
    SyncState.AUTO_RESOLUTION_IN_PROGRESS: {
        SyncState.VALIDATION_IN_PROGRESS,
        SyncState.ARBITRATION_REQUIRED,
        SyncState.SYNC_FAILED,
    },
    SyncState.VALIDATION_IN_PROGRESS: {
        SyncState.PUBLICATION_IN_PROGRESS,
        SyncState.RELEASE_PENDING,
        SyncState.ARBITRATION_REQUIRED,
        SyncState.SYNC_FAILED,
    },
    SyncState.ARBITRATION_REQUIRED: {
        SyncState.ARBITRATION_PENDING,
        SyncState.SYNC_FAILED,
        SyncState.WATCHDOG_ALERT,
    },
    SyncState.ARBITRATION_PENDING: {
        SyncState.ARBITRATION_RECEIVED,
        SyncState.ARBITRATION_REQUIRED,
        SyncState.SYNC_IN_PROGRESS,
        SyncState.WATCHDOG_ALERT,
    },
    SyncState.ARBITRATION_RECEIVED: {
        SyncState.SYNC_IN_PROGRESS,
        SyncState.AUTO_RESOLUTION_IN_PROGRESS,
        SyncState.ARBITRATION_REQUIRED,
        SyncState.SYNC_FAILED,
    },
    SyncState.RELEASE_PENDING: {
        SyncState.DOCKER_BUILD_IN_PROGRESS,
        SyncState.PUBLICATION_IN_PROGRESS,
        SyncState.PUBLICATION_FAILED,
    },
    SyncState.DOCKER_BUILD_IN_PROGRESS: {
        SyncState.DOCKER_VALIDATION_IN_PROGRESS,
        SyncState.PUBLICATION_FAILED,
    },
    SyncState.DOCKER_VALIDATION_IN_PROGRESS: {
        SyncState.PUBLICATION_IN_PROGRESS,
        SyncState.PUBLICATION_FAILED,
    },
    SyncState.PUBLICATION_IN_PROGRESS: {
        SyncState.FULLY_VERIFIED,
        SyncState.RELEASE_PENDING,
        SyncState.PUBLICATION_FAILED,
        SyncState.RECOVERY_IN_PROGRESS,
    },
    SyncState.PUBLICATION_FAILED: {
        SyncState.RECOVERY_IN_PROGRESS,
        SyncState.WATCHDOG_ALERT,
    },
    SyncState.RECOVERY_IN_PROGRESS: {
        SyncState.SYNC_IN_PROGRESS,
        SyncState.PUBLICATION_IN_PROGRESS,
        SyncState.FULLY_VERIFIED,
        SyncState.WATCHDOG_ALERT,
        SyncState.SYNC_FAILED,
    },
    SyncState.SYNC_FAILED: {
        SyncState.RECOVERY_IN_PROGRESS,
        SyncState.ARBITRATION_REQUIRED,
        SyncState.WATCHDOG_ALERT,
    },
    SyncState.WATCHDOG_ALERT: {
        SyncState.RECOVERY_IN_PROGRESS,
        SyncState.ARBITRATION_PENDING,
        SyncState.FULLY_VERIFIED,
    },
    SyncState.FULLY_VERIFIED: {
        SyncState.UP_TO_DATE,
        SyncState.UPSTREAM_CHANGED,
    },
}


# Critical SickShift files that no upstream merge may silently delete or drop.
CRITICAL_PROTECTED_PATHS: tuple[str, ...] = (
    ".github/workflows/upstream-watch.yml",
    ".github/workflows/arbitration-handler.yml",
    ".github/workflows/sync-watchdog.yml",
    ".github/workflows/sickshift-ci.yml",
    ".github/workflows/bootstrap-platforms.yml",
    ".github/workflows/publish-release.yml",
    ".github/workflows/docker-publish.yml",
    "scripts/auto_sync_sickgear.py",
    "scripts/sync_state.py",
    "scripts/conflict_resolver.py",
    "scripts/arbitration.py",
    "scripts/watchdog.py",
    "scripts/check_release.py",
    "Dockerfile",
    ".dockerignore",
    "docker-compose.yml",
    "gui/slick/css/sickshift-override.css",
    "sickshift_dashboard/app.py",
    "sickshift_dashboard/routes.py",
    "sickshift_dashboard/services.py",
    "sickshift_dashboard/preview_clip.py",
    "sickshift_dashboard/db_backup.py",
    "sickshift_dashboard/version.py",
    "tests/frontend_sanity_tests.py",
    "tests/dashboard_health_tests.py",
    "tests/workflow_policy_tests.py",
    "tests/release_privacy_tests.py",
    "tests/db_backup_tests.py",
    "tests/sync_pipeline_tests.py",
    "readme.md",
    "CHANGELOG.md",
)


@dataclass
class StateTransition:
    from_state: str
    to_state: str
    reason: str
    timestamp: str


@dataclass
class SyncStateMachine:
    state: SyncState = SyncState.UP_TO_DATE
    history: list[StateTransition] = field(default_factory=list)

    def transition(self, target: SyncState, reason: str = "") -> SyncState:
        if target == self.state:
            return self.state
        allowed = ALLOWED_TRANSITIONS.get(self.state, set())
        if target not in allowed:
            raise ValueError(f"Illegal state transition: {self.state.value} -> {target.value}")
        self.history.append(
            StateTransition(
                from_state=self.state.value,
                to_state=target.value,
                reason=reason,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        )
        self.state = target
        return self.state

    def to_dict(self) -> dict:
        return {
            "state": self.state.value,
            "history": [
                {
                    "from": item.from_state,
                    "to": item.to_state,
                    "reason": item.reason,
                    "timestamp": item.timestamp,
                }
                for item in self.history
            ],
        }


def retry_with_backoff(
    fn: Callable[[], T],
    *,
    attempts: int = 3,
    base_delay: float = 2.0,
    retryable: tuple[type[BaseException], ...] = (subprocess.CalledProcessError, OSError, RuntimeError),
    sleep_fn: Callable[[float], None] = time.sleep,
) -> T:
    """Execute fn with bounded exponential backoff retries."""
    last_exc: Optional[BaseException] = None
    for attempt in range(1, max(1, attempts) + 1):
        try:
            return fn()
        except retryable as exc:
            last_exc = exc
            if attempt >= attempts:
                raise
            delay = base_delay * (2 ** (attempt - 1))
            sleep_fn(delay)
    assert last_exc is not None
    raise last_exc


def verify_critical_protections(
    repo_root: str,
    base_ref: str = "HEAD",
    protected_paths: Sequence[str] = CRITICAL_PROTECTED_PATHS,
) -> list[str]:
    """Verify that none of SickShift's critical infrastructure files were deleted or emptied."""
    from pathlib import Path

    root = Path(repo_root)
    violations: list[str] = []
    # Check git index for any deletions of protected files relative to base_ref
    diff = subprocess.run(
        ["git", "-C", str(root), "diff", "--cached", "--name-status", base_ref],
        capture_output=True,
        text=True,
        check=False,
    )
    deleted_in_index: set[str] = set()
    if diff.returncode == 0:
        for line in diff.stdout.splitlines():
            parts = line.split("\t")
            if len(parts) >= 2 and parts[0].startswith("D"):
                deleted_in_index.add(parts[1].strip())

    # Only enforce existence for paths that already existed at base_ref
    tracked_at_base = set(
        subprocess.run(
            ["git", "-C", str(root), "ls-tree", "-r", "--name-only", base_ref],
            capture_output=True,
            text=True,
            check=False,
        ).stdout.splitlines()
    )

    for rel in protected_paths:
        if rel not in tracked_at_base:
            continue
        if rel in deleted_in_index:
            violations.append(f"Protected file deleted during merge: {rel}")
            continue
        target = root / rel
        if not target.is_file() or target.stat().st_size == 0:
            violations.append(f"Protected file missing or emptied: {rel}")
    return violations


def classify_release_impact(changed_files: Iterable[str]) -> str:
    """Return 'none', 'patch', or 'minor' based on changed files for release automation.

    Documentation-only or CI-only metadata edits do not require a Docker rebuild or release.
    """
    files = [f.strip() for f in changed_files if f.strip()]
    if not files:
        return "none"

    app_prefixes = (
        "sickshift/",
        "sickshift_dashboard/",
        "gui/",
        "lib/",
        "autoProcessTV/",
    )
    app_exact = {
        "sickshift.py",
        "bootstrap_dependencies.py",
        "Dockerfile",
        ".dockerignore",
        "docker-compose.yml",
        "requirements.txt",
        "requirements-dashboard.txt",
    }
    touches_runtime = any(
        f in app_exact or f.startswith(app_prefixes) for f in files
    )
    if not touches_runtime:
        return "none"
    # Broad upstream feature releases touching many runtime files or new modules merit patch/minor;
    # default automated upstream merges to 'patch' unless explicitly bumped.
    return "patch"
