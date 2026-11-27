# SickShift Release Policy

## Versioning Scheme

SickShift uses [Semantic Versioning](https://semver.org/) (`vMAJOR.MINOR.PATCH`):

- **PATCH (`v1.3.1`)**: Upstream SickGear hotfixes, bug fixes, security patches, reliability fixes, or minor compatible refinements.
- **MINOR (`v1.3.0`)**: New backwards-compatible SickShift features, significant upstream SickGear minor releases (e.g., `3.37.0`), or major operational improvements.
- **MAJOR (`v2.0.0`)**: Deliberate breaking compatibility changes.

Infrastructure-only or documentation-only edits (`docs/**`, `*.md`) never force a release or Docker rebuild (`classify_release_impact()` returns `"none"`).

## Strict Consistency Invariants

Every official release guarantees 1:1 traceability across:
1. Application version (`sickshift_dashboard/version.py` -> `/dashboard/health` & `/dashboard/api/diagnostics`)
2. Git tag (`vX.Y.Z`) on `main`
3. GitHub Release (`SickShift vX.Y.Z`)
4. Official Docker image versioned tag (`ghcr.io/pomercier/sickshift:X.Y.Z` + minor tag `X.Y`)
5. Official Docker `:latest` tag (promoted **only** after the versioned image is validated and verified remotely)
6. `CHANGELOG.md` and OCI image labels (`org.opencontainers.image.version`, `org.opencontainers.image.revision`)

## Automated & Manual Release Flow

```text
UPSTREAM CHANGE -> SYNC -> TEST -> VERSION -> DOCKER BUILD -> CONTAINER VALIDATE
  -> PUSH IMMUTABLE TAG -> VERIFY REMOTE PULL -> GITHUB RELEASE -> PROMOTE :latest -> VERIFY
```

- A GitHub release is **never** created before its multi-architecture Docker image is validated in a live container and confirmed pullable from GHCR.
- Existing tags and releases are immutable; `publish-release.yml` refuses tag collisions.
- `publish-release.yml` is triggered only via `workflow_dispatch` (manually or programmatically by `auto_sync_sickgear.py` when runtime/Docker files change), eliminating workflow push loops.
