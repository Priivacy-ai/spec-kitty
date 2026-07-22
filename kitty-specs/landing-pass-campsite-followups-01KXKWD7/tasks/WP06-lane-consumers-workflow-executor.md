---
work_package_id: WP06
title: Lane consumer behavior + workflow_executor type-clears (#2675)
dependencies: ["WP05"]
requirement_refs:
- C-001
- FR-010
- NFR-003
- NFR-004
- NFR-005
tracker_refs: []
planning_base_branch: feat/landing-pass-campsite-followups
merge_target_branch: feat/landing-pass-campsite-followups
branch_strategy: Planning artifacts for this mission were generated on feat/landing-pass-campsite-followups. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/landing-pass-campsite-followups unless the human explicitly redirects the landing branch.
subtasks:
- T050
- T051
- T052
- T053
- T054
- T055
phase: Phase 2 - Lane consumers
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "3863044"
shell_pid_created_at: "1784161725.33"
history:
- at: '2026-07-15T22:32:40Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/agent/workflow_executor.py
create_intent:
- tests/specify_cli/test_lane_consumer_behavior.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/merge/done_bookkeeping.py
- src/specify_cli/core/worktree_topology.py
- src/specify_cli/status/aggregate.py
- src/specify_cli/coordination/status_transition.py
- src/specify_cli/workspace/context.py
- src/specify_cli/cli/commands/agent/workflow_executor.py
- src/specify_cli/dashboard/scanner.py
- tests/specify_cli/test_lane_consumer_behavior.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP06 – Lane consumer behavior + workflow_executor type-clears (#2675)

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## ⚠️ IMPORTANT: Review Feedback

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_ref` field in the event log (via `spec-kitty agent status` or the Activity Log below).
- **You must address all feedback** before your work is complete. Feedback items are your implementation TODO list.
- **Report progress**: As you address each feedback item, update the Activity Log explaining what you changed.

---

## Review Feedback

*[If this WP was returned from review, the reviewer feedback reference appears in the Activity Log below or in the status event log.]*

---

## Markdown Formatting

Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`,````bash`

---

## Objectives & Success Criteria

Update the behavioral consumers of the `Lane` sentinel so they remain correct once
WP05's loader returns the real `Lane.UNINITIALIZED` StrEnum member (value
`"uninitialized"`), and clear the remaining `mypy` errors in
`src/specify_cli/cli/commands/agent/workflow_executor.py`. This is the mission's
heaviest WP because it braids two hazards that a compiler cannot see: a
**type-invisible behavior regression** across the sentinel consumers, and a set of
`workflow_executor.py` type clusters that must all land in ONE lane so no parallel
lane collides on the same 1855-LOC file.

**This WP is complete when:**

- A new behavior test file, `tests/specify_cli/test_lane_consumer_behavior.py`,
  pins the **sites that actually flip after WP05** — `done_bookkeeping` site-1's
  force-done flag must stay `False` (tuple `(coord_lane, False)`, not `True`) for an
  unseeded WP, and `coordination/status_transition.py:557`'s unseeded read must still
  return `Lane.GENESIS` (not `Lane.UNINITIALIZED`) — plus the secondary
  characterization that an unseeded WP maps to `"planned"` via `worktree_topology` and
  is **NOT done** via `done_bookkeeping` site-2. Those tests were written RED first
  (C-005).
- `done_bookkeeping.py` preserves both sentinel contracts **explicitly**: site-1 keeps
  returning `(coord_lane, False)` (force-done stays `False`) and site-2 keeps treating
  the unseeded sentinel as not-done; the now-dead `except ValueError` branches no
  longer carry the semantics silently.
- `worktree_topology.py` and `aggregate.py` compare `Lane.UNINITIALIZED` for clarity,
  with behavior preserved; `coordination/status_transition.py:557` keeps its
  GENESIS-fallback contract explicit now that its `except` (which fired when
  `Lane("uninitialized")` raised) has gone dead.
- `workspace/context.py` no longer trips a `dict[str, Lane]` annotation ripple
  (the `str` default / `str()`-comparison sites).
- `workflow_executor.py` clears ALL three of its #2675 type clusters
  (`str → Lane`, `no-any-return`, `Optional` narrowings) with **zero new
  suppressions** and **no refactor/extraction** beyond the single justified typed
  wrapper.
- `coordination/status_transition.py` narrows the `StatusEvent | None` param before
  its `StatusEvent`-typed use.
- `uv run mypy` reports **0 errors and 0 new suppressions** across every WP06
  surface; the full behavior suite is green.

**Success metric:** `uv run pytest tests/specify_cli/test_lane_consumer_behavior.py -q`
green, `uv run mypy` clean on all WP06 surfaces, and
`uv run python -c "import specify_cli.status.transitions"` still succeeds.

## Context & Constraints

**Part of #2675 (full `Lane` sentinel unification).** This WP consumes the
`Lane.UNINITIALIZED` member introduced by **WP05** — do not start behavioral edits
until WP05's loader change is on your base. See `dependencies: ["WP05"]` in the
frontmatter (written by `finalize-tasks`); the WP05 loader is the precondition for
the `str → Lane` clears in `workflow_executor.py`.

**Binding constraints:**

- **RED-FIRST (C-005):** the T050 behavior tests MUST be written and observed
  failing (or at least exercising the pre-change contract) before the consumer
  edits land. The regression this WP guards is **TYPE-INVISIBLE** — every consumer
  already `str(...)`-coerces the lane, so `mypy` will NOT catch a behavior change.
  Behavior tests are mandatory, not optional.
- **FIX-NOT-SUPPRESS (C-001):** no blanket `# type: ignore`, `# noqa`, or per-file
  ignore additions. The only sanctioned cast in this WP is the single, justified
  `_locate_wp` typed wrapper described in T054.
- **Canonical sources:** work from the resolver/loader seam WP05 established; do not
  reconstruct sentinel semantics from an older mission.

**Verified code facts (read these before editing):**

1. **`done_bookkeeping.py` (~:151-160 and ~:375-378).** Builds
   `_Lane(_resolve_lane_alias("uninitialized"))` and, further down,
   `Lane(resolve_lane_alias(raw))` inside a `try/except ValueError` whose comment
   reads "Unknown sentinels such as 'uninitialized' … treat as not done." Once WP05
   makes `UNINITIALIZED` a real member, `Lane("uninitialized")` **succeeds** — the
   `ValueError` is never raised, so that `except` branch goes **DEAD**. The
   "treat as not done" semantics must be re-expressed **explicitly** against
   `Lane.UNINITIALIZED`, not left riding on a branch that can no longer fire.

2. **`worktree_topology.py:81`.** `if lane == LEGACY_UNINITIALIZED_SENTINEL: return "planned"`
   still matches via StrEnum equality (the member's value is `"uninitialized"`), so
   behavior holds. Update the comparison to `Lane.UNINITIALIZED` for clarity and
   keep the `"planned"` mapping exactly.

3. **`aggregate.py:691`** consumes the sentinel via equality; update to compare
   `Lane.UNINITIALIZED`, preserving behavior.

3b. **`coordination/status_transition.py:557-574` is NOT an equality comparison.** It
   reads:
   ```python
   try:
       return Lane(resolve_lane_alias(get_wp_lane(identity.feature_dir, wp_id))), None
   except (ValueError, FileNotFoundError, CanonicalStatusNotFoundError):
       return Lane.GENESIS, None
   ```
   TODAY an unseeded WP → `get_wp_lane` returns `"uninitialized"` →
   `Lane("uninitialized")` **raises `ValueError`** → the `except` fires → returns
   `Lane.GENESIS`. After WP05, `get_wp_lane` returns `Lane.UNINITIALIZED` →
   `Lane("uninitialized")` **succeeds** → the `except` never fires → the function
   returns `Lane.UNINITIALIZED` instead of `Lane.GENESIS`. This flip is
   **type-invisible, mypy-clean, and currently untested**. Preserve the
   GENESIS-fallback contract **explicitly** — map/return `Lane.GENESIS` for the
   unseeded (`Lane.UNINITIALIZED`) read at this site, per the existing FR-008d/R7
   contract comment.

4. **`workspace/context.py:501,513`.** `:513` uses `.get(wp_id, "uninitialized")` (a
   `str` default) and `:501` uses `str(lanes_by_wp.get(wp_id)) == Lane.IN_PROGRESS.value`.
   WP05's change of `get_all_wp_lanes` to return `dict[str, Lane]` surfaces the **NEW**
   `mypy` diagnostic at the `:513` `str` default supplied to a `dict[str, Lane]`
   `.get(...)`. Resolve it cleanly — align the default and the comparison with the
   `Lane`-typed dict.

5. **`dashboard/scanner.py:623,633,914-918`.** Already defensive — accepts
   `{Lane.GENESIS, "genesis", "uninitialized"}`. **Verify** it is still correct
   after WP05; the expectation is **no change**. If a change is genuinely required,
   keep it minimal and note the reasoning in the Activity Log.

6. **`workflow_executor.py` — the three #2675 clusters** (file is 1855 LOC; do NOT
   extract or refactor beyond the type fixes — this is a recorded **no-extract**
   call):
   - **`str → Lane`** diagnostics at ~807 / ~816 / ~837 / ~1232. These clear once
     WP05's loader returns pure `Lane`. The two assignment sites feeding them are
     ~770 and ~1209 (via `get_wp_lane`). Verify the clears; only coerce at those two
     assignment sites if a diagnostic genuinely survives.
   - **`no-any-return`** at ~428 / ~1372. `_wf().locate_work_package(...)` leaks
     `Any` through `ModuleType`. Add **ONE** typed wrapper and route both erroring
     sites plus the two non-erroring `locate_work_package` assignments (~831 and
     ~1194, structurally identical) through it:
     ```python
     def _locate_wp(...) -> WorkPackage:
         return cast(WorkPackage, _wf().locate_work_package(...))
     ```
     This single, justified `cast` is the only sanctioned cast in the WP.
   - **`Optional` narrowings** at ~668 (`set_scalar(..., agent)` where `agent` is
     validated non-`None` at ~781) and ~873 (`ReviewCycleArtifact | None`). Narrow
     with a guard/assert against the real invariant — never a blanket cast.

7. **`coordination/status_transition.py` — `StatusEvent | None` narrowing.** The
   plan's earlier reference to `status/status_transition.py:854` was **WRONG**; the
   real file is `coordination/status_transition.py`, and the `event: StatusEvent | None`
   parameter is at ~:763. Add the `None` guard/narrowing before the
   `StatusEvent`-typed use — assert or guard on a real invariant, not a blanket cast.

**Supporting documents:** `research-notes-csf-2670.md`, plan **IC-05**,
`data-model.md` **LN-1**.

## Branch Strategy

- **Strategy**: {{branch_strategy}}
- **Planning base branch**: {{planning_base_branch}}
- **Merge target branch**: {{merge_target_branch}}

> These fields are populated automatically by `spec-kitty agent mission tasks`.
> Do NOT change them manually unless you are certain the branch topology has changed.
>
> **Dependency note:** this WP declares `dependencies: ["WP05"]` (written into the
> frontmatter by `finalize-tasks`). WP05 introduces `Lane.UNINITIALIZED` and the
> loader change that makes `workflow_executor.py`'s `str → Lane` clears possible. Do
> not begin behavioral edits until WP05 is on your base branch.

## Subtasks & Detailed Guidance

### Subtask T050 – RED behavior tests for the sites that flip after WP05

- **Purpose**: Pin the TYPE-INVISIBLE regression at the sites that **actually change
  behavior** once WP05 makes `Lane("uninitialized")` succeed. Because every consumer
  `str(...)`-coerces the lane, `mypy` cannot see the change; only behavior tests can.
  Write these RED first (C-005).
- **Primary targets (these flip after WP05 — the red-first spine):**
  1. **`done_bookkeeping` site-1 (~:151-160).** Today the `except` returns
     `(coord_lane, False)`; after WP05 the `try` returns `(Lane.UNINITIALIZED, True)`,
     which flips the force-done flag `False → True`. Assert the PRESERVED contract:
     the unseeded read still yields force-done **`False`** (tuple `(coord_lane, False)`).
  2. **`coordination/status_transition.py:557`.** Today an unseeded WP returns
     `Lane.GENESIS` (the `except` fires because `Lane("uninitialized")` raises); after
     WP05 the `try` succeeds and it would return `Lane.UNINITIALIZED`. Assert the
     PRESERVED contract: the unseeded read still returns **`Lane.GENESIS`**.
  These two assertions pass today but would break the moment WP05 lands without the
  consumer being updated — i.e. they genuinely guard the regression WP05 introduces
  (red-first, not vacuous characterization).
- **Secondary characterization (already correct today AND after WP05 — NOT the
  red-first spine):**
  3. A WP **absent from the status snapshot** maps to `"planned"` through
     `worktree_topology` (unseeded → planned).
  4. The same unseeded WP is treated as **NOT done** by `done_bookkeeping` site-2
     (~:375) — `Lane.UNINITIALIZED` still `!=` `Lane.DONE`, so this never flips.
- **Steps**:
  1. Create `tests/specify_cli/test_lane_consumer_behavior.py`.
  2. Cover the two primary (flipping) targets above, asserting the preserved
     contracts (force-done `False`; returns `Lane.GENESIS`). Construct or stub the
     snapshot so the WP resolves to `Lane.UNINITIALIZED` (or is missing).
  3. Cover the two secondary characterization targets.
  4. Prefer real, production-shaped WP IDs and snapshot shapes over toy
     placeholders so the tests exercise the true path.
  5. Run the file and confirm the tests describe the intended contract before the
     consumer edits (RED-first discipline).
- **Files**: `tests/specify_cli/test_lane_consumer_behavior.py` (create).
- **Parallel?**: No — this is the guard the rest of the WP must satisfy.
- **Notes**: The primary targets are the exact regressions that would slip past the
  compiler; the `worktree_topology` / site-2 checks are already-correct
  characterization and must NOT be mistaken for the red-first spine (they never flip).

### Subtask T051 – `done_bookkeeping.py`: preserve both sentinel tuples explicitly

- **Purpose**: Re-express the sentinel semantics explicitly now that the
  `except ValueError` branches go dead (`Lane("uninitialized")` succeeds under WP05).
- **Steps**:
  1. **Site-1 (~:151-160).** Today the `except` returns `(coord_lane, False)`; after
     WP05 the `try` returns `(Lane.UNINITIALIZED, True)`, flipping the **force-done
     flag `False → True`**. Add an explicit check so the unseeded / `Lane.UNINITIALIZED`
     case still returns the EXACT preserved tuple **`(coord_lane, False)`** (force-done
     stays `False`) — do NOT let it fall through to the `True` branch. This exact
     tuple, not just "not done", is the contract T050's primary test guards.
  2. **Site-2 (~:375-378).** This one is genuinely preserved — `Lane.UNINITIALIZED`
     still `!=` `Lane.DONE`, so the unseeded sentinel still resolves to not-done. Make
     the comparison explicit for clarity but keep the behavior identical.
  3. If an `except ValueError` block is genuinely unreachable after the explicit
     handling, do not leave it as an empty/effect-free handler; either remove it or
     retain it only for a genuinely-distinct unknown-value case with a clear comment
     (Sonar S1066/effect-free-handler discipline).
- **Files**: `src/specify_cli/merge/done_bookkeeping.py`.
- **Parallel?**: Gated behind T050.
- **Notes**: This is the highest-risk consumer — site-1's silent `False → True`
  force-done flip is exactly what T050's primary test guards; preserve the exact
  `(coord_lane, False)` tuple, not merely "not done".

### Subtask T052 – Sentinel consumers: equality clears + preserve the GENESIS fallback

- **Purpose**: Make the equality-based sentinel comparisons explicit and
  self-documenting (behavior preserved), and — separately — preserve the
  GENESIS-fallback contract at the `coordination/status_transition.py` try/except site
  whose `except` goes dead under WP05.
- **Steps**:
  1. `worktree_topology.py:81` — change the `LEGACY_UNINITIALIZED_SENTINEL`
     comparison to `Lane.UNINITIALIZED`; keep the `return "planned"` mapping.
  2. `aggregate.py:691` — update the sentinel equality comparison to
     `Lane.UNINITIALIZED`.
  3. **`coordination/status_transition.py:557-574` — NOT an equality comparison.**
     This is a
     `try: return Lane(resolve_lane_alias(get_wp_lane(...))), None` /
     `except (ValueError, FileNotFoundError, CanonicalStatusNotFoundError): return Lane.GENESIS, None`
     block. TODAY an unseeded WP makes `Lane("uninitialized")` **raise `ValueError`**,
     so the `except` fires and returns `Lane.GENESIS`. After WP05
     `Lane("uninitialized")` **succeeds**, the `except` goes **dead**, and the function
     would return `Lane.UNINITIALIZED` instead — a type-invisible flip. Preserve the
     GENESIS-fallback contract **explicitly**: map/return `Lane.GENESIS` for the
     unseeded (`Lane.UNINITIALIZED`) read at this site, per the existing FR-008d/R7
     contract comment. Do NOT treat this as an equality-comparison rename.
  4. For the equality sites (1–2), confirm StrEnum equality means observable behavior
     is unchanged.
- **Files**: `src/specify_cli/core/worktree_topology.py`,
  `src/specify_cli/status/aggregate.py`,
  `src/specify_cli/coordination/status_transition.py`.
- **Parallel?**: Gated behind T050.
- **Notes**: T050's secondary unseeded → planned test covers `worktree_topology.py:81`
  directly; T050's PRIMARY `status_transition:557` test guards the GENESIS-fallback
  contract in step 3.

### Subtask T053 – `workspace/context.py`: fix the `dict[str, Lane]` annotation ripple

- **Purpose**: Resolve the NEW `mypy` diagnostic WP05's `get_all_wp_lanes -> dict[str, Lane]`
  annotation surfaces here.
- **Steps**:
  1. `workspace/context.py:513` — `.get(wp_id, "uninitialized")` supplies a `str`
     default against a `dict[str, Lane]`; this `:513` `str` default is the actual NEW
     mypy-diagnostic site. Align the default with the `Lane`-typed dict (e.g. use
     `Lane.UNINITIALIZED` or handle the missing key without a mismatched `str`
     default).
  2. `workspace/context.py:501` — `str(lanes_by_wp.get(wp_id)) == Lane.IN_PROGRESS.value`.
     Adjust so the comparison is `mypy`-clean against `Lane` values while preserving
     the exact truth condition.
  3. Confirm `uv run mypy` is clean on this file.
- **Files**: `src/specify_cli/workspace/context.py`.
- **Parallel?**: Gated behind WP05's annotation change.
- **Notes**: This is a ripple from WP05, not a behavior change — keep the comparison
  semantics identical.

### Subtask T054 – `workflow_executor.py`: clear all three #2675 type clusters

- **Purpose**: Land every `workflow_executor.py` type fix in ONE lane (no parallel
  collision on this 1855-LOC file), with zero new suppressions and NO refactor.
- **Steps**:
  1. **`str → Lane` (~807 / ~816 / ~837 / ~1232):** verify these clear once WP05's
     loader returns pure `Lane`. Only if a diagnostic genuinely survives, coerce at
     the two assignment sites (~770 and ~1209, via `get_wp_lane`) — never at the
     read sites.
  2. **`no-any-return` (~428 / ~1372):** add the single typed wrapper
     `def _locate_wp(...) -> WorkPackage: return cast(WorkPackage, _wf().locate_work_package(...))`
     and route both erroring sites plus the two non-erroring `locate_work_package`
     assignments (~831 and ~1194, structurally identical) through it, for consistency.
  3. **`Optional` narrowings:** at ~668, narrow `agent` (validated non-`None` at
     ~781) with a guard/assert before `set_scalar(..., agent)`; at ~873, narrow the
     `ReviewCycleArtifact | None` against its real invariant.
  4. Do NOT extract, split, or restructure `workflow_executor.py` — this is a
     recorded no-extract call. Touch only the lines needed for the type fixes plus
     the one `_locate_wp` wrapper.
  5. No blanket casts anywhere except the single justified `_locate_wp` cast.
- **Files**: `src/specify_cli/cli/commands/agent/workflow_executor.py`.
- **Parallel?**: No — the whole file is claimed by this lane precisely to avoid a
  parallel-lane collision.
- **Notes**: `dashboard/scanner.py` (~:623,633,914-918) is expected to need **no
  change**; verify and record the verification in the Activity Log.

### Subtask T055 – `coordination/status_transition.py`: narrow `StatusEvent | None`

- **Purpose**: Clear the `StatusEvent | None` mypy narrowing at the real location
  (the plan's `status/status_transition.py:854` reference was wrong).
- **Steps**:
  1. Locate the `event: StatusEvent | None` parameter at ~:763.
  2. Add a `None` guard/narrowing (assert or early-return on a genuine invariant)
     before the `StatusEvent`-typed use downstream.
  3. Do not use a blanket cast — the narrowing must reflect a real invariant.
  4. Confirm `uv run mypy` is clean on this file.
- **Files**: `src/specify_cli/coordination/status_transition.py`.
- **Parallel?**: Can proceed alongside T052's edits to the same file — coordinate
  the two edits so they land together.
- **Notes**: Same file as T052; make both edits in one pass to avoid churn.

## Test Strategy

- **Behavior suite (mandatory):**
  ```bash
  uv run pytest tests/specify_cli/test_lane_consumer_behavior.py -q
  ```
  Both the unseeded → planned and unseeded → not-done tests must be green, and were
  written RED first.
- **Type gate (mandatory, zero-tolerance):**
  ```bash
  uv run mypy
  ```
  Must report **0 errors and 0 new suppressions** across every WP06 surface:
  `done_bookkeeping.py`, `worktree_topology.py`, `aggregate.py`,
  `coordination/status_transition.py`, `workspace/context.py`,
  `workflow_executor.py`, and `dashboard/scanner.py`.
- **Import smoke check:**
  ```bash
  uv run python -c "import specify_cli.status.transitions"
  ```
  Must still succeed (guards against a broken sentinel/import edit).
- **Lint gate:**
  ```bash
  uv run ruff check src/specify_cli tests/specify_cli/test_lane_consumer_behavior.py
  ```
  Zero issues; complexity ceiling 15 respected on any touched function.
- **Fixtures/data:** use production-shaped WP IDs and snapshot structures in the new
  test file; avoid toy placeholders that mask real behavior.

## Risks & Mitigations

- **Type-invisible behavior regression (highest risk).** Every consumer
  `str(...)`-coerces the lane, so `mypy` will not catch a semantics change. The two
  sites that ACTUALLY flip after WP05 are `done_bookkeeping` site-1 (force-done
  `False → True`) and `coordination/status_transition.py:557`
  (`GENESIS → UNINITIALIZED`). *Mitigation:* T050's primary behavior tests pin those
  preserved contracts (force-done `False`; returns `Lane.GENESIS`) and are written RED
  first; the unseeded → planned / site-2 not-done checks are secondary
  characterization only.
- **Dead `except` branches in `done_bookkeeping.py` and `coordination/status_transition.py`.**
  After WP05, `Lane("uninitialized")` succeeds, so the branches that fell back to
  not-done / `Lane.GENESIS` never fire. *Mitigation:* T051 preserves site-1's exact
  `(coord_lane, False)` tuple and T052 preserves the `status_transition:557`
  GENESIS-fallback explicitly; dead handlers are removed or annotated.
- **`workspace/context.py` annotation ripple.** WP05's `dict[str, Lane]` return type
  can surface a new `str`-default diagnostic. *Mitigation:* T053 aligns the default
  and comparison with the `Lane`-typed dict without changing truth conditions.
- **Parallel-lane collision on `workflow_executor.py`.** The file is 1855 LOC and
  all three type clusters touch it. *Mitigation:* the whole file is owned by this
  lane; no extraction/refactor; a single `_locate_wp` wrapper concentrates the only
  sanctioned cast.
- **Over-suppression temptation.** *Mitigation:* C-001 — narrow guards/asserts over
  casts everywhere except the one justified `_locate_wp` wrapper; zero new
  suppressions is an acceptance gate.
- **Dependency ordering.** Starting before WP05 lands will make the `str → Lane`
  clears impossible and the annotation ripple invisible. *Mitigation:* respect
  `dependencies: ["WP05"]`; confirm the loader change is on the base branch first.

## Review Guidance

Reviewers (`reviewer-renata`) should confirm:

- The T050 behavior tests genuinely pin the **sites that flip after WP05** —
  `done_bookkeeping` site-1 keeps force-done `False` (tuple `(coord_lane, False)`) and
  `coordination/status_transition.py:557` still returns `Lane.GENESIS` — and were
  written RED first; the unseeded → planned / site-2 not-done checks are present only
  as secondary characterization (they never flip).
- `done_bookkeeping` (both sentinel tuples), `worktree_topology`, and
  `coordination/status_transition.py:557` **semantics are preserved** — no silent
  force-done `False → True` flip and no `GENESIS → UNINITIALIZED` flip from the
  now-dead `except` branches.
- `workflow_executor.py` uses a **single `_locate_wp` wrapper**, not casts scattered
  across the read sites; the `str → Lane`, `no-any-return`, and `Optional` clusters
  are all resolved.
- **No new suppressions** (`# type: ignore`, `# noqa`, per-file ignores) anywhere in
  the diff.
- **No extraction/refactor** of `workflow_executor.py` beyond the type fixes and the
  one wrapper (recorded no-extract call).
- `dashboard/scanner.py` is unchanged (or minimally changed with a recorded
  rationale), and the import smoke check plus `uv run mypy` are clean on all WP06
  surfaces.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

### How to Add Activity Log Entries

**When adding an entry**:

1. Scroll to the bottom of this Activity Log section
2. **APPEND the new entry at the END** (do NOT prepend or insert in middle)
3. Use exact format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`
4. Timestamp MUST be current time in UTC (check with `date -u "+%Y-%m-%dT%H:%M:%SZ"`)
5. Agent ID should identify who made the change (claude-sonnet-4-5, codex, etc.)

**Format**:

```
- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <brief action description>
```

**Example (correct chronological order)**:

```
- 2026-01-12T10:00:00Z – system – Prompt created
- 2026-01-12T10:30:00Z – claude – Started implementation
- 2026-01-12T11:00:00Z – codex – Implementation complete, ready for review
- 2026-01-12T11:30:00Z – claude – Review passed, all tests passing  ← LATEST (at bottom)
```

**Common mistakes (DO NOT DO THIS)**:

- Adding new entry at the top (breaks chronological order)
- Using future timestamps (causes acceptance validation to fail)
- Inserting in middle instead of appending to end

**Why this matters**: The acceptance system reads the LAST activity log entry as the current state. If entries are out of order, acceptance will fail even when the work is complete.

**Initial entry**:

- 2026-07-15T22:32:40Z – system – Prompt created.

---

### Updating Status

Status is managed via `status.events.jsonl`. Use `spec-kitty agent tasks move-task <WPID> --to <status>` to change WP status.

### Optional Phase Subdirectories

For large features, organize prompts under `tasks/` to keep bundles grouped while maintaining lexical ordering.
- 2026-07-15T23:54:33Z – claude:sonnet:python-pedro:implementer – shell_pid=3790279 – Assigned agent via action command
- 2026-07-16T00:27:57Z – claude:sonnet:python-pedro:implementer – shell_pid=3790279 – T050-T055 done. New tests/specify_cli/test_lane_consumer_behavior.py (4 tests, RED-first verified against pre-fix code): 2 primary targets (done_bookkeeping site-1 force-done stays False; coordination/status_transition.py GENESIS-fallback preserved) + 2 secondary characterizations (worktree_topology unseeded->planned; done_bookkeeping site-2 not-done). done_bookkeeping.py/worktree_topology.py/aggregate.py/coordination/status_transition.py now mypy-clean on the full-tree --strict run (removed 6 real diagnostics: done_bookkeeping.py:151, status_transition.py:854 [not :763 as spec guessed -- real site verified via full-tree mypy], workflow_executor.py:428/668/873/1372). workflow_executor.py: added single _locate_wp cast wrapper, routed 4 call sites through it, no extraction. dashboard/scanner.py verified unchanged (already Lane.UNINITIALIZED-safe via StrEnum hash equality). All validation green: pytest test_lane_consumer_behavior.py (4/4), mypy --strict full-tree (0 new errors, 6 removed), ruff clean, import smoke check OK, broader regression sweep (tests/merge+coordination+status+dashboard: 2220 passed; tests/agent+review+workflow: 3137 passed/1 pre-existing unrelated sphinx failure confirmed on base branch).
- 2026-07-16T00:28:47Z – claude:opus:reviewer-renata:reviewer – shell_pid=3863044 – Started review via action command
