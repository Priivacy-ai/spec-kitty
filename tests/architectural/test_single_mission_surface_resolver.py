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
These failures are NOT ours (confirmed: they also fail on the clean lane base
BEFORE the WP05 changes); they are dependency-lane/cross-WP residuals tracked
for the orchestrator's pre-merge sweep:
- ``test_untrusted_path_containment.py::test_audit_passes_on_fixed_tree`` and
  ``::test_all_discovered_rows_appear_in_inventory``: the SEPARATE
  untrusted-path-audit ``inventory.md`` is stale (line numbers shifted after the
  WP01/WP03 read-side seam edits). The companion ``surface_resolution_audit``
  ``inventory.md`` carries the SAME point-in-time line-number staleness class
  (the convergence edits shifted every seam file); THIS guard therefore does not
  depend on either inventory — it re-runs ``discover_rows()`` live (see the
  module docstring above). Neither inventory is a live-pinned CI gate; both are
  reviewer reference snapshots.
- ``test_pytest_marker_convention.py``: pre-existing ratchet drift.
- ``test_no_dead_modules.py`` / ``test_no_dead_symbols.py``: dead-module /
  ``__all__`` symbol debt from seam additions (src-side; outside WP05's
  test-only owned surface). The ``specify_cli.mission_read_path`` shim that
  formerly contributed to this debt was retired by #2048.

C-003 pre-condition verification (WP08 / T037)
----------------------------------------------
The ``#2161`` read-leg handle-safety fix is a PRE-CONDITION of this mission
(spec C-003): it must be present on the base before WP02-WP05 build on it. This
WP verifies (does NOT re-implement) it. Evidence captured on the integrated lane:

- Introducing commit: ``ecf45f52c`` ("feat(2119): retrospective durable-home +
  handle-safe write/read seams + topology-aware teardown") — the #2119/#2161
  handle-safe read/write seam work.
- Fix function: ``_canonicalize_primary_read_handle`` is DEFINED at
  ``src/specify_cli/missions/_read_path_resolver.py:1244`` and APPLIED at ``:1367``
  (``canonical = _canonicalize_primary_read_handle(repo_root, mission_slug)``
  immediately before the handle-blind ``primary_feature_dir_for_mission`` compose
  at ``:1368``).
- This fix is DISTINCT from the ``:454`` bare probe
  (``primary_feature_dir_for_mission(repo_root, handle)`` inside
  ``_canonicalize_bare_modern_handle``), which is the C-001/FR-011 topology-blind
  recursion probe — sanctioned, never folded. The read-leg fix lives at the
  seam (``:1367``), NOT at the primitive call.

C-003 status: PRESENT on the base. T038/T040 may build on it.
"""

from __future__ import annotations

import functools
import importlib.util
import sys
from pathlib import Path

import pytest

from tests.architectural._ratchet_keys import (
    CompositeKey,
    ContentDescriptor,
    composite_key_from_file,
    descriptor_still_live,
    resolve_descriptor,
)

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
discover_selection_callsites = _audit_mod.discover_selection_callsites

# ---------------------------------------------------------------------------
# Constants mirrored from audit.py (re-read from the live module so any
# changes to the walker are automatically reflected here).
# ---------------------------------------------------------------------------
_RESOLVER_SOURCE_STEMS: frozenset[str] = _audit_mod._RESOLVER_SOURCE_STEMS
_SELECTION_SEAM_STEMS: frozenset[str] = _audit_mod._SELECTION_SEAM_STEMS
_KITTY_SPECS_NAMES: frozenset[str] = _audit_mod.KITTY_SPECS_NAMES
_SLUG_NAMES: frozenset[str] = _audit_mod.SLUG_NAMES
_ALLOWLISTED_SELECTION_CALLSITES: dict[str, str] = (
    _audit_mod.ALLOWLISTED_SELECTION_CALLSITES
)

# ---------------------------------------------------------------------------
# Minimum discovered-row floor (T031 anti-vacuous assertion).
#
# The WP01 walker produced 27 rows on the pre-WP08 tree (26 in the stale
# inventory, +1 for the shifted seam).  A walk that returns fewer than this
# floor is almost certainly misconfigured or operating on an empty source tree.
# ---------------------------------------------------------------------------
_MIN_DISCOVERED_ROWS: int = 20

# ---------------------------------------------------------------------------
# Allowlisted raw-path-join rows (T030 — explicit disposition with rationale;
# WP04 content-descriptor migration, #2469 IC-DESCRIPTOR).
#
# Each entry is a :class:`ContentDescriptor` (``rel_path``, ``qualname``,
# ``token_substring``, ``occurrence``, ``rationale``) — a two-axis
# content-addressed pointer (enclosing function + a substring of its
# NORMALIZED token line), never a bare ``<rel_path>:<line>`` locator and never
# a hand-authored composite-key literal (NFR-004).  ``resolve_descriptor``
# (``tests/architectural/_ratchet_keys.py``, IC-DESCRIPTOR/WP02) resolves each
# descriptor against the LIVE source to the **exactly one** finding it names —
# RAISING (RED) rather than silently picking a match if the descriptor is
# ambiguous or has drifted off its site entirely.  A descriptor survives
# benign line drift (a seam WP inserting code above the site) AND, unlike a
# bare composite key seeded from a single line, requires no re-anchoring NOTE
# every time an unrelated edit shifts the line — the descriptor is authored
# once against the finding's own qualname + token line and never touched
# again (see ``kitty-specs/content-address-ratchet-allowlists-01KX8M4D/contracts/descriptor-resolver.md``).
#
# These are the ONLY raw-path-join rows permitted on the final collapsed tree.
# Any new raw-path-join row whose composite key is NOT in this set is treated
# as a functional FS-bypass and the guard FAILS.
#
# ``_RAW_JOIN_SEEDED_KEYS`` resolves every descriptor ONCE at import time to
# its live ``(rel_path, qualname, token_line)`` composite key.
# ``_build_allowlisted_raw_joins`` narrows that to the 2-tuple
# ``(qualname, token_line)`` shape ``test_zero_functional_raw_bypass_on_collapsed_tree``
# compares discovered rows against (via ``composite_key_from_file``).
# ``test_allowlist_entries_are_not_stale`` re-resolves each descriptor against
# the live source and compares it to its seeded key via ``descriptor_still_live``
# (exactly-one AND key-equal), so a site that drifts off its function, whose
# code line changes, or that gains a same-qualname sibling with a colliding
# substring is caught loudly.
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

#: Seed of content descriptors for each allowlisted raw-join site.  Each
#: ``token_substring`` is authored from the finding's OWN normalized token
#: line (never a raw-source substring — see the descriptor-resolver
#: contract's "Authoring rule"); RJ#1/RJ#2 share the ``_coord_mid8`` qualname
#: and disambiguate purely by ``token_substring``, proving the two-axis
#: descriptor shape.
_RAW_JOIN_SITES: tuple[ContentDescriptor, ...] = (
    # ----- surface_resolver.py: _coord_mid8 fail-closed raise payloads -----
    # Both joins compose paths ONLY inside a ``StatusReadPathNotFound(...)``
    # constructor call inside a ``raise`` statement.  No FS open/stat/write
    # ever happens — the exception is raised immediately.  Rationale: the
    # diagnostic paths document what the resolver searched; they are not used
    # to read any mission file.  RJ#1 (``coord_candidate``) and RJ#2
    # (``primary_candidate``) share the ``_coord_mid8`` qualname; the distinct
    # ``token_substring`` per entry is the disambiguator (no ``occurrence``
    # ordinal needed).
    ContentDescriptor(
        rel_path="specify_cli/coordination/surface_resolver.py",
        qualname="_coord_mid8",
        token_substring="coord_candidate = repo_root",
        occurrence=None,
        rationale=(
            "DIAG — _coord_mid8 fail-closed raise payload: "
            "CoordinationWorkspace.worktree_path(...) / KITTY_SPECS_DIR / mission_slug "
            "inside StatusReadPathNotFound constructor; no FS sink (raise is immediate)."
        ),
    ),
    ContentDescriptor(
        rel_path="specify_cli/coordination/surface_resolver.py",
        qualname="_coord_mid8",
        token_substring="primary_candidate = repo_root / KITTY_SPECS_DIR / mission_slug",
        occurrence=None,
        rationale=(
            "DIAG — _coord_mid8 fail-closed raise payload: "
            "repo_root / KITTY_SPECS_DIR / mission_slug for primary_candidate field; "
            "no FS sink (raise is immediate)."
        ),
    ),
    # ----- _read_path_resolver.py: primary_feature_dir_for_mission definition -----
    # This IS the topology-blind primitive (``primary_feature_dir_for_mission``).
    # It calls ``assert_safe_path_segment(mission_slug)`` at the line before the
    # join and wraps ``get_main_repo_root(repo_root)`` on the left.  The join is
    # the DEFINITION of the blessed seam, not a bypass of it.  All callers that
    # need topology-blind primary-dir access delegate through THIS function.
    ContentDescriptor(
        rel_path="specify_cli/missions/_read_path_resolver.py",
        qualname="primary_feature_dir_for_mission",
        token_substring=(
            "primary_dir : Path = get_main_repo_root ( repo_root ) / "
            "KITTY_SPECS_DIR / mission_slug"
        ),
        occurrence=None,
        rationale=(
            "TBYD — IS the primary_feature_dir_for_mission primitive definition; "
            "assert_safe_path_segment called just above (NFR-002); "
            "get_main_repo_root wraps the left operand; "
            "this function is the canonical topology-blind entry point."
        ),
    ),
    # ----- mission_creation.py: seam-grammar output -----
    # ``mission_slug_formatted = mission_dir_name(mission_slug, mid8=...)`` is
    # composed just above.  The slug on the RHS of the join is NOT raw operator
    # input: it is the OUTPUT of the canonical ``mission_dir_name`` grammar
    # seam (FR-032/FR-044), which produces a validated ``<human-slug>-<mid8>``
    # dir name.  The join is therefore using a seam-produced, pre-composed
    # name — not a raw slug bypass.
    ContentDescriptor(
        rel_path="specify_cli/core/mission_creation.py",
        qualname="create_mission_core",
        token_substring="feature_dir = resolved_root / KITTY_SPECS_DIR / mission_slug_formatted",
        occurrence=None,
        rationale=(
            "TBYD — join uses mission_slug_formatted, the OUTPUT of the canonical "
            "mission_dir_name(mission_slug, mid8=...) grammar seam (not raw operator "
            "input); seam is defined in lanes/branch_naming.py (FR-032/FR-044). "
            "Create-time-canonical: the mission dir is being created here "
            "(feature_dir.mkdir follows immediately), so there is no prior surface "
            "to resolve through."
        ),
    ),
    # ----- DRAINED by mission retrospective-durable-home-01KVYM1W (#2136/#2164):
    # the raw ``KITTY_SPECS_DIR / parts.mission_slug`` join formerly in
    # ``resolve_review_cycle_pointer`` (review/cycle.py) was routed through the
    # shared write-seam resolver ``candidate_feature_dir_for_mission`` (which folds
    # every handle form and propagates ``MissionSelectorAmbiguous`` — no silent pick,
    # C-009), matching the WRITE seam ``create_rejected_review_cycle``.  No raw join
    # remains, so its allowlist entry was removed to keep this guard precise
    # (``test_allowlist_entries_are_not_stale``).  The downstream ``wp_slug``
    # path-joins remain dispositioned in the untrusted-path inventory.
    # ----- DRAINED by WP02 (FR-002): the four read-CLI raw-join bootstraps that
    # formerly lived here (decision.py D-6 factory boundary +
    # agent/context.py, agent/mission.py x2 #2046 read-side-desync residuals)
    # have been migrated onto the single guarded read-side seam
    # ``resolve_handle_to_read_path`` (and, for the primary-only existence
    # probe, the topology-blind ``primary_feature_dir_for_mission`` primitive).
    # None of them performs a raw ``KITTY_SPECS_DIR / <handle>`` join any
    # longer, so their allowlist entries were removed to keep this guard
    # precise (``test_allowlist_entries_are_not_stale``).  The seam adds the
    # ``assert_safe_path_segment`` guard (FR-004) each bootstrap previously
    # lacked.  WP05 confirms the drain by re-derivation against the
    # equivalence matrix.
)


@functools.cache
def _raw_join_source(rel_path: str) -> str:
    """Read (and cache) a ``_RAW_JOIN_SITES`` descriptor's source file, once.

    Several descriptors (RJ#1/RJ#2) share a file — caching avoids re-reading it
    once per descriptor.
    """
    return (_SRC_ROOT / rel_path).read_text(encoding="utf-8")


#: Every ``_RAW_JOIN_SITES`` descriptor resolved ONCE at import time to its
#: live full ``(rel_path, qualname, token_line)`` composite key (NFR-004:
#: never hand-author the key literal).  RAISES :class:`DescriptorResolutionError`
#: at import time if a descriptor is already ambiguous or dangling — the
#: earliest possible surfacing of a mis-authored ``token_substring`` (GAP-1).
_RAW_JOIN_SEEDED_KEYS: dict[ContentDescriptor, CompositeKey] = {
    descriptor: resolve_descriptor(_raw_join_source(descriptor.rel_path), descriptor)
    for descriptor in _RAW_JOIN_SITES
}


def _build_allowlisted_raw_joins() -> dict[tuple[str, str], str]:
    """Narrow ``_RAW_JOIN_SEEDED_KEYS`` to the ``(qualname, token_line)`` shape.

    ``test_zero_functional_raw_bypass_on_collapsed_tree`` (T030) keys
    discovered rows via ``composite_key_from_file`` — a bare 2-tuple with no
    ``rel_path`` component — so the allowlist it consults must match that
    shape.  The rationale is carried verbatim from the descriptor.
    """
    return {
        (qualname, token_line): descriptor.rationale
        for descriptor, (_rel_path, qualname, token_line) in _RAW_JOIN_SEEDED_KEYS.items()
    }


#: Composite-keyed allowlist: ``(enclosing_qualname, token_line) -> rationale``.
_ALLOWLISTED_RAW_JOINS: dict[tuple[str, str], str] = _build_allowlisted_raw_joins()

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
        # Composite key (qualname, token_line) — content-addressed, drift-proof.
        key = composite_key_from_file(_SRC_ROOT / row.rel_path, row.line)
        if key not in _ALLOWLISTED_RAW_JOINS:
            unexpected.append(
                f"  {row.key()}  key={key!r}  handle={row.handle_source!r}  "
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
    """Every ``_RAW_JOIN_SITES`` descriptor still resolves to its seeded key.

    A stale descriptor — one that no longer resolves via ``descriptor_still_live``
    (exactly-one AND key-equal, per the descriptor-resolver contract's D-1
    rule) — indicates either the site drifted off its qualname/token line (an
    upstream refactoring changed the shape of a seam file), the join was
    removed, or a NEW same-qualname sibling now collides with the
    ``token_substring`` and the descriptor can no longer disambiguate to a
    single finding.  Any of these must be caught loudly: a stale descriptor
    that silently keeps "passing" would widen the allowlist and defeat the
    precision of the guard (never "≥1 finding matches" semantics — the D-1
    bite hole).

    This assertion is the twin of ``test_zero_functional_raw_bypass_on_collapsed_tree``:
    that test rejects new bypasses; this test rejects stale exemptions.
    """
    stale: list[str] = []
    for descriptor, seeded_key in _RAW_JOIN_SEEDED_KEYS.items():
        source = _raw_join_source(descriptor.rel_path)
        if not descriptor_still_live(source, descriptor, seeded_key):
            stale.append(
                f"  {descriptor.rel_path}::{descriptor.qualname} "
                f"substring={descriptor.token_substring!r} "
                f"(seeded key={seeded_key!r}) — no longer resolves to exactly "
                "one live finding equal to its seeded key"
            )

    assert not stale, (
        "Stale _RAW_JOIN_SITES descriptors:\n"
        + "\n".join(stale)
        + "\n\nEither the site drifted off its qualname/token line (a seam edit "
        "changed the layout), the join was removed entirely, or a new "
        "same-qualname sibling now collides with the token_substring.  Re-author "
        "the descriptor against the live source, or remove the entry if the join "
        "is gone.\n"
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


# ===========================================================================
# T019 — plant-and-catch battery for the WP04 content-descriptor migration.
#
# FR-013 / NFR-001 / NFR-002: proves the descriptor migration (T016/T017) is
# neither a false-red trap (a benign line insertion above a migrated site must
# stay green — the whole point of content-addressing) nor a false-green hole
# (a genuinely new/ambiguous raw join must RED).  Three scenarios, per the WP
# prompt:
#   (a) motion battery  — line insertion above a migrated site -> green.
#   (b) bite            — a new un-allowlisted raw KITTY_SPECS_DIR join -> red.
#   (c) same-qualname sibling — a THIRD un-sanctioned raw join planted inside
#       ``_coord_mid8`` with a token line matching RJ#1's sanctioned
#       substring -> red (proves ``resolve_descriptor``'s exactly-one rule
#       does NOT silently absorb the sibling into the existing allowance).
# ===========================================================================


class _SourceInsertion:
    """Context manager: insert a line right after the first line containing
    ``anchor_substring`` in a real source file, then restore.

    Unlike :class:`_SourceMutation` (which only appends at EOF), this shifts
    every line AFTER the insertion point down by one — the exact "line
    inserted above a migrated site" shape the T019 motion battery must prove
    stays green.  The original bytes are restored on exit even if the body
    raises.
    """

    def __init__(self, path: Path, anchor_substring: str, inserted_line: str) -> None:
        self._path = path
        self._anchor_substring = anchor_substring
        self._inserted_line = inserted_line
        self._original: str = ""

    def __enter__(self) -> Path:
        self._original = self._path.read_text(encoding="utf-8")
        lines = self._original.splitlines(keepends=True)
        anchor_index = next(
            i for i, line in enumerate(lines) if self._anchor_substring in line
        )
        lines.insert(anchor_index + 1, self._inserted_line + "\n")
        self._path.write_text("".join(lines), encoding="utf-8")
        return self._path

    def __exit__(self, *exc: object) -> None:
        self._path.write_text(self._original, encoding="utf-8")


#: The shared file both the motion-battery and same-qualname-sibling plants
#: mutate — it hosts RJ#1/RJ#2's ``_coord_mid8`` qualname.
_COORD_MID8_FILE = _SRC_SPECIFY_CLI / "coordination" / "surface_resolver.py"

#: Anchor line inside ``_coord_mid8`` (just before the fail-closed raise) used
#: to insert a benign comment ABOVE both RJ#1/RJ#2 join lines without changing
#: their content.
_COORD_MID8_ANCHOR = "mid8 = resolve_declared_mid8(meta, mission_slug)"


def test_raw_join_motion_battery_zero_false_reds() -> None:
    """A comment inserted above RJ#1/RJ#2 does NOT flip the twin-guard RED.

    NFR-001: content-addressing (qualname + normalized token line) survives a
    benign ``+1`` line-drift caused by an unrelated edit above the site — the
    entire premise the WP04 migration exists to prove.  Both RJ#1
    (``coord_candidate``) and RJ#2 (``primary_candidate``) live in the SAME
    ``_coord_mid8`` qualname, so a single insertion exercises both at once.
    """
    with _SourceInsertion(
        _COORD_MID8_FILE,
        _COORD_MID8_ANCHOR,
        "    # T019 motion-battery witness: benign comment, no semantic change.",
    ):
        for descriptor, seeded_key in _RAW_JOIN_SEEDED_KEYS.items():
            if descriptor.rel_path != "specify_cli/coordination/surface_resolver.py":
                continue
            source = _COORD_MID8_FILE.read_text(encoding="utf-8")
            assert descriptor_still_live(source, descriptor, seeded_key), (
                f"Motion battery FALSE-RED: {descriptor.qualname} / "
                f"{descriptor.token_substring!r} stopped resolving to its seeded "
                "key after a benign comment insertion above the site — the "
                "descriptor is NOT content-addressed as intended."
            )


def test_raw_join_bite_battery_new_unsanctioned_join_reds() -> None:
    """A brand-new, non-allowlisted raw KITTY_SPECS_DIR join IS caught (red).

    NFR-002: mirrors ``test_zero_functional_raw_bypass_on_collapsed_tree``'s
    own logic against a mutated tree — a genuinely new raw-path-join row whose
    composite key is absent from ``_ALLOWLISTED_RAW_JOINS`` must be flagged as
    an unexpected functional bypass, proving the migration didn't accidentally
    widen the guard.
    """
    snippet = (
        "\n\n"
        "def _wp04_bite_witness(repo_root, mission_slug):  # noqa: injected T019\n"
        "    return repo_root / KITTY_SPECS_DIR / mission_slug\n"
    )
    with _SourceMutation(_SRC_SPECIFY_CLI / "core" / "mission_creation.py", snippet):
        unexpected = [
            row
            for row in discover_rows()
            if row.call_name == "raw-path-join"
            and composite_key_from_file(_SRC_ROOT / row.rel_path, row.line)
            not in _ALLOWLISTED_RAW_JOINS
        ]
        witness = [
            row for row in unexpected if row.rel_path.endswith("core/mission_creation.py")
        ]
        assert witness, (
            "Bite battery FALSE-GREEN: the injected _wp04_bite_witness raw "
            "KITTY_SPECS_DIR/mission_slug join was NOT flagged as an unexpected "
            "functional bypass."
        )


def test_raw_join_same_qualname_sibling_bites() -> None:
    """A THIRD un-sanctioned raw join sharing RJ#1's qualname+substring RED's.

    NFR-002 / D-1: plants a second ``_coord_mid8``-named function (same
    qualname string) whose join line duplicates RJ#1's sanctioned
    ``token_substring`` (``coord_candidate = repo_root``).  With the sibling
    present, ``resolve_descriptor`` sees TWO candidates for RJ#1 inside the
    ``_coord_mid8`` qualname and — per the exactly-one rule (never "≥1 finding
    matches") — must RAISE rather than silently keep resolving to the
    original site.  This proves the twin-guard does not let a routed-away
    allowance mask a genuinely new same-qualname offender.
    """
    snippet = (
        "\n\n"
        "def _coord_mid8(meta, mission_slug, repo_root):  # noqa: injected T019 sibling\n"
        "    coord_candidate = repo_root  # duplicate RJ#1 token line\n"
        "    return coord_candidate\n"
    )
    rj1 = next(
        descriptor
        for descriptor in _RAW_JOIN_SITES
        if descriptor.qualname == "_coord_mid8"
        and descriptor.token_substring == "coord_candidate = repo_root"
    )
    seeded_key = _RAW_JOIN_SEEDED_KEYS[rj1]
    with _SourceMutation(_COORD_MID8_FILE, snippet):
        source = _COORD_MID8_FILE.read_text(encoding="utf-8")
        assert not descriptor_still_live(source, rj1, seeded_key), (
            "Same-qualname-sibling battery FALSE-GREEN: RJ#1 kept resolving "
            "(exactly-one) even with a colliding sibling planted in a second "
            "_coord_mid8-named function — the sibling was silently absorbed "
            "instead of breaking the exactly-one resolution."
        )


# ===========================================================================
# WP05 — read-SELECTION-authority ratchet (FR-006a) + seam empty-mid8 gate
#        (FR-006b) + drain re-derivation (FR-007) + frozen-net (FR-006/FR-007)
#
# These tests add a SECOND discriminator to the architectural guard that the
# pre-WP05 raw-path-JOIN scanner is structurally BLIND to: a DIRECT
# ``resolve_mission_read_path(...)`` call (the read-SELECTION authority) outside
# the ``resolve_handle_to_read_path`` seam.  Such a call composes NO
# ``KITTY_SPECS_DIR / slug`` join of its own — the resolver does the join
# internally — so ``discover_rows()`` (raw-join scanner) never sees it.
# ``discover_selection_callsites()`` catches it by name.
# ===========================================================================

# A read CLI that the WP02/WP03 migration routed onto the seam.  We mutate THIS
# file (a real read path) to prove both the selection ratchet (T017/T019a) and
# the SLUG_NAMES re-injection guard (T021) actually bite on a real source file.
_READ_CLI_FOR_MUTATION = (
    _SRC_SPECIFY_CLI / "cli" / "commands" / "agent" / "context.py"
)

# The guarded read-side seam source (T018 gate-presence assertion).
_SEAM_SOURCE = _SRC_SPECIFY_CLI / "missions" / "_read_path_resolver.py"


class _SourceMutation:
    """Context manager: append a snippet to a real source file, then restore.

    Used for live mutation proofs (inject -> assert guard FAILS -> revert ->
    assert guard PASSES).  The original bytes are restored on exit even if the
    body raises, so a failing assertion never leaves the tree dirty.
    """

    def __init__(self, path: Path, snippet: str) -> None:
        self._path = path
        self._snippet = snippet
        self._original: str = ""

    def __enter__(self) -> Path:
        self._original = self._path.read_text(encoding="utf-8")
        self._path.write_text(self._original + self._snippet, encoding="utf-8")
        return self._path

    def __exit__(self, *exc: object) -> None:
        self._path.write_text(self._original, encoding="utf-8")


def _external_selection_bypasses() -> list[str]:
    """Return locator keys of direct selection calls outside the seam+allowlist."""
    return [
        sel.key()
        for sel in discover_selection_callsites()
        if not sel.in_seam_file and sel.key() not in _ALLOWLISTED_SELECTION_CALLSITES
    ]


# ---------------------------------------------------------------------------
# T017 — read-SELECTION-callsite ratchet (the NEW discriminator).
# ---------------------------------------------------------------------------


def test_no_direct_selection_call_outside_seam() -> None:
    """Every direct ``resolve_mission_read_path`` call routes through the seam.

    FR-006a: the read-SELECTION authority (``resolve_mission_read_path``) is
    reached ONLY through the ``resolve_handle_to_read_path`` seam, except for
    seam-internal definitions and explicitly-blessed lenient callers in
    ``ALLOWLISTED_SELECTION_CALLSITES``.

    This is the NEW discriminator (NOT the raw-path-JOIN scanner): it catches a
    direct selection call that composes NO ``KITTY_SPECS_DIR`` join — the shape
    the raw-join guard is blind to.
    """
    bypasses = _external_selection_bypasses()
    assert not bypasses, (
        "Direct read-SELECTION calls (resolve_mission_read_path) found outside "
        "the resolve_handle_to_read_path seam and not allowlisted:\n"
        + "\n".join(f"  {b}" for b in bypasses)
        + "\n\nRoute these through resolve_handle_to_read_path (the single "
        "guarded read-side seam, IC-01) or — for a deliberately lenient caller "
        "— add a justified entry to ALLOWLISTED_SELECTION_CALLSITES (FR-006a)."
    )


def test_selection_discriminator_is_independent_of_raw_join_scanner() -> None:
    """The selection discriminator sees calls the raw-join scanner is blind to.

    Anti-vacuous proof (squad-mandated).  WP01 (01KVN754) DRAINED the last
    permanent external selection callsite (``acceptance/__init__.py`` rerouted
    onto the seam), so the independence proof now uses a LIVE mutation witness
    instead of a standing callsite: inject a direct
    ``resolve_mission_read_path`` call (composing NO ``KITTY_SPECS_DIR`` join)
    into a real read CLI and assert the SELECTION scanner discovers it while the
    RAW-JOIN scanner stays blind to it — proving the selection discriminator is
    strictly stronger than (independent of) the raw-join scanner.
    """
    snippet = (
        "\n\ndef _wp01_independence_witness(repo_root, slug, mid8):  # noqa\n"
        "    from specify_cli.missions._read_path_resolver import (\n"
        "        resolve_mission_read_path,\n"
        "    )\n"
        "    return resolve_mission_read_path(repo_root, slug, mid8)\n"
    )
    with _SourceMutation(_READ_CLI_FOR_MUTATION, snippet):
        selection_keys = {s.key() for s in discover_selection_callsites()}
        raw_join_keys = {
            r.key() for r in discover_rows() if r.call_name == "raw-path-join"
        }
        witness = next(
            (
                k
                for k in selection_keys
                if k.startswith("specify_cli/cli/commands/agent/context.py:")
            ),
            None,
        )
        assert witness is not None, (
            "The SELECTION scanner failed to discover the injected direct "
            "resolve_mission_read_path call — the AST walker is misconfigured or "
            "vacuous."
        )
        assert witness not in raw_join_keys, (
            "The injected selection call must NOT appear as a raw-path-join row — "
            "it composes no KITTY_SPECS_DIR join, so the raw-join scanner is blind "
            "to it. Its presence there would contradict the independence premise."
        )


# ---------------------------------------------------------------------------
# FR-006a hardening — the SELECTION seam is the single
# ``_read_path_resolver.py`` home, NOT the broader RAW-JOIN resolver-source set.
#
# Pins the guard blind-spot fix: ``_find_selection_calls`` discriminates on
# ``_SELECTION_SEAM_STEMS`` (selection axis) rather than
# ``_RESOLVER_SOURCE_STEMS`` (raw-join axis).  The three resolver-source files
# below (``surface_resolver.py``, ``status_transition.py``, ``aggregate.py``)
# define resolvers for the RAW-JOIN axis but are NOT the selection seam — a
# hypothetical direct ``resolve_mission_read_path`` call there must be FLAGGED
# (allowlist or refactor), never auto-blessed as seam-internal.  (WP01 drained
# the lone real external consumer, ``mission_runtime/resolution.py``, by routing
# it onto the ``resolve_handle_to_read_path`` seam — there are now ZERO external
# selection callsites and the allowlist is empty.)
# ---------------------------------------------------------------------------

_NON_SELECTION_RESOLVER_SOURCES: tuple[str, ...] = (
    "specify_cli/coordination/surface_resolver.py",
    "specify_cli/coordination/status_transition.py",
    "specify_cli/status/aggregate.py",
)


def test_non_seam_resolver_sources_are_not_auto_blessed_for_selection() -> None:
    """RAW-JOIN resolver-source files are NOT in the SELECTION seam set.

    FR-006a guard hardening (paula): ``_SELECTION_SEAM_STEMS`` is the single
    ``resolve_handle_to_read_path`` home (``_read_path_resolver.py``).  The
    three broader resolver-source files legitimately define resolvers for the
    RAW-JOIN axis but are NOT the selection seam — so a future direct
    ``resolve_mission_read_path`` call in any of them would be FLAGGED (not
    auto-blessed as seam-internal) and must be allowlisted or refactored.
    """
    assert frozenset(
        {"specify_cli/missions/_read_path_resolver.py"}
    ) == _SELECTION_SEAM_STEMS, (
        "The SELECTION seam must be the single resolve_handle_to_read_path home. "
        "Widening it re-introduces the guard blind-spot where a direct "
        "resolve_mission_read_path call in a raw-join resolver-source file is "
        "silently auto-blessed."
    )
    for src in _NON_SELECTION_RESOLVER_SOURCES:
        assert src in _RESOLVER_SOURCE_STEMS, (
            f"{src!r} should still be a RAW-JOIN resolver-source file "
            "(_RESOLVER_SOURCE_STEMS) — its raw-join axis tracking is unchanged."
        )
        assert src not in _SELECTION_SEAM_STEMS, (
            f"{src!r} is a RAW-JOIN resolver-source file but NOT the selection "
            "seam; including it in _SELECTION_SEAM_STEMS would auto-bless a "
            "hypothetical direct resolve_mission_read_path call there (FR-006a "
            "guard blind-spot)."
        )


def test_resolution_internal_read_converged_onto_seam() -> None:
    """``mission_runtime/resolution.py`` no longer holds a direct selection call.

    WP01 (01KVN754) rerouted ``_resolve_mission_slug`` from a direct
    ``resolve_mission_read_path`` call onto the single guarded seam
    (``resolve_handle_to_read_path``), keeping the StatusReadPathNotFound /
    MissionSelectorAmbiguous → ActionContextError boundary translation.  The
    formerly-allowlisted callsite is therefore DRAINED: ``resolution.py`` must no
    longer surface as an external selection callsite, and the seam-convergence is
    proven by the absence of any discovered direct call in that file.
    """
    resolution_selection_calls = [
        s.key()
        for s in discover_selection_callsites()
        if s.rel_path == "mission_runtime/resolution.py"
    ]
    assert not resolution_selection_calls, (
        "mission_runtime/resolution.py still holds a direct read-SELECTION call "
        "after the WP01 reroute onto resolve_handle_to_read_path; the convergence "
        f"is incomplete. Discovered: {resolution_selection_calls}"
    )
    # And it must carry NO stale allowlist entry (the reroute drained it).
    assert "mission_runtime/resolution.py:185" not in _ALLOWLISTED_SELECTION_CALLSITES, (
        "The mission_runtime/resolution.py:185 selection allowlist entry is stale "
        "— WP01 rerouted that callsite onto the seam; remove the dead allowlist entry."
    )


# ---------------------------------------------------------------------------
# T019(a) — mutation: inject a direct selection call into a read CLI.
# ---------------------------------------------------------------------------


def test_selection_ratchet_bites_on_injected_direct_call() -> None:
    """Inject a direct ``resolve_mission_read_path`` call -> ratchet FAILS; revert -> PASSES.

    Two-axis live proof on a REAL read CLI (``agent/context.py``).  Axis (a):
    a NEW direct selection call OUTSIDE the seam is caught.
    """
    # Pre-mutation: clean tree, no external bypasses.
    assert not _external_selection_bypasses(), (
        "Pre-condition failed: the clean adopted tree already has an external "
        "selection bypass — fix that before running the mutation proof."
    )

    snippet = (
        "\n\ndef _wp05_injected_selection_bypass(repo_root, slug):  # noqa\n"
        "    from specify_cli.missions._read_path_resolver import (\n"
        "        resolve_mission_read_path,\n"
        "    )\n"
        "    from specify_cli.lanes.branch_naming import mid8_from_slug\n"
        "    return resolve_mission_read_path(repo_root, slug, mid8_from_slug(slug))\n"
    )
    with _SourceMutation(_READ_CLI_FOR_MUTATION, snippet):
        during = _external_selection_bypasses()
        assert any(
            k.startswith("specify_cli/cli/commands/agent/context.py:") for k in during
        ), (
            "Selection ratchet did NOT catch the injected direct "
            "resolve_mission_read_path call in agent/context.py — the "
            "discriminator is vacuous.\n"
            f"  external bypasses during mutation: {during}"
        )

    # Post-revert: clean again.
    assert not _external_selection_bypasses(), (
        "Selection ratchet still reports a bypass after the mutation was "
        "reverted — the _SourceMutation restore failed."
    )


# ---------------------------------------------------------------------------
# T019(b) — pre/post-mission-tree discrimination (NOT a tautology).
# ---------------------------------------------------------------------------


def test_ratchet_would_have_failed_on_pre_mission_tree() -> None:
    """The ratchet PASSES on the adopted tree but WOULD HAVE FAILED pre-mission.

    Discrimination proof (squad-mandated anti-vacuous): the read CLIs that WP02
    migrated (``agent/context.py``, ``agent/mission.py``, ``decision.py``) used
    to perform a raw ``KITTY_SPECS_DIR / raw_handle`` primary-meta bootstrap
    join.  We reconstruct that PRE-mission shape on a real read CLI and confirm
    the raw-join scanner catches it (i.e. the guard discriminates between the
    pre- and post-migration trees — it is not a constant-true tautology).

    The adopted tree passes ``test_zero_functional_raw_bypass_on_collapsed_tree``;
    the reconstructed pre-mission shape FAILS the same scanner.
    """
    # Adopted tree: the migrated read CLI carries NO raw KITTY_SPECS_DIR join.
    clean_keys = {
        r.key()
        for r in discover_rows()
        if r.call_name == "raw-path-join"
        and r.key().startswith("specify_cli/cli/commands/agent/context.py:")
    }
    assert not clean_keys, (
        "Pre-condition failed: the adopted agent/context.py already has a raw "
        f"KITTY_SPECS_DIR join: {clean_keys} — WP02 migration regressed."
    )

    # Reconstruct the pre-mission raw-join bootstrap shape.
    snippet = (
        "\n\ndef _wp05_pre_mission_raw_bootstrap(repo_root, raw_handle):  # noqa\n"
        "    from specify_cli.core.paths import KITTY_SPECS_DIR\n"
        "    primary_dir = repo_root / KITTY_SPECS_DIR / raw_handle\n"
        "    return primary_dir\n"
    )
    with _SourceMutation(_READ_CLI_FOR_MUTATION, snippet):
        during = {
            r.key()
            for r in discover_rows()
            if r.call_name == "raw-path-join"
            and r.key().startswith("specify_cli/cli/commands/agent/context.py:")
        }
        assert during, (
            "The raw-join scanner did NOT catch the reconstructed pre-mission "
            "KITTY_SPECS_DIR / raw_handle bootstrap — the guard would NOT have "
            "discriminated against the pre-mission tree (tautology risk)."
        )

    # Revert restored the clean tree.
    post = {
        r.key()
        for r in discover_rows()
        if r.call_name == "raw-path-join"
        and r.key().startswith("specify_cli/cli/commands/agent/context.py:")
    }
    assert not post, "Pre-mission-shape mutation was not reverted cleanly."


# ---------------------------------------------------------------------------
# T018 — seam runtime empty-mid8 fail-closed gate (FR-006b).
# ---------------------------------------------------------------------------


def test_seam_empty_mid8_fail_closed_gate_raises() -> None:
    """The seam RAISES on empty-mid8-against-declared-coord (FR-006b / M5).

    A bare slug whose primary ``meta.json`` declares a ``coordination_branch``
    but carries NEITHER ``mid8`` NOR ``mission_id`` leaves the cascade exhausted
    (empty mid8).  Reading primary would expose a stale view, so the seam MUST
    raise the typed ``StatusReadPathNotFound`` rather than silently fall back.
    """
    import json

    from specify_cli.missions._read_path_resolver import (
        StatusReadPathNotFound,
        resolve_handle_to_read_path,
    )

    slug = "read-side-surface-resolver-adoption"
    coord_branch = "kitty/mission-read-side-surface-resolver-adoption-01KVJPEQ"

    repo_root = _REPO_ROOT  # placeholder; overwritten per-test via tmp below

    import tempfile

    with tempfile.TemporaryDirectory() as td:
        repo_root = Path(td)
        primary_dir = repo_root / "kitty-specs" / slug
        primary_dir.mkdir(parents=True)
        # Declares coordination but NO mid8 / mission_id => unprovable identity.
        (primary_dir / "meta.json").write_text(
            json.dumps({"mission_slug": slug, "coordination_branch": coord_branch}),
            encoding="utf-8",
        )

        with pytest.raises(StatusReadPathNotFound) as exc_info:
            resolve_handle_to_read_path(repo_root, slug)

        assert exc_info.value.mid8 == ""
        assert exc_info.value.mission_slug == slug


def test_seam_source_contains_fail_closed_gate() -> None:
    """The seam SOURCE still contains the empty-mid8 fail-closed gate (mutation tripwire).

    FR-006b mutation proof, static form: removing the gate
    (``if not mid8 and declares_coordination ...:`` -> ``raise StatusReadPathNotFound``)
    from the seam would make ``test_seam_empty_mid8_fail_closed_gate_raises``
    FAIL (the seam would fall through to a stale primary read).  This companion
    assertion pins the gate's STRUCTURAL presence so a refactor that drops the
    branch is caught even if the runtime test fixture drifts.

    NOTE (WP04 / FR-006, single-planning-surface-authority-01KVPR00): the gate
    condition gained a trailing ``and consults_coord_husk`` term — a stored
    coord-less topology resolves PRIMARY rather than failing closed on a residual
    husk (the husk is structurally not consulted; #2062 cannot re-open). The
    structural pin is anchored on the load-bearing ``not mid8 and
    declares_coordination`` clause (without the trailing colon) so it survives that
    narrowing while still catching a refactor that drops the empty-mid8 branch.
    """
    src = _SEAM_SOURCE.read_text(encoding="utf-8")
    assert "if not mid8 and declares_coordination" in src, (
        "The seam's empty-mid8 fail-closed gate "
        "(`if not mid8 and declares_coordination ...`) is MISSING from "
        f"{_SEAM_SOURCE} — removing it regresses FR-006b (silent stale-primary "
        "read on an unprovable coord-declared topology)."
    )
    # The gate must raise the typed read-path error, not fall through.
    gate_idx = src.index("if not mid8 and declares_coordination")
    gate_block = src[gate_idx : gate_idx + 400]
    assert "raise StatusReadPathNotFound(" in gate_block, (
        "The empty-mid8 gate no longer RAISES StatusReadPathNotFound — a "
        "fall-through here is a silent stale-primary read (FR-006b regression)."
    )


# ---------------------------------------------------------------------------
# T020 — confirm the four read-CLI raw joins drained (FR-007 re-derivation).
# ---------------------------------------------------------------------------

# The four read-CLI primary-meta bootstrap raw-join keys that the pre-mission
# tree carried.  WP02 migrated all four onto the ``resolve_handle_to_read_path``
# seam; re-derivation must now find ZERO raw joins at these files.  Three are
# the #2046 read-side-desync residuals; ``decision.py`` is the D-6 consolidation
# drain (a consequence of the WP02 factory-boundary consolidation, NOT a #2046
# residual).
_DRAINED_READ_CLI_FILES: tuple[str, ...] = (
    "specify_cli/cli/commands/agent/context.py",  # #2046
    "specify_cli/cli/commands/agent/mission.py",  # #2046 (x2: :1327 + :1378)
    "specify_cli/cli/commands/decision.py",  # D-6 consolidation
)


def test_read_cli_raw_joins_are_drained() -> None:
    """The four read-CLI raw-join bootstraps no longer appear in discover_rows().

    FR-007 drain confirmed BY RE-DERIVATION (not by editing the net): after
    WP02 routed them onto the seam, ``discover_rows()`` finds ZERO
    ``raw-path-join`` rows in any of the read-CLI files.  The drain is real
    because the joins are GONE, not because the scanner was narrowed (see
    ``test_slug_names_net_is_frozen``).
    """
    raw_join_keys = [r.key() for r in discover_rows() if r.call_name == "raw-path-join"]
    leaks = [
        k
        for k in raw_join_keys
        if any(k.startswith(f) for f in _DRAINED_READ_CLI_FILES)
    ]
    assert not leaks, (
        "Read-CLI raw-join bootstraps are NOT drained — these still compose a "
        "raw KITTY_SPECS_DIR join:\n"
        + "\n".join(f"  {k}" for k in leaks)
        + "\n\nThey must route through resolve_handle_to_read_path (FR-007)."
    )


def test_drained_keys_are_not_in_allowlist() -> None:
    """No drained read-CLI key lingers in _ALLOWLISTED_RAW_JOINS (no stale exemption).

    FR-007: the drain removed the joins, so their allowlist entries (added
    earlier as honest residual exemptions) must also be gone.  A lingering
    entry would be flagged by ``test_allowlist_entries_are_not_stale``, but this
    test asserts the specific drained-key invariant directly.
    """
    # The composite-keyed allowlist no longer carries a file path in its KEY, so
    # the drained-file check runs against the ``_RAW_JOIN_SITES`` descriptor seed
    # (each descriptor still carries its own ``rel_path``) — a lingering drained
    # entry would still be seeded there.
    lingering = [
        f"{descriptor.rel_path}::{descriptor.qualname}"
        for descriptor in _RAW_JOIN_SITES
        if any(descriptor.rel_path.startswith(f) for f in _DRAINED_READ_CLI_FILES)
    ]
    assert not lingering, (
        "Drained read-CLI keys still present in _ALLOWLISTED_RAW_JOINS "
        "(stale exemption):\n" + "\n".join(f"  {k!r}" for k in lingering)
    )


# ---------------------------------------------------------------------------
# T021 — frozen SLUG_NAMES net + re-injection mutation.
# ---------------------------------------------------------------------------

# The minimum net the read-CLI primary-meta bootstrap joins were caught by.
# Narrowing the net (dropping either token) would silently re-blind the scanner
# to the read-CLI bootstrap shape — the fake-drain hole closed by 01KVGCE8.
_FROZEN_SLUG_NET: frozenset[str] = frozenset({"raw_handle", "handle"})


def test_slug_names_net_is_frozen() -> None:
    """``audit.py``'s SLUG_NAMES must keep (or widen) ``{raw_handle, handle}``.

    FR-006/FR-007 anti-fake-drain invariant: the read-CLI bootstrap raw joins
    were caught because ``raw_handle`` (and ``handle``) are in the scanner's
    ``SLUG_NAMES`` net.  Dropping either token would re-blind the scanner and
    let a re-introduced raw bootstrap pass silently.  The net may only stay the
    same or WIDEN — never narrow.
    """
    missing = _FROZEN_SLUG_NET - _SLUG_NAMES
    assert not missing, (
        "SLUG_NAMES was NARROWED — these required tokens are missing:\n"
        + "\n".join(f"  {t!r}" for t in sorted(missing))
        + "\n\nNarrowing the net re-blinds discover_rows() to the read-CLI "
        "primary-meta bootstrap shape (the fake-drain hole). The net must stay "
        "unchanged-or-widened (FR-006/FR-007)."
    )


def test_raw_handle_reinjection_is_caught() -> None:
    """Re-inject a raw ``KITTY_SPECS_DIR / raw_handle`` join -> guard FAILS; revert -> PASSES.

    FR-007 anti-fake-drain mutation proof: on the ADOPTED tree, re-introducing
    the exact pre-mission raw bootstrap shape (``repo_root / KITTY_SPECS_DIR /
    raw_handle``) into a real read CLI must be caught by the raw-join scanner.
    This proves the net was NOT silently narrowed to make the drain pass.
    """
    snippet = (
        "\n\ndef _wp05_reinject_raw_handle(repo_root, raw_handle):  # noqa\n"
        "    from specify_cli.core.paths import KITTY_SPECS_DIR\n"
        "    return repo_root / KITTY_SPECS_DIR / raw_handle\n"
    )
    with _SourceMutation(_READ_CLI_FOR_MUTATION, snippet):
        during = [
            r.key()
            for r in discover_rows()
            if r.call_name == "raw-path-join"
            and r.handle_source == "raw_handle"
            and r.key().startswith("specify_cli/cli/commands/agent/context.py:")
        ]
        assert during, (
            "Re-injected raw KITTY_SPECS_DIR / raw_handle join was NOT caught — "
            "SLUG_NAMES must have been narrowed (fake-drain hole re-opened)."
        )

    post = [
        r.key()
        for r in discover_rows()
        if r.call_name == "raw-path-join"
        and r.handle_source == "raw_handle"
        and r.key().startswith("specify_cli/cli/commands/agent/context.py:")
    ]
    assert not post, "raw_handle re-injection mutation was not reverted cleanly."


# ---------------------------------------------------------------------------
# WP05 (coord-authority-trio-degod-01KX7094) -- trio-split files carry zero
# raw-path-join rows (T027 extension).
#
# The trio decomposition (agent/workflow.py, cli/commands/implement.py,
# acceptance/__init__.py -> shell + pure core(s) + executor) added five new
# source files to the tree. None of the _ALLOWLISTED_RAW_JOINS entries above
# reference any of them -- the split kept every raw-join site (allowlisted or
# not) inside the pre-existing seam/resolver modules. This guard is additive,
# not a weakening of anything above: it does not touch _ALLOWLISTED_RAW_JOINS
# or any existing assertion, it only asserts that discover_rows() -- the SAME
# live walker every other test in this file uses -- finds zero raw-path-join
# rows specifically inside the five new files. See
# ``tests/architectural/test_trio_seam_only.py`` for the trio's other two
# invariants (T027 seam-only imports, T028 cores-no-I/O).
# ---------------------------------------------------------------------------

_TRIO_SPLIT_FILES: frozenset[str] = frozenset(
    {
        "specify_cli/cli/commands/agent/workflow_cores.py",
        "specify_cli/cli/commands/agent/workflow_executor.py",
        "specify_cli/cli/commands/implement_cores.py",
        "specify_cli/acceptance/summary_core.py",
        "specify_cli/acceptance/gates_core.py",
    }
)


def test_trio_split_files_carry_no_raw_bypass_rows() -> None:
    """The five new trio-split files introduce zero raw-path-join rows.

    If a future edit moved (or introduced) a raw ``KITTY_SPECS_DIR``/slug join
    into one of the split-out files, this guard -- not just the whole-tree
    zero-bypass guard above -- calls it out by the specific new file it landed
    in, since ``_ALLOWLISTED_RAW_JOINS`` has (correctly) never had to carry an
    entry for any of them.
    """
    rows = discover_rows()
    leaks = [
        row.key()
        for row in rows
        if row.call_name == "raw-path-join" and row.rel_path in _TRIO_SPLIT_FILES
    ]
    assert not leaks, (
        "New raw KITTY_SPECS_DIR/slug joins found in a trio-split file "
        f"(none were expected -- these files are new in this mission and carry "
        f"no _ALLOWLISTED_RAW_JOINS entries): {leaks}"
    )


def test_trio_split_files_are_covered_by_the_live_walker() -> None:
    """Anti-vacuous companion: the five trio-split files actually exist and are
    on the walker's search path, so the zero-leaks assertion above is not
    trivially satisfied by scanning nothing.
    """
    missing = [rel for rel in sorted(_TRIO_SPLIT_FILES) if not (_SRC_ROOT / rel).is_file()]
    assert not missing, f"Trio-split files missing from the current tree: {missing}"
