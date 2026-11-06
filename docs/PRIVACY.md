# Publishing without personal data

The export contains source code, static product assets, tests, and their public fixtures. It excludes SQLite databases, installation configuration, media caches, library posters, logs, backups, Python environments, and machine-specific files.

The TMDB key added during development is not included in the export. Credential-bearing mirror URLs were removed from the published source in favor of PyPI. If a previously used credential is personal, its owner must revoke it: deleting a string from a file does not revoke a key.

Before committing or pushing:

```sh
git add <explicitly-selected-files>
python scripts/check_release.py
git diff --cached --stat
```

The checker examines indexed files for private-data extensions, machine paths, selected token formats, and embedded keys. Public examples inherited from the pinned upstream revision are distinguished from newly introduced values. This is not a substitute for human review: it does not inspect binary image contents or prove that every possible secret is absent. Screenshots showing a real library require the owner’s explicit publication permission. The two showcase images in `docs/assets` were specifically authorized. They contain visual library content only; databases, paths, credentials, capture scripts, and configuration are not included.

The retained history comes from the public upstream repository. No commits from the private development history are imported.

## Local installation and Git

The main checkout may coexist with an installation's data, but `.gitignore` excludes the default `data/` directory, known library/download directories, database sidecars, media and subtitle files, logs, private keys, archives, and environment files. Ignore rules do not remove files that were already tracked, so the release checker remains a second gate. Do not force-add ignored private files.

Keep media and custom data directories outside the checkout whenever practical. Arbitrary text or image files can still contain sensitive content: neither extension rules nor a scanner can guarantee complete protection. Review staged changes before every push. Runtime data is never needed to publish a code update.
