"""ATDD acceptance tests for ``spec-kitty migrate backfill-runtime-state`` (WP01 / US1).

Drives the real command via ``typer.testing.CliRunner`` over real fixture corpora:

* US1.1 — ``--dry-run`` reports would-seed counts, writes 0 events / 0 flips, exit 0;
* US1.2 — a real run flips ``status_phase="1"`` only for passing missions, exit 0, and
  the reduced snapshot matches the OLD reader (the library verify, re-run here);
* US1.3 — a REAL fault-injected corrupt deterministic seed records that mission's failure, exits
  non-zero, names the mismatch, and leaves ``status_phase`` untouched (per-mission
  best-effort: sibling missions still flip);
* US1.4 — a re-run seeds nothing and flips nothing (idempotent), exit 0.

No verify is mocked — every fault is a real divergent seed exercised through the real
library verify over a real event log.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import Result
from typer.testing import CliRunner

from specify_cli.cli.commands.migrate_cmd import app as migrate_app
from specify_cli.migration.backfill_runtime_state import backfill_runtime_state
from tests.unit.migration._backfill_fixture import build_mission, corrupt_seed_value

pytestmark = [pytest.mark.integration]

runner = CliRunner()

_LOCATE = "specify_cli.cli.commands.migrate_cmd.locate_project_root"


def _invoke(repo_root: Path, args: list[str]) -> Result:
    with patch(_LOCATE, return_value=repo_root):
        return runner.invoke(migrate_app, ["backfill-runtime-state", *args])


def _inject_conflicting_seed(feature_dir: Path) -> None:
    """Corrupt the canonical assignee seed payload under its deterministic ID."""
    corrupt_seed_value(
        feature_dir,
        field_name="assignee",
        slot_name="assignee",
        value="EVIL-DIVERGENT",
    )


def test_command_registered_in_help() -> None:
    result = runner.invoke(migrate_app, ["--help"])
    assert result.exit_code == 0
    assert "backfill-runtime-state" in result.stdout


def test_missing_project_root_errors() -> None:
    with patch(_LOCATE, return_value=None):
        result = runner.invoke(migrate_app, ["backfill-runtime-state"])
    assert result.exit_code == 1


# --- US1.1: dry-run reports counts, writes nothing ---------------------------


def test_dry_run_reports_counts_and_writes_nothing(tmp_path: Path) -> None:
    # Two healthy legacy missions — a dry-run must NOT frame either as "failed"
    # just because verify is not-ok pre-seed.
    fd_a = build_mission(tmp_path, slug="alpha")
    fd_b = build_mission(tmp_path, slug="beta")
    events_before = (fd_a / "status.events.jsonl").read_bytes()
    meta_before = (fd_a / "meta.json").read_bytes()

    result = _invoke(tmp_path, ["--dry-run", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["dry_run"] is True
    assert payload["summary"]["seeded"] > 0
    assert payload["summary"]["would_seed"] == 2
    assert payload["summary"]["flipped"] == 0
    # A healthy legacy corpus reports 0 "failed" in dry-run (verify-not-ok pre-seed
    # is "would seed (verify pending)", not a failure) and emits no mismatch wall.
    assert payload["summary"]["failed"] == 0
    assert all(r["failed"] is False for r in payload["results"])
    assert all(r["mismatches"] == [] for r in payload["results"])
    # Zero events, zero flips: byte-stable.
    assert (fd_a / "status.events.jsonl").read_bytes() == events_before
    assert (fd_a / "meta.json").read_bytes() == meta_before
    assert "status_phase" not in json.loads((fd_b / "meta.json").read_text())


# --- US1.2: real run flips only passing missions, matches OLD reader ---------


def test_real_run_flips_and_matches_old_reader(tmp_path: Path) -> None:
    feature_dir = build_mission(tmp_path)

    result = _invoke(tmp_path, ["--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["summary"]["flipped"] == 1
    assert payload["summary"]["failed"] == 0
    assert payload["results"][0]["verify_ok"] is True
    assert json.loads((feature_dir / "meta.json").read_text())["status_phase"] == "1"


# --- US1.3: fault injection -> best-effort failure, untouched, exit non-zero --


def test_fault_injected_conflict_exits_nonzero_and_leaves_phase_untouched(tmp_path: Path) -> None:
    bad = build_mission(tmp_path, slug="bad-mission")
    good = build_mission(tmp_path, slug="good-mission")
    backfill_runtime_state(bad)  # legit seeds first
    _inject_conflicting_seed(bad)  # REAL corruption
    bad_meta_before = (bad / "meta.json").read_bytes()

    result = _invoke(tmp_path, ["--json"])

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["summary"]["failed"] == 1
    by_slug = {r["slug"]: r for r in payload["results"]}
    assert by_slug["bad-mission"]["verify_ok"] is False
    assert by_slug["bad-mission"]["mismatches"]
    # status_phase untouched for the failed mission...
    assert (bad / "meta.json").read_bytes() == bad_meta_before
    assert "status_phase" not in json.loads(bad_meta_before)
    # ...but the sibling still flipped (per-mission best-effort).
    assert by_slug["good-mission"]["flipped"] is True
    assert json.loads((good / "meta.json").read_text())["status_phase"] == "1"


# --- US1.4: idempotent re-run --------------------------------------------------


def test_rerun_is_idempotent(tmp_path: Path) -> None:
    feature_dir = build_mission(tmp_path)
    first = _invoke(tmp_path, [])
    assert first.exit_code == 0
    events_after = (feature_dir / "status.events.jsonl").read_bytes()
    meta_after = (feature_dir / "meta.json").read_bytes()

    result = _invoke(tmp_path, ["--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["summary"]["seeded"] == 0
    assert (feature_dir / "status.events.jsonl").read_bytes() == events_after
    assert (feature_dir / "meta.json").read_bytes() == meta_after


# --- scoping + INV-5 -----------------------------------------------------------


def test_single_mission_scope_flips_only_that_mission(tmp_path: Path) -> None:
    target = build_mission(tmp_path, slug="scoped", mission_id="01SCOPEDMISSION00000000AAA")
    other = build_mission(tmp_path, slug="untouched", mission_id="01UNTOUCHEDMISSION0000BBBB")

    result = _invoke(tmp_path, ["--mission", "scoped", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert [r["slug"] for r in payload["results"]] == ["scoped"]
    assert json.loads((target / "meta.json").read_text())["status_phase"] == "1"
    assert "status_phase" not in json.loads((other / "meta.json").read_text())


def test_mission_handle_resolves_by_mid8_and_full_ulid(tmp_path: Path) -> None:
    """--mission accepts mission_id / mid8 / slug via the canonical resolver (T002)."""
    mission_id = "01JQ8T5N0X6RZV9K2WYB3CD4EF"
    feature_dir = build_mission(tmp_path, slug="042-demo", mission_id=mission_id)
    mid8 = mission_id[:8]

    for handle in (mission_id, mid8, "042-demo"):
        result = _invoke(tmp_path, ["--mission", handle, "--json"])
        assert result.exit_code == 0, f"handle {handle!r} failed to resolve"
        payload = json.loads(result.stdout)
        assert [r["slug"] for r in payload["results"]] == ["042-demo"], handle

    assert json.loads((feature_dir / "meta.json").read_text())["status_phase"] == "1"


def test_unknown_mission_handle_exits_nonzero(tmp_path: Path) -> None:
    (tmp_path / "kitty-specs").mkdir()
    result = _invoke(tmp_path, ["--mission", "does-not-exist"])
    # resolve_mission_handle prints + sys.exit(2)s on an unknown handle.
    assert result.exit_code != 0


def test_no_kitty_specs_is_clean_noop(tmp_path: Path) -> None:
    result = _invoke(tmp_path, ["--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["summary"]["total"] == 0


def test_no_repo_root_event_write_via_cli(tmp_path: Path) -> None:
    build_mission(tmp_path)
    result = _invoke(tmp_path, [])
    assert result.exit_code == 0
    assert not (tmp_path / "status.events.jsonl").exists()
    assert not (tmp_path / "meta.json").exists()
