"""Neutrality lint scanner for charter/doctrine artifacts.

Scans configured roots for banned language-specific terms in generic-scoped files.
Language-scoped files listed in ``language_scoped_allowlist.yaml`` are exempt.

Contracts:
  - C-3  src/charter/neutrality/banned_terms.yaml (banned terms schema)
  - C-4  contracts/banned-terms-schema.yaml
  - C-5  contracts/language-scoped-allowlist-schema.yaml

Mission: charter-ownership-consolidation-and-neutrality-hardening-01KPD880
"""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ruamel.yaml import YAML


# ---------------------------------------------------------------------------
# Public data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BannedTermHit:
    """A single banned-term match found in a scanned file."""

    file: Path  # repo-relative path
    line: int  # 1-indexed
    column: int  # 1-indexed
    term_id: str  # e.g. "PY-001"
    match: str  # the actual matched text


@dataclass(frozen=True)
class NeutralityLintResult:
    """Aggregated result from ``run_neutrality_lint``."""

    hits: tuple[BannedTermHit, ...]
    stale_allowlist_entries: tuple[str, ...]  # paths that resolve to zero files
    scanned_file_count: int
    banned_term_count: int
    allowlisted_path_count: int

    @property
    def passed(self) -> bool:
        """True iff there are no hits and no stale allowlist entries."""
        return not self.hits and not self.stale_allowlist_entries


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_YAML = YAML(typ="safe")

_SCANNABLE_SUFFIXES: frozenset[str] = frozenset(
    {".md", ".yaml", ".yml", ".txt", ".j2"}
)
# Segment names that disqualify a file (checked against each path component, not the full path)
_SKIP_SEGMENTS: frozenset[str] = frozenset({"__pycache__", ".worktrees"})
# Suffix-level skips (applied to the filename)
_SKIP_SUFFIXES: frozenset[str] = frozenset({".pyc"})


@dataclass(frozen=True)
class _CompiledTerm:
    term_id: str
    kind: str  # "literal" | "regex"
    pattern: str
    compiled: Optional[re.Pattern[str]]  # None for literal


def _load_banned_terms(path: Path) -> list[_CompiledTerm]:
    """Load and compile banned terms from YAML. Raises ValueError on bad regex."""
    raw = _YAML.load(path)
    terms: list[_CompiledTerm] = []
    for entry in raw.get("terms", []):
        term_id: str = entry["id"]
        kind: str = entry["kind"]
        pattern: str = entry["pattern"]
        compiled: Optional[re.Pattern[str]] = None
        if kind == "regex":
            try:
                compiled = re.compile(pattern, re.MULTILINE)
            except re.error as exc:
                raise ValueError(
                    f"Banned term {term_id!r} has invalid regex pattern {pattern!r}: {exc}"
                ) from exc
        terms.append(_CompiledTerm(term_id=term_id, kind=kind, pattern=pattern, compiled=compiled))
    return terms


def _load_allowlist(path: Path) -> list[str]:
    """Return raw path strings from the allowlist YAML."""
    raw = _YAML.load(path)
    return [entry["path"] for entry in raw.get("paths", [])]


def _is_allowlisted(repo_relative: str, allowlist: list[str]) -> bool:
    """Return True if repo_relative matches any allowlist entry (literal or glob)."""
    for entry in allowlist:
        # Glob entries contain wildcards; literals are exact matches.
        if "*" in entry or "?" in entry or "[" in entry:
            if fnmatch.fnmatchcase(repo_relative, entry):
                return True
        else:
            if repo_relative == entry:
                return True
    return False


def _check_stale(repo_root: Path, allowlist_paths: list[str]) -> list[str]:
    """Return allowlist path strings that resolve to zero files."""
    stale: list[str] = []
    for entry in allowlist_paths:
        if "*" in entry or "?" in entry or "[" in entry:
            matches = list(repo_root.glob(entry))
            if not matches:
                stale.append(entry)
        else:
            if not (repo_root / entry).exists():
                stale.append(entry)
    return stale


def _should_skip(path: Path, root: Path) -> bool:
    """Return True if path should be excluded from scanning.

    Checks only the parts *relative to root* so that skip-segments embedded
    in the root path itself (e.g. ``.worktrees``) do not disqualify valid
    scan targets.
    """
    try:
        rel_parts = path.relative_to(root).parts
    except ValueError:
        # path is not inside root — use all parts
        rel_parts = path.parts
    for part in rel_parts:
        if part in _SKIP_SEGMENTS:
            return True
    if path.suffix in _SKIP_SUFFIXES:
        return True
    return False


def _iter_scannable_files(roots: list[Path]) -> list[Path]:
    """Return all scannable files from the given scan roots (deduped, stable order)."""
    found: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        if root.is_file():
            # Single-file roots (e.g. mission.yaml)
            if root.suffix in _SCANNABLE_SUFFIXES and not _should_skip(root, root.parent):
                found.append(root)
        else:
            # Directory roots — descend recursively by suffix
            for suffix in _SCANNABLE_SUFFIXES:
                for path in root.rglob(f"*{suffix}"):
                    if path.is_file() and not _should_skip(path, root):
                        found.append(path)

    # Deduplicate while preserving insertion order
    seen: set[Path] = set()
    unique: list[Path] = []
    for p in found:
        if p not in seen:
            seen.add(p)
            unique.append(p)
    return unique


def _scan_file(
    path: Path,
    repo_root: Path,
    terms: list[_CompiledTerm],
) -> list[BannedTermHit]:
    """Scan a single file for all banned terms; return hits."""
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    repo_relative = path.relative_to(repo_root)
    hits: list[BannedTermHit] = []
    lines = content.splitlines()

    for lineno, line_text in enumerate(lines, start=1):
        for term in terms:
            if term.kind == "literal":
                idx = 0
                while True:
                    pos = line_text.find(term.pattern, idx)
                    if pos == -1:
                        break
                    hits.append(
                        BannedTermHit(
                            file=repo_relative,
                            line=lineno,
                            column=pos + 1,
                            term_id=term.term_id,
                            match=term.pattern,
                        )
                    )
                    idx = pos + len(term.pattern)
            else:
                # regex
                assert term.compiled is not None
                for m in term.compiled.finditer(line_text):
                    hits.append(
                        BannedTermHit(
                            file=repo_relative,
                            line=lineno,
                            column=m.start() + 1,
                            term_id=term.term_id,
                            match=m.group(0),
                        )
                    )
    return hits


def _default_scan_roots(repo_root: Path) -> list[Path]:
    """Return default scan roots per contract C-3."""
    roots: list[Path] = [
        repo_root / "src" / "doctrine",
    ]

    # src/charter/ excluding src/charter/neutrality/ itself
    charter_root = repo_root / "src" / "charter"
    if charter_root.exists():
        for child in charter_root.iterdir():
            if child.name != "neutrality" and child.is_dir():
                roots.append(child)
            elif child.is_file() and child.suffix in _SCANNABLE_SUFFIXES:
                roots.append(child)

    # src/specify_cli/missions/*/command-templates/ and mission.yaml
    missions_root = repo_root / "src" / "specify_cli" / "missions"
    if missions_root.exists():
        for mission_dir in missions_root.iterdir():
            if not mission_dir.is_dir():
                continue
            ct = mission_dir / "command-templates"
            if ct.exists():
                roots.append(ct)
            my = mission_dir / "mission.yaml"
            if my.exists():
                roots.append(my)

    # .kittify/charter/ if present
    kittify_charter = repo_root / ".kittify" / "charter"
    if kittify_charter.exists():
        roots.append(kittify_charter)

    return roots


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_neutrality_lint(
    *,
    repo_root: Optional[Path] = None,
    scan_roots: Optional[list[Path]] = None,
    banned_terms_path: Optional[Path] = None,
    allowlist_path: Optional[Path] = None,
) -> NeutralityLintResult:
    """Run the neutrality lint scanner.

    Args:
        repo_root: Root of the repository. Defaults to the directory containing
            ``pyproject.toml`` searched upward from this file's location.
        scan_roots: Override the default scan roots. When provided, the scanner
            only traverses these paths (used by fault-injection tests).
        banned_terms_path: Override the path to ``banned_terms.yaml``.
        allowlist_path: Override the path to ``language_scoped_allowlist.yaml``.

    Returns:
        A :class:`NeutralityLintResult` describing hits, stale entries, and counts.
    """
    if repo_root is None:
        # Walk up from this file to find pyproject.toml
        here = Path(__file__).resolve().parent
        for parent in [here, *here.parents]:
            if (parent / "pyproject.toml").exists():
                repo_root = parent
                break
        if repo_root is None:
            repo_root = Path.cwd()

    this_dir = Path(__file__).resolve().parent
    if banned_terms_path is None:
        banned_terms_path = this_dir / "banned_terms.yaml"
    if allowlist_path is None:
        allowlist_path = this_dir / "language_scoped_allowlist.yaml"

    # Load configuration (compile regexes once)
    terms = _load_banned_terms(banned_terms_path)
    allowlist_paths = _load_allowlist(allowlist_path)

    # Check for stale allowlist entries
    stale = _check_stale(repo_root, allowlist_paths)

    # Determine scan roots
    if scan_roots is None:
        effective_roots = _default_scan_roots(repo_root)
    else:
        effective_roots = scan_roots

    # Collect files
    all_files = _iter_scannable_files(effective_roots)

    # Scan files
    all_hits: list[BannedTermHit] = []
    scanned = 0
    for file_path in all_files:
        scanned += 1
        try:
            repo_relative_str = file_path.relative_to(repo_root).as_posix()
        except ValueError:
            # scan_roots override may be outside repo_root (e.g. tmp_path in tests)
            repo_relative_str = file_path.as_posix()

        if _is_allowlisted(repo_relative_str, allowlist_paths):
            continue
        hits = _scan_file(file_path, repo_root, terms)
        all_hits.extend(hits)

    return NeutralityLintResult(
        hits=tuple(all_hits),
        stale_allowlist_entries=tuple(stale),
        scanned_file_count=scanned,
        banned_term_count=len(terms),
        allowlisted_path_count=len(allowlist_paths),
    )
