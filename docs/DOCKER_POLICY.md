# SickShift Official Docker Policy

## Single Official Image Identity

SickShift publishes **one and only one** official Docker image:

- **Registry:** GitHub Container Registry (`ghcr.io`)
- **Image:** `ghcr.io/pomercier/sickshift`
- **Architectures:** `linux/amd64`, `linux/arm64` (single unified multi-arch manifest)

There are no competing official images (no separate `-stable`, `-dev`, `-nightly`, or `-legacy` repositories).

## Tagging Policy

| Tag | Meaning | Mutability |
|---|---|---|
| `latest` | Most recent validated stable release | Promoted **only** after full CI + container validation + GitHub release |
| `X.Y.Z` (e.g., `1.3.0`) | Exact immutable release version for predictable deployments & rollbacks | Immutable (never overwritten) |
| `X.Y` (e.g., `1.3`) | Latest validated patch within minor series `X.Y` | Moves forward on validated patches |
| `sha-<7chars>` | Technical traceability tag for `main` commits | Immutable per commit |

## Pre-Publication Validation Gate

Before any image is published or promoted to `:latest`, GitHub Actions (`docker-publish.yml` and `publish-release.yml`) runs a live container validation suite:
1. Builds `linux/amd64` candidate locally (`load: true`, not pushed).
2. Seeds a legacy `sickbeard.db` inside a persistent `/data` volume mount.
3. Starts the container and verifies `/dashboard/health` returns `status: "ok"` and `db_header_ok: true`.
4. Verifies `/dashboard/api/diagnostics` (`ffmpeg_available: true`, no leaked `db_path`), `/dashboard`, and `/view-shows/`.
5. Verifies legacy `sickbeard.db` migrated non-destructively to `/data/sickshift.db`.
6. Restarts the container against the same `/data` volume to verify persistent volume survival.
7. Runs an informational Trivy vulnerability scan (`CRITICAL,HIGH`, ignoring unfixed).
8. Pushes the multi-arch manifest and verifies remote availability via `docker buildx imagetools inspect` and `docker pull`.

A failed build or validation gate **never** replaces `:latest`.

## Updating & Rolling Back

- **Update:** `docker compose pull && docker compose up -d`
- **Rollback:** Change `image: ghcr.io/pomercier/sickshift:latest` to a previous immutable tag (e.g., `ghcr.io/pomercier/sickshift:1.2.6`), then run `docker compose pull && docker compose up -d`. Persistent data in `/data` and media in `/shows` are preserved across updates and rollbacks.
