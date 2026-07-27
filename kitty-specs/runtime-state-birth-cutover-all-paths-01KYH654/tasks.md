# Tasks: Runtime-State Birth-Cutover (All Landing Paths)

**Mission**: `runtime-state-birth-cutover-all-paths-01KYH654`
**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Contracts**: [stamp-seam](./contracts/stamp-seam.md), [pre-merge-guard](./contracts/pre-merge-guard.md)

5 work packages across 3 lanes. MVP = WP02 (the auto-stamp closes the leak);
WP03+WP04 (the guard) is the binding backstop and must ship this mission.

## Lanes & dependencies

- **Lane A**: WP01 → WP02 (anchor pin → auto-stamp)
- **Lane B**: WP03 → WP04 (guard logic → CI wiring)
- **Lane C**: WP05 (doctor audit, independent)

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Identify the canonical anchor leg and its resolution path | WP01 | |
| T002 | Pin `_resolve_anchor`/`_synthesize_claim_anchor` to the canonical leg | WP01 | |
| T003 | Red-first: payload-determinism-across-legs test | WP01 | [P] |
| T004 | Assert byte-identical `status.events.jsonl` across contexts | WP01 | |
| T005 | Locate the terminal `accept` seam & confirm runtime-state finality | WP02 | |
| T006 | Add the accept-time `cutover_mission` caller (mirror `_run_birth_cutover`) | WP02 | |
| T007 | Commit both partitions into the branch (PRIMARY meta, COORD events), resume-heal | WP02 | |
| T008 | Fail closed on absent `mission_id`; no slug-namespaced seeds | WP02 | |
| T009 | Red-first: GitHub-squash-merge simulation acceptance test | WP02 | [P] |
| T010 | Red-first: accept-time idempotency test | WP02 | [P] |
| T011 | Extract the event-log-evidence eligibility predicate to a shared src module | WP03 | |
| T012 | Build the diff-scoped guard: compute changed missions, decide cut-over via the shared predicate | WP03 | |
| T013 | Fail closed on verify error / ambiguity / absent `mission_id`; print exact remedy | WP03 | |
| T014 | Red-first: guard reds on native un-cut-over mission (vacuity trap); passes all-cut-over | WP03 | [P] |
| T015 | Update the CLI-surface census for the new guard command | WP03 | |
| T016 | Host the guard in a `pull_request`-scoped job; add `kitty-specs/**` to trigger paths | WP04 | |
| T017 | Ensure the job runs outside the src `changes` filter and cannot be silently skipped | WP04 | |
| T018 | Register as a required status check; document the required-checks contract | WP04 | |
| T019 | Live verify: scratch corpus-only PR triggers the guard and can fail; measure <30s | WP04 | |
| T020 | Add `spec-kitty doctor cutover` subcommand shell → `_cutover_doctor.py` | WP05 | |
| T021 | Back the audit with `cutover_repo(dry_run=True)`; render per-mission status | WP05 | |
| T022 | Update the CLI-surface census for the new doctor subcommand | WP05 | |
| T023 | Red-first: doctor cutover reports un-cut-over vs cut-over correctly | WP05 | [P] |

## Work Packages

### WP01 — Pin claim-anchor to one canonical leg (IC-02)

- **Goal**: Make the seed payload (incl. the resolved claim anchor) byte-identical across runs, machines, and landing-path contexts, so the two stamp callers cannot diverge.
- **Priority**: High (prerequisite for WP02). **Requirements**: NFR-004.
- **Independent test**: Run the seed twice from different leg contexts → identical `status.events.jsonl` bytes.
- **Dependencies**: none.

- [ ] T001 Identify the canonical anchor leg and its resolution path (WP01)
- [ ] T002 Pin anchor resolution to the canonical leg (WP01)
- [ ] T003 Red-first payload-determinism test (WP01)
- [ ] T004 Assert byte-identical events across contexts (WP01)

### WP02 — Auto-stamp cutover at the terminal `accept` seam (IC-01)

- **Goal**: Stamp the cutover into the mission branch at `accept`, committed before the branch can land, reusing the single authority `cutover_mission`.
- **Priority**: High (MVP — closes the leak). **Requirements**: FR-001, FR-004, FR-005, FR-006, NFR-003.
- **Independent test**: Finalize a mission, stamp at accept, simulate a GitHub squash merge → target-branch corpus is cut over with no post-merge step.
- **Dependencies**: WP01.

- [ ] T005 Locate the accept seam & confirm runtime finality (WP02)
- [ ] T006 Add the accept-time `cutover_mission` caller (WP02)
- [ ] T007 Commit both partitions into the branch, resume-heal (WP02)
- [ ] T008 Fail closed on absent `mission_id` (WP02)
- [ ] T009 Red-first GitHub-squash simulation test (WP02)
- [ ] T010 Red-first idempotency test (WP02)

### WP03 — Diff-scoped fail-closed guard + shared eligibility predicate (IC-03)

- **Goal**: Reject any change set leaving an un-cut-over mission, evaluating every mission in the PR diff via the event-log-evidence predicate (not bare `verify_backfill`).
- **Priority**: High (binding backstop). **Requirements**: FR-002, FR-003, FR-009, NFR-002, NFR-003.
- **Independent test**: A diff with a native un-cut-over mission reds the guard with name + remedy; an all-cut-over diff passes.
- **Dependencies**: none.

- [ ] T011 Extract the eligibility predicate to a shared src module (WP03)
- [ ] T012 Build the diff-scoped guard (WP03)
- [ ] T013 Fail closed + exact remedy message (WP03)
- [ ] T014 Red-first native-vacuity + all-cut-over tests (WP03)
- [ ] T015 Update CLI-surface census for the guard command (WP03)

### WP04 — CI wiring + live corpus-only-PR verification (IC-04)

- **Goal**: Ensure the guard fires on corpus-only PRs and is a required, non-skippable check.
- **Priority**: High. **Requirements**: FR-008, NFR-001, SC-004.
- **Independent test**: A scratch PR touching only `kitty-specs/**` shows the guard job running and able to fail.
- **Dependencies**: WP03.

- [ ] T016 Host the guard on `pull_request`; add `kitty-specs/**` paths (WP04)
- [ ] T017 Outside the src `changes` filter; not silently skippable (WP04)
- [ ] T018 Register as a required check; document contract (WP04)
- [ ] T019 Live-verify corpus-only PR + measure <30s (WP04)

### WP05 — On-demand `doctor cutover` audit (IC-05)

- **Goal**: Let an operator list every mission's cut-over status outside CI.
- **Priority**: Medium. **Requirements**: FR-007.
- **Independent test**: `spec-kitty doctor cutover` reports un-cut-over vs cut-over missions correctly.
- **Dependencies**: none.

- [ ] T020 Add the doctor cutover subcommand shell (WP05)
- [ ] T021 Back with `cutover_repo(dry_run=True)` (WP05)
- [ ] T022 Update CLI-surface census (WP05)
- [ ] T023 Red-first doctor cutover reporting test (WP05)
