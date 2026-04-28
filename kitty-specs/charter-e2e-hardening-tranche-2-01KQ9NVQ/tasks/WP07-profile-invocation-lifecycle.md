---
work_package_id: WP07
title: Profile-Invocation Lifecycle (#843)
dependencies:
- WP01
requirement_refs:
- FR-007
planning_base_branch: fix/charter-e2e-827-tranche-2
merge_target_branch: fix/charter-e2e-827-tranche-2
branch_strategy: Planning artifacts for this feature were generated on fix/charter-e2e-827-tranche-2. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/charter-e2e-827-tranche-2 unless the human explicitly redirects the landing branch.
subtasks:
- T030
- T031
- T032
- T033
agent: "claude:sonnet:implementer-ivan:implementer"
shell_pid: "202"
history:
- at: '2026-04-28T09:36:40Z'
  actor: spec-kitty.tasks
  event: created
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/invocation/
execution_mode: code_change
mission_slug: charter-e2e-hardening-tranche-2-01KQ9NVQ
model: claude-sonnet-4-6
owned_files:
- src/specify_cli/mission_step_contracts/**
- src/specify_cli/invocation/**
- tests/specify_cli/mission_step_contracts/**
- tests/specify_cli/invocation/**
- tests/integration/test_profile_invocation_lifecycle*.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Run `/ad-hoc-profile-load implementer-ivan` before reading further.

## Objective

When `spec-kitty next` issues or advances a composed action, write paired `started` and `completed` lifecycle records under `.kittify/events/profile-invocations/` whose `action` matches the issued step and whose `outcome` is in the canonical vocabulary (`done`, `failed`, `skipped`, `blocked`). Today, this directory is populated for WP-bound implement/review actions but skipped for composed actions issued by `next` outside the implement-review loop.

Closes (with strict E2E gate): `#843`. Satisfies: `FR-007`, `NFR-006`.

## Context

- **Spec FR-007**: paired records exist with action identity match and canonical outcome.
- **Contract**: `contracts/next-advance.json` `x-on-disk-lifecycle`.
- **Research R5** (`research.md`): file:line refs for executor and invocation pipeline; canonical record schema; reason composed actions are skipped today.
- **Brief**: `start-here.md` "Issued actions must write paired profile-invocation lifecycle records" section.
- **Existing files**:
  - `src/specify_cli/mission_step_contracts/executor.py`
  - `src/specify_cli/invocation/{executor,writer,record,propagator,router,registry}.py`
  - `tests/integration/test_documentation_runtime_walk.py` (existing trail-record assertion pattern)
  - `tests/integration/test_research_runtime_walk.py`

## Branch Strategy

- Mission planning/base branch: `fix/charter-e2e-827-tranche-2`
- Mission merge target: `fix/charter-e2e-827-tranche-2`
- Execution worktree: assigned by `finalize-tasks`. Enter via `spec-kitty agent action implement WP07 --agent <name>`.

## Subtasks

### T030 — Extend lifecycle writer to cover composed actions

**Purpose**: Make composed actions issued by `next` go through the same lifecycle-write path as WP-bound actions.

**Steps**:
1. Read research R5 for the canonical write call site (likely `src/specify_cli/invocation/writer.py` or `mission_step_contracts/executor.py`).
2. Identify the conditional that skips composed actions today (kind check, lane check, or feature flag).
3. Extend the path so composed actions issued by `next` also write the `started` record at issue time and the `completed` record at advance time.
4. Reuse the existing record schema from `src/specify_cli/invocation/record.py`. **Do not redefine** the schema — that would risk corrupting existing readers (e.g., status reducer per issue #847).

**Files**: `src/specify_cli/mission_step_contracts/executor.py`, `src/specify_cli/invocation/writer.py`, possibly `src/specify_cli/next/runtime_bridge.py` to wire the call site.

### T031 — Ensure outcome field uses canonical vocabulary

**Purpose**: Lock the `outcome` field on `completed` records to `done` / `failed` / `skipped` / `blocked`.

**Steps**:
1. Confirm the canonical vocabulary in `src/specify_cli/invocation/record.py` (or wherever the enum/Literal lives).
2. Map `next --result <value>` to the corresponding outcome:
   - `--result success` → `done`
   - `--result failed` → `failed`
   - other public values → corresponding canonical outcomes per existing convention
3. Validate before writing: refuse to write a `completed` record whose `outcome` is outside the vocabulary (raise a typed error).

### T032 — Add integration test asserting paired records

**Purpose**: Lock FR-007 with regression coverage.

**Steps**:
1. Add `tests/integration/test_profile_invocation_lifecycle.py` (or extend an existing runtime-walk test) that:
   - Sets up a fresh project with a composed mission step.
   - Invokes `next --json` to issue an action; parses stdout strictly.
   - Asserts `.kittify/events/profile-invocations/` exists and contains a `started` record whose `action` matches the issued step.
   - Invokes `next --result success --json` to advance.
   - Asserts a `completed` record exists, paired with the `started`, with `outcome == "done"`.
2. Use the existing trail-record assertion pattern from `test_documentation_runtime_walk.py` / `test_research_runtime_walk.py` so the test reads consistent with the codebase.

### T033 — Verify documentation/research runtime walks regression-free

**Steps**:
1. Run `uv run pytest tests/integration/test_documentation_runtime_walk.py tests/integration/test_research_runtime_walk.py tests/specify_cli/mission_step_contracts tests/specify_cli/invocation -q`. Must exit 0.
2. Run `uv run mypy --strict src/specify_cli` and `uv run ruff check src tests`.

## Test Strategy

- **Per-fix regression coverage**: T032 (NFR-006).
- **Targeted gates**: `tests/integration/`, `tests/specify_cli/mission_step_contracts/`, `tests/specify_cli/invocation/`.

## Definition of Done

- [ ] Composed actions issued by `next` write paired `started`/`completed` records.
- [ ] Action identity matches issued step.
- [ ] Outcome in canonical vocabulary.
- [ ] T032 test passes; fails without fixes.
- [ ] Existing runtime-walk tests still pass.
- [ ] `mypy --strict` passes; ruff passes.
- [ ] Owned files only.

## Risks

- **Status reducer corruption** (issue #847 deferred): adding records to `.kittify/events/profile-invocations/` should not affect `status.events.jsonl`. Confirm by reading the reducer entry path. If the lifecycle writer reuses status-event infrastructure, isolate the write paths.
- **Existing trail records duplicated**: ensure WP-bound actions don't get *two* records (one from the existing path + one from the new). Test by walking an implement action through the existing `tests/integration/`.
- **Outcome vocabulary expansion**: if the existing vocabulary is narrower than the contract's `done|failed|skipped|blocked`, expand it carefully and update consumers.

## Reviewer Guidance

- Confirm composed actions write paired records (run `next` against a fixture and inspect `.kittify/events/profile-invocations/`).
- Confirm WP-bound actions still write exactly one paired record (no duplication).
- Confirm record schema is unchanged from existing readers' expectations.

## Implementation command

```bash
spec-kitty agent action implement WP07 --agent <your-agent-key>
```

## Activity Log

- 2026-04-28T11:24:55Z – claude:sonnet:implementer-ivan:implementer – shell_pid=202 – Started implementation via action command
- 2026-04-28T13:26:34Z – claude:sonnet:implementer-ivan:implementer – shell_pid=202 – Composed actions issued by next now write paired started/completed lifecycle records with canonical outcome (done|failed|abandoned); integration test added; existing runtime walks regression-free
