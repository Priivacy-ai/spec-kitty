"""Dual-mode + manual dispatch + merge-eligibility contract (mission
``ci-pipeline-reinstatement-01M1X35E`` WP11, FR-018/FR-019/NFR-008,
SC-009/SC-010).

**Ownership boundary (binding, see the WP11 task file's "Owned_files
partition decision"):** this module is the ONE cross-cutting artefact that
ASSERTS the dual-mode contract against the on-disk reinstated-workflow SET.
It authors NO per-workflow mode/``if:``/``workflow_dispatch`` logic — that is
owned by each workflow-owning WP inside its own file (WP07 ``ci-router.yml``;
WP09 ``module-tests.yml``/``ci-modules.yml``; WP10 ``ci-aggregate.yml``; WP12
``sonar.yml``; WP13 ``ci-nightly.yml``; WP14 ``packs.yml``). This test reads
those files; it never edits them.

The reinstated-workflow SET this module asserts over is **discovered**, not
hardcoded to a fixed cardinality: :data:`REINSTATED_WORKFLOW_CANDIDATES` lists
every workflow this mission's plan (T4/D3, data-model.md E6) commits to
eventually reinstating, and each test filters that list down to the files
that actually exist on disk right now. WP11 depends only on the FOUNDATION
cluster + WP07 + WP09, so at WP11's landing time only ``ci-router.yml``,
``ci-modules.yml`` and ``module-tests.yml`` exist; the four still-pending
sibling workflows (``ci-aggregate.yml``, ``sonar.yml``, ``ci-nightly.yml``,
``packs.yml``) are silently skipped until their owning WPs land them, at
which point this module starts asserting over them automatically without a
code change here (the "on-disk workflow SET" the task file names).

Three invariants are pinned:

* **T057/T058 — dual-mode + dispatch threading.** Every present reinstated
  workflow declares ``workflow_dispatch``, threads a ``mode`` input
  (``pr``/``full``, default ``pr``), and realizes PR fail-fast / full
  run-all-regardless somewhere in its job graph (a matrix ``fail-fast``
  keyed off ``mode``, a per-shard mode branch, or an ``if: always()``
  terminal aggregator — the mechanism the file already uses).
* **T059 — skipped != green.** The terminal aggregator's own evaluation logic
  distinguishes a merely-``skipped`` dependency (not blocking) from a
  ``failure``/``cancelled`` one (blocking) — proven *behaviorally* by
  extracting the embedded evaluation script from the YAML and executing it
  with synthetic ``needs`` payloads, not just pattern-matching the source.

What this module does **not** and cannot prove: the short-circuit / run-all /
skipped-not-counted-green behaviors are GitHub *host* semantics (matrix
``fail-fast`` cancellation, branch-protection required-check treatment of a
``cancelled``/``skipped`` check). Those are provable only by a real dispatched
run — that evidence lives in
``kitty-specs/ci-pipeline-reinstatement-01M1X35E/dual-mode-dispatch-evidence.md``
(T060), honestly marked PENDING until this mission's workflows go live.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = pytest.mark.architectural

# tests/architectural/test_dual_mode_contract.py -> parents[2] is repo root.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_WORKFLOWS_DIR = _REPO_ROOT / ".github" / "workflows"

# Every workflow this mission's plan (T4) commits to reinstating with
# dual-mode + workflow_dispatch semantics. Discovered, not asserted whole:
# tests below filter this to whichever of these files exist on disk today.
REINSTATED_WORKFLOW_CANDIDATES: tuple[str, ...] = (
    "ci-router.yml",
    "ci-modules.yml",
    "module-tests.yml",
    "ci-aggregate.yml",
    "sonar.yml",
    "ci-nightly.yml",
    "packs.yml",
)

# WP11 claims only after FOUNDATION + WP07 + WP09 are approved/done, so these
# three MUST already be present when this test runs — this is the file's
# non-vacuity floor (and would be red, for the right reason, on any base that
# predates WP07/WP09 landing).
_MINIMUM_PRESENT_AT_WP11_CLAIM_TIME = frozenset({"ci-router.yml", "ci-modules.yml", "module-tests.yml"})

# YAML 1.1 parses the bare `on:` mapping key as the boolean True, not the
# string "on" -- every workflow file hits this, so triggers are looked up
# under either key.
_ON_KEYS: tuple[Any, ...] = ("on", True)


def _present_reinstated_workflows() -> list[Path]:
    """The subset of :data:`REINSTATED_WORKFLOW_CANDIDATES` that exist on disk."""
    return [_WORKFLOWS_DIR / name for name in REINSTATED_WORKFLOW_CANDIDATES if (_WORKFLOWS_DIR / name).is_file()]


def _load_workflow(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        doc = yaml.safe_load(fh)
    assert isinstance(doc, dict), f"{path}: workflow YAML did not parse to a mapping"
    return doc


def _triggers(workflow: dict[str, Any], path: Path) -> dict[str, Any]:
    for key in _ON_KEYS:
        if key in workflow:
            triggers = workflow[key]
            assert isinstance(triggers, dict), f"{path}: `on:` block is not a mapping"
            return triggers
    raise AssertionError(f"{path}: no `on:` trigger block found (checked keys {_ON_KEYS!r})")


def _mode_input(triggers: dict[str, Any], path: Path) -> dict[str, Any]:
    dispatch = triggers.get("workflow_dispatch")
    assert isinstance(dispatch, dict), f"{path}: workflow_dispatch has no `inputs:` block"
    inputs = dispatch.get("inputs")
    assert isinstance(inputs, dict), f"{path}: workflow_dispatch has no `inputs:` block"
    mode = inputs.get("mode")
    assert isinstance(mode, dict), f"{path}: workflow_dispatch.inputs has no `mode` input"
    return mode


_PRESENT_WORKFLOW_PATHS = _present_reinstated_workflows()
_PRESENT_WORKFLOW_IDS = [p.name for p in _PRESENT_WORKFLOW_PATHS]


# ---------------------------------------------------------------------------
# Non-vacuity floor: the reinstated-workflow SET this module asserts over is
# not empty, and the WP11-cluster-gate dependencies (WP07 ci-router.yml, WP09
# module-tests.yml/ci-modules.yml) are actually present. This is what would
# be red, for the right reason, if this test ran against a base that predates
# those WPs landing (mode wiring / workflow_dispatch absent because the files
# themselves are absent).
# ---------------------------------------------------------------------------
def test_wp07_wp09_reinstated_workflows_are_present() -> None:
    present_names = {p.name for p in _PRESENT_WORKFLOW_PATHS}
    missing = _MINIMUM_PRESENT_AT_WP11_CLAIM_TIME - present_names
    assert not missing, (
        f"WP11 claims only after WP07 (ci-router.yml) + WP09 (module-tests.yml/ci-modules.yml) are approved/done; missing on disk: {sorted(missing)}"
    )
    assert present_names, "no reinstated workflow files found under .github/workflows/"


@pytest.mark.parametrize("workflow_path", _PRESENT_WORKFLOW_PATHS, ids=_PRESENT_WORKFLOW_IDS)
def test_every_present_reinstated_workflow_declares_workflow_dispatch(
    workflow_path: Path,
) -> None:
    """T058 / SC-010 / C-009: manual dispatch on every reinstated workflow."""
    workflow = _load_workflow(workflow_path)
    triggers = _triggers(workflow, workflow_path)
    assert "workflow_dispatch" in triggers, f"{workflow_path.name}: missing workflow_dispatch trigger (SC-010/C-009)"


@pytest.mark.parametrize("workflow_path", _PRESENT_WORKFLOW_PATHS, ids=_PRESENT_WORKFLOW_IDS)
def test_every_present_reinstated_workflow_threads_a_pr_full_mode_input(
    workflow_path: Path,
) -> None:
    """T057: the `mode` input (pr/full) is threaded via dispatch.

    The ``pr`` default (path-scoped fail-fast) is the ordinary case only for
    PR-triggered workflows. A schedule/dispatch-only workflow (the nightly
    ``ci-nightly.yml`` / ``sonar.yml``) never runs per-PR, so its scheduled runs
    are full-mode *by cadence* and it may default ``mode`` to ``full``; the
    input still offers both options either way.
    """
    workflow = _load_workflow(workflow_path)
    triggers = _triggers(workflow, workflow_path)
    mode = _mode_input(triggers, workflow_path)
    is_pr_triggered = "pull_request" in triggers or "push" in triggers
    default = mode.get("default")
    if is_pr_triggered:
        assert default == "pr", (
            f"{workflow_path.name}: PR-triggered workflow's mode input default must be 'pr' "
            "(path-scoped fail-fast is the ordinary per-PR case; full run-all is opt-in)"
        )
    else:
        assert default in {"pr", "full"}, (
            f"{workflow_path.name}: schedule/dispatch-only workflow mode default "
            f"must be 'pr' or 'full', got {default!r}"
        )
    mode_type = mode.get("type")
    if mode_type == "choice":
        options = mode.get("options")
        assert isinstance(options, list) and set(options) >= {"pr", "full"}, (
            f"{workflow_path.name}: mode choice options must include both 'pr' and 'full', got {options!r}"
        )


# ---------------------------------------------------------------------------
# T057 — concrete PR-fail-fast / full-run-all mechanisms, per file.
# ---------------------------------------------------------------------------


def test_ci_modules_matrix_fail_fast_is_keyed_off_mode() -> None:
    """ci-modules.yml (WP09): `fail-fast: mode != 'full'` is the literal PR
    short-circuit (cancel remaining matrix legs on the first red shard) vs
    full run-all-regardless mechanism (data-model.md E6, research.md D3)."""
    path = _WORKFLOWS_DIR / "ci-modules.yml"
    if not path.is_file():
        pytest.skip("ci-modules.yml not yet reinstated")
    workflow = _load_workflow(path)
    test_job = workflow["jobs"]["test"]
    strategy = test_job.get("strategy")
    assert isinstance(strategy, dict), "ci-modules.yml: job `test` has no `strategy:` block"
    fail_fast_expr = strategy.get("fail-fast")
    assert isinstance(fail_fast_expr, str), (
        "ci-modules.yml: `strategy.fail-fast` must be an expression, not a hardcoded boolean, so PR mode fails fast and full mode does not"
    )
    assert "mode" in fail_fast_expr and "full" in fail_fast_expr, f"ci-modules.yml: strategy.fail-fast ({fail_fast_expr!r}) is not keyed off the mode input"
    # PR mode (mode != 'full') must resolve fail-fast=true; full mode must
    # resolve fail-fast=false. Confirm the expression's polarity directly.
    assert "!=" in fail_fast_expr, (
        f"ci-modules.yml: strategy.fail-fast ({fail_fast_expr!r}) must be a "
        "negated equality against 'full' so pr (or an empty/default mode) "
        "resolves fail-fast=true"
    )


def test_module_tests_shard_run_step_branches_pr_fail_fast_vs_full_run_all() -> None:
    """module-tests.yml (WP09): the per-shard pytest run step propagates the
    real exit status in pr mode (fail fast) but only warns and continues in
    full mode (run-all-regardless); artefact upload always runs regardless of
    shard outcome so full mode reports every failure (SC-009)."""
    path = _WORKFLOWS_DIR / "module-tests.yml"
    if not path.is_file():
        pytest.skip("module-tests.yml not yet reinstated")
    workflow = _load_workflow(path)
    steps = workflow["jobs"]["test"]["steps"]
    run_step = next((s for s in steps if s.get("name") == "Run pytest for this shard"), None)
    assert run_step is not None, "module-tests.yml: missing 'Run pytest for this shard' step"
    run_script = run_step["run"]
    assert 'mode" = "full"' in run_script.replace("$mode", "mode"), "module-tests.yml: run step does not branch on mode"
    assert 'exit "$status"' in run_script, "module-tests.yml: pr-mode branch must propagate the real pytest exit status"

    upload_step = next(
        (s for s in steps if s.get("name") == "Upload coverage + xunit artefacts"),
        None,
    )
    assert upload_step is not None, "module-tests.yml: missing artefact-upload step"
    assert upload_step.get("if") == "always()", (
        "module-tests.yml: artefact upload must be if: always() so full mode reports every shard's failure, not just the first"
    )


def test_ci_router_terminal_gate_declares_if_always_not_cancelled() -> None:
    """ci-router.yml (WP07): the terminal `router-gate` aggregator must
    evaluate regardless of whether any upstream job failed, was cancelled, or
    was skipped by path-scoping -- otherwise a failure upstream would just
    skip the gate itself rather than let it render a verdict."""
    path = _WORKFLOWS_DIR / "ci-router.yml"
    if not path.is_file():
        pytest.skip("ci-router.yml not yet reinstated")
    workflow = _load_workflow(path)
    gate_job = workflow["jobs"]["router-gate"]
    condition = gate_job.get("if", "")
    assert "always()" in condition, f"ci-router.yml: router-gate `if:` ({condition!r}) must contain always()"


# ---------------------------------------------------------------------------
# T059 — merge-eligibility: skipped != green, proven behaviorally.
#
# We do not just pattern-match the embedded evaluation script's source; we
# extract it and execute it with synthetic `needs` context payloads so the
# assertion is about behavior, not text.
# ---------------------------------------------------------------------------

_HEREDOC_PATTERN = re.compile(r"<<'PY'\n(.*?)\nPY", re.DOTALL)


def _extract_router_gate_script(workflow: dict[str, Any]) -> str:
    run_text = workflow["jobs"]["router-gate"]["steps"][0]["run"]
    match = _HEREDOC_PATTERN.search(run_text)
    assert match is not None, "ci-router.yml: could not extract the router-gate evaluation script from its `<<'PY' ... PY` heredoc"
    return match.group(1)


def _run_router_gate_script(script: str, needs: dict[str, dict[str, str]], mode: str, tmp_path: Path) -> subprocess.CompletedProcess[str]:
    script_path = tmp_path / "router_gate_eval.py"
    script_path.write_text(script, encoding="utf-8")
    env = dict(os.environ)
    env["NEEDS_JSON"] = json.dumps(needs)
    env["MODE"] = mode
    return subprocess.run(
        [sys.executable, str(script_path)],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


@pytest.fixture(scope="module")
def router_gate_script() -> str | None:
    path = _WORKFLOWS_DIR / "ci-router.yml"
    if not path.is_file():
        return None
    workflow = _load_workflow(path)
    return _extract_router_gate_script(workflow)


def test_router_gate_treats_merely_skipped_dependency_as_not_blocking(router_gate_script: str | None, tmp_path: Path) -> None:
    """A dependency skipped because it was not selected for this diff (e.g.
    path-scoped routing) must NOT block the terminal gate."""
    if router_gate_script is None:
        pytest.skip("ci-router.yml not yet reinstated")
    needs = {
        "changes": {"result": "success"},
        "ruff": {"result": "success"},
        "tests-e2e": {"result": "skipped"},
    }
    result = _run_router_gate_script(router_gate_script, needs, mode="pr", tmp_path=tmp_path)
    assert result.returncode == 0, f"router-gate: a merely-skipped dependency must not block; stdout={result.stdout!r} stderr={result.stderr!r}"
    assert "router-gate OK" in result.stdout


@pytest.mark.parametrize("blocking_result", ["failure", "cancelled"])
def test_router_gate_treats_failure_and_cancelled_as_blocking(router_gate_script: str | None, tmp_path: Path, blocking_result: str) -> None:
    """FR-019: a dependency that genuinely failed, or was cancelled by a
    short-circuit (e.g. a fail-fast matrix elsewhere), must count as
    blocking -- it must never be silently treated as green."""
    if router_gate_script is None:
        pytest.skip("ci-router.yml not yet reinstated")
    needs = {
        "changes": {"result": "success"},
        "ruff": {"result": blocking_result},
        "tests-e2e": {"result": "skipped"},
    }
    result = _run_router_gate_script(router_gate_script, needs, mode="pr", tmp_path=tmp_path)
    assert result.returncode != 0, f"router-gate: a dependency reporting {blocking_result!r} must block the gate; stdout={result.stdout!r} stderr={result.stderr!r}"
    assert "blocking job(s)" in result.stderr


def test_router_gate_passes_clean_when_every_dependency_succeeded(router_gate_script: str | None, tmp_path: Path) -> None:
    if router_gate_script is None:
        pytest.skip("ci-router.yml not yet reinstated")
    needs = {"changes": {"result": "success"}, "ruff": {"result": "success"}}
    result = _run_router_gate_script(router_gate_script, needs, mode="full", tmp_path=tmp_path)
    assert result.returncode == 0
    assert "mode=full" in result.stdout
