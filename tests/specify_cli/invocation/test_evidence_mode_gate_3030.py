"""FR-003 applied to FR-009's evidence gate: absence is not malformation (#3030).

``_read_started_mode`` used to collapse two different states into one ``None``:

* the started record carries **no** ``mode_of_work`` (pre-v2 record), and
* the started record carries a ``mode_of_work`` that is **not** a recognised
  :class:`ModeOfWork` (hand-edited or corrupted ``kitty-ops`` line),

and ``None`` skipped FR-009 enforcement entirely.  So mangling one string in a
``kitty-ops`` line bought a Tier-2 evidence artifact on an advisory or query Op
— inability to determine the mode read as permission, which is the exact rule
this mission exists to close.

This module measures the **consequence**, not the boolean: whether the Tier-2
artifact under ``.kittify/evidence/<invocation_id>/`` actually appears.  Every
case runs through one probe (:func:`_close_with_evidence`) that returns two
independent facts, and the parametrised table below contains cases that must
land on *both* answers — a probe that returned the same verdict for every input
would fail on the permitted rows.

Absence keeps meaning absence: a pre-v2 record has no ``mode_of_work`` because
the field did not exist, its documented default is ``task_execution`` (see the
WP05 migration ``m_3_3_0_op_record_schema_v2`` and ``propagator``'s
``_projection_rule_for``), and that default is evidence-eligible.  Refusing on
absence would strand every legacy Op — a fail-closed answer to a question
nobody asked.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from specify_cli.invocation.errors import InvalidModeForEvidenceError
from specify_cli.invocation.executor import ProfileInvocationExecutor, build_close_contract
from specify_cli.invocation.modes import ModeOfWork
from specify_cli.invocation.writer import EVENTS_DIR

pytestmark = [pytest.mark.unit, pytest.mark.git_repo]

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "profiles"

_COMPACT_CTX = MagicMock()
_COMPACT_CTX.mode = "compact"
_COMPACT_CTX.text = "compact governance context"


# A distinct ULID per case keeps the per-op JSONL files independent.
# ``validate_invocation_id`` enforces 26 Crockford-base32 chars (no I/L/O/U).
def _op_id(tag: str) -> str:
    return f"01KPWA5X1{tag}".ljust(26, "0")


_IDS = {
    "valid_task_execution": _op_id("A1"),
    "valid_mission_step": _op_id("A2"),
    "valid_advisory": _op_id("A3"),
    "valid_query": _op_id("A4"),
    "absent": _op_id("B1"),
    "absent_null": _op_id("B2"),
    "absent_empty": _op_id("B3"),
    "cased": _op_id("C1"),
    "trailing_space": _op_id("C2"),
    "hyphenated": _op_id("C3"),
    "unknown_word": _op_id("C4"),
    "json_false": _op_id("C5"),
    "json_zero": _op_id("C6"),
    "json_list": _op_id("C7"),
    "json_object": _op_id("C8"),
}


def _setup_minimal_project(tmp_path: Path) -> Path:
    profiles_dir = tmp_path / ".kittify" / "profiles"
    profiles_dir.mkdir(parents=True)
    for yaml_file in FIXTURES_DIR.glob("*.agent.yaml"):
        shutil.copy(yaml_file, profiles_dir / yaml_file.name)
    (tmp_path / EVENTS_DIR).mkdir(parents=True, exist_ok=True)
    return tmp_path


_ABSENT = object()  # "the key is not in the record at all"


def _write_started(project: Path, invocation_id: str, mode: Any) -> None:
    """Write a raw started line whose ``mode_of_work`` is *mode*.

    Raw JSONL because ``OpStartedEvent`` cannot represent either of the shapes
    under test: the v2 model requires ``mode_of_work`` and validates it against
    a ``Literal``.  The states this module distinguishes only exist on disk.
    """
    events_dir = project / EVENTS_DIR
    events_dir.mkdir(parents=True, exist_ok=True)
    record: dict[str, Any] = {
        "event": "started",
        "invocation_id": invocation_id,
        "profile_id": "implementer-fixture",
        "action": "implement",
        "request_text": "ACME Holdings carve-out: draft the disclosure schedule",
        "actor": "claude",
        "governance_context_hash": "0123456789abcdef",
        "governance_context_available": True,
        "started_at": "2026-07-30T06:00:00Z",
    }
    if mode is not _ABSENT:
        record["mode_of_work"] = mode
    (events_dir / f"{invocation_id}.jsonl").write_text(json.dumps(record) + "\n", encoding="utf-8")


def _close_with_evidence(project: Path, invocation_id: str, evidence_file: Path) -> tuple[bool, bool]:
    """Close *invocation_id* with ``--evidence``; return ``(refused, promoted)``.

    ``promoted`` is the fact that matters: whether a Tier-2 evidence artifact
    now exists on disk for this Op.  It is read independently of whether the
    call raised, so a probe that raises for the wrong reason cannot be mistaken
    for a working gate.
    """
    refused = False
    with patch(
        "specify_cli.invocation.executor.build_charter_context",
        return_value=_COMPACT_CTX,
    ):
        executor = ProfileInvocationExecutor(project)
        try:
            executor.complete_invocation(
                invocation_id=invocation_id,
                outcome="done",
                closed_by="agent",
                evidence_ref=str(evidence_file),
            )
        except InvalidModeForEvidenceError:
            refused = True
    promoted = (project / ".kittify" / "evidence" / invocation_id).exists()
    return refused, promoted


# ---------------------------------------------------------------------------
# The table: recorded mode_of_work -> may it buy a Tier-2 evidence artifact?
# ---------------------------------------------------------------------------

_CASES = [
    # --- permitted: recognised evidence-eligible modes (positive controls) ---
    pytest.param("valid_task_execution", "task_execution", True, id="valid-task_execution"),
    pytest.param("valid_mission_step", "mission_step", True, id="valid-mission_step"),
    # --- permitted: ABSENCE. Pre-v2 records legitimately lack the field and
    #     its documented default (task_execution) is evidence-eligible.
    #     These rows are the regression pin: absence must keep meaning absence.
    pytest.param("absent", _ABSENT, True, id="absent-key-missing"),
    pytest.param("absent_null", None, True, id="absent-json-null"),
    pytest.param("absent_empty", "", True, id="absent-empty-string"),
    # --- refused: recognised non-eligible modes (the gate that already worked) ---
    pytest.param("valid_advisory", "advisory", False, id="valid-advisory"),
    pytest.param("valid_query", "query", False, id="valid-query"),
    # --- refused: MALFORMATION. Each of these is a plausible hand-edit or
    #     corruption of an advisory/query line; none of them may buy evidence.
    pytest.param("cased", "Advisory", False, id="malformed-cased"),
    pytest.param("trailing_space", "advisory ", False, id="malformed-trailing-space"),
    pytest.param("hyphenated", "task-execution", False, id="malformed-hyphenated"),
    pytest.param("unknown_word", "supervisory", False, id="malformed-unknown-word"),
    pytest.param("json_false", False, False, id="malformed-json-false"),
    pytest.param("json_zero", 0, False, id="malformed-json-zero"),
    pytest.param("json_list", ["advisory"], False, id="malformed-json-list"),
    pytest.param("json_object", {"mode": "advisory"}, False, id="malformed-json-object"),
]


@pytest.mark.parametrize(("case", "recorded_mode", "may_promote"), _CASES)
def test_evidence_promotion_follows_the_recorded_mode(
    tmp_path: Path,
    case: str,
    recorded_mode: Any,
    may_promote: bool,
) -> None:
    """A Tier-2 artifact appears iff the record's mode is *determinably* eligible.

    The malformed rows are the red: before the absent/malformed split they all
    reached ``_read_started_mode``'s ``None`` and skipped enforcement, so the
    artifact was written.  The permitted rows are the positive control — if the
    gate simply refused everything they would fail here.
    """
    project = _setup_minimal_project(tmp_path)
    invocation_id = _IDS[case]
    _write_started(project, invocation_id, recorded_mode)

    evidence_file = tmp_path / f"{case}-evidence.md"
    evidence_file.write_text("# Evidence\n\nACME Holdings carve-out schedule.\n")

    refused, promoted = _close_with_evidence(project, invocation_id, evidence_file)

    evidence_dir = project / ".kittify" / "evidence" / invocation_id
    if may_promote:
        assert promoted, f"mode_of_work={recorded_mode!r} must still promote evidence; nothing at {evidence_dir}"
        assert not refused, f"mode_of_work={recorded_mode!r} must not be refused"
    else:
        assert not promoted, (
            f"mode_of_work={recorded_mode!r} bought a Tier-2 evidence artifact at {evidence_dir} — "
            "an undeterminable mode is not permission to promote (FR-003/FR-009)"
        )
        assert refused, f"mode_of_work={recorded_mode!r} must raise InvalidModeForEvidenceError"


@pytest.mark.parametrize(("case", "recorded_mode", "may_promote"), _CASES)
def test_refusal_is_pre_write(
    tmp_path: Path,
    case: str,
    recorded_mode: Any,
    may_promote: bool,
) -> None:
    """A refused close appends no ``completed`` event; a permitted one does.

    Same two-answer shape as above: the permitted rows prove the assertion can
    distinguish a written trail from an unwritten one.
    """
    project = _setup_minimal_project(tmp_path)
    invocation_id = _IDS[case]
    _write_started(project, invocation_id, recorded_mode)

    evidence_file = tmp_path / f"{case}-evidence.md"
    evidence_file.write_text("# Evidence")

    _close_with_evidence(project, invocation_id, evidence_file)

    trail = (project / EVENTS_DIR / f"{invocation_id}.jsonl").read_text(encoding="utf-8")
    events = [json.loads(line)["event"] for line in trail.splitlines() if line.strip()]
    if may_promote:
        assert "completed" in events, f"permitted close must append a completed event; got {events}"
    else:
        assert events == ["started"], f"refusal must be pre-write; trail is {events}"


def test_undeterminable_mode_still_lets_the_op_close_without_evidence(tmp_path: Path) -> None:
    """The refusal is scoped to evidence promotion — it never strands an Op.

    Refusing to *close* a record whose mode cannot be read would be fail-closed
    on a question nobody asked (the same trap ``_projection_rule_for`` calls out
    for absence).  Only the promotion is a permission; closing is not.
    """
    project = _setup_minimal_project(tmp_path)
    invocation_id = _op_id("D1")
    _write_started(project, invocation_id, "Advisory")

    with patch(
        "specify_cli.invocation.executor.build_charter_context",
        return_value=_COMPACT_CTX,
    ):
        executor = ProfileInvocationExecutor(project)
        completed = executor.complete_invocation(
            invocation_id=invocation_id,
            outcome="done",
            closed_by="agent",
        )

    assert completed.event == "completed"
    assert completed.evidence_ref is None


# ---------------------------------------------------------------------------
# Sibling: the close contract advertises --evidence off the same classification
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("recorded_mode", "advertises_evidence"),
    [
        pytest.param("task_execution", True, id="valid-task_execution"),
        pytest.param("mission_step", True, id="valid-mission_step"),
        pytest.param(None, True, id="absent"),
        pytest.param("", True, id="absent-empty-string"),
        pytest.param("advisory", False, id="valid-advisory"),
        pytest.param("query", False, id="valid-query"),
        pytest.param("Advisory", False, id="malformed-cased"),
        pytest.param("advisory ", False, id="malformed-trailing-space"),
        pytest.param("supervisory", False, id="malformed-unknown-word"),
    ],
)
def test_close_contract_advertises_evidence_iff_the_gate_permits_it(
    recorded_mode: Any,
    advertises_evidence: bool,
) -> None:
    """The advertised contract and the enforced gate read one classification.

    Two gates on two chains is how C-003 divergence starts; the contract must
    not offer ``--evidence`` on a mode the executor will refuse.
    """
    contract = build_close_contract(_op_id("E1"), recorded_mode)
    assert ("evidence_flag" in contract) is advertises_evidence, (
        f"mode_of_work={recorded_mode!r}: close contract evidence_flag presence disagrees with the enforcement gate"
    )


def test_every_recognised_mode_is_covered_by_the_table() -> None:
    """Guard against a new ModeOfWork member landing with no row in _CASES."""
    covered = {param.values[1] for param in _CASES if isinstance(param.values[1], str)}
    missing = {mode.value for mode in ModeOfWork} - covered
    assert not missing, f"ModeOfWork members with no row in _CASES: {sorted(missing)}"
