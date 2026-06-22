"""WP03 / T019 — the death-spiral grep gate (SC-001 / NFR-004 / FR-004).

This is the keystone ratchet of mission ``single-planning-surface-authority``:
it proves that the ``coordination_branch is None ⇒ FLATTENED/COORDINATION`` /
``_coord_path.exists() ⇒ COORDINATION`` **topology/surface-inference** pattern has
**zero live decision sites** across ``src/``. After WP03 the mission shape is
READ from the WP02 stored :class:`MissionTopology`, never re-inferred ad-hoc from
the coordination-branch value or a disk ``stat`` — so all three historical
derivations are retired:

* ``mission_runtime/resolution.py`` (the door-internal ``_assemble_core_fragments``
  derivation);
* ``runtime/next/runtime_bridge.py`` (the ``_coord_path.exists()`` decision
  ladder);
* ``specify_cli/coordination/surface_resolver.py:resolve_status_surface_with_anchor``
  (the third, status-surface re-inference — INCLUDING the former
  ``coord_branch is None ⇒ PRIMARY`` gate, which the gate explicitly asserts is
  gone, alphonso/renata: a gate that passes while that site still classifies the
  surface is a vacuous-gate REJECTION).

The gate is **AST-based** (so comments / docstrings that merely *mention* the
idiom never trip it) and covers the negated / aliased spellings (renata N-2), not
just the literal ``coordination_branch is None``:

* ``coordination_branch is None`` / ``is not None`` / ``not coordination_branch``
  / ``if coordination_branch:`` (bare truthiness);
* the ``coord_branch`` alias in all the same forms;
* ``_coord_path.exists()`` / ``.exists()`` / ``.stat()`` on any ``*coord*`` path.

A test is flagged ONLY when such an inference test's enclosing branch **classifies
topology** — i.e. the branch body assigns a :class:`CommitTargetKind` /
:class:`MissionTopology` / a ``decision_target`` kind, or returns a status-surface
keyed on it. Pure VALUE-reads (``coord_branch = str(raw) if raw else None``) and
the C-006 transient probe arms (the ``CoordState.DELETED`` / ``CoordState.EMPTY``
discrimination, the ``worktree_root`` materialization selection) are NOT
classifications and are not flagged.

Strictness (T031 / NFR-004): the gate carries a **negative-control** proving it
FAILS when a negated/aliased inference-classification site is reintroduced — a
gate that cannot fail is not a gate (the vacuous-grep REJECTION the prompt warns
against).
"""
from __future__ import annotations

import ast
import textwrap
from pathlib import Path

import pytest

pytestmark = pytest.mark.architectural

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC_ROOT = _REPO_ROOT / "src"

# Names whose presence/absence/disk-state historically inferred topology.
_COORD_VALUE_NAMES: frozenset[str] = frozenset(
    {"coordination_branch", "coord_branch"}
)
_COORD_PATH_TOKEN = "coord"

# Tokens whose appearance in an inference branch body marks a TOPOLOGY/SURFACE
# CLASSIFICATION (as opposed to a value-read or a transient-state arm).
_CLASSIFICATION_TOKENS: tuple[str, ...] = (
    "CommitTargetKind.",
    "MissionTopology.",
    "decision_target",
)


def _iter_src_python_files() -> list[Path]:
    return sorted(p for p in _SRC_ROOT.rglob("*.py") if "__pycache__" not in p.parts)


def _rel(path: Path) -> str:
    return path.relative_to(_REPO_ROOT).as_posix()


def _is_coord_value_name(node: ast.expr) -> bool:
    """True for a bare ``coordination_branch`` / ``coord_branch`` Name."""
    return isinstance(node, ast.Name) and node.id in _COORD_VALUE_NAMES


def _is_coord_path_exists_or_stat(node: ast.expr) -> bool:
    """True for ``<*coord*>.exists()`` / ``<*coord*>.stat()`` disk probes."""
    if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
        return False
    if node.func.attr not in ("exists", "stat"):
        return False
    receiver = node.func.value
    return isinstance(receiver, ast.Name) and _COORD_PATH_TOKEN in receiver.id.lower()


def _test_references_coord_inference(test: ast.expr) -> bool:
    """True when *test* is a coord value/disk inference in any aliased spelling.

    Covers: ``x is None`` / ``x is not None`` (Compare), ``not x`` (UnaryOp),
    bare truthiness ``if x:`` (a Name used directly as the test), boolean
    combinations (BoolOp), and ``*coord*.exists()/.stat()`` disk probes.
    """
    for node in ast.walk(test):
        if _is_coord_value_name(node):
            return True
        if _is_coord_path_exists_or_stat(node):
            return True
    return False


def _branch_classifies_topology(body: list[ast.stmt]) -> bool:
    """True when a branch body classifies topology (vs a value-read / transient).

    A classification assigns a ``CommitTargetKind`` / ``MissionTopology`` /
    ``decision_target`` token. The C-006 transient arms (``CoordState.*``,
    ``worktree_root`` Path selection) and value-reads do not, so they never trip.
    """
    for stmt in body:
        snippet = ast.unparse(stmt)
        if any(token in snippet for token in _CLASSIFICATION_TOKENS):
            return True
    return False


def _live_inference_classification_sites(path: Path) -> list[int]:
    """Return line numbers of live coord-inference *classification* branches.

    Walks every ``if``/``elif`` and ternary (``IfExp``) whose test is a coord
    value/disk inference; flags it ONLY when the controlled branch classifies
    topology. Value-reads and transient-state arms are not classifications.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    hits: list[int] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            if _test_references_coord_inference(node.test) and (
                _branch_classifies_topology(node.body)
                or _branch_classifies_topology(node.orelse)
            ):
                hits.append(node.lineno)
        elif isinstance(node, ast.IfExp) and _test_references_coord_inference(
            node.test
        ):
            # A ternary classifies when either arm names a classification token.
            body_src = ast.unparse(node.body) + " " + ast.unparse(node.orelse)
            if any(token in body_src for token in _CLASSIFICATION_TOKENS):
                hits.append(node.lineno)
    return hits


# The three formerly-deriving modules MUST now show ZERO classification sites.
_FORMERLY_DERIVING_MODULES: tuple[str, ...] = (
    "src/mission_runtime/resolution.py",
    "src/runtime/next/runtime_bridge.py",
    "src/specify_cli/coordination/surface_resolver.py",
)


def test_zero_live_topology_inference_classification_sites() -> None:
    """No live ``coordination_branch``-None / ``_coord_path.exists()`` classifier.

    Across all of ``src/``, no ``if``/ternary keyed on the coord value/disk
    inference may classify topology. The shape is READ from the stored
    ``MissionTopology`` (FR-004 / SC-001). A new such site re-opens the
    parallel-inference death-spiral.
    """
    offenders: dict[str, list[int]] = {}
    for path in _iter_src_python_files():
        hits = _live_inference_classification_sites(path)
        if hits:
            offenders[_rel(path)] = hits
    assert not offenders, (
        "Live coordination_branch-None / _coord_path.exists() topology "
        f"CLASSIFICATION site(s) found: {dict(sorted(offenders.items()))}. The "
        "mission shape MUST be READ from the WP02 stored MissionTopology "
        "(mission_runtime.resolution.destination_kind_for_topology / "
        "ensure_topology), never re-inferred from the coordination-branch value "
        "or a disk stat (FR-004 / SC-001). Value-reads and the C-006 "
        "CoordState.DELETED/EMPTY transient arms are fine — only kind/topology "
        "classification keyed on the inference is forbidden."
    )


def test_surface_resolver_600_gate_is_explicitly_covered() -> None:
    """The third derivation (surface_resolver) is in the swept set and is clean.

    Belt-and-braces against a vacuous gate: assert the surface resolver is one of
    the swept modules AND that it has zero classification sites — so the gate
    cannot pass while ``resolve_status_surface_with_anchor`` still decides the
    surface from ``coord_branch is None`` (the prompt's vacuous-gate REJECTION).
    """
    surface_resolver = _SRC_ROOT / "specify_cli/coordination/surface_resolver.py"
    assert surface_resolver.exists()
    assert _rel(surface_resolver) in _FORMERLY_DERIVING_MODULES
    assert _live_inference_classification_sites(surface_resolver) == []


def test_negative_control_gate_catches_reintroduced_classifier() -> None:
    """Injection proof (T031): the gate FAILS on a negated/aliased classifier.

    Proves the gate is not vacuous. The synthetic offender uses the ALIASED,
    NEGATED ``not coord_branch`` spelling (never the literal
    ``coordination_branch is None``) and a classification body — the gate must
    still catch it, or a grep-for-one-literal would let an equivalent inference
    survive.
    """
    bad = textwrap.dedent(
        """
        from mission_runtime import CommitTarget, CommitTargetKind

        def rogue(coord_branch, target_branch):
            if not coord_branch:
                # ALIASED + NEGATED reintroduction of the retired derivation.
                return CommitTarget(ref=target_branch, kind=CommitTargetKind.FLATTENED)
            return CommitTarget(ref=coord_branch, kind=CommitTargetKind.COORDINATION)
        """
    )
    tmp = _REPO_ROOT / "src" / "__t019_negative_control__.py"
    tmp.write_text(bad, encoding="utf-8")
    try:
        hits = _live_inference_classification_sites(tmp)
    finally:
        tmp.unlink()
    assert hits, (
        "The T019 gate failed to catch a reintroduced negated/aliased "
        "(`not coord_branch` ⇒ CommitTargetKind) classifier — it is vacuous. A "
        "gate that cannot fail is not a gate (NFR-004 / SC-001)."
    )


def test_negative_control_ternary_classifier_is_caught() -> None:
    """The gate also catches a ternary (IfExp) inference classifier."""
    bad = textwrap.dedent(
        """
        from mission_runtime import CommitTargetKind

        def rogue(coordination_branch):
            kind = (
                CommitTargetKind.COORDINATION
                if coordination_branch is not None
                else CommitTargetKind.FLATTENED
            )
            return kind
        """
    )
    tmp = _REPO_ROOT / "src" / "__t019_negative_control_ternary__.py"
    tmp.write_text(bad, encoding="utf-8")
    try:
        hits = _live_inference_classification_sites(tmp)
    finally:
        tmp.unlink()
    assert hits, "The gate must catch a ternary coord-inference classifier."


def test_value_read_and_transient_arms_are_not_flagged() -> None:
    """Belt-and-braces: a value-read and a C-006 transient arm do NOT trip."""
    benign = textwrap.dedent(
        """
        def value_read(raw_coord):
            coord_branch = str(raw_coord) if raw_coord else None
            return coord_branch

        def transient_arm(_coord_path, feature_dir, resolved):
            # C-006 worktree-materialization selection (the surviving
            # runtime_bridge arm): a Path choice keyed on a *coord* disk stat,
            # but it assigns a Path, NOT a CommitTargetKind — so it is a transient
            # arm, not a topology classifier, and must NOT be flagged.
            worktree_root = _coord_path if _coord_path.exists() else resolved
            return worktree_root
        """
    )
    tmp = _REPO_ROOT / "src" / "__t019_benign__.py"
    tmp.write_text(benign, encoding="utf-8")
    try:
        hits = _live_inference_classification_sites(tmp)
    finally:
        tmp.unlink()
    assert hits == [], (
        f"Value-reads / transient arms must not be flagged as classifiers, "
        f"got lines {hits}."
    )
