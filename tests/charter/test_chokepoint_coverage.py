"""AST-walk coverage test: every reader of the v1.0.0 manifest derivatives
routes through the ``ensure_charter_bundle_fresh`` chokepoint (FR-016).

This test enforces the architectural invariant that no live reader of
``governance.yaml`` / ``directives.yaml`` / ``metadata.yaml`` at
``.kittify/charter/*`` bypasses the chokepoint. It walks every ``.py``
file under ``src/`` with ``ast`` and flags any function that either:

  * Reads a manifest derivative via a literal file path (``"governance.yaml"``,
    ``"directives.yaml"``, ``"metadata.yaml"``), OR
  * Calls ``load_governance_config`` / ``load_directives_config``
    directly (these functions already route through the chokepoint, so
    callers are transitively covered).

For each reader site the test asserts that the file as a whole imports
``ensure_charter_bundle_fresh`` (or re-exports it / calls a delegating
wrapper that does). The carve-out list is explicit and narrow:

  * ``src/charter/sync.py`` — the chokepoint IS defined here.
  * ``src/charter/bundle.py`` — manifest definition only.
  * ``src/charter/resolution.py`` — canonical-root resolver, called by
    the chokepoint.
  * ``src/charter/compiler.py`` — references.yaml pipeline (C-012).
  * ``src/charter/context.py`` lines 385-398 — context-state.json write
    region (C-012). The rest of the file IS in scope and flips through
    the chokepoint.
  * ``src/specify_cli/upgrade/migrations/m_3_2_3_unified_bundle.py`` —
    bootstrap migration (future).
  * ``src/charter/extractor.py``
    — producers of governance/directives/metadata.yaml; they WRITE, not
    READ, those files.
  * ``src/charter/hasher.py`` — metadata.yaml consumer used by the chokepoint itself.
  * ``src/charter/schemas.py`` — only string constants for YAML filenames.

See ``kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/contracts/chokepoint.contract.md``
for the architectural contract.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.fast


_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC_ROOT = _REPO_ROOT / "src"


# Files permitted to directly read/write manifest derivatives without
# routing through ``ensure_charter_bundle_fresh``. Paths are relative to
# the repo root.
_CARVE_OUTS: frozenset[str] = frozenset(
    {
        # Chokepoint + its dependencies
        "src/charter/sync.py",
        "src/charter/bundle.py",
        "src/charter/resolution.py",
        # Producers (they WRITE, not read manifest derivatives)
        "src/charter/extractor.py",
        # Compiler pipeline (C-012 — references.yaml, out of v1.0.0 scope)
        "src/charter/compiler.py",
        # metadata.yaml hash-reader used by the chokepoint itself
        "src/charter/hasher.py",
        # Schema definitions — string literals only
        "src/charter/schemas.py",
        # Future bootstrap migration
        "src/specify_cli/upgrade/migrations/m_3_2_3_unified_bundle.py",
    }
)

# Literal tokens that indicate a direct read of a v1.0.0 derivative.
_DERIVATIVE_FILENAMES: frozenset[str] = frozenset(
    {"governance.yaml", "directives.yaml", "metadata.yaml"}
)

# Function calls whose presence implies a reader site.
_CHOKEPOINT_READER_CALLS: frozenset[str] = frozenset(
    {"load_governance_config", "load_directives_config"}
)

# The chokepoint symbol whose presence (imported or called) in a file
# proves that file routes through the chokepoint.
_CHOKEPOINT_SYMBOL = "ensure_charter_bundle_fresh"


def _iter_src_files() -> list[Path]:
    """Yield every .py file under src/, excluding __pycache__ + byte-identical twins."""
    files: list[Path] = []
    for path in _SRC_ROOT.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        files.append(path)
    return files


def _rel(path: Path) -> str:
    return str(path.relative_to(_REPO_ROOT))


def _source_mentions_charter_dir(source: str) -> bool:
    """Heuristic: the file references the charter sub-directory in some form.

    A literal ``"metadata.yaml"`` token is ambiguous because spec-kitty
    also maintains a top-level ``.kittify/metadata.yaml`` for project
    bookkeeping. Only hits where the enclosing file mentions the charter
    sub-directory (via ``".kittify/charter"`` or ``"charter"`` as a Path
    segment) are treated as v1.0.0-derivative reads for coverage.
    """
    return (
        ".kittify/charter" in source
        or '"charter"' in source
        or "'charter'" in source
        or "_CHARTER_DIRNAME" in source
    )


def _find_derivative_reader_calls(tree: ast.Module, source: str) -> list[tuple[int, str]]:
    """Return (lineno, reason) for every apparent manifest-derivative read.

    Reasons:
      * ``"literal:<filename>"`` — a string literal matching a derivative,
        only emitted when the enclosing file also references the charter
        sub-directory (to avoid confusing ``.kittify/charter/metadata.yaml``
        with the distinct ``.kittify/metadata.yaml`` project-level file).
      * ``"call:<func_name>"`` — a call to a chokepoint-fronted loader.

    The caller owns carve-out filtering; this function reports raw hits.
    """
    hits: list[tuple[int, str]] = []
    is_charter_context = _source_mentions_charter_dir(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if node.value in _DERIVATIVE_FILENAMES and is_charter_context:
                hits.append((node.lineno, f"literal:{node.value}"))
        elif isinstance(node, ast.Call):
            func = node.func
            name: str | None = None
            if isinstance(func, ast.Name):
                name = func.id
            elif isinstance(func, ast.Attribute):
                name = func.attr
            if name in _CHOKEPOINT_READER_CALLS:
                hits.append((node.lineno, f"call:{name}"))
    return hits


def _file_routes_through_chokepoint(source: str) -> bool:
    """True iff the file imports/calls the chokepoint directly, OR calls
    a loader that already routes through it.

    ``load_governance_config`` and ``load_directives_config`` (defined in
    ``src/charter/sync.py``) invoke ``ensure_charter_bundle_fresh`` at
    their function head. Callers of those loaders are therefore
    transitively chokepoint-routed and do NOT need to import the
    chokepoint symbol directly.
    """
    if _CHOKEPOINT_SYMBOL in source:
        return True
    # Transitively-routed loader calls satisfy the chokepoint requirement.
    return any(loader in source for loader in _CHOKEPOINT_READER_CALLS)


def test_every_manifest_reader_routes_through_chokepoint() -> None:
    """AST-walk assertion: no source file outside the carve-out list may
    read ``governance.yaml`` / ``directives.yaml`` / ``metadata.yaml`` or
    call the chokepoint-fronted loaders without also importing/calling
    ``ensure_charter_bundle_fresh`` (directly or via re-export).
    """
    violations: list[tuple[str, int, str]] = []

    for file_path in _iter_src_files():
        rel = _rel(file_path)
        if rel in _CARVE_OUTS:
            continue

        source = file_path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source, filename=rel)
        except SyntaxError:  # pragma: no cover — malformed source is a bigger bug
            continue

        hits = _find_derivative_reader_calls(tree, source)
        if not hits:
            continue

        # For context.py, permit hits in the C-012 carve-out region
        # (lines 385-398) for context-state.json writes — but note that
        # region doesn't read manifest derivatives, so this is defensive.
        if rel == "src/charter/context.py":
            hits = [(lineno, reason) for lineno, reason in hits if not (385 <= lineno <= 398)]
            if not hits:
                continue

        if not _file_routes_through_chokepoint(source):
            for lineno, reason in hits:
                violations.append((rel, lineno, reason))

    if violations:
        lines = [f"  {rel}:{lineno} — {reason}" for rel, lineno, reason in violations]
        pytest.fail(
            "The following files read v1.0.0 manifest derivatives but do "
            "not route through ``ensure_charter_bundle_fresh``:\n" + "\n".join(lines)
        )


def test_carve_out_files_exist() -> None:
    """Carve-outs must point at real files. A stale carve-out entry
    masks a newly-introduced reader that would otherwise be flagged.
    """
    missing = [rel for rel in _CARVE_OUTS if not (_REPO_ROOT / rel).exists()]
    # m_3_2_3_unified_bundle.py is forward-looking; tolerate its absence.
    missing = [rel for rel in missing if "m_3_2_3_unified_bundle" not in rel]
    assert not missing, f"Carve-out entries reference missing files: {missing}"


def test_chokepoint_symbol_is_defined_in_charter_sync() -> None:
    """The chokepoint function must be defined in ``src/charter/sync.py``.
    If this test fails, the chokepoint has been moved or renamed without
    updating this coverage test.
    """
    sync_src = (_SRC_ROOT / "charter" / "sync.py").read_text(encoding="utf-8")
    tree = ast.parse(sync_src)
    fnames = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    assert _CHOKEPOINT_SYMBOL in fnames, (
        f"{_CHOKEPOINT_SYMBOL} not defined in src/charter/sync.py"
    )
