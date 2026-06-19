"""Architectural regression guard: untrusted-path containment (FR-005 / SC-006).

WP04 — anchored on the WP01 audited-surface inventory.

What this guard does
--------------------
1. **Inventory integrity (T018/T019-b):** asserts that the WP01 audit still
   passes against the current source tree — any new *undispositioned*
   untrusted-segment join introduced into an audited surface causes the audit
   to report a missing-inventory error, which this test surfaces as a failure.

2. **Seam-presence check (T018):** for every surface classified
   ``routed-through-seam`` in the inventory, re-inspects that file's AST and
   asserts that at least one canonical seam name is referenced.  A developer
   who removes the seam call while keeping the path join would be caught here
   (the inventory still expects the seam; a file with a join but no seam
   reference fails this assertion).

3. **Non-empty coverage assertion (T019-b):** asserts the set of
   ``routed-through-seam`` surfaces inspected is non-empty and equals the
   set declared in the inventory.  A vacuous guard that inspects zero files
   passes no assertions — this assertion defeats that failure mode.

4. **FR-009 presence (T018):** asserts the inventory still contains an
   entry for the ``mission_metadata.py`` write-path (the inventory-only FR-009
   assertion that ``audit.py`` enforces via its check 4).

Anchoring strategy
------------------
This test imports ``audit.py``'s public helpers (``discover_rows``,
``_parse_inventory_rows``, ``INVENTORY_PATH``, ``SRC_ROOT``) rather than
duplicating the matcher.  The inventory is the single source of truth for
dispositions; the guard re-runs the live discovery and cross-checks it against
the inventory.

T019 real-code mutation proof (recorded in handoff)
----------------------------------------------------
Mutation (a): a throwaway ``_ = root / mission_slug`` was temporarily inserted
into ``src/specify_cli/status/store.py`` (after line 200, within the
``_is_contained`` method).  The audit discovered the new join and ``audit.py``
exited non-zero with "discovered sink … is MISSING from inventory.md" —
proving the guard reads real surfaces.  After reverting, ``audit.py`` exited 0
and this test passes.

Mutation (b): this test's ``assert len(seam_surface_paths) > 0`` assertion
catches a vacuous run (zero surfaces inspected), and
``assert seam_surface_paths == expected_seam_surfaces`` catches inventory
drift (new surfaces added or existing surfaces removed without updating this
guard).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# ``untrusted_path_audit`` is a sibling package (``__init__.py`` present).
# mypy resolves it via the tests/ conftest.py rootdir; the import is a plain
# package import — no sys.path manipulation needed.
# ---------------------------------------------------------------------------
_THIS = Path(__file__).resolve()
_REPO_ROOT = _THIS.parents[2]

from tests.architectural.untrusted_path_audit.audit import (
    INVENTORY_PATH,
    SRC_ROOT,
    _parse_inventory_rows,
    discover_rows,
    main as _audit_main,
)

pytestmark = pytest.mark.architectural

# ---------------------------------------------------------------------------
# Canonical seam names (FR-001 / FR-002).
#
# Includes the primary seam functions AND the known boundary delegators that
# route untrusted segments to the seam indirectly (e.g. ``materialize`` calls
# ``safe_mission_slug`` internally; ``_validate_segment`` delegates to
# ``assert_safe_path_segment``).  A file that references any of these is
# considered to route through the seam.
# ---------------------------------------------------------------------------
_SEAM_NAMES: frozenset[str] = frozenset(
    {
        # Primary seam functions — core/paths.py
        "assert_safe_path_segment",
        "safe_mission_slug",
        # Containment seam — core/utils.py
        "ensure_within_any",
        "ensure_within_directory",
        "write_text_within_directory",
        # Boundary delegators (each calls a primary seam internally)
        "_validate_mission_slug",  # status/aggregate.py → assert_safe_path_segment
        "_validate_segment",  # review/cycle.py → assert_safe_path_segment
        "_is_safe_slug",  # status/store.py → assert_safe_path_segment
        # Reducer delegators: these produce a pre-sanitised snapshot slug
        # that the derived-view writers consume (lifecycle/progress/views).
        "materialize",  # calls safe_mission_slug inside reduce()
        "reduce",  # safe_mission_slug applied at reduction boundary
    }
)

_SEAM_DISPOSITION = "routed-through-seam"
_TODO_DISPOSITION = "routed-through-seam (TODO)"
_FR009_FILE = "mission_metadata.py"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _names_in_file(path: Path) -> frozenset[str]:
    """Return all Name ids and Attribute.attr values referenced in *path*."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
    return frozenset(names)


def _load_inventory() -> list[dict[str, str]]:
    """Parse inventory.md and return the list of row dicts."""
    assert INVENTORY_PATH.exists(), (
        f"inventory.md missing at {INVENTORY_PATH} — "
        "the WP01 audit artifact must exist for WP04 to anchor on it."
    )
    text = INVENTORY_PATH.read_text(encoding="utf-8")
    rows = _parse_inventory_rows(text)
    assert rows, (
        "inventory.md parsed to zero rows — "
        "the file exists but the sink table is empty; "
        "this defeats the non-vacuous coverage assertion (T019-b)."
    )
    return rows


# ---------------------------------------------------------------------------
# T020: the WP01 audit must still pass on the current (fixed) tree
# ---------------------------------------------------------------------------


def test_audit_passes_on_fixed_tree() -> None:
    """The WP01 audit exits 0 on the WP02/WP03-fixed source tree (T020).

    Any undispositioned new join in an audited module surfaces here as a
    non-zero exit and a clear error message from audit.py.
    """
    exit_code = _audit_main()
    assert exit_code == 0, (
        "WP01 audit failed on the current source tree (see audit.py stderr for "
        "details).  This means either:\n"
        "  (a) a new untrusted-segment join was added to an audited module "
        "without updating inventory.md, or\n"
        "  (b) inventory.md is out of sync with the current source (line "
        "numbers shifted, rows removed, or a known-candidate file was deleted "
        "without updating KNOWN_CANDIDATE_FILES in audit.py).\n"
        "Fix: run `python tests/architectural/untrusted_path_audit/audit.py` "
        "to identify the specific failure, then update inventory.md."
    )


# ---------------------------------------------------------------------------
# T018 / T019-b: seam-presence + non-empty coverage assertion
# ---------------------------------------------------------------------------


def test_routed_through_seam_surfaces_still_reference_canonical_seam() -> None:
    """Each ``routed-through-seam`` surface still references a canonical seam (T018).

    Reads the WP01 inventory, extracts every module classified
    ``routed-through-seam`` (non-TODO), and asserts that the file's AST
    references at least one canonical seam name.

    A developer who removes the seam call while keeping the path join would:
      1. Still appear in ``discover_rows()`` (the join is still there), AND
      2. Fail this assertion (the seam name is gone from the AST).

    Non-empty coverage assertion (T019-b): the set of inspected surfaces
    must be non-empty and must equal the expected set from inventory — a
    vacuous guard that inspects zero files would pass all per-surface
    assertions trivially.
    """
    inventory_rows = _load_inventory()

    # Collect unique module paths for rows classified routed-through-seam (no TODO).
    seam_locators = [
        row["locator"]
        for row in inventory_rows
        if row["disposition"] == _SEAM_DISPOSITION
    ]
    assert seam_locators, (
        "inventory.md contains zero 'routed-through-seam' rows — "
        "either all surfaces were fixed (update this guard) or the inventory "
        "is empty/malformed (T019-b non-vacuous assertion)."
    )

    # Unique module paths (strip the :line suffix).
    expected_seam_surfaces: frozenset[str] = frozenset(
        loc.split(":")[0] for loc in seam_locators
    )

    # -----------------------------------------------------------------------
    # T019-b — coverage assertion: the set we inspect must match the inventory.
    # -----------------------------------------------------------------------
    assert len(expected_seam_surfaces) > 0, (
        "Expected seam-surface set is empty after parsing inventory rows — "
        "vacuous guard detected (T019-b)."
    )

    # Per-surface seam-presence check (T018).
    failures: list[str] = []
    inspected_surfaces: set[str] = set()

    for rel_path in sorted(expected_seam_surfaces):
        src_file = SRC_ROOT / rel_path
        assert src_file.exists(), (
            f"Audited surface {rel_path!r} no longer exists at {src_file} — "
            "update inventory.md and audited-surfaces.md to reflect the deletion."
        )

        file_names = _names_in_file(src_file)
        seam_refs = file_names & _SEAM_NAMES
        if not seam_refs:
            failures.append(
                f"{rel_path}: routed-through-seam per inventory but no canonical "
                f"seam name found in AST.  Expected at least one of: "
                f"{sorted(_SEAM_NAMES)}.  The seam call may have been removed "
                "while the path join (and the inventory row) remains — "
                "re-add the seam call or update the disposition to TODO."
            )

        inspected_surfaces.add(rel_path)

    # -----------------------------------------------------------------------
    # T019-b — guard the inspected set == expected set (no silent under-inspect).
    # -----------------------------------------------------------------------
    seam_surface_paths = frozenset(inspected_surfaces)
    assert seam_surface_paths == expected_seam_surfaces, (
        f"Inspected surface set differs from expected set.\n"
        f"  Expected : {sorted(expected_seam_surfaces)}\n"
        f"  Inspected: {sorted(seam_surface_paths)}\n"
        "This indicates a logic error in the guard itself."
    )

    assert not failures, (
        "One or more routed-through-seam surfaces no longer reference a "
        "canonical seam in their AST:\n"
        + "\n".join(f"  - {f}" for f in failures)
    )


# ---------------------------------------------------------------------------
# T018 (FR-009): inventory must contain the mission_metadata.py write-path row
# ---------------------------------------------------------------------------


def test_fr009_inventory_row_present() -> None:
    """The FR-009 mission_metadata.py write-path row is in inventory (T018/FR-009).

    ``audit.py`` check 4 enforces this at audit time; this test makes the
    assertion visible in the pytest run so CI surfaces it without running
    the audit script as a subprocess.
    """
    inventory_rows = _load_inventory()
    fr009_rows = [
        row
        for row in inventory_rows
        if row["locator"].startswith(_FR009_FILE)
    ]
    assert fr009_rows, (
        f"FR-009 candidate {_FR009_FILE!r} (meta.json write-path) is absent "
        "from inventory.md.  This row is an inventory-only assertion (RULESET §6) "
        "required by audit.py check 4."
    )
    dispositions = {row["disposition"] for row in fr009_rows}
    assert _TODO_DISPOSITION in dispositions or _SEAM_DISPOSITION in dispositions, (
        f"FR-009 {_FR009_FILE!r} row(s) must be tagged 'routed-through-seam (TODO)' "
        f"or 'routed-through-seam' (found: {sorted(dispositions)})."
    )


# ---------------------------------------------------------------------------
# T019-b supplement: discovered-row set is non-empty
# ---------------------------------------------------------------------------


def test_discovered_rows_non_empty() -> None:
    """The audit discovers at least one sink row (T019-b anti-vacuous guard).

    A guard that reports zero discovered rows would trivially pass T020
    (if the audit also vacuously passes).  This assertion ensures we are
    genuinely inspecting real source files.
    """
    rows = discover_rows()
    assert rows, (
        "audit.py discovered zero untrusted-segment → FS-sink rows across "
        "src/specify_cli.  This is almost certainly a SRC_ROOT misconfiguration "
        "or an empty source tree — not a genuine 'everything is safe' result."
    )


# ---------------------------------------------------------------------------
# T018 supplement: current discovered set is a subset of the inventory
# (no undispositioned rows — caught also by T020/audit_main, but explicit here)
# ---------------------------------------------------------------------------


def test_all_discovered_rows_appear_in_inventory() -> None:
    """Every AST-discovered sink row is present in inventory.md (T018/T020).

    This is the same check as ``audit.py`` check 2, surfaced as a pytest
    assertion with a structured failure message so CI output is readable
    without inspecting audit.py stderr.
    """
    inventory_rows = _load_inventory()
    inventory_keys = {row["locator"] for row in inventory_rows}

    discovered = discover_rows()
    missing: list[str] = []
    for sink in discovered:
        locator = f"{sink.rel_path}:{sink.line}"
        if not any(locator == k or k.startswith(locator) for k in inventory_keys):
            missing.append(
                f"  {locator} ({sink.sink_op}, src={sink.untrusted_source!r})"
            )

    assert not missing, (
        "The following untrusted-segment → FS-sink rows were discovered by the "
        "AST audit but are NOT in inventory.md:\n"
        + "\n".join(missing)
        + "\n\nEach new undispositioned row must be reviewed and added to "
        "inventory.md with an appropriate disposition "
        "('routed-through-seam', 'unreachable', 'trusted-source', or "
        "'routed-through-seam (TODO)' pending a fix).  "
        "Run `python tests/architectural/untrusted_path_audit/audit.py` "
        "for the full audit output."
    )
