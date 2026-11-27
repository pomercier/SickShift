# SickShift Official Docker Validation Report

## Single Official Image Identity

- **Registry:** GitHub Container Registry (`ghcr.io`)
- **Official Image:** `ghcr.io/pomercier/sickshift`
- **Supported Architectures:** `linux/amd64`, `linux/arm64`
- **No competing official images exist.**

## Automated Validation Pipeline (GitHub Actions)

Because Docker is intentionally not installed on the maintainer's personal workstation, all Docker builds, live container boot checks, database migration checks, volume persistence checks, Trivy scans, multi-architecture pushes, and remote pull verifications run cleanly inside GitHub Actions (`docker-publish.yml` and `publish-release.yml`):

1. **Candidate Image Build (`linux/amd64`, `load: true`):** Built locally inside the runner without pushing unvalidated artifacts.
2. **Legacy Migration Fixture:** Seeds `/data/sickbeard.db` in a mounted persistent volume before container start.
3. **Real Container Boot & HTTP Health Gate:** Polls `http://127.0.0.1:18081/dashboard/health` until `status == "ok"` and `db_header_ok == true`.
4. **Functional Endpoints & Privacy Gate:** Verifies `/dashboard/api/diagnostics` (`ffmpeg_available == true`, `version` present, `db_path` omitted), `/dashboard`, and `/view-shows/`.
5. **Migration & Volume Persistence Gate:** Verifies `/data/sickshift.db` exists inside the mounted volume, restarts the container (`docker restart`), and re-verifies `/dashboard/health` returns `status == "ok"`.
6. **Vulnerability Scan:** Runs Trivy (`CRITICAL,HIGH`, ignoring unfixed) for visibility.
7. **Immutable Versioned Multi-Arch Push (`linux/amd64,linux/arm64`):** Publishes `ghcr.io/pomercier/sickshift:<version>` before creating the GitHub release.
8. **Remote Pull & Manifest Verification:** Executes `docker buildx imagetools inspect` and `docker pull` against the published GHCR tag before creating the GitHub Release and promoting `ghcr.io/pomercier/sickshift:latest`.

## Protection of `:latest`

- Non-release pushes to `main` only publish traceability tags (`sha-<7chars>`) after container validation and **never** overwrite `:latest`.
- `:latest` is promoted strictly via `docker buildx imagetools create` from the exact verified digest of a published GitHub Release.
- Any build or container startup failure aborts the workflow before touching `:latest`, keeping the previous stable image untouched.
