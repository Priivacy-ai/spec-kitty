# FR-009 Marker Census — tasks-domain CI gate visibility

**Mission**: tasks-py-degod-wave2-01KWH9EQ · **WP10 / T044** · Generated: 2026-07-02
**Tree**: lane-j worktree containing all WP01–WP09 approved work (the mission's final file set).

## Scope (the FR-009 glob — fixed, verbatim)

- `tests/tasks/**`
- `tests/specify_cli/cli/commands/agent/test_tasks*`
- `tests/architectural/test_tasks_command_surface.py` (mission-added)
- `tests/architectural/test_tasks_domain_gate_visibility.py` (mission-added, WP10/T045)

Every test file this mission added is inside this set: the byte-freeze suite
(`test_tasks_json_bytes.py`), the six seam suites (`test_tasks_shared_seam.py`,
`test_tasks_move_task_seam.py`, `test_tasks_map_requirements_seam.py`,
`test_tasks_status_cmd_seam.py`, `test_tasks_mark_status_seam.py`,
`test_tasks_finalize_seam.py`), and the two architectural gate files.

## Method

The census reuses the canonical CI-selection model
(`tests/architectural/_gate_coverage.py`, Issue #2034/#1933): a one-pass
`--collect-only` with the marker-dump plugin records every test's *effective*
markers exactly as pytest's `-m` evaluator sees them (`item.iter_markers()` —
so any conftest auto-marking would be included), then every test is evaluated
against every parsed CI gate (`ci-quality.yml` / `ci-windows.yml` /
`drift-detector.yml` / `release.yml`) using pytest's own marker-expression
evaluator.

Conftest check: the only `pytest_collection_modifyitems` on the path
(`tests/conftest.py`) adds *skip* markers (`windows_ci` off-platform,
`quarantine`) — it adds no selection markers, so the per-file `pytestmark`
lines below are the effective selection markers. Neither `tests/tasks/conftest.py`
nor `tests/specify_cli/cli/commands/agent/conftest.py` auto-marks.

## Census

| file | markers | selecting gate(s) |
|------|---------|-------------------|
| `tests/architectural/test_tasks_command_surface.py` | `architectural`, `fast` | `ci-quality.yml::fast-tests-core-misc` -m "fast and not windows_ci"<br>`ci-quality.yml::integration-tests-core-misc (shard: architectural)` -m "not windows_ci and (git_repo or integration or architectural)" |
| `tests/architectural/test_tasks_domain_gate_visibility.py` | `architectural`, `fast` | `ci-quality.yml::fast-tests-core-misc` -m "fast and not windows_ci"<br>`ci-quality.yml::integration-tests-core-misc (shard: architectural)` -m "not windows_ci and (git_repo or integration or architectural)" |
| `tests/specify_cli/cli/commands/agent/test_tasks.py` | `fast` | `ci-quality.yml::fast-tests-cli` -m "fast and not windows_ci"<br>`ci-quality.yml::fast-tests-core-misc` -m "fast and not windows_ci" |
| `tests/specify_cli/cli/commands/agent/test_tasks_backward_emit.py` | `fast` | `ci-quality.yml::fast-tests-cli` -m "fast and not windows_ci"<br>`ci-quality.yml::fast-tests-core-misc` -m "fast and not windows_ci" |
| `tests/specify_cli/cli/commands/agent/test_tasks_canonical_cleanup.py` | `fast` | `ci-quality.yml::fast-tests-cli` -m "fast and not windows_ci"<br>`ci-quality.yml::fast-tests-core-misc` -m "fast and not windows_ci" |
| `tests/specify_cli/cli/commands/agent/test_tasks_cli_contract.py` | `fast` | `ci-quality.yml::fast-tests-cli` -m "fast and not windows_ci"<br>`ci-quality.yml::fast-tests-core-misc` -m "fast and not windows_ci" |
| `tests/specify_cli/cli/commands/agent/test_tasks_cli_contract_coord.py` | `git_repo`, `integration` | `ci-quality.yml::integration-tests-cli` -m "not windows_ci and (git_repo or integration)"<br>`ci-quality.yml::integration-tests-core-misc (shard: specify-cli-rest)` -m "not windows_ci and (git_repo or integration or architectural)" |
| `tests/specify_cli/cli/commands/agent/test_tasks_core_backed_orchestration.py` | `fast` | `ci-quality.yml::fast-tests-cli` -m "fast and not windows_ci"<br>`ci-quality.yml::fast-tests-core-misc` -m "fast and not windows_ci" |
| `tests/specify_cli/cli/commands/agent/test_tasks_coreless_orchestration.py` | `fast` | `ci-quality.yml::fast-tests-cli` -m "fast and not windows_ci"<br>`ci-quality.yml::fast-tests-core-misc` -m "fast and not windows_ci" |
| `tests/specify_cli/cli/commands/agent/test_tasks_dependency_readiness.py` | `fast`, `unit` | `ci-quality.yml::fast-tests-cli` -m "fast and not windows_ci"<br>`ci-quality.yml::fast-tests-core-misc` -m "fast and not windows_ci" |
| `tests/specify_cli/cli/commands/agent/test_tasks_finalize_seam.py` | `fast` | `ci-quality.yml::fast-tests-cli` -m "fast and not windows_ci"<br>`ci-quality.yml::fast-tests-core-misc` -m "fast and not windows_ci" |
| `tests/specify_cli/cli/commands/agent/test_tasks_finalize_validation.py` | `fast`, `unit` | `ci-quality.yml::fast-tests-cli` -m "fast and not windows_ci"<br>`ci-quality.yml::fast-tests-core-misc` -m "fast and not windows_ci" |
| `tests/specify_cli/cli/commands/agent/test_tasks_json_bytes.py` | `fast` | `ci-quality.yml::fast-tests-cli` -m "fast and not windows_ci"<br>`ci-quality.yml::fast-tests-core-misc` -m "fast and not windows_ci" |
| `tests/specify_cli/cli/commands/agent/test_tasks_map_requirements_seam.py` | `fast` | `ci-quality.yml::fast-tests-cli` -m "fast and not windows_ci"<br>`ci-quality.yml::fast-tests-core-misc` -m "fast and not windows_ci" |
| `tests/specify_cli/cli/commands/agent/test_tasks_mapping_core.py` | `fast` | `ci-quality.yml::fast-tests-cli` -m "fast and not windows_ci"<br>`ci-quality.yml::fast-tests-core-misc` -m "fast and not windows_ci" |
| `tests/specify_cli/cli/commands/agent/test_tasks_mark_status.py` | `fast`, `unit` | `ci-quality.yml::fast-tests-cli` -m "fast and not windows_ci"<br>`ci-quality.yml::fast-tests-core-misc` -m "fast and not windows_ci" |
| `tests/specify_cli/cli/commands/agent/test_tasks_mark_status_seam.py` | `fast` | `ci-quality.yml::fast-tests-cli` -m "fast and not windows_ci"<br>`ci-quality.yml::fast-tests-core-misc` -m "fast and not windows_ci" |
| `tests/specify_cli/cli/commands/agent/test_tasks_materialization.py` | `fast`, `unit` | `ci-quality.yml::fast-tests-cli` -m "fast and not windows_ci"<br>`ci-quality.yml::fast-tests-core-misc` -m "fast and not windows_ci" |
| `tests/specify_cli/cli/commands/agent/test_tasks_move_task_seam.py` | `fast` | `ci-quality.yml::fast-tests-cli` -m "fast and not windows_ci"<br>`ci-quality.yml::fast-tests-core-misc` -m "fast and not windows_ci" |
| `tests/specify_cli/cli/commands/agent/test_tasks_outline.py` | `fast`, `unit` | `ci-quality.yml::fast-tests-cli` -m "fast and not windows_ci"<br>`ci-quality.yml::fast-tests-core-misc` -m "fast and not windows_ci" |
| `tests/specify_cli/cli/commands/agent/test_tasks_parsing_validation.py` | `fast` | `ci-quality.yml::fast-tests-cli` -m "fast and not windows_ci"<br>`ci-quality.yml::fast-tests-core-misc` -m "fast and not windows_ci" |
| `tests/specify_cli/cli/commands/agent/test_tasks_planning_artifact_lifecycle.py` | `fast` | `ci-quality.yml::fast-tests-cli` -m "fast and not windows_ci"<br>`ci-quality.yml::fast-tests-core-misc` -m "fast and not windows_ci" |
| `tests/specify_cli/cli/commands/agent/test_tasks_ports.py` | `fast` | `ci-quality.yml::fast-tests-cli` -m "fast and not windows_ci"<br>`ci-quality.yml::fast-tests-core-misc` -m "fast and not windows_ci" |
| `tests/specify_cli/cli/commands/agent/test_tasks_shared_seam.py` | `fast` | `ci-quality.yml::fast-tests-cli` -m "fast and not windows_ci"<br>`ci-quality.yml::fast-tests-core-misc` -m "fast and not windows_ci" |
| `tests/specify_cli/cli/commands/agent/test_tasks_status_cmd_seam.py` | `fast` | `ci-quality.yml::fast-tests-cli` -m "fast and not windows_ci"<br>`ci-quality.yml::fast-tests-core-misc` -m "fast and not windows_ci" |
| `tests/specify_cli/cli/commands/agent/test_tasks_status_progress.py` | `fast` | `ci-quality.yml::fast-tests-cli` -m "fast and not windows_ci"<br>`ci-quality.yml::fast-tests-core-misc` -m "fast and not windows_ci" |
| `tests/specify_cli/cli/commands/agent/test_tasks_status_view.py` | `fast` | `ci-quality.yml::fast-tests-cli` -m "fast and not windows_ci"<br>`ci-quality.yml::fast-tests-core-misc` -m "fast and not windows_ci" |
| `tests/specify_cli/cli/commands/agent/test_tasks_transition_core.py` | `fast` | `ci-quality.yml::fast-tests-cli` -m "fast and not windows_ci"<br>`ci-quality.yml::fast-tests-core-misc` -m "fast and not windows_ci" |
| `tests/tasks/test_check_prerequisites_surface_agreement.py` | `git_repo`, `unit` | `ci-quality.yml::integration-tests-core-misc (shard: misc)` -m "not windows_ci and (git_repo or integration or architectural)" |
| `tests/tasks/test_finalize_ownership_routing.py` | `fast` | `ci-quality.yml::fast-tests-core-misc` -m "fast and not windows_ci" |
| `tests/tasks/test_finalize_sequential_overlap_allowed.py` | `fast` | `ci-quality.yml::fast-tests-core-misc` -m "fast and not windows_ci" |
| `tests/tasks/test_finalize_tasks_json_output_unit.py` | `fast` | `ci-quality.yml::fast-tests-core-misc` -m "fast and not windows_ci" |
| `tests/tasks/test_finalize_tasks_lanes_disjoint_fan_in.py` | `fast` | `ci-quality.yml::fast-tests-core-misc` -m "fast and not windows_ci" |
| `tests/tasks/test_finalize_tasks_owned_files_validation.py` | `fast` | `ci-quality.yml::fast-tests-core-misc` -m "fast and not windows_ci" |
| `tests/tasks/test_finalize_tasks_wps_yaml_unit.py` | `fast` | `ci-quality.yml::fast-tests-core-misc` -m "fast and not windows_ci" |
| `tests/tasks/test_frontmatter.py` | `fast` | `ci-quality.yml::fast-tests-core-misc` -m "fast and not windows_ci" |
| `tests/tasks/test_frontmatter_unit.py` | `fast` | `ci-quality.yml::fast-tests-core-misc` -m "fast and not windows_ci" |
| `tests/tasks/test_lane_directory_removal_unit.py` | `fast`, `unit` | `ci-quality.yml::fast-tests-core-misc` -m "fast and not windows_ci" |
| `tests/tasks/test_move_task_git_validation_unit.py` | `git_repo` | `ci-quality.yml::integration-tests-core-misc (shard: misc)` -m "not windows_ci and (git_repo or integration or architectural)" |
| `tests/tasks/test_planning_workflow_integration.py` | `git_repo`, `non_sandbox` | `ci-quality.yml::integration-tests-core-misc (shard: misc)` -m "not windows_ci and (git_repo or integration or architectural)" |
| `tests/tasks/test_pre_commit_wp_guard_unit.py` | `git_repo`, `non_sandbox` | `ci-quality.yml::integration-tests-core-misc (shard: misc)` -m "not windows_ci and (git_repo or integration or architectural)" |
| `tests/tasks/test_tasks_2x_unit.py` | `fast`, `unit` | `ci-quality.yml::fast-tests-core-misc` -m "fast and not windows_ci" |
| `tests/tasks/test_tasks_support.py` | `fast`, `non_sandbox` | `ci-quality.yml::fast-tests-core-misc` -m "fast and not windows_ci" |


## Summary

| Metric | Value |
|--------|-------|
| Files in FR-009 domain | **43** (15 `tests/tasks/` + 26 `agent/test_tasks*` + 2 `tests/architectural/`) |
| Tests in FR-009 domain | **754** |
| Tests selected by ZERO gates | **0** |
| Marker fixes required | **0** — every file already carried a selected marker |

**ZERO-UNSELECTED: every FR-009 test is selected by ≥1 CI gate.** This matches
the pre-plan squad ground truth (domain fully gate-visible on the mission base);
the mission-added files (byte suite, seam suites, both architectural gates) all
carry `fast` (in-process CliRunner / pure checks) — the architectural pair also
carries `architectural`, so each is selected by two gates (fast shard + the
core-misc `architectural` shard).

Orphan baseline cross-check: `tests/architectural/_gate_coverage_baseline.json`
holds 4 `orphan_files`; none matches the FR-009 glob. Permanence is enforced by
`tests/architectural/test_tasks_domain_gate_visibility.py` (WP10/T045).

## Reproduce

From the repo root (any checkout containing the mission's final file set):

```bash
PYTHONPATH=src python /path/to/fr009_census.py   # script below, verbatim
```

<details>
<summary>fr009_census.py (generation script, verbatim)</summary>

```python
"""FR-009 marker census generator (mission tasks-py-degod-wave2-01KWH9EQ, WP10/T044).

Reuses the canonical CI-selection model (tests.architectural._gate_coverage):
collects the whole suite once with the marker-dump plugin, then for every test
file matching the FR-009 glob reports its effective markers and the exact CI
gate(s) that select it. Exits 1 if any FR-009 test is selected by zero gates.

Run from the repo root:
    PYTHONPATH=src python <this-file>
"""

from __future__ import annotations

from collections import defaultdict
from fnmatch import fnmatch

from tests.architectural._gate_coverage import CompiledGate, collect_universe, load_gates

# FR-009 glob — verbatim (spec.md FR-009 + WP10/T044). Mission-added seam/byte
# files all live under the test_tasks* glob; the two architectural files are
# named explicitly.
FR009_GLOB: tuple[str, ...] = (
    "tests/tasks/**",
    "tests/specify_cli/cli/commands/agent/test_tasks*",
    "tests/architectural/test_tasks_command_surface.py",
    "tests/architectural/test_tasks_domain_gate_visibility.py",
)

# Markers that are not selection-relevant (bookkeeping / runtime behavior).
NOISE_MARKERS = frozenset(
    {"parametrize", "usefixtures", "filterwarnings", "skip", "skipif", "xfail", "timeout"}
)


def gate_display(cg: CompiledGate) -> str:
    g = cg.gate
    shard = f" (shard: {g.shard})" if g.shard else ""
    expr = f' -m "{g.marker_expr}"' if g.marker_expr else " (no -m)"
    return f"`{g.workflow}::{g.job}{shard}`{expr}"


def main() -> int:
    universe = collect_universe()
    compiled = [CompiledGate(g) for g in load_gates()]

    per_file: dict[str, dict[str, set[str]]] = defaultdict(
        lambda: {"markers": set(), "gates": set(), "unselected": set()}
    )
    for test in universe:
        rel, nodeid = test["relpath"], test["nodeid"]
        if not any(fnmatch(rel, pat) for pat in FR009_GLOB):
            continue
        markers = set(test["markers"])
        rec = per_file[rel]
        rec["markers"] |= markers - NOISE_MARKERS
        hits = {gate_display(cg) for cg in compiled if cg.selects(rel, nodeid, markers)}
        if hits:
            rec["gates"] |= hits
        else:
            rec["unselected"].add(nodeid)

    print("| file | markers | selecting gate(s) |")
    print("|------|---------|-------------------|")
    unselected_total: list[str] = []
    for rel in sorted(per_file):
        rec = per_file[rel]
        marks = ", ".join(f"`{m}`" for m in sorted(rec["markers"])) or "(none)"
        gates = "<br>".join(sorted(rec["gates"])) or "**NONE — ORPHAN**"
        print(f"| `{rel}` | {marks} | {gates} |")
        unselected_total.extend(sorted(rec["unselected"]))

    print()
    print(f"Files in FR-009 domain : {len(per_file)}")
    n_tests = sum(1 for t in universe if any(fnmatch(t["relpath"], p) for p in FR009_GLOB))
    print(f"Tests in FR-009 domain : {n_tests}")
    print(f"Tests selected by ZERO gates : {len(unselected_total)}")
    if unselected_total:
        for nid in unselected_total:
            print(f"  ORPHAN: {nid}")
        return 1
    print("ZERO-UNSELECTED: every FR-009 test is selected by >=1 CI gate.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

</details>
