# SickShift Upstream Sync Incident Report (2026-11-26)

## Executive Summary

On **2026-11-26**, `pomercier/SickShift:main` accumulated **349 commits behind** `SickGear/SickGear:main` (while 37 commits ahead) despite an existing scheduled synchronization workflow.

## Verified Forensic Timeline

| Timestamp (UTC) | Event | Evidence |
|---|---|---|
| `2026-11-25 14:28:47` | Last synced upstream commit (`hotfix/3.36.18`) | `c61b044325ed0c8df46e471d66ad08d6299caed3` |
| `2026-11-25 15:59:32` | Last successful automatic sync into `SickShift:main` | Commit `573cd7a1`, Run [`45650116216`](https://github.com/pomercier/SickShift/actions/runs/45650116216) |
| `2026-11-26 05:37:00` | Scheduled daily cron (`37 5 * * *`) missed/delayed by GitHub by ~10 hours | GitHub cron queue delay |
| `2026-11-26 09:41:24` | SickGear published `hotfix/3.36.19` modifying `sickgear/search.py` | Commit `b0d7d8d83642` |
| `2026-11-26 15:40:07` | Delayed daily sync ran; conflicted on `sickshift/search.py`; created Issue #13 & failed job | Run [`45851369206`](https://github.com/pomercier/SickShift/actions/runs/45851369206), Issue [#13](https://github.com/pomercier/SickShift/issues/13) |
| `2026-11-26 18:03 – 22:44` | SickGear published `hotfix/3.36.20`, `3.36.21`, `3.36.22` | `64f501b2`, `6497bf76`, `a03f738f` |
| `2026-11-26 23:01:45` | SickGear merged `release/3.37.0` (`dev` → `main`, ~340 commits, 1,363 files) | Commit `bb386ddc` |
| `2026-11-27 00:03:30` | SickGear published `hotfix/3.37.1` (total: 349 commits behind) | Commit `68d2f864e930` |

## Root Causes Identified

1. **Fragile 2-way conflict heuristic caused an unnecessary manual conflict on `sickshift/search.py`:**
   `resolve_mechanical_conflicts()` only used 2-way markers without a `diff3` base comparison and failed to match pure `sickgear` → `sickshift` rename hunks in `sickshift/search.py`, halting sync at `b0d7d8d83642`.
2. **Once-daily cron (`37 5 * * *`) + 10-hour GitHub cron jitter:**
   After run `45851369206` failed at 15:40 UTC, no further sync check occurred for 24 hours, during which SickGear merged the entire `release/3.37.0` branch (349 commits total).
3. **No independent watchdog:**
   No secondary monitor detected that `behind` jumped from 2 commits to 349 commits or that Issue #13 became stale relative to `68d2f864e930`.
4. **No in-issue arbitration automation:**
   Issue #13 asked the owner to SSH into a local machine and run `~/.local/bin/sickshift-sync start` manually rather than offering a one-reply `/approve` workflow.
5. **Email notification gaps:**
   GitHub Actions failure emails for `schedule` events depend on personal GitHub notification settings (`Actions -> Email` and `Participating, @mentions -> Email`) and repository watching state. Furthermore, the repository API returned HTTP 404 on subscription inspection without `notifications` scope, meaning email delivery could not be assumed without verifying user notification settings.
6. **Silent post-merge import breakage risk on large upstream merges:**
   Across the 349 commits in `3.37.0`, Git auto-merged 71 files cleanly **without** conflict while introducing `import sickgear`, `sickgear.*`, and `$.SickGear.*` (such as `lib/api_trakt/trakt.py` and `sickshift/common.py`). Without a post-merge namespace normalizer, clean merges could silently break startup.
7. **Frozen `public_base` in `scripts/check_release.py`:**
   New upstream unit tests (`tests/sg_ech_tests.py`, `tests/sg_tunnel_tests.py`) and `lib/sg_tunnel.py` triggered false-positive privacy blocks because `public_base` was pinned to a November 2025 commit (`60b9dec4`), and `dateutil-zoneinfo.tar.gz` moved from `lib/dateutil/zoneinfo/` to `sickshift/`.
8. **Release & Docker weaknesses:**
   `docker-publish.yml` promoted `:latest` on every `main` push without booting a container or verifying health/migrations; `publish-release.yml` did not gate GitHub release creation on validated Docker publication.

## Permanent Remediations Implemented

All 8 root causes have been permanently fixed in SickShift `v1.3.0`:
- 15-minute lightweight upstream detection (`upstream-watch.yml`).
- Mathematical 3-way `diff3` pure-rename resolver + URL-preserving post-merge namespace normalizer (`scripts/conflict_resolver.py`).
- Dynamic `PUBLIC_UPSTREAM_COMMIT` and `PUBLIC_UPSTREAM_SHA256` refresh (`scripts/auto_sync_sickgear.py`, `scripts/check_release.py`).
- Plain-English `/approve` / `/choose A|B|C` / `/retry` / `/explain` arbitration (`arbitration-handler.yml`, `scripts/arbitration.py`).
- Independent 2-hour watchdog with auto-recovery (`sync-watchdog.yml`, `scripts/watchdog.py`).
- Real container boot, legacy DB migration, volume persistence, and remote pull gates before publishing releases or promoting `:latest` (`publish-release.yml`, `docker-publish.yml`).
