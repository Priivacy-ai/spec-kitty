"""Architectural guard: dossier emitters must never be called positionally.

This mission (``legacy-cleanup-split-dossier-queue-migration-01M0MGHB``,
FR-008) closes the defect class PR #1056 had to patch around by hand:
``emit_snapshot_computed`` and its siblings drifted their positional
parameter order out from under a caller that still passed bare positional
arguments, and the mismatch was silent until runtime. WP01 promoted every
dossier-emitter parameter to keyword-only at the call sites this repo
controls, but nothing *enforced* that shape — a future edit could reintroduce
a positional call and nothing would catch it until the next drift incident.
This guard closes that gap by construction (spec.md User Story 3): it fails
CI if any production code under ``src/`` calls ``emit_artifact_indexed``,
``emit_artifact_missing``, ``emit_snapshot_computed``, or
``emit_parity_drift_detected`` with a positional argument.

**What this guard covers**: every ``*.py`` file under ``src/`` (production
code only), scanned via ``ast.parse()`` for ``ast.Call`` nodes whose callee
is a simple ``Name`` (module-level function call, e.g. ``emit_x(...)``)
matching one of the four dossier-emitter names, flagged when
``node.args`` (positional arguments) is non-empty.

**What this guard deliberately does NOT cover** (spec.md's own design scope,
matching the emitters' actual usage pattern — no aliasing/re-export exists
in ``src/`` today):

- ``tests/`` and any other non-``src/`` path (test fixtures may legitimately
  construct throwaway positional calls to exercise error paths; policing
  them is out of scope and would be a false-positive risk for no benefit).
- Attribute-chain calls (``module.emit_artifact_indexed(...)``) — the four
  emitters are always called as bare module-level names in ``src/`` today,
  never via a qualified attribute access, so this guard does simple
  ``Name``-based matching only, not full call-graph/import resolution.
- Aliased imports (``from ... import emit_artifact_indexed as ei``) — an
  alias would not match the name set and would silently escape detection;
  none exist in ``src/`` today (spec.md's own readiness probe verified
  this), so widening the detector to handle aliasing is explicitly deferred
  until a real aliased call site exists.

Modeled directly on this repo's own established AST-guard idiom:
``tests/architectural/test_shared_package_boundary.py``'s
``_forbidden_imports()`` + planted-violation positive-control pattern.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.architectural

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC = _REPO_ROOT / "src"

# The four dossier emitters this guard protects (spec.md FR-008 / User
# Story 3). Simple module-level function names — no attribute-chain
# resolution needed, per spec.md's own detector-design scope.
_GUARDED_EMITTERS: frozenset[str] = frozenset(
    {
        "emit_artifact_indexed",
        "emit_artifact_missing",
        "emit_snapshot_computed",
        "emit_parity_drift_detected",
    }
)


class PositionalCallViolation:
    """One detected positional call to a guarded dossier emitter."""

    __slots__ = ("path", "lineno", "func_name")

    def __init__(self, path: Path, lineno: int, func_name: str) -> None:
        self.path = path
        self.lineno = lineno
        self.func_name = func_name

    def __repr__(self) -> str:  # pragma: no cover - debug aid only
        return f"{self.path}:{self.lineno}:{self.func_name}"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PositionalCallViolation):
            return NotImplemented
        return (self.path, self.lineno, self.func_name) == (
            other.path,
            other.lineno,
            other.func_name,
        )


def _call_target_name(node: ast.Call) -> str | None:
    """Return the simple callee name of *node*, or ``None`` if not a bare Name call."""
    if isinstance(node.func, ast.Name):
        return node.func.id
    return None


def _violations_in_tree(tree: ast.AST, path: Path) -> list[PositionalCallViolation]:
    """Return every guarded-emitter positional call found in *tree*."""
    found: list[PositionalCallViolation] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _call_target_name(node)
        if name not in _GUARDED_EMITTERS:
            continue
        if node.args:
            found.append(PositionalCallViolation(path, node.lineno, name))
    return found


def _find_positional_emitter_calls(roots: tuple[Path, ...]) -> list[PositionalCallViolation]:
    """Walk every ``*.py`` file under *roots* and report positional-call violations.

    Mirrors ``test_shared_package_boundary.py``'s ``_forbidden_imports()``
    shape: accepts a tuple of file-or-directory roots (so the same function
    serves both the real ``src/`` scan and a single planted-fixture-file
    scan), parses each file with ``ast.parse()``, and returns a structured
    list of violations rather than raising — callers decide what "zero
    violations" or "exactly one violation" means for their assertion.
    """
    violations: list[PositionalCallViolation] = []
    for root in roots:
        paths = [root] if root.is_file() else sorted(root.rglob("*.py"))
        for path in paths:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            violations.extend(_violations_in_tree(tree, path))
    return violations


def test_src_tree_has_no_positional_dossier_emitter_calls() -> None:
    """Clean-tree assertion (T015): the real, unmodified ``src/`` tree is clean.

    All 5 verified real call sites (``sync/dossier_pipeline.py`` lines
    101/126/175/230 and ``dossier/drift_detector.py`` line 419) are already
    100% keyword-argument as of WP01/WP02 — this is expected to pass on day
    one and to keep passing through this mission's own remaining changes.
    A failure here means either a false positive in the detector (most
    likely: an unrelated function coincidentally sharing one of these four
    names) or a genuine mission regression reintroducing a positional call —
    both require investigation before proceeding, never a silent `# noqa`.
    """
    assert _SRC.is_dir()
    assert sum(1 for _ in _SRC.rglob("*.py")) > 0
    assert _find_positional_emitter_calls((_SRC,)) == []


def test_detector_flags_planted_positional_call(tmp_path: Path) -> None:
    """Positive-control (T016): prove the detector actually fires.

    Per the charter's "a gate-unmask cannot self-validate" rule and spec.md's
    own explicit self-mutation requirement (User Story 3's Independent Test
    and Acceptance Scenario 3): a guard that passes only because nothing in
    ``src/`` happens to trip it is not coverage. This plants a synthetic
    positional call — spec.md's own example,
    ``emit_artifact_indexed("m", "k", "c", "p", "h", 1)`` (six bare
    positional arguments) — into a throwaway fixture file and asserts the
    detector reports exactly one violation identifying that exact call. This
    test IS the guard's red-first proof: reverting/gutting the detector to
    always return "no violations" makes this assertion fail.
    """
    planted = tmp_path / "planted.py"
    planted.write_text(
        'result = emit_artifact_indexed("m", "k", "c", "p", "h", 1)\n',
        encoding="utf-8",
    )

    violations = _find_positional_emitter_calls((planted,))

    assert len(violations) == 1
    (violation,) = violations
    assert violation.path == planted
    assert violation.lineno == 1
    assert violation.func_name == "emit_artifact_indexed"


def test_detector_does_not_flag_keyword_only_call(tmp_path: Path) -> None:
    """Negative control: an all-keyword call to a guarded emitter is clean.

    Complements the clean-tree assertion above with a minimal, isolated
    fixture (rather than relying solely on the size and drift-proneness of
    the real ``src/`` tree) proving the detector does not false-positive on
    the legitimate call shape every real call site in ``src/`` already uses.
    """
    clean = tmp_path / "clean.py"
    clean.write_text(
        'result = emit_artifact_indexed(mission_slug="m", artifact_key="k")\n',
        encoding="utf-8",
    )

    assert _find_positional_emitter_calls((clean,)) == []


def test_detector_ignores_unrelated_same_name_free_function(tmp_path: Path) -> None:
    """Negative control: an unrelated positional call sharing no guarded name is clean.

    Guards against the detector over-matching on call shape alone (e.g.
    "any call with positional args") rather than the specific guarded
    function names — the false-positive risk this WP's Risks & Mitigations
    section calls out explicitly.
    """
    other = tmp_path / "other.py"
    other.write_text("result = some_other_function(1, 2, 3)\n", encoding="utf-8")

    assert _find_positional_emitter_calls((other,)) == []


def test_detector_flags_attribute_chain_positional_call(tmp_path: Path) -> None:
    """Positive-control: prove the widened detector catches attribute-chain calls.

    Issue #3676's first named gap: ``specify_cli/dossier/__init__.py``
    re-exports the four ``emit_*`` functions, so
    ``dossier.emit_artifact_indexed(...)`` is already a valid, real Python
    call shape any future caller could use (a *potential*, not currently
    exercised, shape). The callee here is ``ast.Attribute`` (``dossier.emit_
    artifact_indexed``), not ``ast.Name`` — the pre-widening detector misses
    it entirely because ``_call_target_name`` only handled bare ``Name``
    calls. Same planted-violation idiom and same canonical six-positional
    -argument example as ``test_detector_flags_planted_positional_call``.
    """
    planted = tmp_path / "planted_attribute_chain.py"
    planted.write_text(
        'result = dossier.emit_artifact_indexed("m", "k", "c", "p", "h", 1)\n',
        encoding="utf-8",
    )

    violations = _find_positional_emitter_calls((planted,))

    assert len(violations) == 1
    (violation,) = violations
    assert violation.path == planted
    assert violation.lineno == 1
    assert violation.func_name == "emit_artifact_indexed"


def test_detector_flags_aliased_import_positional_call(tmp_path: Path) -> None:
    """Positive-control: prove the widened detector catches aliased-import calls.

    Issue #3676's second named gap: ``from ...dossier.events import
    emit_artifact_indexed as ei`` followed by ``ei(...)``. The callee IS an
    ``ast.Name``, but its ``.id`` is ``"ei"`` — not one of the four guarded
    names — so the pre-widening detector silently let it through. The
    violation must be attributed to the alias's *resolved original name*
    (``emit_artifact_indexed``), not to the alias ``"ei"`` itself, and not
    silently dropped as an unrecognized name.
    """
    planted = tmp_path / "planted_aliased_import.py"
    planted.write_text(
        "from ...dossier.events import emit_artifact_indexed as ei\n"
        "\n"
        'result = ei("m", "k", "c", "p", "h", 1)\n',
        encoding="utf-8",
    )

    violations = _find_positional_emitter_calls((planted,))

    assert len(violations) == 1
    (violation,) = violations
    assert violation.path == planted
    assert violation.lineno == 3
    assert violation.func_name == "emit_artifact_indexed"
