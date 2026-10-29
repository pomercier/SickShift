# SickShift compared with SickGear

This comparison was prepared on October 29, 2026 against `SickGear/SickGear`, branch `main`, commit `60b9dec46e9ffae97a87cad0905a654acc726167`. The statements describe the compared sources, not every future release.

| Area | SickGear foundation | SickShift changes |
|---|---|---|
| Show management | Tracking, search, metadata, providers, and integrations | Engine retained; modules renamed to `sickshift` |
| Appearance | Slick interface and its display modes | Cinema-inspired styling, SickShift identity, and a transparent logo |
| Overview | Native management pages | Integrated dashboard and the `sickshift_dashboard` FastAPI package |
| Local previews | No equivalent component in the compared base | Local-episode popup, FFmpeg cache, 8-bit output, and HDR conversion |
| Missing episodes | Native episode-status management | Collapsible groups, copy confirmation, and consistent typography |
| Dashboard sections | No equivalent component | Accessible chevrons, expanded by default, with browser-local preferences |
| Renaming | Native file moves and database updates | Verified before/after results; a failed video move stops processing before associated files |
| Code updates | Built-in upstream updater | Separate integration branches and review; direct replacement blocked |
| Private data | Created by each installation | Clean source export, exclusions, and indexed-file checks |

## Method and history

The publication repository starts directly from SickGear's **public** history. SickShift sources are introduced in new commits; private development history, backups, and the original installation's databases are not imported. The 31 local development commits are consolidated rather than published without review.

Before the global rename, the local committed changes affected 66 files and added approximately 7,452 lines. Those figures do not include all uncommitted changes or the global rename and are not the final size of the fork. For the exact current source comparison:

```sh
git diff --stat 60b9dec46e9ffae97a87cad0905a654acc726167 HEAD
git diff --find-renames 60b9dec46e9ffae97a87cad0905a654acc726167 HEAD
```

## Known limitations

The global rename increases upstream integration work. A successful Git merge is not sufficient: new imports, module names, SQL migrations, and user flows also need review. Older scripts and third-party integrations may still need adaptation. Real public URLs and external protocol identifiers must not be renamed arbitrarily.

A personalized "what to watch" discovery page remains a future enhancement. The current dashboard is not presented as a new recommendation engine.

## Release verification

Local validation covered privacy checks across 4,170 indexed files, imports of both packages, Python compilation, and video-conversion and publication-filtering tests. A fresh startup with an empty data directory on a separate port served the dashboard with HTTP 200 without accessing the personal library.

The first publication exposed CI setup issues, which were corrected in pull request #1: full upstream history is now available to privacy checks, async database dependencies are declared, and current GitHub actions run on Ubuntu 24.04. The required Python 3.11, 3.12, and 3.13 checks passed before that pull request was merged. Branch protection was verified on GitHub. See the Actions tab for the latest results rather than treating these historical checks as a guarantee for future commits.
