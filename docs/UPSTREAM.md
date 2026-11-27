# SickShift Upstream Synchronization & Recovery

This document summarizes SickShift's permanent single-branch (`main`) upstream synchronization setup. For deep architectural details, see [SYNC_ARCHITECTURE.md](SYNC_ARCHITECTURE.md), [ARBITRATION_GUIDE.md](ARBITRATION_GUIDE.md), and [SYNC_RUNBOOK.md](SYNC_RUNBOOK.md).

## Permanent multi-level protection

1. **Level 1 — High-frequency detection (`upstream-watch.yml`):**
   Runs every **15 minutes** (`*/15 * * * *`) with a fast ~5-second `detect` job that fetches `SickGear/SickGear:main` and checks real `ahead`/`behind` counts. Heavy validation runs only when `behind > 0`.
2. **Level 2 — Isolated merge & validation (`scripts/auto_sync_sickgear.py`):**
   Performs a true Git merge (`--no-ff`, `merge.conflictStyle=diff3`) preserving complete upstream Git ancestry without creating extra branches or pull requests. Applies deterministic Level-3 conflict resolution (`scripts/conflict_resolver.py`), normalizes stray upstream `sickgear` imports/JS references, refreshes verified public dependency hashes (`scripts/check_release.py`), verifies critical SickShift files are intact, and executes the full regression suite.
3. **Isolated publication (`publish` job):**
   Receives only the verified Git bundle and `SICKSHIFT_SYNC_TOKEN`, verifies `main` has not moved, performs a non-force push, confirms remote `behind == 0`, closes any resolved arbitration issue, and dispatches automated release + Docker validation when runtime or Docker files changed.
4. **One-reply arbitration (`arbitration-handler.yml`):**
   If a genuine semantic conflict cannot be deterministically resolved, a deduplicated GitHub issue (`[ACTION REQUIRED] SickShift synchronization — decision needed`) is created/updated, assigned to `@pomercier`, and the workflow fails to trigger GitHub's own Actions failure emails. Replying `/approve` (or `/choose A|B|C`, `/retry`, `/explain`) applies the decision automatically after strict actor, option, and SHA validation.
5. **Independent watchdog (`sync-watchdog.yml`):**
   Runs every **2 hours** (`17 */2 * * *`) to detect hidden behind drift, false successes, disabled workflows, or release/Docker tag mismatches, attempting safe automatic recovery and opening a `[WATCHDOG ALERT]` issue if attention is required.

## Verification & releases

- `sickshift-ci.yml` tests Python 3.11, 3.12, and 3.13 (privacy scan, compilation, imports, and full unit test suite).
- `bootstrap-platforms.yml` verifies Linux, Windows, and macOS Intel bootstrap behavior.
- `publish-release.yml` requires passing CI and cross-platform checks AND full Docker container validation before publishing a public GitHub Release and promoting `ghcr.io/pomercier/sickshift:latest`.
- The automated GitHub sync never mutates a local running SickShift service directly; keep independent backups (SickShift also creates daily hot SQLite backups automatically in `backups/`).
