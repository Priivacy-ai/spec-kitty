"""Corpus-measured tests for the un-terminable-work detector (#3590, FR-007/FR-008).

The fixed labeled corpus under ``fixtures/`` is the oracle (SC-003): the
detector's claim is scoped to it, not the open world.

- ``positive/`` — every fixture MUST warn (100% recall).
- ``negative/`` — every fixture MUST NOT warn (0 false positives), including two
  verbatim copies of real work packages from this repository.

The final test proves the advisory CLI surface (``check-terminability``) exits 0
even when a warning fires (FR-008 — authoring is never blocked).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.agent.tasks import app as tasks_app
from specify_cli.tasks_authoring import (
    TRIGGER_SET_VERSION,
    PostIntegrationWarning,
    scan_work_package,
    trigger_phrases,
)
from specify_cli.tasks_authoring.post_integration_warning import _normalize

pytestmark = [pytest.mark.unit, pytest.mark.fast]

_FIXTURES = Path(__file__).parent / "fixtures"
_POSITIVE_DIR = _FIXTURES / "positive"
_NEGATIVE_DIR = _FIXTURES / "negative"


def _positive_fixtures() -> list[Path]:
    return sorted(_POSITIVE_DIR.glob("*.md"))


def _negative_fixtures() -> list[Path]:
    return sorted(_NEGATIVE_DIR.glob("*.md"))


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


# --------------------------------------------------------------------------- #
# Corpus sanity: the oracle must actually exist and include the real-repo files.
# --------------------------------------------------------------------------- #


def test_corpus_is_populated() -> None:
    assert _positive_fixtures(), "positive corpus is empty"
    assert _negative_fixtures(), "negative corpus is empty"


def test_corpus_includes_two_real_repo_negatives() -> None:
    real = [p for p in _negative_fixtures() if p.name.startswith("real_repo_")]
    assert len(real) >= 2, f"corpus must include at least two negatives copied from real repo WP files to avoid being self-serving; found: {[p.name for p in real]}"


# --------------------------------------------------------------------------- #
# Recall / precision against the fixed corpus (SC-003).
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("fixture", _positive_fixtures(), ids=lambda p: p.stem)
def test_positive_fixtures_warn(fixture: Path) -> None:
    """100% recall: every positive fixture yields at least one warning."""
    warnings = scan_work_package(fixture.stem, _read(fixture))
    assert warnings, f"expected a warning for positive fixture {fixture.name}"
    for warning in warnings:
        assert isinstance(warning, PostIntegrationWarning)
        assert warning.matched_phrase in trigger_phrases()
        assert warning.criterion_excerpt


@pytest.mark.parametrize("fixture", _negative_fixtures(), ids=lambda p: p.stem)
def test_negative_fixtures_are_silent(fixture: Path) -> None:
    """0 false positives: no negative fixture yields a warning."""
    warnings = scan_work_package(fixture.stem, _read(fixture))
    assert warnings == [], f"false positive on {fixture.name}: {[w.matched_phrase for w in warnings]}"


def test_full_corpus_confusion_matrix() -> None:
    """Aggregate SC-003 check: 100% recall, 0 false positives across the corpus."""
    positives = _positive_fixtures()
    negatives = _negative_fixtures()

    true_positives = sum(1 for p in positives if scan_work_package(p.stem, _read(p)))
    false_positives = sum(1 for p in negatives if scan_work_package(p.stem, _read(p)))

    assert true_positives == len(positives), "recall < 100% on positive corpus"
    assert false_positives == 0, "false positives on negative corpus"


# --------------------------------------------------------------------------- #
# Matcher unit behavior.
# --------------------------------------------------------------------------- #


def test_matcher_is_pure_and_returns_records() -> None:
    text = "This is done only once merged into the target branch."
    warnings = scan_work_package("WP99", text)
    assert len(warnings) == 1
    (warning,) = warnings
    assert warning.wp_id == "WP99"
    assert warning.matched_phrase == "once merged"
    assert "once merged" in warning.criterion_excerpt


def test_matcher_tolerates_hyphen_and_case_variants() -> None:
    # "POST_MERGE" normalizes to the "post-merge" trigger.
    assert scan_work_package("WP1", "Verify POST_MERGE behavior.")
    # "merge blocked when absent" (spaces) matches "merge-blocked-when-absent".
    assert scan_work_package("WP1", "The gate is merge blocked when absent.")


def test_empty_text_yields_no_warnings() -> None:
    assert scan_work_package("WP1", "") == []
    assert scan_work_package("WP1", "\n\n   \n") == []


def test_ordinary_ci_merge_mentions_do_not_fire() -> None:
    # Near-miss guard at the unit level (mirrors the negative corpus intent).
    assert scan_work_package("WP1", "Run the merge helper and add a CI job.") == []


def test_to_dict_shape() -> None:
    warning = PostIntegrationWarning("WP7", "after merge", "done after merge")
    assert warning.to_dict() == {
        "wp_id": "WP7",
        "matched_phrase": "after merge",
        "criterion_excerpt": "done after merge",
    }


def test_normalize_folds_case_hyphens_and_whitespace() -> None:
    assert _normalize("Post-Merge\tRuns") == "post merge runs"


def test_trigger_set_is_versioned_and_enumerable() -> None:
    assert isinstance(TRIGGER_SET_VERSION, int)
    phrases = trigger_phrases()
    assert phrases and len(set(phrases)) == len(phrases)


# --------------------------------------------------------------------------- #
# Advisory CLI surface (FR-008): warns but never blocks (exit 0).
# --------------------------------------------------------------------------- #


def _install_mission_boundaries(monkeypatch: pytest.MonkeyPatch, tasks_dir_parent: Path) -> None:
    """Point the CLI's resolution seams at a fixture ``kitty-specs`` layout.

    Mirrors the seam-patch pattern used across the ``agent tasks`` CLI tests
    (see ``test_map_requirements_read_surface.py``): patch ``locate_project_root``,
    ``_find_mission_slug``, ``_ensure_target_branch_checked_out`` and the
    ``placement_seam`` WORK_PACKAGE_TASK projection so the real command body runs
    against on-disk fixtures without a full git/mission scaffold.
    """
    mod = "specify_cli.cli.commands.agent.tasks"
    monkeypatch.setattr(f"{mod}.locate_project_root", lambda: tasks_dir_parent)
    monkeypatch.setattr(f"{mod}._find_mission_slug", lambda *a, **k: "demo-mission")
    monkeypatch.setattr(
        f"{mod}._ensure_target_branch_checked_out",
        lambda *a, **k: (tasks_dir_parent, "main"),
    )

    class _StubSeam:
        def read_dir(self, kind: object) -> Path:
            return tasks_dir_parent

    monkeypatch.setattr(f"{mod}.placement_seam", lambda *a, **k: _StubSeam())


def test_check_terminability_exits_zero_when_warning_fires(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """FR-008: a fired warning must NOT fail authoring — the command exits 0."""
    tasks_dir = tmp_path / "tasks"
    tasks_dir.mkdir()
    # Seed one trapped WP (carries a trigger phrase) so a warning is guaranteed.
    trapped = _POSITIVE_DIR / "observe_consecutive_runs.md"
    (tasks_dir / "WP01-observe.md").write_text(_read(trapped), encoding="utf-8")

    _install_mission_boundaries(monkeypatch, tmp_path)

    result = CliRunner().invoke(
        tasks_app,
        ["check-terminability", "--mission", "demo-mission", "--json"],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["count"] >= 1
    assert payload["trigger_set_version"] == TRIGGER_SET_VERSION
    assert payload["warnings"], "expected at least one warning record"
    assert payload["guidance"], "guidance must accompany a fired warning"


def test_check_terminability_exits_zero_and_silent_on_clean_mission(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A clean mission produces no warnings and still exits 0."""
    tasks_dir = tmp_path / "tasks"
    tasks_dir.mkdir()
    clean = _NEGATIVE_DIR / "adds_ci_workflow_file.md"
    (tasks_dir / "WP01-ci.md").write_text(_read(clean), encoding="utf-8")

    _install_mission_boundaries(monkeypatch, tmp_path)

    result = CliRunner().invoke(
        tasks_app,
        ["check-terminability", "--mission", "demo-mission", "--json"],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["count"] == 0
    assert payload["warnings"] == []
