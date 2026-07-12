---
work_package_id: WP02
title: "IC-EMIT-CORE — close the emit-layer fail-open at its callers"
dependencies:
- WP01
requirement_refs:
- FR-002
- FR-003
- FR-004
tracker_refs: []
planning_base_branch: rework/ray-cluster-aggregation
merge_target_branch: rework/ray-cluster-aggregation
branch_strategy: Planning artifacts for this mission were generated on rework/ray-cluster-aggregation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into rework/ray-cluster-aggregation unless the human explicitly redirects the landing branch.
subtasks:
- T007
- T008
- T009
- T010
- T011
- T012
- T013
- T014
agent: "claude:sonnet:python-pedro:implementer"
shell_pid: "59999"
history:
- created at planning (tasks) — the class-closer; retires the emit-layer fail-open at all four production callers
agent_profile: python-pedro
authoritative_surface: src/specify_cli/status/emit.py
create_intent:
- tests/specify_cli/status/test_infer_subtasks_primary.py
execution_mode: code_change
model: sonnet
owned_files:
- src/specify_cli/status/emit.py
- src/specify_cli/status/aggregate.py
- src/specify_cli/coordination/status_transition.py
- tests/specify_cli/status/test_infer_subtasks_primary.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile
`/ad-hoc-profile-load python-pedro` (role: implementer). Then read [spec.md](../spec.md)
FR-002/FR-003/FR-004 + Scenario 1 (the headline class-closure scenario) + the edge case "a WP
section with zero T### rows → inference returns complete", [plan.md](../plan.md) §IC-EMIT (the
full "Per-caller primary-surface resolution (code-verified)" subsection — it corrects the plan's
own earlier draft, read it as ground truth over any looser prose elsewhere) and §Sequencing (this
is WP-A of the IC-EMIT split; WP03 depends on this WP finishing `status_transition.py:444`
first), and [research.md](../research.md) "Decision: close the fail-open at the shared emit
layer, not per-door" + "Verified-current: the vulnerable vs already-correct surfaces". This WP
depends on **WP01** — do not start rewriting `_infer_subtasks_complete`'s row logic until
`core.subtask_rows.count_wp_section_subtask_rows` has landed with its final, unified semantics.

## Objective
`_infer_subtasks_complete` (`status/emit.py` ~:272-295) is the shared completeness inference the
lane-transition gate ultimately trusts on every path except the already-correct native
`move-task` guard. Today it (a) fails open when the resolved `tasks.md` is absent
(`if not tasks_path.exists(): return True` at ~:275-276), and (b) re-derives row semantics with a
divergent regex/heading/no-fence walk instead of the canonical counter. Worse, at least two of
its **four** production call sites resolve the wrong (coord-husk) surface instead of the primary
partition where `tasks.md` actually lives on a coord-topology mission. This WP: reimplements the
row logic on WP01's canonical counter, removes the fail-open, and threads the primary-surface
resolver through all four callers — `status/emit.py` (two call sites), `status/aggregate.py`
(:717), and `coordination/status_transition.py` (:444). **Do NOT touch**
`tasks_shared._check_unchecked_subtasks` — it is the native `move-task` guard and is already
primary-correct; re-asserting it here would be scope creep and risks masking a real regression
with a redundant fix.

## Subtasks

### T007 — SPIKE: confirm the exact call sites and their surrounding context before editing
Do this first and record findings in the Activity Log (this is not throwaway — it is the
contract for T010-T012). Confirm by reading the live code (not just the plan's prose):

(a) `status/aggregate.py` — `_resolve_review_gate_inputs` is a method on the `MissionStatus`
    class (`class MissionStatus:` at ~:167); at ~:717 it calls
    `status_emit._infer_subtasks_complete(self.read_dir, request.wp_id or "")`. `self.repo_root`
    and `self.mission_slug` are both set in `MissionStatus.__init__` (see the several
    `self.mission_slug = mission_slug` assignments earlier in the file) and are available at this
    call site — introducing `resolve_planning_read_dir(self.repo_root, self.mission_slug,
    kind=MissionArtifactKind.TASKS_INDEX)` here is a **new introduction** (today's code passes
    `self.read_dir`, not a `resolve_planning_read_dir(...)` result) — do not describe this as "a
    swap of an existing call", it adds the resolver where none existed.
(b) `status/emit.py` — the nullable-`repo_root` fallback sites are at ~:532
    (`context_root = repo_root if repo_root is not None else feature_dir`, feeding the
    `_infer_subtasks_complete(feature_dir, wp_id)` call at ~:535) and ~:685
    (`context_root = request.repo_root if request.repo_root is not None else feature_dir`,
    feeding the call at ~:690). Confirm `repo_root` is genuinely nullable at both — these are
    library-internal functions callable with `repo_root=None` from contexts (including some unit
    tests) that have no git-repo `cwd` at all.
(c) Confirm `resolve_canonical_root` (`core/paths.py:381`, param `cwd: Path | None = None`)
    **raises `WorkspaceRootNotFound`** (defined `core/paths.py:367`, raised at `core/paths.py:437`)
    when no git repo is found upward from `cwd` — i.e. it is **not** a drop-in replacement for
    `else feature_dir`, which never raises. Any caller that swaps in
    `resolve_canonical_root(feature_dir)` unconditionally will crash existing non-repo/tmp-dir
    unit tests that construct a bare `feature_dir` with no git ancestry.
(d) `coordination/status_transition.py` — the caller is inside `_prepare_event` (~:421-445); the
    call itself is at ~:444: `subtasks_complete = _emit._infer_subtasks_complete(feature_dir,
    request.wp_id)`, guarded by `if subtasks_complete is None and from_lane ==
    Lane.IN_PROGRESS and resolved_lane == Lane.FOR_REVIEW:`. The file already imports
    `resolve_planning_read_dir` at ~:769 for an unrelated call (`lanes_read_dir = ...` at ~:771)
    — that is the in-file precedent to follow, not a new import pattern. `request.repo_root` and
    `mission_slug` (a `_prepare_event` parameter) are both in scope at :444.

### T008 — Reimplement `_infer_subtasks_complete` row semantics on the canonical counter
Rewrite the body of `_infer_subtasks_complete(feature_dir: Path, wp_id: str) -> bool` in
`status/emit.py` to resolve `tasks.md`'s text and call
`core.subtask_rows.count_wp_section_subtask_rows(text, wp_id)` (WP01's canonical, fence-aware,
first-WPxx-token, mandatory-`T\d{3,}` counter) instead of the current bespoke regex/heading walk
(the `re.search(rf"^#{{2,4}}(?!#).*\b{re.escape(wp_id)}\b", line)` / `re.match(r"^\s*-\s*\[\s*\]\s+",
line)` loop at ~:279-291, which matches ANY unchecked checkbox line — including prose checkboxes
and rows inside fenced code — not just canonical `T###` rows). Delete the divergent loop
entirely; import `count_wp_section_subtask_rows` from `specify_cli.core.subtask_rows` at module
level (no cycle risk — `core` sits below `status`). Return `done == total` (complete) when
`total > 0`; when `total == 0` (the WP section genuinely has no subtask rows, or the WP heading
was never found), return `True` — "nothing to block on" per the spec's edge case.

**Campsite note (SAFE)**: while in this function, replace the hardcoded `"tasks.md"` string
literal inside `_infer_subtasks_complete` with the module's canonical `TASKS_MD_FILENAME`
constant, to match the guard's existing naming convention. **Do NOT** expand
`emit_status_transition` while you're in this file — it currently sits at complexity 12 and
carries a `# NOSONAR` — leave it as-is; that function is ADJACENT and out of this WP's scope.

### T009 — Remove the fail-open on missing `tasks.md`
Delete the `if not tasks_path.exists(): return True` short-circuit (~:275-276). Once the resolved
path is the **primary** surface (T010/T011), a genuinely-absent `tasks.md` is not "no subtasks
exist" — it means the caller resolved the wrong surface, or the mission's planning artifacts are
missing entirely. Either way, per FR-002/Scenario 1, the correct behavior is to treat "cannot
prove subtasks are complete" as **not complete** — return `False` (block), never `True` (fail
open). Update the function's docstring accordingly; this is the single most important line-level
change in the whole mission — get the polarity right (absent-and-unprovable → **block**, not
"no rows found in an existing file" → complete, which is the *different*, legitimate T008
zero-rows case).

### T010 — Thread the primary surface at `aggregate.py:717`
In `MissionStatus._resolve_review_gate_inputs`, replace `self.read_dir` with
`resolve_planning_read_dir(self.repo_root, self.mission_slug,
kind=MissionArtifactKind.TASKS_INDEX)` as the `feature_dir` argument passed into
`status_emit._infer_subtasks_complete(...)`. Import `resolve_planning_read_dir` from
`specify_cli.missions._read_path_resolver` and `MissionArtifactKind` from
`mission_runtime.artifacts` (module-level import if `aggregate.py` doesn't already import from
either; check for an existing deferred/function-local import pattern in this file first and
follow it for consistency — several call sites in this file already do function-local imports of
resolver helpers). `MissionStatus.repo_root`/`mission_slug` are dataclass-required fields
documented as the primary checkout — no `None`-guard needed here, unlike T011.

### T011 — Thread the primary surface at `emit.py:532` / `:685` (with the WorkspaceRootNotFound guard)
At both nullable-`repo_root` fallback sites in `status/emit.py`, derive the primary root from
`feature_dir` via `resolve_canonical_root` when `repo_root` is `None`, **wrapped in a
`try/except WorkspaceRootNotFound` that falls back to the existing `else feature_dir` behavior**:

```python
from specify_cli.core.paths import WorkspaceRootNotFound, resolve_canonical_root
...
if repo_root is not None:
    context_root = repo_root
else:
    try:
        context_root = resolve_canonical_root(feature_dir)
    except WorkspaceRootNotFound:
        context_root = feature_dir
```

This preserves `workspace_context` string construction (unchanged consumer at ~:533/:686) while
giving `_infer_subtasks_complete` a **primary-rooted** `feature_dir` to resolve `tasks.md`
against when a real repo root is derivable. Concretely: once `context_root` is resolved this
way, pass it (or a `resolve_planning_read_dir(context_root, mission_slug,
kind=MissionArtifactKind.TASKS_INDEX)` derived from it, mirroring T010) into the
`_infer_subtasks_complete` call at ~:535/:690 instead of the raw `feature_dir` used today. Do
**not** let the guard swallow any other exception — only `WorkspaceRootNotFound`; a real bug
inside `resolve_canonical_root` must still surface. Verify by running the existing `status/emit`
test suite for any test that constructs a `feature_dir` under `tmp_path` with no `.git` ancestor
— it must still pass unchanged after this subtask.

### T012 — Thread the primary surface at `status_transition.py:444`
In `_prepare_event`, before the `subtasks_complete = _emit._infer_subtasks_complete(feature_dir,
request.wp_id)` call at ~:444, resolve the primary surface the same way T010 does, reusing the
file's existing `resolve_planning_read_dir` import (already present at ~:769 — do not add a
second import of the same symbol). `request.repo_root` is populated on the orchestrator-api door
(`orchestrator_api/commands.py:1437` passes it through `TransitionRequest`) — confirm this by
tracing the call chain from `orchestrator_api/commands.py`'s `emit_status_transition_transactional`
call. Use `mission_slug` (already a `_prepare_event` parameter) and `request.repo_root` to build
the resolved dir; fall back to the existing `feature_dir` when `request.repo_root` is `None`
(mirror T011's pattern — this function is called from non-orchestrator paths too, where
`repo_root` may be absent).

### T013 — Regression test: native `agent status --to for_review` blocks on unchecked rows
Create `tests/specify_cli/status/test_infer_subtasks_primary.py`. The headline test drives the
**production** path: construct a coord-topology mission fixture (primary `tasks.md` with a WP
section containing at least one unchecked `T###` row) and call the native
`spec-kitty agent status --to for_review` transition **without** `--subtasks-complete` and
**without** `--force`, asserting through `status/aggregate.py`'s `MissionStatus` /
`_resolve_review_gate_inputs` route (the T010 call site) — NOT the standalone
`_infer_subtasks_complete` function called directly (that would only prove the unit works, not
that the wiring is correct end to end). Assert the transition is **blocked**. Add:
- A positive case: all `T###` rows checked → transition **allowed**.
- The primary-absent case: primary `tasks.md` genuinely does not exist for the mission → the
  transition is **blocked** (proves T009's fail-open removal, not just T008's row-semantics fix).
- A zero-rows case: the WP section exists but has no `T###` rows at all → transition **allowed**
  (the edge case from spec.md, proving T008 didn't over-correct into always-blocking).

### T014 — Full-suite check + confirm the native guard is untouched
Run `uv run pytest tests/specify_cli/status/ -q` plus any coord-mission status integration tests
(search `tests/` for existing coverage of `agent status --to for_review` on coord topologies and
run those too). Confirm via `git diff` that `tasks_shared._check_unchecked_subtasks` and its
call sites are **not** modified by this WP — it was already primary-correct and is out of scope.
`uv run ruff check` + `uv run mypy` on all four owned files, zero new issues, zero new
suppressions.

## Branch Strategy
Planning base branch and merge target branch are both `rework/ray-cluster-aggregation`;
`spec-kitty implement WP02` allocates an execution worktree per the lane computed from
`lanes.json`. **Depends on WP01** — `count_wp_section_subtask_rows` must have its final
canonical semantics before T008 wires it in; do not start T008 against an in-flight WP01.

## Definition of Done
- `_infer_subtasks_complete` derives completeness from `core.subtask_rows.count_wp_section_subtask_rows`
  — the divergent regex/heading/no-fence loop is deleted.
- The `tasks_path.exists()` fail-open is removed; a genuinely-absent primary `tasks.md` blocks,
  never passes.
- All four production callers (`emit.py` x2, `aggregate.py:717`, `status_transition.py:444`)
  resolve the **primary** planning surface, not a coord husk; the `emit.py` sites are guarded
  against `WorkspaceRootNotFound` so non-repo unit tests do not regress.
- `test_infer_subtasks_primary.py` proves, through the production `aggregate.py` route: blocked
  (unchecked rows), allowed (all checked), blocked (primary absent), allowed (zero rows).
- `tasks_shared._check_unchecked_subtasks` is untouched (confirmed via diff).
- `uv run pytest tests/specify_cli/status/ -q` green; `uv run ruff check` + `uv run mypy` clean,
  zero new suppressions; full `tests/architectural/` 0-failed; dead-code gate green.

## Risks
- **The `WorkspaceRootNotFound` guard is the single highest-risk line in this WP** — get it wrong
  (catch too broadly, or skip it) and either a real bug is silently swallowed, or existing
  non-repo/tmp-dir unit tests in `status/emit`'s test suite start failing. Write/attempt-run those
  existing tests early, not last.
- **`aggregate.py:717` is a genuinely new resolver introduction**, not a mechanical swap — don't
  assume `self.read_dir` and `resolve_planning_read_dir(self.repo_root, self.mission_slug, ...)`
  are equivalent in every existing test fixture; some fixtures may construct `MissionStatus`
  directly with a `read_dir` that diverges from what the resolver would compute. Run the full
  `status/aggregate` test suite, not just the new regression test.
- **Four-caller threading risk** — it is easy to fix three call sites and miss the fourth (or fix
  the wrong line number if the file has drifted since spec.md was written). Grep for
  `_infer_subtasks_complete(` across the whole `src/` tree after this WP and confirm every call
  site resolves a primary surface (or intentionally documents why not, if any is found that
  spec.md didn't anticipate).

## Reviewer Guidance
Confirm: `_infer_subtasks_complete`'s row logic is 100% delegated to WP01's counter (no residual
regex); the fail-open line is gone and replaced with block-on-absent; all four callers listed in
FR-003 are threaded; the `WorkspaceRootNotFound` try/except is narrowly scoped (only that
exception) and does not silently swallow other errors; `test_infer_subtasks_primary.py` exercises
the **production** `aggregate.py` route, not a standalone function call; `tasks_shared._check_unchecked_subtasks`
diff is empty; ruff/mypy clean; full arch suite 0-failed.

## Activity Log
- {{TIMESTAMP}} — system — Prompt created at planning (tasks).
- 2026-07-12T11:21:23Z – claude:sonnet:python-pedro:implementer – shell_pid=59999 – Assigned agent via action command
- 2026-07-12T12:07:51Z – claude:sonnet:python-pedro:implementer – shell_pid=59999 – WP02 IC-EMIT-CORE ready (8572186f5)
- 2026-07-12T12:16:54Z – user – shell_pid=59999 – APPROVE (opus renata, out-of-band review): fail-open closed, all callers threaded w/ WorkspaceRootNotFound guard, T013 production-path regression 362 green, test remediation judged, mypy no-new
