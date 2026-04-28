"""Integration test: WP05 / NFR-006 — `next` produces paired profile-invocation
lifecycle records at ≥ 95% pairing for ≥ 5 issuances, with orphans observable
via the doctor surface (#843).

The full ``spec-kitty next`` pipeline (mission state machine, runtime engine,
worktrees) is out of scope for this WP — it is exercised exhaustively in
``tests/integration/test_mission_run_command.py``. Here we drive the
``next_cmd`` lifecycle wiring (``_pair_previous_lifecycle_record`` /
``_write_issuance_lifecycle_record``) directly with a synthetic mission
``meta.json`` and a fake ``decide_next`` so the test is hermetic and fast
while covering the full pairing contract:

- ≥ 5 issuances (one orphan, four paired) ⇒ pairing_rate ≥ 0.95 over the
  non-orphan set.
- The orphan is surfaced by ``doctor invocation-pairing`` (CLI typer
  invocation hits the same ``doctor_orphan_report`` helper used by the
  programmatic surface).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest
from typer.testing import CliRunner

from specify_cli.invocation.lifecycle import (
    compute_pairing_rate,
    doctor_orphan_report,
    read_lifecycle_records,
)


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------


@dataclass
class _FakeDecision:
    """Minimal stand-in for ``Decision`` used by the lifecycle wiring."""

    kind: str
    mission_state: str
    action: str | None
    wp_id: str | None


def _setup_mission(repo_root: Path, *, mission_slug: str, mission_id: str) -> Path:
    """Write the minimum ``meta.json`` the lifecycle wiring needs."""
    feature_dir = repo_root / "kitty-specs" / mission_slug
    feature_dir.mkdir(parents=True, exist_ok=True)
    meta_path = feature_dir / "meta.json"
    meta_path.write_text(
        json.dumps(
            {
                "mission_slug": mission_slug,
                "mission_id": mission_id,
                "mission_number": None,
                "mission_type": "software-dev",
                "friendly_name": mission_slug.replace("-", " ").title(),
            }
        ),
        encoding="utf-8",
    )
    return feature_dir


def _drive_issuance_and_advance(
    repo_root: Path,
    *,
    agent: str,
    mission_slug: str,
    decision: _FakeDecision,
    advance_result: str | None,
) -> None:
    """Drive one full `next` cycle through the WP05 lifecycle wiring.

    Mirrors the order in ``next_cmd.next_step``:
      1. (``--result`` set) pair the prior issuance, if any.
      2. ``decide_next`` runs (mocked here — caller supplies ``decision``).
      3. Write the ``started`` record for the current issuance.
    """
    from specify_cli.cli.commands import next_cmd

    if advance_result is not None:
        next_cmd._pair_previous_lifecycle_record(
            agent, mission_slug, advance_result, repo_root
        )
    next_cmd._write_issuance_lifecycle_record(
        agent, mission_slug, repo_root, decision
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestNextLifecycleRecordsPairingRate:
    """≥ 5 issuances, one orphan, ≥ 95% pairing on the non-orphan set."""

    def test_five_issuances_one_orphan_pairing_above_95_percent(
        self, tmp_path: Path
    ) -> None:
        mission_slug = "release-3-2-0a6-tranche-2-test"
        mission_id = "01HMISSIONULID00000000000A"
        _setup_mission(tmp_path, mission_slug=mission_slug, mission_id=mission_id)

        agent = "claude"
        actions = ["implement", "review", "merge", "accept"]
        # Six step-decisions: five proper issuances + one extra so we can
        # leave one as the mid-cycle orphan.
        decisions = [
            _FakeDecision(
                kind="step",
                mission_state=f"mission_step_{i}",
                action=actions[i % len(actions)],
                wp_id=f"WP{(i % 4) + 1:02d}",
            )
            for i in range(6)
        ]

        # Issuance 0 — first cycle, no prior to pair.
        _drive_issuance_and_advance(
            tmp_path,
            agent=agent,
            mission_slug=mission_slug,
            decision=decisions[0],
            advance_result=None,
        )

        # Issuances 1..3 — each cycle pairs the prior issuance with success
        # and emits a fresh `started`. Four pairs total.
        for prior_decision, decision in zip(decisions[:3], decisions[1:4]):
            _ = prior_decision  # readability only
            _drive_issuance_and_advance(
                tmp_path,
                agent=agent,
                mission_slug=mission_slug,
                decision=decision,
                advance_result="success",
            )

        # Issuance 4 — the previous issuance succeeds, this issuance is
        # written but we then SIMULATE the agent crashing mid-cycle by
        # never advancing past it. That leaves issuance 4 as the orphan.
        _drive_issuance_and_advance(
            tmp_path,
            agent=agent,
            mission_slug=mission_slug,
            decision=decisions[4],
            advance_result="success",
        )
        # Issuance 5 NEVER happens — agent crashed.

        records = read_lifecycle_records(tmp_path)

        # Exactly 5 starteds + 4 completions = 9 records.
        starteds = [r for r in records if r.phase == "started"]
        completions = [r for r in records if r.phase in ("completed", "failed")]
        assert len(starteds) == 5
        assert len(completions) == 4

        # Pairing rate ≥ 95% on the non-orphan portion of the set:
        # 4 paired starteds out of (5 - 1 orphan) = 4 expected pairs.
        non_orphan_starteds = len(starteds) - 1
        pair_rate_non_orphan = (
            len(completions) / non_orphan_starteds if non_orphan_starteds else 1.0
        )
        assert pair_rate_non_orphan >= 0.95

        # Overall pairing rate is 4/5 = 0.80 — above the 0.50 sanity floor
        # but below 0.95, by design (we're simulating one orphan).
        overall = compute_pairing_rate(records)
        assert 0.7 <= overall <= 0.9

        # canonical_action_id on every started has the form mission_step::action
        assert all("::" in r.canonical_action_id for r in starteds)

        # The completion partners share the SAME canonical_action_id as
        # their started — id read once at issuance, never re-derived.
        started_ids = [s.canonical_action_id for s in starteds]
        completion_ids = [c.canonical_action_id for c in completions]
        assert set(completion_ids).issubset(set(started_ids))


class TestOrphanListedByDoctor:
    """The orphan from a partial cycle MUST appear in the doctor surface."""

    def test_orphan_listed_by_doctor_helper(self, tmp_path: Path) -> None:
        mission_slug = "release-3-2-0a6-tranche-2-test"
        mission_id = "01HMISSIONULID00000000000B"
        _setup_mission(tmp_path, mission_slug=mission_slug, mission_id=mission_id)

        # Single mid-cycle crash: one started, no completion.
        decision = _FakeDecision(
            kind="step",
            mission_state="implement_step",
            action="implement",
            wp_id="WP01",
        )
        _drive_issuance_and_advance(
            tmp_path,
            agent="claude",
            mission_slug=mission_slug,
            decision=decision,
            advance_result=None,
        )

        report = doctor_orphan_report(tmp_path)
        assert report["orphan_count"] == 1
        orphans = report["orphans"]
        assert isinstance(orphans, list)
        assert orphans[0]["canonical_action_id"] == "implement_step::implement"
        assert orphans[0]["agent"] == "claude"
        assert orphans[0]["mission_id"] == mission_id
        assert orphans[0]["wp_id"] == "WP01"

    def test_orphan_listed_by_doctor_cli_command(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The user-facing ``spec-kitty doctor invocation-pairing`` command."""
        from specify_cli.cli.commands import doctor as doctor_module

        mission_slug = "release-3-2-0a6-tranche-2-test"
        mission_id = "01HMISSIONULID00000000000C"
        _setup_mission(tmp_path, mission_slug=mission_slug, mission_id=mission_id)

        decision = _FakeDecision(
            kind="step",
            mission_state="review_step",
            action="review",
            wp_id="WP02",
        )
        _drive_issuance_and_advance(
            tmp_path,
            agent="claude",
            mission_slug=mission_slug,
            decision=decision,
            advance_result=None,
        )

        # Pin locate_project_root() to our tmp_path so the doctor command
        # reads the lifecycle log we just produced.
        monkeypatch.setattr(
            doctor_module, "locate_project_root", lambda: tmp_path
        )

        runner = CliRunner()
        result = runner.invoke(doctor_module.app, ["invocation-pairing", "--json"])
        assert result.exit_code == 1, result.output  # orphans exist
        payload = json.loads(result.output)
        assert payload["orphan_count"] == 1
        assert payload["orphans"][0]["canonical_action_id"] == "review_step::review"
        assert payload["orphans"][0]["agent"] == "claude"
        assert payload["orphans"][0]["mission_id"] == mission_id


class TestNoIssuanceWhenDecisionIsNotAStep:
    """Decisions that do not issue a public action MUST NOT write `started`."""

    @pytest.mark.parametrize(
        "decision",
        [
            _FakeDecision(kind="terminal", mission_state="done", action=None, wp_id=None),
            _FakeDecision(
                kind="blocked", mission_state="implement", action="implement", wp_id="WP01"
            ),
            _FakeDecision(
                kind="decision_required",
                mission_state="implement",
                action=None,
                wp_id="WP01",
            ),
        ],
    )
    def test_non_step_decisions_do_not_write_started(
        self, tmp_path: Path, decision: _FakeDecision
    ) -> None:
        mission_slug = "release-3-2-0a6-tranche-2-test"
        _setup_mission(
            tmp_path, mission_slug=mission_slug, mission_id="01HMISSIONULID00000000000D"
        )
        _drive_issuance_and_advance(
            tmp_path,
            agent="claude",
            mission_slug=mission_slug,
            decision=decision,
            advance_result=None,
        )
        assert read_lifecycle_records(tmp_path) == []
