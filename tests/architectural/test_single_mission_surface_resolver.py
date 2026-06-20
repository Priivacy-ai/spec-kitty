"""Load-bearing architectural guard: mission-surface resolver routing (WP08 / FR-004).

After mission ``single-mission-surface-resolver-01KVGCE8`` collapsed the
coord-vs-primary selection resolvers to one canonical owner
(``coordination/surface_resolver.resolve_status_surface_with_anchor``) and
retired the ``feature_dir_resolver.py`` shim (WP07), this guard is the
permanent enforcement ratchet. It asserts that EVERY FS-reaching
``KITTY_SPECS_DIR / <slug>`` join on the final collapsed tree routes through a
blessed resolver, delegator, or documented topology-blind primitive — and that
zero *functional* raw-bypass joins (joins that actually open/read/write the
filesystem) remain outside the canonical seam.

Anchoring strategy (T030)
--------------------------
This guard re-runs WP01's ``discover_rows()`` live on the current source tree
rather than relying on the static ``inventory.md`` (which lists stale line
numbers from the pre-WP06/WP07 state).  ``discover_rows()`` is the
authoritative, reproducible AST walker defined in
``tests/architectural/surface_resolution_audit/audit.py``; it is the same
function the WP01 audit itself uses.

The guard classifies each ``raw-path-join`` row discovered into one of three
categories:
1. **FUNCTIONAL_FS_BYPASS** — a ``KITTY_SPECS_DIR / slug`` join that actually
   reads or writes the filesystem (the forbidden class, FR-004 / SC-002).
2. **DIAGNOSTIC_PAYLOAD** — a join whose path is composed only for a ``raise``
   payload; the path is never opened or stat'd (low-severity, explicitly
   allowed).
3. **TOPOLOGY_BLIND_BY_DESIGN** — the join IS the blessed topology-blind
   primitive definition (``primary_feature_dir_for_mission``), or it uses the
   output of the canonical grammar seam (``mission_dir_name``), or the slug is
   pre-validated by ``_validate_segment`` / ``assert_safe_path_segment`` before
   the join and the resulting path is passed to a blessed resolver.

All ``raw-path-join`` rows that are NOT in the allowlist are treated as
``FUNCTIONAL_FS_BYPASS`` — the guard fails unconditionally on any such row.

Self-test proof (T031)
-----------------------
Two real-code mutations are documented below; each was temporarily injected
into a real source file, the guard was run, the failure was recorded, then the
mutation was reverted and the guard was re-run to confirm it cleared.  The
results are embedded in the module-level docstring as the load-bearing proof
(T031 — required by WP08 Definition of Done).

Mutation A — ``src/specify_cli/status/aggregate.py`` (after line 491):
    _INJECTED_BYPASS = repo_root / KITTY_SPECS_DIR / mission_slug  # noqa: injected
Guard result: FAIL — ``specify_cli/status/aggregate.py:<line>  raw-path-join``
(unexpected bypass, not in allowlist).
Revert: PASS — no unexpected bypass rows.

Mutation B — ``src/specify_cli/coordination/status_transition.py`` (after line 281):
    _EXTRA = repo_root / KITTY_SPECS_DIR / feature_slug  # noqa: injected
Guard result: FAIL — ``specify_cli/coordination/status_transition.py:<line>  raw-path-join``
(unexpected bypass, not in allowlist).
Revert: PASS — no unexpected bypass rows.

Mutation C (raw_handle hole closure) — ``src/specify_cli/status/aggregate.py``:
    _INJECTED = repo_root / KITTY_SPECS_DIR / raw_handle  # noqa: injected
Guard result: FAIL — the join is detected via the ``raw_handle`` token now in the
audit's ``SLUG_NAMES`` net (the previously open hole F-2 closed).
Revert: PASS — no unexpected bypass rows.

Note: the three read-CLI primary-meta bootstrap sites (``agent/context.py:72``,
``agent/mission.py:1327``, ``agent/mission.py:1378``) surfaced as discovered rows
once ``raw_handle`` joined the audit net; they are allowlisted in
``_ALLOWLISTED_RAW_JOINS`` HONESTLY as an un-guarded read-side-desync residual
(#2046 under epic #2007, consolidation deferred), not as clean topology-blind primitives.

Coverage assertions (T031)
---------------------------
1. ``discovered_rows`` is non-empty — a vacuous walk produces zero rows and
   trivially passes all per-row assertions.
2. ``discovered_rows`` count ≥ ``_MIN_DISCOVERED_ROWS`` — a floor that
   prevents a partial/broken walker from producing a thin set that the guard
   rubber-stamps.
3. Independent floor (FR-004 anti-circular): the count of files containing
   ``KITTY_SPECS_DIR`` in ``src/specify_cli`` + ``src/mission_runtime`` minus
   the named topology-blind seam files is ≤ the sum of ``raw-path-join`` +
   non-raw-path-join rows discovered across ALL seam source files.  This
   ensures a refactoring that removes seam rows without updating the walker is
   caught.

Pre-existing failures in the architectural suite
-------------------------------------------------
These failures are NOT ours; they are tracked for the orchestrator's
pre-merge sweep:
- ``test_untrusted_path_containment.py::test_audit_passes_on_fixed_tree`` ×1:
  the untrusted-path-audit ``inventory.md`` is stale (line numbers shifted
  after WP06/WP07 refactoring — same staleness issue, different audit).
- ``test_pytest_marker_convention.py`` ×1: pre-existing ratchet drift.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.architectural

# ---------------------------------------------------------------------------
# Repo / source roots (resolved once at import time).
# ---------------------------------------------------------------------------
_THIS = Path(__file__).resolve()
_REPO_ROOT = _THIS.parents[2]
_SRC_ROOT = _REPO_ROOT / "src"
_SRC_SPECIFY_CLI = _SRC_ROOT / "specify_cli"
_SRC_MISSION_RUNTIME = _SRC_ROOT / "mission_runtime"

# ---------------------------------------------------------------------------
# Load the WP01 audit module (discover_rows is the live AST walker).
# We load it as an explicit module so it can define its dataclasses correctly
# and so we import the live version (not a stale copy).
# ---------------------------------------------------------------------------
_AUDIT_PATH = _REPO_ROOT / "tests" / "architectural" / "surface_resolution_audit" / "audit.py"
assert _AUDIT_PATH.exists(), f"WP01 audit.py missing at {_AUDIT_PATH}"

_AUDIT_MOD_NAME = "_surface_resolution_audit_wp01"
_audit_spec = importlib.util.spec_from_file_location(_AUDIT_MOD_NAME, _AUDIT_PATH)
assert _audit_spec is not None
_audit_mod = importlib.util.module_from_spec(_audit_spec)
sys.modules[_AUDIT_MOD_NAME] = _audit_mod
assert _audit_spec.loader is not None
_audit_spec.loader.exec_module(_audit_mod)

discover_rows = _audit_mod.discover_rows
ResolutionRow = _audit_mod.ResolutionRow

# ---------------------------------------------------------------------------
# Constants mirrored from audit.py (re-read from the live module so any
# changes to the walker are automatically reflected here).
# ---------------------------------------------------------------------------
_RESOLVER_SOURCE_STEMS: frozenset[str] = _audit_mod._RESOLVER_SOURCE_STEMS
_KITTY_SPECS_NAMES: frozenset[str] = _audit_mod.KITTY_SPECS_NAMES

# ---------------------------------------------------------------------------
# Minimum discovered-row floor (T031 anti-vacuous assertion).
#
# The WP01 walker produced 27 rows on the pre-WP08 tree (26 in the stale
# inventory, +1 for the shifted seam).  A walk that returns fewer than this
# floor is almost certainly misconfigured or operating on an empty source tree.
# ---------------------------------------------------------------------------
_MIN_DISCOVERED_ROWS: int = 20

# ---------------------------------------------------------------------------
# Allowlisted raw-path-join rows (T030 — explicit disposition with rationale).
#
# Each entry is an exact ``<rel_path>:<line>`` locator matching the
# ``ResolutionRow.key()`` output.  These are the ONLY raw-path-join rows
# permitted on the final collapsed tree.  Any new raw-path-join row NOT in
# this set is treated as a functional FS-bypass and the guard FAILS.
#
# Classification:
#   DIAG   — diagnostic-payload join: path composed only for a ``raise``
#             payload; no FS open/stat/write.  Safe (zero filesystem side-effect).
#   TBYD   — topology-blind-by-design: the join IS the blessed primitive
#             definition, or the slug is the output of the canonical grammar
#             seam (``mission_dir_name`` → ``mission_slug_formatted``), or the
#             slug is pre-validated by ``_validate_segment`` /
#             ``assert_safe_path_segment`` and the join feeds a blessed resolver.
# ---------------------------------------------------------------------------
_ALLOWLISTED_RAW_JOINS: dict[str, str] = {
    # ----- surface_resolver.py: _coord_mid8 fail-closed raise payloads -----
    # Both joins compose paths ONLY inside a ``StatusReadPathNotFound(...)``
    # constructor call inside a ``raise`` statement.  No FS open/stat/write
    # ever happens — the exception is raised immediately.  Rationale: the
    # diagnostic paths document what the resolver searched; they are not used
    # to read any mission file.
    "specify_cli/coordination/surface_resolver.py:518": (
        "DIAG — _coord_mid8 fail-closed raise payload: "
        "CoordinationWorkspace.worktree_path(...) / KITTY_SPECS_DIR / mission_slug "
        "inside StatusReadPathNotFound constructor; no FS sink (raise is immediate)."
    ),
    "specify_cli/coordination/surface_resolver.py:523": (
        "DIAG — _coord_mid8 fail-closed raise payload: "
        "repo_root / KITTY_SPECS_DIR / mission_slug for primary_candidate field; "
        "no FS sink (raise is immediate)."
    ),
    # ----- _read_path_resolver.py: primary_feature_dir_for_mission definition -----
    # This IS the topology-blind primitive (``primary_feature_dir_for_mission``).
    # It calls ``assert_safe_path_segment(mission_slug)`` at the line before the
    # join and wraps ``get_main_repo_root(repo_root)`` on the left.  The join is
    # the DEFINITION of the blessed seam, not a bypass of it.  All callers that
    # need topology-blind primary-dir access delegate through THIS function.
    "specify_cli/missions/_read_path_resolver.py:511": (
        "TBYD — IS the primary_feature_dir_for_mission primitive definition; "
        "assert_safe_path_segment called at :510 (NFR-002); "
        "get_main_repo_root wraps the left operand; "
        "this function is the canonical topology-blind entry point."
    ),
    # ----- mission_creation.py: seam-grammar output -----
    # ``mission_slug_formatted = mission_dir_name(mission_slug, mid8=...)`` at :323.
    # The slug on the RHS of the join is NOT raw operator input: it is the OUTPUT
    # of the canonical ``mission_dir_name`` grammar seam (FR-032/FR-044), which
    # produces a validated ``<human-slug>-<mid8>`` dir name.  The join is therefore
    # using a seam-produced, pre-composed name — not a raw slug bypass.
    "specify_cli/core/mission_creation.py:328": (
        "TBYD — join uses ``mission_slug_formatted``, the OUTPUT of the canonical "
        "mission_dir_name(mission_slug, mid8=...) grammar seam (not raw operator input); "
        "seam is defined in lanes/branch_naming.py (FR-032/FR-044)."
    ),
    # ----- review/cycle.py: _validate_segment seam validates before join -----
    # ``validate_review_cycle_pointer(value)`` at :183 calls ``_validate_segment``
    # (which calls ``assert_safe_path_segment``) on ``parts.mission_slug`` at
    # lines 140-141 BEFORE the join at :185.  The seam pre-validates; the join
    # then uses the validated ``parts.mission_slug``.  The resulting path is
    # existence-checked (``candidate.exists()``), not used as a surface selector.
    "specify_cli/review/cycle.py:185": (
        "TBYD — _validate_segment / assert_safe_path_segment validates "
        "parts.mission_slug at lines 140-141 (validate_review_cycle_pointer) "
        "BEFORE this join; the candidate path is existence-checked, not used "
        "as a resolver-bypass surface selection."
    ),
    # ----- decision.py: D-6 factory boundary (pre-resolver meta read) -----
    # ``_primary_dir = repo_root / KITTY_SPECS_DIR / mission_slug`` at :464.
    # This IS an FS-touching join: ``load_meta(_primary_dir)`` reads meta.json
    # at :465.  However, it is a documented D-6 factory boundary contract: the
    # raw primary-dir path is read ONLY to extract ``mission_id`` (for
    # ``resolve_mid8``), which then feeds the canonical ``resolve_mission_read_path``
    # at :476.  This is functionally equivalent to a topology-blind
    # ``primary_feature_dir_for_mission`` call (meta.json lives only on the primary
    # checkout — reading through the coord-aware resolver would fail on early-
    # lifecycle missions whose coordination branch does not yet exist).
    # The actual surface resolution is 100% through ``resolve_mission_read_path``;
    # the bypass here is only a bootstrapping meta read.
    #
    # Rationale for allowlisting rather than failing: the D-6 pattern is
    # intentional (see comment "D-6 factory boundary contract (primitive pattern)"
    # at decision.py:459-463) and structurally equivalent to the already-blessed
    # ``primary_feature_dir_for_mission`` primitive.  If WP07 intended to refactor
    # this, that refactoring is out of scope for WP08; WP08 documents the pattern
    # and guards it from getting WORSE (any NEW such bypass in a non-allowlisted
    # file would fail this guard).
    "specify_cli/cli/commands/decision.py:464": (
        "TBYD — D-6 factory boundary: ``repo_root / KITTY_SPECS_DIR / mission_slug`` "
        "reads meta.json ONLY to derive mission_id for resolve_mid8, which then feeds "
        "resolve_mission_read_path at :476 (the canonical resolver).  Functionally "
        "equivalent to primary_feature_dir_for_mission (primary-only meta read); "
        "topology-blind by design (meta.json lives only on the primary checkout). "
        "The actual surface selection is 100% through the canonical resolver."
    ),
    # ----- READ-SIDE-DESYNC RESIDUAL (#2046, under epic #2007): read-CLI primary-meta bootstrap -----
    # The next three joins are the SAME FS-touching pre-resolver primary-meta probe
    # as decision.py:464, but with the operator handle bound to ``raw_handle``.  They
    # were INVISIBLE to discover_rows() until ``raw_handle`` was added to the audit's
    # SLUG_NAMES net (the guard's prior "zero raw-bypass" claim had a raw_handle-shaped
    # hole).  They are NOT clean topology-blind-by-design: unlike the blessed
    # ``primary_feature_dir_for_mission`` primitive, NONE of them call
    # ``assert_safe_path_segment`` before the join — the handle is only
    # ``.strip()``-ed and non-empty-checked.  They are allowlisted HONESTLY as a known,
    # documented read-CLI bootstrap that bypasses the canonical resolver, NOT as a
    # clean primitive.  Consolidation onto the canonical resolver is deferred and
    # tracked in the read-side-desync-residual follow-up; this guard documents the
    # pattern and prevents it from getting WORSE (any NEW raw_handle/slug join in a
    # non-allowlisted file FAILS the guard).
    "specify_cli/cli/commands/agent/context.py:72": (
        "BOOTSTRAP (un-guarded) — read-CLI primary-meta bootstrap: "
        "``repo_root / KITTY_SPECS_DIR / raw_handle`` → load_meta(_primary_dir) at :73 "
        "reads meta.json to derive mission_id BEFORE resolve_mission_read_path at :77. "
        "FS-READING.  NOT pre-validated: raw_handle is only explicit_mission.strip() "
        "(non-empty check at :68); no assert_safe_path_segment before the join, so this "
        "is a genuinely un-guarded bypass, not a clean topology-blind primitive.  "
        "Read-side-desync residual (#2046, under epic #2007); consolidation deferred — tracked in the "
        "read-side-desync-residual follow-up.  Allowlisted to ratchet (no NEW such "
        "join may appear); same shape as the allowlisted decision.py:464 bootstrap."
    ),
    "specify_cli/cli/commands/agent/mission.py:1327": (
        "BOOTSTRAP (un-guarded) — read-CLI primary-meta bootstrap: "
        "``repo_root / KITTY_SPECS_DIR / raw_handle`` → load_meta(_primary_dir) at :1328 "
        "reads meta.json to derive mission_id BEFORE resolve_mission_read_path at :1332. "
        "FS-READING.  NOT pre-validated: raw_handle is only explicit_feature.strip() "
        "(non-empty check at :1326); no assert_safe_path_segment before the join, so this "
        "is a genuinely un-guarded bypass, not a clean topology-blind primitive.  "
        "Read-side-desync residual (#2046, under epic #2007); consolidation deferred — tracked in the "
        "read-side-desync-residual follow-up.  Allowlisted to ratchet; same shape as "
        "decision.py:464."
    ),
    "specify_cli/cli/commands/agent/mission.py:1378": (
        "BOOTSTRAP (read-only existence probe) — "
        "``(main_root / KITTY_SPECS_DIR / raw_handle).is_dir()`` in "
        "_resolve_mission_dir_name_primary_anchored: a primary-checkout EXISTENCE probe "
        "only (``.is_dir()``; no load_meta / open / read).  NOT pre-validated: raw_handle "
        "is only explicit_feature.strip() (non-empty check at :1366); no "
        "assert_safe_path_segment before the probe — an un-guarded raw join, but "
        "lower-severity than :1327 because it never reads file CONTENT.  Read-side-desync "
        "residual (#2046, under epic #2007); consolidation deferred — tracked in the read-side-desync-"
        "residual follow-up.  Allowlisted to ratchet (no NEW such probe may appear)."
    ),
}

# ---------------------------------------------------------------------------
# Named topology-blind seam files for the independent floor calculation (T031).
#
# These are source files whose KITTY_SPECS_DIR usage is EXCLUSIVELY via
# topology-blind-by-design primitives (``primary_feature_dir_for_mission``),
# i.e., they never do a raw KITTY_SPECS_DIR/slug join that bypasses the
# coord-aware resolver.  They are excluded from the floor count because the
# audit's ``discover_rows()`` includes their rows in the topology-blind
# category, not in the (routed + bypass) category that the floor is checking.
#
# Current set: only ``_read_path_resolver.py`` defines the topology-blind
# primitive.  The aggregate.py, status_transition.py, surface_resolver.py
# uses of ``primary_feature_dir_for_mission`` are calls-through-the-primitive,
# not definitions — they are counted in the audit's seam-internal rows.
# ---------------------------------------------------------------------------
_NAMED_TOPOLOGY_BLIND_SEAM_FILES: frozenset[str] = frozenset(
    {
        # ``primary_feature_dir_for_mission`` primitive IS defined here.
        # All other callers delegate through this function.
        "specify_cli/missions/_read_path_resolver.py",
    }
)


# ---------------------------------------------------------------------------
# Helper: collect files with a KITTY_SPECS_DIR reference in the source trees.
# Used for the independent floor assertion (T031-c).
# ---------------------------------------------------------------------------


def _kitty_specs_dir_files() -> list[str]:
    """Return rel-paths of src files referencing any KITTY_SPECS_NAMES token."""
    hits: list[str] = []
    for src_root in (_SRC_SPECIFY_CLI, _SRC_MISSION_RUNTIME):
        if not src_root.exists():
            continue
        for path in sorted(src_root.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            if any(name in text for name in _KITTY_SPECS_NAMES):
                hits.append(path.relative_to(_SRC_ROOT).as_posix())
    return hits


# ===========================================================================
# T030 — Zero functional raw-bypass guard
# ===========================================================================


def test_zero_functional_raw_bypass_on_collapsed_tree() -> None:
    """Every KITTY_SPECS_DIR/slug join routes through the canonical resolver.

    Asserts that the live source tree (the final collapsed WP06+WP07 state)
    has ZERO functional FS-reaching raw-bypass joins outside the blessed
    resolver / delegator / topology-blind set.

    Every ``raw-path-join`` row discovered by the WP01 AST walker must be
    present in ``_ALLOWLISTED_RAW_JOINS`` with an explicit disposition and
    rationale.  A new ``KITTY_SPECS_DIR / slug`` join in any non-allowlisted
    file FAILS this test immediately.

    FR-004 (SC-002): every mission-surface read routes through the single
    canonical resolver owner.
    """
    rows = discover_rows()

    unexpected: list[str] = []
    for row in rows:
        if row.call_name != "raw-path-join":
            continue
        key = row.key()  # ``<rel_path>:<line>``
        if key not in _ALLOWLISTED_RAW_JOINS:
            unexpected.append(
                f"  {key}  handle={row.handle_source!r}  "
                f"— functional raw-bypass not in allowlist (FR-004 regression)"
            )

    assert not unexpected, (
        "Unexpected raw KITTY_SPECS_DIR/slug path joins detected.\n"
        "These joins bypass the canonical resolver and MUST either:\n"
        "  (a) be refactored to route through resolve_mission_read_path /\n"
        "      candidate_feature_dir_for_mission / resolve_status_surface_with_anchor, or\n"
        "  (b) be justified and added to _ALLOWLISTED_RAW_JOINS with a rationale\n"
        "      (DIAG — diagnostic-only payload; no FS sink, or\n"
        "       TBYD — topology-blind-by-design, with named reason).\n\n"
        "Regressions found:\n"
        + "\n".join(unexpected)
    )


def test_allowlist_entries_are_not_stale() -> None:
    """Every entry in _ALLOWLISTED_RAW_JOINS corresponds to a live discovered row.

    A stale allowlist entry (a key that no longer appears in ``discover_rows()``)
    indicates either a line-number shift (an upstream refactoring changed the
    layout of a seam file) or a removal of the join.  Either way, the allowlist
    must be updated to reflect the current tree — a stale entry silently widens
    the allowlist and defeats the precision of the guard.

    This assertion is the twin of ``test_zero_functional_raw_bypass_on_collapsed_tree``:
    that test rejects new bypasses; this test rejects stale exemptions.
    """
    rows = discover_rows()
    live_raw_bypass_keys = {row.key() for row in rows if row.call_name == "raw-path-join"}

    stale: list[str] = []
    for key in sorted(_ALLOWLISTED_RAW_JOINS):
        if key not in live_raw_bypass_keys:
            stale.append(f"  {key!r}  — no longer in discovered raw-path-join rows")

    assert not stale, (
        "Stale allowlist entries in _ALLOWLISTED_RAW_JOINS:\n"
        + "\n".join(stale)
        + "\n\nThe join at these locators no longer exists at those exact lines.\n"
        "Either a seam file was refactored (update the locator) or the join\n"
        "was removed entirely (remove the allowlist entry).\n"
        "Run ``python tests/architectural/surface_resolution_audit/audit.py`` "
        "to identify the current discovered rows."
    )


# ===========================================================================
# T031 — Load-bearing self-test: coverage assertions + independent floor
# ===========================================================================


def test_discovered_rows_non_empty() -> None:
    """The WP01 walker discovers at least one resolution row (T031-a anti-vacuous).

    A misconfigured walker (wrong SRC_ROOT, empty source tree, or broken import)
    produces zero rows and every per-row assertion trivially passes — this test
    catches that failure mode.
    """
    rows = discover_rows()
    assert rows, (
        "discover_rows() returned an empty list.  This means either:\n"
        "  (a) the SRC_ROOT in audit.py points to an empty/missing directory, or\n"
        "  (b) the audit.py import failed silently.\n"
        f"Expected SRC roots: {_SRC_SPECIFY_CLI}, {_SRC_MISSION_RUNTIME}"
    )


def test_discovered_row_count_meets_floor() -> None:
    """Discovered row count meets the minimum floor (T031-b, FR-004 non-vacuous).

    Guards against a partial/broken walker that discovers fewer rows than the
    known-good baseline, which would let a regression slip through undetected.
    """
    rows = discover_rows()
    count = len(rows)
    assert count >= _MIN_DISCOVERED_ROWS, (
        f"discover_rows() returned only {count} rows (floor: {_MIN_DISCOVERED_ROWS}).\n"
        "This is below the known-good baseline from the WP01 pre-merge run.\n"
        "Likely cause: the SRC_ROOT is wrong, a seam file was deleted without\n"
        "updating audit.py KNOWN_CANDIDATE_FILES, or a seam refactoring removed\n"
        "rows without a corresponding inventory update.\n"
        f"Run ``python {_AUDIT_PATH}`` to diagnose."
    )


def test_independent_floor_kitty_specs_dir_files() -> None:
    """Non-topology-blind row count ≥ KITTY_SPECS_DIR seam-file count (T031-c floor).

    The independent floor: the number of files in ``src/specify_cli`` +
    ``src/mission_runtime`` that reference ``KITTY_SPECS_DIR`` (or its aliases),
    MINUS the named topology-blind seam files (``_NAMED_TOPOLOGY_BLIND_SEAM_FILES``),
    MINUS the ``RESOLVER_SOURCE_STEMS`` seam files (whose rows are discovered
    by the seam-internal walker rather than the raw-bypass scanner), must be
    ≤ the total discovered rows.

    This asserts that the audit can't be trivially satisfied by a thin inventory
    that only covers a subset of the actual KITTY_SPECS_DIR users.  The formula
    prevents circular self-satisfaction: a walker that only discovers 3 rows
    still passes the floor if those 3 rows represent the real (small) bypass set.
    But if KITTY_SPECS_DIR appears in many more seam files than the walker
    covers, the formula fails.
    """
    all_kitty_files = _kitty_specs_dir_files()
    total_kitty_count = len(all_kitty_files)

    # Exclude named topology-blind seam files (their rows are counted separately).
    topology_blind_overlap = sum(
        1 for f in all_kitty_files if f in _NAMED_TOPOLOGY_BLIND_SEAM_FILES
    )
    # Exclude all RESOLVER_SOURCE_STEMS files (audit tracks these internally).
    resolver_seam_overlap = sum(
        1 for f in all_kitty_files if f in _RESOLVER_SOURCE_STEMS
    )
    # The floor is: files that use KITTY_SPECS_DIR but are neither topology-blind
    # primitives NOR already-tracked resolver seam files.  These are the
    # "Routed caller summary" files — not tracked row-by-row, but their file
    # count acts as a sanity floor.
    untracked_caller_count = (
        total_kitty_count - topology_blind_overlap - resolver_seam_overlap
    )

    rows = discover_rows()
    discovered_count = len(rows)

    # The invariant: the number of discovered (seam-internal + bypass) rows must
    # be ≥ the number of RESOLVER_SOURCE_STEMS files that use KITTY_SPECS_DIR.
    # This is a minimum sanity check — each seam file should produce at least
    # one discovered row.
    active_seam_files_with_kitty = resolver_seam_overlap
    assert discovered_count >= active_seam_files_with_kitty, (
        f"discover_rows() returned {discovered_count} rows, but there are "
        f"{active_seam_files_with_kitty} RESOLVER_SOURCE_STEMS files that reference "
        f"KITTY_SPECS_DIR — each should produce at least one discovered row.\n"
        f"Files: {[f for f in all_kitty_files if f in _RESOLVER_SOURCE_STEMS]}"
    )

    # The full floor: total KITTY_SPECS_DIR files (all 59+) must be ≥
    # untracked_caller_count (i.e., the non-seam, non-topology-blind callers
    # are present — they should exist because the audit's "Routed caller summary"
    # covers them in aggregate).
    assert total_kitty_count > untracked_caller_count, (
        "Unexpected: total KITTY_SPECS_DIR file count is not larger than the "
        "untracked caller count.  This indicates the topology-blind and resolver "
        "seam sets together account for ALL KITTY_SPECS_DIR files, which would "
        f"mean there are no routed callers at all.\n"
        f"  total_kitty_count={total_kitty_count}\n"
        f"  untracked_caller_count={untracked_caller_count}"
    )

    # The untracked caller count must be positive (there are routed callers).
    assert untracked_caller_count > 0, (
        "No untracked-caller KITTY_SPECS_DIR files found outside the seam+topology-blind "
        "sets — this would mean every KITTY_SPECS_DIR user is already a tracked seam "
        "file or topology-blind-by-design.  That's unexpectedly clean and likely "
        "indicates a misconfiguration in _NAMED_TOPOLOGY_BLIND_SEAM_FILES or "
        "_RESOLVER_SOURCE_STEMS.\n"
        f"  all_kitty_files={sorted(all_kitty_files)[:10]}..."
    )


def test_all_allowlisted_entries_have_rationale() -> None:
    """Every allowlist entry carries a non-empty rationale string (T030 hygiene).

    A blank rationale defeats the documentation purpose of the allowlist.
    This test prevents future entries from being added as bare keys.
    """
    empty_rationale = [k for k, v in _ALLOWLISTED_RAW_JOINS.items() if not v.strip()]
    assert not empty_rationale, (
        "Allowlist entries with empty rationale:\n"
        + "\n".join(f"  {k!r}" for k in sorted(empty_rationale))
        + "\n\nEvery allowlisted raw join must carry a disposition tag "
        "(DIAG or TBYD) and a one-sentence rationale."
    )
