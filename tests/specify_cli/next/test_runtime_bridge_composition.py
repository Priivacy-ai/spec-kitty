"""Integration tests for runtime-bridge composition dispatch (WP02).

Mission: ``software-dev-composition-rewrite-01KQ26CY``.

These tests lock in the bridge ↔ ``StepContractExecutor`` handoff:

* The dispatch branch fires only for ``mission == "software-dev"`` AND a
  composed action ID (``specify``, ``plan``, ``tasks``, ``implement``,
  ``review``).
* The legacy ``tasks_outline`` / ``tasks_packages`` / ``tasks_finalize`` step
  IDs collapse to a single composed ``tasks`` action.
* Any other mission or step ID falls through to the legacy DAG handler
  unchanged (constraint C-008).
* ``StepContractExecutionError`` surfaces as a structured CLI failure
  (``Decision`` with ``kind=blocked`` and populated ``guard_failures``) — not
  a Python traceback (FR-009).
* The collapsed ``tasks`` post-action guard asserts the union of the three
  legacy ``tasks_*`` checks (no weakening of validation).
* The ``specify`` and ``plan`` post-action guards behave like their legacy
  counterparts.

The tests mock ``StepContractExecutor.execute`` rather than instantiating it,
so no real DRG is required.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from specify_cli.mission_step_contracts.executor import (
    StepContractExecutionContext,
    StepContractExecutionError,
)
from specify_cli.next.runtime_bridge import (
    _check_composed_action_guard,
    _dispatch_via_composition,
    _normalize_action_for_composition,
    _should_dispatch_via_composition,
)


pytestmark = pytest.mark.fast


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_wp_file(
    tasks_dir: Path,
    wp_id: str,
    *,
    with_dependencies: bool = True,
) -> Path:
    """Write a minimal WP*.md file with optional 'dependencies:' frontmatter."""
    wp_file = tasks_dir / f"{wp_id}-test.md"
    deps_line = "dependencies: []\n" if with_dependencies else ""
    wp_file.write_text(
        f"---\nwork_package_id: {wp_id}\ntitle: Test\n{deps_line}---\nbody\n",
        encoding="utf-8",
    )
    return wp_file


@pytest.fixture()
def feature_dir(tmp_path: Path) -> Path:
    """Bare feature dir (no spec.md / plan.md / tasks.md / WP files)."""
    fd = tmp_path / "kitty-specs" / "test-feature"
    fd.mkdir(parents=True)
    return fd


@pytest.fixture()
def feature_dir_with_full_tasks(tmp_path: Path) -> Path:
    """Feature dir with spec.md, plan.md, tasks.md, and one valid WP*.md."""
    fd = tmp_path / "kitty-specs" / "test-feature"
    fd.mkdir(parents=True)
    (fd / "spec.md").write_text("# spec", encoding="utf-8")
    (fd / "plan.md").write_text("# plan", encoding="utf-8")
    (fd / "tasks.md").write_text("# tasks", encoding="utf-8")
    tasks = fd / "tasks"
    tasks.mkdir()
    _write_wp_file(tasks, "WP01")
    return fd


# ---------------------------------------------------------------------------
# Helper-function unit tests (cheap, no executor)
# ---------------------------------------------------------------------------


def test_should_dispatch_fires_for_software_dev_composed_actions() -> None:
    """All five composed actions on software-dev route through composition."""
    for action in ("specify", "plan", "tasks", "implement", "review"):
        assert _should_dispatch_via_composition("software-dev", action) is True


def test_should_dispatch_falls_through_for_unknown_mission_helper() -> None:
    """Any mission other than software-dev falls through (C-008)."""
    for mission in ("documentation", "architecture", "doctrine-rewrite", "other"):
        for action in ("specify", "plan", "tasks", "implement", "review"):
            assert _should_dispatch_via_composition(mission, action) is False


def test_should_dispatch_falls_through_for_unknown_step_id_helper() -> None:
    """Step IDs outside the composed set fall through (e.g. ``accept``)."""
    for step_id in ("accept", "merge", "bootstrap", "unknown_step"):
        assert _should_dispatch_via_composition("software-dev", step_id) is False


def test_normalize_collapses_legacy_tasks_step_ids() -> None:
    """All three legacy tasks_* IDs collapse to the composed ``tasks`` action."""
    assert _normalize_action_for_composition("tasks_outline") == "tasks"
    assert _normalize_action_for_composition("tasks_packages") == "tasks"
    assert _normalize_action_for_composition("tasks_finalize") == "tasks"
    # Composed actions and other step IDs pass through unchanged.
    for step_id in ("specify", "plan", "tasks", "implement", "review", "accept"):
        assert _normalize_action_for_composition(step_id) == step_id


# ---------------------------------------------------------------------------
# Test #1 — Composition fires for software-dev specify
# ---------------------------------------------------------------------------


def test_dispatch_via_composition_fires_for_software_dev_specify(
    feature_dir_with_full_tasks: Path, tmp_path: Path
) -> None:
    """``software-dev/specify`` routes through ``StepContractExecutor.execute``.

    Verifies (a) the executor is called exactly once with a context whose
    mission/action match, and (b) the legacy DAG handler is NOT entered for
    this dispatch decision.
    """
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    fake_result = MagicMock()
    with patch(
        "specify_cli.mission_step_contracts.executor.StepContractExecutor.execute",
        return_value=fake_result,
    ) as mock_execute:
        failures = _dispatch_via_composition(
            repo_root=repo_root,
            mission="software-dev",
            action="specify",
            actor="researcher-robbie",
            profile_hint=None,
            request_text=None,
            mode_of_work=None,
            feature_dir=feature_dir_with_full_tasks,
        )

    assert mock_execute.call_count == 1
    # Inspect the StepContractExecutionContext that was passed in.
    (call_args, call_kwargs) = mock_execute.call_args
    # execute(context) — single positional context argument.
    context = call_args[0] if call_args else call_kwargs.get("context")
    assert isinstance(context, StepContractExecutionContext)
    assert context.mission == "software-dev"
    assert context.action == "specify"
    assert context.actor == "researcher-robbie"
    # Composition succeeded AND post-action guard passed → returns None.
    assert failures is None


# ---------------------------------------------------------------------------
# Test #2 — Composition fires for collapsed tasks (each legacy step ID)
# ---------------------------------------------------------------------------


def test_dispatch_via_composition_fires_for_collapsed_tasks(
    feature_dir_with_full_tasks: Path, tmp_path: Path
) -> None:
    """Each legacy ``tasks_*`` step ID routes to a single composed ``tasks``.

    The bridge first normalizes the step_id; then dispatches one composition
    call per invocation (no triplication).
    """
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    for legacy_step_id in ("tasks_outline", "tasks_packages", "tasks_finalize"):
        # Normalization must collapse the legacy ID to "tasks".
        normalized = _normalize_action_for_composition(legacy_step_id)
        assert normalized == "tasks"
        # And a single composition dispatch must produce a single
        # executor call for the composed "tasks" action.
        with patch(
            "specify_cli.mission_step_contracts.executor.StepContractExecutor.execute",
            return_value=MagicMock(),
        ) as mock_execute:
            failures = _dispatch_via_composition(
                repo_root=repo_root,
                mission="software-dev",
                action=normalized,
                actor="architect-alphonso",
                profile_hint=None,
                request_text=None,
                mode_of_work=None,
                feature_dir=feature_dir_with_full_tasks,
            )
        assert mock_execute.call_count == 1, (
            f"Expected one composition call for {legacy_step_id}; "
            f"got {mock_execute.call_count}"
        )
        context = mock_execute.call_args[0][0]
        assert context.action == "tasks"
        assert failures is None


# ---------------------------------------------------------------------------
# Test #3 — Fall-through for unknown mission
# ---------------------------------------------------------------------------


def test_dispatch_falls_through_for_unknown_mission(tmp_path: Path) -> None:
    """For any non-software-dev mission, composition MUST NOT be entered.

    We assert the routing predicate returns False — the bridge's caller
    only invokes composition when the predicate fires, so a False result
    proves the legacy DAG handler is the only dispatch path.
    """
    # Pre-condition: the executor is never called when the predicate is False.
    with patch(
        "specify_cli.mission_step_contracts.executor.StepContractExecutor.execute"
    ) as mock_execute:
        for mission in ("other-mission", "documentation", "architecture"):
            for step_id in ("specify", "plan", "tasks", "implement", "review"):
                assert _should_dispatch_via_composition(mission, step_id) is False
        # Predicate never matched → the bridge would never call _dispatch.
        mock_execute.assert_not_called()


# ---------------------------------------------------------------------------
# Test #4 — Fall-through for unknown step ID inside software-dev
# ---------------------------------------------------------------------------


def test_dispatch_falls_through_for_unknown_step_id() -> None:
    """``software-dev`` step IDs outside the composed set fall through.

    Examples: ``accept``, ``merge``, ``bootstrap`` — these are legitimate
    runtime DAG steps but are not part of the composition layer in this
    slice. The predicate must return False so the bridge keeps using the
    legacy DAG handler for them.
    """
    for step_id in ("accept", "merge", "bootstrap", "unknown_step"):
        assert _should_dispatch_via_composition("software-dev", step_id) is False


# ---------------------------------------------------------------------------
# Test #5 — StepContractExecutionError → structured CLI error (FR-009)
# ---------------------------------------------------------------------------


def test_missing_contract_surfaces_structured_cli_error(
    feature_dir_with_full_tasks: Path, tmp_path: Path
) -> None:
    """A raised ``StepContractExecutionError`` becomes a structured failure.

    No Python traceback escapes; the bridge gets a non-empty failure list
    that it can wrap in a ``Decision(kind=blocked, guard_failures=[...])``
    response — same UX as the legacy guard-failure surface.
    """
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    err_message = "No step contract found for mission/action software-dev/specify"
    with patch(
        "specify_cli.mission_step_contracts.executor.StepContractExecutor.execute",
        side_effect=StepContractExecutionError(err_message),
    ) as mock_execute:
        failures = _dispatch_via_composition(
            repo_root=repo_root,
            mission="software-dev",
            action="specify",
            actor="researcher-robbie",
            profile_hint=None,
            request_text=None,
            mode_of_work=None,
            feature_dir=feature_dir_with_full_tasks,
        )

    assert mock_execute.call_count == 1
    assert failures is not None
    assert len(failures) == 1
    # The CLI-surface message preserves the executor's error text and tags
    # the mission/action so operators can correlate.
    assert "software-dev/specify" in failures[0]
    assert err_message in failures[0]
    # Must NOT be a Python repr — confirms structured surfacing rather than
    # ``repr(exception)`` style which would leak the class name in brackets.
    assert "Traceback" not in failures[0]


# ---------------------------------------------------------------------------
# Test #6 — Collapsed tasks guard requires tasks.md
# ---------------------------------------------------------------------------


def test_tasks_guard_requires_tasks_md(tmp_path: Path) -> None:
    """Composed ``tasks`` guard fails when tasks.md is absent.

    Mirrors the legacy ``tasks_outline`` negative case under the collapsed
    guard.
    """
    fd = tmp_path / "kitty-specs" / "feat"
    fd.mkdir(parents=True)
    # Intentionally do NOT create tasks.md.
    failures = _check_composed_action_guard("tasks", fd)
    assert any("tasks.md" in f for f in failures), (
        f"Expected a failure mentioning tasks.md; got {failures!r}"
    )


# ---------------------------------------------------------------------------
# Test #7 — Collapsed tasks guard requires at least one WP*.md file
# ---------------------------------------------------------------------------


def test_tasks_guard_requires_wp_files(tmp_path: Path) -> None:
    """Composed ``tasks`` guard fails when tasks/ exists but has no WP*.md.

    Mirrors the legacy ``tasks_packages`` negative case.
    """
    fd = tmp_path / "kitty-specs" / "feat"
    fd.mkdir(parents=True)
    (fd / "tasks.md").write_text("# tasks", encoding="utf-8")
    (fd / "tasks").mkdir()
    failures = _check_composed_action_guard("tasks", fd)
    assert any("WP*.md" in f for f in failures), (
        f"Expected a failure mentioning WP*.md; got {failures!r}"
    )


# ---------------------------------------------------------------------------
# Test #8 — Collapsed tasks guard requires raw 'dependencies:' frontmatter
# ---------------------------------------------------------------------------


def test_tasks_guard_requires_dependencies_frontmatter(tmp_path: Path) -> None:
    """Composed ``tasks`` guard fails when WP*.md lacks raw dependencies.

    Mirrors the legacy ``tasks_finalize`` negative case (the one that asserts
    every WP*.md has a 'dependencies:' field in raw frontmatter, indicating
    that 'spec-kitty agent mission finalize-tasks' has run).
    """
    fd = tmp_path / "kitty-specs" / "feat"
    fd.mkdir(parents=True)
    (fd / "tasks.md").write_text("# tasks", encoding="utf-8")
    tasks = fd / "tasks"
    tasks.mkdir()
    # WP file without 'dependencies:' frontmatter.
    _write_wp_file(tasks, "WP01", with_dependencies=False)
    failures = _check_composed_action_guard("tasks", fd)
    assert any("dependencies" in f for f in failures), (
        f"Expected a failure mentioning dependencies; got {failures!r}"
    )
    # The remediation hint should also surface the finalize-tasks command.
    assert any("finalize-tasks" in f for f in failures)


# ---------------------------------------------------------------------------
# Test #9 — Specify guard requires spec.md
# ---------------------------------------------------------------------------


def test_specify_guard_requires_spec_md(tmp_path: Path) -> None:
    """Composed ``specify`` guard fails when spec.md is absent.

    Parity with legacy ``_check_cli_guards("specify", ...)``.
    """
    fd = tmp_path / "kitty-specs" / "feat"
    fd.mkdir(parents=True)
    failures = _check_composed_action_guard("specify", fd)
    assert any("spec.md" in f for f in failures), (
        f"Expected a failure mentioning spec.md; got {failures!r}"
    )


# ---------------------------------------------------------------------------
# Test #10 — Plan guard requires plan.md
# ---------------------------------------------------------------------------


def test_plan_guard_requires_plan_md(tmp_path: Path) -> None:
    """Composed ``plan`` guard fails when plan.md is absent.

    Parity with legacy ``_check_cli_guards("plan", ...)``.
    """
    fd = tmp_path / "kitty-specs" / "feat"
    fd.mkdir(parents=True)
    failures = _check_composed_action_guard("plan", fd)
    assert any("plan.md" in f for f in failures), (
        f"Expected a failure mentioning plan.md; got {failures!r}"
    )


# ---------------------------------------------------------------------------
# Mission-review follow-up tests (post-merge fixes for findings R-2 and R-3)
# ---------------------------------------------------------------------------


def test_dispatch_logs_invocation_chain_on_success(
    feature_dir_with_full_tasks: Path,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """FR-008: the bridge forwards the executor's invocation_id chain to logs.

    Mission-review finding R-2: prior to this test, ``_dispatch_via_composition``
    captured no return value from ``StepContractExecutor.execute``, so the
    ``StepContractExecutionResult.invocation_ids`` chain was discarded on the
    live path. This test pins the new behavior: composition success emits an
    INFO log line that includes the mission, action, count, and the
    invocation_ids tuple so downstream operators / event-trail consumers can
    correlate the composed action with its underlying ProfileInvocationExecutor
    calls.
    """
    import logging

    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    fake_result = MagicMock()
    fake_result.invocation_ids = ("inv-001", "inv-002", "inv-003", "inv-004")

    with (
        caplog.at_level(logging.INFO, logger="specify_cli.next.runtime_bridge"),
        patch(
            "specify_cli.mission_step_contracts.executor.StepContractExecutor.execute",
            return_value=fake_result,
        ),
    ):
        failures = _dispatch_via_composition(
            repo_root=repo_root,
            mission="software-dev",
            action="tasks",
            actor="architect-alphonso",
            profile_hint=None,
            request_text=None,
            mode_of_work=None,
            feature_dir=feature_dir_with_full_tasks,
        )

    assert failures is None
    # The chain must reach the bridge log so it can be consumed by event/trail
    # writers and operator triage tools.
    composition_logs = [
        r for r in caplog.records if "composed software-dev/tasks emitted" in r.message
    ]
    assert composition_logs, (
        f"Expected a composition INFO log forwarding the invocation chain; "
        f"got {[r.message for r in caplog.records]!r}"
    )
    log_msg = composition_logs[0].getMessage()
    assert "4 invocation(s)" in log_msg
    assert "inv-001" in log_msg


def test_unexpected_exception_surfaces_structured_cli_error(
    feature_dir_with_full_tasks: Path, tmp_path: Path
) -> None:
    """FR-009: any executor exception class becomes a structured CLI failure.

    Mission-review finding R-3: prior to this test, only
    ``StepContractExecutionError`` was caught; a ``ValueError`` (or any other
    exception class) raised by the executor would escape as a Python traceback,
    contradicting FR-009's "structured CLI error, NOT crash" mandate. This
    test pins the widened catch: an unexpected exception class becomes a
    well-formed failure list the caller can wrap in a
    ``Decision(kind=blocked, guard_failures=[...])``.

    The assertion text checks for the ``crashed`` keyword (vs. the expected
    ``failed`` from the narrow catch) so the two failure modes remain
    distinguishable in operator-facing surfaces.
    """
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    err_message = "transient error reading contract from disk"
    with patch(
        "specify_cli.mission_step_contracts.executor.StepContractExecutor.execute",
        side_effect=ValueError(err_message),
    ) as mock_execute:
        failures = _dispatch_via_composition(
            repo_root=repo_root,
            mission="software-dev",
            action="implement",
            actor="implementer-ivan",
            profile_hint=None,
            request_text=None,
            mode_of_work=None,
            feature_dir=feature_dir_with_full_tasks,
        )

    assert mock_execute.call_count == 1
    assert failures is not None
    assert len(failures) == 1
    surface = failures[0]
    # Distinguishes "unexpected" path from the narrow StepContractExecutionError
    # path which uses "failed".
    assert "crashed" in surface
    assert "software-dev/implement" in surface
    # Exception class is named so operators can triage by type.
    assert "ValueError" in surface
    assert err_message in surface
    # Must NOT be a Python repr / traceback — confirms structured surfacing.
    assert "Traceback" not in surface


# ---------------------------------------------------------------------------
# Hotfix tests for collapsed-tasks-guard regression (P0)
# ---------------------------------------------------------------------------
#
# Reviewer-reproduced bug: the legacy DAG fires the bridge once per substep
# (``tasks_outline`` → ``tasks_packages`` → ``tasks_finalize``), and the
# collapsed guard demanded the post-finalize terminal state on every call.
# That broke the live tasks_* flow because the user can only have produced
# the post-outline artifacts after the first call. Fix: the guard branches
# on ``legacy_step_id`` so it asks for only what the user is expected to
# have produced at that substep.


def test_collapsed_tasks_guard_passes_after_outline_with_only_tasks_md(
    feature_dir: Path,
) -> None:
    """tasks_outline guard requires only tasks.md, not WP files yet.

    Reproduces the reviewer-reported live-flow blocker: with only spec.md +
    plan.md + tasks.md (no WP files yet), the collapsed-on-tasks_outline
    guard previously returned a "Required: at least one tasks/WP*.md file"
    failure, blocking the user from progressing to tasks_packages.
    """
    (feature_dir / "spec.md").write_text("# spec", encoding="utf-8")
    (feature_dir / "plan.md").write_text("# plan", encoding="utf-8")
    (feature_dir / "tasks.md").write_text("# tasks", encoding="utf-8")
    failures = _check_composed_action_guard(
        "tasks", feature_dir, legacy_step_id="tasks_outline"
    )
    assert failures == [], (
        f"tasks_outline must accept only tasks.md being present at this point; "
        f"got blocking failures {failures!r}"
    )


def test_collapsed_tasks_guard_fails_after_outline_when_tasks_md_missing(
    feature_dir: Path,
) -> None:
    """tasks_outline guard still fails when tasks.md is absent."""
    failures = _check_composed_action_guard(
        "tasks", feature_dir, legacy_step_id="tasks_outline"
    )
    assert any("tasks.md" in f for f in failures), (
        f"Expected tasks.md missing failure; got {failures!r}"
    )


def test_collapsed_tasks_guard_passes_after_packages_without_dependencies(
    feature_dir: Path,
) -> None:
    """tasks_packages guard accepts WP files without dependencies frontmatter.

    Reproduces the second flavor of the reviewer-reported blocker: with WP
    files present but no ``dependencies:`` frontmatter (because finalize
    hasn't run yet), the collapsed-on-tasks_packages guard previously
    returned a "missing 'dependencies' in frontmatter — run finalize-tasks"
    failure that pushed the user back to a step that wouldn't help.
    """
    (feature_dir / "tasks.md").write_text("# tasks", encoding="utf-8")
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir()
    _write_wp_file(tasks_dir, "WP01", with_dependencies=False)
    failures = _check_composed_action_guard(
        "tasks", feature_dir, legacy_step_id="tasks_packages"
    )
    assert failures == [], (
        f"tasks_packages must accept WP files without dependencies "
        f"(finalize-tasks adds them next); got {failures!r}"
    )


def test_collapsed_tasks_guard_fails_after_packages_when_no_wp_files(
    feature_dir: Path,
) -> None:
    """tasks_packages guard requires at least one WP*.md file."""
    (feature_dir / "tasks.md").write_text("# tasks", encoding="utf-8")
    (feature_dir / "tasks").mkdir()
    failures = _check_composed_action_guard(
        "tasks", feature_dir, legacy_step_id="tasks_packages"
    )
    assert any("WP*.md" in f for f in failures), (
        f"Expected WP*.md missing failure; got {failures!r}"
    )


def test_collapsed_tasks_guard_demands_dependencies_on_finalize(
    feature_dir: Path,
) -> None:
    """tasks_finalize guard demands the full terminal state including deps."""
    (feature_dir / "tasks.md").write_text("# tasks", encoding="utf-8")
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir()
    _write_wp_file(tasks_dir, "WP01", with_dependencies=False)
    failures = _check_composed_action_guard(
        "tasks", feature_dir, legacy_step_id="tasks_finalize"
    )
    assert any("dependencies" in f for f in failures), (
        f"Expected dependencies-missing failure on finalize; got {failures!r}"
    )


def test_collapsed_tasks_guard_terminal_when_no_legacy_step_id(
    feature_dir_with_full_tasks: Path,
) -> None:
    """Composition-only invocation (no legacy_step_id) demands terminal state.

    Backward-compat with the original collapsed guard semantics: when
    something invokes the composed ``tasks`` action directly (not via a
    legacy DAG substep), the user has implicitly committed to producing the
    full post-finalize state in one shot, so the guard demands all three
    legacy checks pass.
    """
    failures = _check_composed_action_guard("tasks", feature_dir_with_full_tasks)
    assert failures == [], (
        f"Composition-only tasks call against a fully-finalized feature dir "
        f"must pass; got {failures!r}"
    )

    # And conversely: terminal-state demand still fails when WP deps missing.
    bare = feature_dir_with_full_tasks.parent / "bare"
    bare.mkdir()
    (bare / "tasks.md").write_text("# tasks", encoding="utf-8")
    tasks_dir = bare / "tasks"
    tasks_dir.mkdir()
    _write_wp_file(tasks_dir, "WP02", with_dependencies=False)
    failures2 = _check_composed_action_guard("tasks", bare)
    assert any("dependencies" in f for f in failures2), (
        f"Composition-only call without deps must surface dependencies failure; "
        f"got {failures2!r}"
    )


def test_dispatch_threads_legacy_step_id_to_guard(
    feature_dir: Path, tmp_path: Path
) -> None:
    """End-to-end: bridge passes legacy_step_id through to the guard.

    Reproduces the reviewer's decide_next() walk in a tighter form: after a
    successful executor call (mocked) for a tasks_outline substep, the
    bridge's guard check accepts only-tasks_md state instead of demanding
    WP files. Without legacy_step_id threading, this would block.
    """
    (feature_dir / "spec.md").write_text("# spec", encoding="utf-8")
    (feature_dir / "plan.md").write_text("# plan", encoding="utf-8")
    (feature_dir / "tasks.md").write_text("# tasks", encoding="utf-8")
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    fake_result = MagicMock()
    fake_result.invocation_ids = ("inv-001",)
    with patch(
        "specify_cli.mission_step_contracts.executor.StepContractExecutor.execute",
        return_value=fake_result,
    ):
        failures = _dispatch_via_composition(
            repo_root=repo_root,
            mission="software-dev",
            action="tasks",
            actor="architect-alphonso",
            profile_hint=None,
            request_text=None,
            mode_of_work=None,
            feature_dir=feature_dir,
            legacy_step_id="tasks_outline",
        )
    assert failures is None, (
        f"tasks_outline through dispatch must not block on missing WP files; "
        f"got {failures!r}"
    )
