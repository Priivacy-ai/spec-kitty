---
work_package_id: WP05
title: '#2755 SSOT retrofit + single-authority guard'
dependencies:
- WP01
- WP04
requirement_refs:
- FR-006
tracker_refs:
- '#2755'
planning_base_branch: fix/2736-batch-400-poisoning-isolation
merge_target_branch: fix/2736-batch-400-poisoning-isolation
branch_strategy: Planning artifacts for this mission were generated on fix/2736-batch-400-poisoning-isolation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/2736-batch-400-poisoning-isolation unless the human explicitly redirects the landing branch.
subtasks:
- T017
- T018
- T019
- T020
phase: Phase 3 - release-optional retrofit
assignee: ''
agent: "claude"
shell_pid: "1721789"
shell_pid_created_at: "1784431319.17"
history:
- at: '2026-07-19T02:11:31Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/architectural/
create_intent:
- tests/architectural/test_batch_split_single_authority.py
execution_mode: code_change
model: ''
owned_files:
- tests/architectural/test_batch_split_single_authority.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP05 – #2755 SSOT retrofit + single-authority guard

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave
according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

---

## Markdown Formatting

Wrap HTML/XML tags in backticks. Use language identifiers in code blocks.

---

## Objectives & Success Criteria

Close **#2755** by making `_shrink_events_for_retry` (the legacy 413 byte-shrink) consume the shared SSOT
`split_in_half` instead of its own inline `//2`, guarded so no future splitter re-derives the midpoint.

**Behavior-preserving by construction** (renata): `split_in_half(events)[0]` is textually equal to the
inline `events[:max(1, len(events)//2)]`, so the six merged #2735 tests MUST stay green with **no shift** —
any red is a mechanical bug to FIX, not "friction" to defer.

**Done when**: the behavioral-delegation guard (T017) passes; the AST guard (T018) passes with the correct
allowlist; `_shrink_events_for_retry` delegates to `split_in_half`; the six #2735 tests stay green.

**Release-optional** — off the P0 gate (nothing in WP01/WP02 depends on this).

## Context & Constraints

- **Plan**: IC-06. **Spec**: FR-006, SC-004.
- **Consumes WP01**: `from specify_cli.core.batch_partition import split_in_half`. The 413 shrink uses the
  **PLAIN** `split_in_half` — NOT `create_aware_midpoint` (byte-sizing must not inherit create-aware snapping).
- **Ownership**: this WP owns ONLY `tests/architectural/test_batch_split_single_authority.py`. The one-line
  rewire of `_shrink_events_for_retry` lives in `sync/batch.py` (owned by WP04) — make it as a **declared
  out-of-map edit**, recorded with a one-line rationale, sequenced AFTER WP04 (hence `dependencies:
  [WP01, WP04]`) so there is no same-file race.
- **Guard hierarchy**: T017 (behavioral spy) is the LOAD-BEARING, non-fakeable guard. T018 (AST) is
  belt-and-suspenders.
- **Pre-review-gate blind spot (debbie/F9)**: `tests/architectural/**` lands only in CI's excluded
  `core_misc` catch-all, so the automated pre-review gate returns `no_coverage — excluded scope` — **that is
  NOT a pass.** Run `PWHEADLESS=1 pytest tests/architectural/ -q` manually and rely on CI
  `integration-tests-core-misc`.

## Branch Strategy

- **Strategy**: per computed lane from `lanes.json`
- **Planning base branch**: `fix/2736-batch-400-poisoning-isolation`
- **Merge target branch**: `fix/2736-batch-400-poisoning-isolation`

## Subtasks & Detailed Guidance

### Subtask T017 [red] – Behavioral-delegation guard (LOAD-BEARING)

- **Purpose**: Prove `_shrink_events_for_retry` delegates to the SSOT, not a re-derived `//2` — robustly,
  independent of source spelling.
- **Steps**: New `tests/architectural/test_batch_split_single_authority.py`. Spy/patch the REAL
  `core.batch_partition.split_in_half` and assert `_shrink_events_for_retry` invokes it (call-count ≥ 1 for a
  `len>1` batch). This is behavioral delegation — NOT a source-count/grep. RED until T019.
- **Files**: `tests/architectural/test_batch_split_single_authority.py`.

### Subtask T018 [red] – AST single-authority guard (belt-and-suspenders, allowlisted)

- **Purpose**: Best-effort catch of a re-derived events-midpoint anywhere in `src/`.
- **Steps**: In the same file, AST-walk `src/specify_cli/` for a `BinOp` FloorDiv-by-2 whose left operand is
  a `len()` call over the function's batch/events parameter. **MUST allowlist `core/batch_partition.py`
  (the SSOT itself) AND `doc_analysis/gap_analysis.py:392`** (a live, unrelated `len(project_areas)//2` —
  paula/debbie), or scope the walk to the `events`/`batch` identifier / to `sync/` + `delivery/` modules.
  `cli/commands/sync.py:807` (`limit//2`) is not `len()`-based and is correctly out of scope. Keep the
  red-first proof that the matcher fires on `sync/batch.py:392` before T019. Belt-and-suspenders — T017 is
  the real guard.
- **Files**: `tests/architectural/test_batch_split_single_authority.py`.

### Subtask T019 – Rewire `_shrink_events_for_retry` (out-of-map)

- **Purpose**: Close #2755 via the shared mechanism.
- **Steps**: In `sync/batch.py:392`, replace `events[:max(1, len(events)//2)]` with
  `split_in_half(events)[0]` (keep the keep-left-drop-rest policy — the right half is dropped). This is an
  **out-of-map edit** in a WP04-owned file: record a one-line rationale ("#2755 SSOT retrofit, sequenced
  after WP04"). Run the six #2735 pinning tests (`test_batch_sync_shrinks_...`, `..._retries_smaller_batch...`,
  `..._single_oversized...`, `..._server_413_on_single_event...`, `test_sync_all_continues_past_oversized_event`,
  plus the body-upload tests) — all stay green with NO shift (behavior-identical).
- **Files**: `src/specify_cli/sync/batch.py` (out-of-map).

### Subtask T020 – Confirm #2755 closed (blocker-only hatch)

- **Purpose**: Verify closure; keep the escape hatch honest.
- **Steps**: Confirm T017/T018 pass and #2755 is closed. **The rewire is behavior-preserving by construction,
  so any #2735 red is a mechanical bug in YOUR rewire — FIX IT.** The escape hatch (defer T019) applies ONLY
  to a genuine architectural blocker (e.g. an unbreakable import cycle), which MUST be recorded in the mission
  tracer `design-decisions.md` with the specific failure and needs operator sign-off — NEVER invoked on a
  self-inflicted test red.
- **Files**: (verification/record only).

## Test Strategy

- `PWHEADLESS=1 pytest tests/architectural/ tests/sync/ -q` green at close (plus the #2735 body-upload tests).
- Run T017/T018 RED first (before T019) to prove they detect a non-delegating implementation.
- Remember the pre-review gate is blind to `tests/architectural/**` — the manual run + CI is the real gate.

## Risks & Mitigations

- **Behavior-identical rewire** → near-zero semantic risk; residual is a mechanical fumble (import cycle,
  off-by-one) that T017 + the #2735 tests catch. Not deferrable on a self-inflicted red.
- **AST guard false-positive** on `gap_analysis.py:392` → the allowlist (T018) is mandatory before authoring.

## Review Guidance

- Confirm the shrink uses PLAIN `split_in_half`, never `create_aware_midpoint`.
- Confirm T017 (behavioral) is present and load-bearing; T018 allowlists the two known `len//2` sites.
- Confirm the six #2735 tests are green with no shift.

## Activity Log

- 2026-07-19T02:11:31Z – system – Prompt created.
- 2026-07-19T03:22:18Z – claude – shell_pid=1721789 – Assigned agent via action command
