# SickShift Synchronization Architecture

## Overview

SickShift maintains a **single permanent remote branch (`main`)** and preserves **true Git merge ancestry** with `SickGear/SickGear:main`. No squash merges, history rewrites, force pushes, or persistent PR branches are ever used.

```text
SickGear/SickGear:main
   │
   ▼  (Every 15 min — upstream-watch.yml: detect)
[UP_TO_DATE] ──(behind > 0)──► [UPSTREAM_CHANGED]
                                      │
                                      ▼  (upstream-watch.yml: prepare, no push token)
                              [SYNC_IN_PROGRESS]
                                      │
                       ┌──────────────┴──────────────┐
                       ▼                             ▼
           [AUTO_RESOLUTION_IN_PROGRESS]      (clean merge)
            (diff3 pure rename / DU / UA)            │
                       │                             │
            ┌──────────┴──────────┐                  │
            ▼ (unresolved)        ▼ (resolved)       │
  [ARBITRATION_REQUIRED]   Post-merge normalizer ◄───┘
            │                     │
            ▼                     ▼
  [ARBITRATION_PENDING]   [VALIDATION_IN_PROGRESS]
   (Issue + email alert)    (Privacy, compile, imports,
            │                critical paths, unit tests)
            ▼ (/approve)          │
  [ARBITRATION_RECEIVED] ─────────┤
                                  ▼  (isolated publish job with SICKSHIFT_SYNC_TOKEN)
                         [PUBLICATION_IN_PROGRESS]
                          (Non-force push + verify behind==0)
                                  │
                     ┌────────────┴────────────┐
                     ▼ (docs/CI only)          ▼ (runtime/Docker changed)
             [FULLY_VERIFIED]          [RELEASE_PENDING]
                                               │
                                               ▼ (publish-release.yml)
                                   [DOCKER_BUILD_IN_PROGRESS]
                                               │
                                               ▼ (real container boot, DB migration, health)
                                  [DOCKER_VALIDATION_IN_PROGRESS]
                                               │
                                               ▼ (push versioned tag -> GH release -> promote :latest)
                                       [FULLY_VERIFIED]
```

## Explicit State Machine (`scripts/sync_state.py`)

All 17 operational states (`UP_TO_DATE`, `UPSTREAM_CHANGED`, `SYNC_IN_PROGRESS`, `AUTO_RESOLUTION_IN_PROGRESS`, `VALIDATION_IN_PROGRESS`, `ARBITRATION_REQUIRED`, `ARBITRATION_PENDING`, `ARBITRATION_RECEIVED`, `RELEASE_PENDING`, `DOCKER_BUILD_IN_PROGRESS`, `DOCKER_VALIDATION_IN_PROGRESS`, `PUBLICATION_IN_PROGRESS`, `PUBLICATION_FAILED`, `RECOVERY_IN_PROGRESS`, `SYNC_FAILED`, `WATCHDOG_ALERT`, `FULLY_VERIFIED`) enforce valid transitions via `SyncStateMachine`.

## Three-Level Defense

| Layer | Workflow / Script | Frequency | Role |
|---|---|---|---|
| **Level 1 — Detection** | `.github/workflows/upstream-watch.yml` (`detect`) | Every 15 min + manual | Lightweight ~5s `git fetch` + `rev-list` check |
| **Level 2 — Sync & Validation** | `scripts/auto_sync_sickgear.py` (`prepare` + `publish`) | On drift (`behind > 0`) | Merge, validate in tokenless job, publish verified bundle in isolated job |
| **Level 3 — Deterministic Resolution** | `scripts/conflict_resolver.py` | During merge | 3-way `diff3` mathematical rename proof (`ours == shift(base)`), URL-preserving shift, post-merge stray import normalizer |
| **Human Arbitration** | `.github/workflows/arbitration-handler.yml`, `scripts/arbitration.py` | On owner comment | Deduplicated plain-English issue + `/approve`, `/choose A|B|C`, `/retry`, `/explain` |
| **Independent Watchdog** | `.github/workflows/sync-watchdog.yml`, `scripts/watchdog.py` | Every 2 hours + manual | Independent behind/false-success/workflow/Docker audit + safe auto-recovery |

## Credential & Security Isolation

- `prepare` runs with `persist-credentials: false` and **no push token**; untrusted upstream code or tests can never access `SICKSHIFT_SYNC_TOKEN`.
- `publish` downloads only the cryptographically verified Git bundle, verifies `base == origin/main` and `target` ancestry, and pushes via `GIT_CONFIG_COUNT` in memory without ever echoing credentials.
- `CRITICAL_PROTECTED_PATHS` in `scripts/sync_state.py` prevents any upstream merge from deleting or emptying SickShift workflows, scripts, Dockerfile, dashboard, or regression tests.
- Arbitration commands are parsed strictly against an allowlist (`approve`, `choose A|B|C`, `retry`, `explain`) for the repository owner (`pomercier`) only; comment content is never executed as shell or Python code.
