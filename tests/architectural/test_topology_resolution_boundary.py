"""Architectural guardrail (WP09 / FR-009): the C-RATCHET topology boundary.

After mission ``name-vs-authority-remediation-01KTYGTE`` routed every
coord-topology decision through the blessed seam authority
(``coordination/surface_resolver.py``), every mission-branch *composition*
through the canonical grammar (``lanes/branch_naming.py``), and eradicated the
mid8 *fabrication* idiom, this ratchet becomes the *permanent* C-RATCHET
enforcement. It locks the mission's invariant — **name proposes, authority
disposes** — against regression along three independent decision points
(contracts/authority-seams.md §C-RATCHET; spec.md FR-009; NFR-003 fail-closed).

It mirrors ``tests/architectural/test_safe_commit_import_boundary.py`` exactly:
``pytestmark = pytest.mark.architectural``; ``_REPO_ROOT = parents[2]``;
``_SRC_ROOT = _REPO_ROOT / "src"``; ``_iter_src_python_files`` / ``_rel``
helpers; AST + textual scans; allowlists as ``frozenset[str]`` of repo-relative
POSIX paths, each entry carrying a one-line justification comment that references
the seam contracts.

The three assertions
--------------------
1.  **Coord-predicate allowlist (C-SEAM-1).** The path-shape *proposals*
    (``".worktrees" in <X>.parts`` / ``part == _WORKTREES_*`` membership and the
    ``-coord`` suffix test) that decide coord-topology routing live ONLY inside
    the blessed seam module plus an explicit, documented allowlist. The migrated
    sites (status_service, aggregate, scanner, root_resolver, emit,
    work_package_lifecycle) delegate to the seam and MUST NOT re-grow raw
    predicates.

2.  **Unbackstopped ``f"kitty/mission-{slug}"`` composes (C-SEAM-2).** Zero
    legacy-shape mission-branch composes (a ``kitty/mission-`` f-string
    interpolating a bare slug-class field and no mid8/mission_id) outside
    ``lanes/branch_naming.py``, except a documented allowlist. The migrated B
    sites (aggregate, recovery, compute, sync, manifest, detection) route
    through ``mission_branch_name``/``mission_branch_name_required``.

3.  **Zero fabrication idiom (NFR-003).** The mid8-fabrication idiom
    (``... + "00000000")[:8]`` / ``replace("-", "") + "00000000"``) has zero
    occurrences anywhere in ``src/``. It was replaced by the fail-closed
    ``resolve_transaction_mid8`` cascade.

Strictness: each assertion is proven by a temporary rogue injection that FAILS
the test with an actionable message, then reverted (T031 — proofs recorded in
the WP09 handoff note). A ratchet that cannot catch a rogue is not a ratchet.

Spec source: FR-009, NFR-003, contracts/authority-seams.md §C-SEAM-1/§C-SEAM-2/
§C-RATCHET; mission ``name-vs-authority-remediation-01KTYGTE``; normative design
``kitty-specs/name-vs-authority-remediation-01KTYGTE/research/research-authority-seams.md``.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.architectural

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC_ROOT = _REPO_ROOT / "src"


def _iter_src_python_files() -> list[Path]:
    return sorted(p for p in _SRC_ROOT.rglob("*.py") if "__pycache__" not in p.parts)


def _rel(path: Path) -> str:
    return path.relative_to(_REPO_ROOT).as_posix()


# ===========================================================================
# (1) Coord-topology path-shape predicate allowlist (C-SEAM-1).
# ===========================================================================
#
# The "is this a coordination worktree / what status surface am I on" decision
# routes through ``is_registered_coord_worktree`` / ``classify_worktree_topology``
# (git-registry authority: name proposes, registry disposes). The path-shape
# *proposals* it is built on — the ``".worktrees" in <X>.parts`` / ``part ==
# _WORKTREES_*`` membership idiom and the ``<name>.endswith("-coord")`` suffix
# test — are legal ONLY inside the blessed seam module, plus the explicit
# allowlist below. Every entry is a NON-coord-routing use (generic worktree
# context detection, navigation hints, migration cleanup) or a documented,
# scope-reserved deferral; each carries its own justification. A NEW raw
# predicate in any other file is a C-SEAM-1 regression: infer coord-ness from a
# registered-worktree check, not from path shape.
_BLESSED_COORD_PREDICATE_MODULE = "src/specify_cli/coordination/surface_resolver.py"

_ALLOWLISTED_COORD_PREDICATE_SITES: frozenset[str] = frozenset(
    {
        # NOTE (#1900 / SC-005 — drained by single-mission-surface-resolver WP06):
        # ``coordination/status_transition.py`` used to be allowlisted here for its
        # ``_is_coordination_feature_dir`` / ``_is_coord_worktree_feature_dir``
        # path-shape predicates (the 5th parallel topology-selection site, C-002
        # deferral). WP06 (FR-001/FR-007) migrated them to the canonical seam
        # (``is_under_worktrees_segment`` / ``is_registered_coord_worktree``), so the
        # entry is REMOVED — its removal IS the SC-005 proof that zero parallel
        # selectors remain in that module. Do NOT re-add it: a new raw predicate
        # there is now an unconditional C-SEAM-1 regression.
        # root_resolver delegates to is_registered_coord_worktree; the raw suffix
        # test survives ONLY in the WorktreeRegistryUnavailable except-branch
        # (ad-hoc dirs outside a git repo cannot be canonicalized, so the shape
        # proposal is the only signal). Authority-first, shape as last resort.
        "src/specify_cli/workspace/root_resolver.py",
        # ---- NON-coord-routing worktree-context detection (out of seam scope) -
        # NOTE (#2123 — discard exact-set fix): ``cli/commands/mission_type.py``
        # used to be allowlisted here for its lane-prune cleanup loop's raw
        # ``-coord`` dir-shape skip. That loop was migrated to the blessed
        # ``CoordinationWorkspace`` authority + a manifest-derived exact lane set
        # (no ``<slug>-*`` prefix / ``-coord`` shape predicate remains), so the
        # entry is REMOVED — its removal IS the proof the migration completed for
        # that site. Do NOT re-add it: a new raw predicate there is now a
        # C-SEAM-1 regression.
        # Operator navigation hint: extracts the main-repo prefix from a
        # ``.worktrees`` cwd to print a "cd <repo>" suggestion. Pure UX string
        # building, no coord routing. (Relocated mission.py -> mission_create.py
        # by mission decompose-mission-god-module-01KVXHF8 #2056 WP05 create-seam
        # extraction; same UX-only ``_print_worktree_navigation_hint`` predicate.)
        "src/specify_cli/cli/commands/agent/mission_create.py",
        # ``spec-kitty context`` workspace-name extraction from cwd parts — a
        # display/diagnostic read, not a coord-surface routing decision.
        "src/specify_cli/cli/commands/context.py",
        # ``spec-kitty sync`` lane-workspace-name extraction from cwd parts —
        # discovery of the enclosing workspace, not coord routing.
        "src/specify_cli/cli/commands/sync.py",
        # Context-validation worktree detection: locates the enclosing repo root
        # from a ``.worktrees`` cwd for guidance/validation; not coord routing.
        "src/specify_cli/core/context_validation.py",
        # is_worktree_context fast-path: a generic "am I anywhere under a managed
        # worktree" boolean (falls through to a .git-pointer walk for external
        # worktrees); not a coord-vs-lane decision.
        "src/specify_cli/core/paths.py",
        # Upgrade migration m_2_0_6: detects legacy worktree assets to clean up;
        # one-shot migration housekeeping, not runtime coord routing.
        "src/specify_cli/upgrade/migrations/m_2_0_6_consistency_sweep.py",
    }
)


def _coord_predicate_sites(path: Path) -> bool:
    """True iff *path* contains a raw coord-topology path-shape predicate.

    Two idiom classes are detected via AST (so comments/docstrings that merely
    *mention* ``-coord`` or ``.worktrees`` never trip the scan):

    * ``-coord`` suffix proposal: ``<expr>.endswith("-coord")`` or any
      ``==``/``in`` comparison against the ``"-coord"`` constant.
    * ``.worktrees`` membership proposal: ``".worktrees" in <X>.parts`` /
      ``_WORKTREES_* in <X>.parts`` and the equivalent comprehension element
      test ``part == _WORKTREES_*`` / ``part == ".worktrees"``.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        # ``<expr>.endswith("-coord")``
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "endswith"
            and any(
                isinstance(arg, ast.Constant) and arg.value == "-coord"
                for arg in node.args
            )
        ):
            return True
        if isinstance(node, ast.Compare):
            left = node.left
            for op, comparator in zip(node.ops, node.comparators, strict=False):
                # ``<x> == "-coord"`` (suffix proposal via equality)
                if (
                    isinstance(op, ast.Eq)
                    and isinstance(comparator, ast.Constant)
                    and comparator.value == "-coord"
                ):
                    return True
                # ``".worktrees" / _WORKTREES_* in <X>.parts`` (membership)
                if (
                    isinstance(op, ast.In)
                    and isinstance(comparator, ast.Attribute)
                    and comparator.attr == "parts"
                    and _is_worktrees_token(left)
                ):
                    return True
                # ``part == ".worktrees" / _WORKTREES_*`` (comprehension element)
                if (
                    isinstance(op, ast.Eq)
                    and isinstance(left, ast.Name)
                    and _is_worktrees_token(comparator)
                ):
                    return True
    return False


def _is_worktrees_token(node: ast.expr) -> bool:
    """True for the ``".worktrees"`` literal or a ``*WORKTREES*`` constant name."""
    if isinstance(node, ast.Constant):
        return node.value == ".worktrees"
    if isinstance(node, ast.Name):
        return "WORKTREES" in node.id
    return False


def test_coord_path_predicate_only_in_blessed_modules() -> None:
    """Raw coord-topology path-shape predicates live only in blessed sites.

    A new ``".worktrees" in parts`` / ``endswith("-coord")`` predicate in an
    un-allowlisted file means a coord-vs-lane routing decision was inferred from
    path shape instead of the git-registry authority — a C-SEAM-1 regression.
    """
    actual: set[str] = set()
    for path in _iter_src_python_files():
        if _coord_predicate_sites(path):
            actual.add(_rel(path))

    blessed = {_BLESSED_COORD_PREDICATE_MODULE} | set(_ALLOWLISTED_COORD_PREDICATE_SITES)
    unexpected = actual - blessed
    stale = blessed - actual

    assert not unexpected, (
        "Unexpected raw coord-topology path-shape predicate(s) in: "
        f"{sorted(unexpected)}. Infer coord-ness from a registered-worktree "
        "check (coordination.surface_resolver.is_registered_coord_worktree / "
        "classify_worktree_topology) — name proposes, the git registry disposes. "
        "If this is a legitimate non-routing use, add it to "
        "_ALLOWLISTED_COORD_PREDICATE_SITES with a one-line justification "
        "(C-SEAM-1, contracts/authority-seams.md)."
    )
    assert not stale, (
        "Allowlisted coord-predicate site(s) no longer contain a raw predicate: "
        f"{sorted(stale)}. Remove them from _ALLOWLISTED_COORD_PREDICATE_SITES — "
        "the seam migration is one site closer to complete."
    )


# ===========================================================================
# (2) Unbackstopped ``f"kitty/mission-{slug}"`` branch composes (C-SEAM-2).
# ===========================================================================
#
# Mission-branch name COMPOSITION outside ``lanes/branch_naming.py`` is
# prohibited: consumers call the canonical grammar fed by ``mission_id`` from
# meta (``mission_branch_name`` / ``mission_branch_name_required``), which is
# dual-era and fail-closed. The defect class this catches is the LEGACY-shape
# compose — a ``kitty/mission-`` f-string interpolating a bare slug-class field
# (``mission_slug`` / ``slug`` / ``feature_slug`` / ``self.mission_slug``) and
# NO mid8/mission_id — which silently fabricates a branch name that does not
# exist on disk for every mid8-era mission.
#
# Composes that thread mid8 (e.g. via ``_compose_mission_dir(slug, mid8)`` or a
# pre-composed ``human_part``/``worktree_name``) are NOT legacy-shape: their
# interpolated field is not a bare slug name, so they are not flagged. A glob
# query (``kitty/mission-{slug}*`` for ``git branch --list``) is a read, not a
# compose, and is excluded by its trailing ``*``.
_BARE_SLUG_FIELD_NAMES: frozenset[str] = frozenset(
    {"mission_slug", "slug", "feature_slug", "self.mission_slug", "self.slug"}
)

# All previously-reserved legacy-compose residuals have now been routed through
# the canonical seam by this mission's routing WPs:
#   * runtime_bridge.py  — now resolves the branch from the declared mission_id;
#   * cli/commands/merge.py — now uses the mission_branch resolver (FR-004);
#   * merge/preflight.py — now composes via mission_branch_name_required.
# Each retains only a docstring mentioning the bare legacy form (which the
# detector skips), so the allow-list is empty: any new bare-slug compose is now
# an unconditional C-SEAM-2 regression. The ``stale`` assertion below keeps this
# empty set from silently re-accumulating dead exemptions.
_ALLOWLISTED_LEGACY_COMPOSE_SITES: frozenset[str] = frozenset()


def _legacy_mission_compose_sites(path: Path) -> bool:
    """True iff *path* has a legacy-shape ``kitty/mission-{bare_slug}`` compose.

    A ``JoinedStr`` (f-string) qualifies only when ALL of:
    * its literal text contains ``kitty/mission-`` and does NOT end the
      interpolation with a ``*`` glob (which marks a ``git branch --list`` query);
    * it interpolates at least one bare slug-class field
      (:data:`_BARE_SLUG_FIELD_NAMES`);
    * it interpolates NO mid8/mission_id-class field (so a mid8-threading
      compose is never flagged).

    Docstring/module-level prose f-strings are excluded because real composes
    are not statement-level string expressions; an f-string used purely as a
    docstring is an ``ast.Expr`` whose ``.value`` is the ``JoinedStr`` — those
    are skipped via the ``_docstring_joinedstrs`` set.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    docstring_joinedstrs = _docstring_joinedstrs(tree)
    for node in ast.walk(tree):
        if not isinstance(node, ast.JoinedStr):
            continue
        if id(node) in docstring_joinedstrs:
            continue
        literal = "".join(
            v.value
            for v in node.values
            if isinstance(v, ast.Constant) and isinstance(v.value, str)
        )
        if "kitty/mission-" not in literal:
            continue
        if literal.rstrip().endswith("*"):
            # ``kitty/mission-{slug}*`` is a glob query (git branch --list),
            # not a branch compose.
            continue
        fields = {
            ast.unparse(v.value)
            for v in node.values
            if isinstance(v, ast.FormattedValue)
        }
        has_bare_slug = bool(fields & _BARE_SLUG_FIELD_NAMES)
        has_mid8 = any(
            ("mid8" in f) or ("mission_id" in f) for f in fields
        )
        if has_bare_slug and not has_mid8:
            return True
    return False


def _docstring_joinedstrs(tree: ast.AST) -> set[int]:
    """Collect ``id()`` of any ``JoinedStr`` that is a docstring expression."""
    out: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(
            node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
        ):
            body = getattr(node, "body", [])
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.JoinedStr)
            ):
                out.add(id(body[0].value))
    return out


def test_legacy_mission_branch_compose_is_allowlisted() -> None:
    """Only allowlisted sites may compose a legacy ``kitty/mission-{slug}`` name.

    Every other producer routes through the canonical dual-era, fail-closed
    grammar (lanes.branch_naming.mission_branch_name /
    mission_branch_name_required, fed mission_id from meta). A new bare-slug
    compose silently fabricates a branch that does not exist for any mid8-era
    mission — a C-SEAM-2 regression.
    """
    actual: set[str] = set()
    for path in _iter_src_python_files():
        if _rel(path) == "src/specify_cli/lanes/branch_naming.py":
            # The canonical grammar module: the f-strings here ARE the contract.
            continue
        if _legacy_mission_compose_sites(path):
            actual.add(_rel(path))

    allowlist = set(_ALLOWLISTED_LEGACY_COMPOSE_SITES)
    unexpected = actual - allowlist
    stale = allowlist - actual

    assert not unexpected, (
        "Unexpected legacy kitty/mission-{slug} compose site(s): "
        f"{sorted(unexpected)}. Compose via "
        "lanes.branch_naming.mission_branch_name(slug, mission_id=...) or "
        "mission_branch_name_required(slug, mission_id) — fed mission_id from "
        "meta.json — instead of an f-string that omits the mid8 disambiguator. "
        "If this is a documented residual or pre-init carve-out, add it to "
        "_ALLOWLISTED_LEGACY_COMPOSE_SITES with a justification (C-SEAM-2)."
    )
    assert not stale, (
        "Allowlisted legacy-compose site(s) no longer compose the legacy form: "
        f"{sorted(stale)}. Remove them from _ALLOWLISTED_LEGACY_COMPOSE_SITES — "
        "the branch-identity seam is one site closer to complete."
    )


# ===========================================================================
# (3) Zero mid8-fabrication idiom anywhere in src/ (NFR-003 fail-closed).
# ===========================================================================
#
# The fabrication idiom invented a mid8 by zero-padding a de-hyphenated slug
# (``(mission_slug.replace("-", "") + "00000000")[:8]``). It produced a
# plausible-but-wrong mid8 that mis-routed locks/transactions/branches instead
# of failing closed. WP05 replaced it with the fail-closed
# ``resolve_transaction_mid8`` cascade (meta.mid8 -> mission_id[:8] ->
# mid8_from_slug; raise BranchIdentityUnresolved when coord-topology is declared
# but the mid8 is unrecoverable). Any textual reappearance is a NFR-003
# regression. The ``00000000-0000-...`` project_uuid placeholders elsewhere are
# a different shape and do not match these substrings, so no allowlist is needed.
_FABRICATION_IDIOMS: tuple[str, ...] = (
    '+ "00000000")[:8]',
    '+"00000000")[:8]',
    'replace("-", "") + "00000000"',
    'replace("-", "")+"00000000"',
)


def test_fabricated_mid8_idiom_has_zero_references() -> None:
    """The mid8-fabrication idiom has zero occurrences in ``src/``.

    Fabricating a mid8 from a slug invents a disambiguator that mis-routes
    locks/transactions/branches. The fail-closed resolve_transaction_mid8
    cascade replaced it; any reappearance regresses NFR-003.
    """
    offenders: dict[str, list[str]] = {}
    for path in _iter_src_python_files():
        text = path.read_text(encoding="utf-8")
        hits = [idiom for idiom in _FABRICATION_IDIOMS if idiom in text]
        if hits:
            offenders[_rel(path)] = hits
    assert not offenders, (
        "mid8-fabrication idiom reappears in: "
        f"{dict(sorted(offenders.items()))}. Do not fabricate a "
        "mid8 by zero-padding a de-hyphenated slug — resolve it through the "
        "fail-closed cascade (lanes.branch_naming.resolve_transaction_mid8: "
        "meta.mid8 -> mission_id[:8] -> mid8_from_slug, else "
        "BranchIdentityUnresolved). Name proposes, authority disposes (NFR-003)."
    )
