"""Structural read-side gate — no read-side placement-seam bypass (WP08 / IC-06).

read-side-placement-seam-migration-01KYHP67, FR-005 / FR-006 / NFR-003 /
NFR-004: the CAPSTONE structural gate over the TWO read-bypass primitives this
mission censused — ``candidate_feature_dir_for_mission`` and
``resolve_planning_read_dir`` — mirroring the write-side structural gate
(``test_no_write_side_rederivation.py``'s
``test_adopted_and_residual_modules_have_no_checkout_derived_commit_target``
whole-tree AST scan). This is NOT modeled on the *behavioral*
``test_read_surface_placement_guard.py`` — it is the symmetric structural
analog of the write gate.

Scope of the guarantee (honest bounds — do NOT overstate)
----------------------------------------------------------
This gate makes a new call to **either of the two ledger-censused primitives**
un-addable outside the sanctioned + allow-listed sets. It does NOT make every
conceivable read-side bypass "unrepresentable":

- **Covered**: bare-``Name`` calls, ``Attribute.attr`` calls (``mod.symbol(...)``),
  and **import-aliased** calls (``from ... import X as _alias`` → ``_alias(...)``),
  which ``_import_alias_map`` resolves back to the origin symbol.
- **Known gap — ``primary_feature_dir_for_mission``**: a topology-blind sibling
  primitive in the same module with ~40 unpoliced call sites in ``src/``.
  Widening ``_TARGET_CALLEE_NAMES`` to include it would require a comparably
  sized allow-list census and is tracked as issue #3014 (under epic #1878),
  NOT covered here. See the ledger's "Known gap" section.
- **Known gap — local rebinding**: ``_alias = candidate_feature_dir_for_mission``
  followed by ``_alias(...)`` is value-flow, not import aliasing, and is not
  resolved.

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
``Name``, ``Attribute.attr``, or an ``ImportFrom``/``Import`` alias resolved
back to its origin symbol). Callee identity IS the finding — reads have no
``ref`` argument to value-flow-trace, so no "seam-derived" discriminator is
needed (unlike the write gate's ``CommitTarget(ref=...)`` grammar). A
docstring/comment merely NAMING one of these symbols never becomes an
``ast.Call`` node and is therefore never flagged (the bite test below proves
this).

Allow-list (T018) — the ledger is the ONE authority, mechanically
------------------------------------------------------------------
``docs/development/read-side-seam-classification.md`` (WP02) is the single
authority for WHICH sites stay lenient and HOW MANY there are. This module
does not restate those numbers: it PARSES the ledger (``_ledger_summary_counts``
+ ``_ledger_stay_lenient_index``) and reconciles ``_ALLOW_LIST_SEED`` against
it, so editing the ledger's Summary table or its machine-checked stay-lenient
index REDS this gate. ``_ALLOW_LIST_SEED`` contributes only the per-site
*content descriptors* (token substrings + condensed rationale) that markdown
cannot carry; its membership and cardinality are ledger-derived, not
independently declared. Content-descriptor allow-listing (``_ratchet_keys.resolve_descriptor``,
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

# ``docs_scoped``: this gate parses the classification ledger under ``docs/``
# as its authority for the stay-lenient allow-list, so a docs-only PR must
# still select it.
pytestmark = [pytest.mark.architectural, pytest.mark.docs_scoped]

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


def _import_alias_map(tree: ast.Module) -> dict[str, str]:
    """Map every module-level import ALIAS to the origin symbol it binds.

    ``from ..._read_path_resolver import candidate_feature_dir_for_mission as _cfd``
    binds the local name ``_cfd`` to the origin symbol
    ``candidate_feature_dir_for_mission``. Without this map a call to ``_cfd(...)``
    presents as an unrelated ``Name.id`` and silently un-polices the site (and
    invalidates any content-descriptor allow-list entry keyed on the old token
    line). Resolving the alias back to its origin closes that escape.

    Only ``Name`` callees are alias-resolved by the caller; ``Attribute.attr``
    lives in a different namespace (``obj.attr``), so applying the same map
    there could false-positive on an unrelated method of the same name.
    """
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.asname:
                    aliases[alias.asname] = alias.name
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.asname:
                    aliases[alias.asname] = alias.name.rsplit(".", 1)[-1]
    return aliases


def _callee_name(call: ast.Call, aliases: dict[str, str]) -> str | None:
    """Return the origin callee identifier for bare-name OR attribute call forms.

    A bare ``Name`` is resolved through ``aliases`` (the module's import-alias
    map) so an ``import ... as _alias`` rename cannot un-police a call site.
    """
    func = call.func
    if isinstance(func, ast.Name):
        return aliases.get(func.id, func.id)
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

    Import aliases are resolved back to their origin symbol first (see
    :func:`_import_alias_map`), so an ``import ... as _alias`` rename cannot
    hide a call site from this walk.
    """
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return []
    aliases = _import_alias_map(tree)
    findings: list[_Finding] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            callee = _callee_name(node, aliases)
            if callee in _TARGET_CALLEE_NAMES:
                findings.append(_Finding(path, node.lineno, callee, source))
    return findings


def _scan_read_bypass_module(path: Path) -> list[_Finding]:
    return _scan_read_bypass(path.read_text(encoding="utf-8"), path)


# ---------------------------------------------------------------------------
# T018 — allow-list: every stay-lenient residual from the WP02 ledger.
# ---------------------------------------------------------------------------

#: The WP02 classification ledger -- the ONE authority for which sites stay
#: lenient and how many there are. Parsed live below (never restated here as a
#: hand-synced literal): perturbing either the § Summary counts or the
#: § "Stay-lenient allow-list index (machine-checked)" table REDS this gate.
_LEDGER_PATH = _REPO_ROOT / "docs" / "development" / "read-side-seam-classification.md"

#: Heading of the ledger's machine-checked ``rel_path | qualname`` index table.
_LEDGER_INDEX_HEADING = "## Stay-lenient allow-list index (machine-checked)"

#: Heading of the ledger's verdict-count Summary table.
_LEDGER_SUMMARY_HEADING = "## Summary"


def _markdown_table_rows(text: str, heading: str) -> list[list[str]]:
    """Return the pipe-table cell rows under ``heading`` (header + separator dropped).

    Reads only the FIRST table in the section and stops at the next ``##``
    heading, so an unrelated later table can never be silently absorbed. Cells
    are stripped of surrounding whitespace, backticks and bold markers so the
    ledger stays human-readable markdown while remaining machine-checkable.
    """
    lines = text.splitlines()
    try:
        start = lines.index(heading)
    except ValueError as exc:
        raise AssertionError(
            f"ledger {_LEDGER_PATH.name} has no {heading!r} section -- the gate "
            "parses it as the authority for the stay-lenient census"
        ) from exc
    rows: list[list[str]] = []
    for line in lines[start + 1 :]:
        stripped = line.strip()
        if stripped.startswith("## "):
            break
        if not stripped.startswith("|"):
            if rows:
                break
            continue
        cells = [cell.strip().strip("`").strip("*").strip() for cell in stripped.strip("|").split("|")]
        if all(set(cell) <= {"-", ":"} and cell for cell in cells):
            continue  # the |---|---| separator row
        rows.append(cells)
    return rows[1:] if rows else rows  # drop the header row


def _ledger_stay_lenient_index(text: str) -> frozenset[tuple[str, str]]:
    """The ledger's authoritative ``(rel_path, qualname)`` stay-lenient membership."""
    rows = _markdown_table_rows(text, _LEDGER_INDEX_HEADING)
    return frozenset((row[0], row[1]) for row in rows if len(row) >= 2)


def _ledger_summary_counts(text: str) -> dict[str, tuple[int, int]]:
    """Parse the ledger's § Summary verdict table into ``verdict -> (sites, files)``.

    Rows whose site/file cells are not both plain integers (the ``No real call
    site`` / ``Grand total`` rows carry a blank cell) are skipped -- only the
    three verdict rows and the total row are needed.
    """
    counts: dict[str, tuple[int, int]] = {}
    for row in _markdown_table_rows(text, _LEDGER_SUMMARY_HEADING):
        if len(row) < 3:
            continue
        verdict, sites, files = row[0], row[1], row[2]
        if sites.isdigit() and files.isdigit():
            counts[verdict] = (int(sites), int(files))
    return counts


#: Content-descriptor allow-list (T018): each entry is a ``stay-lenient``
#: residual from the WP02 classification ledger, derived site-for-site (never
#: invented). Membership and cardinality are ledger-DERIVED (asserted below
#: against the parsed ledger index); the entries add only the token substring
#: and condensed rationale that markdown cannot carry.
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


def _ledger_text() -> str:
    assert _LEDGER_PATH.exists(), f"WP02 classification ledger missing: {_LEDGER_PATH}"
    return _LEDGER_PATH.read_text(encoding="utf-8")


def test_allow_list_membership_is_exactly_the_ledgers_stay_lenient_index() -> None:
    """The allow-list IS the ledger's stay-lenient index -- parsed, not hand-synced.

    The ledger (``docs/development/read-side-seam-classification.md``,
    § "Stay-lenient allow-list index (machine-checked)") is the ONE authority
    for WHICH sites stay lenient. This test parses that table and asserts
    ``(rel_path, qualname)`` set equality with ``_ALLOW_LIST_SEED``, so:

    - deleting/editing/adding a ledger row without touching the seed REDS here;
    - adding a seed entry the ledger does not sanction REDS here.

    That is the mechanical link the previous count-only pin lacked (both sides
    of it lived five lines apart in THIS file, so the ledger could drift freely).
    """
    ledger_index = _ledger_stay_lenient_index(_ledger_text())
    seed_index = frozenset((d.rel_path, d.qualname) for d in _ALLOW_LIST_SEED)

    assert seed_index == ledger_index, (
        "the read gate's allow-list no longer matches the WP02 ledger's "
        "stay-lenient index (the authority).\n"
        f"  in the ledger only: {sorted(ledger_index - seed_index)}\n"
        f"  in the gate only:   {sorted(seed_index - ledger_index)}\n"
        "Fix the LEDGER first (it is the authority), then mirror the change here."
    )
    # One row per site: a file with two lenient sites must contribute two rows,
    # so a de-duplicating typo in the ledger cannot shrink the census silently.
    assert len(_ALLOW_LIST_SEED) == len(seed_index), (
        "duplicate (rel_path, qualname) in _ALLOW_LIST_SEED -- the ledger index "
        "is one row per SITE and cannot address two sites in one qualname"
    )


def test_ledger_parser_fails_loud_when_the_authority_section_is_removed() -> None:
    """Deleting the ledger's machine-checked section REDS -- it never parses to empty.

    The dangerous failure mode for a parse-the-docs gate is a SILENT one: if a
    missing heading yielded an empty row list, ``ledger_index`` would be the
    empty set and the membership assertion would degrade into "the seed must
    also be empty" -- or worse, a renamed section would quietly un-police the
    allow-list. ``_markdown_table_rows`` raises instead.
    """
    text_without_index = _ledger_text().replace(_LEDGER_INDEX_HEADING, "## Something Else")

    with pytest.raises(AssertionError, match="Stay-lenient allow-list index"):
        _ledger_stay_lenient_index(text_without_index)


def test_ledger_summary_counts_reconcile_with_the_allow_list_and_themselves() -> None:
    """The ledger's § Summary stay-lenient counts bind the allow-list's shape.

    Two independent reconciliations, both against the PARSED ledger:

    1. ``stay-lenient`` sites/files == the allow-list's site count and distinct
       file count. Editing ``| stay-lenient | 16 | 11 |`` REDS here.
    2. The ledger is internally consistent: migrate + stay-lenient +
       sanction-infra sites/files == the ``Total real call sites`` row, so a
       Summary edit cannot be "balanced" by silently mis-stating the total.
    """
    counts = _ledger_summary_counts(_ledger_text())
    for verdict in ("migrate-fail-loud", "stay-lenient", "sanction-infra", "Total real call sites"):
        assert verdict in counts, (
            f"ledger § Summary has no parseable {verdict!r} row; parsed {sorted(counts)}"
        )

    lenient_sites, lenient_files = counts["stay-lenient"]
    assert lenient_sites == len(_ALLOW_LIST_SEED), (
        f"ledger § Summary declares {lenient_sites} stay-lenient sites but the "
        f"allow-list carries {len(_ALLOW_LIST_SEED)} entries"
    )
    assert lenient_files == len({d.rel_path for d in _ALLOW_LIST_SEED}), (
        f"ledger § Summary declares {lenient_files} stay-lenient files but the "
        f"allow-list spans {len({d.rel_path for d in _ALLOW_LIST_SEED})}"
    )

    verdict_sites = sum(
        counts[v][0] for v in ("migrate-fail-loud", "stay-lenient", "sanction-infra")
    )
    total_sites, _total_files = counts["Total real call sites"]
    assert verdict_sites == total_sites, (
        f"ledger § Summary verdict rows sum to {verdict_sites} sites but the "
        f"total row declares {total_sites} -- the census no longer adds up"
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


def test_ratchet_bites_on_an_import_aliased_bypass() -> None:
    """An ``import ... as _alias`` rename must NOT un-police a call site.

    Before ``_import_alias_map``, this exact fixture returned ZERO findings:
    ``_callee_name`` matched only the literal ``Name.id`` / ``Attribute.attr``
    token, so renaming the import at the top of a module silently removed the
    site from the gate's view AND invalidated any content-descriptor allow-list
    entry keyed on the old token line. Both alias forms (``from X import Y as
    Z`` and a plain module ``import ... as``) are covered.
    """
    fixture_source = (
        "from ..._read_path_resolver import candidate_feature_dir_for_mission as _cfd\n"
        "from ..._read_path_resolver import resolve_planning_read_dir as _rpd\n"
        "\n"
        "def _aliased_bypass(root, slug, kind):\n"
        "    a = _cfd(root, slug)\n"
        "    b = _rpd(root, slug, kind=kind)\n"
        "    return a, b\n"
    )
    findings = _scan_read_bypass(
        fixture_source, _REPO_ROOT / "src" / "specify_cli" / "manifest.py"
    )
    callees = sorted(f.callee for f in findings)
    assert callees == ["candidate_feature_dir_for_mission", "resolve_planning_read_dir"], (
        f"the gate failed to resolve import-aliased read bypasses; found {callees}"
    )


def test_ratchet_does_not_flag_an_alias_that_shadows_a_target_name() -> None:
    """Aliasing is resolved to the ORIGIN symbol, not matched on the local name.

    ``from x import unrelated as candidate_feature_dir_for_mission`` binds a
    target-looking local name to a non-target origin. Resolving to the origin
    (rather than pattern-matching the token) keeps the grammar honest in both
    directions -- no false positive here, and no false negative above.
    """
    fixture_source = (
        "from somewhere import unrelated_helper as candidate_feature_dir_for_mission\n"
        "\n"
        "def _not_a_bypass(root, slug):\n"
        "    return candidate_feature_dir_for_mission(root, slug)\n"
    )
    findings = _scan_read_bypass(
        fixture_source, _REPO_ROOT / "src" / "specify_cli" / "manifest.py"
    )
    assert findings == [], (
        f"an alias bound to a NON-target origin symbol was flagged: {findings!r}"
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
    """Symmetry meta-test: the write gate consumes the SAME shared walker this
    gate does -- never a forked second walk.

    This gate's own consumption is proven by its module-level ``from
    tests.architectural._placement_whole_tree_scan import scan_scope`` (an
    identity assertion on that import would be true by construction and cannot
    fail, so it is not made here). What CAN drift is the write gate: its source
    is parsed via AST to confirm it still imports ``scan_scope`` from the
    identical shared module, rather than reaching into the write gate module's
    private runtime alias (which strict mypy correctly refuses to treat as a
    public re-export). Python's module cache then guarantees both importers
    hold the same function object.
    """
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
# Allow-list staleness twin-guard.
#
# (The former ``test_allow_list_is_content_addressed_not_a_blanket_file_escape``
# is gone: its tuple-shape asserts were true by construction -- ``CompositeKey``
# IS a 3-tuple of non-empty strings by the resolver's own contract -- and its
# one load-bearing assertion, that ``dossier/api.py`` is allow-listed at THREE
# distinct qualnames rather than as a whole file, is now subsumed by
# ``test_allow_list_membership_is_exactly_the_ledgers_stay_lenient_index``,
# which pins every (rel_path, qualname) pair against the ledger by set equality.)
# ---------------------------------------------------------------------------


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
