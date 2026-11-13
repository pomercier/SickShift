# SickShift upstream synchronization and recovery

This is the **current automatic synchronization procedure**, not the older
manual branch-and-pull-request workflow. The public fork maintains only the
remote **main** branch. GitHub Actions never merges in the live installation.

## Automatic synchronization

The workflow [Sync SickGear](../.github/workflows/upstream-watch.yml)
runs daily at **05:37 UTC** and can be started manually.

1. A read-only CI checkout of SickShift/main fetches the official
   [SickGear main](https://github.com/SickGear/SickGear).
2. If upstream is already an ancestor of main, no commit, issue or notification
   is requested. Otherwise, Git prepares a merge in disposable CI without
   creating any new branch or pull request.
3. A conflict-free candidate is checked for private files, verified public
   dependencies, syntax errors and regressions. An English merge commit is
   bundled without exposing a publishing token.
4. A separate publish job receives that exact validated bundle and the secret
   SICKSHIFT_SYNC_TOKEN, verifies main has not changed and attempts a normal
   non-force push to main. A changed main causes a safe stop.

The GitHub sync **does not deploy** new code or database migrations into a
running local SickShift service. Keep an independent database backup.

## Conflict-only arbitration

Only a genuine Git merge conflict creates a GitHub issue assigned to
@pomercier, deduplicated by upstream commit SHA. No conflicted merge is pushed.

The existing local conflict helper on CachyOS is used with the fish shell:

~~~fish
~/.local/bin/sickshift-sync start
# After reviewing and resolving the reported files:
~/.local/bin/sickshift-sync resume
~~~

The helper is local to the existing installation and is not created by a
fresh GitHub clone. Unrelated CI, runner, credential or service errors also
block publication but are not falsely reported as merge conflicts.

**GitHub's own Actions failure emails are independent** of the conflict-only
issue policy and depend on the account's notification settings. An issue
assignment does not guarantee an email will be delivered.

## Inspect upstream without modifying main

From a clean development checkout:

~~~fish
git fetch https://github.com/SickGear/SickGear.git main
git merge-base --is-ancestor FETCH_HEAD main
git status --short
~~~

The merge-base check exits with 0 when the upstream revision is included,
and 1 when it is not. It does not create branches or commit changes.

The historical scripts/integrate_upstream.sh still creates a **local review
branch**. It is not used by the automated workflow and should not be used
for the preferred single-branch setup.

## Safeguards and tests

- Release CI checks Python 3.11, 3.12 and 3.13 with privacy scanning, module
  compilation, import checks and targeted regression tests.
- Bootstrap CI checks Linux, Windows and macOS Intel. Passing a bootstrap test
  does **not** certify every feature on that operating system.
- The merge prepare job runs without publishing credentials. The publish job
  refuses to overwrite changes to main.
- Never commit runtime data, credentials, downloads or real databases.
- Branch protection is a separate GitHub setting; passing CI alone does not
  prove it is enabled. Use an authorized GitHub account to inspect it.

## Manual public releases

The [release workflow](../.github/workflows/publish-release.yml) is manual
only. It requires successful release CI and cross-platform bootstrap
checks for the **exact current main commit**, and refuses existing tags.
No release is created merely because the release workflow file changes.

These checks do not replace testing a real running SickShift installation,
a real database, or individual media providers.
