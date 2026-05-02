"""Tests for src/specify_cli/audit/engine.py (T023).

8 test cases covering the audit engine scan loop, mission filtering,
determinism, corrupt-JSONL resilience, repo-summary counts, performance,
and empty-scan-root behavior.

Fixture layout (for tests that need identity functions to work):
    tmp_path/               ← repo_root
      kitty-specs/          ← scan_root = tmp_path / "kitty-specs"
        mission-a/
          meta.json         ← {"mission_id": "<valid ULID>", ...}
        mission-b/
          meta.json
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from specify_cli.audit import AuditOptions, RepoAuditReport, run_audit
from specify_cli.audit.serializer import build_report_json

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# A set of distinct valid ULIDs (26 chars, Crockford Base32: 0-9 A-H J-N P-T V-Z)
_ULID_A = "01KQHRB8GCFJAX7HM4ZY52AQGR"
_ULID_B = "01KQHRB9GCFJAX7HM4ZY52AQGR"
_ULID_C = "01KQHRB7GCFJAX7HM4ZY52AQGR"
_ULID_D = "01KQHRC0GCFJAX7HM4ZY52AQGR"
_ULID_E = "01KQHRC1GCFJAX7HM4ZY52AQGR"


def _write_meta(mission_dir: Path, mission_id: str, mission_number: int | None = None) -> None:
    """Write a minimal valid meta.json to the mission directory."""
    mission_dir.mkdir(parents=True, exist_ok=True)
    meta: dict[str, object] = {
        "mission_id": mission_id,
        "mission_slug": mission_dir.name,
        "friendly_name": f"Test mission {mission_dir.name}",
    }
    if mission_number is not None:
        meta["mission_number"] = mission_number
    (mission_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")


def _make_mission(parent: Path, slug: str, mission_id: str, mission_number: int | None = None) -> Path:
    """Create a minimal mission directory with a valid meta.json."""
    mission_dir = parent / slug
    _write_meta(mission_dir, mission_id, mission_number)
    return mission_dir


def _options(tmp_path: Path, *, mission_filter: str | None = None) -> AuditOptions:
    """Create AuditOptions with tmp_path as repo_root and kitty-specs as scan_root."""
    return AuditOptions(
        repo_root=tmp_path,
        scan_root=tmp_path / "kitty-specs",
        mission_filter=mission_filter,
        fail_on=None,
    )


# ---------------------------------------------------------------------------
# Test 1: test_scan_visits_all_missions
# ---------------------------------------------------------------------------


def test_scan_visits_all_missions(tmp_path: Path) -> None:
    """Engine visits all mission directories and returns them sorted by slug."""
    specs_dir = tmp_path / "kitty-specs"
    _make_mission(specs_dir, "mission-a", _ULID_A)
    _make_mission(specs_dir, "mission-b", _ULID_B)
    _make_mission(specs_dir, "mission-c", _ULID_C)

    report = run_audit(_options(tmp_path))

    assert isinstance(report, RepoAuditReport)
    slugs = [m.mission_slug for m in report.missions]
    assert slugs == ["mission-a", "mission-b", "mission-c"]
    assert report.repo_summary["total_missions"] == 3


# ---------------------------------------------------------------------------
# Test 2: test_fixture_dir_substitution
# ---------------------------------------------------------------------------


def test_fixture_dir_substitution(tmp_path: Path, tmp_path_factory: pytest.TempPathFactory) -> None:
    """scan_root override causes the engine to scan a different directory."""
    # Primary fixture: tmp_path/kitty-specs/fixture-mission
    specs_dir = tmp_path / "kitty-specs"
    _make_mission(specs_dir, "fixture-mission", _ULID_A)

    # Engine with default scan_root should find fixture-mission
    report_a = run_audit(_options(tmp_path))
    assert any(m.mission_slug == "fixture-mission" for m in report_a.missions)

    # Alternate fixture in a different tmp directory
    alt_root = tmp_path_factory.mktemp("alt")
    alt_specs = alt_root / "kitty-specs"
    _make_mission(alt_specs, "alt-mission", _ULID_B)

    # Override scan_root to alt_specs — should find alt-mission, NOT fixture-mission
    alt_options = AuditOptions(
        repo_root=alt_root,
        scan_root=alt_specs,
        mission_filter=None,
        fail_on=None,
    )
    report_b = run_audit(alt_options)
    slugs_b = [m.mission_slug for m in report_b.missions]
    assert "alt-mission" in slugs_b
    assert "fixture-mission" not in slugs_b


# ---------------------------------------------------------------------------
# Test 3: test_mission_filter_scoping
# ---------------------------------------------------------------------------


def test_mission_filter_scoping(tmp_path: Path) -> None:
    """--mission filter restricts the scan to exactly one mission."""
    specs_dir = tmp_path / "kitty-specs"
    _make_mission(specs_dir, "001-alpha", _ULID_A, mission_number=1)
    _make_mission(specs_dir, "002-beta", _ULID_B, mission_number=2)
    _make_mission(specs_dir, "003-gamma", _ULID_C, mission_number=3)

    # Filter by full slug — should return only 001-alpha
    report = run_audit(
        AuditOptions(
            repo_root=tmp_path,
            scan_root=tmp_path / "kitty-specs",
            mission_filter="001-alpha",
            fail_on=None,
        )
    )

    assert len(report.missions) == 1
    assert report.missions[0].mission_slug == "001-alpha"
    assert report.repo_summary["total_missions"] == 1


# ---------------------------------------------------------------------------
# Test 4: test_determinism
# ---------------------------------------------------------------------------


def test_determinism(tmp_path: Path) -> None:
    """Two successive run_audit() calls produce byte-identical JSON output."""
    specs_dir = tmp_path / "kitty-specs"
    _make_mission(specs_dir, "mission-x", _ULID_A, mission_number=1)
    _make_mission(specs_dir, "mission-y", _ULID_B, mission_number=2)
    _make_mission(specs_dir, "mission-z", _ULID_C, mission_number=3)

    opts = _options(tmp_path)
    report_1 = run_audit(opts)
    report_2 = run_audit(opts)

    json_1 = build_report_json(report_1)
    json_2 = build_report_json(report_2)

    assert json_1 == json_2, "Two identical run_audit() calls produced different JSON"


# ---------------------------------------------------------------------------
# Test 5: test_corrupt_jsonl_does_not_crash_engine
# ---------------------------------------------------------------------------


def test_corrupt_jsonl_does_not_crash_engine(tmp_path: Path) -> None:
    """Engine handles a corrupt status.events.jsonl without raising.

    The corrupt line causes CORRUPT_JSONL to appear in findings.
    SNAPSHOT_DRIFT must NOT appear because skip_drift=True was applied.
    """
    specs_dir = tmp_path / "kitty-specs"
    mission_dir = specs_dir / "bad-events-mission"
    _write_meta(mission_dir, _ULID_A)

    # Write a valid status.json (minimal) so the drift check would normally run
    (mission_dir / "status.json").write_text(
        json.dumps({"wps": {}}) + "\n", encoding="utf-8"
    )

    # Write a corrupt status.events.jsonl
    events_path = mission_dir / "status.events.jsonl"
    events_path.write_text("THIS IS NOT JSON {{{\n", encoding="utf-8")

    report = run_audit(_options(tmp_path))

    assert len(report.missions) == 1
    result = report.missions[0]
    codes = {f.code for f in result.findings}

    assert "CORRUPT_JSONL" in codes, f"Expected CORRUPT_JSONL in {codes}"
    assert "SNAPSHOT_DRIFT" not in codes, f"SNAPSHOT_DRIFT should be suppressed, got {codes}"


# ---------------------------------------------------------------------------
# Test 6: test_repo_summary_counts
# ---------------------------------------------------------------------------


def test_repo_summary_counts(tmp_path: Path) -> None:
    """Repo summary correctly counts missions with errors/warnings."""
    specs_dir = tmp_path / "kitty-specs"

    # Clean mission: valid meta.json with mission_id + mission_number
    _make_mission(specs_dir, "001-clean", _ULID_A, mission_number=1)

    # Mission with a LEGACY_KEY warning: add feature_slug to meta.json
    legacy_dir = specs_dir / "002-legacy"
    legacy_dir.mkdir(parents=True, exist_ok=True)
    legacy_meta: dict[str, object] = {
        "mission_id": _ULID_B,
        "mission_slug": "002-legacy",
        "mission_number": 2,
        "friendly_name": "Legacy mission",
        "feature_slug": "old-slug",  # LEGACY_KEY → WARNING
    }
    (legacy_dir / "meta.json").write_text(json.dumps(legacy_meta), encoding="utf-8")

    report = run_audit(_options(tmp_path))

    summary = report.repo_summary
    assert summary["total_missions"] == 2
    assert summary["missions_with_errors"] == 0
    assert summary["missions_with_warnings"] == 1  # only 002-legacy has a warning
    assert summary["total_findings"] >= 1
    assert summary["findings_by_severity"]["warning"] >= 1
    assert summary["findings_by_severity"]["error"] == 0


# ---------------------------------------------------------------------------
# Test 7: test_performance_204_missions
# ---------------------------------------------------------------------------


def test_performance_204_missions(tmp_path: Path) -> None:
    """204 minimal missions complete in under 30 seconds (NFR-003)."""
    specs_dir = tmp_path / "kitty-specs"
    specs_dir.mkdir(parents=True, exist_ok=True)

    # Use a pool of valid ULIDs, cycling through them with a suffix to make unique
    _BASE_ULID = "01KQHRB8GCFJAX7HM4ZY52AQ"
    valid_suffix_chars = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"

    # Generate 204 distinct valid ULIDs
    def _make_ulid(i: int) -> str:
        # Encode i as 2 chars from the valid Crockford Base32 alphabet
        high = i // len(valid_suffix_chars)
        low = i % len(valid_suffix_chars)
        return _BASE_ULID + valid_suffix_chars[high] + valid_suffix_chars[low]

    for i in range(204):
        slug = f"mission-{i:04d}"
        mission_dir = specs_dir / slug
        mission_dir.mkdir()
        meta = {
            "mission_id": _make_ulid(i),
            "mission_slug": slug,
            "friendly_name": f"Mission {i}",
            "mission_number": i,
        }
        (mission_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")

    opts = AuditOptions(repo_root=tmp_path, scan_root=specs_dir, fail_on=None)

    start = time.perf_counter()
    report = run_audit(opts)
    elapsed = time.perf_counter() - start

    assert len(report.missions) == 204, f"Expected 204 missions, got {len(report.missions)}"
    assert elapsed < 30.0, f"204-mission audit took {elapsed:.2f}s, expected < 30s"


# ---------------------------------------------------------------------------
# Test 8: test_empty_scan_root
# ---------------------------------------------------------------------------


def test_empty_scan_root(tmp_path: Path) -> None:
    """An empty scan_root produces an empty report with zero missions."""
    # Create an empty kitty-specs directory
    specs_dir = tmp_path / "kitty-specs"
    specs_dir.mkdir(parents=True)

    report = run_audit(_options(tmp_path))

    assert report.missions == []
    assert report.repo_summary["total_missions"] == 0
    assert report.repo_summary["total_findings"] == 0
