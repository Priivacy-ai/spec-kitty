# Tasks: Charter E2E #827 Follow-ups (Tranche A)

**Mission**: charter-e2e-827-followups-01KQAJA0
**Mission ID**: 01KQAJA02YZ2Q7SH5WND713HKA
**Spec**: [spec.md](spec.md) · **Plan**: [plan.md](plan.md) · **Research**: [research.md](research.md) · **Data model**: [data-model.md](data-model.md) · **Contracts**: [contracts/](contracts/) · **Quickstart**: [quickstart.md](quickstart.md)

**Branch contract**: current `main` → planning/base `main` → merge target `main` (`branch_matches_target=true`).

## Strategy

Four independent WPs, one per #827 follow-up. Each WP is laser-focused on a single subsystem fix with no upstream code dependencies. **Operator preference**: WP01 (#848) should be the **first to land in the PR** because it protects every other gate from false failures. Code-wise, all four WPs can be developed in parallel lanes.

Per Constraint C-004 in the spec: **WP01 stays scoped as environment/review-gate hygiene**. No WP in this mission redesigns dependency management, replaces `uv.lock`, or restructures `pyproject.toml` shape.

## Subtask Index

| ID | Description | WP | Parallel |
|---|---|---|---|
| T001 | Author `tests/architectural/test_uv_lock_pin_drift.py` (parse `uv.lock`, diff against installed versions, name offenders + sync command) | WP01 |  | [D] |
| T002 | Author/extend `docs/development/review-gates.md` documenting `uv sync --frozen` as the pre-review/pre-PR sync command | WP01 | [D] |
| T003 | Audit `kitty-specs/**/issue-matrix.md` rows labeled "verified-already-fixed" for #848-related hygiene; correct any that misrepresent current risk | WP01 | [D] |
| T004 | Validate the new drift test green-path on a clean install AND red-path with synthetic mismatch | WP01 |  | [D] |
| T005 | Tighten `RuntimeDecision` validation in `src/specify_cli/next/decision.py` — `kind=step` requires non-null + on-disk `prompt_file` at envelope construction; replace the legitimizing inline comment | WP02 |  |
| T006 | Audit every step-construction site in `src/specify_cli/next/runtime_bridge.py` and route any "no prompt available" case to `kind=blocked` with reason instead of emitting `kind=step` with null prompt | WP02 |  |
| T007 | Tighten the assertion in `tests/e2e/test_charter_epic_golden_path.py` — for every issued `kind=step`, assert `prompt_file`/`prompt_path` is non-null, non-empty, and `Path(value).is_file()` is true | WP02 | [P] |
| T008 | Scrub `src/doctrine/skills/spec-kitty-runtime-next/SKILL.md` and any peer doctrine surface — remove text legitimizing null prompts for `kind=step` | WP02 | [P] |
| T009 | Add unit tests under `tests/specify_cli/next/` covering positive + negative cases for the new `RuntimeDecision` validation | WP02 | [P] |
| T010 | Add `*/.kittify/dossiers/*/snapshot-latest.json` glob to root `.gitignore` | WP03 | [D] |
| T011 | Add explicit path filter helper (`_is_dossier_snapshot(path)` or equivalent) in the dirty-state preflight code path in `src/specify_cli/cli/commands/agent/tasks.py` (and any peer in `src/specify_cli/status/`) | WP03 |  | [D] |
| T012 | Author `tests/integration/test_dossier_snapshot_no_self_block.py` — green path (snapshot write → move-task succeeds) AND control case (unrelated dirty file still blocks, naming that file not the snapshot) | WP03 |  | [D] |
| T013 | Verify `tests/integration -k 'dossier or move_task or dirty or transition'` runs clean | WP03 |  | [D] |
| T014 | Implement `_substantive` helpers (`is_substantive` + `is_committed`) in new module `src/specify_cli/missions/_substantive.py` — section-presence only (no byte-length OR) | WP04 |  |
| T015 | `mission create` boundary fix: stop including `spec.md` in the create-time `safe_commit` call. Empty scaffolds remain untracked at create time | WP04 |  |
| T016 | `setup-plan` gates: entry check (spec must be committed AND substantive) + exit check (plan must be substantive). Both emit `phase_complete=False / blocked_reason` and skip the relevant commit on failure | WP04 |  |
| T017 | Update mission templates `src/specify_cli/missions/<mission-type>/command-templates/{specify,plan}.md` AND author `tests/integration/test_specify_plan_commit_boundary.py` covering the five contract scenarios | WP04 | [P] |
| T018 | Verify `tests/integration -k 'specify or plan or auto_commit or mission'` and `tests/specify_cli/cli/commands/agent` run clean | WP04 |  |

`[P]` in this index marks parallel-safe items per file/concern. The per-WP checkbox lists below are the tracking surface for `agent tasks mark-status`.

## Work Packages

### WP01 — #848 review-gate pin-drift detector

**Goal**: Add a deterministic, fast architectural test that detects `uv.lock` vs installed shared-package drift and fails with an actionable error message naming the offenders and the sync command. Document the sync command in one place. Correct any stale issue-matrix language that mislabels the underlying risk as already-fixed.

**Priority**: Highest (operator: lands first in PR order to protect every other gate).
**Independent test**: `uv run pytest tests/architectural/test_uv_lock_pin_drift.py -q` passes on a clean install and fails with synthetic mismatch.
**Estimated prompt size**: ~280 lines.
**Dependencies**: none.
**Lane**: A (independent of WP02/03/04).

**Subtasks**:

- [x] T001 Author `tests/architectural/test_uv_lock_pin_drift.py` (parse `uv.lock`, diff against installed versions, name offenders + sync command) (WP01)
- [x] T002 [P] Author/extend `docs/development/review-gates.md` documenting `uv sync --frozen` as the pre-review/pre-PR sync command (WP01)
- [x] T003 [P] Audit `kitty-specs/**/issue-matrix.md` rows labeled "verified-already-fixed" for #848-related hygiene; correct any that misrepresent current risk (WP01)
- [x] T004 Validate the new drift test green-path on a clean install AND red-path with synthetic mismatch (WP01)

**Implementation sketch**:

1. Read `uv.lock` (TOML); extract resolved version of `spec-kitty-events` and `spec-kitty-tracker` (the governed list — centralized as a module constant in the test).
2. For each governed package, compare `importlib.metadata.version(...)` against the lock's resolved version.
3. On disagreement, fail the test with a multi-line message: list each offending package as `(lock_version, installed_version)` plus the literal command `uv sync --frozen`.
4. Document the sync command in `docs/development/review-gates.md` (create if absent; cross-reference from the test's failure message wording).
5. Audit issue-matrix rows; correct any that say #848 is "verified-already-fixed" if the underlying risk still exists.

**Risks**:
- `importlib.metadata` may not be aware of dev-only path overrides — guard with a clear note that path-overridden envs are dev-only and the test is allowed to fail in that mode (or skipped via env var if needed).
- Test must complete in <5s per NFR-001 — single TOML parse + a few `version()` calls easily fit.

**Scope guardrail**: this WP MUST NOT modify `pyproject.toml` `[project.dependencies]`, `[tool.uv.sources]`, or `uv.lock` itself. It MUST NOT introduce new dependency-management abstractions.

**Prompt file**: [tasks/WP01-uv-lock-pin-drift-detector.md](tasks/WP01-uv-lock-pin-drift-detector.md)

---

### WP02 — #844 charter E2E mandates a real prompt file

**Goal**: Tighten the `kind=step` envelope contract so a `prompt_file` (or its alias `prompt_path`) is mandatory, non-null, non-empty, and resolves on disk. Update the E2E test to assert the strict contract. Scrub doctrine that legitimizes null prompts.

**Priority**: High (charter golden-path correctness).
**Independent test**: `PWHEADLESS=1 uv run pytest tests/e2e/test_charter_epic_golden_path.py -q` passes; new unit tests under `tests/specify_cli/next/` pass.
**Estimated prompt size**: ~430 lines.
**Dependencies**: none.
**Lane**: B (independent of WP01/03/04).

**Subtasks**:

- [ ] T005 Tighten `RuntimeDecision` validation in `src/specify_cli/next/decision.py` — `kind=step` requires non-null + on-disk `prompt_file` at envelope construction; replace the legitimizing inline comment (WP02)
- [ ] T006 Audit every step-construction site in `src/specify_cli/next/runtime_bridge.py` and route any "no prompt available" case to `kind=blocked` with reason instead of emitting `kind=step` with null prompt (WP02)
- [ ] T007 [P] Tighten the assertion in `tests/e2e/test_charter_epic_golden_path.py` — for every issued `kind=step`, assert `prompt_file`/`prompt_path` is non-null, non-empty, and `Path(value).is_file()` is true (WP02)
- [ ] T008 [P] Scrub `src/doctrine/skills/spec-kitty-runtime-next/SKILL.md` and any peer doctrine surface — remove text legitimizing null prompts for `kind=step` (WP02)
- [ ] T009 [P] Add unit tests under `tests/specify_cli/next/` covering positive + negative cases for the new `RuntimeDecision` validation (WP02)

**Implementation sketch**:

1. In `decision.py`, add a `__post_init__` (or peer construction-time validator) that enforces C1/C2 from `contracts/next-prompt-file-contract.md` for `kind=step`. If a step decision arrives with a null/empty/missing-file prompt, raise a typed error so the call site can fall back to `kind=blocked`.
2. In `runtime_bridge.py`, wrap each step-construction site (around lines 1571, 1662, 2118, 2138, 2225, 2271, 2310 in the current code) in a try/recover that produces `kind=blocked` with a reason like `"prompt_file_not_resolvable"` when the validator raises. Do NOT silently emit `kind=step` with a null prompt.
3. In `tests/e2e/test_charter_epic_golden_path.py`, replace the existing "key exists" check with the C1/C2 assertion (non-null, non-empty, `Path.is_file()`) for every `kind=step` envelope.
4. Scrub `SKILL.md` and the inline comment at `decision.py:79` that says "advance mode populates this"; replace with the C1/C2/C3 contract language.
5. Add a small test module under `tests/specify_cli/next/` with: positive case (`kind=step` with valid prompt → constructs cleanly); negative cases (`kind=step` with `prompt_file=None` and with non-existent path → either raise at construction OR are routed to `kind=blocked` by `runtime_bridge`); positive non-step (`kind=blocked` with null prompt → still legal).

**Risks**:
- A legitimate runtime path may currently rely on emitting `kind=step` with null prompts — call out in PR description and document any newly-routed `kind=blocked` cases. Mitigate by running `tests/next -q`, `tests/contract/test_next_no_implicit_success.py`, and `tests/contract/test_next_no_unknown_state.py` as smoke.

**Prompt file**: [tasks/WP02-charter-e2e-prompt-file-contract.md](tasks/WP02-charter-e2e-prompt-file-contract.md)

---

### WP03 — #845 dossier snapshot does not self-block transitions

**Goal**: Adopt the EXCLUDE ownership policy for `*/.kittify/dossiers/*/snapshot-latest.json`. Snapshots are gitignored AND explicitly filtered by the dirty-state preflight used by `agent tasks move-task` and related transitions. Real unrelated dirty state still blocks.

**Priority**: High (operator papercut for status-aware mission flows).
**Independent test**: `uv run pytest tests/integration/test_dossier_snapshot_no_self_block.py -q` passes; broader `uv run pytest tests/integration -k 'dossier or move_task or dirty or transition' -q` runs clean.
**Estimated prompt size**: ~310 lines.
**Dependencies**: none.
**Lane**: C (independent of WP01/02/04).

**Subtasks**:

- [x] T010 [P] Add `*/.kittify/dossiers/*/snapshot-latest.json` glob to root `.gitignore` (WP03)
- [x] T011 Add explicit path filter helper (`_is_dossier_snapshot(path)` or equivalent) in the dirty-state preflight code path in `src/specify_cli/cli/commands/agent/tasks.py` (and any peer in `src/specify_cli/status/`) (WP03)
- [x] T012 Author `tests/integration/test_dossier_snapshot_no_self_block.py` — green path (snapshot write → move-task succeeds) AND control case (unrelated dirty file still blocks, naming that file not the snapshot) (WP03)
- [x] T013 Verify `tests/integration -k 'dossier or move_task or dirty or transition'` runs clean (WP03)

**Implementation sketch**:

1. Add the glob pattern to root `.gitignore`. Verify with `git check-ignore -v <feature_dir>/.kittify/dossiers/<slug>/snapshot-latest.json` after change.
2. Locate the dirty-state preflight in `src/specify_cli/cli/commands/agent/tasks.py` (the move-task path). Add a small helper `_is_dossier_snapshot(path: Path) -> bool` that matches the glob in D1 from `data-model.md`. Call it to filter the dirty-files list before computing the gate.
3. If `src/specify_cli/status/` has helpers that drive the preflight, add the same filter there for consistency (belt-and-suspenders per R6 in research.md).
4. Author the regression test exercising the exact path that previously blocked, plus the control case. Make sure failure messages name the offending file (so the control case asserts "the unrelated file" is named, not the snapshot).

**Risks**:
- The preflight may pass through multiple wrapping layers — touch the layer closest to the gate decision to keep the change reviewable.
- `.gitignore` alone is insufficient if some preflight bypasses it; the explicit filter is the airtight version. Both are required (per research R6).

**Prompt file**: [tasks/WP03-dossier-snapshot-no-self-block.md](tasks/WP03-dossier-snapshot-no-self-block.md)

---

### WP04 — #846 specify/plan auto-commit boundary

**Goal**: Gate the auto-commit branches in `setup-plan` (and the specify equivalent) on `_is_substantive(file_path, kind)`. When the file is empty/template-scaffolded, do not auto-commit a "ready" envelope; emit `phase_complete=false` with `blocked_reason` so workflow status reflects the incomplete state. Document the boundary in templates.

**Priority**: High (workflow-state correctness).
**Independent test**: `uv run pytest tests/integration/test_specify_plan_commit_boundary.py -q` passes; broader `uv run pytest tests/integration -k 'specify or plan or auto_commit or mission' -q` runs clean.
**Estimated prompt size**: ~430 lines.
**Dependencies**: none.
**Lane**: D (independent of WP01/02/03).

**Subtasks**:

- [ ] T014 Implement `_substantive` helpers (`is_substantive` + `is_committed`) in new module `src/specify_cli/missions/_substantive.py` — section-presence only (no byte-length OR) (WP04)
- [ ] T015 `mission create` boundary fix: stop including `spec.md` in the create-time `safe_commit` call. Empty scaffolds remain untracked at create time (WP04)
- [ ] T016 `setup-plan` gates: entry check (spec must be committed AND substantive) + exit check (plan must be substantive). Both emit `phase_complete=False / blocked_reason` and skip the relevant commit on failure (WP04)
- [ ] T017 [P] Update mission templates `src/specify_cli/missions/<mission-type>/command-templates/{specify,plan}.md` AND author `tests/integration/test_specify_plan_commit_boundary.py` covering the five contract scenarios (WP04)
- [ ] T018 Verify `tests/integration -k 'specify or plan or auto_commit or mission'` and `tests/specify_cli/cli/commands/agent` run clean (WP04)

**Implementation sketch**:

1. Place `is_substantive(file_path, kind)` and `is_committed(file_path, repo_root)` in a new module `src/specify_cli/missions/_substantive.py`. **Section-presence only** for `is_substantive` — no byte-length OR. Detect template placeholders (`[NEEDS CLARIFICATION …]`, `[e.g., …]`) as NON-substantive.
2. In `mission create` (`src/specify_cli/cli/commands/agent/mission.py` around line 333): omit `spec.md` from the `safe_commit(files_to_commit=[...])` list. Keep `meta.json` and other genuine scaffolding files. Add a comment explaining the agent commits the populated `spec.md` from the slash-template.
3. In `setup-plan` (`mission.py` around line 973): add an entry gate (`is_committed(spec, repo) and is_substantive(spec, "spec")`) before any plan write/commit. Replace the existing `_commit_to_branch(plan_file, ...)` call with a gated version that only commits when `is_substantive(plan, "plan")`.
4. Ensure `mission setup-plan --json` payload reflects `phase_complete=False` with a `blocked_reason` in both gate-failure cases.
5. Update both command templates with a "Commit Boundary" subsection.
6. Author the regression test with the five contract scenarios (including: scaffold + 300 bytes prose stays NON-substantive).

**Risks**:
- Legacy missions whose `spec.md` was committed empty by the pre-fix `mission create` will be reported as incomplete by the new setup-plan entry gate until populated and re-committed. That is correct behavior — surface in PR description.
- Workflow status reporters and dashboards must read the new `phase_complete=False` cleanly. Smoke via `tests/integration -k 'mission'`.

**Prompt file**: [tasks/WP04-specify-plan-commit-boundary.md](tasks/WP04-specify-plan-commit-boundary.md)

---

## MVP scope

Operator-mandated: **WP01 first** (lands first in PR order). Strictly speaking, all four WPs ship in the same PR — there is no "MVP subset" to ship without the others. WP01-first is a sequencing preference for code review and merge order, not a scope reduction.

## Parallelization

All four WPs are independently implementable and have no upstream code dependencies. Suggested lane assignment (computed by `finalize-tasks`):

| Lane | WP | Reason |
|---|---|---|
| A | WP01 | Fully isolated to `tests/architectural/` + `docs/development/`. Preferred to land first in PR order. |
| B | WP02 | Owns `src/specify_cli/next/**`, doctrine SKILL.md, and the E2E test. No file overlap with other lanes. |
| C | WP03 | Owns `.gitignore`, `src/specify_cli/cli/commands/agent/tasks.py`, status helpers, and a new integration test. No overlap. |
| D | WP04 | Owns `src/specify_cli/missions/_substantive.py` (new), `src/specify_cli/cli/commands/agent/mission.py`, command-templates, and a new integration test. No overlap. |

## Out of scope (recap)

- #847 (closed).
- #822 stabilization backlog (#771, #726/#728/#729, #303/#662/#595, #260/#253/#631/#630/#629/#644/#317).
- Any redesign of dependency management beyond #848's drift-detection hygiene.
- Closing #827 itself (umbrella epic remains open).
- Merging PR #855 (superseded; reference only).
