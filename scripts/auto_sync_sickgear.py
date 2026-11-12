#!/usr/bin/env python3
"""Safe upstream merge preparation, conflict-only issue alert, and separate push.

Run by .github/workflows/upstream-watch.yml; never runs on the live service.
No branches or pull requests are created. The publishing token exists only in the
separate publish job after all checks complete.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

REPO = "pomercier/SickShift"
UPSTREAM_URL = "https://github.com/SickGear/SickGear.git"
PUBLIC_BLOBS = (
    "lib/certifi/cacert.pem",
    "lib/dateutil/zoneinfo/dateutil-zoneinfo.tar.gz",
)


def run(*args: str, check: bool = True, text: bool = True, env=None):
    command = [str(a) for a in args]
    result = subprocess.run(command, check=False, text=text, capture_output=True, env=env)
    if result.stdout:
        print(result.stdout if text else f"<{len(result.stdout)} bytes>", end="" if text else "\n")
    if result.stderr:
        print(result.stderr if text else f"<{len(result.stderr)} bytes stderr>", file=sys.stderr, end="" if text else "\n")
    if check and result.returncode:
        raise subprocess.CalledProcessError(result.returncode, command)
    return result


def git(*args, check=True):
    return run("git", *args, check=check)


def revparse(rev):
    return git("rev-parse", "--verify", rev).stdout.strip()


def output(**items):
    path = os.environ.get("GITHUB_OUTPUT")
    if not path:
        print("OUTPUT:", items)
        return
    with open(path, "a", encoding="utf-8") as file:
        for key, value in items.items():
            file.write(f"{key}={value}\n")


def unchanged():
    return not git("status", "--porcelain", "--untracked-files=no").stdout.strip()


def notify_conflict(upstream_sha: str, files: list[str], gh_token: str):
    """Create only one GitHub issue per upstream SHA, notifying its assignee."""
    if not gh_token:
        raise RuntimeError("GITHUB_TOKEN absent : impossible de notifier le conflit")
    gh_env = os.environ.copy()
    gh_env["GH_TOKEN"] = gh_token
    title = f"[SickShift] Conflit Git SickGear {upstream_sha[:12]}"
    existing = run(
        "gh", "issue", "list", "-R", REPO, "--state", "all",
        "--limit", "500", "--json", "title,number", check=True, env=gh_env,
    )
    issues = json.loads(existing.stdout or "[]")
    if any(issue.get("title") == title for issue in issues):
        print("Conflit déjà notifié pour cette révision ; aucun autre email demandé.")
        return
    links = f"https://github.com/{REPO}/actions/workflows/upstream-watch.yml"
    body = (
        f"@pomercier : le rapprochement de SickGear `{upstream_sha}` avec "
        "`SickShift/main` demande une résolution manuelle.\n\n"
        "**Fichiers en conflit :**\n"
        + "".join(f"- `{name}`\n" for name in files)
        + "\nAucune modification n'a été publiée. Pas de branche ni de PR créée.\n\n"
        "**Résolution sur le PC CachyOS :**\n\n"
        "```fish\n"
        "~/.local/bin/sickshift-sync start\n"
        "# Résoudre les fichiers indiqués puis :\n"
        "~/.local/bin/sickshift-sync resume\n"
        "```\n\n"
        f"[Historique de l'automatisation]({links})\n"
    )
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".md") as file:
        file.write(body)
        file.flush()
        run("gh", "issue", "create", "-R", REPO, "--title", title,
            "--body-file", file.name, "--assignee", "pomercier", env=gh_env)


def update_public_hashes(upstream_sha: str):
    """Refresh ONLY verified public dependency bytes already explicitly allowlisted.

    Matches the exact marker inserted by sickshift-sync v2. An unexpected
    checker layout causes a safe failure rather than weakening privacy checks.
    """
    checker = Path("scripts/check_release.py")
    source = checker.read_text(encoding="utf-8")
    marker_begin = "# sickshift-sync: PUBLIC-UPSTREAM-SHA256-BEGIN"
    marker_end = "# sickshift-sync: PUBLIC-UPSTREAM-SHA256-END"
    if source.count(marker_begin) != 1 or source.count(marker_end) != 1:
        raise RuntimeError("Marqueurs v2 absents dans check_release.py : arrêt sécurisé")
    hashes = {}
    for path in PUBLIC_BLOBS:
        upstream = run("git", "show", f"{upstream_sha}:{path}", check=False, text=False)
        local = Path(path)
        if upstream.returncode != 0 or not local.is_file():
            continue
        if upstream.stdout != local.read_bytes():
            raise RuntimeError(f"Dépendance publique modifiée hors amont: {path}")
        hashes[path] = hashlib.sha256(upstream.stdout).hexdigest()
    if len(hashes) != len(PUBLIC_BLOBS):
        raise RuntimeError("Une dépendance publique attendue manque : arrêt sécurisé")
    entries = "\n".join(f"    {path!r}: {digest!r}," for path, digest in sorted(hashes.items()))
    replacement = (
        marker_begin + "\n"
        "# Empreintes vérifiées octet par octet sur SickGear/main.\n"
        "PUBLIC_UPSTREAM_SHA256 = {\n" + entries + "\n}\n"
        "def trusted_public_upstream_blob(name, content):\n"
        "    expected = PUBLIC_UPSTREAM_SHA256.get(name)\n"
        "    return expected is not None and hashlib.sha256(content).hexdigest() == expected\n"
        + marker_end
    )
    updated = re.sub(
        re.escape(marker_begin) + r".*?" + re.escape(marker_end),
        lambda _: replacement,
        source,
        count=1,
        flags=re.DOTALL,
    )
    if updated != source:
        checker.write_text(updated, encoding="utf-8")
        git("add", "--", str(checker))
        print("Empreintes publiques amont rafraîchies après vérification stricte.")


def prepare():
    # Do not expose issue-writing credentials to unreviewed upstream tests.
    gh_token = os.environ.pop("GH_TOKEN", "")
    if not unchanged():
        raise RuntimeError("Checkout comporte des modifications suivies non prévues")
    git("config", "user.name", "SickShift Upstream Sync")
    git("config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
    git("config", "rerere.enabled", "false")  # Do not silently reuse historical conflict resolutions.
    git("fetch", "--no-tags", UPSTREAM_URL, "+main:refs/remotes/upstream/main")
    upstream_sha = revparse("refs/remotes/upstream/main")
    base = revparse("HEAD")
    print("SickShift base:", base)
    print("SickGear upstream:", upstream_sha)
    if git("merge-base", "--is-ancestor", upstream_sha, "HEAD", check=False).returncode == 0:
        print("Déjà synchronisé avec toutes les modifications de SickGear.")
        output(ready="false", conflict="false")
        return
    merged = git("-c", "merge.renameLimit=10000", "merge", "--no-commit", "--no-ff", upstream_sha, check=False)
    if merged.returncode:
        conflicted = git("diff", "--name-only", "--diff-filter=U").stdout.splitlines()
        if conflicted:
            print("Conflits Git détectés, sans publication:", *conflicted, sep="\n - ")
            notify_conflict(upstream_sha, conflicted, gh_token)
            output(ready="false", conflict="true")
            return
        raise RuntimeError("Échec de fusion sans index en conflit : consulter le journal")
    update_public_hashes(upstream_sha)
    print("Contrôle de confidentialité...")
    run(sys.executable, "scripts/check_release.py")
    print("Contrôle syntaxique...")
    run(sys.executable, "-m", "compileall", "-q", "sickshift", "sickshift_dashboard")
    print("Tests de non-régression...")
    run(sys.executable, "-m", "unittest", "tests.preview_clip_tests", "tests.release_privacy_tests", "-v")
    git("commit", "-m", f"Merge upstream SickGear {upstream_sha[:12]} into SickShift")
    target = revparse("HEAD")
    if not unchanged():
        raise RuntimeError("Modifications inattendues après préparation")
    temp = Path(os.environ.get("RUNNER_TEMP", "/tmp")) / "sickshift-merge"
    temp.mkdir(parents=True, exist_ok=True)
    bundle = temp / "integration.bundle"
    git("bundle", "create", str(bundle), "HEAD", f"^{base}")
    (temp / "metadata.json").write_text(json.dumps({"base": base, "target": target, "upstream": upstream_sha}), encoding="utf-8")
    print("Fusion et validations OK ; bundle prêt pour une publication isolée.")
    output(ready="true", conflict="false")


def publish():
    secret = os.environ.get("SICKSHIFT_PUSH_TOKEN", "")
    if not secret:
        raise RuntimeError("Secret GitHub SICKSHIFT_SYNC_TOKEN absent")
    temp = Path(os.environ.get("RUNNER_TEMP", "/tmp")) / "sickshift-merge"
    info = json.loads((temp / "metadata.json").read_text(encoding="utf-8"))
    bundle = temp / "integration.bundle"
    for key in ("base", "target", "upstream"):
        if not re.fullmatch(r"[0-9a-f]{40}", info.get(key, "")):
            raise RuntimeError("Métadonnées de commit invalides")
    git("fetch", "--no-tags", "origin", "main")
    current = revparse("FETCH_HEAD")
    if current != info["base"]:
        raise RuntimeError("main a changé pendant la validation : nouvel essai au prochain passage")
    git("bundle", "verify", str(bundle))
    git("fetch", str(bundle), "HEAD")
    if revparse("FETCH_HEAD") != info["target"]:
        raise RuntimeError("Le bundle ne correspond pas au commit validé")
    if git("merge-base", "--is-ancestor", info["base"], info["target"], check=False).returncode:
        raise RuntimeError("Le commit préparé n'est pas descendant de main")
    if git("merge-base", "--is-ancestor", info["upstream"], info["target"], check=False).returncode:
        raise RuntimeError("Le commit préparé n'inclut pas SickGear")
    with tempfile.TemporaryDirectory(prefix="sickshift-push-") as directory:
        askpass = Path(directory) / "askpass.sh"
        askpass.write_text('#!/bin/sh\nprintf "%s\\n" "$SICKSHIFT_PUSH_TOKEN"\n', encoding="utf-8")
        askpass.chmod(0o700)
        env = os.environ.copy()
        env["GIT_ASKPASS"] = str(askpass)
        env["GIT_TERMINAL_PROMPT"] = "0"
        run("git", "-c", "credential.helper=", "push",
            f"https://x-access-token@github.com/{REPO}.git",
            f"{info['target']}:refs/heads/main", env=env)
    print(f"SUCCÈS : main publié à {info['target']}; aucune branche créée.")


if __name__ == "__main__":
    try:
        mode = sys.argv[1] if len(sys.argv) == 2 else ""
        if mode == "prepare":
            prepare()
        elif mode == "publish":
            publish()
        else:
            raise ValueError("Usage: auto_sync_sickgear.py prepare|publish")
    except (RuntimeError, ValueError, subprocess.CalledProcessError, OSError, json.JSONDecodeError) as exc:
        print(f"ERREUR NON LIÉE À UN CONFLIT : {exc}", file=sys.stderr)
        sys.exit(2)
