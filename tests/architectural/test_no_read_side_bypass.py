"""Structural read-side gate — no read-side placement-seam bypass (WP08 / IC-06).

read-side-placement-seam-migration-01KYHP67, FR-005 / FR-006 / NFR-003 /
NFR-004: the CAPSTONE structural gate over the read-bypass primitives this
mission censused — mirroring the write-side structural gate
(``test_no_write_side_rederivation.py``'s
``test_adopted_and_residual_modules_have_no_checkout_derived_commit_target``
whole-tree AST scan). This is NOT modeled on the *behavioral*
``test_read_surface_placement_guard.py`` — it is the symmetric structural
analog of the write gate.

read-side-seam-primary-primitive-closure-01KYKMMT, WP02 (FR-012): the censused
callee set grew **2 → 4** here — ``resolve_feature_dir_for_mission`` (the one
resolver no prior gate covered, #3014) and ``primary_feature_dir_for_mission``
(which inherits the guarantee transferred from WP01's retired use-count
floors) join the original two. Growing the census makes the 34 real
``primary_feature_dir_for_mission`` call sites -- minus the 3 newly sanctioned
FR-005 foundation sites (31 remain), plus the one newly-classified
``migrate-fail-loud`` ``resolve_feature_dir_for_mission`` site (32 total) --
**expected red** until a later WP routes them. That red is this mission's
acceptance signal (US8 / FR-023), not a defect.

Post-merge aggregate-squad closeout (fix/read-side-seam-primary-primitive-
closure follow-up, cross-lane integration lens): the censused callee set grew
**4 → 5** here — ``_compose_primary_feature_dir``, the module-private leaf
WP03 extracted and WP08 re-pointed the deleted public wrapper's foundation
callers onto, joins the four above. Before this closeout the leaf was censused
ONLY via ``_LEAF_PRIMITIVE_ALIASES`` bookkeeping, never a member of
``_TARGET_CALLEE_NAMES`` itself, so the gate enforced the deleted wrapper's
*dead name* (zero live call sites, permanently) while the *live leaf* carried
no census entry at all -- a module outside the five named foundation sites
could import it directly and call it with a canonical handle, reopening the
exact canonical-handle + caller-chosen-partition bypass this mission exists to
end, invisibly to this gate. See ``docs/development/reference/read-side-seam-classification.md``'s
"Post-merge closeout" section for the full record.

Scope of the guarantee (honest bounds — do NOT overstate)
----------------------------------------------------------
This gate makes a new call to **any of the five ledger-censused primitives**
un-addable outside the sanctioned + allow-listed sets. It does NOT make every
conceivable read-side bypass "unrepresentable":

- **Covered**: bare-``Name`` calls, ``Attribute.attr`` calls (``mod.symbol(...)``),
  and **import-aliased** calls (``from ... import X as _alias`` → ``_alias(...)``),
  which ``_import_alias_map`` resolves back to the origin symbol.
- **Known gap — ``resolve_feature_dir_for_slug``**: a zero-call-site latent
  sibling in the same module. Not censused (nothing to census); importing it
  anywhere would silently re-open the gap this gate closes for its siblings.
  See the ledger's "Known gap" section.
- **Known gap — wrapper laundering**: ``resolve_subtasks_gate_dir`` wraps a
  censused primitive behind a pinned-kind call; a callee-name census cannot
  see through the wrapper. See the ledger's "Known gap" section.
- **Known gap — local rebinding**: ``_alias = candidate_feature_dir_for_mission``
  followed by ``_alias(...)`` is value-flow, not import aliasing, and is not
  resolved.

Contract: ``kitty-specs/read-side-placement-seam-migration-01KYHP67/
contracts/read-side-gate.md`` and ``kitty-specs/
read-side-seam-primary-primitive-closure-01KYKMMT/contracts/ledger-grammar.md``
/ ``gate-extension.md``.

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
``docs/development/reference/read-side-seam-classification.md`` (WP02) is the single
authority for WHICH sites stay lenient and HOW MANY there are. This module
does not restate those numbers: it PARSES the ledger (``_ledger_summary_counts``
+ ``_ledger_stay_lenient_index``) and reconciles ``_ALLOW_LIST_SEED`` against
it, so editing the ledger's live-census Summary table or its machine-checked
stay-lenient index REDS this gate. ``_ALLOW_LIST_SEED`` contributes only the
per-site *content descriptors* (token substrings + condensed rationale) that
markdown cannot carry; its membership and cardinality are ledger-derived, not
independently declared. Content-descriptor allow-listing (``_ratchet_keys.resolve_descriptor``,
the SAME resolver WS1/WS2/WS3/checkout-grammar entries in the write gate use):
``(rel_path, qualname, token_substring)`` resolves LIVE to exactly one finding's
``(rel_path, qualname, token_line)`` composite key — never a bare path (C-003:
no file-scoped blanket exemptions). Shrink-only: a staleness twin-guard REDS
the moment a routed/removed entry stops resolving to its seeded key (FR-006 /
NFR-004) — the fix is to DELETE the stale entry, never leave a vacuous rule.

Per-site index discriminator (WP02 T009, G2) — ``primitive`` + ``site token``
----------------------------------------------------------------------------
The stay-lenient index is keyed per **site**, not per function: a qualname can
carry SEVERAL censused sites of the SAME primitive
(``status/aggregate.py::MissionStatus._find_meta_path`` alone carries one
existing ``candidate_feature_dir_for_mission`` site plus three
newly-censused ``primary_feature_dir_for_mission`` sites — SC-015's
acceptance fixture, see ``test_index_discriminator_represents_a_four_site_qualname``
below). A trailing ``primitive`` column alone is NOT sufficient to address
this case: the three ``primary_feature_dir_for_mission`` sites inside that
one qualname would still collapse onto ONE ``(rel_path, qualname, primitive)``
key. ``_entry_primitive`` derives the ``primitive`` discriminator from each
entry's own ``token_substring`` (never restated as a separate hand-synced
field — the token substring already names its callee); a SECOND trailing
column, the site's own normalised ``token_substring`` verbatim, then
discriminates several same-primitive sites sharing one qualname (anchored on
qualname + normalised token, never a line number — DIRECTIVE_041). The
ledger's index table therefore gains a third AND a fourth trailing column
(``primitive``, ``site token`` — G1: both appended, never inserted) and the
membership/uniqueness checks below key on the resulting
``(rel_path, qualname, primitive, site_token)`` 4-tuple.

Foundation-site sanctions (WP02 T011, E3) — per-site, never a module blanket
------------------------------------------------------------------------------
``core/paths.py`` (×2) and ``core/git_ops.py`` (×1) call
``primary_feature_dir_for_mission`` from beneath the seam's own composition
root (NFR-009: routing them risks a resolution cycle). Neither module is
otherwise a sanctioned-infra module — both carry substantial unrelated logic
— so whole-module sanctioning would be exactly the path-scoped blanket C-003
forbids. ``_FOUNDATION_SANCTION_SEED`` sanctions these THREE sites
individually (the same content-descriptor mechanism as the allow-list, a
separate ledger-reconciled table so foundation-infra counts never blend into
the stay-lenient business-logic counts). The fourth named FR-005 foundation
site, ``coordination/surface_resolver.py``, is already a whole-module
sanctioned entry in ``_READ_SANCTIONED_MODULES`` (both primitives' calls there
are covered by the existing per-file rationale).
"""

from __future__ import annotations

import ast
import re
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

#: The five kind-blind / lenient-kind-aware read bypass primitives this gate
#: forbids outside the sanctioned + allow-listed sets (contract "Finding").
#: WP02 (FR-012) grew this 2 -> 4: ``resolve_feature_dir_for_mission`` (the one
#: resolver no prior gate covered, #3014) and ``primary_feature_dir_for_mission``
#: (receiving the guarantee transferred from WP01's retired use-count floors)
#: join the original two.
#:
#: Post-merge aggregate-squad closeout (fix/read-side-seam-primary-primitive-
#: closure follow-up) grew this 4 -> 5: ``_compose_primary_feature_dir``, the
#: module-private leaf WP03 extracted and WP08 re-pointed the deleted public
#: wrapper's foundation callers onto. Before this closeout the leaf was
#: censused ONLY via ``_LEAF_PRIMITIVE_ALIASES`` bookkeeping (see below) --
#: never a member of this set -- so the gate enforced the *deleted wrapper's
#: dead name* (zero live call sites) while the *live leaf itself* carried no
#: census entry at all: a module outside the five named foundation sites could
#: import ``_compose_primary_feature_dir`` directly and call it with a
#: canonical handle, reopening the exact canonical-handle +
#: caller-chosen-partition bypass shape this mission exists to end, invisibly
#: to this gate. Adding it here closes that gap (see
#: ``test_ratchet_bites_on_a_planted_leaf_primitive_call_outside_sanctioned_modules``).
_TARGET_CALLEE_NAMES: frozenset[str] = frozenset(
    {
        "candidate_feature_dir_for_mission",
        "resolve_planning_read_dir",
        "resolve_feature_dir_for_mission",
        "primary_feature_dir_for_mission",
        "_compose_primary_feature_dir",
    }
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
#:   ``resolve_planning_read_dir`` (:1438) and ``resolve_subtasks_gate_dir``
#:   (:1479, via ``resolve_planning_read_dir``) to compose its own public
#:   surface -- self-reference, not a bypass (the primitive authority itself,
#:   per FR-003; excluded from the ledger's consumer census entirely for the
#:   same reason).
#: - ``coordination/surface_resolver.py`` (:675 / :739,
#:   ``resolve_status_surface_with_anchor``) is the canonical surface resolver
#:   infra that ``candidate_feature_dir_for_mission`` is partly built to serve
#:   -- FR-003 names this module explicitly. WP02 (FR-012 E3): it also calls
#:   the newly-censused ``primary_feature_dir_for_mission`` (:739) as one of
#:   the four named FR-005 foundation sites -- the SAME rationale covers both
#:   primitives (per-primitive non-vacuity for this module is asserted below).
#: - ``mission_runtime/write_target_degrade.py`` (:183,
#:   ``resolve_write_target_or_degrade``'s bootstrap-window existence probe) is
#:   ALREADY excluded from ``scan_scope()`` via the shared
#:   ``BOUNDARY_SANCTIONED_PREFIXES`` ``src/mission_runtime/`` blanket; this
#:   entry restores the individual, rationale-bearing accountability the
#:   write-side ``_placement_whole_tree_scan`` module docstring itself calls
#:   out for this exact file, so the read gate's own sanctioned-module test
#:   (below) can assert it directly rather than it going unpoliced behind the
#:   package-wide prefix.
#: - ``mission_runtime/resolution.py`` (the seam itself: ``PlacementSeam.read_dir``)
#:   is ALSO already excluded via the same ``src/mission_runtime/``
#:   ``BOUNDARY_SANCTIONED_PREFIXES`` blanket. WP02 (FR-012 E3, "resolver-internal
#:   sites"): it composes its own PRIMARY-partition leg by calling BOTH
#:   ``primary_feature_dir_for_mission`` (4 internal sites) and (pre-existing)
#:   ``resolve_planning_read_dir`` -- self-reference, not a bypass, mirroring
#:   ``_read_path_resolver.py``'s own self-exclusion. This entry restores the
#:   individual, rationale-bearing accountability for the seam module, the same
#:   way the write-side degrade-helper entry above does for its file, so the
#:   per-primitive non-vacuity meta-test can assert it directly.
_READ_SANCTIONED_MODULES: dict[str, str] = {
    "src/specify_cli/missions/_read_path_resolver.py": (
        "The primitive authority itself: defines all four censused "
        "primitives (candidate_feature_dir_for_mission, "
        "resolve_planning_read_dir, resolve_feature_dir_for_mission, "
        "primary_feature_dir_for_mission), and resolve_planning_read_dir "
        "calls candidate_feature_dir_for_mission and "
        "primary_feature_dir_for_mission internally to compose its own "
        "partition legs -- a self-reference, not a bypass. Excluded from the "
        "WP02 classification ledger's consumer census for the same reason "
        "(FR-003)."
    ),
    "src/specify_cli/coordination/surface_resolver.py": (
        "The canonical surface resolver (resolve_status_surface_with_anchor "
        "et al., :675) that candidate_feature_dir_for_mission is partly built "
        "to serve; FR-003 names this module explicitly as sanctioned infra, "
        "not a bypass site awaiting a route. WP02 (FR-012 E3): it also calls "
        "the newly-censused primary_feature_dir_for_mission (:739) as its own "
        "PRIMARY anchor -- one of the four named FR-005 foundation sites, "
        "already covered by this whole-module sanction rather than needing a "
        "separate per-site entry."
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
    "src/mission_runtime/resolution.py": (
        "The read-side seam itself (PlacementSeam.read_dir / "
        "resolve_artifact_surface) -- already excluded from scan_scope() via "
        "the shared src/mission_runtime/ BOUNDARY_SANCTIONED_PREFIXES "
        "blanket. WP02 (FR-012 E3, 'resolver-internal sites'): it calls "
        "primary_feature_dir_for_mission internally (four sites: the "
        "mid8/coordination-branch/topology/mission-id resolution helpers) to "
        "compose its own PRIMARY-partition leg -- a self-reference, not a "
        "bypass. This per-file entry restores the individual, "
        "rationale-bearing accountability for the seam module, mirroring the "
        "write-side degrade-helper entry above, so this gate's own "
        "per-primitive non-vacuity meta-test asserts it directly rather than "
        "it going unpoliced behind the package-wide prefix."
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
# T008/T018 — ledger grammar: one table per heading, fail loud, never silent.
# ---------------------------------------------------------------------------

#: The WP02 classification ledger -- the ONE authority for which sites stay
#: lenient and how many there are. Parsed live below (never restated here as a
#: hand-synced literal): perturbing either the live-census Summary counts or
#: the § "Stay-lenient allow-list index (machine-checked)" table REDS this
#: gate.
_LEDGER_PATH = _REPO_ROOT / "docs" / "development" / "reference" / "read-side-seam-classification.md"

#: Heading of the ledger's machine-checked ``rel_path | qualname | primitive``
#: index table (G2: the stay-lenient index, keyed per SITE).
_LEDGER_INDEX_HEADING = "## Stay-lenient allow-list index (machine-checked)"

#: Heading of the ledger's machine-checked foundation-sanction index table
#: (WP02 T011/E3: the 3 per-site FR-005 foundation entries -- core/paths.py x2,
#: core/git_ops.py x1 -- that cannot be whole-module sanctioned, C-003).
_LEDGER_FOUNDATION_HEADING = "## Foundation-site sanctions (machine-checked)"

#: Heading of the ledger's LIVE (end-state, post-migration) verdict-count
#: Summary table -- the ONE table this gate reconciles against (NFR-008: the
#: gate parses the live residual/lenient totals, never the historical
#: pre-migration totals). Deliberately a DIFFERENT heading string from the
#: historical "## Summary (historical...)" table so G1's "exactly one table
#: per heading" rule cannot be satisfied by two differently-scoped tables
#: sharing one heading.
_LEDGER_SUMMARY_HEADING = "## Live census summary (machine-checked, end-state)"

#: The four verdict/bucket names the live Summary table may declare per
#: primitive (G1 rule 6: any other bucket name is accepted structurally, but
#: only these four participate in the sum-reconciliation below).
_LEDGER_VERDICT_NAMES: tuple[str, ...] = (
    "migrate-fail-loud",
    "stay-lenient",
    "sanction-infra",
    "expected-red (unrouted)",
)
_LEDGER_TOTAL_ROW_NAME = "Total real call sites"


def _markdown_table_rows(text: str, heading: str, *, expected_columns: int) -> list[list[str]]:
    """Return the pipe-table cell rows under ``heading`` (header + separator dropped).

    Reads only the FIRST table in the section (G1 rule 1) and FAILS LOUD
    (raises ``AssertionError``) rather than silently stopping if a SECOND
    pipe-table block appears later in the same section, before the next
    ``##`` heading -- the exact silent-drop failure a prior landing pass
    executed against this parser (see the module docstring). Every row MUST
    carry exactly ``expected_columns`` cells (G1 rule 4: a mid-table column
    insertion is an error, never a silent skip) -- also fails loud.
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
    first_table_ended = False
    for line in lines[start + 1 :]:
        stripped = line.strip()
        if stripped.startswith("## "):
            break
        if not stripped.startswith("|"):
            if rows:
                first_table_ended = True
            continue
        if first_table_ended:
            raise AssertionError(
                f"ledger section {heading!r} has a SECOND pipe-table after the "
                "first one ended -- G1 requires exactly one table per "
                "machine-parsed heading (a second table is silently dropped "
                "by a naive reader). Merge the extra rows into the first "
                "table, or give the second table its own heading."
            )
        cells = [cell.strip().strip("`").strip("*").strip() for cell in stripped.strip("|").split("|")]
        if all(set(cell) <= {"-", ":"} and cell for cell in cells):
            continue  # the |---|---| separator row
        if len(cells) != expected_columns:
            raise AssertionError(
                f"ledger section {heading!r} row {cells!r} has {len(cells)} "
                f"cell(s), expected exactly {expected_columns} -- G1 forbids a "
                "silently mid-table column insertion/removal"
            )
        rows.append(cells)
    return rows[1:] if rows else rows  # drop the header row


def _assert_no_duplicate_keys(keys: list[tuple[str, ...]], *, heading: str) -> None:
    """RAISE if ``keys`` (one per parsed row) contains a duplicate (G1 rule 5).

    A duplicate key silently overwrites (last-wins) if collapsed straight into
    a ``dict``/``frozenset`` -- this check runs FIRST so the collision is
    reported loudly instead.
    """
    seen: set[tuple[str, ...]] = set()
    for key in keys:
        if key in seen:
            raise AssertionError(
                f"ledger section {heading!r} has a DUPLICATE key {key!r} -- "
                "G1 forbids a silently-overwriting duplicate row"
            )
        seen.add(key)


#: read-side-seam-primary-primitive-closure-01KYKMMT WP08 (T035): the public
#: wrapper ``primary_feature_dir_for_mission`` is deleted, so the five FR-005/
#: NFR-009 foundation sites now literally call the module-private leaf
#: ``_compose_primary_feature_dir`` instead (their ``_FOUNDATION_SANCTION_SEED``
#: tokens were re-pointed in the same commit). Those sites are still the SAME
#: sanctioned foundation-infra population for the SAME censused primitive --
#: only the literal callee name changed, not what is being sanctioned -- so
#: ``_entry_primitive`` maps the leaf's name back onto its primitive for
#: bookkeeping/grouping purposes.
#:
#: Post-merge aggregate-squad closeout: the leaf is now ALSO a first-class
#: member of ``_TARGET_CALLEE_NAMES`` (``_scan_read_bypass`` DOES flag it,
#: closing the census gap the squad found -- see that set's docstring). This
#: alias mapping is NOT retired by that change: ``_entry_primitive`` checks it
#: FIRST, before the literal-name match, so the five ``_FOUNDATION_SANCTION_SEED``
#: entries whose ``token_substring`` names the leaf keep bucketing under
#: ``primary_feature_dir_for_mission`` for the ledger's bookkeeping/
#: reconciliation purposes -- preserving the historical continuity WP08
#: established -- while the RATCHET's own offender check (keyed on
#: ``(rel_path, qualname, token_line)``, never on this primitive label) is
#: completely unaffected by which bucket a sanctioned entry counts toward.
_LEAF_PRIMITIVE_ALIASES: dict[str, str] = {
    "_compose_primary_feature_dir": "primary_feature_dir_for_mission",
}


def _entry_primitive(token_substring: str) -> str:
    """The censused primitive named in ``token_substring`` (G2's trailing discriminator).

    Every ``_ALLOW_LIST_SEED`` / ``_FOUNDATION_SANCTION_SEED`` entry's
    ``token_substring`` already names its callee literally (it IS the
    normalized call token) -- deriving the discriminator from it, rather than
    hand-restating a parallel field, means the two can never drift apart.

    Alias check runs FIRST (post-merge closeout): every seed entry whose token
    names the ``_compose_primary_feature_dir`` leaf resolves to the bookkept
    ``primary_feature_dir_for_mission`` bucket, not to the leaf's own literal
    name -- even though the leaf is now ALSO a member of
    ``_TARGET_CALLEE_NAMES`` in its own right (for the ratchet's offender
    check, which does not consult this function at all). Checking the alias
    first is what keeps that bookkeeping stable across the leaf's promotion to
    a first-class censused callee.
    """
    for leaf_name, primitive in _LEAF_PRIMITIVE_ALIASES.items():
        if leaf_name in token_substring:
            return primitive
    for name in _TARGET_CALLEE_NAMES:
        if name in token_substring:
            return name
    raise AssertionError(
        f"token_substring {token_substring!r} names none of {sorted(_TARGET_CALLEE_NAMES)} "
        "-- every allow-list/foundation-sanction entry's token_substring must "
        "literally contain its censused primitive's name (G2 discriminator)"
    )


def _ledger_stay_lenient_index(text: str) -> frozenset[tuple[str, str, str, str]]:
    """The ledger's authoritative ``(rel_path, qualname, primitive, site_token)`` stay-lenient membership.

    G2: the trailing ``primitive`` column ALONE cannot disambiguate several
    censused sites of the SAME primitive sharing one qualname (SC-015's
    ``_find_meta_path`` four-site fixture carries three
    ``primary_feature_dir_for_mission`` sites in one qualname -- a
    ``(rel_path, qualname, primitive)`` triple still collapses those three
    onto one key). A second trailing ``site token`` column -- the site's own
    normalised token line -- makes each site distinct.
    """
    rows = _markdown_table_rows(text, _LEDGER_INDEX_HEADING, expected_columns=4)
    keys = [(row[0], row[1], row[2], row[3]) for row in rows]
    _assert_no_duplicate_keys(list(keys), heading=_LEDGER_INDEX_HEADING)
    return frozenset(keys)


def _ledger_foundation_index(text: str) -> frozenset[tuple[str, str, str, str]]:
    """The ledger's authoritative ``(rel_path, qualname, primitive, site_token)`` foundation-sanction membership."""
    rows = _markdown_table_rows(text, _LEDGER_FOUNDATION_HEADING, expected_columns=4)
    keys = [(row[0], row[1], row[2], row[3]) for row in rows]
    _assert_no_duplicate_keys(list(keys), heading=_LEDGER_FOUNDATION_HEADING)
    return frozenset(keys)


def _ledger_summary_counts(text: str) -> dict[tuple[str, str], tuple[int, int]]:
    """Parse the ledger's live-census Summary table into ``(verdict, primitive) -> (sites, files)``.

    G1 rule 6: a non-numeric count cell RAISES rather than being silently
    skipped. G1 rule 5: a duplicate ``(verdict, primitive)`` key RAISES rather
    than silently overwriting (last-wins).
    """
    counts: dict[tuple[str, str], tuple[int, int]] = {}
    keys: list[tuple[str, ...]] = []
    for row in _markdown_table_rows(text, _LEDGER_SUMMARY_HEADING, expected_columns=4):
        verdict, sites, files, primitive = row[0], row[1], row[2], row[3]
        if not sites.isdigit() or not files.isdigit():
            raise AssertionError(
                f"ledger live-census Summary row {row!r} has a non-numeric "
                "count cell -- G1 forbids silently skipping a malformed count row"
            )
        key = (verdict, primitive)
        keys.append(key)
        counts[key] = (int(sites), int(files))
    _assert_no_duplicate_keys(keys, heading=_LEDGER_SUMMARY_HEADING)
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
        rel_path="src/specify_cli/retrospective/tracer_writer.py",
        qualname="_local_staging_path",
        token_substring="candidate_feature_dir_for_mission ( repo_root , mission_slug )",
        occurrence=None,
        rationale=(
            "Ledger (write-side-seam-matrix-tracer-01KYP3MH, commit 2d96492ca): "
            "_local_staging_path computes where a LOCAL traces/<category>.md "
            "staging file should LAND before the mission's traces/ subdir exists "
            "(the caller append_tracer_finding mkdir+write_text's it), then "
            "commits through the WP03 write_seam.write_artifact whose FR-011 "
            "probe is the canonical routability authority. Mirrors the sibling "
            "retrospective/summary.py::_read_proposal_events (:220) staging "
            "pattern -- same package, same 'candidate dir + local subpath' shape. "
            "A read_dir(kind) route is wrong here: this resolves a write-then-"
            "stage destination, not where to READ from. Replaced a raw "
            "repo_root/KITTY_SPECS_DIR/mission_slug join (the deleted "
            "surface-resolution/untrusted-path ghost sink)."
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
    # ---- WP02 (FR-012, read-side-seam-primary-primitive-closure-01KYKMMT):
    # ---- resolve_feature_dir_for_mission's 7 stay-lenient sites (8 real call
    # ---- sites total; the 8th, decisions/emit.py:71, is migrate-fail-loud and
    # ---- deliberately NOT allow-listed -- it is an expected-red site until a
    # ---- later WP routes it).
    ContentDescriptor(
        rel_path="src/specify_cli/agent_tasks_ports.py",
        qualname="RealCoordCommitRouter.feature_write_dir",
        token_substring="resolve_feature_dir_for_mission (",
        occurrence=None,
        rationale=(
            "Ledger :323: tasks_move_task.py:348-353's production comment is "
            "the rationale of record -- 'feature_write_dir wraps "
            "resolve_feature_dir_for_mission (the kind-blind coord-husk leg) "
            "-- the SAME on-disk dir the pre-rewire body read; it feeds the "
            "pre30 guard, the authoritative event-log lane read, and the "
            "coord override persist. It is NEVER repointed to a primary kind "
            "-- that would move the event-log read off the coord husk and "
            "reintroduce the split-brain FR-010 closes.' Ambiguous whether a "
            "COORD-kind read_dir() swap would preserve resolve_action_context's "
            "richer resolution; defaulted lenient pending a bespoke fix."
        ),
    ),
    ContentDescriptor(
        rel_path="src/specify_cli/cli/commands/decision.py",
        qualname="_resolve_repo_root_and_slug",
        token_substring="resolve_feature_dir_for_mission ( repo_root , mission_handle )",
        occurrence=None,
        rationale=(
            "Ledger :130: own production comment (WP09/FR-001, prior mission) "
            "-- 'deliberately EXCLUDED from the read_dir(kind) migration': "
            "relies on resolve_action_context's structured ActionContextError "
            "(e.g. COORDINATION_BRANCH_DELETED) propagating for the #8 live "
            "symptom fix pinned by test_decision_single_authority.py. Neither "
            "read_dir(kind) partition leg replicates that fail-closed contract."
        ),
    ),
    ContentDescriptor(
        rel_path="src/specify_cli/cli/commands/mission_type.py",
        qualname="current_cmd",
        token_substring="resolve_feature_dir_for_mission ( project_root , mission_slug )",
        occurrence=None,
        rationale=(
            "Ledger :238: own production comment -- 'deliberately EXCLUDED "
            "from the read_dir(kind) migration, mirroring close_cmd below and "
            "decision.py::_resolve_repo_root_and_slug' -- shares the identical "
            "existence-probe shape needing resolve_action_context's "
            "structured-error contract."
        ),
    ),
    ContentDescriptor(
        rel_path="src/specify_cli/cli/commands/mission_type.py",
        qualname="close_cmd",
        token_substring="resolve_feature_dir_for_mission ( repo_root , mission_slug )",
        occurrence=None,
        rationale=(
            "Ledger :582: own production comment -- pinned tests "
            "(test_mission_close_unresolvable_handle_keeps_structured_error / "
            "..._ambiguous_handle_propagates_structured_error) require an "
            "unresolvable/ambiguous --mission handle to RAISE the structured "
            "ActionContextError here, never a silent 'Mission not found' or a "
            "wrong-mission pick; both read_dir(kind) partition legs are "
            "lenient by design and would swallow that contract."
        ),
    ),
    ContentDescriptor(
        rel_path="src/specify_cli/context/resolver.py",
        qualname="resolve_context",
        token_substring="resolve_feature_dir_for_mission ( repo_root , mission_slug )",
        occurrence=None,
        rationale=(
            "Ledger :191: own comment -- 'this call stays on the kind-blind "
            "primitive by design -- it exists to canonicalize the caller's "
            "HANDLE to a directory NAME, not to read a PRIMARY-partition "
            "artifact off the returned dir... re-routing this site too would "
            "over-claim a single funnel over the *_feature_dir_for_mission "
            "primitives beyond what the gate enforces.' Catches "
            "ActionContextError and translates it to FeatureNotFoundError "
            "(degrade axis), preserving the resolver's typed diagnostic code."
        ),
    ),
    ContentDescriptor(
        rel_path="src/specify_cli/lanes/recovery.py",
        qualname="reconcile_status",
        token_substring="resolve_feature_dir_for_mission ( repo_root , mission_slug )",
        occurrence=None,
        rationale=(
            "Ledger :781: own comment -- 'KEEP coord-aware (C-001 / #2155 "
            "analog): this feature_dir feeds emit_status_transition_"
            "transactional below -- a STATUS-WRITE leg. The status event log "
            "lives on the coordination worktree for coord-topology missions, "
            "so this MUST stay on the coord-aware resolver -- never route it.'"
        ),
    ),
    ContentDescriptor(
        rel_path="src/specify_cli/widen/state.py",
        qualname="WidenPendingStore.__init__",
        token_substring="resolve_feature_dir_for_mission ( repo_root , mission_slug )",
        occurrence=None,
        rationale=(
            "Ledger :63 (ambiguous -- reviewer confirm): no protective "
            "comment; widen-pending.jsonl's partition (PRIMARY vs COORD) is "
            "not established anywhere else in the module, and the store's own "
            "'a missing file is equivalent to an empty store -- never raises' "
            "invariant would be broken by a read_dir(kind) swap that CAN raise "
            "on a deleted coord branch for a COORD-partition kind. Defaulted "
            "lenient pending a bespoke kind decision (T012's vacuity guard: "
            "not a reason to skip classifying the site)."
        ),
    ),
    # ---- decisions/emit.py:71 (_mission_dir) is intentionally ABSENT here.
    # ---- The read-side-seam-primary-primitive-closure mission left it an
    # ---- expected-red `migrate-fail-loud` site; a later reviewer allow-listed
    # ---- it pending gate-owner work (#3055). The write-side-seam-matrix-tracer
    # ---- mission (WP02, FR-010 "Move A") then ROUTED it: `_mission_dir` now
    # ---- resolves through `placement_seam(...).read_dir(STATUS_STATE)`, so the
    # ---- `resolve_feature_dir_for_mission ( repo_root , mission_slug )` call no
    # ---- longer exists in emit.py. It is a COMPLETED migration, not an
    # ---- allow-listed offender -- keeping a descriptor here would resolve to 0
    # ---- findings and red the census on a vacuous key. The ledger's
    # ---- `resolve_feature_dir_for_mission` summary drops 8/7 -> 7/6 to match.
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
# WP02 (FR-012, E3/E4) -- foundation-site sanctions: per-site, never a module
# blanket. core/paths.py (x2) and core/git_ops.py (x1) call
# primary_feature_dir_for_mission from beneath the seam's own composition
# root (NFR-009: routing risks a resolution cycle). Neither module is a
# dedicated resolver-infra module (both carry substantial unrelated logic),
# so a whole-module _READ_SANCTIONED_MODULES entry would be exactly the
# path-scoped blanket C-003 forbids -- these are per-SITE content descriptors
# instead, reusing the SAME resolver as the stay-lenient allow-list (never a
# third key-builder), reconciled against a SEPARATE ledger table so
# sanction-infra counts never blend into the stay-lenient business-logic
# counts.
# ---------------------------------------------------------------------------

_FOUNDATION_SANCTION_SEED: tuple[ContentDescriptor, ...] = (
    ContentDescriptor(
        rel_path="src/specify_cli/core/paths.py",
        qualname="get_feature_target_branch",
        token_substring="_compose_primary_feature_dir (",
        occurrence=None,
        rationale=(
            "FR-005 foundation site 1/4: resolves the PRIMARY anchor to read "
            "the target-branch field feeding the write-side composition root "
            "-- routing through the seam here would recurse into the "
            "resolver the seam itself depends on (NFR-009). Recorded by name, "
            "deliberately unrouted. WP08 (T035): re-pointed at the "
            "module-private leaf _compose_primary_feature_dir (was "
            "primary_feature_dir_for_mission) in the same commit as the "
            "public wrapper's deletion -- the M1 build-break fix WP07 "
            "deferred (this token was pinned to the wrapper's literal name; "
            "re-pointing the call without moving this token would "
            "DescriptorResolutionError at collection)."
        ),
    ),
    ContentDescriptor(
        rel_path="src/specify_cli/core/paths.py",
        qualname="resolve_merge_target_branch",
        token_substring="_compose_primary_feature_dir (",
        occurrence=None,
        rationale=(
            "FR-005 foundation site 2/4: same core/paths.py recursion "
            "rationale as get_feature_target_branch above -- a second, "
            "distinct site in the same file (two entries, not a module "
            "blanket, per C-003). WP08 (T035): token re-pointed to the leaf "
            "in the same commit as the wrapper deletion, same M1 rationale."
        ),
    ),
    ContentDescriptor(
        rel_path="src/specify_cli/core/git_ops.py",
        qualname="resolve_target_branch",
        token_substring="_compose_primary_feature_dir (",
        occurrence=None,
        rationale=(
            "FR-005 foundation site 3/4: mirrors core/paths.py's target-branch "
            "resolution one layer up the git-ops composition root; the same "
            "recursion rationale applies (NFR-009). WP08 (T035): token "
            "re-pointed to the leaf in the same commit as the wrapper "
            "deletion, same M1 rationale."
        ),
    ),
    # ---- Post-merge aggregate-squad closeout (fix/read-side-seam-primary-
    # ---- primitive-closure follow-up): the remaining two named FR-005/
    # ---- NFR-009 foundation sites, deferred at WP06/WP08 time (ledger's "WP06
    # ---- correction" note: "WP08's end-state reconciliation (T039) is the
    # ---- owner of folding this site into that machine-checked set" -- WP08
    # ---- closed resolve_feature_dir_for_mission's reconciliation but left
    # ---- these two rows unclaimed). Both already called the leaf directly
    # ---- (WP03/WP08 re-pointed them in prior commits) and both already carry
    # ---- an equivalent entry in resolution_gate_allowlist.yaml's
    # ---- canonicalizer allow-list -- this closeout adds the two machine-
    # ---- checked entries the prior WPs deferred, and (separately)
    # ---- _compose_primary_feature_dir itself to _TARGET_CALLEE_NAMES so the
    # ---- ratchet can flag any FUTURE un-sanctioned call to the leaf.
    ContentDescriptor(
        rel_path="src/specify_cli/retrospective/writer.py",
        qualname="resolve_retrospective_home",
        token_substring="_compose_primary_feature_dir (",
        occurrence=None,
        rationale=(
            "FR-005 foundation site 4/5: the durable retrospective-home "
            "resolver sits BENEATH PlacementSeam.read_dir's RETROSPECTIVE "
            "short-circuit (resolution.py:1454) -- calling back through the "
            "(now-deleted) public wrapper would close a "
            "read_dir -> resolve_retrospective_home -> wrapper -> read_dir "
            "cycle (NFR-009), so this site calls the leaf directly and "
            "permanently, exactly like core/paths.py and core/git_ops.py "
            "above. WP06 verified (not routed) this exact site -- confirmed "
            "the call target, the standing regression guard "
            "(test_home_resolution_single_authority.py::"
            "test_writer_authority_gates_on_primary_partition_kind, which "
            "reds when mutated back to the wrapper) -- and explicitly "
            "deferred its machine-checked sanction to a later WP (ledger's "
            "'WP06 correction' note). This closeout is that later step: the "
            "leaf itself was never censused at all (not merely missing from "
            "this one table), so this site sat outside every gate's view "
            "until now."
        ),
    ),
    ContentDescriptor(
        rel_path="src/specify_cli/status/aggregate.py",
        qualname="MissionStatus._find_meta_path",
        token_substring="_compose_primary_feature_dir (",
        occurrence=None,
        rationale=(
            "FR-005 foundation site 5/5: bare_dir_name is the on-disk composed "
            "dir NAME already returned by resolve_bare_modern_mission_dir_name "
            "-- already-canonical by provenance, the PERMANENT canonicalizer "
            "fixture (resolution_gate_allowlist.yaml, qualname "
            "MissionStatus._find_meta_path, WP08-authored) predating this "
            "closeout. This same qualname also carries an existing "
            "candidate_feature_dir_for_mission stay-lenient allow-list entry "
            "above (SC-015's four-site acceptance fixture) -- the token here "
            "names the LEAF, not the kind-blind primitive, so it resolves to "
            "the DIFFERENT, distinct call site at this qualname's line 537, "
            "never colliding with that entry (resolve_descriptor requires "
            "exactly-one per (qualname, token_substring), enforced at import "
            "time by the staleness twin-guard below). WP08 (T039) re-pointed "
            "this call at the leaf when it deleted the public wrapper but did "
            "not add the corresponding machine-checked sanction row; this "
            "closeout adds it."
        ),
    ),
)

#: Composite key resolved LIVE for each ``_FOUNDATION_SANCTION_SEED`` entry.
_FOUNDATION_SANCTION_KEYS: tuple[CompositeKey, ...] = tuple(
    resolve_descriptor((_REPO_ROOT / descriptor.rel_path).read_text(encoding="utf-8"), descriptor)
    for descriptor in _FOUNDATION_SANCTION_SEED
)

#: Composite-keyed foundation-sanction set: ``frozenset[(rel_path, qualname, token_line)]``.
#: The 4th named FR-005 foundation site, coordination/surface_resolver.py, is
#: NOT here -- it is already covered by its existing whole-module
#: _READ_SANCTIONED_MODULES entry (which now names both primitives it serves).
#:
#: Foundation-count reconciliation: the in-code "RECORDED FOUNDATION SITE N/4"
#: comments at core/paths.py (x2), core/git_ops.py, and
#: coordination/surface_resolver.py count FOUR sites -- the ones sanctioned by
#: an inline module/function-level comment (surface_resolver.py's is a
#: whole-module sanction, not an individual seed row). This table's "N/5"
#: numbering counts a DIFFERENT five: the same paths.py x2 + git_ops.py trio,
#: swapping out surface_resolver.py (already whole-module sanctioned, so not
#: individually machine-checked here) for the two sites that WERE deferred
#: until this table added them -- retrospective/writer.py and
#: status/aggregate.py. Six underlying leaf-call sites exist in total; "N/4"
#: and "N/5" are two different countable subsets of that same six, not a
#: drifted recount.
_FOUNDATION_SANCTIONED: frozenset[CompositeKey] = frozenset(_FOUNDATION_SANCTION_KEYS)


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
            key = finding.as_allow_key()
            if key in _ALLOW_LIST or key in _FOUNDATION_SANCTIONED:
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

    The ledger (``docs/development/reference/read-side-seam-classification.md``,
    § "Stay-lenient allow-list index (machine-checked)") is the ONE authority
    for WHICH sites stay lenient. This test parses that table and asserts
    ``(rel_path, qualname, primitive, site_token)`` set equality with
    ``_ALLOW_LIST_SEED`` (G2's trailing ``primitive`` + ``site token``
    discriminators, WP02 T009 cycle-1 fix), so:

    - deleting/editing/adding a ledger row without touching the seed REDS here;
    - adding a seed entry the ledger does not sanction REDS here.

    That is the mechanical link the previous count-only pin lacked (both sides
    of it lived five lines apart in THIS file, so the ledger could drift freely).
    """
    ledger_index = _ledger_stay_lenient_index(_ledger_text())
    seed_index = frozenset(
        (d.rel_path, d.qualname, _entry_primitive(d.token_substring), d.token_substring)
        for d in _ALLOW_LIST_SEED
    )

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
        "duplicate (rel_path, qualname, primitive, site_token) in "
        "_ALLOW_LIST_SEED -- the ledger index is one row per SITE and cannot "
        "address two DISTINCT sites sharing one qualname+primitive+site_token"
    )


def test_foundation_sanction_membership_is_exactly_the_ledgers_foundation_index() -> None:
    """The foundation-sanction set IS the ledger's foundation index -- parsed, not hand-synced.

    Mirrors ``test_allow_list_membership_is_exactly_the_ledgers_stay_lenient_index``
    for the separate FR-005 foundation-site table (WP02 T011/E3): editing
    ``docs/development/reference/read-side-seam-classification.md``'s
    § "Foundation-site sanctions (machine-checked)" table without touching
    ``_FOUNDATION_SANCTION_SEED`` (or vice versa) REDS here.
    """
    ledger_index = _ledger_foundation_index(_ledger_text())
    seed_index = frozenset(
        (d.rel_path, d.qualname, _entry_primitive(d.token_substring), d.token_substring)
        for d in _FOUNDATION_SANCTION_SEED
    )

    assert seed_index == ledger_index, (
        "the read gate's foundation-sanction set no longer matches the WP02 "
        "ledger's foundation index (the authority).\n"
        f"  in the ledger only: {sorted(ledger_index - seed_index)}\n"
        f"  in the gate only:   {sorted(seed_index - ledger_index)}\n"
        "Fix the LEDGER first (it is the authority), then mirror the change here."
    )
    assert len(_FOUNDATION_SANCTION_SEED) == len(seed_index), (
        "duplicate (rel_path, qualname, primitive, site_token) in "
        "_FOUNDATION_SANCTION_SEED"
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


def test_ledger_parser_fails_loud_when_the_foundation_section_is_removed() -> None:
    """Deleting the foundation-sanction heading REDS too (same fail-loud discipline)."""
    text_without_section = _ledger_text().replace(_LEDGER_FOUNDATION_HEADING, "## Something Else")

    with pytest.raises(AssertionError, match="Foundation-site sanctions"):
        _ledger_foundation_index(text_without_section)


def _allow_seed_by_primitive() -> dict[str, list[ContentDescriptor]]:
    grouped: dict[str, list[ContentDescriptor]] = {name: [] for name in _TARGET_CALLEE_NAMES}
    for descriptor in _ALLOW_LIST_SEED:
        grouped[_entry_primitive(descriptor.token_substring)].append(descriptor)
    return grouped


def _foundation_seed_by_primitive() -> dict[str, list[ContentDescriptor]]:
    grouped: dict[str, list[ContentDescriptor]] = {name: [] for name in _TARGET_CALLEE_NAMES}
    for descriptor in _FOUNDATION_SANCTION_SEED:
        grouped[_entry_primitive(descriptor.token_substring)].append(descriptor)
    return grouped


def _live_primitive_site_counts() -> dict[str, tuple[int, int]]:
    """Fresh ``(site_count, file_count)`` per censused primitive, live scan scope.

    T014 / SC-008: every count claimed in the ledger's live-census Summary
    table must match a FRESH re-derivation, never a copied figure -- this
    walks the actual tree at test-run time (never a frozen snapshot).
    """
    sites: dict[str, int] = dict.fromkeys(_TARGET_CALLEE_NAMES, 0)
    files: dict[str, set[str]] = {name: set() for name in _TARGET_CALLEE_NAMES}
    for module in _read_side_scan_scope():
        for finding in _scan_read_bypass_module(module):
            sites[finding.callee] += 1
            files[finding.callee].add(_placement_rel_path(module))
    return {name: (sites[name], len(files[name])) for name in _TARGET_CALLEE_NAMES}


def _reconciliation_errors(text: str) -> list[str]:
    """Every G3 reconciliation mismatch in ``text``'s live-census Summary table.

    Pulled out of the test body (T010's mutation validation reuses this
    exact logic against a mutated ledger copy): empty list == fully
    reconciled. Never silently passes on missing rows -- ``_ledger_summary_counts``
    already raises loud for a malformed table; this function assumes it
    already succeeded and only checks the FOUR G3 reconciliations per
    primitive.
    """
    counts = _ledger_summary_counts(text)
    live = _live_primitive_site_counts()
    allow_by_primitive = _allow_seed_by_primitive()
    foundation_by_primitive = _foundation_seed_by_primitive()

    errors: list[str] = []
    for primitive in sorted(_TARGET_CALLEE_NAMES):
        for verdict in (*_LEDGER_VERDICT_NAMES, _LEDGER_TOTAL_ROW_NAME):
            if (verdict, primitive) not in counts:
                errors.append(f"no parseable ({verdict!r}, {primitive!r}) row")
        if any(e.startswith("no parseable") and primitive in e for e in errors):
            continue

        lenient_sites, lenient_files = counts[("stay-lenient", primitive)]
        seed = allow_by_primitive[primitive]
        if lenient_sites != len(seed):
            errors.append(
                f"{primitive}: stay-lenient sites={lenient_sites} but allow-list carries {len(seed)}"
            )
        if lenient_files != len({d.rel_path for d in seed}):
            errors.append(
                f"{primitive}: stay-lenient files={lenient_files} but allow-list spans "
                f"{len({d.rel_path for d in seed})}"
            )

        sanction_sites, sanction_files = counts[("sanction-infra", primitive)]
        found = foundation_by_primitive[primitive]
        if sanction_sites != len(found):
            errors.append(
                f"{primitive}: sanction-infra sites={sanction_sites} but foundation set carries "
                f"{len(found)}"
            )
        if sanction_files != len({d.rel_path for d in found}):
            errors.append(
                f"{primitive}: sanction-infra files={sanction_files} but foundation set spans "
                f"{len({d.rel_path for d in found})}"
            )

        verdict_sites = sum(counts[(v, primitive)][0] for v in _LEDGER_VERDICT_NAMES)
        total_sites, total_files = counts[(_LEDGER_TOTAL_ROW_NAME, primitive)]
        if verdict_sites != total_sites:
            errors.append(
                f"{primitive}: verdict rows sum to {verdict_sites} sites but total row "
                f"declares {total_sites}"
            )

        live_sites, live_files = live[primitive]
        if total_sites != live_sites:
            errors.append(
                f"{primitive}: ledger declares {total_sites} total real call sites but a "
                f"fresh census finds {live_sites}"
            )
        if total_files != live_files:
            errors.append(
                f"{primitive}: ledger declares {total_files} total files but a fresh "
                f"census finds {live_files}"
            )
        # A files-side sum-of-verdicts companion to verdict_sites (above) was
        # considered and deliberately dropped: files are NOT strictly additive
        # across verdicts when one file mixes verdicts (e.g. a mixed
        # migrate+stay-lenient file), so summing per-verdict file counts and
        # comparing to total_files would be a false-precision check, not a
        # real invariant. This comment is the record of that decision.

    return errors


def test_ledger_summary_counts_reconcile_with_the_allow_list_and_themselves() -> None:
    """The ledger's live-census Summary counts bind the allow-list/foundation-set shape.

    Per-primitive reconciliation (G3, T010), for EACH of the five censused
    primitives independently:

    1. ``stay-lenient`` sites/files == that primitive's allow-list entries.
    2. ``sanction-infra`` sites/files == that primitive's foundation-sanction entries.
    3. The four verdict-bucket rows sum to the ``Total real call sites`` row
       (internal consistency -- a Summary edit cannot be "balanced" by
       silently mis-stating the total).
    4. The total matches a FRESH live census (T014 / SC-008) -- never a
       copied figure.

    T010.3 / NFR-008 update (review cycle 1): the Summary table above
    declares the POST-MIGRATION END STATE. WP08 (T039) closed out
    ``resolve_feature_dir_for_mission``'s reconciliation red (its one
    ``migrate-fail-loud`` site, ``decisions/emit.py:71``, was allow-listed --
    reconciliation item #5 -- moving the declared numbers to match a fresh
    live census exactly), so it now carries NO exemption and must stay fully
    reconciled like the two already-migrated primitives.
    ``primary_feature_dir_for_mission`` carries a PERMANENT exemption instead
    of a transitional one: WP08 (T035) deleted the public wrapper outright
    (SC-001), so a fresh live census permanently finds 0 real call sites for
    it, never converging on the declared `5` (a frozen bookkeeping pointer to
    the five FR-005/NFR-009 foundation sites, not a live-call tally -- see
    the ledger's "WP08 (T039) closeout" paragraph for the full record).

    Post-merge aggregate-squad closeout adds a SECOND, mirror-image permanent
    exemption: ``_compose_primary_feature_dir`` (the leaf, newly promoted to a
    first-class member of ``_TARGET_CALLEE_NAMES``) declares `0` in every
    bucket -- nothing is bookkept under the leaf's own literal name, since
    ``_entry_primitive``'s alias check keeps routing those five entries to the
    ``primary_feature_dir_for_mission`` bucket above -- yet a fresh live
    census permanently finds the same 5 real call sites for it. Both
    exemptions describe the identical five-site population, counted once,
    under the old primitive's name; see the ledger's "Post-merge closeout"
    and mirror-image paragraphs for the full record. Any OTHER mismatch on
    any of the five primitives is unexpected and reds this test.
    """
    errors = _reconciliation_errors(_ledger_text())
    expected_end_state_reds = (
        "primary_feature_dir_for_mission: ledger declares",
        "_compose_primary_feature_dir: ledger declares",
    )
    unexpected = [e for e in errors if not e.startswith(expected_end_state_reds)]
    assert not unexpected, (
        "ledger live-census Summary reconciliation failed with an UNEXPECTED "
        "mismatch (beyond the two permanent end-state total-count reds noted "
        "above):\n" + "\n".join(unexpected)
    )
    for expected_prefix in expected_end_state_reds:
        assert any(e.startswith(expected_prefix) for e in errors), (
            f"expected the permanent end-state reconciliation red for "
            f"{expected_prefix!r} to be present -- if the live census has "
            "caught up to the declared end state, whoever edits these count "
            "rows should have already updated this exemption"
        )


@pytest.mark.parametrize("primitive", sorted(_TARGET_CALLEE_NAMES))
def test_per_primitive_summary_mutation_reds(primitive: str) -> None:
    """T010 validation: mutating ONE primitive's live-census row REDS -- independently.

    The exact vacuity this closes: a single-primitive mutation test would
    pass happily while a SECOND primitive's row is entirely unenforced. This
    test is parameterised over all five censused primitives so each one is
    proven to bite on its own -- not riding on another primitive's coverage.

    Non-blocking review-cycle-1 hardening, two independent fixes:

    1. **Row located structurally, not by count value.** The row is now found
       by a regex anchored on the row's OWN trailing ``primitive`` cell
       (``| stay-lenient | <sites> | <files> | \\`{primitive}\\` |``), not by
       matching the count VALUE -- the previous needle
       (``f"| stay-lenient | {n} | "``) would silently mutate the FIRST
       same-count row for a DIFFERENT primitive if two primitives ever shared
       an equal stay-lenient count, making the per-primitive claim false
       while staying green.
    2. **New-error diff, not bare truthiness.** T010.3 (this cycle's Blocker 2
       fix) makes the ledger's baseline reconciliation carry permanent reds.
       Post-merge closeout update: those are now
       ``primary_feature_dir_for_mission`` / ``_compose_primary_feature_dir``
       (the mirror-image pair described in
       ``test_ledger_summary_counts_reconcile_with_the_allow_list_and_themselves``'s
       docstring), not ``resolve_feature_dir_for_mission`` (closed at WP08). A
       bare ``assert errors`` would now pass vacuously for those two
       primitives even if the mutation introduced NO new error at all, since
       the baseline itself is already non-empty. This asserts the mutation
       adds a NEW error that specifically names the mutated primitive.
    """
    text = _ledger_text()
    baseline_errors = set(_reconciliation_errors(text))

    row_pattern = re.compile(
        r"^\| stay-lenient \| (\d+) \| (\d+) \| `" + re.escape(primitive) + r"` \|$",
        re.MULTILINE,
    )
    match = row_pattern.search(text)
    assert match is not None, f"could not locate the stay-lenient row for {primitive!r} to mutate"
    mutated = f"{text[: match.start(1)]}{int(match.group(1)) + 5}{text[match.end(1) :]}"
    assert mutated != text

    new_errors = set(_reconciliation_errors(mutated)) - baseline_errors
    assert new_errors, (
        f"mutating the stay-lenient count for {primitive!r} did not introduce a "
        "NEW reconciliation error beyond the permanent end-state baseline "
        "(primary_feature_dir_for_mission / _compose_primary_feature_dir "
        "legitimately carry persistent reconciliation reds by permanent "
        "design) -- the per-primitive mutation gate is vacuous for this "
        "primitive"
    )
    assert any(primitive in e for e in new_errors), (
        f"the new reconciliation error(s) do not name {primitive!r}: {sorted(new_errors)}"
    )


def test_ledger_second_table_under_a_parsed_heading_reds() -> None:
    """T008 validation: a second pipe-table under one heading REDS (never silently dropped).

    Reproduces the exact executed defect this WP repairs: the originally
    prescribed per-primitive sub-tables shape, run through the real parser,
    silently read only the FIRST table. Appending a second table here must
    now RAISE instead.
    """
    text = _ledger_text()
    injected = text.replace(
        _LEDGER_INDEX_HEADING,
        _LEDGER_INDEX_HEADING
        + "\n\n| rel_path | qualname | primitive | site token |\n|---|---|---|---|\n"
        "| `src/bogus.py` | `bogus` | `candidate_feature_dir_for_mission` | `bogus (` |",
        1,
    )
    with pytest.raises(AssertionError, match="SECOND pipe-table"):
        _ledger_stay_lenient_index(injected)


def test_ledger_mid_table_column_insertion_reds() -> None:
    """T008 validation: inserting a column mid-table REDS (never silently mis-read).

    A leading/middle insertion into an existing row shifts every subsequent
    cell one column over for a positional reader -- ``expected_columns``
    catches the row-shape mismatch instead of silently mis-assigning cells.
    """
    text = _ledger_text()
    lines = text.splitlines()
    index_heading_at = lines.index(_LEDGER_INDEX_HEADING)
    # The first real data row anywhere between the heading and the next ``##``
    # heading (prose paragraphs may precede the table itself).
    mutated_at: int | None = None
    for offset in range(1, len(lines) - index_heading_at):
        candidate = lines[index_heading_at + offset]
        stripped = candidate.strip()
        if stripped.startswith("## "):
            break
        if stripped.startswith("|") and "rel_path" not in candidate and "---" not in candidate:
            lines[index_heading_at + offset] = candidate.replace("|", "| `EXTRA` |", 1)
            mutated_at = offset
            break
    if mutated_at is None:  # pragma: no cover - defensive; the table always has >=1 data row
        pytest.fail("could not locate a stay-lenient index data row to mutate")

    mutated = "\n".join(lines)
    with pytest.raises(AssertionError, match="expected exactly 4"):
        _ledger_stay_lenient_index(mutated)


def test_ledger_duplicate_index_key_reds() -> None:
    """G1 rule 5: a duplicated ``(rel_path, qualname, primitive)`` key REDS.

    A silently-overwriting duplicate (last-wins) would let a routed-away
    entry mask a genuinely new offender sharing the same key -- this proves
    the parser raises instead of collapsing the two rows.
    """
    text = _ledger_text()
    lines = text.splitlines()
    heading_at = lines.index(_LEDGER_INDEX_HEADING)
    data_row_line: str | None = None
    for line in lines[heading_at + 1 :]:
        stripped = line.strip()
        if stripped.startswith("## "):
            break
        if stripped.startswith("|") and "rel_path" not in stripped and set(stripped.strip("|")) - {
            "-",
            ":",
            "|",
        }:
            data_row_line = line
            break
    assert data_row_line is not None, "the stay-lenient index has no data row to duplicate"

    # Double the exact same raw line immediately after itself -- guaranteed to
    # produce an identical (rel_path, qualname, primitive) key collision
    # regardless of the table's current column formatting.
    mutated = text.replace(data_row_line, data_row_line + "\n" + data_row_line, 1)
    assert mutated != text

    with pytest.raises(AssertionError, match="DUPLICATE key"):
        _ledger_stay_lenient_index(mutated)


def test_ledger_non_numeric_summary_count_reds() -> None:
    """G1 rule 6: a non-numeric count cell in the live Summary table REDS, never silently skips."""
    text = _ledger_text()
    lines = text.splitlines()
    heading_at = lines.index(_LEDGER_SUMMARY_HEADING)
    mutated_at: int | None = None
    for offset in range(1, len(lines) - heading_at):
        line = lines[heading_at + offset]
        stripped = line.strip()
        if stripped.startswith("## "):
            break
        if stripped.startswith("| stay-lenient |"):
            cells = line.split("|")
            cells[2] = " N/A "  # the sites count cell
            lines[heading_at + offset] = "|".join(cells)
            mutated_at = offset
            break
    assert mutated_at is not None, "could not locate a stay-lenient live-summary row to mutate"
    mutated = "\n".join(lines)

    with pytest.raises(AssertionError, match="non-numeric"):
        _ledger_summary_counts(mutated)


def test_historical_pre_migration_figures_are_preserved_and_labelled() -> None:
    """NFR-008: the historical pre-migration totals are PRESERVED, never rewritten.

    The live-census Summary (parsed above) covers only the residual/lenient
    totals as they stand today. The original 2-primitive pre-migration census
    (90 real call sites across 60 consumer files) must still be present,
    explicitly labelled as a historical audit record -- not silently deleted
    or folded into the live figures.
    """
    text = _ledger_text()
    assert "historical" in text.lower(), (
        "the ledger no longer labels its pre-migration census as a historical "
        "audit record (NFR-008)"
    )
    assert "90" in text and "60" in text, (
        "the historical pre-migration census figures (90 real call sites / 60 "
        "consumer files) are no longer present in the ledger -- NFR-008 "
        "forbids rewriting a historical figure to satisfy a check"
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


def test_ratchet_bites_on_a_planted_leaf_primitive_call_outside_sanctioned_modules() -> None:
    """Post-merge aggregate-squad closeout: a rogue call to the LEAF primitive
    itself, planted in a module the read-side scan actually walks, is flagged
    AND would be a genuine offender -- never masked by an existing allow-list
    or foundation-sanction entry.

    This is the bite test the census gap made impossible before this
    closeout: ``_compose_primary_feature_dir`` was absent from
    ``_TARGET_CALLEE_NAMES`` entirely, so ``_scan_read_bypass`` produced ZERO
    findings for it no matter where it was called from -- a module OUTSIDE the
    five named foundation sites could import the leaf directly and call it
    with a canonical handle, reopening the exact canonical-handle +
    caller-chosen-partition bypass shape this mission exists to end,
    invisibly to every one of the four gates (the finding this test proves
    against never existed to be masked; it simply never fired).

    Proved by construction, mirroring the other four bite tests above: a
    fixture source with a planted call is fed straight to the real detector
    (never a mocked or hypothetical scanner), and the resulting finding's
    composite key is asserted to fall OUTSIDE both the allow-list and the
    foundation-sanction set -- so this is not merely "the detector matched a
    name", it is "the main ratchet's own offender-membership check would flag
    this exact finding as red", the identical check
    ``test_no_read_side_bypass_outside_sanctioned_and_allow_listed`` performs
    against every real scanned module.
    """
    fixture_source = (
        "def _rogue_leaf_bypass_site(root, slug):\n"
        "    return _compose_primary_feature_dir(root, slug)\n"
    )
    rogue_path = _REPO_ROOT / "src" / "specify_cli" / "manifest.py"  # scanned, unsanctioned
    findings = _scan_read_bypass(fixture_source, rogue_path)
    callees = {f.callee for f in findings}
    assert "_compose_primary_feature_dir" in callees, (
        "ratchet failed to flag a planted call to the leaf primitive itself "
        f"(the exact census gap this closeout fixes); found {callees}"
    )

    finding = next(f for f in findings if f.callee == "_compose_primary_feature_dir")
    key = finding.as_allow_key()
    assert key not in _ALLOW_LIST and key not in _FOUNDATION_SANCTIONED, (
        f"the planted rogue finding's key {key!r} unexpectedly matches an "
        "existing allow-list/foundation-sanction entry -- this bite test must "
        "plant a genuinely NEW offender, never one already excused, or the "
        "proof would be vacuous"
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
    """None of the four sanctioned infra modules ever enters ``_read_side_scan_scope()``.

    Asserted directly (FR-003 "asserted, not silently skipped") rather than
    relying on incidental overlap with the write-side
    ``BOUNDARY_SANCTIONED_PREFIXES`` blanket (which only happens to cover
    ``write_target_degrade.py`` and ``resolution.py``, not the other two).
    """
    scanned_rel = {_placement_rel_path(p) for p in _read_side_scan_scope()}
    for sanctioned in _READ_SANCTIONED_MODULES:
        assert sanctioned not in scanned_rel, (
            f"{sanctioned} is a read-sanctioned infra module and must never "
            "enter the read-side bypass scan scope"
        )


def test_read_sanctioned_modules_have_real_findings_that_would_otherwise_red() -> None:
    """The sanction is not vacuous: each of the four modules DOES contain a
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


#: Sanctioned modules whose per-file rationale now ALSO claims coverage of a
#: newly-censused primitive (WP02 T011/E3), not merely of a pre-existing one.
#:
#: read-side-seam-primary-primitive-closure-01KYKMMT WP08 (T035, reconciliation
#: item #2 from ``research/expected-reds.md``): ``src/mission_runtime/
#: resolution.py`` DROPPED here -- WP03's T016 re-pointed its four internal
#: composition sites at the extracted leaf (``_compose_primary_feature_dir``)
#: directly, so it now has ZERO real ``primary_feature_dir_for_mission`` call
#: sites; claiming non-vacuous coverage of that primitive there would be
#: exactly the vacuous "proved by a different primitive's finding" shape this
#: meta-test exists to catch. It stays sanctioned overall (still non-vacuous
#: for ``candidate_feature_dir_for_mission`` / ``resolve_planning_read_dir``,
#: per ``test_read_sanctioned_modules_have_real_findings_that_would_otherwise_red``)
#: -- only its claim for THIS primitive is retired.
#:
#: ``src/specify_cli/coordination/surface_resolver.py`` DROPPED for the exact
#: same reason, one WP later: WP08's own T035 re-pointed this module's
#: foundation site 4/4 at the same leaf (in the same commit as the public
#: wrapper's deletion), so it too now has zero real
#: ``primary_feature_dir_for_mission`` call sites. It remains sanctioned
#: overall (non-vacuous for ``candidate_feature_dir_for_mission``).
#:
#: Post-merge aggregate-squad closeout: repopulated for the NEWLY-censused
#: ``_compose_primary_feature_dir`` leaf itself (THE bar this closeout must
#: clear -- "the meta-tests must still prove each sanctioned module carries a
#: real finding *for the leaf primitive* too"). Every whole-module
#: ``_READ_SANCTIONED_MODULES`` entry that has a real, live call to the leaf is
#: named here so its exclusion cannot be vacuously "proved" by riding on one of
#: the OTHER three primitives' unrelated findings:
#:
#: - ``_read_path_resolver.py`` defines the leaf and calls it internally
#:   (``:464``, ``:845``, ``:982``, ``:1004``, ``:1055``, ``:1259``, ``:1458``)
#:   to compose ``resolve_planning_read_dir``'s PRIMARY leg and the module's
#:   other resolver-internal helpers.
#: - ``coordination/surface_resolver.py`` calls it at its own foundation site
#:   (``:748``, ``resolve_status_surface_with_anchor``'s PRIMARY anchor).
#: - ``mission_runtime/resolution.py`` (the seam itself) calls it at four
#:   internal sites (``:430``, ``:762``, ``:811``, ``:1008``) to compose its
#:   own PRIMARY-partition leg.
#:
#: ``write_target_degrade.py`` is NOT listed: it has zero real calls to the
#: leaf (confirmed by a direct scan of the file), so claiming coverage for it
#: here would itself be the exact vacuity this meta-test exists to catch.
_NEWLY_CENSUSED_SANCTION_CLAIMS: dict[str, str] = {
    "src/specify_cli/missions/_read_path_resolver.py": "_compose_primary_feature_dir",
    "src/specify_cli/coordination/surface_resolver.py": "_compose_primary_feature_dir",
    "src/mission_runtime/resolution.py": "_compose_primary_feature_dir",
}


def test_sanctioned_modules_are_non_vacuous_for_the_newly_censused_primitive() -> None:
    """WP02 T011/E3 per-primitive non-vacuity.

    Growing the censused callee set 2 -> 4 must not let an EXISTING
    sanctioned-module exclusion "vacuously prove" coverage of a NEW primitive
    by riding on a real finding for the OLD one only. Each module in
    ``_NEWLY_CENSUSED_SANCTION_CLAIMS`` must carry a real call site for the
    NEW primitive specifically.
    """
    for rel, primitive in _NEWLY_CENSUSED_SANCTION_CLAIMS.items():
        module = _REPO_ROOT / rel
        findings = _scan_read_bypass_module(module)
        callees = {f.callee for f in findings}
        assert primitive in callees, (
            f"{rel} is sanctioned but has ZERO real {primitive!r} call sites "
            "-- its exclusion would be vacuously 'proved' by a "
            "previously-censused primitive's finding only (WP02 T011/E3 "
            "per-primitive non-vacuity)"
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


@pytest.mark.parametrize(
    "descriptor",
    _FOUNDATION_SANCTION_SEED,
    ids=[f"{d.rel_path}::{d.qualname}" for d in _FOUNDATION_SANCTION_SEED],
)
def test_foundation_sanction_entry_is_still_a_live_finding(descriptor: ContentDescriptor) -> None:
    """Staleness twin-guard for the foundation-sanction set (WP02 T011/E4).

    Mirrors :func:`test_allow_list_entry_is_still_a_live_finding` for the
    separate FR-005 foundation-site table: if ``core/paths.py`` or
    ``core/git_ops.py`` is ever refactored to no longer call
    ``primary_feature_dir_for_mission`` at one of these three sites, this
    fails loudly rather than leaving a vacuous sanction in place.
    """
    seed_index = _FOUNDATION_SANCTION_SEED.index(descriptor)
    seeded_key = _FOUNDATION_SANCTION_KEYS[seed_index]
    source = (_REPO_ROOT / descriptor.rel_path).read_text(encoding="utf-8")
    assert descriptor_still_live(source, descriptor, seeded_key), (
        f"{descriptor.rel_path} ({descriptor.qualname}) no longer resolves to "
        "its seeded live foundation-sanction finding -- DELETE this now-stale "
        "entry (shrink-only, never leave a vacuous rule)."
    )


# ---------------------------------------------------------------------------
# T009 (G2, SC-015) — the index discriminator represents a four-site qualname.
# ---------------------------------------------------------------------------


#: read-side-seam-primary-primitive-closure-01KYKMMT WP08 (T035/T039,
#: reconciliation item #3 from ``research/expected-reds.md``): a FROZEN
#: synthetic fixture, not a live scan of ``status/aggregate.py``. The test
#: used to scan that file directly, but its four-site shape (1
#: ``candidate_feature_dir_for_mission`` + 3 ``primary_feature_dir_for_mission``
#: calls, all inside ``MissionStatus._find_meta_path``) depended on the very
#: migration this ledger exists to drive to completion: WP07 routed two of
#: the three ``primary_feature_dir_for_mission`` sites through the seam, and
#: WP08 deleted the primitive outright and re-pointed the third (the
#: permanent canonicalizer fixture) at the module-private leaf -- so the live
#: file now carries ZERO ``primary_feature_dir_for_mission`` calls, and this
#: test's live-scan assumption cannot survive its own migration (WP07's own
#: handoff report flagged this gap and recommended exactly this fix: a frozen
#: synthetic source string, the same technique the module's other synthetic
#: fixtures already use elsewhere in this file). The synthetic source below
#: reproduces the acceptance shape the test needs -- one qualname, one
#: existing-primitive call, three same-primitive calls with distinct
#: arguments (so each normalises to a distinct token line) -- independent of
#: any real file's migration state.
_SYNTHETIC_FOUR_SITE_SOURCE = '''\
class MissionStatus:
    def _find_meta_path(self, repo_root, mission_slug, bare_dir_name, canonical_slug):
        candidate = candidate_feature_dir_for_mission(repo_root, mission_slug)
        first = primary_feature_dir_for_mission(repo_root, mission_slug)
        second = primary_feature_dir_for_mission(repo_root, bare_dir_name)
        third = primary_feature_dir_for_mission(repo_root, canonical_slug)
        return candidate, first, second, third
'''


def test_index_discriminator_represents_a_four_site_qualname() -> None:
    """The acceptance fixture: one qualname carrying FOUR censused sites -- one
    ``candidate_feature_dir_for_mission`` call plus three
    ``primary_feature_dir_for_mission`` calls with distinct arguments.

    This exercises the LEDGER INDEX'S OWN key-construction functions
    (``_ledger_stay_lenient_index`` / ``_assert_no_duplicate_keys``) directly --
    review-cycle-1 finding: a prior version of this test asserted distinctness
    of ``_Finding.as_allow_key()`` (``(rel_path, qualname, token_line)``), a key
    that carries NO ``primitive`` discriminator at all and would be four-way
    distinct with or without G2's fix -- vacuous by construction. This version
    proves the INDEX key shape bites, both ways:

    1. the PREVIOUS (cycle-1) 3-column shape, ``(rel_path, qualname,
       primitive)`` -- collapses the three ``primary_feature_dir_for_mission``
       sites onto ONE key and REDS with ``DUPLICATE key`` when fed through the
       gate's own duplicate-detector;
    2. the CURRENT 4-column shape, ``(rel_path, qualname, primitive,
       site_token)`` -- resolves all four sites to four DISTINCT keys and
       passes the identical duplicate-detector cleanly.

    A cycle-1/WP07 review flagged the PREVIOUS version of this test as a
    live-file scan whose fixture assumption did not survive the migration it
    was validating (WP08, reconciliation item #3) -- this version pins the
    fixture as a frozen synthetic source string instead, so it stays
    meaningful regardless of how many real ``primary_feature_dir_for_mission``
    sites remain in the tree (now zero: the primitive itself is deleted).
    """
    module = _REPO_ROOT / "src" / "specify_cli" / "status" / "aggregate.py"
    source = _SYNTHETIC_FOUR_SITE_SOURCE
    findings = [
        finding
        for finding in _scan_read_bypass(source, module)
        if finding.callee in {"candidate_feature_dir_for_mission", "primary_feature_dir_for_mission"}
    ]
    qualname_findings = [
        finding for finding in findings if composite_key(source, finding.lineno)[0] == "MissionStatus._find_meta_path"
    ]
    assert len(qualname_findings) == 4, (
        "expected the four-site synthetic fixture (1 candidate_feature_dir_for_mission "
        f"+ 3 primary_feature_dir_for_mission) inside MissionStatus._find_meta_path; "
        f"found {len(qualname_findings)}: {[(f.lineno, f.callee) for f in qualname_findings]}"
    )
    primitives = {finding.callee for finding in qualname_findings}
    assert primitives == {"candidate_feature_dir_for_mission", "primary_feature_dir_for_mission"}, (
        "expected both the existing and the newly-censused primitive among "
        f"the four sites; found only {sorted(primitives)}"
    )

    rel_path = _placement_rel_path(module)
    qualname = "MissionStatus._find_meta_path"
    # The exact 4-column ledger row each finding WOULD occupy: rel_path,
    # qualname, primitive (G2's pre-existing discriminator), and a site-token
    # column carrying the site's own normalised token line (this fix) -- built
    # from the SAME ``composite_key`` primitive the gate's drift-proof anchor
    # uses (DIRECTIVE_041: never a raw line number).
    synthetic_rows: list[tuple[str, str, str, str]] = [
        (rel_path, qualname, finding.callee, composite_key(source, finding.lineno)[1])
        for finding in qualname_findings
    ]

    # --- Proof it FAILS against the PREVIOUS (cycle-1) 3-column key shape ---
    # Dropping the trailing site-token column collapses the three
    # primary_feature_dir_for_mission sites onto ONE (rel_path, qualname,
    # primitive) key -- the exact review-cycle-1 finding, reproduced here by
    # feeding the gate's OWN duplicate-detector the old shape's keys.
    old_shape_keys = [row[:3] for row in synthetic_rows]
    assert len(set(old_shape_keys)) == 2, (  # golden-count: cardinality-is-contract
        "sanity check failed: the previous 3-column shape was expected to "
        f"collapse 4 sites onto 2 keys; got {sorted(set(old_shape_keys))}"
    )
    with pytest.raises(AssertionError, match="DUPLICATE key"):
        _assert_no_duplicate_keys(old_shape_keys, heading="synthetic (pre-fix 3-column shape)")

    # --- Proof it PASSES against the CURRENT 4-column key shape (this fix) ---
    _assert_no_duplicate_keys(list(synthetic_rows), heading="synthetic (post-fix 4-column shape)")
    assert len(set(synthetic_rows)) == 4, (
        "the four sites inside the SAME qualname did not resolve to four "
        f"DISTINCT (rel_path, qualname, primitive, site_token) keys -- got "
        f"{sorted(set(synthetic_rows))}"
    )
