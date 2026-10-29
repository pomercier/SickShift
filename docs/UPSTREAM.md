# Integrating upstream without overwriting the fork

## Keep development and live data separate

Work in a clean development clone. Never use the live installation or its data directory as a merge workspace. The integration script refuses a checkout with uncommitted changes. The repository retains public upstream history so Git can merge against a common ancestor.

```sh
git switch main
git pull --ff-only origin main
bash scripts/integrate_upstream.sh
```

The script creates an `upstream-sync/<revision>` branch, prepares the merge, and runs checks before creating a commit. It does not push or deploy anything. Conflicts remain on that branch: resolve them or run `git merge --abort`. If tests fail, the merge remains uncommitted for investigation.

## Required review

1. Adapt new SickGear imports and files to the SickShift module layout.
2. Review each SQL migration, its version, and its requirements. Test against synthetic data or a private local copy that will never be committed.
3. Run privacy, syntax, import, and test checks. Start the application with a new data directory.
4. Verify fork-specific behavior: dashboard, copying, section collapsing, previews, and actual file renaming.
5. Push only the integration branch and open a pull request targeting `main`.
6. Merge after review. Before deployment, stop the service and back up the data directory. If a SQL migration is involved, roll back code **and** database together.

The weekly workflow opens an issue for each new upstream revision that has not been integrated. It does not merge changes. GitHub Actions and repository issues must be enabled. Manually opened pull requests trigger the normal checks.

## GitHub repository protection

Protect `main` with required pull requests, the three `SickShift release checks` matrix jobs, blocked force-pushes and branch deletion, and resolved conversations. These are GitHub settings: this document does not activate them by itself. They were configured and verified at initial publication. Administrators can change repository settings, so periodically check that the intended rules remain enabled.

The inherited in-application code-replacement entry point is disabled in the fork. Show-data and dependency updates are not blocked by that safeguard. Dependency updates still require an isolated environment and backups because a new package version may introduce incompatibilities.

Application startup does not install Git hooks or automatically repair source files. That prototype behavior was removed from the main entry point so changes remain visible during review.

## First-publication helper

`scripts/publish_github.sh` requires GitHub CLI authentication as `pomercier`. If needed, it creates a real GitHub fork of SickGear named SickShift. It refuses to force-push a divergent remote branch, publishes the source, then configures `main` protection. Rule availability depends on repository permissions and the GitHub plan. If configuration fails, address that failure before considering the repository protected. Running this script performs a real publication.
