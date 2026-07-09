"""Clock consolidation invariants (mission-resolver-port-01KX1C05 WP06, T024-T026).

Three distinct clock-helper contracts must coexist (D-04 / NFR-004):

1. **Isoformat family** -- 12 byte-identical
   ``datetime.now(UTC).isoformat()`` copies collapsed into one canonical
   :func:`specify_cli.core.time_utils.now_utc_iso`.
2. **Stamp family** (preserved, NOT folded into #1) -- second-precision
   ``%Y-%m-%dT%H:%M:%SZ`` output from ``task_utils.support.now_utc`` and
   ``cli.commands.agent.mission_parsing._utc_now_iso``.
3. **Datetime-returning family** (preserved, out of this WP's owned files) --
   ``decisions.emit._now_utc`` / ``decisions.service._now_utc`` return a
   ``datetime`` object, not a string.

This module asserts:
* the stamp family's serialized output is byte-identical to a frozen
  expected string (NFR-004) -- folding it into the isoformat helper would
  have changed on-disk timestamps;
* the isoformat family has exactly one definition (the 12 former local
  copies now import the canonical helper; none re-defines its own).
"""

from __future__ import annotations

import ast
from datetime import UTC, datetime
from pathlib import Path

import pytest

from specify_cli.cli.commands.agent import mission_parsing
from specify_cli.core.time_utils import now_utc_iso
from specify_cli.task_utils import support as task_utils_support

pytestmark = pytest.mark.fast

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC = _REPO_ROOT / "src"

# Fixed instant used to prove byte-identical serialization across the stamp
# and isoformat families. Chosen with non-zero microseconds so the isoformat
# family's higher precision is visibly exercised (and distinguished from the
# stamp family's second-only precision).
_FIXED_INSTANT = datetime(2026, 7, 8, 12, 34, 56, 789123, tzinfo=UTC)

# The 12 owned files that previously carried a byte-identical local
# ``datetime.now(UTC).isoformat()`` copy (mission-resolver-port-01KX1C05
# WP06 T024 owned_files, minus mission_parsing.py which hosts the stamp
# family instead).
_ISOFORMAT_FAMILY_FILES: tuple[str, ...] = (
    "specify_cli/event_journal/journal.py",
    "specify_cli/event_journal/coalesce.py",
    "specify_cli/sync/migrate_journal.py",
    "specify_cli/status/reducer.py",
    "specify_cli/status/emit.py",
    "specify_cli/status/lifecycle_events.py",
    "specify_cli/retrospective/lifecycle_events.py",
    "specify_cli/retrospective/events.py",
    "specify_cli/delivery/ledger.py",
    "specify_cli/delivery/targets.py",
    "specify_cli/delivery/retention.py",
    "specify_cli/dossier/events.py",
)

# The names the 12 local copies used to carry. A canonical-consolidation
# regression would look like one of these reappearing as a *function def*
# (not merely a call to the shared helper) in one of the owned files above.
_FORMER_LOCAL_NAMES = frozenset({"_now_utc", "_utc_now_iso", "_now_iso", "_iso_utc_now"})


class _FixedDatetime(datetime):
    """A ``datetime`` subclass whose ``now()`` always returns the fixed instant."""

    @classmethod
    def now(cls, tz=None):  # noqa: ANN001 -- mirrors datetime.now's signature
        return _FIXED_INSTANT if tz is not None else _FIXED_INSTANT.replace(tzinfo=None)


class TestCanonicalIsoformatHelper:
    """T024: one canonical `now_utc_iso()`, no surviving local duplicates."""

    def test_now_utc_iso_returns_iso8601_string(self) -> None:
        value = now_utc_iso()
        assert isinstance(value, str)
        # Round-trips losslessly through fromisoformat (proves ISO 8601 shape).
        assert datetime.fromisoformat(value).tzinfo is not None

    def test_now_utc_iso_byte_identical_under_fixed_clock(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import specify_cli.core.time_utils as time_utils_module

        monkeypatch.setattr(time_utils_module, "datetime", _FixedDatetime)
        assert time_utils_module.now_utc_iso() == "2026-07-08T12:34:56.789123+00:00"

    def test_no_owned_file_redefines_a_local_clock_helper(self) -> None:
        """None of the 12 formerly-duplicated owned files re-defines its own
        isoformat helper -- they must import the canonical
        :func:`now_utc_iso` instead (behavior-preserving reduction, T024).
        """
        offenders: list[str] = []
        for rel_path in _ISOFORMAT_FAMILY_FILES:
            path = _SRC / rel_path
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name in _FORMER_LOCAL_NAMES:
                    offenders.append(f"{rel_path}::{node.name}")
        assert offenders == [], f"local clock-helper duplicate(s) reintroduced: {offenders}"

    def test_every_owned_file_imports_the_canonical_helper(self) -> None:
        """Each of the 12 owned files either imports ``now_utc_iso`` from the
        canonical home rather than reimplementing it, or (status/reducer.py)
        had a genuinely dead, uncalled local copy that was deleted outright --
        confirmed separately by :func:`test_reducer_dead_copy_had_no_callers`.
        """
        genuinely_dead_no_import_needed = {"specify_cli/status/reducer.py"}
        missing: list[str] = []
        for rel_path in _ISOFORMAT_FAMILY_FILES:
            if rel_path in genuinely_dead_no_import_needed:
                continue
            path = _SRC / rel_path
            text = path.read_text(encoding="utf-8")
            if "from specify_cli.core.time_utils import now_utc_iso" not in text:
                missing.append(rel_path)
        assert missing == [], f"owned file(s) missing canonical helper import: {missing}"

    def test_reducer_dead_copy_had_no_callers(self) -> None:
        """``status/reducer.py``'s former local ``_now_utc`` copy was never
        called anywhere in the module (``materialized_at`` is derived from
        the last event's own ``at`` field, not a fresh clock read) -- so its
        removal needed no replacement import, unlike the other 11 owned
        copies. This pins that finding so a future edit can't silently
        reintroduce a dead clock helper without a test noticing the call.
        """
        path = _SRC / "specify_cli/status/reducer.py"
        text = path.read_text(encoding="utf-8")
        assert "_now_utc(" not in text
        assert "now_utc_iso(" not in text


class TestStampFamilyPreserved:
    """NFR-004: the 2 stamp callers stay byte-identical (%Y-%m-%dT%H:%M:%SZ),
    proving the isoformat consolidation did not fold this different-contract
    family in with it.
    """

    def test_task_utils_support_now_utc_byte_identical_under_fixed_clock(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(task_utils_support, "datetime", _FixedDatetime)
        assert task_utils_support.now_utc() == "2026-07-08T12:34:56Z"

    def test_mission_parsing_utc_now_iso_byte_identical_under_fixed_clock(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(mission_parsing, "datetime", _FixedDatetime)
        assert mission_parsing._utc_now_iso() == "2026-07-08T12:34:56Z"

    def test_stamp_helpers_share_one_format_constant(self) -> None:
        """T026 SAFE campsite fold: mission_parsing's stamp helper routes
        through the same ``TIMESTAMP_FORMAT`` constant as
        ``task_utils.support.now_utc`` instead of a second hardcoded literal
        -- no behavior change, just de-duplication of the format string.
        """
        assert mission_parsing.TIMESTAMP_FORMAT is task_utils_support.TIMESTAMP_FORMAT
        assert task_utils_support.TIMESTAMP_FORMAT == "%Y-%m-%dT%H:%M:%SZ"

    def test_stamp_and_isoformat_families_are_distinct_serializations(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The two families must never converge: the isoformat helper keeps
        sub-second precision and a ``+00:00`` offset; the stamp helper is
        second-precision with a literal ``Z`` suffix.
        """
        import specify_cli.core.time_utils as time_utils_module

        monkeypatch.setattr(time_utils_module, "datetime", _FixedDatetime)
        monkeypatch.setattr(task_utils_support, "datetime", _FixedDatetime)

        iso_value = time_utils_module.now_utc_iso()
        stamp_value = task_utils_support.now_utc()

        assert iso_value != stamp_value
        assert iso_value.endswith("+00:00")
        assert stamp_value.endswith("Z")
        assert "." in iso_value  # microseconds retained
        assert "." not in stamp_value  # microseconds dropped (second precision)
