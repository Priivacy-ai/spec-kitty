"""Structural read-side gate — no read-side placement-seam bypass (WP08 / IC-06).

read-side-placement-seam-migration-01KYHP67, FR-005 / FR-006 / NFR-003 /
NFR-004: the CAPSTONE structural gate that makes new read-side bypasses of
``PlacementSeam.read_dir(kind)`` unrepresentable, mirroring the write-side
structural gate (``test_no_write_side_rederivation.py``'s
``test_adopted_and_residual_modules_have_no_checkout_derived_commit_target``
whole-tree AST scan). This is NOT modeled on the *behavioral*
``test_read_surface_placement_guard.py`` — it is the symmetric structural
analog of the write gate.

Contract: ``kitty-specs/read-side-placement-seam-migration-01KYHP67/
contracts/read-side-gate.md``.

Scope (NFR-003 — reuse, never fork the walk)
---------------------------------------------
Reuses ``tests.architectural._placement_whole_tree_scan.scan_scope()`` — the
SAME shared whole-tree ``src/`` walker + write-side sanctioned-module filter
the write gate consumes (``test_read_and_write_gates_share_the_same_scan_scope``
below asserts identity, not mere equality, of the two gates' base scan
function). The read gate layers ONE additional, read-specific sanctioned-module
filter (``_READ_SANCTIONED_MODULES``) on top of that shared base — composing a
second filter is not forking the walk; ``_placement_whole_tree_scan`` itself
already composes ``BOUNDARY_SANCTIONED_MODULES`` and
``BOUNDARY_SANCTIONED_PREFIXES`` the same way.

Finding grammar
----------------
AST-based (``ast.Call``): flags any callee resolving to
``candidate_feature_dir_for_mission`` or ``resolve_planning_read_dir`` (bare
``Name`` or ``Attribute.attr``). Callee identity IS the finding — reads have no
``ref`` argument to value-flow-trace, so no "seam-derived" discriminator is
needed (unlike the write gate's ``CommitTarget(ref=...)`` grammar). A
docstring/comment merely NAMING one of these symbols never becomes an
``ast.Call`` node and is therefore never flagged (the bite test below proves
this).

Allow-list (T018)
------------------
Every entry mirrors a ``stay-lenient`` row in
``docs/development/read-side-seam-classification.md`` (WP02, the authoritative
per-site ledger) — 16 sites across 11 files, reconciled 1:1 against the
ledger's AST-verified census (see the module-level ``_LEDGER_STAY_LENIENT_SITE_COUNT``
pin below). Content-descriptor allow-listing (``_ratchet_keys.resolve_descriptor``,
the SAME resolver WS1/WS2/WS3/checkout-grammar entries in the write gate use):
``(rel_path, qualname, token_substring)`` resolves LIVE to exactly one finding's
``(rel_path, qualname, token_line)`` composite key — never a bare path (C-003:
no file-scoped blanket exemptions). Shrink-only: a staleness twin-guard REDS
the moment a routed/removed entry stops resolving to its seeded key (FR-006 /
NFR-004) — the fix is to DELETE the stale entry, never leave a vacuous rule.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

import pytest

from tests.architectural._placement_whole_tree_scan import rel_path as _placement_rel_path
from tests.architectural._placement_whole_tree_scan import scan_scope as _whole_tree_scan_scope
from tests.architectural._ratchet_keys import (
    CompositeKey,
    ContentDescriptor,
    composite_key,
    descriptor_still_live,
    resolve_descriptor,
)

pytestmark = pytest.mark.architectural

_REPO_ROOT = Path(__file__).resolve().parents[2]

#: The two kind-blind / lenient-kind-aware read bypass primitives this gate
#: forbids outside the sanctioned + allow-listed sets (contract "Finding").
_TARGET_CALLEE_NAMES: frozenset[str] = frozenset(
    {"candidate_feature_dir_for_mission", "resolve_planning_read_dir"}
)

#: Read-side sanctioned infra modules (FR-003): the seam's OWN internals that
#: legitimately call the low-level resolvers -- asserted sanctioned with a
#: rationale (mirroring ``resolution.py``'s self-exclusion style / the write
#: gate's ``BOUNDARY_SANCTIONED_MODULES`` per-file rationale convention), NOT
#: silently skipped. This is a SECOND, read-specific filter layered on top of
#: the shared ``scan_scope()`` base (NFR-003 "reuse, do not fork the walk") --
#: composing an additional filter is exactly how ``_placement_whole_tree_scan``
#: itself layers ``BOUNDARY_SANCTIONED_MODULES``/``_PREFIXES`` on
#: ``iter_src_modules``.
#:
#: - ``_read_path_resolver.py`` defines BOTH primitives and calls
#:   ``candidate_feature_dir_for_mission`` from inside
#:   ``resolve_planning_read_dir`` (:1432) and ``resolve_subtasks_gate_dir``
#:   (:1473, via ``resolve_planning_read_dir``) to compose its own public
#:   surface -- self-reference, not a bypass (the primitive authority itself,
#:   per FR-003; excluded from the ledger's consumer census entirely for the
#:   same reason).
#: - ``coordination/surface_resolver.py`` (:675,
#:   ``resolve_status_surface_with_anchor``) is the canonical surface resolver
#:   infra that ``candidate_feature_dir_for_mission`` is partly built to serve
#:   -- FR-003 names this module explicitly.
#: - ``mission_runtime/write_target_degrade.py`` (:183,
#:   ``resolve_write_target_or_degrade``'s bootstrap-window existence probe) is
#:   ALREADY excluded from ``scan_scope()`` via the shared
#:   ``BOUNDARY_SANCTIONED_PREFIXES`` ``src/mission_runtime/`` blanket; this
#:   entry restores the individual, rationale-bearing accountability the
#:   write-side ``_placement_whole_tree_scan`` module docstring itself calls
#:   out for this exact file, so the read gate's own sanctioned-module test
#:   (below) can assert it directly rather than it going unpoliced behind the
#:   package-wide prefix.
_READ_SANCTIONED_MODULES: dict[str, str] = {
    "src/specify_cli/missions/_read_path_resolver.py": (
        "The primitive authority itself: defines both "
        "candidate_feature_dir_for_mission and resolve_planning_read_dir, and "
        "resolve_planning_read_dir calls candidate_feature_dir_for_mission "
        "internally (:1432) to compose its own STATUS-partition leg -- a "
        "self-reference, not a bypass. Excluded from the WP02 classification "
        "ledger's consumer census for the same reason (FR-003)."
    ),
    "src/specify_cli/coordination/surface_resolver.py": (
        "The canonical surface resolver (resolve_status_surface_with_anchor "
        "et al., :675) that candidate_feature_dir_for_mission is partly built "
        "to serve; FR-003 names this module explicitly as sanctioned infra, "
        "not a bypass site awaiting a route."
    ),
    "src/mission_runtime/write_target_degrade.py": (
        "Bootstrap-window write-target degrade helper "
        "(resolve_write_target_or_degrade, :183) -- already excluded from "
        "scan_scope() via the shared src/mission_runtime/ "
        "BOUNDARY_SANCTIONED_PREFIXES blanket; this per-file entry restores "
        "individual, rationale-bearing accountability so this gate's own "
        "sanctioned-module test asserts it directly (mirrors the write gate's "
        "per-file BOUNDARY_SANCTIONED_MODULES entry for the same file)."
    ),
}


def _is_read_sanctioned(rel: str) -> bool:
    """``True`` iff ``rel`` is a read-side sanctioned infra module (FR-003)."""
    return rel in _READ_SANCTIONED_MODULES


def _read_side_scan_scope() -> list[Path]:
    """The read gate's scan scope: the SHARED ``scan_scope()`` minus the
    read-specific sanctioned-infra set.

    Reuses (never forks) the shared whole-tree walker -- see the module
    docstring's "Scope" section.
    """
    return [
        module
        for module in _whole_tree_scan_scope()
        if not _is_read_sanctioned(_placement_rel_path(module))
    ]


def _callee_name(call: ast.Call) -> str | None:
    """Return the callee identifier for bare-name OR attribute call forms."""
    func = call.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


@dataclass(frozen=True)
class _Finding:
    """A flagged read-side bypass call: ``(path, lineno, callee, source)``."""

    path: Path
    lineno: int
    callee: str
    source: str

    def as_allow_key(self) -> CompositeKey:
        """The drift-proof ``(rel_path, qualname, token_line)`` composite allow-list key."""
        qualname, token_line = composite_key(self.source, self.lineno)
        rel_path = self.path.relative_to(_REPO_ROOT).as_posix()
        return (rel_path, qualname, token_line)


def _scan_read_bypass(source: str, path: Path) -> list[_Finding]:
    """Flag every real ``ast.Call`` to a read-bypass primitive in ``source``.

    AST-based (unlike a textual/token grammar): the finding is a call
    CONSTRUCTION, so a docstring or comment merely naming
    ``candidate_feature_dir_for_mission`` / ``resolve_planning_read_dir`` is
    inert prose (never an ``ast.Call`` node) and is never flagged -- this is
    exactly the discrimination the WP02 ledger's own AST census had to get
    right (90 real call sites vs. 93 raw textual grep hits, 3 false positives).
    """
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return []
    findings: list[_Finding] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            callee = _callee_name(node)
            if callee in _TARGET_CALLEE_NAMES:
                findings.append(_Finding(path, node.lineno, callee, source))
    return findings


def _scan_read_bypass_module(path: Path) -> list[_Finding]:
    return _scan_read_bypass(path.read_text(encoding="utf-8"), path)


# ---------------------------------------------------------------------------
# T018 — allow-list: every stay-lenient residual from the WP02 ledger.
# ---------------------------------------------------------------------------

#: Ledger-pinned count (docs/development/read-side-seam-classification.md
#: Summary table): 16 stay-lenient sites across 11 files. A change to this
#: number without a corresponding ledger update is a drift signal.
_LEDGER_STAY_LENIENT_SITE_COUNT = 16

#: Content-descriptor allow-list (T018): each entry is a ``stay-lenient``
#: residual from the WP02 classification ledger, derived site-for-site (never
#: invented) -- 16 sites across 11 files. Every rationale is condensed from
#: the ledger's own per-row rationale; see the ledger for the full reasoning.
_ALLOW_LIST_SEED: tuple[ContentDescriptor, ...] = (
    ContentDescriptor(
        rel_path="src/specify_cli/cli/commands/agent/tasks_move_task.py",
        qualname="_coord_status_events_path",
        token_substring="candidate_feature_dir_for_mission ( coord_root , mission_dir )",
        occurrence=None,
        rationale=(
            "Ledger :2368 (ambiguous -- reviewer confirm): repo_root here is "
            "CoordinationWorkspace.worktree_path(...) -- an ALREADY-RESOLVED "
            "coord worktree path, not the primary checkout -- and the slug arg "
            "is a composed mission_dir_name(...), not a raw handle. A direct "
            "probe of an already-verified coord worktree's own "
            "status.events.jsonl, not the seam's repo_root+topology contract. "
            "Defaulted lenient pending a bespoke (non-mechanical) fix."
        ),
    ),
    ContentDescriptor(
        rel_path="src/specify_cli/cli/commands/agent/tasks_status_cmd.py",
        qualname="_st_resolve_dirs",
        token_substring="candidate_feature_dir_for_mission ( status_read_root , st . mission_slug )",
        occurrence=None,
        rationale=(
            "Ledger :160 (ambiguous -- reviewer confirm): an explicit "
            "'last-ditch fallback to the original worktree-aware path' using a "
            "CWD-derived status_read_root (not repo_root) 'so tests / projects "
            "that stand up status files in unusual places still work'. The "
            "seam is explicitly CWD-invariant by design -- routing this "
            "fallback through it would defeat its documented purpose."
        ),
    ),
    ContentDescriptor(
        rel_path="src/specify_cli/cli/commands/archive.py",
        qualname="create",
        token_substring="candidate_feature_dir_for_mission ( root , mission )",
        occurrence=None,
        rationale=(
            "Ledger :65 (stay-lenient, flagged multi-kind; ambiguous -- "
            "reviewer confirm): feature_dir is an existence probe then passed "
            "into archive_mission(feature_dir=...), which threads it into BOTH "
            "a STATUS_STATE read (terminal_state_resolver) and an "
            "ACCEPTANCE_MATRIX read (invariants_reader) -- a genuine multi-kind "
            "reader off one kind-blind anchor. A single-kind swap would be "
            "false precision; needs a two-call split before migrating."
        ),
    ),
    ContentDescriptor(
        rel_path="src/specify_cli/cli/commands/_coordination_doctor.py",
        qualname="_finding_for_reconcile_marker",
        token_substring="feature_dir = resolve_planning_read_dir (",
        occurrence=None,
        rationale=(
            "Ledger :933: named explicitly in research.md's hard-cases list -- "
            "a diagnostic tool auditing pending_coord_reconcile markers / live-"
            "strand findings across the corpus; this site already catches "
            "(ValueError, MissionSelectorAmbiguous) and degrades to a warning "
            "finding rather than aborting the doctor run. Kept lenient "
            "module-wide per doctrine, independent of this kind's incidental "
            "safety."
        ),
    ),
    ContentDescriptor(
        rel_path="src/specify_cli/cli/commands/_coordination_doctor.py",
        qualname="_heal_one_strand",
        token_substring="feature_dir = resolve_planning_read_dir (",
        occurrence=None,
        rationale=(
            "Ledger :1057: same _coordination_doctor.py module-wide leniency "
            "doctrine as :933 above -- a strand-healing diagnostic path that "
            "must tolerate a half-materialized or deleted coord branch."
        ),
    ),
    ContentDescriptor(
        rel_path="src/specify_cli/cli/commands/reconcile.py",
        qualname="reconcile_mission_dossier",
        token_substring="candidate_feature_dir_for_mission ( root , mission_slug )",
        occurrence=None,
        rationale=(
            "Ledger :126 (stay-lenient, flagged multi-kind; ambiguous -- "
            "reviewer confirm): feature_dir feeds dossier.snapshot.load_snapshot "
            "(a .kittify/dossiers cache read, no MissionArtifactKind mapping) "
            "and a present_projection rebuild hashing across several artifact "
            "kinds -- a genuine multi-kind reader with no single clean target "
            "kind. The fail-closed ReconciliationResult.ERROR return already "
            "absorbs any resolution failure gracefully -- no regression from "
            "staying put."
        ),
    ),
    ContentDescriptor(
        rel_path="src/specify_cli/cli/commands/retrospect.py",
        qualname="_canonical_events_path",
        token_substring="candidate_feature_dir_for_mission ( repo_root , mission_slug )",
        occurrence=None,
        rationale=(
            "Ledger :110 (ambiguous -- reviewer confirm): fires only when "
            "resolve_status_surface raises FileNotFoundError/ValueError -- "
            "'meta.json absent for a legacy mission' per its own docstring. "
            "Migrating this fallback leg to the fail-loud seam risks raising "
            "CoordinationBranchDeleted in exactly the degraded window this "
            "fallback exists to tolerate."
        ),
    ),
    ContentDescriptor(
        rel_path="src/specify_cli/cli/commands/retrospect.py",
        qualname="summary_cmd",
        token_substring="candidate_feature_dir_for_mission ( resolved_project , mission_slug )",
        occurrence=None,
        rationale=(
            "Ledger :1005: a corpus-walk classifier iterating EVERY mission "
            "under .kittify/missions/ to compute a 4-state retrospective-"
            "coverage report -- a single problematic mission's coord-branch "
            "deletion must not abort the whole report (named diagnostic "
            "pattern, research.md)."
        ),
    ),
    ContentDescriptor(
        rel_path="src/specify_cli/dashboard/scanner.py",
        qualname="_resolve_identity_primary_first",
        token_substring="primary_dir = resolve_planning_read_dir (",
        occurrence=None,
        rationale=(
            "Ledger :423: named explicitly in research.md's hard-cases list; "
            "this site already catches (ValueError, MissionSelectorAmbiguous) "
            "with an explicit 'the dashboard scan must never crash' comment. "
            "Kept lenient module-wide."
        ),
    ),
    ContentDescriptor(
        rel_path="src/specify_cli/dashboard/scanner.py",
        qualname="_resolve_planning_dir_primary_first",
        token_substring="candidate = resolve_planning_read_dir (",
        occurrence=None,
        rationale=(
            "Ledger :461: same dashboard/scanner.py module-wide leniency "
            "doctrine as :423 above."
        ),
    ),
    ContentDescriptor(
        rel_path="src/specify_cli/dossier/api.py",
        qualname="DossierAPIHandler.handle_dossier_overview",
        token_substring="candidate_feature_dir_for_mission ( self . repo_root , mission_slug )",
        occurrence=None,
        rationale=(
            "Ledger :227 (ambiguous -- reviewer confirm): feeds "
            "dossier.snapshot.load_snapshot -- not a MissionArtifactKind-mapped "
            "artifact. Already treats 'not found' as an expected outcome "
            "(error_response(..., 404)); an external/SaaS-facing read endpoint "
            "('SaaS import-compatible') that should not start raising "
            "CoordinationBranchDeleted for a mission whose coord branch was "
            "later consolidated away (a plausible steady state post-merge)."
        ),
    ),
    ContentDescriptor(
        rel_path="src/specify_cli/dossier/api.py",
        qualname="DossierAPIHandler.handle_dossier_snapshot_export",
        token_substring="candidate_feature_dir_for_mission ( self . repo_root , mission_slug )",
        occurrence=None,
        rationale=(
            "Ledger :397: same dossier/api.py leniency doctrine as :227 above "
            "-- feeds the identical snapshot cache read."
        ),
    ),
    ContentDescriptor(
        rel_path="src/specify_cli/dossier/api.py",
        qualname="DossierAPIHandler._load_dossier",
        token_substring="candidate_feature_dir_for_mission ( self . repo_root , mission_slug )",
        occurrence=None,
        rationale=(
            "Ledger :435: same dossier/api.py leniency doctrine as :227/:397 "
            "above -- the shared internal loader all three public handlers "
            "route through."
        ),
    ),
    ContentDescriptor(
        rel_path="src/specify_cli/retrospective/summary.py",
        qualname="_read_proposal_events",
        token_substring="candidate_feature_dir_for_mission ( project_path , mission_slug )",
        occurrence=None,
        rationale=(
            "Ledger :220: own docstring says 'Returns (0, 0, 0) on any error, "
            "including missing slug, missing log, or corrupt lines' -- an "
            "explicitly resilient summary-statistics reader, named in the "
            "WP06 diagnostic cluster."
        ),
    ),
    ContentDescriptor(
        rel_path="src/specify_cli/status/aggregate.py",
        qualname="MissionStatus._find_meta_path",
        token_substring="candidate_feature_dir_for_mission ( repo_root , mission_slug )",
        occurrence=None,
        rationale=(
            "Ledger :527: named explicitly in research.md's hard-cases list; "
            "the surrounding code already translates StatusReadPathNotFound "
            "into a graceful fail-closed result for every handle form rather "
            "than letting it propagate raw -- status aggregation is itself an "
            "audit/reporting surface."
        ),
    ),
    ContentDescriptor(
        rel_path="src/specify_cli/manifest.py",
        qualname="WorktreeStatus.get_feature_status",
        token_substring="candidate_feature_dir_for_mission ( worktree_path , feature )",
        occurrence=None,
        rationale=(
            "Ledger :272 (ambiguous -- reviewer confirm): worktree_path (not "
            "repo_root) is passed as the first arg -- a deliberate 'what "
            "artifacts physically exist in THIS worktree' probe compared "
            "against the sibling artifacts_in_main leg (already migrated to "
            "the seam). Structurally incompatible with the seam's "
            "repo_root+topology contract; migrating would collapse the "
            "main-vs-worktree drift comparison this diagnostic exists to make."
        ),
    ),
)

#: Composite key resolved LIVE for each ``_ALLOW_LIST_SEED`` entry (parallel,
#: order-preserving with the seed tuple).
_ALLOW_LIST_KEYS: tuple[CompositeKey, ...] = tuple(
    resolve_descriptor((_REPO_ROOT / descriptor.rel_path).read_text(encoding="utf-8"), descriptor)
    for descriptor in _ALLOW_LIST_SEED
)

#: Composite-keyed allow-list: ``frozenset[(rel_path, qualname, token_line)]``.
_ALLOW_LIST: frozenset[CompositeKey] = frozenset(_ALLOW_LIST_KEYS)


# ---------------------------------------------------------------------------
# T017 — the ratchet: no un-sanctioned, un-allow-listed read bypass anywhere.
# ---------------------------------------------------------------------------


def test_no_read_side_bypass_outside_sanctioned_and_allow_listed() -> None:
    """FR-005 / IC-06: every real read-bypass call site in ``src/`` is either
    sanctioned infra, an allow-listed stay-lenient residual, or does not exist.

    A flag on a scanned module that is NOT on ``_ALLOW_LIST`` means a real,
    un-migrated read-side bypass of ``PlacementSeam.read_dir(kind)`` -- the
    exact split-brain / silent-degrade risk the seam exists to close. The scan
    scope is the shared whole-tree ``scan_scope()`` (NFR-003) minus the
    read-specific sanctioned-infra set (FR-003) -- no module allowlist for a
    bypass to hide behind.
    """
    modules = _read_side_scan_scope()
    for module in modules:
        assert module.exists(), f"read-bypass-scan module missing: {module}"

    offenders: list[str] = []
    for module in modules:
        for finding in _scan_read_bypass_module(module):
            if finding.as_allow_key() in _ALLOW_LIST:
                continue
            offenders.append(
                f"{finding.path.relative_to(_REPO_ROOT)}:{finding.lineno} "
                f"{finding.callee}(...) is a kind-blind/lenient read bypass of "
                "PlacementSeam.read_dir(kind) -- route it through the seam or "
                "add a tracked, ledger-backed allow-list entry"
            )

    assert not offenders, (
        "Read-side placement-seam bypass found outside the sanctioned + "
        "allow-listed sets (FR-005 / IC-06). Offenders:\n" + "\n".join(offenders)
    )


def test_allow_list_reconciles_with_the_wp02_ledger_stay_lenient_count() -> None:
    """The allow-list has exactly the ledger's 16 stay-lenient sites -- no more, no fewer.

    Derived site-for-site from ``read-side-seam-classification.md``'s Summary
    table (72 migrate + 16 stay-lenient + 2 sanction-infra = 90 real sites). A
    count drift here means either a genuine ledger update was not mirrored
    here, or an entry was invented that the ledger does not mark stay-lenient
    (forbidden -- this mission's instructions require deriving the allow-list
    from the ledger, never classifying ad hoc).
    """
    assert len(_ALLOW_LIST_SEED) == _LEDGER_STAY_LENIENT_SITE_COUNT, (
        f"expected {_LEDGER_STAY_LENIENT_SITE_COUNT} allow-list entries "
        f"(the WP02 ledger's stay-lenient count), got {len(_ALLOW_LIST_SEED)}"
    )


# ---------------------------------------------------------------------------
# T019 — bite test + symmetry meta-test.
# ---------------------------------------------------------------------------


def test_ratchet_bites_on_a_planted_kind_blind_read_call() -> None:
    """The detector FLAGS a planted ``candidate_feature_dir_for_mission(...)`` call.

    Without this, a vacuous detector (one that never matches) would pass the
    ratchet above regardless of whether real bypasses exist. We feed the
    detector a fixture source string carrying a planted call and assert it is
    flagged.
    """
    fixture_source = (
        "def _new_bypass_site(root, slug):\n"
        "    feature_dir = candidate_feature_dir_for_mission(root, slug)\n"
        "    return feature_dir\n"
    )
    findings = _scan_read_bypass(
        fixture_source, _REPO_ROOT / "src" / "specify_cli" / "manifest.py"
    )
    callees = {f.callee for f in findings}
    assert "candidate_feature_dir_for_mission" in callees, (
        f"ratchet failed to flag a planted kind-blind read call; found {callees}"
    )


def test_ratchet_bites_on_a_planted_kind_aware_lenient_read_call() -> None:
    """The detector FLAGS a planted ``resolve_planning_read_dir(...)`` call too.

    The second target primitive (kind-aware but lenient -- never raises
    ``CoordinationBranchDeleted``) must be caught by the same grammar, not
    just the kind-blind one.
    """
    fixture_source = (
        "def _new_lenient_bypass_site(root, slug, kind):\n"
        "    feature_dir = resolve_planning_read_dir(root, slug, kind=kind)\n"
        "    return feature_dir\n"
    )
    findings = _scan_read_bypass(
        fixture_source, _REPO_ROOT / "src" / "specify_cli" / "manifest.py"
    )
    callees = {f.callee for f in findings}
    assert "resolve_planning_read_dir" in callees, (
        f"ratchet failed to flag a planted kind-aware-lenient read call; found {callees}"
    )


def test_ratchet_ignores_a_prose_only_mention() -> None:
    """A docstring/comment mention of either symbol stays GREEN.

    The forbidden grammar is a call CONSTRUCTION (an ``ast.Call`` node), not a
    textual pattern -- a docstring or comment that merely NAMES
    ``candidate_feature_dir_for_mission`` / ``resolve_planning_read_dir`` (to
    describe the very seam this gate enforces, for example) is inert prose,
    never a ``Call`` node, and must NOT be flagged. This is exactly the
    discrimination the WP02 ledger's own AST census had to get right (3 false
    positives out of 93 raw textual hits).
    """
    prose_only = (
        "def _documents_the_seam(root, slug):\n"
        '    """This function used to call candidate_feature_dir_for_mission\n'
        "    directly; it now routes through resolve_planning_read_dir only in\n"
        '    this docstring\'s narrative, never as real code."""\n'
        "    # historical: resolve_planning_read_dir(root, slug, kind=kind)\n"
        "    return placement_seam(root, slug).read_dir(kind)\n"
    )
    findings = _scan_read_bypass(
        prose_only, _REPO_ROOT / "src" / "specify_cli" / "manifest.py"
    )
    assert findings == [], (
        f"a prose-only mention of a read-bypass primitive was flagged: {findings!r}"
    )


#: The write gate module this symmetry meta-test cross-checks against.
_WRITE_GATE_PATH = Path(__file__).resolve().parent / "test_no_write_side_rederivation.py"


def _imports_shared_scan_scope(source: str) -> bool:
    """``True`` iff ``source`` contains
    ``from tests.architectural._placement_whole_tree_scan import scan_scope``
    (any alias) -- the ONE shared walker import, never a re-implementation.
    """
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.ImportFrom)
            and node.module == "tests.architectural._placement_whole_tree_scan"
            and any(alias.name == "scan_scope" for alias in node.names)
        ):
            return True
    return False


def test_read_and_write_gates_share_the_same_scan_scope() -> None:
    """Symmetry meta-test: the read gate and write gate consume the SAME
    ``scan_scope()`` object -- not merely an equal-valued copy.

    Proven two ways:

    1. Runtime identity on THIS module's own import: ``_whole_tree_scan_scope``
       (this gate's alias) IS the ``_placement_whole_tree_scan.scan_scope``
       function object -- Python caches modules, so every importer of a given
       module-level name gets the SAME object, never a copy.
    2. Structural proof for the write gate: its source imports ``scan_scope``
       from the identical shared module (never a re-implementation) -- parsed
       via AST rather than reaching into the write gate module's private
       runtime alias (which strict mypy correctly refuses to treat as a public
       re-export; a source-level check avoids that private-interface reach
       entirely while still proving the SAME shared function is consumed, by
       Python's own module-caching guarantee).

    Together these rule out a future refactor that quietly forks a second
    walker in either gate.
    """
    import tests.architectural._placement_whole_tree_scan as _placement_whole_tree_scan

    assert _whole_tree_scan_scope is _placement_whole_tree_scan.scan_scope, (
        "this gate's imported scan_scope is not the shared "
        "_placement_whole_tree_scan.scan_scope function object"
    )

    assert _WRITE_GATE_PATH.exists(), f"write gate module missing: {_WRITE_GATE_PATH}"
    write_gate_source = _WRITE_GATE_PATH.read_text(encoding="utf-8")
    assert _imports_shared_scan_scope(write_gate_source), (
        "the write gate no longer imports scan_scope from the shared "
        "tests.architectural._placement_whole_tree_scan module -- NFR-003 "
        "requires both gates to consume the SAME shared whole-tree walker, "
        "never a forked second walk"
    )


# ---------------------------------------------------------------------------
# Sanctioned-module meta-tests (FR-003: asserted, not silently skipped).
# ---------------------------------------------------------------------------


def test_read_sanctioned_modules_carry_a_rationale() -> None:
    """Every ``_READ_SANCTIONED_MODULES`` entry has a non-empty inline rationale.

    A sanctioned exclusion with no rationale is unauditable -- it cannot be
    told apart from a lazy escape hatch (mirrors the write gate's
    ``test_sanctioned_modules_carry_a_rationale``).
    """
    for rel, rationale in _READ_SANCTIONED_MODULES.items():
        assert isinstance(rationale, str) and rationale.strip(), (
            f"_READ_SANCTIONED_MODULES entry {rel!r} has no non-empty inline "
            "rationale -- every sanctioned-primitive exclusion must carry a "
            "justification."
        )


def test_read_sanctioned_modules_are_excluded_from_the_read_scan_scope() -> None:
    """None of the three sanctioned infra modules ever enters ``_read_side_scan_scope()``.

    Asserted directly (FR-003 "asserted, not silently skipped") rather than
    relying on incidental overlap with the write-side
    ``BOUNDARY_SANCTIONED_PREFIXES`` blanket (which only happens to cover
    ``write_target_degrade.py``, not the other two).
    """
    scanned_rel = {_placement_rel_path(p) for p in _read_side_scan_scope()}
    for sanctioned in _READ_SANCTIONED_MODULES:
        assert sanctioned not in scanned_rel, (
            f"{sanctioned} is a read-sanctioned infra module and must never "
            "enter the read-side bypass scan scope"
        )


def test_read_sanctioned_modules_have_real_findings_that_would_otherwise_red() -> None:
    """The sanction is not vacuous: each of the three modules DOES contain a
    real read-bypass call site that would red the main ratchet if scanned.

    Proves the exclusion is doing real work, not decorating a module that
    never needed it in the first place.
    """
    for rel in _READ_SANCTIONED_MODULES:
        module = _REPO_ROOT / rel
        assert module.exists(), f"read-sanctioned module missing: {module}"
        findings = _scan_read_bypass_module(module)
        assert findings, (
            f"{rel} is read-sanctioned but has ZERO real read-bypass call "
            "sites -- the sanction is vacuous; confirm this module still "
            "needs the exclusion."
        )


# ---------------------------------------------------------------------------
# Allow-list shape + non-vacuity meta-tests.
# ---------------------------------------------------------------------------


def test_allow_list_is_content_addressed_not_a_blanket_file_escape() -> None:
    """The allow-list keys are ``(rel_path, qualname, token_line)`` composites,
    never bare paths (C-003: no file-scoped blanket exemptions).

    ``dossier/api.py`` carries THREE distinct allow-list entries (different
    qualnames, same file) -- proof this is qualname/line-scoped granularity,
    not a whole-file escape: a fourth, un-listed bypass added anywhere else in
    that file would still red the main ratchet.
    """
    assert _ALLOW_LIST, "the allow-list must seed the ledger's stay-lenient residuals"
    for entry in _ALLOW_LIST:
        # A fixed-arity tuple shape check (the composite key IS always a
        # 3-tuple by construction, per CompositeKey) -- genuinely
        # cardinality-only, not a nameable-member collection a set/frozenset
        # equality could strengthen.
        assert isinstance(entry, tuple) and len(entry) == 3, (  # golden-count: cardinality-is-contract
            f"allow-list entry must be a (rel_path, qualname, token_line) "
            f"composite, got {entry!r}"
        )
        rel_path, qualname, token_line = entry
        assert isinstance(rel_path, str) and rel_path, (
            f"rel_path component must be a non-empty str, got {rel_path!r}"
        )
        assert isinstance(qualname, str) and qualname, (
            f"qualname component must be a non-empty str, got {qualname!r}"
        )
        assert isinstance(token_line, str) and token_line, (
            "token_line component must be a non-empty code line, never a "
            f"whole-file wildcard, got {token_line!r}"
        )

    dossier_api_qualnames = {
        descriptor.qualname
        for descriptor in _ALLOW_LIST_SEED
        if descriptor.rel_path == "src/specify_cli/dossier/api.py"
    }
    # Exact member-name equality (not a bare count): pins WHICH three handlers
    # are allow-listed, so a rename/drop/add of any one of them fails loudly
    # here rather than silently passing at an unchanged count.
    assert dossier_api_qualnames == {
        "DossierAPIHandler.handle_dossier_overview",
        "DossierAPIHandler.handle_dossier_snapshot_export",
        "DossierAPIHandler._load_dossier",
    }, (
        "expected exactly these 3 qualname-scoped entries for dossier/api.py "
        f"(proof of line-scoping, not a file-scoped escape), got "
        f"{dossier_api_qualnames!r}"
    )


@pytest.mark.parametrize(
    "descriptor",
    _ALLOW_LIST_SEED,
    ids=[f"{d.rel_path}::{d.qualname}" for d in _ALLOW_LIST_SEED],
)
def test_allow_list_entry_is_still_a_live_finding(descriptor: ContentDescriptor) -> None:
    """Staleness twin-guard (FR-006 / NFR-004): every seeded descriptor still
    resolves to its live finding.

    If a residual site is finally routed through the seam (or removed),
    :func:`descriptor_still_live` returns ``False`` (0 matches, or a
    key-inequality) and this test fails loudly -- the fix is to DELETE the
    now-stale allow-list entry (shrink-only governance), never to leave a
    vacuous allow-list rule masking nothing. Exactly-one + key-equal: NEVER
    "≥1 finding matches" (the D-1 bite hole).
    """
    seed_index = _ALLOW_LIST_SEED.index(descriptor)
    seeded_key = _ALLOW_LIST_KEYS[seed_index]
    source = (_REPO_ROOT / descriptor.rel_path).read_text(encoding="utf-8")
    assert descriptor_still_live(source, descriptor, seeded_key), (
        f"{descriptor.rel_path} ({descriptor.qualname}) no longer resolves to "
        "its seeded live read-bypass finding -- the site was routed through "
        "the seam (or removed); DELETE this now-stale allow-list entry "
        "(shrink-only, never leave a vacuous rule)."
    )
