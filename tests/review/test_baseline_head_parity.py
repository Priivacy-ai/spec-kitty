"""Baseline<->head parity across BOTH ``ScopeSource`` implementations (T024,
mission ``scopesource-gate-followup-01KY6S9P`` WP04, FR-010/FR-014).

Proves ``capture_baseline`` (WP03) and ``evaluate_pre_review_gate`` (this WP)
land in ONE shared failure-identity namespace for a REAL repo — the SAME
committed script/test producing the SAME failure identity on both sides
never false-mismatches and never false-``NEW_FAILURES``. Four combinations:

1. ``GateCoverageScopeSource`` — real pytest subprocess, JUnit (its only
   parse mode) — scope_source injected directly.
2. ``GateCoverageScopeSource`` — SAME shape, but the HEAD-side source is
   resolved through ``tasks_move_task._mt_resolve_scope_source`` (the REAL
   production wrapper), proving the FR-014 rewire (T024 step 1) is actually
   wired — a direct-injection-only suite would pass even with the head path
   un-rewired onto the factory.
3. ``DeclaredCommandScopeSource`` — worktree-relative JUnit (the B1 case,
   ``test_baseline_lifecycle.py``'s T016 shape).
4. ``DeclaredCommandScopeSource`` — FAIL-text convention (no JUnit artifact).

Plus the SC-004 mismatch demo: a baseline captured under ONE source's
identity, diffed against a head evaluated under the OTHER -> SOURCE_MISMATCH.

Plus (issue #3611) a diverging-roots case: capture-time resolves
``ScopeSource`` selection against the planning root (``main_repo_root``,
mirroring ``implement_capture_baseline``'s
``resolve_scope_source(main_repo_root)``), while the head-side gate
resolves selection through ``_mt_resolve_transition_gate_inputs`` /
``_TransitionGateInputs.scope_source_root`` -- which must ALSO be
``main_repo_root``, never the lane worktree the tests actually run in
(``gate_repo_root``). All four combos above share a single implicit root
(capture and head evaluated in the SAME repo), which is exactly the gap
that let the two call sites drift onto different roots in production
without any of the existing parity coverage noticing.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Any

import pytest

from specify_cli.cli.commands.agent import tasks_move_task as tmt
from specify_cli.review.baseline import BaselineTestResult, capture_baseline
from specify_cli.review.pre_review_gate import GateOutcome, evaluate_pre_review_gate
from specify_cli.review.scope_source import (
    DeclaredCommandScopeSource,
    GateCoverageScopeSource,
    ScopeSource,
    resolve_scope_source,
)

pytestmark = [pytest.mark.git_repo]

_MISSION_SLUG = "scopesource-gate-followup-01KY6S9P"


def _init_git_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, check=True)


def _write_file(repo: Path, relative_path: str, content: str) -> None:
    target = repo / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def _git_commit_all(path: Path, message: str) -> None:
    subprocess.run(["git", "add", "-A"], cwd=path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", message], cwd=path, check=True)


def _capture(repo: Path, *, wp_slug: str, scope_source: ScopeSource) -> BaselineTestResult | None:
    feature_dir = repo.parent / "kitty-specs" / _MISSION_SLUG
    return capture_baseline(
        worktree_path=repo,
        base_branch="main",
        wp_id="WP04",
        mission_slug=_MISSION_SLUG,
        feature_dir=feature_dir,
        wp_slug=wp_slug,
        scope_source=scope_source,
    )


# ---------------------------------------------------------------------------
# Combos 1/2 — GateCoverageScopeSource (real pytest subprocess, JUnit)
# ---------------------------------------------------------------------------

_GIT_CHANGED_FILE = "src/specify_cli/git/foo.py"
_GATE_COVERAGE_GROUPS = {"auth_audit_git": ("src/specify_cli/git/**",)}
_GATE_COVERAGE_ROUTING = {"git": (None, None, ("test_sample.py",))}


def _build_gate_coverage_repo(tmp_path: Path) -> Path:
    """A real repo with one committed, always-failing pytest test file.

    No ``review.test_command`` is configured, so ``resolve_scope_source``
    (and ``_mt_resolve_scope_source``) both route to
    ``GateCoverageScopeSource`` — the pytest-shaped-repo default (FR-014).
    """
    repo = tmp_path / "gate-coverage-repo"
    _init_git_repo(repo)
    _write_file(
        repo,
        "test_sample.py",
        "def test_pass():\n    assert True\n\n\ndef test_break():\n    assert False, 'boom'\n",
    )
    _git_commit_all(repo, "base commit with a failing pytest test")
    return repo


def test_gate_coverage_scope_source_baseline_head_parity_direct_injection(tmp_path: Path) -> None:
    repo = _build_gate_coverage_repo(tmp_path)
    baseline_source = GateCoverageScopeSource(repo_root=repo)
    baseline = _capture(repo, wp_slug="WP04-gc-direct", scope_source=baseline_source)
    assert baseline is not None
    assert baseline.source_identity == "GateCoverageScopeSource/junit_xml"

    head_source = GateCoverageScopeSource(
        repo_root=repo,
        filter_groups_override=_GATE_COVERAGE_GROUPS,
        composite_routing_override=_GATE_COVERAGE_ROUTING,
    )
    verdict = evaluate_pre_review_gate(
        [_GIT_CHANGED_FILE], repo_root=repo, baseline=baseline, scope_source=head_source,
    )

    # Same failing test on both sides -> pre-existing, never NEW_FAILURES,
    # and never SOURCE_MISMATCH -- the shared failure-identity namespace holds.
    assert verdict.outcome is GateOutcome.NO_NEW_FAILURES
    assert any("test_break" in f.test for f in verdict.pre_existing_failures)


def test_gate_coverage_scope_source_baseline_head_parity_through_the_real_wrapper(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T024 step 3: drives the HEAD side through ``_mt_resolve_scope_source``
    itself (not direct injection) -- so a future un-rewire (back onto a
    hard-constructed ``GateCoverageScopeSource`` with no factory delegation,
    or worse, a regression that silently selects the WRONG source) would be
    caught here even though a direct-injection-only test would not notice."""
    repo = _build_gate_coverage_repo(tmp_path)
    baseline = _capture(repo, wp_slug="WP04-gc-wrapper", scope_source=GateCoverageScopeSource(repo_root=repo))
    assert baseline is not None

    monkeypatch.setattr(tmt, "_pre_review_gate_filter_groups", lambda: _GATE_COVERAGE_GROUPS)
    monkeypatch.setattr(tmt, "_pre_review_gate_composite_routing", lambda: _GATE_COVERAGE_ROUTING)

    head_source = tmt._mt_resolve_scope_source(repo)
    assert isinstance(head_source, GateCoverageScopeSource), (
        "the real wrapper must resolve a pytest-shaped repo to GateCoverageScopeSource"
    )

    verdict = evaluate_pre_review_gate(
        [_GIT_CHANGED_FILE], repo_root=repo, baseline=baseline, scope_source=head_source,
    )

    assert verdict.outcome is GateOutcome.NO_NEW_FAILURES
    assert any("test_break" in f.test for f in verdict.pre_existing_failures)


# ---------------------------------------------------------------------------
# Combos 3/4 — DeclaredCommandScopeSource (worktree-relative JUnit / FAIL-text)
# ---------------------------------------------------------------------------

_JUNIT_SCRIPT = textwrap.dedent(
    """\
    import sys
    from pathlib import Path

    JUNIT_XML = (
        '<?xml version="1.0" encoding="utf-8"?>\\n'
        '<testsuites>\\n'
        '  <testsuite name="pytest" tests="1" failures="1" errors="0" skipped="0">\\n'
        '    <testcase classname="tests.test_thing" name="test_boom" '
        'file="tests/test_thing.py" line="3">\\n'
        '      <failure message="AssertionError: boom">AssertionError: boom</failure>\\n'
        '    </testcase>\\n'
        '  </testsuite>\\n'
        '</testsuites>\\n'
    )

    # Issue #3612: the command declares --junitxml={output_file}, substituted
    # by DeclaredCommandScopeSource.test_command() into a REAL absolute path
    # (this source's own _output_file) -- read it back from argv rather than
    # hardcoding a worktree-relative literal, so this fixture exercises the
    # ACTUAL substitution path instead of a pre-#3612 relative-filename
    # convention argv-sniffing can no longer see through the shell wrap.
    junit_arg = next(a for a in sys.argv if a.startswith("--junitxml="))
    Path(junit_arg.split("=", 1)[1]).write_text(JUNIT_XML, encoding="utf-8")
    sys.exit(1)
    """
)

_FAIL_TEXT_SCRIPT = "print('FAIL tests.test_thing.test_boom: boom')\nraise SystemExit(1)\n"


def _build_declared_command_repo(tmp_path: Path, *, script_name: str, script_body: str) -> Path:
    repo = tmp_path / f"declared-command-repo-{script_name}"
    _init_git_repo(repo)
    _write_file(repo, script_name, script_body)
    test_command = (
        f"{sys.executable} {script_name} --junitxml={{output_file}}"
        if script_name.endswith("junit.py")
        else f"{sys.executable} {script_name}"
    )
    _write_file(repo, ".kittify/config.yaml", f"review:\n  test_command: {test_command!r}\n")
    _git_commit_all(repo, "base commit with a declared test command")
    return repo


def test_declared_command_scope_source_worktree_relative_junit_parity(tmp_path: Path) -> None:
    repo = _build_declared_command_repo(tmp_path, script_name="write_junit.py", script_body=_JUNIT_SCRIPT)
    baseline = _capture(repo, wp_slug="WP04-dc-junit", scope_source=DeclaredCommandScopeSource(repo_root=repo))
    assert baseline is not None
    assert baseline.source_identity == "DeclaredCommandScopeSource/junit_xml"
    assert baseline.failures and baseline.failures[0].test == "tests.test_thing.test_boom"

    verdict = evaluate_pre_review_gate(
        ["anything/at/all.rb"],
        repo_root=repo,
        baseline=baseline,
        scope_source=DeclaredCommandScopeSource(repo_root=repo),
    )

    assert verdict.outcome is GateOutcome.NO_NEW_FAILURES
    assert any(f.test == "tests.test_thing.test_boom" for f in verdict.pre_existing_failures)


def test_declared_command_scope_source_fail_text_parity(tmp_path: Path) -> None:
    repo = _build_declared_command_repo(tmp_path, script_name="run_tests.py", script_body=_FAIL_TEXT_SCRIPT)
    baseline = _capture(repo, wp_slug="WP04-dc-text", scope_source=DeclaredCommandScopeSource(repo_root=repo))
    assert baseline is not None
    assert baseline.source_identity == "DeclaredCommandScopeSource/text"
    assert baseline.failures and baseline.failures[0].test == "tests.test_thing.test_boom"

    verdict = evaluate_pre_review_gate(
        ["anything/at/all.rb"],
        repo_root=repo,
        baseline=baseline,
        scope_source=DeclaredCommandScopeSource(repo_root=repo),
    )

    assert verdict.outcome is GateOutcome.NO_NEW_FAILURES
    assert any(f.test == "tests.test_thing.test_boom" for f in verdict.pre_existing_failures)


# ---------------------------------------------------------------------------
# SC-004 — deliberately mismatched pair
# ---------------------------------------------------------------------------


def test_deliberately_mismatched_pair_raises_source_mismatch(tmp_path: Path) -> None:
    """A baseline captured under ``GateCoverageScopeSource`` diffed against a
    head evaluated under ``DeclaredCommandScopeSource`` -- the mission's own
    bug re-skinned if T024's rewire is skipped (head stays on
    ``GateCoverageScopeSource`` while a config-driven baseline uses the
    selected source) -- must surface as ``SOURCE_MISMATCH``, never a false
    ``NEW_FAILURES``/``NO_NEW_FAILURES``."""
    gate_repo = _build_gate_coverage_repo(tmp_path)
    baseline = _capture(gate_repo, wp_slug="WP04-mismatch", scope_source=GateCoverageScopeSource(repo_root=gate_repo))
    assert baseline is not None
    assert baseline.source_identity == "GateCoverageScopeSource/junit_xml"

    declared_repo = _build_declared_command_repo(tmp_path, script_name="write_junit.py", script_body=_JUNIT_SCRIPT)
    verdict = evaluate_pre_review_gate(
        ["anything/at/all.rb"],
        repo_root=declared_repo,
        baseline=baseline,
        scope_source=DeclaredCommandScopeSource(repo_root=declared_repo),
    )

    assert verdict.outcome is GateOutcome.SOURCE_MISMATCH
    assert "GateCoverageScopeSource/junit_xml" in (verdict.reason or "")
    assert "DeclaredCommandScopeSource/junit_xml" in (verdict.reason or "")


# ---------------------------------------------------------------------------
# Combo 5 (issue #3611) — diverging capture-root vs. head-root
# ---------------------------------------------------------------------------


def _make_move_task_state(**overrides: Any) -> tmt._MoveTaskState:
    """Minimal ``_MoveTaskState`` builder, mirroring the escape-hatch suite's
    ``_make_state`` helper (``test_tasks_move_task_pre_review_gate_escape_hatch.py``)."""
    kwargs: dict[str, Any] = {
        "task_id": "WP04",
        "to": "for_review",
        "mission": _MISSION_SLUG,
        "agent": "claude",
        "assignee": None,
        "shell_pid": None,
        "note": None,
        "review_feedback_file": None,
        "approval_ref": None,
        "reviewer": None,
        "self_review_fallback": False,
        "intended_reviewer": None,
        "reviewer_failure_reason": None,
        "done_override_reason": None,
        "force": False,
        "tracker_ref": None,
        "skip_review_artifact_check": False,
        "auto_commit": None,
        "json_output": False,
        "skip_pre_review_gate": False,
    }
    field_names = set(tmt._MoveTaskState.__dataclass_fields__)
    field_overrides = {k: v for k, v in overrides.items() if k in kwargs}
    kwargs.update(field_overrides)
    st = tmt._MoveTaskState(**kwargs)
    for key, value in overrides.items():
        if key not in field_overrides:
            assert key in field_names, f"unknown _MoveTaskState field: {key!r}"
            setattr(st, key, value)
    return st


def test_scope_source_resolves_from_planning_root_not_lane_worktree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """#3611: capture-time and head-time selection must share ONE root.

    A lane worktree is branched off ``main`` BEFORE ``review.test_command``
    is committed, so the worktree's own checked-out ``.kittify/config.yaml``
    never gains the key. Capture-time (mirroring
    ``implement_capture_baseline``) resolves ``resolve_scope_source`` against
    ``main_repo_root`` and gets ``DeclaredCommandScopeSource``. The head gate
    must resolve the SAME source -- via
    ``_mt_resolve_transition_gate_inputs``'s ``scope_source_root`` field,
    which is always ``st.main_repo_root``, never the lane worktree used for
    ``gate_repo_root`` (where the scoped test subprocess actually runs).

    Before the #3611 fix, ``_TransitionGateInputs`` had no
    ``scope_source_root`` field at all and resolved selection from
    ``gate_repo_root`` (the worktree) -- picking ``GateCoverageScopeSource``
    while the baseline used ``DeclaredCommandScopeSource``, a divergence the
    ``SOURCE_MISMATCH`` check never even gets to compare (each side computes
    an identity from an incomparable, wrongly-selected source).
    """
    main_repo_root = _build_declared_command_repo(
        tmp_path, script_name="write_junit.py", script_body=_JUNIT_SCRIPT
    )

    # `_build_declared_command_repo` commits script + config together in a
    # single commit, so there is no pre-config commit to branch a lane
    # worktree from on this repo shape. Simulate the real-world divergence
    # directly instead: the lane worktree's OWN checked-out config.yaml is
    # rewritten to omit `review.test_command`, exactly the observable state
    # a lane branch cut before the config change would have.
    lane_worktree = tmp_path / "lane-worktree-3611"
    subprocess.run(
        ["git", "worktree", "add", "-b", "lane/wp04-3611", str(lane_worktree), "main"],
        cwd=main_repo_root, check=True, capture_output=True,
    )
    (lane_worktree / ".kittify" / "config.yaml").unlink()

    capture_source = resolve_scope_source(main_repo_root)
    assert isinstance(capture_source, DeclaredCommandScopeSource)

    baseline = _capture(main_repo_root, wp_slug="WP04-3611-capture", scope_source=capture_source)
    assert baseline is not None
    assert baseline.source_identity == "DeclaredCommandScopeSource/junit_xml"

    st = _make_move_task_state()
    st.main_repo_root = main_repo_root
    st.target_branch = "main"
    st.mission_slug = _MISSION_SLUG
    monkeypatch.setattr(tmt, "_mt_resolve_pre_review_workspace", lambda _st: lane_worktree)

    inputs, _dirty_before = tmt._mt_resolve_transition_gate_inputs(st)
    assert inputs.gate_repo_root == lane_worktree

    head_source = tmt._mt_resolve_scope_source(inputs.scope_source_root)
    assert isinstance(head_source, DeclaredCommandScopeSource), (
        "head-side selection must match capture-time selection (SAME root), "
        f"got {type(head_source).__name__} instead"
    )

    verdict = evaluate_pre_review_gate(
        ["anything/at/all.rb"],
        repo_root=inputs.gate_repo_root,
        baseline=baseline,
        scope_source=head_source,
    )

    assert verdict.outcome is GateOutcome.NO_NEW_FAILURES
    assert any(f.test == "tests.test_thing.test_boom" for f in verdict.pre_existing_failures)

    subprocess.run(
        ["git", "worktree", "remove", str(lane_worktree), "--force"],
        cwd=main_repo_root, check=False, capture_output=True,
    )
