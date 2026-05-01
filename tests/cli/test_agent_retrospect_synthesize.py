"""Tests for ``spec-kitty agent retrospect synthesize`` (WP08 / T041).

Exercises all exit codes (0–5), JSON envelope schema, Rich/JSON informational
equivalence (CHK034), and the --apply flag semantics.

Uses :class:`typer.testing.CliRunner` against the agent typer app.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.agent import app
from specify_cli.context.mission_resolver import AmbiguousHandleError, ResolvedMission
from specify_cli.doctrine_synthesizer import (
    AppliedChange,
    ConflictGroup,
    PlannedApplication,
    RejectedProposal,
    SynthesisResult,
)

# ---------------------------------------------------------------------------
# Runner + fixtures
# ---------------------------------------------------------------------------

runner = CliRunner()

# Valid 26-char ULIDs for test fixtures (Crockford base32: 0-9 A-H J-N P-T V-Z)
# No I, L, O, or U characters allowed.
FAKE_MISSION_ID = "01KQ6YEG000000000000000000"
FAKE_MID8 = FAKE_MISSION_ID[:8]
FAKE_SLUG = "mission-retrospective-learning-loop-01KQ6YEG"
FAKE_PROPOSAL_ID_A = "01KQ6YEG00000000000000001A"
FAKE_PROPOSAL_ID_B = "01KQ6YEG00000000000000001B"
FAKE_EVENT_ID = "01KQ6YEG00000000000000001C"

PLANNED_APP = PlannedApplication(
    proposal_id=FAKE_PROPOSAL_ID_A,
    kind="add_glossary_term",
    targets=["glossary:term:foo"],
    diff_preview="add glossary term 'foo'",
)

APPLIED_CHANGE = AppliedChange(
    proposal_id=FAKE_PROPOSAL_ID_A,
    target_urn="glossary:term:foo",
    artifact_path=".kittify/glossary/foo.yaml",
    provenance_path=".kittify/glossary/.provenance/foo.yaml",
    re_applied=False,
)

CONFLICT_GROUP = ConflictGroup(
    proposal_ids=[FAKE_PROPOSAL_ID_A, FAKE_PROPOSAL_ID_B],
    reason="Conflicting add_glossary_term proposals",
)

STALE_REJECTION = RejectedProposal(
    proposal_id=FAKE_PROPOSAL_ID_A,
    reason="stale_evidence",
    detail="Evidence event ids not reachable in source mission event log: ['01EV']",
)

INVALID_REJECTION = RejectedProposal(
    proposal_id=FAKE_PROPOSAL_ID_A,
    reason="invalid_payload",
    detail="No apply handler found",
)


def _make_resolved_mission(mission_id: str = FAKE_MISSION_ID, tmp_path: Path | None = None) -> ResolvedMission:
    """Build a fake ResolvedMission."""
    feature_dir = (tmp_path or Path("/tmp")) / "kitty-specs" / FAKE_SLUG
    return ResolvedMission(
        mission_id=mission_id,
        mission_slug=FAKE_SLUG,
        mid8=mission_id[:8],
        feature_dir=feature_dir,
    )


def _good_result(dry_run: bool = True) -> SynthesisResult:
    """A clean SynthesisResult (no conflicts/rejections)."""
    return SynthesisResult(
        dry_run=dry_run,
        planned=[PLANNED_APP],
        applied=[] if dry_run else [APPLIED_CHANGE],
        conflicts=[],
        rejected=[],
        events_emitted=[] if dry_run else [FAKE_EVENT_ID],
    )


def _conflict_result() -> SynthesisResult:
    return SynthesisResult(
        dry_run=False,
        planned=[],
        applied=[],
        conflicts=[CONFLICT_GROUP],
        rejected=[
            RejectedProposal(
                proposal_id=FAKE_PROPOSAL_ID_A,
                reason="conflict",
                detail="Conflicting proposals",
            )
        ],
        events_emitted=[],
    )


def _stale_result() -> SynthesisResult:
    return SynthesisResult(
        dry_run=False,
        planned=[PLANNED_APP],
        applied=[],
        conflicts=[],
        rejected=[STALE_REJECTION],
        events_emitted=[],
    )


# ---------------------------------------------------------------------------
# Helpers for patching the command's dependencies
# ---------------------------------------------------------------------------


def _patched_invoke(
    args: list[str],
    *,
    resolved_mission: ResolvedMission | None = None,
    result: SynthesisResult | None = None,
    read_record_side_effect: Exception | None = None,
    repo_root: Path | None = None,
) -> Any:
    """
    Invoke ``agent retrospect synthesize`` with key dependencies mocked.

    - locate_project_root → returns ``repo_root`` (default: Path("/fake/root"))
    - resolve_mission_handle → returns ``resolved_mission``
    - read_record → returns a stub RetrospectiveRecord (or raises side_effect)
    - apply_proposals → returns ``result``
    """
    root = repo_root or Path("/fake/root")
    resolved = resolved_mission or _make_resolved_mission()

    # Build a minimal stub retrospective record whose proposals list is empty
    stub_record = MagicMock()
    stub_record.proposals = []
    stub_record.mission.mission_id = FAKE_MISSION_ID

    with (
        patch(
            "specify_cli.cli.commands.agent_retrospect.locate_project_root",
            return_value=root,
        ),
        patch(
            "specify_cli.cli.commands.agent_retrospect.resolve_mission_handle",
            return_value=resolved,
        ),
        patch(
            "specify_cli.cli.commands.agent_retrospect.read_record",
            side_effect=read_record_side_effect,
            return_value=None if read_record_side_effect else stub_record,
        ),
        patch(
            "specify_cli.cli.commands.agent_retrospect.apply_proposals",
            return_value=result or _good_result(),
        ),
    ):
        return runner.invoke(app, args, catch_exceptions=False)


# ---------------------------------------------------------------------------
# Exit code 0 — valid handle, dry-run, fixture record
# ---------------------------------------------------------------------------


def test_valid_handle_dryrun_exit0() -> None:
    """Valid handle + dry-run completes cleanly (exit 0)."""
    result = _patched_invoke(
        ["retrospect", "synthesize", "--mission", "01KQ6YEG"],
        result=_good_result(dry_run=True),
    )
    assert result.exit_code == 0, result.output


def test_dryrun_is_default() -> None:
    """Default (no --apply flag) is dry-run."""
    result = _patched_invoke(
        ["retrospect", "synthesize", "--mission", "01KQ6YEG"],
        result=_good_result(dry_run=True),
    )
    assert result.exit_code == 0
    # Rich output should say DRY-RUN
    assert "DRY-RUN" in result.output


# ---------------------------------------------------------------------------
# Exit code 1 — ambiguous / unresolvable handle
# ---------------------------------------------------------------------------


def test_ambiguous_handle_exit1() -> None:
    """Ambiguous mission handle → exit 1."""
    mock_ambig = AmbiguousHandleError(
        handle="dup",
        candidates=[
            ResolvedMission(
                mission_id=FAKE_MISSION_ID,
                mission_slug=FAKE_SLUG,
                mid8=FAKE_MID8,
                feature_dir=Path("/fake/kitty-specs") / FAKE_SLUG,
            )
        ],
    )

    with (
        patch(
            "specify_cli.cli.commands.agent_retrospect.locate_project_root",
            return_value=Path("/fake/root"),
        ),
        patch(
            "specify_cli.cli.commands.agent_retrospect.resolve_mission_handle",
            side_effect=SystemExit(2),
        ),
    ):
        result = runner.invoke(app, ["retrospect", "synthesize", "--mission", "dup"])

    # Contract: exit 1 for unresolvable (resolve_mission_handle calls sys.exit(2),
    # the command catches SystemExit and re-raises typer.Exit(1))
    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# Exit code 3 — missing retrospective record
# ---------------------------------------------------------------------------


def test_missing_record_exit3() -> None:
    """Missing retrospective.yaml → exit 3 (record not found)."""
    result = _patched_invoke(
        ["retrospect", "synthesize", "--mission", "01KQ6YEG"],
        read_record_side_effect=FileNotFoundError("not found"),
    )
    assert result.exit_code == 3


def test_malformed_record_exit3() -> None:
    """Malformed retrospective.yaml (SchemaError) → exit 3."""
    from specify_cli.retrospective.reader import SchemaError

    result = _patched_invoke(
        ["retrospect", "synthesize", "--mission", "01KQ6YEG"],
        read_record_side_effect=SchemaError("bad schema"),
    )
    assert result.exit_code == 3


def test_yaml_parse_error_exit3() -> None:
    """Invalid YAML (YAMLParseError) → exit 3."""
    from specify_cli.retrospective.reader import YAMLParseError

    result = _patched_invoke(
        ["retrospect", "synthesize", "--mission", "01KQ6YEG"],
        read_record_side_effect=YAMLParseError("bad yaml"),
    )
    assert result.exit_code == 3


def test_io_error_exit2() -> None:
    """OS-level I/O error reading retrospective → exit 2."""
    result = _patched_invoke(
        ["retrospect", "synthesize", "--mission", "01KQ6YEG"],
        read_record_side_effect=OSError("permission denied"),
    )
    assert result.exit_code == 2


# ---------------------------------------------------------------------------
# Exit code 4 — conflict batch with --apply
# ---------------------------------------------------------------------------


def test_conflict_batch_apply_exit4() -> None:
    """Conflict batch with --apply → exit 4; nothing applied."""
    result = _patched_invoke(
        ["retrospect", "synthesize", "--mission", "01KQ6YEG", "--apply"],
        result=_conflict_result(),
    )
    assert result.exit_code == 4


# ---------------------------------------------------------------------------
# Exit code 5 — stale evidence / invalid_payload rejections with --apply
# ---------------------------------------------------------------------------


def test_stale_evidence_apply_exit5() -> None:
    """Stale evidence with --apply → exit 5."""
    result = _patched_invoke(
        ["retrospect", "synthesize", "--mission", "01KQ6YEG", "--apply"],
        result=_stale_result(),
    )
    assert result.exit_code == 5


def test_invalid_payload_apply_exit5() -> None:
    """invalid_payload rejection with --apply → exit 5."""
    inv_result = SynthesisResult(
        dry_run=False,
        planned=[PLANNED_APP],
        applied=[],
        conflicts=[],
        rejected=[INVALID_REJECTION],
        events_emitted=[],
    )
    result = _patched_invoke(
        ["retrospect", "synthesize", "--mission", "01KQ6YEG", "--apply"],
        result=inv_result,
    )
    assert result.exit_code == 5


def test_apply_success_exit0() -> None:
    """Successful --apply (no conflicts/rejections) → exit 0."""
    result = _patched_invoke(
        ["retrospect", "synthesize", "--mission", "01KQ6YEG", "--apply"],
        result=_good_result(dry_run=False),
    )
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# JSON output schema
# ---------------------------------------------------------------------------


def test_json_output_schema() -> None:
    """--json output matches expected envelope schema."""
    result = _patched_invoke(
        ["retrospect", "synthesize", "--mission", "01KQ6YEG", "--json"],
        result=_good_result(dry_run=True),
    )
    assert result.exit_code == 0

    envelope = json.loads(result.output)
    assert envelope["schema_version"] == "1"
    assert envelope["command"] == "agent.retrospect.synthesize"
    assert "generated_at" in envelope
    assert envelope["dry_run"] is True
    assert "result" in envelope

    r = envelope["result"]
    assert "dry_run" in r
    assert "planned" in r
    assert "applied" in r
    assert "conflicts" in r
    assert "rejected" in r
    assert "events_emitted" in r


def test_json_envelope_apply_field() -> None:
    """dry_run field in JSON envelope is False when --apply is passed."""
    result = _patched_invoke(
        ["retrospect", "synthesize", "--mission", "01KQ6YEG", "--apply", "--json"],
        result=_good_result(dry_run=False),
    )
    assert result.exit_code == 0
    envelope = json.loads(result.output)
    assert envelope["dry_run"] is False


# ---------------------------------------------------------------------------
# Rich / JSON informational equivalence (CHK034)
# ---------------------------------------------------------------------------


def test_rich_json_informational_equivalence() -> None:
    """Rich rendering and JSON result carry the same counts and key fields.

    Asserts:
    - planned count matches between Rich summary line and JSON result
    - applied count matches
    - conflicts count matches
    - rejected count matches
    """
    synth_result = _good_result(dry_run=True)

    # Capture Rich output
    rich_result = _patched_invoke(
        ["retrospect", "synthesize", "--mission", "01KQ6YEG"],
        result=synth_result,
    )
    assert rich_result.exit_code == 0

    # Capture JSON output
    json_result = _patched_invoke(
        ["retrospect", "synthesize", "--mission", "01KQ6YEG", "--json"],
        result=synth_result,
    )
    assert json_result.exit_code == 0

    envelope = json.loads(json_result.output)
    r = envelope["result"]

    # Counts from JSON
    json_planned = len(r["planned"])
    json_applied = len(r["applied"])
    json_conflicts = len(r["conflicts"])
    json_rejected = len(r["rejected"])

    # Verify JSON counts match what was in the result
    assert json_planned == len(synth_result.planned)
    assert json_applied == len(synth_result.applied)
    assert json_conflicts == len(synth_result.conflicts)
    assert json_rejected == len(synth_result.rejected)

    # Verify Rich output summary line contains the same counts
    rich_output = rich_result.output
    assert f"planned={json_planned}" in rich_output
    assert f"applied={json_applied}" in rich_output
    assert f"conflicts={json_conflicts}" in rich_output
    assert f"rejected={json_rejected}" in rich_output


def test_rich_json_equivalence_with_conflicts() -> None:
    """Conflict case: Rich and JSON both surface the same conflict count."""
    conflict_res = _conflict_result()

    rich_result = _patched_invoke(
        ["retrospect", "synthesize", "--mission", "01KQ6YEG", "--apply"],
        result=conflict_res,
    )
    json_result = _patched_invoke(
        ["retrospect", "synthesize", "--mission", "01KQ6YEG", "--apply", "--json"],
        result=conflict_res,
    )

    envelope = json.loads(json_result.output)
    json_conflicts = len(envelope["result"]["conflicts"])
    assert json_conflicts == 1
    assert f"conflicts={json_conflicts}" in rich_result.output


# ---------------------------------------------------------------------------
# Proposal-id filter
# ---------------------------------------------------------------------------


def test_proposal_id_filter_passed_to_apply_proposals() -> None:
    """--proposal-id flag restricts the approved_proposal_ids set."""
    root = Path("/fake/root")
    resolved = _make_resolved_mission()

    stub_record = MagicMock()
    stub_record.proposals = []

    with (
        patch(
            "specify_cli.cli.commands.agent_retrospect.locate_project_root",
            return_value=root,
        ),
        patch(
            "specify_cli.cli.commands.agent_retrospect.resolve_mission_handle",
            return_value=resolved,
        ),
        patch(
            "specify_cli.cli.commands.agent_retrospect.read_record",
            return_value=stub_record,
        ),
        patch(
            "specify_cli.cli.commands.agent_retrospect.apply_proposals",
            return_value=_good_result(),
        ) as mock_apply,
    ):
        result = runner.invoke(
            app,
            [
                "retrospect", "synthesize",
                "--mission", "01KQ6YEG",
                "--proposal-id", FAKE_PROPOSAL_ID_A,
                "--proposal-id", FAKE_PROPOSAL_ID_B,
            ],
            catch_exceptions=False,
        )

    assert result.exit_code == 0
    call_kwargs = mock_apply.call_args.kwargs
    assert call_kwargs["approved_proposal_ids"] == {
        FAKE_PROPOSAL_ID_A,
        FAKE_PROPOSAL_ID_B,
    }
    assert call_kwargs["dry_run"] is True  # default is dry-run


def test_dry_run_is_true_by_default_in_apply_call() -> None:
    """apply_proposals is called with dry_run=True when --apply is not passed."""
    root = Path("/fake/root")
    resolved = _make_resolved_mission()

    stub_record = MagicMock()
    stub_record.proposals = []

    with (
        patch(
            "specify_cli.cli.commands.agent_retrospect.locate_project_root",
            return_value=root,
        ),
        patch(
            "specify_cli.cli.commands.agent_retrospect.resolve_mission_handle",
            return_value=resolved,
        ),
        patch(
            "specify_cli.cli.commands.agent_retrospect.read_record",
            return_value=stub_record,
        ),
        patch(
            "specify_cli.cli.commands.agent_retrospect.apply_proposals",
            return_value=_good_result(dry_run=True),
        ) as mock_apply,
    ):
        result = runner.invoke(
            app,
            ["retrospect", "synthesize", "--mission", "01KQ6YEG"],
            catch_exceptions=False,
        )

    assert result.exit_code == 0
    assert mock_apply.call_args.kwargs["dry_run"] is True


def test_apply_flag_sets_dry_run_false() -> None:
    """apply_proposals is called with dry_run=False when --apply is passed."""
    root = Path("/fake/root")
    resolved = _make_resolved_mission()

    stub_record = MagicMock()
    stub_record.proposals = []

    with (
        patch(
            "specify_cli.cli.commands.agent_retrospect.locate_project_root",
            return_value=root,
        ),
        patch(
            "specify_cli.cli.commands.agent_retrospect.resolve_mission_handle",
            return_value=resolved,
        ),
        patch(
            "specify_cli.cli.commands.agent_retrospect.read_record",
            return_value=stub_record,
        ),
        patch(
            "specify_cli.cli.commands.agent_retrospect.apply_proposals",
            return_value=_good_result(dry_run=False),
        ) as mock_apply,
    ):
        result = runner.invoke(
            app,
            ["retrospect", "synthesize", "--mission", "01KQ6YEG", "--apply"],
            catch_exceptions=False,
        )

    assert result.exit_code == 0
    assert mock_apply.call_args.kwargs["dry_run"] is False


# ---------------------------------------------------------------------------
# actor-id flag
# ---------------------------------------------------------------------------


def test_actor_id_forwarded() -> None:
    """--actor-id overrides the actor passed to apply_proposals."""
    root = Path("/fake/root")
    resolved = _make_resolved_mission()

    stub_record = MagicMock()
    stub_record.proposals = []

    with (
        patch(
            "specify_cli.cli.commands.agent_retrospect.locate_project_root",
            return_value=root,
        ),
        patch(
            "specify_cli.cli.commands.agent_retrospect.resolve_mission_handle",
            return_value=resolved,
        ),
        patch(
            "specify_cli.cli.commands.agent_retrospect.read_record",
            return_value=stub_record,
        ),
        patch(
            "specify_cli.cli.commands.agent_retrospect.apply_proposals",
            return_value=_good_result(),
        ) as mock_apply,
    ):
        runner.invoke(
            app,
            ["retrospect", "synthesize", "--mission", "01KQ6YEG", "--actor-id", "my-agent"],
            catch_exceptions=False,
        )

    actor = mock_apply.call_args.kwargs["actor"]
    assert actor.id == "my-agent"
    assert actor.kind == "agent"


# ---------------------------------------------------------------------------
# json-out flag
# ---------------------------------------------------------------------------


def test_json_out_writes_file(tmp_path: Path) -> None:
    """--json-out writes the JSON envelope to the specified path."""
    out_file = tmp_path / "out" / "plan.json"

    result = _patched_invoke(
        ["retrospect", "synthesize", "--mission", "01KQ6YEG", "--json-out", str(out_file)],
        result=_good_result(dry_run=True),
    )
    assert result.exit_code == 0
    assert out_file.exists()
    envelope = json.loads(out_file.read_text())
    assert envelope["schema_version"] == "1"
    assert envelope["command"] == "agent.retrospect.synthesize"
