---
work_package_id: WP01
title: "IC-ROWS — one canonical subtask-row walk"
dependencies: []
requirement_refs:
- FR-001
- NFR-005
tracker_refs: []
planning_base_branch: rework/ray-cluster-aggregation
merge_target_branch: rework/ray-cluster-aggregation
branch_strategy: Planning artifacts for this mission were generated on rework/ray-cluster-aggregation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into rework/ray-cluster-aggregation unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "5803"
history:
- created at planning (tasks) — keystone canonical subtask-row walk; WP02 consumes count_wp_section_subtask_rows
agent_profile: python-pedro
authoritative_surface: src/specify_cli/core/subtask_rows.py
create_intent: []
execution_mode: code_change
model: sonnet
owned_files:
- src/specify_cli/core/subtask_rows.py
- tests/specify_cli/core/test_subtask_rows.py
- tests/specify_cli/core/test_uncheck_wp_section_subtask_rows.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile
`/ad-hoc-profile-load python-pedro` (role: implementer). Then read [spec.md](../spec.md)
FR-001 + NFR-005 (the bite-battery fixture list), [plan.md](../plan.md) §IC-ROWS (the "Design
decision (pinned)" note — the guard's `break`-on-exit semantic is canonical, the writer's
current re-enter behavior is a bug being corrected) and §Sequencing (WP01 is the keystone; WP02
depends on it), and [research.md](../research.md) "Decision: one canonical subtask-row walk,
guard-semantic wins". Read the current module in full before touching it:
`src/specify_cli/core/subtask_rows.py` (134 lines as of this writing) — it already documents,
in its module docstring, that it is the "faithful union of PR #2505 (read-only
counters/iterator) and PR #2513 (the uncheck writer)" and that they "still carry parallel
section-walk loops" — that is exactly the debt this WP retires.

## Objective
Collapse the two divergent section-walk loops in `core/subtask_rows.py`
(`iter_wp_section_subtask_rows` at line ~65 and `uncheck_wp_section_subtask_rows` at line ~123)
onto **one** private generator `_walk_wp_section(lines, wp_id) -> Iterator[tuple[int, str, bool]]`
so "what counts as a WP subtask row" has exactly one definition, consumed identically by the
lane-transition guard (via `count_wp_section_subtask_rows`), the dashboard (via
`iter_wp_section_subtask_rows` / `count_subtask_rows`), and the rollback writer (via
`uncheck_wp_section_subtask_rows`). **This is the mission's keystone WP** — WP02 (IC-EMIT-CORE)
rewires `status/emit.py::_infer_subtasks_complete` onto `count_wp_section_subtask_rows` and
cannot start meaningfully until this module's semantics are final.

## Subtasks

### T001 — Extract `_walk_wp_section(lines, wp_id) -> Iterator[tuple[int, str, bool]]`
Add a new private generator to `core/subtask_rows.py` that yields `(index, raw_line, checked)`
for every canonical subtask row inside `wp_id`'s section of `lines` (the module already works
on `text.split("\n")` — keep that convention; take `list[str]`, not raw text, so callers control
how they split/rejoin).

Encode, **once**, the three semantics currently proven correct by the read side
(`iter_wp_section_subtask_rows`, lines ~65-110) and required by NFR-005 / FR-001:

1. **First-`WPxx`-token heading rule (#2346/#2324)**: a heading (`##`–`####`) belongs to the WP
   named by the *first* `WP\d{2,}` token found in it, not any mention. `### WP03 … (depends:
   WP01)` belongs to WP03, not WP01 — WP01's section must not treat this heading as "still
   inside WP01" nor "re-entering WP01". Reuse whatever heading-token extraction regex/helper the
   current `iter_wp_section_subtask_rows` already uses (do not write a second one) — read it
   before writing `_walk_wp_section` and lift the logic verbatim into the new helper's heading
   check, deleting the duplicate afterward (see T004).
2. **Fenced-code skipping**: lines between a ` ``` `/`~~~` open and its matching close are never
   yielded as rows, even if they look like `- [ ] T001 …` (both counters and the writer already
   toggle an `in_code_fence` boolean on any line whose stripped form starts with `` ``` `` or
   `~~~` — preserve that toggle exactly, including that the fence markers themselves are not
   emitted as rows).
3. **Break-on-section-exit**: once a *different* WP's heading is seen after the target section
   opened, the section is closed for the rest of the document — do **not** re-enter it if a
   `## WPxx` heading for the same `wp_id` appears again later. This is the read counter's
   existing `break` behavior (`iter_wp_section_subtask_rows` line ~97-98: `if in_wp_section and
   heading_wp is not None and heading_wp != wp_id: break`) — carry it into `_walk_wp_section`
   unchanged. Do **not** carry over the writer's current behavior of setting `in_wp_section =
   False` and *continuing* (see T003 for why that is being deliberately changed, not preserved).

`_walk_wp_section` should track fence + section state internally and be the *only* place any of
this logic lives — it takes the wp_id and yields checked-row tuples plus enough info (the raw
line and its index) for a caller to do read-only counting or in-place mutation.

### T002 — Rewire the read counters onto `_walk_wp_section`
Rewrite `iter_wp_section_subtask_rows`, `count_wp_section_subtask_rows`, and `count_subtask_rows`
(module-level, not WP-scoped — it counts across the whole document) to consume `_walk_wp_section`
where applicable:

- `count_subtask_rows(text)` has no `wp_id` — it counts every canonical row in the whole
  document regardless of section, so it does **not** call `_walk_wp_section` (which is
  WP-scoped); it keeps its own simple fence-aware loop, but must still delegate fence-toggle
  detection and the `CHECKED_SUBTASK_ROW`/`UNCHECKED_SUBTASK_ROW` match to the same two module
  constants (already true today — do not touch this function's control flow beyond confirming it
  shares constants, see T004).
- `iter_wp_section_subtask_rows(tasks_md_text, wp_id)` becomes a thin wrapper: split the text
  into lines, drive `_walk_wp_section`, and for each yielded `(index, line, checked)` extract the
  `task_id` via the same `CHECKED_SUBTASK_ROW`/`UNCHECKED_SUBTASK_ROW` match used inside the
  walker and yield `(task_id, checked)` — preserving its existing public signature and docstring
  contract exactly (callers such as the dashboard progress feature and `tasks_shared` must not
  need to change).
- `count_wp_section_subtask_rows(tasks_md_text, wp_id)` stays a thin wrapper around
  `iter_wp_section_subtask_rows` (it already is — verify the `done`/`total` accumulation loop at
  lines ~112-121 is unchanged; no rewrite needed there beyond confirming it still compiles
  against the new iterator).

Behavior parity requirement: this WP does **not** change what the read counters return for any
existing fixture — it only removes the duplicated loop body. Run any existing tests for these
three functions before and after and confirm identical results (the module's own docstring
already states the counter's break-on-exit is correct; T002 must not regress it).

### T003 — Rewrite `uncheck_wp_section_subtask_rows` onto `_walk_wp_section` (BEHAVIOR CHANGE)
This is the subtask that actually fixes NFR-005's divergence. Today's writer (lines ~123-165ish)
sets `in_wp_section = False` and **continues** when it sees a different WP's heading (line
~155-158: `if in_wp_section and heading_wp is not None and heading_wp != wp_id: in_wp_section =
False; result.append(line); continue`) — so if a `## WP01` heading re-appears later in the same
document (e.g. a stray duplicate, a `depends:` cross-reference block, or hand-edited tasks.md),
the writer **re-enters** it and unchecks `[x]` rows there too. The read counters, by contrast,
`break` — once WP01's section is left, it is closed for the rest of the walk, so a later `## WP01`
duplicate is never counted or touched.

Per the plan's pinned design decision, the **guard's break semantic is canonical**. Rewrite
`uncheck_wp_section_subtask_rows` to:

1. Drive `_walk_wp_section` (or a variant that also yields non-matching lines so the writer can
   reproduce the full document) to find only the checked rows within the *first* WP01 section —
   once that section closes (a different WP's heading, or EOF), stop looking for rows to flip
   even if a `## WP01` heading reappears.
2. Preserve every non-matching line verbatim, in original order — the function must not reorder,
   drop, or reformat surrounding content.
3. Flip only `[x]` → `[ ]` inside the single, first section — use the same
   `re.sub(r"\[[xX]\]", "[ ]", line, count=1)` substitution the current writer uses (line ~160)
   so whitespace/casing around the checkbox is preserved.
4. Return the **original text unchanged** (same string object semantics as today — `if updated
   == original` must still be a valid freshness check for callers like
   `tasks_move_task._mt_uncheck_rollback_subtasks`, which skips the write+commit when nothing
   changed) when nothing in the section needed flipping.

Because this changes observable behavior for the re-appearing-heading case, call this out
explicitly in the WP's Activity Log and PR description as an intentional NFR-005 correction, not
a silent behavior drift — the rationale (guard-semantic wins, see research.md) must be
traceable from the commit message.

### T004 — Exactly one CHECKED/UNCHECKED pattern survives
Audit the module for any duplicate copy of the row-matching regex. Today `CHECKED_SUBTASK_ROW`
and `UNCHECKED_SUBTASK_ROW` are defined once at module level (lines ~33-36) and referenced by
name everywhere — confirm no function has silently forked a local `re.compile(...)` equivalent
(e.g. inline inside the old writer loop) and remove it if one exists after T003's rewrite lands.
This is the FR-001 acceptance bar: "Exactly one checked-row pattern and one unchecked pattern
remain in the module." Grep the final module for `re.compile` and assert there are exactly two
hits (the two module constants) plus any `re.sub`/`re.match` call sites that reference them by
name — zero additional `re.compile(` calls for row matching.

### T005 — NFR-005 bite battery (the fixture list is non-negotiable)
Extend `tests/specify_cli/core/test_subtask_rows.py` and
`tests/specify_cli/core/test_uncheck_wp_section_subtask_rows.py` with a shared fixture battery
exercised through **every public function** (`count_subtask_rows`,
`count_wp_section_subtask_rows`, `iter_wp_section_subtask_rows`, `uncheck_wp_section_subtask_rows`)
where applicable. Required fixtures, each as its own test:

1. **Re-appearing WP heading — the headline NFR-005 case.** A document with `## WP01` (some
   `[x]` rows), then `## WP02` (its own rows), then a *second* `## WP01` block with more `[x]`
   rows. Assert:
   - `count_wp_section_subtask_rows(text, "WP01")` counts only the **first** WP01 block (proves
     the counter already did this — regression guard).
   - `uncheck_wp_section_subtask_rows(text, "WP01")` unchecks rows **only in the first** WP01
     block and leaves the **second** WP01 block's `[x]` rows completely untouched. This is the
     THIS-IS-A-BEHAVIOR-CHANGE assertion from T003 — write it as an explicit, named test (e.g.
     `test_uncheck_does_not_reenter_reappearing_wp_heading`) so a future regression is caught
     immediately.
2. **Content after section end** — non-WP prose/headings following the target WP's section must
   pass through unmodified and uncounted.
3. **Nested headings** — a sub-heading (`###`/`####`) inside the WP's section that does NOT
   contain a `WPxx` token must not close the section (only a heading with a *different* WP's
   token token closes it).
4. **`depends: WPnn` mention in a heading** — `### WP03 Foo (depends: WP01)` must be attributed
   to WP03 only (first-token rule); confirm neither WP01's count nor its uncheck touches this
   heading's rows.
5. **Fenced code blocks containing `- [ ] T001 …`** — rows inside ` ``` `/`~~~` fences are never
   counted or unchecked, including when the fence is nested inside the target WP's section.
6. **IDs past T999** — `T1000`, `T1234` must still match (`T\d{3,}`, not `T\d{3}`).

Also add/keep at least one straightforward happy-path fixture per function (single section, no
edge cases) so the battery documents baseline behavior, not only edge cases.

### T006 — Prove guard == dashboard-count == rollback-uncheck agree
Add a final integration-style test that drives the *same* input document through
`count_wp_section_subtask_rows` (the value the lane-transition guard and WP02's rewritten
`_infer_subtasks_complete` will consume), `iter_wp_section_subtask_rows` (what the dashboard
progress feature consumes), and `uncheck_wp_section_subtask_rows` (what rollback consumes), and
assert they agree on the fixture battery from T005 — e.g. after uncheck, re-running the counter
on the *rewritten* text shows `done == 0` for the (first) WP01 section, and the second WP01 block
(if present) is untouched by both the counter and the uncheck. This is the SC-002 acceptance
proof, driven entirely through public functions (no reaching into `_walk_wp_section` directly
from tests — it is private and internal).

Run `uv run pytest tests/specify_cli/core/test_subtask_rows.py
tests/specify_cli/core/test_uncheck_wp_section_subtask_rows.py -q`, then `uv run ruff check
src/specify_cli/core/subtask_rows.py tests/specify_cli/core/test_subtask_rows.py
tests/specify_cli/core/test_uncheck_wp_section_subtask_rows.py` and `uv run mypy
src/specify_cli/core/subtask_rows.py` — zero new issues, zero new suppressions.

## Branch Strategy
Planning base branch and merge target branch are both `rework/ray-cluster-aggregation`;
`spec-kitty implement WP01` allocates an execution worktree per the lane computed from
`lanes.json` (coord-topology mission — the coordination branch and lane worktree are resolved by
the allocator, not hand-built). No WP dependency to wait on — this is the keystone; nothing else
merges before it lands.

## Definition of Done
- `_walk_wp_section` is the single generator driving the first-WPxx-token heading rule, fence
  skipping, and break-on-section-exit; it is exercised through all four public functions, no
  function has its own parallel loop.
- Exactly one `CHECKED_SUBTASK_ROW` and one `UNCHECKED_SUBTASK_ROW` pattern remain in the module.
- `uncheck_wp_section_subtask_rows` no longer re-enters a re-appearing `## WPnn` heading — proven
  by a named regression test, not just an assertion buried in a larger fixture.
- NFR-005 bite battery (re-appearing heading, content-after-section-end, nested headings,
  `depends:` mention, fenced blocks, ids past T999) is green through every public function.
- Guard-count / dashboard-count / rollback-uncheck agreement proven on the full battery
  (`uv run pytest tests/specify_cli/core/ -q`).
- `uv run ruff check` + `uv run mypy` clean on all three owned files, zero new suppressions.
- Full `tests/architectural/` 0-failed; dead-code gate green (no orphaned symbols left behind by
  the consolidation — `_walk_wp_section` must be exercised by at least the four public functions,
  not sit unreferenced).

## Risks
- **Silently weakening the fence or first-WPxx-token rules while consolidating** — the two
  existing loops both implement these correctly today; the risk is a transcription slip during
  extraction, not a design gap. Mitigate by diffing behavior against the pre-change functions on
  the full fixture battery before deleting the old loops.
- **Under-scoping the behavior-change callout** — because T003 changes real behavior (not just
  refactors), a reviewer who assumes this WP is byte-preserving could wrongly flag the change.
  State the rationale (guard-semantic canonical, per research.md) directly in the PR/Activity Log.
- **WP02 blocking on drift** — if `count_wp_section_subtask_rows`'s signature or semantics shift
  in a way not anticipated by the plan (e.g. return type, edge-case for zero rows), flag it
  immediately since WP02 is gated on this WP landing first.

## Reviewer Guidance
Confirm: `_walk_wp_section` is genuinely the only section-walk loop left (grep for `in_wp_section`
outside the new helper and its wrapper functions); the writer's re-enter bug is fixed and pinned
by a named test; the fixture battery covers all six NFR-005 cases through the actual public
functions (not a private-function probe); `count_subtask_rows` (whole-document, no `wp_id`) was
correctly left as its own loop rather than forced through `_walk_wp_section`; zero new
`re.compile` calls for row matching; ruff/mypy clean; full `tests/architectural/` still 0-failed.

## Activity Log
- {{TIMESTAMP}} — system — Prompt created at planning (tasks).
- 2026-07-12T11:03:05Z – claude:sonnet:python-pedro:implementer – shell_pid=4166725 – Assigned agent via action command
- 2026-07-12T11:03:29Z – claude:sonnet:python-pedro:implementer – shell_pid=4168016 – Assigned agent via action command
- 2026-07-12T11:10:42Z – claude:sonnet:python-pedro:implementer – shell_pid=4168016 – WP01 IC-ROWS: unified _walk_wp_section, writer break-semantic; 313 core tests green, ruff/mypy clean (commit 3f68accfb)
- 2026-07-12T11:11:00Z – claude:opus:reviewer-renata:reviewer – shell_pid=5803 – Started review via action command
- 2026-07-12T11:20:18Z – user – shell_pid=5803 – APPROVE (opus renata): one _walk_wp_section, writer break-semantic verified, dead-code gate 7/0, 313 tests
