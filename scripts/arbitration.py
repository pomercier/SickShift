#!/usr/bin/env python3
"""Human-friendly GitHub issue arbitration: creation, updates, and strict command parsing.

All issue titles, bodies, and comments are written in clear, non-technical English
with collapsible technical details for auditability.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from typing import Any, Optional

from scripts.conflict_resolver import ConflictAnalysis, classify_conflict

REPO = "pomercier/SickShift"
OWNER = "pomercier"
ARBITRATION_LABEL = "arbitration-required"
ARBITRATION_TITLE = "[ACTION REQUIRED] SickShift synchronization — decision needed"
METADATA_RE = re.compile(r"<!--\s*sickshift-arbitration:\s*(\{.*?\})\s*-->", re.DOTALL)

COMMAND_RE = re.compile(
    r"^\s*/(?P<cmd>approve|retry|explain|choose)(?:\s+(?P<arg>[A-Ca-c]))?\s*$",
    re.IGNORECASE,
)


@dataclass
class ParsedCommand:
    command: str  # approve | choose | retry | explain
    option: Optional[str] = None  # A | B | C when command == 'choose'


def parse_arbitration_command(comment_body: str) -> Optional[ParsedCommand]:
    """Parse a strict arbitration command from a GitHub issue comment or email reply.

    Ignores email-quoted lines ('>') and blank lines so replying directly to a GitHub
    notification email with '/approve' works cleanly and safely.
    Never executes arbitrary text.
    """
    if not comment_body or not isinstance(comment_body, str):
        return None
    for raw_line in comment_body.splitlines():
        line = raw_line.strip()
        if not line or line.startswith(">"):
            continue
        # Stop at standard email reply dividers ("On ... wrote:", "-- ")
        if line.startswith("--") or (line.lower().startswith("on ") and line.endswith("wrote:")):
            break
        match = COMMAND_RE.match(line)
        if not match:
            # First non-quoted, non-empty line is not a valid command
            return None
        cmd = match.group("cmd").lower()
        arg = match.group("arg")
        if cmd == "choose":
            if not arg:
                return None
            return ParsedCommand(command="choose", option=arg.upper())
        if arg:
            return None
        return ParsedCommand(command=cmd, option=None)
    return None


def authorize_actor(actor: str, author_association: str = "", allowed_owner: str = OWNER) -> bool:
    """Only allow the repository owner to authorize arbitration actions."""
    if not actor:
        return False
    if actor.lower() == allowed_owner.lower():
        return True
    return author_association.upper() in {"OWNER"}


def extract_arbitration_metadata(issue_body: str) -> Optional[dict[str, Any]]:
    """Extract embedded machine-readable arbitration metadata from an issue body."""
    if not issue_body:
        return None
    match = METADATA_RE.search(issue_body)
    if not match:
        return None
    try:
        data = json.loads(match.group(1))
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        return None


def build_arbitration_plan(conflicted_files: list[str]) -> dict[str, Any]:
    """Build concise, non-technical options and a single recommended decision."""
    analyses: list[ConflictAnalysis] = [classify_conflict(f) for f in conflicted_files]
    all_combinable = bool(analyses) and all(a.combinable for a in analyses)
    any_protected = any(a.category in {"automation/infrastructure", "dependencies/Docker"} for a in analyses)

    options: dict[str, dict[str, str]] = {
        "A": {
            "label": "Keep the SickShift behavior",
            "kept": "All current SickShift customizations and safeguards in the conflicting file(s).",
            "changes": "The conflicting upstream hunk(s) in those file(s) are skipped while all other compatible SickGear updates are still merged.",
            "pros": "Zero risk of losing SickShift features or styling.",
            "cons": "May omit a minor upstream improvement in the skipped section.",
            "risk": "LOW" if any_protected else "LOW",
        },
        "B": {
            "label": "Adopt the new SickGear behavior",
            "kept": "All non-conflicting SickShift features, dashboard, workflows, and Docker setup.",
            "changes": "Replaces the conflicting hunk(s) with SickGear's updated version (adapted to SickShift's namespace).",
            "pros": "Stays closest to upstream SickGear for future updates.",
            "cons": "May overwrite a SickShift customization in the conflicting file(s).",
            "risk": "HIGH" if any_protected else "MEDIUM",
        },
    }

    if all_combinable:
        options["C"] = {
            "label": "Combine both approaches",
            "kept": "Both SickShift's customizations and SickGear's compatible additions.",
            "changes": "Merges both changes together automatically and validates with the full test suite.",
            "pros": "Best of both worlds with no manual Git work.",
            "cons": "Falls back cleanly to arbitration if automated combination fails tests.",
            "risk": "LOW",
        }

    if any_protected:
        recommended = "A"
        rec_reason = (
            "Option A protects SickShift's automation, dashboard, or Docker configuration from being overwritten "
            "while still integrating all other compatible SickGear updates."
        )
    elif all_combinable:
        recommended = "C"
        rec_reason = (
            "Option C keeps SickShift's customizations intact while automatically incorporating SickGear's improvements "
            "and verifying everything with automated tests."
        )
    elif all(a.category == "styling/UI" for a in analyses):
        recommended = "A"
        rec_reason = "Option A preserves SickShift's custom visual theme without breaking any backend functionality."
    else:
        recommended = "A"
        rec_reason = (
            "Option A is the safest default because it preserves SickShift's verified behavior while still merging "
            "all non-conflicting SickGear commits."
        )

    return {
        "analyses": analyses,
        "options": options,
        "allowed_options": list(options.keys()),
        "recommended": recommended,
        "recommended_reason": rec_reason,
    }


def render_arbitration_issue_body(
    *,
    local_sha: str,
    upstream_sha: str,
    merge_base: str,
    behind_count: int,
    conflicted_files: list[str],
    responsible_commits: list[str],
    diff_excerpt: str,
    run_url: str,
    revision: int = 1,
) -> tuple[str, dict[str, Any]]:
    """Render the plain-English arbitration issue body + metadata dict."""
    plan = build_arbitration_plan(conflicted_files)
    options = plan["options"]
    recommended = plan["recommended"]
    allowed_options = plan["allowed_options"]

    file_count = len(conflicted_files)
    file_noun = "file" if file_count == 1 else "files"
    categories = sorted({a.category for a in plan["analyses"]})
    cat_text = ", ".join(categories)

    metadata = {
        "revision": revision,
        "local_sha": local_sha,
        "upstream_sha": upstream_sha,
        "merge_base": merge_base,
        "behind_count": behind_count,
        "recommended": recommended,
        "allowed_options": allowed_options,
        "files": conflicted_files,
    }

    option_lines: list[str] = []
    for key in allowed_options:
        opt = options[key]
        option_lines.append(
            f"**{key} — {opt['label']}.** *(Risk: `{opt['risk']}`)*\n"
            f"- **Kept:** {opt['kept']}\n"
            f"- **Changes:** {opt['changes']}\n"
            f"- **Pros:** {opt['pros']}\n"
            f"- **Cons:** {opt['cons']}\n"
        )

    choose_commands = "\n".join(f"`/choose {k}`\n" for k in allowed_options)
    commits_md = "\n".join(f"- `{c}`" for c in responsible_commits[:15]) or "- *(See upstream compare link)*"
    files_md = "\n".join(f"- `{f}`" for f in conflicted_files)

    body = (
        f"@{OWNER}\n\n"
        "---\n\n"
        "**WHAT HAPPENED?**\n\n"
        f"SickGear published {behind_count} new commit(s), and automatic synchronization encountered a semantic conflict "
        f"in {file_count} {file_noun} ({cat_text}) where both SickShift and SickGear changed the same code. "
        "No broken or unverified change was published to `main`.\n\n"
        "**WHY DOES IT MATTER?**\n\n"
        "Until you choose how to resolve this conflict, SickShift remains paused behind upstream SickGear so that "
        "none of your SickShift features are silently overwritten.\n\n"
        "**WHAT SHOULD YOU DO?**\n\n"
        + "\n".join(option_lines)
        + f"\n**RECOMMENDED DECISION: {recommended}**\n\n"
        f"{plan['recommended_reason']}\n\n"
        "**HOW TO APPROVE**\n\n"
        "Reply to this GitHub issue (or reply directly to this notification email) with:\n\n"
        "`/approve`\n\n"
        "To select another option:\n\n"
        + choose_commands
        + "\nOther commands: `/retry` (re-run automatic sync), `/explain` (extra plain-English explanation).\n\n"
        "No manual Git operation is required.\n\n"
        "---\n\n"
        "<details>\n"
        "<summary>Technical details (for reference)</summary>\n\n"
        f"- **Arbitration revision:** `{revision}`\n"
        f"- **Local `main` SHA:** [`{local_sha[:12]}`](https://github.com/{REPO}/commit/{local_sha})\n"
        f"- **Upstream SickGear SHA:** [`{upstream_sha[:12]}`](https://github.com/SickGear/SickGear/commit/{upstream_sha})\n"
        f"- **Common ancestor (merge-base):** `{merge_base[:12]}`\n"
        f"- **Commits behind upstream:** `{behind_count}`\n"
        f"- **Workflow run:** {run_url}\n\n"
        "**Conflicting files:**\n"
        f"{files_md}\n\n"
        "**Responsible upstream commits:**\n"
        f"{commits_md}\n\n"
        "**Relevant diff excerpt:**\n"
        "```diff\n"
        f"{(diff_excerpt or 'No text diff excerpt available.')[:3500]}\n"
        "```\n\n"
        "**Required validation after resolution:**\n"
        "- Privacy check (`scripts/check_release.py`)\n"
        "- Syntax compilation & package imports (`sickshift`, `sickshift_dashboard`)\n"
        "- Full SickShift non-regression test suite (`tests/*_tests.py`)\n"
        "- Critical infrastructure protection check\n"
        "</details>\n\n"
        f"<!-- sickshift-arbitration: {json.dumps(metadata, sort_keys=True)} -->\n"
    )
    return body, metadata


def _gh(args: list[str], gh_token: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["GH_TOKEN"] = gh_token
    return subprocess.run(["gh", *args], capture_output=True, text=True, check=True, env=env)


def ensure_label(gh_token: str, repo: str = REPO) -> None:
    env = os.environ.copy()
    env["GH_TOKEN"] = gh_token
    subprocess.run(
        [
            "gh", "label", "create", ARBITRATION_LABEL,
            "-R", repo,
            "--color", "d93f0b",
            "--description", "Human arbitration required for SickShift upstream sync",
            "--force",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def create_or_update_arbitration_issue(
    *,
    gh_token: str,
    local_sha: str,
    upstream_sha: str,
    merge_base: str,
    behind_count: int,
    conflicted_files: list[str],
    responsible_commits: list[str],
    diff_excerpt: str,
    run_url: str,
    repo: str = REPO,
) -> dict[str, Any]:
    """Create a single deduplicated arbitration issue or update an existing open one."""
    if not gh_token:
        raise RuntimeError("Missing GH_TOKEN: cannot create or update arbitration issue")

    ensure_label(gh_token, repo=repo)
    existing_raw = _gh(
        ["issue", "list", "-R", repo, "--state", "open", "--limit", "50", "--json", "number,title,body,labels"],
        gh_token,
    ).stdout
    open_issues = json.loads(existing_raw or "[]")
    existing = next(
        (
            item
            for item in open_issues
            if item.get("title") == ARBITRATION_TITLE
            or any(lbl.get("name") == ARBITRATION_LABEL for lbl in (item.get("labels") or []))
        ),
        None,
    )

    if existing:
        old_meta = extract_arbitration_metadata(existing.get("body") or "") or {}
        same_state = (
            old_meta.get("local_sha") == local_sha
            and old_meta.get("upstream_sha") == upstream_sha
            and sorted(old_meta.get("files") or []) == sorted(conflicted_files)
        )
        if same_state:
            return {"action": "unchanged", "issue_number": existing["number"], "metadata": old_meta}
        new_rev = int(old_meta.get("revision") or 1) + 1
        body, meta = render_arbitration_issue_body(
            local_sha=local_sha,
            upstream_sha=upstream_sha,
            merge_base=merge_base,
            behind_count=behind_count,
            conflicted_files=conflicted_files,
            responsible_commits=responsible_commits,
            diff_excerpt=diff_excerpt,
            run_url=run_url,
            revision=new_rev,
        )
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".md") as fh:
            fh.write(body)
            fh.flush()
            _gh(["issue", "edit", str(existing["number"]), "-R", repo, "--title", ARBITRATION_TITLE, "--body-file", fh.name], gh_token)
        _gh(
            [
                "issue", "comment", str(existing["number"]), "-R", repo,
                "--body",
                (
                    f"@{OWNER} Upstream advanced to `{upstream_sha[:12]}` ({behind_count} commits behind). "
                    f"This arbitration was updated to **revision {new_rev}**; any earlier approval is now superseded. "
                    f"Recommended decision: **{meta['recommended']}**. Reply `/approve` to apply it."
                ),
            ],
            gh_token,
        )
        return {"action": "updated", "issue_number": existing["number"], "metadata": meta}

    body, meta = render_arbitration_issue_body(
        local_sha=local_sha,
        upstream_sha=upstream_sha,
        merge_base=merge_base,
        behind_count=behind_count,
        conflicted_files=conflicted_files,
        responsible_commits=responsible_commits,
        diff_excerpt=diff_excerpt,
        run_url=run_url,
        revision=1,
    )
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".md") as fh:
        fh.write(body)
        fh.flush()
        created = _gh(
            [
                "issue", "create", "-R", repo,
                "--title", ARBITRATION_TITLE,
                "--body-file", fh.name,
                "--assignee", OWNER,
                "--label", ARBITRATION_LABEL,
            ],
            gh_token,
        ).stdout.strip()
    return {"action": "created", "issue_url": created, "metadata": meta}


def render_explain_comment(issue_body: str) -> str:
    """Produce an additional plain-English explanation without modifying any repository files."""
    meta = extract_arbitration_metadata(issue_body) or {}
    files = meta.get("files") or []
    rec = meta.get("recommended", "A")
    lines = [
        f"@{OWNER} Here is a plain-English breakdown of the pending decision (revision `{meta.get('revision', 1)}`):",
        "",
    ]
    for f in files:
        info = classify_conflict(f)
        lines.append(f"- **`{f}`** (`{info.category}`, risk `{info.risk}`): {info.summary}")
    lines.extend(
        [
            "",
            f"- Replying **`/approve`** will automatically apply **Option {rec}**, run all SickShift tests and Docker checks, push to `main`, and close this issue once verified.",
            "- No code has been changed by `/explain`.",
        ]
    )
    return "\n".join(lines)
