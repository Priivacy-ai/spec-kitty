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

_SCANNABLE_SUFFIXES: frozenset[str] = frozenset({".md", ".yaml", ".yml", ".txt", ".j2"})
# Segment names that disqualify a file (checked against each path component, not the full path)
_SKIP_SEGMENTS: frozenset[str] = frozenset({"__pycache__", ".worktrees"})
# Suffix-level skips (applied to the filename)
_SKIP_SUFFIXES: frozenset[str] = frozenset({".pyc"})


@dataclass(frozen=True)
class _CompiledTerm:
    term_id: str
    kind: str  # "literal" | "regex"
    pattern: str
    compiled: re.Pattern[str] | None  # None for literal


def _is_glob_pattern(path_spec: str) -> bool:
    """Return True when the allowlist entry uses glob syntax."""
    return any(char in path_spec for char in "*?[")


def _load_banned_terms(path: Path) -> list[_CompiledTerm]:
    """Load and compile banned terms from YAML. Raises ValueError on bad regex."""
    raw = _YAML.load(path) or {}
    terms: list[_CompiledTerm] = []
    for entry in raw.get("terms", []):
        term_id: str = entry["id"]
        kind: str = entry["kind"]
        pattern: str = entry["pattern"]
        compiled: re.Pattern[str] | None = None
        if kind == "regex":
            try:
                compiled = re.compile(pattern, re.MULTILINE)
            except re.error as exc:
                raise ValueError(f"Banned term {term_id!r} has invalid regex pattern {pattern!r}: {exc}") from exc
        terms.append(_CompiledTerm(term_id=term_id, kind=kind, pattern=pattern, compiled=compiled))
    return terms


def _load_allowlist(path: Path) -> list[str]:
    """Return raw path strings from the allowlist YAML."""
    raw = _YAML.load(path) or {}
    return [entry["path"] for entry in raw.get("paths", [])]


def _is_allowlisted(repo_relative: str, allowlist: list[str]) -> bool:
    """Return True if repo_relative matches any allowlist entry (literal or glob)."""
    for entry in allowlist:
        # Glob entries contain wildcards; literals are exact matches.
        if _is_glob_pattern(entry):
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
        if _is_glob_pattern(entry):
            matches = list(repo_root.glob(entry))
            if not matches:
                stale.append(entry)
        else:
            if not (repo_root / entry).exists():
                stale.append(entry)
    return stale


def _relative_parts(path: Path, root: Path) -> tuple[str, ...]:
    """Return path parts relative to root when possible."""
    try:
        return path.relative_to(root).parts
    except ValueError:
        return path.parts


def _should_skip(path: Path, root: Path) -> bool:
    """Return True if path should be excluded from scanning.

    Checks only the parts *relative to root* so that skip-segments embedded
    in the root path itself (e.g. ``.worktrees``) do not disqualify valid
    scan targets.
    """
    for part in _relative_parts(path, root):
        if part in _SKIP_SEGMENTS:
            return True
    return path.suffix in _SKIP_SUFFIXES


def _iter_root_files(root: Path) -> list[Path]:
    """Collect scannable files under one root."""
    if not root.exists():
        return []
    if root.is_file():
        if root.suffix in _SCANNABLE_SUFFIXES and not _should_skip(root, root.parent):
            return [root]
        return []

    found: list[Path] = []
    for suffix in _SCANNABLE_SUFFIXES:
        for path in root.rglob(f"*{suffix}"):
            if path.is_file() and not _should_skip(path, root):
                found.append(path)
    return found


def _dedupe_paths(paths: list[Path]) -> list[Path]:
    """Deduplicate paths while preserving insertion order."""
    seen: set[Path] = set()
    unique: list[Path] = []
    for path in paths:
        if path not in seen:
            seen.add(path)
            unique.append(path)
    return unique


def _iter_scannable_files(roots: list[Path]) -> list[Path]:
    """Return all scannable files from the given scan roots (deduped, stable order)."""
    found: list[Path] = []
    for root in roots:
        found.extend(_iter_root_files(root))
    return _dedupe_paths(found)


def _make_hit(
    repo_relative: Path,
    lineno: int,
    column: int,
    term: _CompiledTerm,
    match: str,
) -> BannedTermHit:
    """Build a banned-term hit with shared metadata."""
    return BannedTermHit(
        file=repo_relative,
        line=lineno,
        column=column,
        term_id=term.term_id,
        match=match,
    )


def _scan_literal_matches(
    repo_relative: Path,
    lineno: int,
    line_text: str,
    term: _CompiledTerm,
) -> list[BannedTermHit]:
    """Return all literal matches for one term on one line."""
    hits: list[BannedTermHit] = []
    idx = 0
    while True:
        pos = line_text.find(term.pattern, idx)
        if pos == -1:
            return hits
        hits.append(_make_hit(repo_relative, lineno, pos + 1, term, term.pattern))
        idx = pos + len(term.pattern)


def _scan_regex_matches(
    repo_relative: Path,
    lineno: int,
    line_text: str,
    term: _CompiledTerm,
) -> list[BannedTermHit]:
    """Return all regex matches for one term on one line."""
    assert term.compiled is not None
    return [_make_hit(repo_relative, lineno, match.start() + 1, term, match.group(0)) for match in term.compiled.finditer(line_text)]


def _scan_line(
    repo_relative: Path,
    lineno: int,
    line_text: str,
    terms: list[_CompiledTerm],
) -> list[BannedTermHit]:
    """Return all banned-term hits for one line."""
    hits: list[BannedTermHit] = []
    for term in terms:
        if term.kind == "literal":
            hits.extend(_scan_literal_matches(repo_relative, lineno, line_text, term))
        else:
            hits.extend(_scan_regex_matches(repo_relative, lineno, line_text, term))
    return hits


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
    for lineno, line_text in enumerate(content.splitlines(), start=1):
        hits.extend(_scan_line(repo_relative, lineno, line_text, terms))
    return hits


def _iter_charter_scan_roots(charter_root: Path) -> list[Path]:
    """Return eligible charter scan roots, excluding neutrality internals."""
    if not charter_root.exists():
        return []

    roots: list[Path] = []
    for child in charter_root.iterdir():
        if child.name == "neutrality":
            continue
        if child.is_dir() or (child.is_file() and child.suffix in _SCANNABLE_SUFFIXES):
            roots.append(child)
    return roots


def _iter_mission_scan_roots(missions_root: Path) -> list[Path]:
    """Return mission prompt/template and mission.yaml scan roots."""
    if not missions_root.exists():
        return []

    roots: list[Path] = []
    for mission_dir in missions_root.iterdir():
        if not mission_dir.is_dir():
            continue
        command_templates = mission_dir / "command-templates"
        templates = mission_dir / "templates"
        mission_manifest = mission_dir / "mission.yaml"
        if command_templates.exists():
            roots.append(command_templates)
        if templates.exists():
            roots.append(templates)
        if mission_manifest.exists():
            roots.append(mission_manifest)
    return roots


def _default_scan_roots(repo_root: Path) -> list[Path]:
    """Return default scan roots per contract C-3."""
    roots: list[Path] = [repo_root / "src" / "doctrine"]
    roots.extend(_iter_charter_scan_roots(repo_root / "src" / "charter"))
    roots.extend(_iter_mission_scan_roots(repo_root / "src" / "specify_cli" / "missions"))
    return roots


def _find_repo_root(start: Path) -> Path:
    """Find the repository root by walking upward for pyproject.toml."""
    for parent in [start, *start.parents]:
        if (parent / "pyproject.toml").exists():
            return parent
    return Path.cwd()


def _resolve_scan_settings(
    repo_root: Path | None,
    scan_roots: list[Path] | None,
    banned_terms_path: Path | None,
    allowlist_path: Path | None,
) -> tuple[Path, list[Path], Path, Path]:
    """Resolve repo-root, scan-roots, and config paths."""
    effective_repo_root = repo_root or _find_repo_root(Path(__file__).resolve().parent)
    this_dir = Path(__file__).resolve().parent
    effective_banned_terms_path = banned_terms_path or (this_dir / "banned_terms.yaml")
    effective_allowlist_path = allowlist_path or (this_dir / "language_scoped_allowlist.yaml")
    effective_roots = scan_roots or _default_scan_roots(effective_repo_root)
    return (
        effective_repo_root,
        effective_roots,
        effective_banned_terms_path,
        effective_allowlist_path,
    )


def _repo_relative_string(file_path: Path, repo_root: Path) -> str:
    """Return a stable repo-relative string, even for override roots outside the repo."""
    try:
        return file_path.relative_to(repo_root).as_posix()
    except ValueError:
        return file_path.as_posix()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_neutrality_lint(
    *,
    repo_root: Path | None = None,
    scan_roots: list[Path] | None = None,
    banned_terms_path: Path | None = None,
    allowlist_path: Path | None = None,
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
    repo_root, effective_roots, banned_terms_path, allowlist_path = _resolve_scan_settings(
        repo_root,
        scan_roots,
        banned_terms_path,
        allowlist_path,
    )

    # Load configuration (compile regexes once)
    terms = _load_banned_terms(banned_terms_path)
    allowlist_paths = _load_allowlist(allowlist_path)

    # Check for stale allowlist entries
    stale = _check_stale(repo_root, allowlist_paths)

    # Collect files
    all_files = _iter_scannable_files(effective_roots)

    # Scan files
    all_hits: list[BannedTermHit] = []
    scanned = 0
    for file_path in all_files:
        scanned += 1
        repo_relative_str = _repo_relative_string(file_path, repo_root)
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
