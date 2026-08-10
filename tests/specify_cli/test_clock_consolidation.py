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


# ---------------------------------------------------------------------------
# The structural ratchet (review #2611): a full-tree AST negative gate.
#
# The owned-file inventory above protects only the ORIGINAL 12 files, so every
# newly migrated module could regress while this suite stayed green. That is an
# inventory, not a gate. The scan below walks the WHOLE src/specify_cli tree for
# the raw aware-UTC ``.isoformat()`` form, so a module added tomorrow is covered
# the moment it lands -- no list to remember to update.
# ---------------------------------------------------------------------------

# Justified exceptions. Each is a genuinely DISTINCT CONTRACT, not an escape
# hatch; anything added here needs the same standard.
_RAW_FORM_EXEMPT: dict[str, str] = {
    # The canonical implementation itself -- this IS the one permitted producer.
    "specify_cli/core/time_utils.py": "hosts now_utc_iso(); the single canonical call site",
}


def _is_utc_alias(node: ast.expr) -> bool:
    """Every aware-UTC spelling, including module-aliased imports.

    Covers ``UTC`` / ``<mod>.UTC`` / ``timezone.utc`` / ``<mod>.timezone.utc``.
    The module segment is matched by *shape*, not by the literal name
    ``datetime``, so an ``import datetime as _dt`` alias (``_dt.UTC`` /
    ``_dt.timezone.utc``) is caught too -- the exact idiom two of this PR's
    own migrated modules used before migration. An attribute chain ending in
    ``.UTC`` or ``.timezone.utc`` passed to a bare ``.now(...)`` is, in
    practice, always stdlib datetime.
    """
    if isinstance(node, ast.Name):
        return node.id == "UTC"
    if isinstance(node, ast.Attribute):
        base = node.value
        # <mod>.UTC  (datetime.UTC, _dt.UTC)
        if node.attr == "UTC" and isinstance(base, ast.Name):
            return True
        if node.attr == "utc":
            # timezone.utc  (bare, or aliased to a bare name)
            if isinstance(base, ast.Name) and base.id == "timezone":
                return True
            # <mod>.timezone.utc  (datetime.timezone.utc, _dt.timezone.utc)
            if (
                isinstance(base, ast.Attribute)
                and base.attr == "timezone"
                and isinstance(base.value, ast.Name)
            ):
                return True
    return False


def _now_call_passes_utc(call: ast.Call) -> bool:
    """True for ``<x>.now(<aware-UTC>)`` where the timezone is passed either
    positionally (``now(UTC)``) or by the ``tz=`` keyword (``now(tz=UTC)``) -
    the two spellings serialize byte-identically.
    """
    if not (isinstance(call.func, ast.Attribute) and call.func.attr == "now"):
        return False
    if len(call.args) == 1 and not call.keywords:  # now(UTC)
        return _is_utc_alias(call.args[0])
    if not call.args and len(call.keywords) == 1:  # now(tz=UTC)
        kw = call.keywords[0]
        return kw.arg == "tz" and _is_utc_alias(kw.value)
    return False


def _raw_utc_isoformat_lines(tree: ast.AST) -> list[int]:
    """Line numbers of every raw ``datetime.now(<aware-UTC>).isoformat()``.

    Deliberately NARROW - it flags only the byte-identical form that
    ``now_utc_iso()`` replaces:

    - ``.isoformat()`` must take NO arguments. ``isoformat(timespec=...)`` is a
      different serialization (a distinct contract), not a violation.
    - the ``now()`` timezone must be an aware-UTC alias, passed positionally
      (``now(UTC)``) or by the ``tz=`` keyword (``now(tz=UTC)``). A naive
      ``now()`` and ``now(some_other_tz)`` are different contracts too.
    """
    hits: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        outer = node.func
        if not (isinstance(outer, ast.Attribute) and outer.attr == "isoformat"):
            continue
        if node.args or node.keywords:
            continue  # timespec= etc. -> a distinct serialization contract
        inner = outer.value
        if isinstance(inner, ast.Call) and _now_call_passes_utc(inner):
            hits.append(node.lineno)
    return hits


def test_no_raw_aware_utc_isoformat_outside_the_canonical_helper() -> None:
    """THE RATCHET: no module may mint the raw form locally.

    Structural, not inventory-based - a module added after this test was
    written is covered automatically.
    """
    offenders: list[str] = []
    scanned = 0
    for path in sorted((_SRC / "specify_cli").rglob("*.py")):
        rel = path.relative_to(_SRC).as_posix()
        if rel in _RAW_FORM_EXEMPT:
            continue
        scanned += 1
        for lineno in _raw_utc_isoformat_lines(ast.parse(path.read_text(encoding="utf-8"))):
            offenders.append(f"{rel}:{lineno}")

    assert scanned > 100, f"the scan must actually cover the tree (only {scanned} files seen)"
    assert not offenders, (
        "raw aware-UTC isoformat() found outside the canonical helper - route these "
        "onto specify_cli.core.time_utils.now_utc_iso():\n  " + "\n  ".join(offenders)
    )


def test_the_ratchet_is_non_vacuous() -> None:
    """SELF-MUTANT: prove the detector FIRES on a planted violation.

    A gate that never exercised its failure path is theatre. This drives the
    SAME detector the tree scan uses, so a future refactor that silently breaks
    the matcher turns this red instead of passing an empty scan.
    """
    violations = (
        "import datetime\nx = datetime.datetime.now(datetime.UTC).isoformat()\n",
        "from datetime import UTC, datetime\nx = datetime.now(UTC).isoformat()\n",
        "from datetime import datetime, timezone\nx = datetime.now(timezone.utc).isoformat()\n",
        # the ``tz=`` keyword spelling -- byte-identical to positional now(UTC)
        "from datetime import UTC, datetime\nx = datetime.now(tz=UTC).isoformat()\n",
        # the fully-qualified ``datetime.timezone.utc`` alias
        "import datetime\nx = datetime.datetime.now(datetime.timezone.utc).isoformat()\n",
        # module-aliased import (``import datetime as _dt``) - the idiom two of
        # this PR's own migrated modules used before migration
        "import datetime as _dt\nx = _dt.datetime.now(_dt.UTC).isoformat()\n",
        "import datetime as _dt\nx = _dt.datetime.now(_dt.timezone.utc).isoformat()\n",
    )
    for src in violations:
        assert _raw_utc_isoformat_lines(ast.parse(src)), f"detector MISSED a violation:\n{src}"

    # ...and does NOT fire on the distinct contracts it must leave alone.
    allowed = (
        "from specify_cli.core.time_utils import now_utc_iso\nx = now_utc_iso()\n",
        # a different serialization: second precision via timespec
        "from datetime import UTC, datetime\nx = datetime.now(UTC).isoformat(timespec='seconds')\n",
        # the datetime-returning family
        "from datetime import UTC, datetime\nx = datetime.now(UTC)\n",
        # naive now() - a different contract
        "from datetime import datetime\nx = datetime.now().isoformat()\n",
    )
    for src in allowed:
        assert not _raw_utc_isoformat_lines(ast.parse(src)), f"detector FALSE-POSITIVED on:\n{src}"


def test_every_exemption_is_real_and_still_needed() -> None:
    """No stale exemptions: each exempt file must exist AND still contain the form."""
    for rel, why in _RAW_FORM_EXEMPT.items():
        path = _SRC / rel
        assert path.exists(), f"exempt file no longer exists, drop it: {rel}"
        assert _raw_utc_isoformat_lines(ast.parse(path.read_text(encoding="utf-8"))), (
            f"exemption is stale (file no longer contains the raw form) - remove it: {rel} ({why})"
        )
