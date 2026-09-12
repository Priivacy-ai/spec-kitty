---
work_package_id: WP01
title: '#3320 — retrospect --update reports/emits the persisted record'
dependencies: []
requirement_refs:
- FR-001
- FR-002
planning_base_branch: fix/mission-a-p0-consistency
merge_target_branch: fix/mission-a-p0-consistency
branch_strategy: Planning artifacts for this mission were generated on fix/mission-a-p0-consistency. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/mission-a-p0-consistency unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-mission-a-p0-consistency-01KZWHY1
base_commit: c7011382fc5f183430603d0dea85232fe8189cd0
created_at: '2026-08-13T04:24:47.286362+00:00'
subtasks:
- T001
- T002
- T003
- T004
history:
- Created by /spec-kitty.tasks for mission-a-p0-consistency-01KZWHY1
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/retrospect.py
create_intent:
- tests/cli/commands/test_retrospect_update_persisted.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/retrospect.py
- tests/cli/commands/test_retrospect_update_persisted.py
- tests/regression/test_issue_3320_retrospect_update_reports_stale_findings.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned profile: run `/ad-hoc-profile-load python-pedro`
(or `spec-kitty agent profile show python-pedro`) and apply its initialization, boundaries,
directives, and tactics. You are an **implementer** — TDD/red-first, type-safe, idiomatic Python.

## Objective

`spec-kitty retrospect create --update` currently reports `counts`/`findings_status`
and emits the `RetrospectiveCaptured` event from the **pre-merge** generated record,
while `write_gen_record(mode="update")` merges with the on-disk record and returns
only a `Path`. Make the CLI report and emit from the **merged persisted record**.

## Context (root cause — verified against `main`)

- `src/specify_cli/cli/commands/retrospect.py::create_cmd`: `write_gen_record(record, mode=write_mode, ...)` (~:375) returns a `Path`; the CLI then builds `counts` (~:423), the JSON `findings_status` (~:442), and calls `emit_captured(record, ...)` (~:405) — all from the **pre-merge** `record`.
- `src/specify_cli/retrospective/writer.py::write_gen_record` merges on disk (`_merge_gen_records` recomputes `findings_status` from the union) but returns only the `Path`.
- Read-back reader already exists: `src/specify_cli/retrospective/reader.py::read_gen_record(path)` (~:329).

## Constraints

- **C-002**: do NOT change `write_gen_record`'s `Path` return type (≈4 callers + ~30 test assertions + mocks return `Path`). Read the record back via `read_gen_record(record_path)`.
- Read-back is a **no-op** for `--overwrite`/`mode="error"`/backfill (persisted == new) — only `--update` diverges. Do not special-case; reading back is uniformly correct.

## Subtasks

### T001 — Report and emit from the persisted record

In `create_cmd`, after `record_path = write_gen_record(...)` succeeds, read the
persisted record: `persisted = read_gen_record(record_path)`. Build the `counts`
dict, the JSON `findings_status`, **and** the `emit_captured(...)` argument from
`persisted`, not `record`. Keep the pre-merge `record` only where genuinely needed
(e.g. provenance already written). Verify `read_gen_record` returns the same
`GenRetrospectiveRecord` shape the counts/emit code expects.

### T002 — On-disk emit-spy guard test [P]

Add `tests/cli/commands/test_retrospect_update_persisted.py`. Seed a `has_findings`
record with one gap via the real writer; invoke `create --update --json` with a
stubbed `ran_no_findings` generator and the **real** `write_gen_record` (not mocked).
Patch `emit_captured` with a **spy** (not `→None`). Assert the spy's captured event
`findings_status`/gap-count equal the values **read back from `record_path` on disk**
(`has_findings`/`1`) — independent of the reported JSON (both could be wrong-and-equal).
Also assert the reported JSON matches disk.

### T003 — Relocate the repro; canonicalize (NFR-005)

Move `tests/regression/test_issue_3320_retrospect_update_reports_stale_findings.py`
into `tests/cli/commands/` (fold its assertion into the new file or keep as a sibling
guard). Drop `@pytest.mark.regression`; add the canonical marks for this suite from
`docs/context/testing-taxonomy.md` (e.g. `integration` + `git_repo`, or `unit` +
`fast` — match siblings). Replace the red-first docstring with a permanent guard
docstring: state the defect (#3320) is fixed and this pins report≡event≡disk.

### T004 — Gates

`ruff check .` and `mypy` clean on changed files. Run the targeted suite:
`PWHEADLESS=1 .venv/bin/python -m pytest tests/cli/commands/ -q -k "retrospect"`.
Confirm no `regression`-marked #3320 test remains green:
`pytest tests/ -m regression -k 3320` selects nothing.

## Branch Strategy

Planning base + merge target: `fix/mission-a-p0-consistency`. Execution worktree is
allocated per computed lane from `lanes.json` (do not reconstruct the path). Implement
via `spec-kitty agent action implement WP01 --agent claude`.

## Definition of Done

- [ ] `create --update` reports counts/`findings_status` from the persisted record.
- [ ] `emit_captured` receives the persisted record (event ≡ disk).
- [ ] Emit-spy guard test asserts against on-disk values (T002).
- [ ] #3320 repro relocated to `tests/cli/commands/`, marker dropped, canonical marks + guard docstring (T003).
- [ ] `ruff`/`mypy` clean; targeted retrospect suite green; no green `regression`-marked #3320 test.

## Risks / Reviewer guidance

- The **event** payload is the easy miss — verify `emit_captured` was re-pointed, not just the JSON. Reviewer: confirm the guard test uses a spy against disk, not the reported JSON.
- Confirm `--overwrite`/`error`/backfill behavior is unchanged (read-back is a no-op there).
