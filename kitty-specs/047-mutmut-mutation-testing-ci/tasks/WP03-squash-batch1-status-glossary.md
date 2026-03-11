---
work_package_id: WP03
title: Squash Survivors — Batch 1 (status/, glossary/)
lane: done
dependencies:
- WP02
subtasks:
- T011
- T012
- T013
- T014
- T015
- T016
- T017
phase: Phase 2 - Squashing Campaign
assignee: ''
agent: ''
shell_pid: ''
review_status: ''
reviewed_by: ''
review_feedback: ''
history:
- timestamp: '2026-03-01T16:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
requirement_refs:
- FR-009
- FR-010
- FR-011
- FR-012
---

# Work Package Prompt: WP03 – Squash Survivors — Batch 1 (status/, glossary/)

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check `review_status`. If it says `has_feedback`, read `review_feedback` first.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback, update `review_status: acknowledged`.

---

## Review Feedback

*No feedback yet — this is a fresh work package.*

---

## Markdown Formatting

Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ` ```python `, ` ```bash `

---

## Objectives & Success Criteria

- All **killable** surviving mutants in `src/specify_cli/status/` have been killed by targeted tests.
- All **killable** surviving mutants in `src/specify_cli/glossary/` have been killed by targeted tests.
- Any **equivalent** mutants are documented in `kitty-specs/047-mutmut-mutation-testing-ci/mutmut-equivalents.md` with a written rationale.
- Mutation score for the combined `status/` + `glossary/` scope is measurably higher than the pre-campaign baseline.
- All existing tests continue to pass.

## Context & Constraints

- **Branch**: `architecture/restructure_and_proposals` (no worktree)
- **Depends on**: WP02 (CI wired up; provides report format to compare against)
- **Priority modules** (from `plan.md` research decision): `status/` and `glossary/` are correctness-critical — state machines, transition guards, term parsing.
- **Spec FR-009, FR-010**: Developers must be able to inspect surviving mutants and re-run after test improvements.
- **Spec FR-012**: Killable mutants in the priority scope must be killed.
- **Key files in scope**:
  - `src/specify_cli/status/transitions.py` — 7-lane state machine, 16-pair allow-list
  - `src/specify_cli/status/store.py` — JSONL append/read with corruption detection
  - `src/specify_cli/status/reducer.py` — deterministic event → snapshot
  - `src/specify_cli/status/emit.py` — orchestration pipeline
  - `src/specify_cli/glossary/` — term parsing, context loading, semantic integrity

**Implementation command** (since WP02 is the dependency):
```bash
spec-kitty implement WP03 --base WP02
```
*(No worktree for this feature — work directly on the branch.)*

## Subtasks & Detailed Guidance

### Subtask T011 – Run mutmut on status/ and record survivors

**Purpose**: Establish the pre-campaign baseline for `status/` and identify all
surviving mutants before writing any new tests.

**Steps**:
1. Run mutmut scoped to the status module:
   ```bash
   mutmut run --paths-to-mutate src/specify_cli/status/
   ```
2. After the run completes (may take 10–30 minutes), run:
   ```bash
   mutmut results
   ```
3. Record the total mutant count, killed count, and surviving mutant IDs.
   Note the IDs in a scratch file or comment — you'll need them in T012.
4. Export the stats for later comparison:
   ```bash
   mkdir -p out/reports/mutation
   mutmut export-cicd-stats --output out/reports/mutation/mutation-stats-status-baseline.json
   ```

**Files**: None modified (measurement step). `out/reports/mutation/` is gitignored.

**Notes**: If the run takes more than 30 minutes, it is still expected — status/ is
the most complex module. Let it run to completion.

---

### Subtask T012 – Triage status/ survivors

**Purpose**: Classify each surviving mutant as killable (a test gap exists) or
equivalent (the mutation produces semantically identical behaviour).

**Steps**:
1. For each surviving mutant ID from T011, run:
   ```bash
   mutmut show <id>
   ```
2. Read the diff. Ask: "Can I write a test that passes for the original code but
   fails for this mutation?"
   - **Yes → killable**: Note the ID and what test would kill it.
   - **No → equivalent**: Note the ID and why the mutation is semantically identical.
3. Examples of killable mutants in status/:
   - Mutation changes `"planned"` → `"claimed"` in a constant — a test asserting the initial lane name kills it.
   - Mutation removes a guard condition — a test that exercises the guard path kills it.
4. Examples of equivalent mutants:
   - Mutation changes `x + 0` to `x - 0` — same result.
   - Mutation changes order of two commutative operations — same result.
5. Create a mental (or scratch) list:
   - Killable IDs: [list them]
   - Equivalent IDs: [list them]

**Files**: None modified (triage step)

---

### Subtask T013 – Write tests to kill status/ mutants

**Purpose**: Write targeted tests that exercise the code paths the surviving mutants
changed, killing them.

**Steps**:
1. For each killable mutant from T012, identify the exact file and line.
2. Look at the existing tests for that file:
   ```bash
   ls tests/unit/status/
   # or wherever status tests live
   ```
3. Either extend an existing test or create a new test function in the appropriate file.
4. Test naming: `test_<behaviour_being_verified>` — make it descriptive.
5. After writing each batch of tests, re-run mutmut for the file containing those mutants:
   ```bash
   mutmut run --paths-to-mutate src/specify_cli/status/transitions.py
   mutmut results
   ```
6. Confirm the previously surviving mutant is now killed.
7. Repeat for all killable mutants.

**Focus areas** (highest-value targets in status/):
- `transitions.py`: ALLOWED_TRANSITIONS pairs — any mutant changing a from/to pair should be killed by a test asserting that transition is or is not allowed.
- `store.py`: JSONL append/read — mutants corrupting the serialisation format should be caught by round-trip tests.
- `reducer.py`: `reduce()` function — mutants changing snapshot computation should be caught by tests asserting specific snapshot fields.

**Files**: `tests/unit/status/*.py` (extend or create)

**Validation**:
```bash
# Run existing + new tests to confirm nothing regresses
pytest tests/unit/status/ -v
# Re-run mutmut and confirm killed count increased
mutmut run --paths-to-mutate src/specify_cli/status/
mutmut results
```

---

### Subtask T014 – Run mutmut on glossary/ and record survivors

**Purpose**: Same as T011 but for the glossary module.

**Steps**:
1. Run mutmut scoped to the glossary module:
   ```bash
   mutmut run --paths-to-mutate src/specify_cli/glossary/
   ```
2. Record survivors:
   ```bash
   mutmut results
   ```
3. Export baseline stats:
   ```bash
   mutmut export-cicd-stats --output out/reports/mutation/mutation-stats-glossary-baseline.json
   ```

**Files**: None modified (measurement step).

---

### Subtask T015 – Triage glossary/ survivors

**Purpose**: Classify glossary/ surviving mutants as killable or equivalent.

**Steps**: Same triage process as T012, applied to glossary/ mutants.

**Focus areas in glossary/**:
- Term parsing functions — mutations changing string comparisons or regex patterns.
- Context loading — mutations altering file path resolution or YAML key lookups.
- Semantic integrity pipeline — mutations skipping validation steps.

**Files**: None modified (triage step)

---

### Subtask T016 – Write tests to kill glossary/ mutants

**Purpose**: Write targeted tests for glossary/ surviving mutants.

**Steps**:
1. For each killable mutant from T015, follow the same write → run → verify loop as T013.
2. Test location: `tests/unit/glossary/` (create if not present) or existing glossary test files.
3. Re-run mutmut on the specific file after writing each batch of tests.

**Files**: `tests/unit/glossary/*.py` (extend or create)

**Validation**:
```bash
pytest tests/unit/glossary/ -v
mutmut run --paths-to-mutate src/specify_cli/glossary/
mutmut results
```

---

### Subtask T017 – Create mutmut-equivalents.md

**Purpose**: Document all equivalent mutants found during this batch so they are
not re-triaged in future campaigns and so reviewers understand what was not killed
and why.

**Steps**:
1. Create the file:
   ```
   kitty-specs/047-mutmut-mutation-testing-ci/mutmut-equivalents.md
   ```
2. For each equivalent mutant identified in T012 and T015, add a section:

```markdown
## Equivalent Mutants

### status/ equivalents

| Mutant ID | File | Line | Mutation | Rationale |
|-----------|------|------|----------|-----------|
| 42 | status/transitions.py | 88 | `>=` → `>` | Off-by-one in a constant boundary that is never reached in practice due to the lane set being finite |

### glossary/ equivalents

| Mutant ID | File | Line | Mutation | Rationale |
|-----------|------|------|----------|-----------|
| 107 | glossary/parser.py | 34 | `strip()` → `lstrip()` | Input is always stripped upstream; trailing whitespace never reaches this point |
```

3. If there are no equivalent mutants, write: "No equivalent mutants identified in this batch."

**Files**: `kitty-specs/047-mutmut-mutation-testing-ci/mutmut-equivalents.md` (new)

## Risks & Mitigations

- **Large number of survivors**: Prioritise by criticality — kill transition guards first (`transitions.py`), then store round-trips (`store.py`), then anything touching Lane enum values.
- **Slow re-runs**: Scope re-runs to a single file (`--paths-to-mutate src/specify_cli/status/transitions.py`) rather than the full module to get fast feedback.
- **Equivalent mutants are misclassified as killable**: When in doubt, write the test — if it's truly equivalent, the test will either be trivially weak or prove the equivalence. It's better to have an extra test than to miss a real gap.

## Review Guidance

- Confirm the surviving mutant count in `status/` is lower after new tests than the T011 baseline.
- Confirm the surviving mutant count in `glossary/` is lower after new tests than the T014 baseline.
- Spot-check 2–3 of the new tests: do they actually exercise the mutated code path, or are they superficial?
- Confirm `mutmut-equivalents.md` exists and each entry has a rationale.
- Run `pytest tests/unit/status/ tests/unit/glossary/` to confirm all tests pass.

## Activity Log

- 2026-03-01T16:00:00Z – system – lane=planned – Prompt created.
- 2026-03-01T07:16:56Z – unknown – lane=in_progress – Starting WP03 squashing campaign: status/ and glossary/
