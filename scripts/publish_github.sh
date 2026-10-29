#!/usr/bin/env bash
# Explicit publication helper for the prepared clean checkout.
set -euo pipefail
command -v gh >/dev/null || { echo 'GitHub CLI (gh) and authentication are required.' >&2; exit 1; }
[[ "$(gh api user --jq .login)" == pomercier ]] || { echo 'Expected GitHub account pomercier.' >&2; exit 1; }
[[ -z "$(git status --porcelain)" ]] || { echo 'Clean checkout required.' >&2; exit 1; }
python scripts/check_release.py
if ! gh api repos/pomercier/SickShift --silent; then
  gh repo fork SickGear/SickGear --fork-name SickShift --clone=false
fi
# Fail instead of overwriting a pre-existing divergent remote.
git fetch origin main
if ! git merge-base --is-ancestor origin/main HEAD; then
  echo 'Remote contains changes not included locally. Review and merge them; never force-push.' >&2; exit 1
fi
git push origin main
# Branch rules are applied only after the source is actually published.
gh api --method PUT repos/pomercier/SickShift/branches/main/protection --input - <<'JSON'
{"required_status_checks":{"strict":true,"contexts":["release (3.11)","release (3.12)","release (3.13)"]},"enforce_admins":true,"required_pull_request_reviews":{"dismiss_stale_reviews":true,"required_approving_review_count":0},"restrictions":null,"allow_force_pushes":false,"allow_deletions":false,"required_conversation_resolution":true}
JSON
echo 'Published and branch protection configured. Verify Actions and repository settings on GitHub.'
