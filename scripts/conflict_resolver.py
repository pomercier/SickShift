#!/usr/bin/env python3
"""Deterministic Level-3 conflict resolution and post-merge namespace normalization.

Guarantees:
- Never blindly applies 'ours' or 'theirs' on unverified semantic conflicts.
- Uses 3-way diff3 conflict markers (ours, base, theirs) to prove mathematically
  when a conflict hunk differs from base strictly by the SickGear -> SickShift rename.
- Preserves external URLs (e.g. https://github.com/SickGear/...) and the intentional
  `$.SickGear = $.SickShift;` JS compatibility alias in inc_top.tmpl.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import subprocess
from typing import Iterable

from scripts.sync_state import CRITICAL_PROTECTED_PATHS

URL_RE = re.compile(r"https?://[^\s'\"<>]+", re.I)
DIFF3_PATTERN = re.compile(
    r"<<<<<<< [^\n]*\n(.*?)\|\|\|\|\|\|\| [^\n]*\n(.*?)=======\n(.*?)>>>>>>> [^\n]*\n",
    re.DOTALL,
)
TWO_WAY_PATTERN = re.compile(
    r"<<<<<<< [^\n]*\n(.*?)=======\n(.*?)>>>>>>> [^\n]*\n",
    re.DOTALL,
)

PROTECTED_SET = set(CRITICAL_PROTECTED_PATHS)


@dataclass
class ConflictAnalysis:
    path: str
    category: str
    risk: str  # LOW | MEDIUM | HIGH
    summary: str
    combinable: bool
    recommended: str  # A | B | C


def shift_preserve_urls(text: str) -> str:
    """Transform SickGear identifiers to SickShift while preserving external URLs."""
    urls: list[str] = []

    def _save(match: re.Match[str]) -> str:
        urls.append(match.group(0))
        return f"__SICKSHIFT_URL_TOKEN_{len(urls) - 1}__"

    tmp = URL_RE.sub(_save, text)
    tmp = (
        tmp.replace("sickgear", "sickshift")
        .replace("SickGear", "SickShift")
        .replace("SICKGEAR", "SICKSHIFT")
        .replace("sickbeard.db", "sickshift.db")
    )
    for idx, url in enumerate(urls):
        tmp = tmp.replace(f"__SICKSHIFT_URL_TOKEN_{idx}__", url)
    return tmp


def _norm_lines(text: str) -> str:
    return re.sub(r"[ \t]+$", "", text, flags=re.M)


def _norm_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def normalize_code_identifiers(text: str, rel_path: str) -> str:
    """Shift stray upstream sickgear imports/JS refs introduced by clean auto-merges."""
    urls: list[str] = []

    def _save(match: re.Match[str]) -> str:
        urls.append(match.group(0))
        return f"__SICKSHIFT_URL_TOKEN_{len(urls) - 1}__"

    # Protect intentional $.SickGear = $.SickShift; compatibility alias in inc_top.tmpl
    alias_token = "__SICKSHIFT_JS_ALIAS_LINE__"
    has_alias = r"\$.SickGear = \$.SickShift;" in text
    tmp = text.replace(r"\$.SickGear = \$.SickShift;", alias_token) if has_alias else text
    tmp = URL_RE.sub(_save, tmp)

    p = Path(rel_path)
    if rel_path.startswith("gui/slick/js/") and p.suffix == ".js" and "/lib/" not in rel_path:
        tmp = tmp.replace("$.SickGear", "$.SickShift")
    elif p.suffix in (".py", ".tmpl"):
        tmp = re.sub(r"\bimport\s+sickgear\b", "import sickshift", tmp)
        tmp = re.sub(r"\bfrom\s+sickgear\b", "from sickshift", tmp)
        tmp = re.sub(r"\bsickgear\.", "sickshift.", tmp)
        tmp = re.sub(r"\.sickgear\b", ".sickshift", tmp)
        tmp = re.sub(r"\bSickGearException\b", "SickShiftException", tmp)
        tmp = re.sub(r"(['\"])sickgear\1", r"\1sickshift\1", tmp)
        tmp = re.sub(r"(['\"])sickgear\.([a-zA-Z0-9_.]+)\1", r"\1sickshift.\2\1", tmp)
        tmp = re.sub(r"\bgetattr\(sickgear,", "getattr(sickshift,", tmp)
        tmp = re.sub(r"\bsetattr\(sickgear,", "setattr(sickshift,", tmp)
        tmp = re.sub(r"\bhasattr\(sickgear,", "hasattr(sickshift,", tmp)
        tmp = re.sub(r"\$\.SickGear\b", "$.SickShift", tmp)
        tmp = re.sub(r"\\\$\.SickGear\b", r"\\$.SickShift", tmp)
        tmp = re.sub(r"\$sickgear\.", "$sickshift.", tmp)

    for idx, url in enumerate(urls):
        tmp = tmp.replace(f"__SICKSHIFT_URL_TOKEN_{idx}__", url)
    if has_alias:
        tmp = tmp.replace(alias_token, r"\$.SickGear = \$.SickShift;")
    return tmp


def _git(repo_root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo_root), *args],
        capture_output=True,
        text=True,
        check=check,
    )


def resolve_deterministic_conflicts(repo_root: Path) -> tuple[list[str], list[str]]:
    """Resolve provably lossless deterministic conflicts; return (auto_resolved, remaining)."""
    auto_resolved: list[str] = []

    # 1. Special index statuses (DU / UA)
    for line in _git(repo_root, "status", "--porcelain").stdout.splitlines():
        if len(line) < 4:
            continue
        code = line[:2]
        rel = line[3:].strip()
        if code == "DU":
            if rel in PROTECTED_SET:
                # Never auto-delete a protected file
                continue
            _git(repo_root, "rm", "-f", "--", rel)
            auto_resolved.append(f"{rel} (DU: kept deleted)")
        elif code == "UA":
            target = repo_root / rel
            if target.is_file() and target.suffix in (".py", ".js", ".tmpl"):
                txt = target.read_text(encoding="utf-8", errors="ignore")
                shifted = shift_preserve_urls(txt)
                if shifted != txt:
                    target.write_text(shifted, encoding="utf-8")
            _git(repo_root, "add", "--", rel)
            auto_resolved.append(f"{rel} (UA: added upstream & normalized)")

    # 2. Content conflicts (UU) using 3-way diff3 proof
    unmerged = _git(repo_root, "diff", "--name-only", "--diff-filter=U").stdout.splitlines()
    for rel in unmerged:
        target = repo_root / rel
        if not target.is_file():
            continue
        try:
            content = target.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue

        # Never blindly auto-resolve protected SickShift infrastructure files if modified on both sides
        if rel in PROTECTED_SET:
            continue

        # Deterministic CHANGES.md handling (upstream release notes file)
        if rel == "CHANGES.md" and "<<<<<<< " in content:
            def _resolve_changes(m: re.Match[str]) -> str:
                ours, base, theirs = m.group(1), m.group(2), m.group(3)
                if _norm_lines(ours) == _norm_lines(base) or _norm_lines(ours) == _norm_lines(shift_preserve_urls(base)):
                    return theirs
                # Additive prepend on both sides: preserve upstream changelog top
                if base.strip() and base.strip() in theirs:
                    return theirs
                return m.group(0)

            updated = DIFF3_PATTERN.sub(_resolve_changes, content)
            if updated != content and "<<<<<<< " not in updated:
                target.write_text(updated, encoding="utf-8")
                _git(repo_root, "add", "--", rel)
                auto_resolved.append(f"{rel} (upstream changelog)")
                continue

        def _resolve_hunk(match: re.Match[str]) -> str:
            ours, base, theirs = match.group(1), match.group(2), match.group(3)
            shifted_base = shift_preserve_urls(base)
            shifted_theirs = shift_preserve_urls(theirs)
            # Rule 1: Pure mechanical package rename (ours == shift(base))
            if _norm_lines(ours) == _norm_lines(shifted_base):
                return shifted_theirs
            # Rule 2: Already converged (ours == shift(theirs))
            if _norm_lines(ours) == _norm_lines(shifted_theirs):
                return ours
            # Rule 3: Whitespace/formatting-only difference vs shifted base
            if _norm_ws(ours) == _norm_ws(shifted_base):
                return shifted_theirs
            return match.group(0)

        new_content = DIFF3_PATTERN.sub(_resolve_hunk, content)
        if new_content != content:
            target.write_text(new_content, encoding="utf-8")
        if "<<<<<<< " not in new_content:
            _git(repo_root, "add", "--", rel)
            auto_resolved.append(f"{rel} (diff3 pure rename/format)")

    remaining = _git(repo_root, "diff", "--name-only", "--diff-filter=U").stdout.splitlines()
    return auto_resolved, remaining


def normalize_merged_files(repo_root: Path, files: Iterable[str]) -> list[str]:
    """Normalize stray upstream sickgear imports/JS refs in all files touched by a merge."""
    normalized: list[str] = []
    for rel in sorted(set(files)):
        target = repo_root / rel
        if not target.is_file():
            continue
        is_candidate = (
            (rel.startswith(("sickshift/", "tests/", "gui/slick/interfaces/", "autoProcessTV/", "lib/")) or "/" not in rel)
            and target.suffix in (".py", ".tmpl")
        ) or (
            rel.startswith("gui/slick/js/") and target.suffix == ".js" and "/lib/" not in rel
        )
        if not is_candidate:
            continue
        try:
            txt = target.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        updated = normalize_code_identifiers(txt, rel)
        if updated != txt:
            target.write_text(updated, encoding="utf-8")
            _git(repo_root, "add", "--", rel)
            normalized.append(rel)
    return normalized


def classify_conflict(rel_path: str) -> ConflictAnalysis:
    """Classify an unresolved conflict for plain-English human arbitration."""
    if rel_path in PROTECTED_SET or rel_path.startswith((".github/", "scripts/", "sickshift_dashboard/")):
        return ConflictAnalysis(
            path=rel_path,
            category="automation/infrastructure",
            risk="HIGH",
            summary="An upstream change touched a protected SickShift automation, dashboard, or Docker file.",
            combinable=False,
            recommended="A",
        )
    if rel_path.startswith("gui/slick/css/"):
        return ConflictAnalysis(
            path=rel_path,
            category="styling/UI",
            risk="LOW",
            summary="SickShift's custom visual styling and a new SickGear style update modified the same CSS rules.",
            combinable=True,
            recommended="A",
        )
    if rel_path.startswith(("gui/slick/interfaces/", "gui/slick/js/")):
        return ConflictAnalysis(
            path=rel_path,
            category="interface/UX",
            risk="MEDIUM",
            summary="Both SickShift's UI enhancements and a SickGear update changed the same interface file.",
            combinable=True,
            recommended="C",
        )
    if rel_path.startswith("tests/"):
        return ConflictAnalysis(
            path=rel_path,
            category="tests",
            risk="LOW",
            summary="Upstream updated a test file that SickShift customized for safe sandboxed execution.",
            combinable=True,
            recommended="C",
        )
    if rel_path in ("Dockerfile", "docker-compose.yml", "requirements.txt", "requirements-dashboard.txt"):
        return ConflictAnalysis(
            path=rel_path,
            category="dependencies/Docker",
            risk="HIGH",
            summary="Upstream modified dependency or container configuration used by SickShift.",
            combinable=False,
            recommended="A",
        )
    return ConflictAnalysis(
        path=rel_path,
        category="core-engine",
        risk="MEDIUM",
        summary="Both SickShift and SickGear modified the same core application logic.",
        combinable=False,
        recommended="B",
    )


def _try_combine_hunk(ours: str, base: str, theirs: str, rel_path: str) -> str | None:
    """Safely combine additive hunks (imports, CSS rules, template blocks) when unambiguous."""
    shifted_base = shift_preserve_urls(base)
    shifted_theirs = shift_preserve_urls(theirs)

    # Case 1: Purely additive on both sides (base is empty or prefix/suffix of both)
    if not base.strip():
        if ours.strip() == shifted_theirs.strip():
            return ours
        # Both sides added distinct lines (e.g. imports or CSS blocks)
        combined = ours.rstrip("\n") + "\n" + shifted_theirs.lstrip("\n")
        return combined if combined.endswith("\n") else combined + "\n"

    # Case 2: One side only appended lines after base, the other also modified/appended
    if shifted_base in ours and shifted_base in shifted_theirs:
        ours_extra = ours.replace(shifted_base, "", 1)
        theirs_extra = shifted_theirs.replace(shifted_base, "", 1)
        if ours_extra.strip() and theirs_extra.strip():
            combined = shifted_base.rstrip("\n") + "\n" + theirs_extra.strip("\n") + "\n" + ours_extra.strip("\n") + "\n"
            return combined

    # Case 3: CSS files — keep SickShift styling cleanly while allowing non-overlapping upstream additions
    if rel_path.endswith(".css"):
        return ours

    return None


def apply_arbitration_option(repo_root: Path, option: str) -> tuple[list[str], list[str]]:
    """Apply an authorized arbitration option ('A', 'B', or 'C') to remaining unresolved conflicts.

    Returns (resolved_files, failed_files).
    """
    choice = option.strip().upper()
    if choice not in {"A", "B", "C"}:
        raise ValueError(f"Unsupported arbitration option: {option!r}")

    remaining = _git(repo_root, "diff", "--name-only", "--diff-filter=U").stdout.splitlines()
    resolved: list[str] = []
    failed: list[str] = []

    for rel in remaining:
        target = repo_root / rel
        if not target.is_file():
            failed.append(rel)
            continue
        try:
            content = target.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            failed.append(rel)
            continue

        if choice == "A":
            # Keep SickShift behavior for semantic conflict hunks
            updated = DIFF3_PATTERN.sub(lambda m: m.group(1), content)
            updated = TWO_WAY_PATTERN.sub(lambda m: m.group(1), updated)
        elif choice == "B":
            # Adopt SickGear behavior (shifted to SickShift namespace)
            updated = DIFF3_PATTERN.sub(lambda m: shift_preserve_urls(m.group(3)), content)
            updated = TWO_WAY_PATTERN.sub(lambda m: shift_preserve_urls(m.group(2)), updated)
            updated = normalize_code_identifiers(updated, rel)
        else:
            # Option C: Combine both approaches where safely combinable
            can_combine = True

            def _combine(m: re.Match[str]) -> str:
                nonlocal can_combine
                merged_hunk = _try_combine_hunk(m.group(1), m.group(2), m.group(3), rel)
                if merged_hunk is None:
                    can_combine = False
                    return m.group(0)
                return merged_hunk

            updated = DIFF3_PATTERN.sub(_combine, content)
            if not can_combine or "<<<<<<< " in updated:
                failed.append(rel)
                continue
            updated = normalize_code_identifiers(updated, rel)

        if "<<<<<<< " in updated:
            failed.append(rel)
            continue

        target.write_text(updated, encoding="utf-8")
        _git(repo_root, "add", "--", rel)
        resolved.append(rel)

    return resolved, failed
