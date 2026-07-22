---
work_package_id: WP01
title: Batch-partition primitive (SSOT leaf)
dependencies: []
requirement_refs:
- FR-003
- FR-006
tracker_refs:
- "#2736"
- "#2755"
planning_base_branch: fix/2736-batch-400-poisoning-isolation
merge_target_branch: fix/2736-batch-400-poisoning-isolation
branch_strategy: Planning artifacts for this mission were generated on fix/2736-batch-400-poisoning-isolation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/2736-batch-400-poisoning-isolation unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
phase: Phase 1 - P0 foundation
assignee: ''
agent: "claude"
shell_pid: "1596481"
shell_pid_created_at: "1784429538.95"
history:
- at: '2026-07-19T02:11:31Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/core/
create_intent:
- src/specify_cli/core/batch_partition.py
- tests/core/test_batch_partition.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/core/batch_partition.py
- tests/core/test_batch_partition.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP01 – Batch-partition primitive (SSOT leaf)

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

Land ONE pure, dependency-free primitive module that becomes the single canonical authority for splitting
an ordered batch of events. Two functions, distinct policies:

- `split_in_half(events) -> tuple[list, list]` — the **plain keep-left cut** at `max(1, len(events)//2)`.
  This is the genuinely-shared / #2755-relevant midpoint math (consumed later by BOTH the receiver bisect
  and the legacy 413 shrink).
- `create_aware_midpoint(events, key_of) -> int` — the **create-aware cut**: snap the split index so an
  *adjacent* `wp_id`'s create+status events do not land in different halves. Consumed by the receiver bisect.

**Done when**: `pytest tests/core/test_batch_partition.py` is green; both functions are pure/deterministic/
no-I/O; `split_in_half` returns a non-empty left slice on the singleton edge; `create_aware_midpoint` is
element-generic via an injected `key_of` callable (works on `dict` AND `OutboundEvent`) with NO
event-shape sniffing inside the primitive.

## Context & Constraints

- **Charter**: `.kittify/charter/charter.md` — DIR-044 single canonical authority; ATDD red-first.
- **Plan**: `kitty-specs/sync-batch-400-poison-isolation-01KXW08B/plan.md` (IC-03).
- **Placement is load-bearing (alphonso, post-plan squad)**: the module MUST live at
  `src/specify_cli/core/batch_partition.py` — the neutral leaf both `delivery` and `sync` already import
  downward (both import `core.time_utils`). Do NOT place it in `delivery/`: WP04 makes `sync/batch.py`
  import this primitive, and a `delivery/` home would create a runtime `sync → delivery` cycle that inverts
  the only existing (TYPE_CHECKING-only) `delivery → sync` edge — and the layer-rules gate would NOT catch
  it (both packages sit inside the single `specify_cli` layer).
- **Ordering-agnostic (alphonso + renata)**: the primitive does NOT and cannot guarantee create-before-status
  for a batch-*spanning* pair — no midpoint can. That guarantee is WP02's sequential recursion. Keep this
  module a pure index/partition helper; do not add reorder logic here.

## Branch Strategy

- **Strategy**: per computed lane from `lanes.json`
- **Planning base branch**: `fix/2736-batch-400-poisoning-isolation`
- **Merge target branch**: `fix/2736-batch-400-poisoning-isolation`

> Populated by `spec-kitty agent mission finalize-tasks`. Do NOT change manually.

## Subtasks & Detailed Guidance

### Subtask T001 [P] – Red-first primitive tests

- **Purpose**: Author the failing tests that pin both functions' contracts before implementing.
- **Steps**:
  1. Create `tests/core/test_batch_partition.py`.
  2. `split_in_half`: assert even/odd halving (`[a,b,c,d] → ([a,b],[c,d])`, `[a,b,c] → ([a],[b,c])`), and
     the **singleton edge**: `split_in_half([x]) == ([x], [])` (non-empty left — proves totality + progress;
     note the recursion's *termination* is guaranteed by WP02 T009's `len==1` base case, not by this test).
  3. `create_aware_midpoint`: build a list where index `k` is a `create` and `k+1` is its matching `status`
     (same key via `key_of`); assert the returned midpoint does NOT fall between them when the naive
     `len//2` would (snaps left or right by one).
  4. Purity: same input → same output; no mutation of the input list; no I/O.
- **Files**: `tests/core/test_batch_partition.py`.
- **Notes**: Mark red-first work `@pytest.mark.regression` only if it must be committed red across a WP
  boundary; here impl lands in the same WP, so a normal red→green cycle is fine.

### Subtask T002 – Implement `split_in_half`

- **Purpose**: The plain keep-left midpoint math — the SSOT `//2` cut.
- **Steps**: `mid = max(1, len(events) // 2); return list(events[:mid]), list(events[mid:])`. Guarantee a
  non-empty left slice so the recursion's singleton base case always terminates.
- **Files**: `src/specify_cli/core/batch_partition.py`.

### Subtask T003 – Implement `create_aware_midpoint(events, key_of)`

- **Purpose**: The create-aware cut that keeps an adjacent same-key pair on one side of the split.
- **Steps**: **Pure key-adjacency only (paula — no role-sniffing).** Start from the naive midpoint; if the
  two events straddling the cut share the same `key_of(...)`, nudge the boundary by one to keep that key's
  pair together (prefer the direction that keeps both slices non-empty). Return the index. **Do NOT try to
  decide which straddling event is the "create" vs the "status"** — that would require the primitive to sniff
  event roles/shape, contradicting T004's shape-blind contract (`key_of` is the only injected policy). The
  create-before-status ORDERING is WP02's sequential recursion, not this function. Ordering-agnostic: returns
  an index, never reorders.
- **Files**: `src/specify_cli/core/batch_partition.py`.

### Subtask T004 – Confirm element-generic via injected `key_of`

- **Purpose**: One primitive for both consumers without a bounded-context leak.
- **Steps**: `key_of` is a REQUIRED `Callable[[T], Hashable]`. In a test, drive it once with `dict` events
  keyed at `aggregate_id` and once with a stand-in keyed inside `payload` — the primitive branches on
  neither shape. Do NOT sniff the wp_id shape inside the module.
- **Files**: `tests/core/test_batch_partition.py`.

## Test Strategy

- `pytest tests/core/test_batch_partition.py` — must be green at WP close.
- Keep the module import-light so the layer stays a leaf (`ruff`/`mypy` clean, zero new suppressions).
- **Pre-review-gate blind spot (debbie/F9)**: `tests/core/**` + `src/specify_cli/core/**` land only in CI's
  excluded `core_misc` catch-all, so the automated pre-review gate reports `no_coverage — excluded scope` —
  **that is NOT a pass.** Run `PWHEADLESS=1 pytest tests/core/ -q` manually and rely on CI
  `integration-tests-core-misc`.

## Risks & Mitigations

- **Bounded-context leak** → keep `key_of` injected; never branch on event type inside the primitive.
- **Wrong home** → `core/`, not `delivery/` (see Context). This is the single most important placement call.

## Review Guidance

- Confirm the module imports nothing from `delivery`/`sync` (leaf).
- Confirm `split_in_half` singleton edge and `create_aware_midpoint` ordering-agnosticism are both tested.

## Activity Log

- 2026-07-19T02:11:31Z – system – Prompt created.
- 2026-07-19T02:52:37Z – claude – shell_pid=1596481 – Assigned agent via action command
- 2026-07-19T03:00:04Z – claude – shell_pid=1596481 – Moved to for_review
- 2026-07-19T03:04:00Z – user – shell_pid=1596481 – Approved: 14 tests green (reviewer re-ran; gate blind to core/ per F9), pure core/ leaf, key-adjacency no role-sniffing, non-tautological assertions, ruff+mypy clean. 2 non-blocking cross-WP nits.
