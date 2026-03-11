---
work_package_id: WP05
title: Enforce Floor
lane: done
dependencies:
- WP04
subtasks:
- T023
- T024
- T025
- T026
- T027
phase: Phase 3 - Hardening
assignee: ''
agent: ''
shell_pid: ''
review_status: approved
reviewed_by: Stijn Dejongh
review_feedback: ''
history:
- timestamp: '2026-03-01T16:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
requirement_refs:
- FR-013
- C-003
---

# Work Package Prompt: WP05 – Enforce Floor

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

- The full mutation suite has been run against all four priority modules (`status/`, `glossary/`, `merge/`, `core/`) after the squashing campaigns.
- The achieved mutation score has been recorded and rounded down to the nearest 5%.
- `MUTATION_FLOOR` in `.github/workflows/ci-quality.yml` is updated to the computed value (must be > 0%).
- A push confirms the `mutation-testing` CI job passes at the new floor.
- The failure path is spot-checked: setting the floor 5% above the actual score causes CI to exit non-zero with a descriptive message.
- `spec.md` constraint C-003 status is updated from `Open` to `Done`.

## Context & Constraints

- **Branch**: `architecture/restructure_and_proposals` (no worktree)
- **Depends on**: WP04 (all squashing complete in both batches)
- **Constraint C-003**: "The feature is not done while the floor remains at 0%." This WP closes C-003.
- **Spec SC-004**: Setting the floor above the actual score causes CI to exit non-zero with a descriptive message.
- **Spec SC-006**: Mutation score for priority scope is measurably higher than pre-campaign baseline.
- **Floor formula**: `floor(score_percent / 5) * 5` — round down to nearest 5%.
  - Example: 73% achieved → floor set to 70%.
  - Example: 50% achieved → floor set to 50%.

**Implementation command** (since WP04 is the dependency):
```bash
spec-kitty implement WP05 --base WP04
```
*(No worktree for this feature — work directly on the branch.)*

## Subtasks & Detailed Guidance

### Subtask T023 – Run full priority-scope mutation suite

**Purpose**: Produce the definitive post-squashing mutation score for all four
priority modules combined, to compute the floor value.

**Steps**:
1. Ensure all new tests from WP03 and WP04 are committed and passing:
   ```bash
   pytest tests/unit/status/ tests/unit/glossary/ tests/unit/merge/ tests/unit/core/ -v
   ```
2. Run mutmut against all four modules:
   ```bash
   mutmut run --paths-to-mutate src/specify_cli/status/ \
                                src/specify_cli/glossary/ \
                                src/specify_cli/merge/ \
                                src/specify_cli/core/
   ```
   This may take 20–60 minutes depending on module sizes.
3. After completion, export the combined stats:
   ```bash
   mkdir -p out/reports/mutation
   mutmut export-cicd-stats --output out/reports/mutation/mutation-stats-final.json
   ```
4. Record the output of:
   ```bash
   mutmut results
   ```

**Files**: None modified (measurement step). `out/reports/mutation/` is gitignored.

**Notes**: If the combined run is too slow (>60 minutes), run each module separately
and add up the killed/survived counts manually to compute the combined score.

---

### Subtask T024 – Compute floor value

**Purpose**: Determine the floor value to configure in CI.

**Steps**:
1. From the T023 stats, extract killed and survived counts:
   ```bash
   cat out/reports/mutation/mutation-stats-final.json
   ```
   Look for `killed` and `survived` fields.
2. Compute the score:
   ```
   score_pct = int(killed / (killed + survived) * 100)
   ```
3. Round down to the nearest 5%:
   ```python
   floor_value = (score_pct // 5) * 5
   ```
   Example: killed=95, survived=25 → score=79% → floor=75%
4. Record both values: `score_pct` (actual) and `floor_value` (what goes in CI).

**Files**: None (calculation step)

**Validation**:
- floor_value must be > 0. If the squashing campaigns produced no improvement,
  escalate before closing this WP.
- floor_value must be ≤ score_pct (we never set the floor above what we achieved).

---

### Subtask T025 – Update MUTATION_FLOOR in ci-quality.yml

**Purpose**: Change the floor from 0 to the value computed in T024, so CI enforces
a meaningful quality gate going forward.

**Steps**:
1. Open `.github/workflows/ci-quality.yml`.
2. Find the `mutation-testing` job's `env:` block:
   ```yaml
       env:
         MUTATION_FLOOR: 0  # Raised to achieved baseline after squashing campaign (WP05)
   ```
3. Update to the computed floor value:
   ```yaml
       env:
         MUTATION_FLOOR: 75  # Achieved baseline: 79% (rounded down to nearest 5%)
   ```
   (Replace `75` and `79` with the actual values from T024.)
4. Update the comment to reflect the actual score and the date.

**Files**: `.github/workflows/ci-quality.yml`

**Can be done in parallel with T027.**

---

### Subtask T026 – Push and verify CI at new floor

**Purpose**: Confirm the enforcement mechanism works end-to-end on the real CI
infrastructure.

**Steps**:
1. Commit all changes (T025, T027) and push to `architecture/restructure_and_proposals`:
   ```bash
   git push origin architecture/restructure_and_proposals
   ```
2. Monitor the `mutation-testing` job in GitHub Actions.
3. Confirm the job passes: `check_mutation_floor.py` reports "PASS: mutation score meets or exceeds the floor."
4. **Spot-check the failure path** (important — validates the mechanism, not just the happy path):
   - Temporarily set `MUTATION_FLOOR` to `floor_value + 5` (one tick above the actual floor).
   - Push (or trigger `workflow_dispatch`).
   - Confirm the job exits non-zero with the message: "FAIL: mutation score X% is below the configured floor of Y%."
   - Reset `MUTATION_FLOOR` back to `floor_value` and push again.

**Files**: None (verification step — changes to CI YAML from T025)

**Notes**:
- If the CI run times out (75-minute limit), the job will be cancelled. Check if this
  is consistent behaviour or a one-off. If consistent, consider splitting the scope
  into two CI runs.
- The spot-check failure push is temporary. Reset the floor before the final commit.

---

### Subtask T027 – Update spec.md constraint C-003 status

**Purpose**: Close out the spec-level constraint that required a meaningful floor
to be set after the squashing campaign.

**Steps**:
1. Open `kitty-specs/047-mutmut-mutation-testing-ci/spec.md`.
2. Find the Constraints table entry for C-003:
   ```markdown
   | C-003 | Initial floor at 0%, raised after squashing | The floor starts at 0% ... | Business | High | Open |
   ```
3. Update the Status column from `Open` to `Done` and append a note with the achieved
   value:
   ```markdown
   | C-003 | Initial floor at 0%, raised after squashing | ... floor set to <floor_value>% after squashing campaign (score: <score_pct>%) | Business | High | Done |
   ```
4. Replace `<floor_value>` and `<score_pct>` with the actual values from T024.

**Files**: `kitty-specs/047-mutmut-mutation-testing-ci/spec.md`

**Can be done in parallel with T025.**

## Risks & Mitigations

- **Achieved score is very low (< 20%)**: Still set the floor to the achieved value — it's better than 0%. Document the low score in the commit message and note that further campaigns will raise it.
- **CI timeout on combined run**: If the four-module mutation run hits 75 minutes consistently, split the run into two jobs (e.g., `mutation-testing-core` covering status+glossary, and `mutation-testing-extended` covering merge+core). Update `check_mutation_floor.py` to read a combined stats file.
- **Spot-check push pollutes branch history**: Use `git push --force` (only on this feature branch, never on main) to remove the temporary floor-bump commit after confirming the failure path, OR use `workflow_dispatch` to trigger the failure check without a commit (if `inputs.run_extended` is already set).

## Review Guidance

- Confirm `MUTATION_FLOOR` in `ci-quality.yml` is > 0.
- Confirm the floor value matches `floor(score_pct / 5) * 5` for the stated score.
- Confirm the CI job passed on the push with the new floor.
- Confirm the spec.md C-003 status is `Done` with the achieved value noted.
- Review the `mutmut-equivalents.md` file to confirm all undead survivors have a rationale.
- Check that no surviving mutants were silently left unkilled without classification.

## Activity Log

- 2026-03-01T16:00:00Z – system – lane=planned – Prompt created.
- 2026-03-02T04:15:58Z – unknown – lane=done – Done override: MUTATION_FLOOR=70 set in CI; spec.md C-003 marked Done; floor verified at 70.5% baseline
