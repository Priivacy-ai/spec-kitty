"""Tests for ``spec-kitty doctor cutover`` (WP05, FR-007).

The on-demand audit is backed entirely by
``migration.runtime_state_cutover.cutover_repo(dry_run=True)`` — no corpus
walking or verification is reimplemented here. These tests build a REAL
fixture corpus (via the shared ``_backfill_fixture.build_mission`` builder
used by the WP01/WP03 cutover unit tests) with one mission whose legacy
runtime is fully event-sourced (cut over) and one whose legacy runtime is
still only in frontmatter (not yet cut over), then assert the audit reports
each correctly — both the human table and the ``--json`` form.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

import specify_cli.cli.commands.doctor as doctor_module
from specify_cli.cli.commands import _cutover_doctor
from specify_cli.migration.backfill_runtime_state import backfill_runtime_state
from tests.unit.migration._backfill_fixture import build_mission

pytestmark = [pytest.mark.fast]

runner = CliRunner()

_SEEDED_SLUG = "042-seeded"
_UNSEEDED_SLUG = "043-unseeded"


def _build_corpus(tmp_path: Path) -> Path:
    """Build a repo_root with one cut-over and one un-cut-over mission.

    ``_SEEDED_SLUG`` has had its legacy runtime backfilled as events (the
    seed-then-verify spine would report it clean — cut over). ``_UNSEEDED_SLUG``
    still only carries its runtime in ``tasks/WP01-demo.md`` frontmatter — no
    seed events exist yet, so verify reports a real, non-vacuous mismatch (not
    cut over). Neither mission has actually had its ``meta.json`` flipped
    (``dry_run=True`` never writes), matching the doctor's read-only contract.
    """
    seeded_dir = build_mission(tmp_path, slug=_SEEDED_SLUG, mission_id="01JSEEDED0000000000000AA")
    backfill_runtime_state(seeded_dir)  # real seed events -> verify.ok on dry-run
    build_mission(tmp_path, slug=_UNSEEDED_SLUG, mission_id="01JUNSEEDED000000000AA")
    return tmp_path


# ---------------------------------------------------------------------------
# Module-level helpers (_cutover_doctor)
# ---------------------------------------------------------------------------


def test_collect_cutover_audit_reports_seeded_mission_as_cut_over(tmp_path: Path) -> None:
    repo_root = _build_corpus(tmp_path)
    entries = {e.slug: e for e in _cutover_doctor.collect_cutover_audit(repo_root)}

    assert entries[_SEEDED_SLUG].cut_over is True
    assert entries[_SEEDED_SLUG].reason


def test_collect_cutover_audit_reports_unseeded_mission_as_not_cut_over(tmp_path: Path) -> None:
    repo_root = _build_corpus(tmp_path)
    entries = {e.slug: e for e in _cutover_doctor.collect_cutover_audit(repo_root)}

    assert entries[_UNSEEDED_SLUG].cut_over is False
    assert entries[_UNSEEDED_SLUG].reason  # a real mismatch reason, not empty


def test_collect_cutover_audit_is_read_only(tmp_path: Path) -> None:
    """The dry-run audit must never write meta.json or the event log."""
    repo_root = _build_corpus(tmp_path)
    unseeded_meta = repo_root / "kitty-specs" / _UNSEEDED_SLUG / "meta.json"
    seeded_meta = repo_root / "kitty-specs" / _SEEDED_SLUG / "meta.json"
    before_unseeded = unseeded_meta.read_bytes()
    before_seeded = seeded_meta.read_bytes()

    _cutover_doctor.collect_cutover_audit(repo_root)

    assert unseeded_meta.read_bytes() == before_unseeded
    assert seeded_meta.read_bytes() == before_seeded


def test_collect_cutover_audit_empty_corpus(tmp_path: Path) -> None:
    (tmp_path / "kitty-specs").mkdir()
    assert _cutover_doctor.collect_cutover_audit(tmp_path) == []


# ---------------------------------------------------------------------------
# CLI surface (human + --json)
# ---------------------------------------------------------------------------


def test_doctor_cutover_human_table_reports_both_missions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root = _build_corpus(tmp_path)
    monkeypatch.setattr(doctor_module, "locate_project_root", lambda *a, **k: repo_root)

    result = runner.invoke(doctor_module.app, ["cutover"])

    assert result.exit_code == 0, result.output
    assert _SEEDED_SLUG in result.output
    assert _UNSEEDED_SLUG in result.output
    assert "1/2" in result.output


def test_doctor_cutover_json_reports_both_missions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root = _build_corpus(tmp_path)
    monkeypatch.setattr(doctor_module, "locate_project_root", lambda *a, **k: repo_root)

    result = runner.invoke(doctor_module.app, ["cutover", "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    by_slug = {m["slug"]: m for m in payload["missions"]}

    assert by_slug[_SEEDED_SLUG]["cut_over"] is True
    assert by_slug[_UNSEEDED_SLUG]["cut_over"] is False
    assert by_slug[_UNSEEDED_SLUG]["reason"]
    assert payload["cut_over_count"] == 1
    assert payload["total"] == 2


def test_doctor_cutover_exits_zero_even_when_a_mission_is_not_cut_over(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Informational audit (T021): non-zero exit is explicitly out of scope."""
    repo_root = _build_corpus(tmp_path)
    monkeypatch.setattr(doctor_module, "locate_project_root", lambda *a, **k: repo_root)

    result = runner.invoke(doctor_module.app, ["cutover"])

    assert result.exit_code == 0


def test_doctor_cutover_not_in_project_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(doctor_module, "locate_project_root", lambda *a, **k: None)

    result = runner.invoke(doctor_module.app, ["cutover"])

    assert result.exit_code == 1
