#!/usr/bin/env bash
# Run only in a clean development clone, never in a live installation.
set -euo pipefail
if [[ -n "$(git status --porcelain)" ]]; then
  echo 'A clean checkout is required; no files changed.' >&2; exit 1
fi
git fetch https://github.com/SickGear/SickGear.git main
upstream_revision=$(git rev-parse FETCH_HEAD)
branch="upstream-sync/${upstream_revision:0:12}"
git switch -c "$branch"
if ! git merge --no-ff --no-commit "$upstream_revision"; then
  echo 'Conflicts retained on the integration branch. Resolve, review renames/imports, and run CI. Do not deploy.' >&2
  exit 1
fi
if git diff --cached --quiet; then
  echo 'No upstream changes to integrate.'; exit 0
fi
python scripts/check_release.py
python -m compileall -q sickshift sickshift_dashboard
python -m unittest tests.preview_clip_tests tests.release_privacy_tests -v
git commit -m "Merge SickGear upstream ${upstream_revision:0:12} for review"
echo "Review $branch and open a pull request. main and the live installation were not changed."
