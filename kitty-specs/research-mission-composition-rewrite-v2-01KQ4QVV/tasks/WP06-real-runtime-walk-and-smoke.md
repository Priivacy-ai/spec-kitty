---
work_package_id: WP06
title: Real-Runtime Walk + Dogfood Smoke (P0 FINAL GATE; BLOCKS MERGE)
dependencies:
- WP05
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-013
- FR-014
planning_base_branch: main
merge_target_branch: main
branch_strategy: Current branch main; planning base main; merge target main; lane-based execution worktree per finalize-tasks. Depends on WP05. THIS IS THE FINAL MERGE GATE — without dogfood evidence in this WP's commit, the mission cannot merge.
subtasks:
- T025
- T026
- T027
- T028
history:
- timestamp: '2026-04-26T11:46:43Z'
  actor: claude
  note: Created during /spec-kitty.tasks for mission research-mission-composition-rewrite-v2-01KQ4QVV
authoritative_surface: tests/integration/
execution_mode: code_change
mission_id: 01KQ4QVVZ4DC6CXA1XCZZAQ8AG
mission_slug: research-mission-composition-rewrite-v2-01KQ4QVV
owned_files:
- tests/integration/test_research_runtime_walk.py
- kitty-specs/research-mission-composition-rewrite-v2-01KQ4QVV/quickstart.md
- kitty-specs/research-mission-composition-rewrite-v2-01KQ4QVV/smoke-evidence.md
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load implementer-ivan
```

# WP06 — Real-Runtime Walk + Dogfood Smoke (P0 FINAL GATE; BLOCKS MERGE)

## Objective

Author the real-runtime integration walk that drives `get_or_start_run('demo-research-walk', tmp_repo, 'research')` end-to-end. Advance at least one composed step. Assert paired lifecycle records, action_hint correctness, structured guard failure on missing artifacts. Add `quickstart.md` with the operator dogfood sequence. **Capture dogfood evidence from a real shell run; without `smoke-evidence.md` containing actual command output, mission-review verdict is UNVERIFIED and the mission cannot merge.**

## Branch Strategy

- Planning base: `main`
- Merge target: `main`
- Execution worktree: lane-based, allocated by `spec-kitty implement WP06`. Depends on WP05.

## Implementation Command

```bash
spec-kitty agent action implement WP06 --agent <name>
```

## C-007 Enforcement (CRITICAL — final gate)

The new test file `test_research_runtime_walk.py` MUST include this header docstring AS THE FIRST CONTENT:

```python
"""Real-runtime integration walk for the research mission.

C-007 enforcement (spec constraint, FINAL GATE):
    The following symbols MUST NOT appear in any unittest.mock.patch target
    in this file. Reviewer greps; any hit blocks approval and blocks the
    mission from merging.

        - _dispatch_via_composition
        - StepContractExecutor.execute
        - ProfileInvocationExecutor.invoke
        - _load_frozen_template (and any frozen-template loader)
        - load_validated_graph
        - resolve_context

This is the test that proves the v1 P0 finding is closed:
    `get_or_start_run('demo-research-walk', tmp_repo, 'research')`
    succeeds end-to-end without raising MissionRuntimeError, the runtime
    advances at least one composed step via the real composition path, and
    structured guard failures fire on missing artifacts.
"""
```

The reviewer greps the file for those exact identifiers in any patch target. Zero hits required.

## Authoritative References

- `kitty-specs/research-mission-composition-rewrite-v2-01KQ4QVV/spec.md` — Acceptance Scenarios 1–6, NFR-005 (mission-review smoke gate), C-007 (no-mock list)
- `tests/integration/test_custom_mission_runtime_walk.py` — pattern reference (drives a custom mission walk; this WP mirrors it for research with the C-007 list more strictly enforced)
- `src/specify_cli/next/runtime_bridge.py` — `get_or_start_run` is the entry point

## Subtask T025 — Author `test_research_runtime_walk.py` with C-007 enforcement

**Steps**:
1. Create `tests/integration/test_research_runtime_walk.py`.
2. **First content of the file MUST be the C-007 header docstring** (see C-007 Enforcement section above).
3. Tests:

   - **`test_get_or_start_run_succeeds_for_research`** — From a clean tmp repo, call `get_or_start_run('demo-research-walk', tmp_repo, 'research')`. Asserts: no `MissionRuntimeError`, returns a run handle. **THIS TEST CLOSES THE V1 P0 FINDING.** Use `tmp_path` fixture; do NOT mock anything in the C-007 list.
   - **`test_research_advances_one_composed_step`** — Set up a realistic feature_dir with the artifacts `scoping`'s guard requires (just `spec.md`). Call into the runtime to advance one step. Assert: at least one call into `_dispatch_via_composition` happened (use a non-forbidden hook to observe — e.g. inspect status events written by the run, NOT patch the function). Assert: status events log shows a research-native action ID, not a profile default verb.
   - **`test_paired_invocation_lifecycle_recorded`** — After the advance in the previous test, read invocation records from `~/.kittify/invocations/<id>/` (or wherever they land — point an env var at `tmp_path/invocations/`). Assert: every started record has a paired done/failed record, and recorded action equals the research-native step ID.
   - **`test_missing_artifact_blocks_advancement_with_structured_error`** — From a clean tmp repo (no artifacts), attempt advance for `scoping`. Assert: structured error mentions `spec.md`; run state does not advance; legacy DAG dispatcher (`runtime_next_step`) is NOT invoked. Use `caplog` or status-events log inspection to observe — NOT patch on the C-007 list.
   - **`test_unknown_research_action_fails_closed`** — Force a synthetic state where `mission="research"` and `action="bogus"` enters `_check_composed_action_guard`. Assert: returns the fail-closed message `"No guard registered for research action: bogus"`. (Same as WP05's bridge test, but at integration layer to confirm WP05's fail-closed actually fires through the dispatch path.)

4. Use `tmp_path` and `tmp_path_factory` for fixtures. Use environment variables to redirect any user-global paths (`~/.kittify/invocations/`) into `tmp_path`.
5. Run: `uv run pytest tests/integration/test_research_runtime_walk.py -v`. All 5 tests pass.

**Files**: `tests/integration/test_research_runtime_walk.py` (new).

## Subtask T026 — Author `quickstart.md` with operator dogfood sequence

**Steps**:
1. Create `kitty-specs/research-mission-composition-rewrite-v2-01KQ4QVV/quickstart.md`.
2. Document the operator-runnable sequence:
   ```bash
   # In a clean checkout of spec-kitty at HEAD:
   cd /tmp && rm -rf demo-research-smoke && mkdir demo-research-smoke && cd demo-research-smoke
   git init && git commit --allow-empty -m "init"
   uv --directory /Users/robert/.../spec-kitty run spec-kitty agent mission create demo-smoke --mission-type research --json
   uv --directory /Users/robert/.../spec-kitty run spec-kitty next --agent claude:opus-4.7:test:operator --mission demo-smoke
   # Observe trail records under ~/.kittify/invocations/
   ```
3. Document expected outcomes for each step (no MissionRuntimeError; mission created; spec-kitty next returns a step decision; trail record paired).
4. Cap at ~80 lines.

**Files**: `kitty-specs/research-mission-composition-rewrite-v2-01KQ4QVV/quickstart.md` (new).

## Subtask T027 — Run full regression sweep + mypy/ruff

**Steps**:
1. `uv run pytest tests/specify_cli/mission_step_contracts/`. All pass.
2. `uv run pytest tests/specify_cli/next/test_runtime_bridge_composition.py`. Software-dev bridge regression green.
3. `uv run pytest tests/integration/test_custom_mission_runtime_walk.py`. Custom mission walk green.
4. `uv run pytest tests/integration/test_mission_run_command.py`. Mission run command green.
5. `git diff --name-only main..HEAD -- 'src/specify_cli/**' 'tests/**'` — capture full mission diff list.
6. `uv run mypy --strict <list>` — zero new errors. Document baseline pre-existing errors so reviewer can distinguish.
7. `uv run ruff check <list>` — zero new findings.
8. **`grep -E "patch.*_dispatch_via_composition|patch.*StepContractExecutor\\.execute|patch.*ProfileInvocationExecutor\\.invoke|patch.*_load_frozen_template|patch.*load_validated_graph|patch.*resolve_context" tests/integration/test_research_runtime_walk.py tests/specify_cli/next/test_runtime_bridge_research_composition.py`** — MUST return zero hits. Reviewer also runs this grep.

## Subtask T028 — Capture dogfood evidence in `smoke-evidence.md`

**Steps**:
1. From a fresh shell, run the quickstart sequence verbatim.
2. Capture EACH command + its full output (no redactions beyond ULIDs/timestamps if you want).
3. Paste into `kitty-specs/research-mission-composition-rewrite-v2-01KQ4QVV/smoke-evidence.md` with this structure:

   ```markdown
   # Dogfood Smoke Evidence — research-mission-composition-rewrite-v2

   **Captured**: <ISO timestamp>
   **Operator**: <agent identity>
   **Spec-kitty HEAD**: <commit at run time>

   ## Step 1: Clean checkout setup
   ```
   <commands and output>
   ```

   ## Step 2: Create research mission
   ```
   <command and full JSON output, with mission_id visible>
   ```

   ## Step 3: spec-kitty next
   ```
   <command and full output, showing next-step decision returned without MissionRuntimeError>
   ```

   ## Step 4: Trail records
   ```
   <ls of ~/.kittify/invocations/<id>/ and cat of one started + one done record>
   ```

   ## Verdict

   PASS — fresh research mission created and advanced via composition. v1 P0 finding closed.
   ```

4. Also paste this into the WP06 commit message under `Dogfood evidence:`.
5. **Without this file, mission-review verdict is UNVERIFIED.**

**Files**: `kitty-specs/research-mission-composition-rewrite-v2-01KQ4QVV/smoke-evidence.md` (new).

## Definition of Done

- [ ] `tests/integration/test_research_runtime_walk.py` exists with C-007 header docstring + 5 tests; all pass.
- [ ] `kitty-specs/research-mission-composition-rewrite-v2-01KQ4QVV/quickstart.md` exists with the operator dogfood sequence.
- [ ] `kitty-specs/research-mission-composition-rewrite-v2-01KQ4QVV/smoke-evidence.md` exists with verbatim command output from a real run.
- [ ] Full regression sweep (4 suites) passes.
- [ ] mypy --strict + ruff zero new findings on the full diff.
- [ ] **Reviewer grep against C-007 forbidden list returns zero hits across BOTH `test_research_runtime_walk.py` AND `test_runtime_bridge_research_composition.py`.**
- [ ] Dogfood evidence pasted in commit message.

## Test Strategy

WP06 is the gate. The test file proves runnability + DRG resolution + guard parity end-to-end via the real runtime engine. The smoke-evidence file proves the same behaviors are observable to a human operator outside the test harness. Mission-review consumes both as the C-008 hard gate.

## Risks

| Risk | Mitigation |
|---|---|
| Real-runtime walk introduces flakiness from filesystem ordering. | Use `tmp_path` strictly; isolate `~/.kittify/invocations/` via env var. |
| `~/.kittify/invocations/` path differs from what tests expect. | Read the real path from the runtime engine's writer; do not hardcode. |
| Quickstart commands hang or differ between operator runs. | T028 captures verbatim from one canonical run. If subsequent runs diverge, document the divergence in `smoke-evidence.md`. |
| C-007 forbidden grep produces a false positive (e.g. a string in a docstring). | Reviewer judgment; the rule applies to `unittest.mock.patch` targets, not arbitrary string occurrences. The C-007 header docstring intentionally contains the names — that is acceptable. |

## Reviewer Guidance

This is the gate. Reviewer MUST:

1. Run the C-007 grep yourself against both test files. Zero hits required.
2. Read `smoke-evidence.md` and confirm it contains real command output, not test-only output.
3. Run the quickstart sequence yourself from a clean shell. Confirm the same outcome.
4. Run all 5 integration tests in `test_research_runtime_walk.py` — they pass.
5. Run the full regression sweep — all 4 suites pass.
6. Confirm the v1 P0 finding (`MissionRuntimeError: Mission 'research' not found`) is reproducibly closed: `git checkout origin/main && uv run python -c "from specify_cli.next.runtime_bridge import get_or_start_run; ..."` should still raise; `git checkout HEAD && <same script>` should succeed.

If any of these fail, REJECT WP06. The mission does not merge without this gate clean.
