"""FR-005/NFR-002: loud, CLI-visible signal when ``mission current`` falls back.

``get_mission_for_feature`` (``src/specify_cli/mission.py``) silently substitutes
``software-dev`` when a feature's ``meta.json`` names a mission type that cannot be
resolved, signalling only via ``warnings.warn`` — a signal that never reaches an
operator running the CLI normally (default warning filters swallow it, and nothing
in ``current_cmd`` ever looks at it). Issue #3831 / FR-005.

These tests drive the real, pre-existing entry point end-to-end
(``spec-kitty mission-type current`` / ``current_cmd``) through
:class:`typer.testing.CliRunner`, capturing real stdout the way an operator would
see it — not ``pytest.warns`` in isolation, which only proves the warning object
exists. ``get_mission_for_feature`` itself is NOT mocked: the fallback is produced
for real, via a genuinely-unresolvable ``mission_type`` in a real ``meta.json``,
resolving against the real packaged ``software-dev`` built-in mission.

Both directions are proven (SC-004 / NFR-005 non-vacuity):
* the loud signal is PRESENT when the fallback fires (T001/T003a), and
* the loud signal is ABSENT when mission-type resolution succeeds normally,
  including the pinned legacy no-mission-field path (T003b/T004).
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.mission_type import app as mission_type_app

pytestmark = [pytest.mark.unit, pytest.mark.fast]

runner = CliRunner()


def _write_meta(feature_dir: Path, *, mission_type: str | None) -> None:
    feature_dir.mkdir(parents=True, exist_ok=True)
    meta: dict[str, object] = {
        "feature_number": "999",
        "slug": feature_dir.name,
        "friendly_name": "Fallback Signal Test Feature",
    }
    if mission_type is not None:
        meta["mission_type"] = mission_type
    (feature_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")


def _invoke_current(tmp_path: Path, mission_slug: str):
    with patch(
        "specify_cli.cli.commands.mission_type.get_project_root_or_exit",
        return_value=tmp_path,
    ):
        return runner.invoke(mission_type_app, ["current", "--mission", mission_slug])


class TestFallbackSignalPresent:
    """T001/T003a: the loud signal IS present when the fallback fires."""

    def test_unresolvable_mission_type_prints_loud_cli_warning(self, tmp_path: Path) -> None:
        mission_slug = "999-unresolvable-mission-type"
        feature_dir = tmp_path / "kitty-specs" / mission_slug
        _write_meta(feature_dir, mission_type="totally-nonexistent-mission-type-xyz")

        result = _invoke_current(tmp_path, mission_slug)

        assert result.exit_code == 0, result.output
        # The real fallback fired (proves this is not a mocked/no-op repro):
        # the panel still renders successfully using the substituted mission.
        assert "Active Mission" in result.output
        # SC-004 evidence bar: a real, operator-visible line naming the
        # substitution — not just the panel rendering silently as if the
        # requested mission type had been found.
        assert "Warning" in result.output
        assert "totally-nonexistent-mission-type-xyz" in result.output
        assert "software-dev" in result.output

    def test_signal_survives_default_warning_filters(self, tmp_path: Path) -> None:
        """Repro of the pre-fix defect: under *default* filters (no
        ``simplefilter('always')``, no ``pytest.warns``), a bare
        ``warnings.warn`` is frequently suppressed outright (Python's default
        'once per location' filter) and never lands in CLI output at all. The
        loud signal must appear in real captured stdout regardless.
        """
        mission_slug = "999-repeat-unresolvable"
        feature_dir = tmp_path / "kitty-specs" / mission_slug
        _write_meta(feature_dir, mission_type="totally-nonexistent-mission-type-xyz")

        # Invoke twice: a bare module-level warnings.warn is filtered to fire
        # only once per (message, category, lineno) under the default filter,
        # so a second invocation is exactly what would previously go silent.
        _invoke_current(tmp_path, mission_slug)
        result = _invoke_current(tmp_path, mission_slug)

        assert result.exit_code == 0, result.output
        assert "Warning" in result.output
        assert "totally-nonexistent-mission-type-xyz" in result.output


class TestFallbackSignalAbsent:
    """T003b: the loud signal is ABSENT when resolution succeeds normally.

    Non-vacuity: a check that always fires regardless of input is not a real
    signal. Proving the negative direction is required alongside the positive.
    """

    def test_resolvable_mission_type_prints_no_warning(self, tmp_path: Path) -> None:
        mission_slug = "999-resolvable-mission-type"
        feature_dir = tmp_path / "kitty-specs" / mission_slug
        _write_meta(feature_dir, mission_type="software-dev")

        result = _invoke_current(tmp_path, mission_slug)

        assert result.exit_code == 0, result.output
        assert "Active Mission" in result.output
        assert "Warning" not in result.output

    def test_legacy_no_mission_field_prints_no_warning(self, tmp_path: Path) -> None:
        """FR-003a: a typeless legacy feature degrades to software-dev with no
        mission-type mismatch, so it is not a "fallback" in the FR-005 sense
        (mission.py itself does not warn for this path either — see
        ``test_legacy_feature_no_warning`` in
        ``tests/missions/test_mission_schema_unit.py``) and must stay silent.
        """
        mission_slug = "999-legacy-no-mission-field"
        feature_dir = tmp_path / "kitty-specs" / mission_slug
        _write_meta(feature_dir, mission_type=None)

        result = _invoke_current(tmp_path, mission_slug)

        assert result.exit_code == 0, result.output
        assert "Active Mission" in result.output
        assert "Warning" not in result.output
