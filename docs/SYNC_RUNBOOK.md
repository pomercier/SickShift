# SickShift Synchronization Runbook

## Routine Operations

No manual steps are required for normal operation:
- `upstream-watch.yml` detects upstream changes every 15 minutes and merges/publishes automatically.
- `sync-watchdog.yml` audits sync health, workflows, releases, and Docker every 2 hours.

## Manual Triggers

```sh
# Trigger immediate upstream sync check
gh workflow run upstream-watch.yml -R pomercier/SickShift --ref main

# Trigger independent watchdog audit
gh workflow run sync-watchdog.yml -R pomercier/SickShift --ref main

# Trigger a validated release + Docker publication (explicit version or auto-bump)
gh workflow run publish-release.yml -R pomercier/SickShift --ref main -f version=v1.3.0
gh workflow run publish-release.yml -R pomercier/SickShift --ref main -f bump=patch
```

## Incident Recovery Procedures

### 1. Push fails with `Invalid username or token`
`SICKSHIFT_SYNC_TOKEN` expired or was revoked. Refresh it cleanly:
```sh
gh auth token | gh secret set SICKSHIFT_SYNC_TOKEN -R pomercier/SickShift
gh workflow run upstream-watch.yml -R pomercier/SickShift --ref main
```

### 2. Watchdog reports `behind > 0` with no arbitration issue
The watchdog automatically dispatches `upstream-watch.yml`. If the issue persists, inspect the latest `upstream-watch.yml` run:
```sh
gh run list -R pomercier/SickShift --workflow upstream-watch.yml -L 5
gh run view <RUN_ID> -R pomercier/SickShift --log-failed
```

### 3. Partial publication (GitHub release exists, Docker tag or `:latest` missing/mismatched)
Re-run `docker-publish.yml` against the exact release tag (idempotent):
```sh
gh workflow run docker-publish.yml -R pomercier/SickShift --ref v1.3.0 -f version_tag=1.3.0 -f promote_latest=true
```

### 4. Local installation sync after remote auto-merge
GitHub Actions never modifies your personal machine directly. To pull validated updates locally:
```sh
git fetch origin --tags
git pull --ff-only origin main
sudo systemctl restart sickshift.service
```

### 5. Known External Limitation
A GitHub-hosted watchdog cannot detect a full GitHub Actions platform outage or an account-wide Actions suspension. If zero-cost external monitoring is desired later, an external HTTP check against the public GitHub API (`https://api.github.com/repos/pomercier/SickShift/compare/SickGear:main...main`) can monitor `behind_by > 0` independently.
