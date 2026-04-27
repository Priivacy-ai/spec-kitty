"""Tolerance tests for the cross-mission summary reducer (WP09 / T047).

Fixture corpus mixes all five tolerance categories:
- rich (full findings + proposals)
- brief (completed, all lists empty)
- skipped (status=skipped with skip_reason)
- missing/legacy (no retrospective.yaml, mission started before tranche)
- missing/in_flight (no retrospective.yaml, mission not yet terminal)
- missing/terminus_no_retrospective (no retrospective.yaml, mission terminal but no record)
- malformed (file exists but corrupt YAML or schema failure)

All five categories must appear in the right counts and malformed[] must carry
structured reasons.  The reducer must NEVER abort on any of these inputs.
"""

from __future__ import annotations

import json
import time
from datetime import date
from pathlib import Path

import pytest

from specify_cli.retrospective.summary import (
    MalformedSummaryEntry,
    SummarySnapshot,
    build_summary,
)

# ---------------------------------------------------------------------------
# ULID helpers and shared YAML templates
# ---------------------------------------------------------------------------

MISSION_ID_1 = "01KQ6YEGT4YBZ3GZF7X680KQ3V"
MISSION_ID_2 = "01KQ6YEGT4YBZ3GZF7X680KQAA"
MISSION_ID_3 = "01KQ6YEGT4YBZ3GZF7X680KQBB"
MISSION_ID_4 = "01KQ6YEGT4YBZ3GZF7X680KQCC"


def _make_completed_yaml(
    mission_id: str = MISSION_ID_1,
    slug: str = "rich-mission",
    started: str = "2026-04-27T10:00:00+00:00",
    completed: str = "2026-04-27T11:00:00+00:00",
    not_helpful_urn: str = "glossary:term:alpha",
    gaps_urn: str = "glossary:term:beta",
    proposal_status: str = "accepted",
) -> str:
    return f"""\
schema_version: "1"
mission:
  mission_id: {mission_id}
  mid8: {mission_id[:8]}
  mission_slug: {slug}
  mission_type: software-dev
  mission_started_at: "{started}"
  mission_completed_at: "{completed}"
mode:
  value: human_in_command
  source_signal:
    kind: charter_override
    evidence: "charter:mode-policy:hic-default"
status: completed
started_at: "{started}"
completed_at: "{completed}"
actor:
  kind: human
  id: rob@robshouse.net
  profile_id: null
helped: []
not_helpful:
  - id: nh-001
    target:
      kind: glossary_term
      urn: "{not_helpful_urn}"
    note: "not helpful note"
    provenance:
      source_mission_id: {mission_id}
      evidence_event_ids: ["{mission_id}"]
      actor:
        kind: agent
        id: facilitator
        profile_id: retrospective-facilitator
      captured_at: "{completed}"
gaps:
  - id: gap-001
    target:
      kind: glossary_term
      urn: "{gaps_urn}"
    note: "gap note"
    provenance:
      source_mission_id: {mission_id}
      evidence_event_ids: ["{mission_id}"]
      actor:
        kind: agent
        id: facilitator
        profile_id: retrospective-facilitator
      captured_at: "{completed}"
proposals:
  - id: {mission_id}
    kind: add_glossary_term
    payload:
      kind: add_glossary_term
      term_key: newterm
      definition: "A new term"
      definition_hash: "abc123"
      related_terms: []
    rationale: "Missing in glossary"
    state:
      status: {proposal_status}
      decided_at: "{completed}"
      decided_by:
        kind: human
        id: rob@robshouse.net
        profile_id: null
      apply_attempts: []
    provenance:
      source_mission_id: {mission_id}
      source_evidence_event_ids: ["{mission_id}"]
      authored_by:
        kind: agent
        id: facilitator
        profile_id: retrospective-facilitator
      approved_by: null
provenance:
  authored_by:
    kind: agent
    id: claude-opus-4-7
    profile_id: retrospective-facilitator
  runtime_version: "3.2.0"
  written_at: "{completed}"
  schema_version: "1"
"""


def _make_brief_yaml(
    mission_id: str = MISSION_ID_2,
    slug: str = "brief-mission",
    started: str = "2026-04-27T10:00:00+00:00",
    completed: str = "2026-04-27T11:00:00+00:00",
) -> str:
    return f"""\
schema_version: "1"
mission:
  mission_id: {mission_id}
  mid8: {mission_id[:8]}
  mission_slug: {slug}
  mission_type: software-dev
  mission_started_at: "{started}"
  mission_completed_at: "{completed}"
mode:
  value: human_in_command
  source_signal:
    kind: charter_override
    evidence: "charter:mode-policy:hic-default"
status: completed
started_at: "{started}"
completed_at: "{completed}"
actor:
  kind: human
  id: rob@robshouse.net
  profile_id: null
helped: []
not_helpful: []
gaps: []
proposals: []
provenance:
  authored_by:
    kind: agent
    id: claude-opus-4-7
    profile_id: retrospective-facilitator
  runtime_version: "3.2.0"
  written_at: "{completed}"
  schema_version: "1"
"""


def _make_skipped_yaml(
    mission_id: str = MISSION_ID_3,
    slug: str = "skipped-mission",
    started: str = "2026-04-27T10:00:00+00:00",
    completed: str = "2026-04-27T11:00:00+00:00",
    skip_reason: str = "Operator elected to skip (insufficient evidence)",
) -> str:
    return f"""\
schema_version: "1"
mission:
  mission_id: {mission_id}
  mid8: {mission_id[:8]}
  mission_slug: {slug}
  mission_type: software-dev
  mission_started_at: "{started}"
  mission_completed_at: "{completed}"
mode:
  value: human_in_command
  source_signal:
    kind: charter_override
    evidence: "charter:mode-policy:hic-default"
status: skipped
started_at: "{started}"
completed_at: "{completed}"
skip_reason: "{skip_reason}"
actor:
  kind: human
  id: rob@robshouse.net
  profile_id: null
helped: []
not_helpful: []
gaps: []
proposals: []
provenance:
  authored_by:
    kind: agent
    id: claude-opus-4-7
    profile_id: retrospective-facilitator
  runtime_version: "3.2.0"
  written_at: "{completed}"
  schema_version: "1"
"""


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------


def _build_corpus(tmp_path: Path) -> Path:
    """Build a corpus with all five tolerance categories.

    Directory layout:
      .kittify/missions/
        <MISSION_ID_1>/retrospective.yaml  -- rich (completed, findings + proposal)
        <MISSION_ID_2>/retrospective.yaml  -- brief (completed, all lists empty)
        <MISSION_ID_3>/retrospective.yaml  -- skipped
        legacy-mission-01KQ0000/           -- missing/legacy (no retro, old started_at)
        inflight-01KQ0001/                 -- missing/in_flight (no retro, in_progress)
        terminus-01KQ0002/                 -- missing/terminus_no_retro (no retro, done)
        malformed-01KQ0003/retrospective.yaml  -- malformed (corrupt YAML)
        malformed-01KQ0004/retrospective.yaml  -- malformed (schema failure)
    """
    missions_root = tmp_path / ".kittify" / "missions"
    missions_root.mkdir(parents=True)

    # Rich record
    rich_dir = missions_root / MISSION_ID_1
    rich_dir.mkdir()
    (rich_dir / "retrospective.yaml").write_text(
        _make_completed_yaml(), encoding="utf-8"
    )

    # Brief record
    brief_dir = missions_root / MISSION_ID_2
    brief_dir.mkdir()
    (brief_dir / "retrospective.yaml").write_text(
        _make_brief_yaml(), encoding="utf-8"
    )

    # Skipped record
    skipped_dir = missions_root / MISSION_ID_3
    skipped_dir.mkdir()
    (skipped_dir / "retrospective.yaml").write_text(
        _make_skipped_yaml(), encoding="utf-8"
    )

    # Missing / legacy: mission started before tranche cutoff (2026-04-27)
    legacy_dir = missions_root / "legacy-mission-01KQ0000"
    legacy_dir.mkdir()
    (legacy_dir / "meta.json").write_text(
        json.dumps({
            "mission_slug": "legacy-mission",
            "mission_started_at": "2026-01-01T00:00:00+00:00",
            "status": "done",
        }),
        encoding="utf-8",
    )
    # No retrospective.yaml

    # Missing / in_flight: no retro, mission still in progress
    inflight_dir = missions_root / "inflight-01KQ0001"
    inflight_dir.mkdir()
    (inflight_dir / "meta.json").write_text(
        json.dumps({
            "mission_slug": "inflight-mission",
            "mission_started_at": "2026-04-27T08:00:00+00:00",
            "status": "in_progress",
        }),
        encoding="utf-8",
    )
    # No retrospective.yaml

    # Missing / terminus_no_retro: no retro, mission is done
    terminus_dir = missions_root / "terminus-01KQ0002"
    terminus_dir.mkdir()
    (terminus_dir / "meta.json").write_text(
        json.dumps({
            "mission_slug": "terminus-mission",
            "mission_started_at": "2026-04-27T08:00:00+00:00",
            "status": "done",
        }),
        encoding="utf-8",
    )
    # No retrospective.yaml

    # Malformed: corrupt YAML
    mf1_dir = missions_root / "malformed-01KQ0003"
    mf1_dir.mkdir()
    (mf1_dir / "retrospective.yaml").write_text(
        "{ not valid yaml: [unclosed\n", encoding="utf-8"
    )

    # Malformed: schema failure (missing required field)
    mf2_dir = missions_root / "malformed-01KQ0004"
    mf2_dir.mkdir()
    (mf2_dir / "retrospective.yaml").write_text(
        "schema_version: '1'\nmission_id: INVALID\n", encoding="utf-8"
    )

    return tmp_path


# ---------------------------------------------------------------------------
# Tests — tolerance categories
# ---------------------------------------------------------------------------


class TestToleranceCategories:
    """All five tolerance categories are handled correctly."""

    def test_rich_record_counted_as_completed(self, tmp_path: Path) -> None:
        project = _build_corpus(tmp_path)
        snapshot = build_summary(project_path=project)
        assert snapshot.completed_count >= 2  # rich + brief

    def test_skipped_record_counted(self, tmp_path: Path) -> None:
        project = _build_corpus(tmp_path)
        snapshot = build_summary(project_path=project)
        assert snapshot.skipped_count == 1

    def test_legacy_mission_counted(self, tmp_path: Path) -> None:
        project = _build_corpus(tmp_path)
        snapshot = build_summary(project_path=project)
        assert snapshot.legacy_no_retro_count == 1

    def test_in_flight_mission_counted(self, tmp_path: Path) -> None:
        project = _build_corpus(tmp_path)
        snapshot = build_summary(project_path=project)
        assert snapshot.in_flight_count == 1

    def test_terminus_no_retro_counted(self, tmp_path: Path) -> None:
        project = _build_corpus(tmp_path)
        snapshot = build_summary(project_path=project)
        assert snapshot.terminus_no_retro_count == 1

    def test_malformed_records_in_list(self, tmp_path: Path) -> None:
        project = _build_corpus(tmp_path)
        snapshot = build_summary(project_path=project)
        assert len(snapshot.malformed) == 2

    def test_malformed_entries_have_path_and_reason(self, tmp_path: Path) -> None:
        project = _build_corpus(tmp_path)
        snapshot = build_summary(project_path=project)
        for entry in snapshot.malformed:
            assert entry.path  # non-empty path
            assert entry.reason  # non-empty reason

    def test_reducer_never_crashes(self, tmp_path: Path) -> None:
        """The reducer must always return a SummarySnapshot — never raise."""
        project = _build_corpus(tmp_path)
        snapshot = build_summary(project_path=project)
        assert isinstance(snapshot, SummarySnapshot)

    def test_total_mission_count(self, tmp_path: Path) -> None:
        """All mission directories contribute to mission_count."""
        project = _build_corpus(tmp_path)
        snapshot = build_summary(project_path=project)
        # 3 retro records + 3 missing + 2 malformed = 8 missions
        assert snapshot.mission_count == 8

    def test_not_helpful_top_populated(self, tmp_path: Path) -> None:
        """Rich record contributes to not_helpful_top."""
        project = _build_corpus(tmp_path)
        snapshot = build_summary(project_path=project)
        # Rich record has one not_helpful finding with urn="glossary:term:alpha"
        assert len(snapshot.not_helpful_top) >= 1
        urns = [tc.urn for tc in snapshot.not_helpful_top]
        assert "glossary:term:alpha" in urns

    def test_skip_reason_top_populated(self, tmp_path: Path) -> None:
        """Skipped record's reason appears in skip_reasons_top."""
        project = _build_corpus(tmp_path)
        snapshot = build_summary(project_path=project)
        reasons = [rc.reason for rc in snapshot.skip_reasons_top]
        assert "Operator elected to skip (insufficient evidence)" in reasons

    def test_proposal_acceptance_total(self, tmp_path: Path) -> None:
        """Rich record's proposal contributes to proposal_acceptance.total."""
        project = _build_corpus(tmp_path)
        snapshot = build_summary(project_path=project)
        assert snapshot.proposal_acceptance.total == 1
        assert snapshot.proposal_acceptance.accepted == 1

    def test_empty_project_no_missions_dir(self, tmp_path: Path) -> None:
        """Empty .kittify/missions/ dir → zero counts, no crash."""
        (tmp_path / ".kittify" / "missions").mkdir(parents=True)
        snapshot = build_summary(project_path=tmp_path)
        assert snapshot.mission_count == 0
        assert len(snapshot.malformed) == 0

    def test_missing_missions_dir(self, tmp_path: Path) -> None:
        """No .kittify/missions/ at all → zero counts, no crash."""
        (tmp_path / ".kittify").mkdir()
        snapshot = build_summary(project_path=tmp_path)
        assert snapshot.mission_count == 0


# ---------------------------------------------------------------------------
# Tests — top-N determinism
# ---------------------------------------------------------------------------


class TestTopNDeterminism:
    """Top-N is sorted deterministically (desc count, asc urn/key tiebreak)."""

    def test_top_n_sorted_desc_by_count(self, tmp_path: Path) -> None:
        missions_root = tmp_path / ".kittify" / "missions"
        missions_root.mkdir(parents=True)

        # Two missions, each with different not_helpful URNs and one shared URN
        # so the shared one has count=2.
        mission_ids = [
            "01KQ6YEGT4YBZ3GZF7X680KQCC",
            "01KQ6YEGT4YBZ3GZF7X680KQDD",
        ]
        for i, mid in enumerate(mission_ids):
            d = missions_root / mid
            d.mkdir()
            (d / "retrospective.yaml").write_text(
                _make_completed_yaml(
                    mission_id=mid,
                    slug=f"m{i}",
                    not_helpful_urn="glossary:term:shared",  # same URN → count=2
                    gaps_urn=f"glossary:term:unique{i}",
                ),
                encoding="utf-8",
            )

        snapshot = build_summary(project_path=tmp_path)
        assert len(snapshot.not_helpful_top) >= 1
        assert snapshot.not_helpful_top[0].urn == "glossary:term:shared"
        assert snapshot.not_helpful_top[0].count == 2

    def test_tie_broken_by_urn_ascending(self, tmp_path: Path) -> None:
        """When two URNs have equal count, urn ascending wins."""
        missions_root = tmp_path / ".kittify" / "missions"
        missions_root.mkdir(parents=True)

        # One mission with two not_helpful findings, each count=1
        # → tie broken by URN alphabetically
        # We test by reading multiple missions each with one unique URN
        mission_ids = [
            ("01KQ6YEGT4YBZ3GZF7X680KQEE", "glossary:term:zz"),
            ("01KQ6YEGT4YBZ3GZF7X680KQFF", "glossary:term:aa"),
        ]
        for mid, urn in mission_ids:
            d = missions_root / mid
            d.mkdir()
            (d / "retrospective.yaml").write_text(
                _make_completed_yaml(
                    mission_id=mid,
                    slug=f"m-{mid[:8].lower()}",
                    not_helpful_urn=urn,
                    gaps_urn="glossary:term:irrelevant",
                ),
                encoding="utf-8",
            )

        snapshot = build_summary(project_path=tmp_path)
        urns = [tc.urn for tc in snapshot.not_helpful_top]
        aa_idx = urns.index("glossary:term:aa")
        zz_idx = urns.index("glossary:term:zz")
        assert aa_idx < zz_idx  # aa before zz (ascending tiebreak)

    def test_limit_truncates_top_n(self, tmp_path: Path) -> None:
        """--limit 2 truncates top-N to 2 entries."""
        missions_root = tmp_path / ".kittify" / "missions"
        missions_root.mkdir(parents=True)

        # 5 missions, each with a unique not_helpful URN
        base = "01KQ6YEGT4YBZ3GZF7X680KQ"
        for i in range(5):
            mid = f"{base}{i:02d}AAAAAAA"[:26]
            # Ensure valid ULID: pad to 26 chars
            mid = (mid + "A" * 26)[:26]
            d = missions_root / mid
            d.mkdir()
            (d / "retrospective.yaml").write_text(
                _make_completed_yaml(
                    mission_id=mid,
                    slug=f"mission-{i}",
                    not_helpful_urn=f"glossary:term:item{i:02d}",
                    gaps_urn="glossary:term:gap",
                ),
                encoding="utf-8",
            )

        snapshot = build_summary(project_path=tmp_path, limit_top_n=2)
        assert len(snapshot.not_helpful_top) <= 2


# ---------------------------------------------------------------------------
# Tests — --since filter
# ---------------------------------------------------------------------------


class TestSinceFilter:
    """--since YYYY-MM-DD filters out earlier missions."""

    def test_since_excludes_old_missions(self, tmp_path: Path) -> None:
        missions_root = tmp_path / ".kittify" / "missions"
        missions_root.mkdir(parents=True)

        # One 2025 mission (should be excluded), one 2026 mission (included)
        old_mid = "01KQ6YEGT4YBZ3GZF7X680KQGG"
        new_mid = "01KQ6YEGT4YBZ3GZF7X680KQHH"

        for mid, started, completed in [
            (old_mid, "2025-06-01T10:00:00+00:00", "2025-06-01T11:00:00+00:00"),
            (new_mid, "2026-04-01T10:00:00+00:00", "2026-04-01T11:00:00+00:00"),
        ]:
            d = missions_root / mid
            d.mkdir()
            (d / "retrospective.yaml").write_text(
                _make_completed_yaml(
                    mission_id=mid,
                    slug=f"m-{mid[:8].lower()}",
                    started=started,
                    completed=completed,
                ),
                encoding="utf-8",
            )

        # Filter to 2026-01-01 and after
        snapshot = build_summary(
            project_path=tmp_path,
            since=date(2026, 1, 1),
        )
        assert snapshot.completed_count == 1

    def test_since_includes_boundary_date(self, tmp_path: Path) -> None:
        """Missions started exactly on the --since date are included."""
        missions_root = tmp_path / ".kittify" / "missions"
        missions_root.mkdir(parents=True)

        mid = "01KQ6YEGT4YBZ3GZF7X680KQJJ"
        d = missions_root / mid
        d.mkdir()
        (d / "retrospective.yaml").write_text(
            _make_completed_yaml(
                mission_id=mid,
                slug="boundary-mission",
                started="2026-01-01T00:00:00+00:00",
                completed="2026-01-01T01:00:00+00:00",
            ),
            encoding="utf-8",
        )

        snapshot = build_summary(
            project_path=tmp_path,
            since=date(2026, 1, 1),
        )
        assert snapshot.completed_count == 1


# ---------------------------------------------------------------------------
# Tests — 200-mission performance (session-scoped fixture)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def large_corpus(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Build a 200-mission corpus once per test session."""
    tmp_path = tmp_path_factory.mktemp("large_corpus")
    missions_root = tmp_path / ".kittify" / "missions"
    missions_root.mkdir(parents=True)

    # Base ULID prefix — we generate 200 unique ULID-like strings.
    # Real ULIDs are 26 chars; we craft deterministic ones by encoding index.
    for i in range(200):
        # Simple valid ULID-like: pad index into Crockford base32 chars
        suffix = f"{i:026d}".replace("0", "A").replace(
            "1", "B"
        ).replace("2", "C").replace("3", "D").replace("4", "E").replace(
            "5", "F"
        ).replace("6", "G").replace("7", "H").replace("8", "J").replace(
            "9", "K"
        )
        # Use a fixed valid prefix + sequential suffix
        mid = f"01KQ6YEGT4YBZ3GZF7X{i:07d}"[:26]
        # Ensure no invalid ULID chars by using safe chars
        safe_chars = "ABCDEFGHJKMNPQRSTVWXYZ0123456789"
        mid_safe = "".join(
            c if c in safe_chars else "A" for c in mid.upper()
        )
        mid_safe = mid_safe[:26]
        if len(mid_safe) < 26:
            mid_safe = mid_safe + "A" * (26 - len(mid_safe))

        d = missions_root / mid_safe
        d.mkdir(exist_ok=True)
        (d / "retrospective.yaml").write_text(
            _make_completed_yaml(
                mission_id=mid_safe,
                slug=f"perf-mission-{i:04d}",
                not_helpful_urn=f"glossary:term:item{i % 50:02d}",
                gaps_urn=f"glossary:term:gap{i % 20:02d}",
            ),
            encoding="utf-8",
        )

    return tmp_path


def test_200_missions_under_5s(large_corpus: Path) -> None:
    """200-mission corpus completes in < 5 s (NFR-003)."""
    start = time.monotonic()
    snapshot = build_summary(project_path=large_corpus)
    elapsed = time.monotonic() - start
    assert elapsed < 5.0, f"200-mission summary took {elapsed:.2f}s (limit: 5s)"
    assert snapshot.mission_count == 200
    assert snapshot.completed_count == 200
