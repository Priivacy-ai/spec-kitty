"""Theater triad + public-shape guard for the surface-resolution audit (WP03 / FR-004).

This is the acceptance instrument for the IC-03 re-key: it proves the surface
``audit.py`` now identifies rows by the drift-proof
``(rel_path, enclosing_qualname, token)`` composite instead of the fragile
``rel:line`` locator (the #2306 failure class), for BOTH the ``ResolutionRow``
(sink) table AND the ``SelectionRow`` (read-SELECTION) table.

The theater drives the REAL entry points CI runs — the pure ``check_undercount`` /
``check_overcount`` seams that ``main()`` itself calls, and ``main()`` end-to-end
against a synthetic source tree (monkeypatched module globals). Helper-only
theater (asserting against a function ``main()`` never calls) would be a review
reject; every leg below terminates at the audit's real check path.

The companion frozen guard ``test_single_mission_surface_resolver.py`` stays
UNMODIFIED and green (it consumes the audit's public shape — ``discover_rows``,
``ResolutionRow``/``SelectionRow`` field names, and the ``key() -> str`` locator).
The ``test_public_shape_*`` cases below pin that coupling so a future edit that
changes the importable surface fails loudly here rather than silently reddening
the frozen guard.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

pytestmark = pytest.mark.architectural

_THIS = Path(__file__).resolve()
_REPO_ROOT = _THIS.parents[2]
_AUDIT_PATH = _REPO_ROOT / "tests" / "architectural" / "surface_resolution_audit" / "audit.py"


def _load_audit() -> ModuleType:
    """Load the surface audit as a standalone module (same as the frozen guard)."""
    spec = importlib.util.spec_from_file_location("_surface_audit_theater", _AUDIT_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


audit = _load_audit()


# ===========================================================================
# Public-shape guard — the REAL coupling with the frozen resolver test.
# ===========================================================================


def test_public_shape_resolution_row_fields_and_locator_key() -> None:
    """``ResolutionRow`` keeps its field names + ``key() -> str`` locator (frozen)."""
    row = audit.ResolutionRow("specify_cli/x.py", 42, "raw-path-join", "mission_slug")
    assert row.rel_path == "specify_cli/x.py"
    assert row.line == 42
    assert row.call_name == "raw-path-join"
    assert row.handle_source == "mission_slug"
    # The frozen resolver test does ``row.key().startswith(...)`` — key() MUST be a
    # ``rel:line`` str, NOT the composite tuple.
    assert row.key() == "specify_cli/x.py:42"
    assert isinstance(row.key(), str)


def test_public_shape_selection_row_fields_and_locator_key() -> None:
    """``SelectionRow`` keeps its field names + ``key() -> str`` locator (frozen)."""
    sel = audit.SelectionRow("specify_cli/x.py", 7, "resolve_mission_read_path", True)
    assert sel.rel_path == "specify_cli/x.py"
    assert sel.line == 7
    assert sel.call_name == "resolve_mission_read_path"
    assert sel.in_seam_file is True
    assert sel.key() == "specify_cli/x.py:7"
    assert isinstance(sel.key(), str)


def test_public_shape_composite_key_is_the_added_comparand() -> None:
    """The composite identity is an ADDED method returning ``(rel, qualname, token)``."""
    assert hasattr(audit.ResolutionRow, "composite_key")
    assert hasattr(audit.SelectionRow, "composite_key")
    # discover_rows / discover_selection_callsites take no arguments (signature frozen).
    rows = audit.discover_rows()
    assert isinstance(rows, list) and rows, "live scan must be non-empty"
    key = rows[0].composite_key()
    assert isinstance(key, tuple) and len(key) == 3
    assert all(isinstance(part, str) for part in key)


def test_allowlisted_selection_callsites_stays_str_keyed_and_empty() -> None:
    """The FR-006a allowlist keeps its ``dict[str, str]`` shape (frozen guard reads it)."""
    assert audit.ALLOWLISTED_SELECTION_CALLSITES == {}


# ===========================================================================
# Pure seam legs — the exact functions main() calls (drive the real path).
# ===========================================================================

# Mirror of ``audit.CompositeKey`` (``audit`` is loaded as a bare ModuleType, so its
# type alias is not statically resolvable — declare a local structural twin).
_CompositeKey = tuple[str, str, str]

_K1: _CompositeKey = ("specify_cli/a.py", "func_one", "root / KITTY_SPECS_DIR / slug")
_K2: _CompositeKey = ("specify_cli/b.py", "func_two", "candidate_feature_dir_for_mission (")
_K3: _CompositeKey = ("specify_cli/c.py", "func_three", "resolve_status_surface (")


def test_check_undercount_flags_discovered_absent_from_inventory() -> None:
    """A discovered composite missing from the inventory set is RED (undercount)."""
    discovered = {_K1: "specify_cli/a.py:10", _K2: "specify_cli/b.py:20"}
    errors = audit.check_undercount(discovered, {_K2})  # _K1 undocumented
    assert len(errors) == 1
    assert "specify_cli/a.py:10" in errors[0]
    assert "func_one" in errors[0]
    assert "undercount" in errors[0]


def test_check_undercount_green_when_all_documented() -> None:
    """Every discovered composite present in the inventory set → no errors."""
    discovered = {_K1: "a:1", _K2: "b:2"}
    assert audit.check_undercount(discovered, {_K1, _K2, _K3}) == []


def test_check_overcount_flags_inventory_ghost_rows() -> None:
    """An inventory composite with no live discovered sink is RED (overcount/ghost)."""
    inventory = {_K1: "specify_cli/a.py:10", _K3: "specify_cli/c.py:30"}
    errors = audit.check_overcount(inventory, {_K1})  # _K3 is a ghost
    assert len(errors) == 1
    assert "specify_cli/c.py:30" in errors[0]
    assert "func_three" in errors[0]
    assert "overcount/ghost" in errors[0]


def test_check_overcount_green_when_all_live() -> None:
    """Every inventory composite backed by a live discovered sink → no errors."""
    inventory = {_K1: "a:1", _K2: "b:2"}
    assert audit.check_overcount(inventory, {_K1, _K2, _K3}) == []


# ===========================================================================
# End-to-end main() triad on a synthetic tree — proves composite drift-immunity
# AND the main() wiring (both tripwire directions), for BOTH row types.
# ===========================================================================

_SINK_HEADER = (
    "| file:line | qualname | token | handle source | sink | disposition | rationale |\n"
    "| --- | --- | --- | --- | --- | --- | --- |"
)
_SEL_HEADER = (
    "| file:line | qualname | token | in seam file | disposition | notes |\n"
    "| --- | --- | --- | --- | --- | --- |"
)


def _sink_row(loc: str, qn: str, tok: str, handle: str, sink: str, disp: str) -> str:
    return f"| {loc} | `{qn}` | `{tok}` | {handle} | {sink} | {disp} | test rationale |"


def _sel_row(loc: str, qn: str, tok: str, seam: str, disp: str) -> str:
    return f"| {loc} | `{qn}` | `{tok}` | {seam} | {disp} | test note |"


class _SyntheticTree:
    """A monkeypatched source tree + inventory the audit runs against."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        self._mp = monkeypatch
        self.root = tmp_path
        self.src = tmp_path / "src"
        self.pkg = self.src / "specify_cli" / "pkg"
        self.pkg.mkdir(parents=True)
        self.inventory = tmp_path / "inventory.md"
        monkeypatch.setattr(audit, "_REPO_ROOT", self.root)
        monkeypatch.setattr(audit, "_SRC_ROOT", self.src)
        monkeypatch.setattr(audit, "SRC_SPECIFY_CLI", self.src / "specify_cli")
        monkeypatch.setattr(audit, "SRC_MISSION_RUNTIME", self.src / "mission_runtime")
        monkeypatch.setattr(audit, "INVENTORY_PATH", self.inventory)
        monkeypatch.setattr(audit, "KNOWN_CANDIDATE_FILES", ())

    def write_mod(self, name: str, body: str) -> None:
        (self.pkg / name).write_text(body, encoding="utf-8")

    def write_inventory(self, sink_rows: list[str], sel_rows: list[str] | None = None) -> None:
        parts = ["# synthetic inventory", "", _SINK_HEADER, *sink_rows]
        if sel_rows is not None:
            parts += ["", _SEL_HEADER, *sel_rows]
        self.inventory.write_text("\n".join(parts) + "\n", encoding="utf-8")


_RAW_JOIN_MOD = (
    "KITTY_SPECS_DIR = 'kitty-specs'\n"
    "\n"
    "\n"
    "def build_dir(mission_slug, root):\n"
    "    return root / KITTY_SPECS_DIR / mission_slug\n"
)


def test_main_drift_immune_documented_sink_stays_green(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """#2306 fix: a +1 line drift of a DOCUMENTED sink keeps main() GREEN.

    The composite ``(rel_path, qualname, token)`` is content-addressed, so shifting
    the callsite down one line (a blank/comment insertion above it) does NOT change
    the identity — unlike the old raw ``rel:line`` compare which reddened on drift.
    """
    tree = _SyntheticTree(monkeypatch, tmp_path)
    tree.write_mod("mod.py", _RAW_JOIN_MOD)

    (row,) = audit.discover_rows()
    original_line = row.line
    # Capture the composite BEFORE the file is rewritten (composite_key reads live).
    original_key = row.composite_key()
    _rel, qualname, token = original_key
    assert qualname == "build_dir"
    tree.write_inventory(
        [_sink_row(row.key(), qualname, token, row.handle_source, row.call_name, "raw-bypass")]
    )
    assert audit.main() == 0  # baseline documented → green

    # Insert a comment line ABOVE the callsite: the join drifts +1 line.
    drifted = "# a fresh comment line inserted above (line drift)\n" + _RAW_JOIN_MOD
    tree.write_mod("mod.py", drifted)
    (drifted_row,) = audit.discover_rows()
    assert drifted_row.line == original_line + 1  # the locator really moved
    assert drifted_row.composite_key() == original_key  # identity is stable
    assert audit.main() == 0  # STILL green — inventory untouched, composite unchanged


def test_main_undocumented_sink_is_red(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Non-vacuity: a genuinely NEW undocumented sink reddens main() (undercount)."""
    tree = _SyntheticTree(monkeypatch, tmp_path)
    second = (
        _RAW_JOIN_MOD
        + "\n\ndef build_other(mission_slug, base):\n"
        "    return base / KITTY_SPECS_DIR / mission_slug\n"
    )
    tree.write_mod("mod.py", second)
    rows = {r.composite_key()[1]: r for r in audit.discover_rows()}
    documented = rows["build_dir"]
    _rel, qn, tok = documented.composite_key()
    # Inventory documents only build_dir — build_other is an undocumented sink.
    tree.write_inventory(
        [_sink_row(documented.key(), qn, tok, documented.handle_source, "raw-path-join", "raw-bypass")]
    )
    assert audit.main() == 1


def test_main_ghost_inventory_row_is_red(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Non-vacuity: an inventory row with no live sink reddens main() (overcount)."""
    tree = _SyntheticTree(monkeypatch, tmp_path)
    tree.write_mod("mod.py", _RAW_JOIN_MOD)
    (row,) = audit.discover_rows()
    _rel, qn, tok = row.composite_key()
    tree.write_inventory(
        [
            _sink_row(row.key(), qn, tok, row.handle_source, "raw-path-join", "raw-bypass"),
            # A ghost: documents a sink that does not exist in the live tree.
            _sink_row(
                "specify_cli/pkg/gone.py:5",
                "deleted_fn",
                "root / KITTY_SPECS_DIR / mission_slug",
                "mission_slug",
                "raw-path-join",
                "raw-bypass",
            ),
        ]
    )
    assert audit.main() == 1


def test_main_inventory_only_tag_exempts_ghost_row(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """An ``[inventory-only]``-tagged ghost row is EXEMPT from the overcount tripwire."""
    tree = _SyntheticTree(monkeypatch, tmp_path)
    tree.write_mod("mod.py", _RAW_JOIN_MOD)
    (row,) = audit.discover_rows()
    _rel, qn, tok = row.composite_key()
    ghost = (
        "| specify_cli/pkg/gone.py:5 | `deleted_fn` "
        "| `root / KITTY_SPECS_DIR / mission_slug` | mission_slug | raw-path-join "
        "| raw-bypass | [inventory-only] removed by mission XYZ; kept for the record |"
    )
    tree.write_inventory(
        [
            _sink_row(row.key(), qn, tok, row.handle_source, "raw-path-join", "raw-bypass"),
            ghost,
        ]
    )
    assert audit.main() == 0  # tagged ghost tolerated


def test_main_fail_closed_on_missing_stored_identity(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A sink row with an empty stored qualname/token aborts (fail-closed parse)."""
    tree = _SyntheticTree(monkeypatch, tmp_path)
    tree.write_mod("mod.py", _RAW_JOIN_MOD)
    (row,) = audit.discover_rows()
    # Empty qualname + token cells → the composite cannot be built → RED.
    broken = f"| {row.key()} |  |  | {row.handle_source} | raw-path-join | raw-bypass | x |"
    tree.write_inventory([broken])
    assert audit.main() == 1


# --- SelectionRow legs (second row type) -----------------------------------

_SELECTION_MOD = (
    "def some_reader(repo_root, slug, mid8):\n"
    "    return resolve_mission_read_path(repo_root, slug, mid8)\n"
)


def test_main_external_selection_call_is_red(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """FR-006a: a direct ``resolve_mission_read_path`` OUTSIDE the seam reddens main().

    Second-row-type non-vacuity: the SelectionRow check is composite-keyed and the
    allowlist is empty, so any external selection callsite is a bypass. Documenting
    it in the read-SELECTION table (so undercount/overcount are green) isolates the
    FR-006a bypass as the sole failure — proving that check bites on its own.
    """
    tree = _SyntheticTree(monkeypatch, tmp_path)
    tree.write_mod("reader.py", _SELECTION_MOD)
    (sel,) = audit.discover_selection_callsites()
    assert sel.in_seam_file is False
    _rel, qn, tok = sel.composite_key()
    tree.write_inventory(
        sink_rows=[],
        sel_rows=[_sel_row(sel.key(), qn, tok, "no", "BLESSED-EXTERNAL")],
    )
    assert audit.main() == 1  # documented, but external + not allowlisted → FR-006a RED


def test_main_selection_ghost_row_is_red(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Overcount on the read-SELECTION table: a ghost selection row reddens main()."""
    tree = _SyntheticTree(monkeypatch, tmp_path)
    # No selection callsites in the tree, but the inventory documents one.
    tree.write_mod("mod.py", _RAW_JOIN_MOD)
    (row,) = audit.discover_rows()
    _rel, qn, tok = row.composite_key()
    ghost_sel = _sel_row(
        "specify_cli/pkg/ghost.py:9",
        "gone_reader",
        "return _resolve_mission_read_path (",
        "no",
        "BLESSED-EXTERNAL",
    )
    tree.write_inventory(
        sink_rows=[
            _sink_row(row.key(), qn, tok, row.handle_source, "raw-path-join", "raw-bypass")
        ],
        sel_rows=[ghost_sel],
    )
    assert audit.main() == 1


# ===========================================================================
# Integration — the audit passes GREEN on the real, committed tree.
# ===========================================================================


def test_audit_passes_on_current_tree() -> None:
    """The committed ``inventory.md`` matches the live scan (both directions green)."""
    assert audit.main() == 0


def test_audit_passes_on_current_tree_immune_to_isolated_bite_mutation() -> None:
    """WP02 (#2638): this scanner is immune to an active isolated bite mutation.

    Root cause this guards against: the companion bite-battery in
    ``test_single_mission_surface_resolver.py`` used to rewrite the REAL
    ``mission_creation.py`` in place (restoring it on exit), so a sibling
    ``pytest-xdist`` worker running THIS scanner — a SEPARATE module instance
    of the same ``surface_resolution_audit/audit.py``, loaded here as
    ``audit`` — could observe the injected witness mid-mutation and produce a
    false RED. WP02 fixed the hazard at the source by isolating the mutation
    to a tmp copy (``_IsolatedSourceMutation``) that never touches the real
    file at all.

    This test RELIES ON that same isolation contract (imported from the
    companion module, not re-implemented here — see WP02 review guidance):
    while ``_IsolatedSourceMutation`` is actively mutating an isolated tmp
    copy through a WHOLLY SEPARATE loaded module instance
    (``_surface_resolution_audit_wp01``), THIS module's own
    ``discover_rows()`` — which always scans the REAL, un-patched tree via
    its own root globals, and is the exact dimension the WP02 bite-battery
    exercises — must return the exact same composite keys as before the
    mutation started, and the real file's bytes must be untouched.

    Scoped to ``discover_rows()`` rather than ``audit.main()``: ``main()``
    also drives the read-SELECTION scanner, which a DIFFERENT, pre-existing
    (out-of-WP02-scope) live-mutation battery
    (``test_selection_discriminator_is_independent_of_raw_join_scanner``, a
    real-file mutation of ``agent/context.py``) can race — an unrelated
    hazard this WP does not claim to fix. Narrowing to ``discover_rows()``
    keeps this proof targeted at exactly the isolation WP02 introduced.
    """
    from tests.architectural.test_single_mission_surface_resolver import (
        _SRC_SPECIFY_CLI,
        _IsolatedSourceMutation,
    )
    from tests.architectural.test_single_mission_surface_resolver import (
        _audit_mod as _isolated_audit_mod,
    )

    baseline_keys = {row.composite_key() for row in audit.discover_rows()}
    target = _SRC_SPECIFY_CLI / "core" / "mission_creation.py"
    original_bytes = target.read_bytes()
    snippet = (
        "\n\n"
        "def _wp02_immunity_witness(repo_root, mission_slug):  # noqa: injected T012\n"
        "    return repo_root / KITTY_SPECS_DIR / mission_slug\n"
    )

    with _IsolatedSourceMutation(target, snippet, _isolated_audit_mod):
        assert {row.composite_key() for row in audit.discover_rows()} == baseline_keys, (
            "#2638 regression: this module's own real-tree discover_rows() "
            "changed while a SIBLING module instance's isolated bite mutation "
            "was active — the isolation leaked onto the real tree."
        )
        assert target.read_bytes() == original_bytes, (
            "The real mission_creation.py was rewritten during a supposedly "
            "isolated mutation window."
        )

    assert {row.composite_key() for row in audit.discover_rows()} == baseline_keys
    assert target.read_bytes() == original_bytes
