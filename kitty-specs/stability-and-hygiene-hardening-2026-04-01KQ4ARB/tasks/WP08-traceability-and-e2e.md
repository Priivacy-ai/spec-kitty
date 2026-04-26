---
work_package_id: WP08
title: Issue Traceability + Cross-Repo E2E Gates
dependencies:
- WP01
- WP02
- WP03
- WP04
- WP05
- WP06
- WP07
requirement_refs:
- FR-037
- FR-038
- FR-039
- FR-040
- FR-041
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T044
- T045
- T046
- T047
- T048
- T049
- T050
agent: "claude:opus-4-7:implementer:implementer"
shell_pid: "31585"
history:
- at: 2026-04-26T07:36:00Z
  actor: claude
  note: WP scaffolded by /spec-kitty.tasks
authoritative_surface: kitty-specs/stability-and-hygiene-hardening-2026-04-01KQ4ARB/issue-matrix.md
execution_mode: code_change
mission_id: 01KQ4ARB0P4SFB0KCDMVZ6BXC8
mission_slug: stability-and-hygiene-hardening-2026-04-01KQ4ARB
owned_files:
- kitty-specs/stability-and-hygiene-hardening-2026-04-01KQ4ARB/issue-matrix.md
- architecture/2.x/adr/2026-04-26-3-e2e-hard-gate.md
- .agents/skills/spec-kitty-mission-review/**
- docs/migration/cross-repo-e2e-gate.md
tags: []
---

# WP08 — Issue Traceability + Cross-Repo E2E Gates

## Objective

Build the issue traceability matrix that the mission-review will check.
Add four end-to-end scenarios in `spec-kitty-end-to-end-testing` that
prove the cross-repo behavior. Wire the mission-review skill to enforce
the contract gate AND the e2e gate. Record an ADR.

## Context

WP08 lands last; its lane base must include every other WP's tip. The
e2e scenarios this WP creates live in the `spec-kitty-end-to-end-testing`
repo, NOT in `spec-kitty/tests/`. Cross-repo work is documented in the
e2e repo's CHANGELOG. Decisions in `research.md` D1 and the contract
markdown for events / runtime / intake.

## Branch strategy

- **Planning base**: tip of last predecessor lane (encoded by
  finalize-tasks).
- **Final merge target**: `main`.
- **Lane workspace**: assigned by `finalize-tasks`. Use
  `spec-kitty agent action implement WP08 --agent <name>`.

Cross-repo note: This WP touches **two** git repos:
- `spec-kitty/` (this repo) for the matrix, the ADR, the mission-review
  skill, and the migration doc.
- `spec-kitty-end-to-end-testing/` for the four e2e scenarios.

The implementer commits to each repo separately; the operator merges
both before mission acceptance.

## Subtasks

### T044 — `issue-matrix.md` scaffold + populated traceability matrix

**Purpose**: One row per GitHub issue listed in `start-here.md`, with a
verdict and an evidence pointer.

**Steps**:

1. Create
   `kitty-specs/stability-and-hygiene-hardening-2026-04-01KQ4ARB/issue-matrix.md`
   with a header block and a markdown table:
   ```markdown
   | repo | issue | theme | verdict | wp_id | evidence_ref |
   |------|-------|-------|---------|-------|--------------|
   ```
2. Populate one row per issue in `start-here.md`. Verdict is one of:
   - `fixed` — bug present, fix landed in WPxx, evidence is a test
     name or commit SHA.
   - `verified-already-fixed` — bug was already fixed on `main`;
     evidence is a regression test name that would have failed
     pre-fix.
   - `deferred-with-followup` — bug deferred; evidence is a follow-up
     issue link.
3. The matrix is a **planning artifact** — this is the only WP marked
   `execution_mode: code_change` whose primary deliverable is a
   markdown file in `kitty-specs/`. The justification is that the
   matrix is large enough to warrant lane allocation and review.

**Validation**:
- The matrix row count equals the issue count from `start-here.md`
  (no rows missing).
- Every row has a non-empty `verdict` and `evidence_ref`.
- No row has the verdict `unknown`.

### T045 — E2E: dependent-WP planning lane merges without data loss

**Purpose**: Cross-repo proof of FR-001 + FR-005 + FR-038.

**Steps**:

1. In `spec-kitty-end-to-end-testing/scenarios/dependent_wp_planning_lane.py`,
   add a scenario that:
   - Creates a fixture mission with 3 sequential implementation WPs +
     1 planning lane.
   - Drives each WP through `for_review` and `approved` via the
     standard runtime.
   - Runs `spec-kitty merge`.
   - Asserts every approved commit (including the planning artifact)
     appears in `git log <merge-target>` after merge.
2. Run with `SPEC_KITTY_ENABLE_SAAS_SYNC=1` to also exercise sync emit
   during the run.

**Validation**:
- Scenario passes.
- Wall-clock under 5 min.

### T046 — E2E: uninitialized repo fails loud

**Purpose**: Cross-repo proof of FR-032 + FR-039.

**Steps**:

1. In `spec-kitty-end-to-end-testing/scenarios/uninitialized_repo_fail_loud.py`:
   - Create a scratch directory without `.kittify/`.
   - Run each of `spec-kitty specify`, `plan`, `tasks`.
   - Assert each exits non-zero with structured
     `SPEC_KITTY_REPO_NOT_INITIALIZED`.
   - Assert no files are written into a sibling-initialized repo.

**Validation**:
- Scenario passes.
- The "no files written into sibling" assertion uses a snapshot of the
  sibling repo file listing.

### T047 — E2E: SaaS / sync flows under `SPEC_KITTY_ENABLE_SAAS_SYNC=1`

**Purpose**: Cross-repo proof of FR-040.

**Steps**:

1. In `spec-kitty-end-to-end-testing/scenarios/saas_sync_enabled.py`:
   - Drive a full mission (specify → merge) with
     `SPEC_KITTY_ENABLE_SAAS_SYNC=1` and the configured dev SaaS
     endpoint.
   - Assert sync emits land at the SaaS endpoint (or, if endpoint is
     unavailable, the scenario records a structured "endpoint
     unavailable" outcome and the mission-review skill treats it as
     blocked needing operator exception).
2. Document the dev SaaS dependency in
   `docs/migration/cross-repo-e2e-gate.md`.

**Validation**:
- Scenario passes when endpoint is reachable.
- Scenario produces a structured "blocked" outcome with a clear
  message when endpoint is unreachable; does NOT silently pass.

### T048 — E2E: package contract drift caught

**Purpose**: Cross-repo proof of FR-041.

**Steps**:

1. In `spec-kitty-end-to-end-testing/scenarios/contract_drift_caught.py`:
   - Stage a fake `spec-kitty-events` candidate that emits an envelope
     with one missing field.
   - Wire it into the spec-kitty venv (via `pip install -e
     spec-kitty-events`).
   - Run `pytest spec-kitty/tests/contract/`.
   - Assert non-zero exit with the missing-field diagnostic.

**Validation**:
- Scenario passes — non-zero exit with diagnostic.
- Cleanup restores the original `spec-kitty-events` install.

### T049 — ADR-2026-04-26-3: Cross-repo e2e as hard mission-review gate

**Purpose**: Document the gate (DIRECTIVE_003).

**Steps**:

1. Create `architecture/2.x/adr/2026-04-26-3-e2e-hard-gate.md`:
   - Context: package-local CI was insufficient; release gates can
     pass while downstream consumers fail.
   - Decision: cross-repo e2e is a hard gate at mission review.
   - Consequences: missions touching cross-repo behavior must run the
     e2e suite; operator may grant explicit exception when blocked,
     recorded in mission artifacts.
2. Cross-reference from `research.md` D1, the migration doc, and the
   mission-review skill artifact.

**Validation**:
- ADR file exists with required sections.
- Cross-references resolve.

### T050 — Wire mission-review skill to enforce gates

**Purpose**: The skill enforces both contract and e2e gates.

**Steps**:

1. Locate the mission-review skill source path.
   `spec-kitty-mission-review` is shipped under
   `.agents/skills/spec-kitty-mission-review/SKILL.md` and possibly
   replicated under
   `src/specify_cli/missions/*/command-templates/mission-review.md` or
   similar template trees. Update the source location and let the
   normal copy / install pathway propagate.
2. Add to the skill's instructions:
   - Run `pytest spec-kitty/tests/contract/ -v`. Non-zero exit ==
     hard fail.
   - Run `pytest spec-kitty-end-to-end-testing/scenarios/ -v`.
     Non-zero exit == hard fail unless an
     `mission-exception.md` artifact under `kitty-specs/<slug>/`
     records an operator-approved exception.
   - Read `kitty-specs/<slug>/issue-matrix.md` and assert every row
     has a non-empty verdict. Reject if any row is empty or has
     verdict `unknown`.
3. Add `docs/migration/cross-repo-e2e-gate.md` describing the new
   gate, the exception path, and the dev SaaS dependency.

**Validation**:
- Manual review: skill instructions explicitly mention all three
  gates.
- The mission-exception.md path is documented.

## Definition of Done

- `issue-matrix.md` populated with one row per `start-here.md` issue.
- All four e2e scenarios pass against the local workspace (or are
  recorded as blocked with structured outcome and operator
  exception).
- ADR committed and cross-referenced.
- Mission-review skill updated to enforce the gates.
- `docs/migration/cross-repo-e2e-gate.md` exists and describes the
  flow.
- WP08 cannot be marked done until WPs 01..07 are all `done` (the
  finalize-tasks dependency edge enforces this).

## Risks

- T044 risk: matrix rows that say `verified-already-fixed` without a
  regression test that would have failed pre-fix are not actually
  evidence. Reviewer must check that each such row points to a test
  name and that the test exercises the bug surface.
- T047 endpoint-unavailable case must produce a structured outcome,
  not a silent pass. The scenario template includes a default
  `expected_endpoint_health` flag that the test asserts before
  proceeding.
- T050 skill changes propagate via the install / migration system;
  edit the SOURCE path (per CLAUDE.md ⚠️ template-source-location
  warning), not the agent copies.

## Reviewer guidance

1. T044: spot-check 5 random rows in the matrix. For each, follow the
   `evidence_ref` to the test or commit; verify the test exists and
   covers the bug.
2. T045–T048: run each scenario locally (with
   `SPEC_KITTY_ENABLE_SAAS_SYNC=1`) and confirm the green run.
3. T050: read the skill source. The exception path must be explicit;
   "the operator can decide" without a documented artifact path is
   not enough.
4. The ADR must be referenced from at least three places (research,
   migration doc, mission-review skill).

## Activity Log

- 2026-04-26T09:51:18Z – claude:opus-4-7:implementer:implementer – shell_pid=31585 – Started implementation via action command
