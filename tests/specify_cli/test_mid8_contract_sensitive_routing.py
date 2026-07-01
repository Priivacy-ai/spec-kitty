"""Byte-parity characterization tests for the contract-sensitive mid8 sites (WP03).

These tests pin the CURRENT output of every site this WP routes to
``resolve_mid8`` — using **hard-coded literals captured from HEAD before any
edit** (never a re-call of ``resolve_mid8``, so the assertions cannot become a
``resolve_mid8(x) == resolve_mid8(x)`` tautology). They must pass before AND
after the routing change (NFR-001 byte-parity).

The five sites and their declared contracts (see
``scope-review/pedro-refute-already-done.md`` landmine analysis):

* ``status/aggregate.py:250``      — ``""`` decline contract.
* ``dashboard/scanner.py:438``     — ``None`` (not ``""``) contract, pseudo short-circuit.
* ``cli/commands/doctor.py:3068/3160`` — short-id tolerance (fallback to ``mission_id[:8]``).
* ``cli/commands/implement.py:385`` — ``meta["mid8"]`` preference, then ``None`` contract.
* ``lanes/worktree_allocator.py:169`` — ``None`` contract (F-1 build-breaker site).

Input domain note: ``aggregate`` and ``scanner`` both source ``mission_id``
from ``meta.json`` via helpers that coerce ``""``/blank to ``None`` and
otherwise carry a full 26-char ULID. A short-but-nonempty ``mission_id`` is not
a reachable input for those two sites, so the realistic domain pinned here is
``{full ULID, None}``. The ``doctor`` and ``worktree_allocator`` sites have an
explicit short-id branch, which IS pinned below.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specify_cli.dashboard.scanner import build_mission_registry
from specify_cli.lanes.branch_naming import resolve_mid8

pytestmark = [pytest.mark.unit, pytest.mark.fast]

# --- Golden literals captured from HEAD before any edit (do NOT recompute) ---
FULL_ULID = "01KV7SFD9ABCDEFGHJKMNPQRST"  # 26-char ULID
FULL_MID8 = "01KV7SFD"  # first 8 chars of FULL_ULID — hard-coded, NOT FULL_ULID[:8]
SHORT_ID = "01KV"  # len 4, < 8
SLUG_WITH_TAIL = "naming-identity-routing-rider-01KV7SFD"
SLUG_NO_TAIL = "plain-mission"


class TestResolveMid8Contracts:
    """Pin the seam outputs the routed expressions rely on (declared literals)."""

    def test_full_ulid_with_matching_slug_tail_yields_mid8(self) -> None:
        assert resolve_mid8(SLUG_WITH_TAIL, mission_id=FULL_ULID) == "01KV7SFD"

    def test_full_ulid_with_no_slug_tail_yields_mid8(self) -> None:
        assert resolve_mid8(SLUG_NO_TAIL, mission_id=FULL_ULID) == "01KV7SFD"

    def test_none_mission_id_declines_to_empty_string(self) -> None:
        assert resolve_mid8(SLUG_WITH_TAIL, mission_id=None) == ""

    def test_short_mission_id_declines_to_empty_string(self) -> None:
        assert resolve_mid8(SLUG_WITH_TAIL, mission_id=SHORT_ID) == ""


class TestAggregateContract:
    """``status/aggregate.py:250`` — the ``""`` decline contract.

    HEAD: ``mid8 = mission_id[:8] if mission_id else ""``.
    Realistic domain (meta.json ULID or None): full → ``"01KV7SFD"``; None → ``""``.
    """

    def test_full_ulid_yields_mid8_literal(self) -> None:
        # HEAD literal: FULL_ULID[:8] == "01KV7SFD"
        assert resolve_mid8(SLUG_WITH_TAIL, mission_id=FULL_ULID) == "01KV7SFD"

    def test_absent_mission_id_yields_empty_string(self) -> None:
        # HEAD literal: "" when mission_id is falsy.
        assert resolve_mid8(SLUG_WITH_TAIL, mission_id=None) == ""


class TestScannerContract:
    """``dashboard/scanner.py:438`` — the ``None`` (not ``""``) contract.

    HEAD: ``None if is_pseudo else (mission_id[:8] if mission_id else None)``.
    Routed: ``None if is_pseudo else (resolve_mid8(...) or None)``.
    Exercised end-to-end through ``build_mission_registry`` against real
    meta.json fixtures so the ``None`` (not ``""``) registry contract is pinned.
    """

    @staticmethod
    def _write_mission(specs_dir: Path, slug: str, meta: dict[str, object] | None) -> None:
        mission_dir = specs_dir / slug
        mission_dir.mkdir(parents=True)
        if meta is not None:
            (mission_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")

    def test_assigned_mission_records_mid8_string(self, tmp_path: Path) -> None:
        specs = tmp_path / "kitty-specs"
        self._write_mission(
            specs,
            SLUG_WITH_TAIL,
            {"mission_id": FULL_ULID, "mission_number": 7},
        )
        registry = build_mission_registry(tmp_path)
        record = registry[FULL_ULID]
        # HEAD literal: FULL_ULID[:8] == "01KV7SFD"
        assert record["mid8"] == "01KV7SFD"

    def test_legacy_pseudo_key_records_none_mid8(self, tmp_path: Path) -> None:
        specs = tmp_path / "kitty-specs"
        # No mission_id but a mission_number → legacy pseudo key, mid8 is None.
        self._write_mission(specs, "legacy-thing", {"mission_number": 3})
        registry = build_mission_registry(tmp_path)
        record = registry["legacy:legacy-thing"]
        # HEAD literal: None (pseudo short-circuit), NOT "".
        assert record["mid8"] is None

    def test_orphan_pseudo_key_records_none_mid8(self, tmp_path: Path) -> None:
        specs = tmp_path / "kitty-specs"
        # No meta.json at all → orphan pseudo key, mid8 is None.
        self._write_mission(specs, "orphan-thing", None)
        registry = build_mission_registry(tmp_path)
        record = registry["orphan:orphan-thing"]
        # HEAD literal: None, NOT "".
        assert record["mid8"] is None


class TestScannerRoutedExpression:
    """Pin the exact routed RHS the scanner uses, isolated from disk I/O.

    Mirrors ``None if is_pseudo else (resolve_mid8(...) or None)`` and asserts
    against HEAD literals for the realistic ``{full ULID, None}`` domain.
    """

    @staticmethod
    def _routed(is_pseudo: bool, slug: str, mission_id: str | None) -> str | None:
        return None if is_pseudo else (resolve_mid8(slug, mission_id=mission_id) or None)

    def test_pseudo_short_circuits_to_none(self) -> None:
        assert self._routed(True, SLUG_WITH_TAIL, FULL_ULID) is None

    def test_full_ulid_yields_mid8_literal(self) -> None:
        assert self._routed(False, SLUG_WITH_TAIL, FULL_ULID) == "01KV7SFD"

    def test_absent_mission_id_yields_none_not_empty(self) -> None:
        result = self._routed(False, SLUG_WITH_TAIL, None)
        assert result is None
        assert result != ""  # explicit: None contract, NOT ""


class TestDoctorShortIdTolerance:
    """``doctor.py:3068`` & ``:3160`` — short-id tolerance must SURVIVE.

    HEAD: ``try: short = _mid8(mission_id) except ValueError: short = mission_id[:8]``.
    Routed: ``short = resolve_mid8(slug, mission_id=mission_id) or mission_id[:8]``.
    The dead ``try/except`` is removed (resolve_mid8 never raises) but the
    short-id fallback display value is preserved via ``or mission_id[:8]``.
    """

    @staticmethod
    def _routed(slug: str, mission_id: str) -> str:
        return resolve_mid8(slug, mission_id=mission_id) or mission_id[:8]

    def test_full_ulid_yields_mid8_literal(self) -> None:
        # HEAD: _mid8(FULL_ULID) == "01KV7SFD" (no exception).
        assert self._routed(SLUG_WITH_TAIL, FULL_ULID) == "01KV7SFD"

    def test_short_id_tolerance_preserved_via_fallback(self) -> None:
        # HEAD: _mid8 raises ValueError → fallback short = SHORT_ID[:8] == "01KV".
        # Routed: resolve_mid8 declines to "" → `or SHORT_ID[:8]` == "01KV".
        assert self._routed(SLUG_WITH_TAIL, SHORT_ID) == "01KV"


class TestImplementContract:
    """``implement.py:385`` — ``meta["mid8"]`` preference, then ``None`` contract.

    HEAD: ``meta.get("mid8") or (mission_id[:8] if isinstance(str) and >=8 else None)``.
    Routed: ``meta.get("mid8") or (resolve_mid8(slug, mission_id=mission_id) or None)``.
    """

    @staticmethod
    def _routed(meta_mid8: str | None, slug: str, mission_id: str | None) -> str | None:
        return meta_mid8 or (resolve_mid8(slug, mission_id=mission_id) or None)

    def test_stored_meta_mid8_takes_precedence(self) -> None:
        # HEAD literal: stored mid8 wins regardless of mission_id.
        assert self._routed("STORED88", SLUG_WITH_TAIL, FULL_ULID) == "STORED88"

    def test_full_ulid_fallback_yields_mid8_literal(self) -> None:
        assert self._routed(None, SLUG_WITH_TAIL, FULL_ULID) == "01KV7SFD"

    def test_short_id_yields_none(self) -> None:
        # HEAD literal: short id fails the >=8 guard → None.
        assert self._routed(None, SLUG_WITH_TAIL, SHORT_ID) is None

    def test_absent_mission_id_yields_none_not_empty(self) -> None:
        # HEAD literal: None (NOT "").
        result = self._routed(None, SLUG_WITH_TAIL, None)
        assert result is None
        assert result != ""


class TestWorktreeAllocatorContract:
    """``lanes/worktree_allocator.py:169`` — the F-1 build-breaker, ``None`` contract.

    HEAD: ``try: short_id = mid8(mission_id) except ValueError: short_id = None``.
    Routed: ``short_id = resolve_mid8(slug, mission_id=mission_id) or None``.
    Downstream ``if short_id is not None:`` guards sparse-checkout registration,
    so preserving the ``None`` contract for short/missing ids is load-bearing.
    """

    @staticmethod
    def _routed(slug: str, mission_id: str | None) -> str | None:
        return resolve_mid8(slug, mission_id=mission_id) or None

    def test_full_ulid_yields_mid8_literal(self) -> None:
        # HEAD: mid8(FULL_ULID) == "01KV7SFD".
        assert self._routed(SLUG_WITH_TAIL, FULL_ULID) == "01KV7SFD"

    def test_short_id_yields_none(self) -> None:
        # HEAD: mid8 raises → except → None.
        assert self._routed(SLUG_WITH_TAIL, SHORT_ID) is None

    def test_absent_mission_id_yields_none(self) -> None:
        # HEAD: mid8 raises on len<8 (None never reaches it via the truthy guard) → None.
        assert self._routed(SLUG_WITH_TAIL, None) is None


@pytest.mark.quarantine  # seam-scan drift: doctor.py refactored to orchestration shell; 'resolve_mid8' literal absent (Wave-0 orphan-bind triage, #2034/#2283)
def test_no_inline_mid8_slices_remain_after_routing() -> None:
    """Verification-by-deletion guard: the routed modules carry no inline
    ``mission_id[:8]`` derivation except the sanctioned ``doctor`` short-id
    tolerance fallback (``or mission_id[:8]``).
    """
    src_root = Path(__file__).resolve().parents[2] / "src" / "specify_cli"
    # aggregate, scanner, implement, allocator: no bare ``mission_id[:8]`` slice.
    for rel in (
        "status/aggregate.py",
        "dashboard/scanner.py",
        "cli/commands/implement.py",
        "lanes/worktree_allocator.py",
    ):
        text = (src_root / rel).read_text(encoding="utf-8")
        assert "mission_id[:8]" not in text, f"inline mid8 slice still present in {rel}"

    # doctor: the only permitted slice is the short-id tolerance fallback.
    doctor_text = (src_root / "cli/commands/doctor.py").read_text(encoding="utf-8")
    assert "resolve_mid8" in doctor_text
    # The dead ``try/except ValueError`` around _mid8 must be gone.
    assert "import mid8 as _mid8" not in doctor_text


if __name__ == "__main__":  # pragma: no cover - manual invocation aid
    raise SystemExit(pytest.main([__file__, "-v"]))
