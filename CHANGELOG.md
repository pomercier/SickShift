# Changelog

All notable changes to **SickShift** are documented in this file.
Upstream SickGear release notes are preserved separately in [`CHANGES.md`](CHANGES.md).

SickShift follows [Semantic Versioning](https://semver.org/):
- **PATCH** (`x.y.Z`): bug fixes, security updates, upstream hotfixes, reliability & maintenance improvements.
- **MINOR** (`x.Y.0`): backwards-compatible features, major upstream SickGear releases, or significant operational upgrades.
- **MAJOR** (`X.0.0`): deliberate breaking compatibility changes.

## [1.3.0] - 2026-11-27

### Upstream Synchronization
- Merged 349 upstream commits from `SickGear/SickGear:main` through `68d2f864e930` (**SickGear 3.37.0 & 3.37.1**), bringing `SickShift:main` to **0 commits behind** while preserving full Git ancestry:
  - Provider ECH & blocked-provider tunnel fallback (`sg_ech`, `sg_tunnel`).
  - Video codec badges and `video_size` stream inspection.
  - Updated bundled libraries (Tornado 6.6.1, apprise 1.13.1, dateutil 4.0.0, urllib3 2.8.0, hachoir 3.4.0, PNotify 3.2.1, soupsieve 4.1.3).
  - Automatic log secret masking filter and zoneinfo packaging refresh.

### Infrastructure, Automation & Docker
- **High-frequency upstream detection:** upgraded `upstream-watch.yml` to a lightweight 15-minute `detect` gate feeding isolated `prepare` and `publish` jobs (zero branches/PRs created).
- **Deterministic Level-3 conflict resolution:** upgraded `scripts/conflict_resolver.py` with 3-way `diff3` mathematical rename verification, URL-preserving transforms, and post-merge namespace normalization across `.py`, `.js`, and `.tmpl` files.
- **One-reply human arbitration:** added `arbitration-handler.yml` and `scripts/arbitration.py` supporting `/approve`, `/choose A|B|C`, `/retry`, and `/explain` directly on deduplicated GitHub issues or email replies.
- **Independent watchdog:** added `sync-watchdog.yml` and `scripts/watchdog.py` running every 2 hours to verify real ahead/behind drift, workflow health, false successes, and release/Docker digest consistency with safe auto-recovery.
- **Validated single-image Docker & release pipeline:** `publish-release.yml` and `docker-publish.yml` now boot a real container, verify legacy `sickbeard.db` -> `sickshift.db` migration, persistent volume restarts, `/dashboard/health`, `/dashboard/api/diagnostics`, and `/view-shows/`, push immutable multi-arch tags (`linux/amd64`, `linux/arm64`), verify remote `docker pull`, and promote `:latest` only after all gates pass.
- **Application version consistency:** added `sickshift_dashboard/version.py` (`1.3.0`) exposed on `/dashboard/health` and `/dashboard/api/diagnostics`.
- **Comprehensive fault-injection test suite:** added `tests/sync_pipeline_tests.py` covering state transitions, deterministic resolution, arbitration commands, authorization, stale approvals, watchdog detection, release impact, and protection guards.
- **Public documentation overhaul:** refreshed `readme.md`, added `CHANGELOG.md`, `docs/SYNC_ARCHITECTURE.md`, `docs/SYNC_RUNBOOK.md`, `docs/ARBITRATION_GUIDE.md`, `docs/CUSTOMIZATIONS_REGISTRY.md`, `docs/RELEASE_POLICY.md`, `docs/DOCKER_POLICY.md`, and validation/incident reports.

## [1.2.6] - 2026-11-26
- Excluded `SKIPPED` and `IGNORED` episodes from `/view-shows/` episode denominators and added distinct full progress bar styling (`.progress-empty`) for `0 / 0` shows.

## [1.2.5] - 2026-11-26
- Excluded already downloaded and archived episodes from the Dashboard **Upcoming Episodes** section.

## [1.2.4] - 2026-11-21
- Widened the Dashboard Diagnostics modal to `640px` and removed horizontal overflow scrollbars.

## [1.2.3] - 2026-11-21
- Kept the Diagnostics modal preview cache row on a single line.

## [1.2.2] - 2026-11-21
- Merged upstream SickGear hotfixes (`6a63ea2b`) and hardened GitHub Actions push authentication in `auto_sync_sickgear.py`.

## [1.2.1] - 2026-11-21
- Added automated daily hot SQLite backups (`sqlite3.backup()`, 7-day rolling retention) and frontend anti-regression CI tests.

## [1.2.0] - 2026-11-21
- Added Diagnostics modal (`/api/diagnostics`, `/api/cache/previews/clear`), 1-hour preview clip cache TTL, hardware-accelerated FFmpeg encoding with CPU fallback, isolated `sickshift-override.css`, official GHCR Docker support, and fixed season expand/collapse, episode deletion, and poster card counter clipping.

## [1.1.0] - 2026-11-19
- Migrated primary database filename from `sickbeard.db` to `sickshift.db`, removed obsolete `SickBeard.py`, sandboxed `tests/test_lib.py`, and improved CI FFmpeg installation resilience.

## [1.0.0] - 2026-11-05
- Initial SickShift release: cinema-inspired interface, FastAPI Dashboard, local FFmpeg hover video previews, and protected single-branch upstream synchronization.
