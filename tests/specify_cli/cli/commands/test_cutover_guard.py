"""Red-first tests for the diff-scoped fail-closed cut-over guard (WP03).

Proves contracts/pre-merge-guard.md (IC-03 / IC-04; FR-002, FR-003, FR-009,
NFR-002, NFR-003) for mission runtime-state-birth-cutover-all-paths:

* (a) R2 vacuity trap — a natively-born mission with genuine event-log
  runtime evidence (a real claim) but an un-flipped ``status_phase`` is
  FLAGGED un-cut-over, even though ``verify_backfill`` is vacuously ``ok``
  (``wp_count=0``, no frontmatter at all). Keying on bare
  ``verify_backfill.ok`` would wrongly pass this mission.
* (b) an all-cut-over diff passes cleanly.
* (c) a mission with no ``mission_id`` at all fails closed, independent of
  everything else about it.

Fixtures below deliberately mirror the shape built by
``tests/specify_cli/migration/test_dogfood_corpus_backfilled.py``'s
``test_reked_lock_reds_on_born_un_reconciled_mission`` (the R2 proof this
guard shares authority with via
:mod:`specify_cli.status.cutover_eligibility`), but are independently
constructed here — this file owns its own fixtures, not a re-import of test
helpers from another test module.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from specify_cli.cli.commands import cutover_guard as cutover_guard_mod
from specify_cli.cli.commands.cutover_guard import (
    CutoverGuardError,
    cutover_guard,
    evaluate_touched_missions,
    remedy_command,
    touched_mission_slugs,
)
from specify_cli.status import (
    Lane,
    StatusEvent,
    append_events_atomic_verified,
    build_claim_policy_metadata,
)

pytestmark = [pytest.mark.fast]

#: ``cutover_guard`` is registered directly on the root app
#: (``app.command(name="cutover-guard")(...)``), not as a Typer sub-app —
#: wrap it the same way ``test_intake.py`` wraps other bare-function
#: commands so ``CliRunner`` has a real Typer instance to invoke.
_guard_app = typer.Typer()
_guard_app.command()(cutover_guard)


def _write_meta(mission_dir: Path, *, mission_id: str | None, status_phase: str | None) -> None:
    payload: dict[str, object] = {"mission_slug": mission_dir.name, "mission_type": "software-dev"}
    if mission_id is not None:
        payload["mission_id"] = mission_id
    if status_phase is not None:
        payload["status_phase"] = status_phase
    mission_dir.mkdir(parents=True, exist_ok=True)
    (mission_dir / "meta.json").write_text(json.dumps(payload), encoding="utf-8")


def _seed_live_claim(mission_dir: Path, mission_id: str, *, event_id: str) -> None:
    """Append a genuine LIVE claim (real ``policy_metadata``) for WP01.

    This is the exact wire shape a real born mission gets at the WP09
    birth-cutover seam — NOT a backfill seed. Its mere presence is the
    event-log runtime evidence the shared predicate keys on.
    """
    claim = StatusEvent(
        event_id=event_id,
        mission_slug=mission_dir.name,
        mission_id=mission_id,
        wp_id="WP01",
        from_lane=Lane.PLANNED,
        to_lane=Lane.CLAIMED,
        at="2026-07-25T09:00:00+00:00",
        actor="claude:sonnet:pedro",
        force=False,
        execution_mode="worktree",
        policy_metadata=build_claim_policy_metadata(
            shell_pid=55221,
            shell_pid_created_at="2026-07-25T08:59:00+00:00",
            agent="claude:sonnet:pedro",
        ),
    )
    append_events_atomic_verified(mission_dir, [claim])


def _build_native_un_cut_over_mission(corpus: Path, *, slug: str, mission_id: str) -> Path:
    """A natively-born mission: real event-log claim, NO ``status_phase`` key at all.

    No frontmatter runtime state anywhere on disk (the FR-008/WP05
    authoring-retired shape), so ``verify_backfill`` reads vacuously ``ok``
    with ``wp_count=0`` — the R2 vacuous-green trap this guard must not fall
    into.
    """
    mission_dir = corpus / slug
    _write_meta(mission_dir, mission_id=mission_id, status_phase=None)
    tasks = mission_dir / "tasks"
    tasks.mkdir()
    (tasks / "WP01-demo.md").write_text(
        "---\nwork_package_id: WP01\ntitle: Demo\nexecution_mode: code_change\n---\n\n# WP01\n",
        encoding="utf-8",
    )
    (mission_dir / "tasks.md").write_text("# Tasks\n\n## WP01 Demo\n\n", encoding="utf-8")
    _seed_live_claim(mission_dir, mission_id, event_id="01NATIVEUNCUTOVERAAAAAAAAA")
    return mission_dir


def _build_cut_over_mission(corpus: Path, *, slug: str, mission_id: str) -> Path:
    """Same shape as :func:`_build_native_un_cut_over_mission`, but flipped.

    ``status_phase`` is stamped ``"1"`` — the exact delta that must move a
    mission from un-cut-over to cut-over under the shared predicate.
    """
    mission_dir = corpus / slug
    _write_meta(mission_dir, mission_id=mission_id, status_phase="1")
    tasks = mission_dir / "tasks"
    tasks.mkdir()
    (tasks / "WP01-demo.md").write_text(
        "---\nwork_package_id: WP01\ntitle: Demo\nexecution_mode: code_change\n---\n\n# WP01\n",
        encoding="utf-8",
    )
    (mission_dir / "tasks.md").write_text("# Tasks\n\n## WP01 Demo\n\n", encoding="utf-8")
    _seed_live_claim(mission_dir, mission_id, event_id="01CUTOVERCUTOVERAAAAAAAAAA")
    return mission_dir


def _build_missing_mission_id_mission(corpus: Path, *, slug: str) -> Path:
    """A mission whose ``meta.json`` carries no ``mission_id`` key at all."""
    mission_dir = corpus / slug
    _write_meta(mission_dir, mission_id=None, status_phase="1")
    return mission_dir


# --- (a) R2 vacuity trap: native un-cut-over mission is FLAGGED ------------


def test_native_un_cut_over_mission_is_flagged(tmp_path: Path) -> None:
    corpus = tmp_path / "kitty-specs"
    corpus.mkdir()
    slug = "native-un-cut-over-01KZQXTR"
    _build_native_un_cut_over_mission(corpus, slug=slug, mission_id="01KZQXTRH8T2X6R4N9YV3D5C7B")

    changed_paths = [f"kitty-specs/{slug}/status.events.jsonl"]
    verdict = evaluate_touched_missions(tmp_path, changed_paths)

    assert verdict.passed is False
    assert verdict.touched_slugs == (slug,)
    assert len(verdict.failures) == 1
    failure = verdict.failures[0]
    assert failure.mission_slug == slug
    assert failure.cut_over is False
    # Non-vacuity: the failure reason must name the real cause (unflipped
    # status_phase), never a silent pass keyed on vacuous verify_backfill.
    assert any("status_phase" in reason for reason in failure.reasons)


def test_native_un_cut_over_mission_reds_the_cli(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Same fixture, driven through the actual Typer command (integration seam).

    ``SPECIFY_REPO_ROOT`` is the documented deterministic override for
    ``locate_project_root`` (authoritative regardless of cwd) — used here
    instead of ``os.chdir``, which would mutate global process state under a
    parallel test run.
    """
    corpus = tmp_path / "kitty-specs"
    corpus.mkdir()
    slug = "native-un-cut-over-cli-01KZQXTS"
    _build_native_un_cut_over_mission(corpus, slug=slug, mission_id="01KZQXTSH8T2X6R4N9YV3D5C7C")
    (tmp_path / ".kittify").mkdir()
    monkeypatch.setenv("SPECIFY_REPO_ROOT", str(tmp_path))

    paths_file = tmp_path / "changed-paths.txt"
    paths_file.write_text(f"kitty-specs/{slug}/meta.json\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(_guard_app, ["--paths-from", str(paths_file)])

    assert result.exit_code == 1
    # Normalize away Rich's ambient-width line wrapping (the console isn't
    # pinned wide here) rather than asserting on a fragile literal substring.
    normalized_output = " ".join(result.output.split())
    assert slug in normalized_output
    assert remedy_command(slug) in normalized_output


def test_all_cut_over_diff_passes_through_the_cli(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    corpus = tmp_path / "kitty-specs"
    corpus.mkdir()
    slug = "cut-over-clean-cli-01KZQXTZ"
    _build_cut_over_mission(corpus, slug=slug, mission_id="01KZQXTZH8T2X6R4N9YV3D5C7G")
    (tmp_path / ".kittify").mkdir()
    monkeypatch.setenv("SPECIFY_REPO_ROOT", str(tmp_path))

    paths_file = tmp_path / "changed-paths.txt"
    paths_file.write_text(f"kitty-specs/{slug}/meta.json\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(_guard_app, ["--paths-from", str(paths_file)])

    assert result.exit_code == 0


def test_neither_base_ref_nor_paths_from_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / ".kittify").mkdir()
    monkeypatch.setenv("SPECIFY_REPO_ROOT", str(tmp_path))
    runner = CliRunner()
    result = runner.invoke(_guard_app, [])
    assert result.exit_code == 1


def test_both_base_ref_and_paths_from_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / ".kittify").mkdir()
    monkeypatch.setenv("SPECIFY_REPO_ROOT", str(tmp_path))
    paths_file = tmp_path / "changed-paths.txt"
    paths_file.write_text("kitty-specs/whatever/meta.json\n", encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(
        _guard_app, ["--base-ref", "origin/main", "--paths-from", str(paths_file)]
    )
    assert result.exit_code == 1


# --- (b) all-cut-over diff passes ------------------------------------------


def test_all_cut_over_diff_passes(tmp_path: Path) -> None:
    corpus = tmp_path / "kitty-specs"
    corpus.mkdir()
    slug = "cut-over-clean-01KZQXTU"
    _build_cut_over_mission(corpus, slug=slug, mission_id="01KZQXTUH8T2X6R4N9YV3D5C7D")

    changed_paths = [f"kitty-specs/{slug}/status.events.jsonl", f"kitty-specs/{slug}/meta.json"]
    verdict = evaluate_touched_missions(tmp_path, changed_paths)

    assert verdict.passed is True
    assert verdict.touched_slugs == (slug,)
    assert verdict.failures == ()


def test_mixed_diff_one_cut_over_one_not_fails_and_names_only_the_bad_one(
    tmp_path: Path,
) -> None:
    corpus = tmp_path / "kitty-specs"
    corpus.mkdir()
    good_slug = "cut-over-good-01KZQXTV"
    bad_slug = "native-un-cut-over-bad-01KZQXTW"
    _build_cut_over_mission(corpus, slug=good_slug, mission_id="01KZQXTVH8T2X6R4N9YV3D5C7E")
    _build_native_un_cut_over_mission(corpus, slug=bad_slug, mission_id="01KZQXTWH8T2X6R4N9YV3D5C7F")

    changed_paths = [
        f"kitty-specs/{good_slug}/meta.json",
        f"kitty-specs/{bad_slug}/meta.json",
    ]
    verdict = evaluate_touched_missions(tmp_path, changed_paths)

    assert verdict.passed is False
    assert {f.mission_slug for f in verdict.failures} == {bad_slug}


def test_no_kitty_specs_paths_touched_passes_vacuously(tmp_path: Path) -> None:
    changed_paths = ["src/specify_cli/core/paths.py", "docs/README.md"]
    verdict = evaluate_touched_missions(tmp_path, changed_paths)

    assert verdict.passed is True
    assert verdict.touched_slugs == ()
    assert verdict.failures == ()


# --- (c) absent mission_id fails closed ------------------------------------


def test_absent_mission_id_fails_closed(tmp_path: Path) -> None:
    corpus = tmp_path / "kitty-specs"
    corpus.mkdir()
    slug = "no-mission-id-01KZQXTX"
    _build_missing_mission_id_mission(corpus, slug=slug)

    changed_paths = [f"kitty-specs/{slug}/meta.json"]
    verdict = evaluate_touched_missions(tmp_path, changed_paths)

    assert verdict.passed is False
    assert len(verdict.failures) == 1
    failure = verdict.failures[0]
    assert failure.mission_slug == slug
    assert any("mission_id" in reason for reason in failure.reasons)


def test_missing_mission_directory_fails_closed(tmp_path: Path) -> None:
    """A diff naming a mission whose directory doesn't exist (ambiguous / removed)."""
    changed_paths = ["kitty-specs/never-existed-01KZQXTY/meta.json"]
    verdict = evaluate_touched_missions(tmp_path, changed_paths)

    assert verdict.passed is False
    assert len(verdict.failures) == 1
    assert verdict.failures[0].mission_slug == "never-existed-01KZQXTY"


# --- Helper unit coverage ----------------------------------------------------


def test_touched_mission_slugs_dedupes_and_ignores_non_kitty_specs_paths() -> None:
    paths = [
        "kitty-specs/alpha-01/meta.json",
        "kitty-specs/alpha-01/status.events.jsonl",
        "kitty-specs/beta-02/tasks/WP01.md",
        "src/specify_cli/foo.py",
        "kitty-specs",  # too short to name a mission
    ]
    assert touched_mission_slugs(paths) == ("alpha-01", "beta-02")


def test_remedy_command_is_exact() -> None:
    assert remedy_command("my-mission-01ABCD") == (
        "spec-kitty migrate backfill-runtime-state --mission my-mission-01ABCD"
    )


# ---------------------------------------------------------------------------
# NFR-003 fail-closed paths.
#
# Every branch below is an *uncertainty* path: the guard cannot determine what
# the diff touched, or cannot decide a mission. The contract is that each one
# is a FAILURE, never a silent pass. These were the guard's whole reason for
# existing and were previously untested (the module sat at 73% with exactly
# these regions uncovered).
# ---------------------------------------------------------------------------


def test_unresolvable_merge_base_raises_rather_than_reporting_no_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An unknown --base-ref must raise, not degrade to an empty diff."""
    monkeypatch.setattr(cutover_guard_mod, "git_merge_base", lambda *a, **k: None)

    with pytest.raises(CutoverGuardError) as excinfo:
        cutover_guard_mod.changed_paths_from_git(tmp_path, "no/such/ref")

    assert "merge-base" in str(excinfo.value)


def test_failed_diff_raises_rather_than_reporting_no_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed git diff must raise: an empty tuple would read as 'nothing touched, pass'."""
    monkeypatch.setattr(cutover_guard_mod, "git_merge_base", lambda *a, **k: "abc123")
    monkeypatch.setattr(cutover_guard_mod, "git_diff_names_checked", lambda *a, **k: None)

    with pytest.raises(CutoverGuardError) as excinfo:
        cutover_guard_mod.changed_paths_from_git(tmp_path, "origin/main")

    assert "git diff failed" in str(excinfo.value)


def test_unsafe_slug_in_diff_fails_closed(tmp_path: Path) -> None:
    """A traversal-shaped slug lifted from a diff path is rejected, not joined."""
    (tmp_path / "kitty-specs").mkdir()

    verdict = evaluate_touched_missions(tmp_path, ["kitty-specs/../../etc/passwd"])

    assert verdict.passed is False
    assert len(verdict.failures) == 1
    assert any("unsafe mission slug" in reason for reason in verdict.failures[0].reasons)


def test_predicate_error_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Any exception from is_cut_over is recorded as a failure, never skipped."""
    corpus = tmp_path / "kitty-specs"
    corpus.mkdir()
    slug = "boom-01KZQXTX"
    (corpus / slug).mkdir()

    def _explode(_mission_dir: Path) -> None:
        raise RuntimeError("predicate exploded")

    monkeypatch.setattr(cutover_guard_mod, "is_cut_over", _explode)

    verdict = evaluate_touched_missions(tmp_path, [f"kitty-specs/{slug}/meta.json"])

    assert verdict.passed is False
    assert any("predicate exploded" in reason for reason in verdict.failures[0].reasons)


def test_unreadable_paths_from_file_exits_one(tmp_path: Path) -> None:
    """An unreadable --paths-from is a fail-closed exit(1), not an empty diff."""
    result = CliRunner().invoke(
        _guard_app, ["--paths-from", str(tmp_path / "does-not-exist.txt")]
    )

    assert result.exit_code == 1


def test_cli_surfaces_guard_error_as_exit_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A CutoverGuardError from the diff resolution reaches the operator as exit 1."""
    monkeypatch.setattr(cutover_guard_mod, "locate_project_root", lambda *a, **k: tmp_path)

    def _raise(*_a: object, **_k: object) -> None:
        raise CutoverGuardError("merge-base unresolvable")

    monkeypatch.setattr(cutover_guard_mod, "changed_paths_from_git", _raise)

    result = CliRunner().invoke(_guard_app, ["--base-ref", "origin/main"])

    assert result.exit_code == 1
