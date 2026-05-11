# Tasks: TeamSpace Mission-State History Repair Coordination

**Mission**: teamspace-mission-state-repair-coordination-01KRB8AC
**Branch**: fix/teamspace-mission-state-closeout-guards → fix/teamspace-mission-state-closeout-guards
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|-----|---------|
| T001 | Confirm target branches (main) for each repo | WP01 | |
| T002 | Verify PR #1017 is merged (gate check) | WP01 | |
| T003 | Coordinate contributor freeze on kitty-specs/ paths | WP01 | |
| T004 | Document spec-kitty-runtime inclusion decision | WP01 | |
| T005 | Pull main + baseline audit in spec-kitty | WP02 | [P] |
| T006 | Pull main + baseline audit in spec-kitty-saas | WP02 | [P] |
| T007 | Pull main + baseline audit in spec-kitty-events | WP02 | [P] |
| T008 | Analyze audit results; record blocker counts by code | WP02 | |
| T009 | Run --fix in spec-kitty; review manifest | WP03 | |
| T010 | Run --fix in spec-kitty-saas; review manifest | WP03 | |
| T011 | Run --fix in spec-kitty-events; review manifest | WP03 | |
| T012 | Verify quarantine lists are explicit and reviewable | WP03 | |
| T013 | Post-repair audit + dry-run in spec-kitty | WP04 | [P] |
| T014 | Post-repair audit + dry-run in spec-kitty-saas | WP04 | [P] |
| T015 | Post-repair audit + dry-run in spec-kitty-events | WP04 | [P] |
| T016 | Verify side logs skipped, not transitions, in dry-run output | WP04 | |
| T017 | Create repair branch + PR in spec-kitty | WP05 | [P] |
| T018 | Create repair branch + PR in spec-kitty-saas | WP05 | [P] |
| T019 | Create repair branch + PR in spec-kitty-events | WP05 | [P] |
| T020 | Verify all PRs link to #979 and #920 | WP05 | |
| T021 | Re-audit from fresh clean checkouts of all repos | WP06 | |
| T022 | Confirm zero TeamSpace blockers across all repos | WP06 | |
| T023 | Comment on #979 with evidence table and close it | WP06 | |
| T024 | Re-assess #920; update child issue checklist | WP06 | |

## Requirements Coverage

| WP | Spec FRs |
|----|---------|
| WP01 | FR-001, C-004 |
| WP02 | FR-001, FR-002, NFR-001 |
| WP03 | FR-003, FR-004, FR-005, FR-006, FR-007, FR-008, NFR-002, C-001, C-002, C-003 |
| WP04 | FR-009, FR-010, FR-011, FR-012, NFR-003 |
| WP05 | FR-013, FR-014 |
| WP06 | FR-015, FR-016 |

---

## WP01: Repair Scope Confirmation and Freeze Coordination

**Priority**: Critical (must complete before any repair runs)
**Dependencies**: none
**Estimated prompt size**: ~180 lines

### Goal
Confirm the exact repos, branches, and prerequisites before running any repair commands. Document the runtime inclusion decision for spec-kitty-runtime. Establish the contributor freeze window.

### Subtasks
- [x] T001 Confirm target branches (main) for each repo (WP01)
- [x] T002 Verify PR #1017 is merged (gate check) (WP01)
- [x] T003 Coordinate contributor freeze on kitty-specs/ paths (WP01)
- [x] T004 Document spec-kitty-runtime inclusion decision (WP01)

### Implementation sketch
Run `gh pr view 1017 --repo Priivacy-ai/spec-kitty --json state,mergedAt` to confirm the gate. Pull main in each repo and verify branch is clean. Document the freeze request as a comment on #979.

### Risks
- If PR #1017 is not merged, the entire repair sequence must halt.
- Contributors editing kitty-specs/ during repair will create dirty-path conflicts.

---

## WP02: Baseline Audits

**Priority**: Critical
**Dependencies**: WP01
**Estimated prompt size**: ~280 lines

### Goal
Run `spec-kitty doctor mission-state --audit --json` in each selected repo from a clean main pull. Save JSON reports as `../<repo>.before.audit.json`. Record blocker counts by code.

### Subtasks
- [ ] T005 Pull main + baseline audit in spec-kitty (WP02)
- [ ] T006 Pull main + baseline audit in spec-kitty-saas (WP02)
- [ ] T007 Pull main + baseline audit in spec-kitty-events (WP02)
- [ ] T008 Analyze audit results; record blocker counts by code (WP02)

### Implementation sketch
For each repo: `git checkout main && git pull --ff-only origin main && SPEC_KITTY_ENABLE_SAAS_SYNC=1 spec-kitty doctor mission-state --audit --json > ../<repo>.before.audit.json`. T005-T007 are parallel-safe (different repos). T008 reads all three outputs and summarizes.

### Parallel opportunities
T005, T006, T007 can run in parallel (separate repo directories).

### Risks
- If any repo has unexpected non-repairable errors, repair must not proceed for that repo without investigation.
- Dirty working tree in any repo will block the audit.

---

## WP03: Run Deterministic Repair

**Priority**: Critical
**Dependencies**: WP02
**Estimated prompt size**: ~320 lines

### Goal
Run `spec-kitty doctor mission-state --fix` in each selected repo. Review the generated manifest for each repo. Verify quarantine lists are explicit.

### Subtasks
- [ ] T009 Run --fix in spec-kitty; review manifest (WP03)
- [ ] T010 Run --fix in spec-kitty-saas; review manifest (WP03)
- [ ] T011 Run --fix in spec-kitty-events; review manifest (WP03)
- [ ] T012 Verify quarantine lists are explicit and reviewable (WP03)

### Implementation sketch
For each repo (sequentially, to avoid concurrent repair locks): `SPEC_KITTY_ENABLE_SAAS_SYNC=1 spec-kitty doctor mission-state --fix`. Then: read `.kittify/migrations/mission-state/<manifest>` and confirm it contains `repo_head`, `checksums`, `row_transformations`, `quarantine_count`, `validation_results`.

### Risks
- Concurrent repair in two clones could produce different manifests; run serially.
- Quarantine means a row could not be repaired; must be documented before raising PRs.
- If manifest is missing required fields, repair is incomplete.

---

## WP04: Post-Repair Dry-Run Validation

**Priority**: Critical
**Dependencies**: WP03
**Estimated prompt size**: ~300 lines

### Goal
Run post-repair audit and TeamSpace dry-run in each repo. Assert `missions_with_teamspace_blockers == 0` and `envelope_validation_errors == []`. Verify runtime side logs are reported as skipped, not as status transitions.

### Subtasks
- [ ] T013 Post-repair audit + dry-run in spec-kitty (WP04)
- [ ] T014 Post-repair audit + dry-run in spec-kitty-saas (WP04)
- [ ] T015 Post-repair audit + dry-run in spec-kitty-events (WP04)
- [ ] T016 Verify side logs skipped, not transitions, in dry-run output (WP04)

### Implementation sketch
For each repo: `SPEC_KITTY_ENABLE_SAAS_SYNC=1 spec-kitty doctor mission-state --audit --json > ../<repo>.after.audit.json` then `SPEC_KITTY_ENABLE_SAAS_SYNC=1 spec-kitty doctor mission-state --teamspace-dry-run --json > ../<repo>.dry-run.json`. Assert gates programmatically with Python one-liners.

### Parallel opportunities
T013, T014, T015 can run in parallel after WP03 completes.

### Risks
- Dry-run requiring `SPEC_KITTY_ENABLE_SAAS_SYNC=1` on this machine — missing env var produces incomplete output.
- Side logs from spec-kitty-runtime (if present) must appear as skipped, not imported.

---

## WP05: Create Repair Branches and PRs

**Priority**: High
**Dependencies**: WP04
**Estimated prompt size**: ~260 lines

### Goal
For each repaired repo, create a `repair/teamspace-mission-state-history` branch, commit the repair artifacts (manifest + modified kitty-specs/), and raise a PR to `main`. Each PR body must satisfy the contract in `contracts/cli-contracts.md`.

### Subtasks
- [ ] T017 Create repair branch + PR in spec-kitty (WP05)
- [ ] T018 Create repair branch + PR in spec-kitty-saas (WP05)
- [ ] T019 Create repair branch + PR in spec-kitty-events (WP05)
- [ ] T020 Verify all PRs link to #979 and #920 (WP05)

### Implementation sketch
For each repo: `git checkout -b repair/teamspace-mission-state-history`, `git add .kittify/migrations/mission-state/ kitty-specs/`, `git commit -m "repair: TeamSpace mission-state history — deterministic repair manifest"`, then `gh pr create --base main --title "repair: TeamSpace mission-state history (<repo>)" --body "..."`. The PR body must include before/after audit summaries, dry-run result, manifest path, and links to #979 and #920.

### Parallel opportunities
T017, T018, T019 can run in parallel after WP04 completes.

---

## WP06: Closeout

**Priority**: High
**Dependencies**: WP05 (all PRs merged)
**Estimated prompt size**: ~220 lines

### Goal
After all repair PRs are merged, re-audit from fresh clean checkouts of each repo. Confirm zero TeamSpace blockers. Comment on #979 with the full evidence table and close it. Re-assess #920 parent epic.

### Subtasks
- [ ] T021 Re-audit from fresh clean checkouts of all repos (WP06)
- [ ] T022 Confirm zero TeamSpace blockers across all repos (WP06)
- [ ] T023 Comment on #979 with evidence table and close it (WP06)
- [ ] T024 Re-assess #920; update child issue checklist (WP06)

### Implementation sketch
For each repo: fresh clone or `git fetch && git checkout main && git pull --ff-only`, then `SPEC_KITTY_ENABLE_SAAS_SYNC=1 spec-kitty doctor mission-state --audit --json`. Aggregate results into an evidence table. `gh issue comment 979 --repo Priivacy-ai/spec-kitty --body "..."` then `gh issue close 979 --repo Priivacy-ai/spec-kitty`. Check #920 child issue checklist and update any newly completed items.

### Risks
- WP06 cannot start until all repair PRs from WP05 are merged.
- If any post-merge audit shows blockers, WP06 fails and the corresponding repo's repair must be re-examined.
