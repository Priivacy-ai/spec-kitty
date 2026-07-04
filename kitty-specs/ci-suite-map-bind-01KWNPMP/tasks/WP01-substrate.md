---
work_package_id: WP01
title: 'Substrate: workflow-scope preflight + gate-coverage parse-model extension'
dependencies: []
requirement_refs:
- FR-003
- FR-008
tracker_refs: []
planning_base_branch: tidy/ci-suite-map-2034
merge_target_branch: tidy/ci-suite-map-2034
branch_strategy: Planning artifacts for this mission were generated on tidy/ci-suite-map-2034. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into tidy/ci-suite-map-2034 unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-ci-suite-map-bind-01KWNPMP
base_commit: f58bcec37663fae6a642815b229307ba2cab1791
created_at: '2026-07-04T08:52:53.610639+00:00'
subtasks:
- T001
- T002
- T003
phase: Phase 1 - Substrate
assignee: ''
agent: "claude-orchestrator"
shell_pid: '3796249'
history:
- at: '2026-07-04T05:27:33Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/architectural/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- tests/architectural/_gate_coverage.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP01 – Substrate: preflight + parse-model extension

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`

---

## ⚠️ IMPORTANT: Review Feedback

Check the `review_ref` field in the event log before starting; address all feedback.

---

## Objectives & Success Criteria

Two enablers everything else stacks on:
1. **C-004 preflight**: prove `.github/workflows/` edits can be pushed from this checkout (the `workflow` OAuth scope gate #2296 warns about). If the push fails, STOP the mission and report — nothing downstream is implementable.
2. **IC-02**: extend `tests/architectural/_gate_coverage.py` ADDITIVELY with every parsed relation the WP03/WP04 consumers need. This file is a single-owner spine: after this WP it is READ-ONLY for the rest of the mission (Wave-2 spine lesson).

## Subtasks & Detailed Guidance

### Subtask T001 – Workflow-scope preflight probe
- From the repo root: create a throwaway branch, append a trailing newline to `.github/workflows/ci-quality.yml`, commit, `unset GITHUB_TOKEN && git push origin probe/workflow-scope`. Paste the push output (success or the OAuth error) into the Activity Log. On success: delete the probe branch (remote + local) and revert nothing (the probe never merges). On failure: STOP, move this WP to blocked with the error verbatim.

### Subtask T002 – Parse-model extensions (additive only)
Read `_gate_coverage.py` end-to-end first. Extend the module (new functions/dataclass fields; do NOT change existing behavior — every existing consumer test must pass untouched) to expose:
- **Positive-marker tokens per gate**: a negation-aware walk of each gate's `-m` expression via `_pytest.mark.expression.Expression` returning the positively-referenced marker names (`not windows_ci` = negative; `windows_ci` in ci-windows = positive). This is FR-001's state-(i) primitive. Expected live result: exactly `{fast, integration, git_repo, architectural, slow, timing, quarantine, windows_ci}` (8) — re-derive, record.
- **`needs:` lists per job** and **`needs.<job>.result` references** inside run scripts (FR-003a).
- **Dorny filter groups**: group name → glob list, plus which job `if:` expressions consume which group outputs (the job→group gating map — FR-011's mapping invariant reads this).
- **Diff-cover critical-path entries** and **`--cov=` emitters per job** (FR-005).
- **The pytest-invoking workflow set** discovered from `.github/workflows/*.yml` by content probe (FR-008) — compared against the module's `WORKFLOW_FILES` allowlist.
- **Quality-gate result-loop membership** (which jobs the aggregator reads) (FR-003d).
- **`on: pull_request` trigger types + outer `paths:` lists** (FR-013 / FR-012 two-layer reads).
- Registered-marker list parsed from `pytest.ini`'s `markers =` block (reuse `test_marker_registry_single_source.py`'s approach if importable; else a small parser).

Keep it pure parsing — NO assertions in this module (the invariants live in WP04's test files). Docstring each new surface with the FR it serves.

### Subtask T003 – Gates
- `PWHEADLESS=1 pytest tests/architectural/test_gate_coverage.py tests/architectural/test_ci_quality_path_filters.py tests/architectural/test_marker_registry_single_source.py -q` — all existing consumers green, untouched.
- A quick self-check script exercising each new parse surface against the LIVE workflows; paste the outputs (the 8-token set, the needs map size, the group count = re-derived gate/group numbers) into the Activity Log — these are WP03/WP04's ground truth.
- Diff-scoped `ruff check` exit 0; `python -m mypy src/ 2>&1 | tail -2` stays Success (this file is under tests/, but if mypy covers it, clean).

## Campsite cleaning (standing rule [[feedback-sonar-attack-vector-campsite]]; ride the WP's normal review)

Sonar: zero open issues in the target files (verified). Local ruff --select ALL census (randy, 2026-07-04) — clean while you're there; auto-fixables in one `ruff check --fix` pass where possible:

- `_gate_coverage.py:40` isort (I001) · `:48` Sequence → TYPE_CHECKING (TC003) · `:53` `from pytest import ExitCode` → `import pytest` (PT013) · `:234` `import yaml` → top-level (PLC0415) · `:240` `includes or [None]` (FURB110) · `:341` hoist `_DUPLICATE_GATE_THRESHOLD = 2` (PLR2004) · `:372` explicit `check=False` on subprocess.run (PLW1510) · trailing commas `:89,:256,:403,:438` (COM812)
- `test_gate_coverage.py`: **highest-leverage** — make the five parse helpers PUBLIC in `_gate_coverage.py` (`_parse_pytest_invocation`, `_path_matches`, `_substitute_matrix`, `_join_continuations`, `_strip_to_command` — the module itself is private, so the underscore adds nothing) clearing 9 SLF001 sites at `:195-341`; docstrings `:64,:368` (D103) + D205 blanks `:129,:155,:192,:239`; `:351/:353` add `# noqa: PLC0415  # intentional: exercises import surface`; `:359` `name == "a"` (FURB171); trailing commas ×8 (COM812)
- Adjudicated OUT (leave): `:145` PERF401 (readability), `:394` TRY003 (load-bearing message), `:445-473` T201 (intentional CLI prints), test `:272` PLR2004 (synthetic-universe size).

## Definition of Done
- Preflight evidence recorded (push success verbatim, probe branch cleaned).
- Every listed parse surface exists, additively, with the live self-check outputs recorded. These recorded counts are WP03/WP04's ground truth: any downstream discrepancy is WP01 feedback (re-open), not a downstream workaround — the cross-check is explicit, not implicit.
- Existing gate-coverage/path-filter/marker-registry tests green with zero edits to them.

## Risks / Reviewer Guidance
- The private `_pytest.mark.expression` API: pin its import with a loud failure message (existing precedent in the module) — reviewer should verify the loud-fail is TESTED behavior via the WP04 fixtures, but for this WP a try/except-raise with a clear message suffices.
- Reject any change to existing parse behavior (this is additive-only by contract).

## Activity Log

> Append at the END, chronological. Format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`

- 2026-07-04T05:27:33Z – system – Prompt created.
- 2026-07-04T09:05:00Z – wp01-implementer – Loaded python-pedro profile (directives 010/024/025/030/034/041/043/044/045; tactic test-scaffolding-as-design-smell). Read WP prompt, spec.md (Adjudicated Decisions), plan.md, `_gate_coverage.py` end-to-end, the three consumer test files, and the live workflow structures.
- 2026-07-04T09:15:00Z – wp01-implementer – T001 C-004 preflight PROBE PUSH SUCCEEDED. `origin` = `git@github.com:stijn-dejongh/spec-kitty.git` (SSH). Sequence: `git checkout -b probe/workflow-scope`; appended trailing newline to `.github/workflows/ci-quality.yml`; committed (`f431825b6`); `unset GITHUB_TOKEN && git push origin probe/workflow-scope`. Verbatim push output:
  ```
  remote:
  remote: Create a pull request for 'probe/workflow-scope' on GitHub by visiting:
  remote:      https://github.com/stijn-dejongh/spec-kitty/pull/new/probe/workflow-scope
  remote:
  To github.com:stijn-dejongh/spec-kitty.git
   * [new branch]          probe/workflow-scope -> probe/workflow-scope
  ```
  Cleanup: `git push origin --delete probe/workflow-scope` → `- [deleted] probe/workflow-scope`; local probe branch deleted; back on lane branch. The `.github/workflows/` push path is OPEN — mission unblocked.
- 2026-07-04T09:35:00Z – wp01-implementer – ATDD RED commit `aac970ac7`: `tests/architectural/test_gate_coverage_parse_model.py` (13 tests pinning every new parse surface; `architectural`-marked → CI-selected per NFR-005). Red run on planning base: `uv run pytest tests/architectural/test_gate_coverage_parse_model.py -q` → **13 failed** (`AttributeError: module 'tests.architectural._gate_coverage' has no attribute 'positive_marker_tokens' / 'load_workflow_model' / 'discover_pytest_workflows' / 'registered_markers' / 'routed_marker_names'`). One initially-vacuous raises-test tightened (pytest.raises(Exception) would have swallowed the AttributeError) before committing the red state.
- 2026-07-04T10:00:00Z – wp01-implementer – T002 implementation commit `c11f3177f` (additive; zero edits to existing functions except hoisting `import yaml` to top-level): `positive_marker_tokens` (Expression.compile validation + stdlib-ast sign walk, loud RuntimeError on unsupported nodes), `routed_marker_names`, `WorkflowModel` + `load_workflow_model` (job_needs, needs_result_reads incl. quality-gate result-loop membership, job_gating_groups from job-level `if:`, dorny filter_groups, cov_targets, diff_cover_critical_paths, pull_request_types/paths, push_paths), `discover_pytest_workflows` (parse_workflow's own semantics), `registered_markers` (pytest.ini line-based, C-006 read-only). Red→green: 13/13 pass. NOTE for WP04: pytest 9.0.3's `Expression.compile` raises plain `SyntaxError` (ParseError type is gone).
- 2026-07-04T10:05:00Z – wp01-implementer – T003 gate (consumers untouched, BEFORE campsite): `PWHEADLESS=1 uv run pytest tests/architectural/test_gate_coverage.py tests/architectural/test_ci_quality_path_filters.py tests/architectural/test_marker_registry_single_source.py -q` → **32 passed, 1 warning in 132.20s** with `git diff --stat` showing only `_gate_coverage.py` + the new test file. `ruff check` clean; `mypy` on the touched files → Success (one real finding it raised — `dict.get(True)` typing on the YAML `on:` key — fixed via honest `dict[Any, Any]` signature). NOTE: `uv run mypy src/` in this lane venv shows 6 pre-existing `types-toml` stub errors (venv provisioning skew, zero src/ files touched by this WP); the primary checkout's `uv run mypy src/` → `Success: no issues found in 1053 source files`.
- 2026-07-04T10:20:00Z – wp01-implementer – LIVE SELF-CHECK (NFR-004 re-derivations — WP03/WP04 GROUND TRUTH):
  - gates parsed: **56**
  - routed-by-marker set (**8**, exactly as spec expected): `['architectural', 'fast', 'git_repo', 'integration', 'quarantine', 'slow', 'timing', 'windows_ci']`
  - ci-quality.yml: **49 jobs** (needs-map size); **20 filter groups** `[agent, charter, cli, core_misc, dashboard, doctrine, e2e, execution_context, kernel, lanes, merge, missions, next, orchestrator_api, post_merge, release, review, status, sync, upgrade]`; **38 jobs gated by group outputs**; **37 cov-emitting jobs / 23 distinct --cov targets**; **11 diff-cover critical paths** (incl. `src/mission_runtime/*`); `pull_request` types **()** (FR-013 will add them); 16 outer pull_request paths / 16 push paths
  - quality-gate: needs-list **42** == result-loop reads **42**, sets IDENTICAL (incl. `integration-tests-charter` declared AND read) → FR-004's charter phantom-read candidate is **verified-already-fixed** at this parse level; `mission-loader-coverage` absent from both (the known FR-004 reachability gap, confirmed live)
  - ci-windows.yml: 2 jobs, 1 filter group `windows_critical`, pull_request paths ()
  - drift-detector.yml: 1 job; release.yml: 4 jobs; no filters/cov/critical-paths in either
  - `discover_pytest_workflows()` == `frozenset(WORKFLOW_FILES)` → **True** (exactly the 4)
  - registered markers: **37**, duplicate-free; unrouted-by-marker registered markers: **29** (incl. `unit`, `contract` — the #2034 gap, live)
- 2026-07-04T10:45:00Z – wp01-implementer – Campsite commit `f5b934849` per the WP list: _gate_coverage.py I001/TC003/PT013/PLC0415/FURB110(tuple-form for mypy)/PLR2004/PLW1510/COM812; five helpers made public (`parse_pytest_invocation`, `path_matches`, `substitute_matrix`, `join_continuations`, `strip_to_command`) clearing 9 SLF001 sites; test_gate_coverage.py D103×2, D205×4, narrow `# noqa: PLC0415` with rationale ×2, FURB171, COM812. Adjudicated-OUT left: PERF401, TRY003, T201, test-PLR2004. Post-campsite verification: 45/45 tests green across the four files (incl. full orphan ratchet re-run: 18 passed in 69s), `ruff check tests/architectural/` clean, `mypy` on the three files → Success.
- 2026-07-04T09:27:45Z – claude-orchestrator – shell_pid=3796249 – Moved to for_review
- 2026-07-04T09:41:25Z – claude-orchestrator – shell_pid=3796249 – reviewer-renata REJECT (1 MAJOR, scoped): campsite rename sed mangled 4 test function names in test_gate_coverage.py:309,319,330,339 (test_ prefix lost underscore: testpath_matches_/testsubstitute_matrix_/testjoin_continuations_/teststrip_to_command_) — restore test_ prefix, re-run file (expect 18 passed). Everything else PASSED with live evidence; re-review scoped to this fix.
- 2026-07-04T09:44:01Z – claude-orchestrator – shell_pid=3796249 – review fix c399bbfdd: 4 test names restored, 18 passed, ruff clean
- 2026-07-04T09:46:38Z – claude-orchestrator – shell_pid=3796249 – Moved to in_review
- 2026-07-04T09:46:40Z – claude-orchestrator – shell_pid=3796249 – reviewer-renata APPROVE at c399bbfdd (scoped re-review after 1-MAJOR rejection cycle): fix commit exactly the 4 test_ prefix restorations, 18 passed + ruff clean live, 3 reviewed commits untouched. Prior full review stands: red->green 13/13, surfaces additive, NFR-004 floors exact (8 routed/42==42/20 groups/37 markers), arch sweep 653 passed, kitty-specs net-zero on lane.
- 2026-07-04T11:30:00Z – wp01-implementer – Review fix (REJECT->fixed): restored test_ prefix on 4 test names mangled by the campsite helper-rename sed (test_gate_coverage.py:309/319/330/339 — testpath_matches_/testsubstitute_matrix_/testjoin_continuations_/teststrip_to_command_ -> test_*). Name hygiene only (pytest's test* pattern had kept collecting them: 18 collected before and after). Commit c399bbfdd; evidence: ruff clean, 18 passed in 70.61s. (Ported from lane by orchestrator.)
