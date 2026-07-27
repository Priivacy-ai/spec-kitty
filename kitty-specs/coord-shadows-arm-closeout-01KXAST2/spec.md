# Specification: Close #2160 Coord-Shadows Read/Gate Arm

**Mission**: `coord-shadows-arm-closeout-01KXAST2`
**Parent epic**: #2160 (coord topology: unify artifact authority for task/status surfaces)
**Branch**: `rework/ray-cluster-aggregation` (planning + merge target)
**Mission type**: software-dev

## Overview / Context

In the coord-topology execution model, planning artifacts (`tasks.md`, `spec.md`) live on the
**primary** partition while lane/status artifacts live on the **coordination** partition. When a
reader resolves a planning artifact off the coord-first surface mid-mission, it reads an empty
**husk** — the "coord-shadows-primary" defect class tracked under epic #2160. The root
write/validate authority split was resolved (PR #2181/#2194/#2212/#2226); what remains open is
the **read/gate arm**: five distinct symptom sites, each filed and fixed by an external
contributor.

Those five fixes (#2503/#2505/#2511/#2514/#2515) have been **faithfully aggregated** onto this
branch (6 cherry-picked commits, original attribution preserved, + 1 campsite lint commit; 89
cherry-picked tests green). But each patched a symptom, and a three-lens review squad found the
aggregate carries three structural gaps: a subtask-row semantic now defined **three** times (two
of them divergent), a **fail-open** in the shared status-gate layer that only one of the five
doors closed, and a **regression** where a recovered execution lane re-leaks status files into
its worktree. This mission aligns the aggregate into one coherent slice that genuinely closes the
class, and folds in the open friction issue that lives on the same claim-marker surface (#1231).
A second candidate fold (#1862, analysis-freshness) was found **already shipped** (#1764) during
the post-spec squad — it is closed verified-already-fixed and retained only as a regression guard.

The original five PRs will be **closed-superseded by the operator after this mission's PR merges
upstream** — not before.

## User Scenarios & Testing

**Primary actors**: the orchestrating agent and operator running the implement/review loop; the
dashboard viewer observing an in-flight mission.

### Scenario 1 — a WP cannot reach review with unfinished subtasks (any emit-layer path)
An agent submits `WP03` for review on a coordination-topology mission without asserting
subtask completeness, via **either** the orchestrator-api **or** the native `agent status --to
for_review` command — both of which reach the shared **emit-layer** completeness inference
(`_infer_subtasks_complete`) rather than the native `move-task` guard. The inference resolves the
primary `tasks.md`, finds unchecked `T###` rows, and **blocks** the transition. Previously this
emit-layer inference read the coord husk (tasks.md absent → **failed open** → "complete") and used
a divergent row regex, so the WP reached `for_review` with every subtask unchecked.

> Note: the native `move-task` guard (`tasks_shared._check_unchecked_subtasks`) is **already**
> primary-correct on this branch and is **not** the vulnerable surface — do not re-assert it. The
> open exposure is exclusively the emit-layer inference and the paths that reach it.

### Scenario 2 — a recovered lane never re-leaks status files
An implementing agent is killed mid-run (OS idle-sleep); the lane branch survives but the worktree
directory is gone. On the next allocation the lane is **recovered** in place, and — because the
recovery path re-registers the same sparse-checkout the fresh-create path applies — the recovered
coord-topology lane contains **no** `status.events.jsonl` / `status.json`. Previously the recovery
path skipped sparse-checkout, re-materializing status files in the lane and reintroducing the very
husk this mission closes.

### Scenario 3 — a live agent is not falsely flagged stale
While a dispatched subagent spends minutes reading and planning before its first commit,
`agent tasks status` consults the claiming `shell_pid`'s liveness, sees the process is alive, and
**does not** flag the WP stale. Previously staleness was judged purely on git-commit-timestamp idle
time (`core/stale_detection.py`), producing false "stale" warnings during normal orchestration.

### Scenario 4 — progress ticks don't invalidate the analysis gate
An agent ticks a subtask checkbox in `tasks.md` (now a first-class, frequent write via the
dashboard progress feature). The implement gate's analysis-freshness check — which hashes only the
structural/authoring content, not checkbox state — remains **fresh**. Previously each tick changed
the wholesale hash and invalidated the analysis after every WP.

### Edge cases
- A WP section with **zero** `T###` rows → inference returns "complete" (nothing to block on).
- `### WP03 … (depends: WP01)` heading → does **not** re-enter WP01's section (first-WPxx-token rule).
- Subtask-shaped lines inside fenced code blocks → **not** counted as subtasks.
- A `shell_pid` that is unparyseable, absent, or belongs to a recycled PID → liveness check is
  conservative and never crashes (treated as not-provably-alive).
- Non-coord (flat/single-branch) topologies → sparse-checkout re-registration is a no-op; behavior
  byte-identical to today.

## Requirements

### Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | `core/subtask_rows.py` exposes a single private section-walk generator `_walk_wp_section(lines, wp_id) -> Iterator[(index, text, checked)]` encoding the first-WPxx-token heading rule (#2346/#2324) and fenced-code skipping exactly once; the read counters (`iter_wp_section_subtask_rows`, `count_wp_section_subtask_rows`, `count_subtask_rows`) and the writer (`uncheck_wp_section_subtask_rows`) all consume it. Exactly one checked-row pattern (`CHECKED_SUBTASK_ROW`) and one unchecked pattern remain in the module. | Draft |
| FR-002 | `_infer_subtasks_complete` (`status/emit.py`) derives completeness from the canonical `count_wp_section_subtask_rows` (mandatory `T\d{3,}` id, first-WPxx-token heading, fence-aware); the divergent regex/heading/no-fence logic is deleted. Returns "complete" only when done == total, or when the section genuinely has no subtask rows. | Draft |
| FR-003 | `_infer_subtasks_complete` resolves the **primary** planning surface — via the single canonical resolver `resolve_planning_read_dir(..., kind=MissionArtifactKind.TASKS_INDEX)` (`missions/_read_path_resolver.py`), NOT any local `_planning_read_dir` variant — at **all four** of its production call sites: the **two** in `status/emit.py` (~:535, ~:690), `coordination/status_transition.py` (~:444), and `status/aggregate.py` (~:717). It never reads a coord husk and never fails open when the coord surface lacks `tasks.md`. (The 5th caller, `orchestrator_api/commands.py` ~:1428, is the #2511 per-door pre-derivation removed under FR-005.) | Draft |
| FR-004 | Submitting a WP `--to for_review` **without** `--subtasks-complete` and without `--force`, on a coordination-topology mission whose primary `tasks.md` has unchecked rows, is blocked when the transition reaches the **emit-layer inference** — exercised via **both** the native `agent status --to for_review` path (→ `status/aggregate.py`) and the orchestrator-api path. The already-correct native `move-task` guard is out of scope. | Draft |
| FR-005 | The orchestrator-api per-door `subtasks_complete` pre-derivation introduced by #2511 (`orchestrator_api/commands.py` ~:1418-1430) is simplified or removed **only after** FR-003 has corrected `coordination/status_transition.py` (the door's remaining block path), leaving no orphaned/dead symbols (dead-code gate green) and #2511's behavioral test coverage green (adapted to the shared-layer behavior). **Depends on FR-003.** | Draft |
| FR-006 | The lane-recovery branch of `allocate_lane_worktree` (`lanes/worktree_allocator.py` ~:172-184) re-registers the lane sparse-checkout under the fresh-create path's **two** guards (`coordination_branch is not None` AND a resolvable `short_id`/`mid8`) — via a single `_register_sparse_checkout_if_coord` helper both paths call (close-by-construction, not two drifting guard copies) — so a recovered coord-topology lane materializes no `status.events.jsonl` / `status.json` while the non-coord path stays a byte-identical no-op. | Draft |
| FR-007 | The existing cross-platform psutil liveness helper (`sync/daemon._is_process_alive`; handles NoSuchProcess/AccessDenied, never raises) is **promoted to a new low-level module `core/process_liveness.py` (`is_process_alive`)**; `sync/daemon.py` and `core/stale_detection.py` import it from there, and `sync/daemon.py` **keeps re-exporting `_is_process_alive`** (thin alias) so the out-of-scope `dashboard/lifecycle.py` import surface is not broken — exactly one liveness definition, no new `os.kill` parse (C-002), and no `core → sync` layering inversion. The claiming `shell_pid` is read via the existing `task_utils` frontmatter readers; the stale-WP indicator (`core/stale_detection.py`, which today judges staleness on git-commit-timestamp idle) suppresses the "stale" flag when the claiming process is live. | Draft |
| FR-009 | *(regression-guard only — the fix already shipped as #1764.)* A regression test pins that `analysis_report._normalize_tasks_md` continues to strip `[ ]`/`[x]` checkbox state before hashing, on both the write and implement-gate-check paths, so subtask progress ticks do not invalidate the analysis. No new normalization logic is authored. | Draft |
| FR-010 | The rollback-to-`planned` resets (clear `agent`/`shell_pid`; uncheck the WP's subtask rows — both already present in `tasks_move_task.py`) are routed through a single `_mt_reset_for_planned_rollback` seam so "reset on rollback" has one home. No new reset behavior. | Draft |
| FR-011 | `issue-matrix.md` records terminal verdicts: #2504, #2510, #2513 (fixed by the aggregate + WS1/WS3), #2502 (fixed by the aggregate), #2512 (fixed by the aggregate — worktree recovery + rollback marker-clear), #1231 (fixed by FR-007), #1862 (**verified-already-fixed** — #1764, pinned by FR-009), and #2160 (parent, remains open). | Draft |

### Non-Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| NFR-001 | Every functional fix is verified by a focused test driven through the **production** path (the live gate/allocator/indicator entry point), not by a standalone helper that self-validates green. | Draft |
| NFR-002 | Full `tests/architectural/` suite is 0-failed; the existing subtask/status/lane test suites (≥ the 89 aggregated tests) stay green with no correctness regressions. | Draft |
| NFR-003 | All changed code passes `ruff` and `mypy` with zero new issues and zero new suppressions (`# noqa` / `# type: ignore` / per-file ignores). | Draft |
| NFR-004 | The `shell_pid` liveness check never raises on any supported platform when the PID is absent, unparseable, dead, or recycled; an undecidable liveness result is conservative (not-provably-alive). | Draft |
| NFR-005 | The `subtask_rows.py` unification is bite-preserving in the sense that **guard-blocking, dashboard done/total counting, and rollback-uncheck all agree** (not "byte-identical to the aggregate" — the two pre-unify walkers already disagree: the counter `break`s on leaving a section, the uncheck writer re-enters a re-appearing WP heading). WS1 must **choose the guard's section-boundary semantic as canonical** (a re-appearing `## WPnn` heading does NOT re-enter a closed section) and prove it with a fixture battery that includes: a re-appearing WP heading, content after a section ends, nested headings, `depends: WPnn` mentions, fenced blocks, and ids past T999. | Draft |
| NFR-006 | The dead-code gate (`tests/architectural`) is green — the #2511 simplification leaves no orphaned symbols and the new `_walk_wp_section` is exercised through live callers. | Draft |

### Constraints

| ID | Constraint | Status |
|----|-----------|--------|
| C-001 | All work stays on branch `rework/ray-cluster-aggregation`; no new branch is started. | Draft |
| C-002 | Fixes consolidate **onto** the single canonical seam for each concept and introduce no parallel implementation: `core.subtask_rows._walk_wp_section` (row semantics), `resolve_planning_read_dir(..., kind=TASKS_INDEX)` (primary-surface resolution — NOT the local `_planning_read_dir` variants in `orchestrator_api/commands.py` / `acceptance/` / `mission_feature_resolution.py`), `core/process_liveness.is_process_alive` (process liveness — promoted from `sync/daemon._is_process_alive`; exactly one helper, imported by the indicator and the daemon, with `sync/daemon` keeping a re-export alias; no `core → sync` layering inversion), and `task_utils` frontmatter readers (frontmatter fields). | Draft |
| C-003 | `owned_files` are disjoint across WPs; `tasks_move_task.py` and `worktree_allocator.py` each have a single owning WP. | Draft |
| C-004 | No version numbers are prescribed; the PO assigns version and release timing. The unreleased CHANGELOG section is the target for dev-cycle entries. | Draft |
| C-005 | The aggregated cherry-pick commits retain their original (Ray Johnson) authorship; mission commits carry the project's `Co-Authored-By` / `Claude-Session` trailers. | Draft |
| C-006 | The original five PRs (#2503/#2505/#2511/#2514/#2515) are closed-superseded by the operator only **after** this mission's PR merges upstream. | Draft |

## Success Criteria

| ID | Criterion |
|----|-----------|
| SC-001 | On a coordination-topology mission with unchecked subtask rows, a work package cannot be moved to review without explicit override on any command surface (native or orchestrator-api). |
| SC-002 | A work-package subtask row has exactly one definition of "what counts": the guard, the dashboard progress count, and the rollback-uncheck all agree on every fixture in the bite battery. |
| SC-003 | A lane recovered after an interrupted session contains none of the coordination status files; the recovered lane is indistinguishable from a freshly-created one in its sparse-checkout footprint. |
| SC-004 | During active multi-agent orchestration, a work package claimed by a live process is never reported stale by the stale indicator, which consults the one liveness helper. (The allocator makes no claim-staleness decision — see the withdrawn allocator-liveness item in Out of Scope.) |
| SC-005 | Ticking a subtask does not force a re-run of the analysis phase (already true via #1764; pinned by a regression guard). |
| SC-006 | Rolling a WP back to `planned` resets its claim markers and unchecks its subtask rows through one seam, leaving the WP fully re-implementable (no stale `[x]` rows, no dangling claim). |
| SC-007 | The tracker issues reach a terminal verdict — #2502/#2504/#2510/#2512/#2513 + #1231 fixed, #1862 verified-already-fixed — with the parent epic #2160's read/gate arm demonstrably closed. |

## Key Entities

- **Subtask row** — a `- [ ] T### …` / `- [x] T### …` checkbox line in a WP's `tasks.md` section;
  the unit the lane-transition guard blocks on and the dashboard counts.
- **Primary planning surface** — the partition holding `tasks.md`/`spec.md`; the authoritative
  read source for planning artifacts, distinct from the coordination status surface.
- **Lane worktree** — the per-lane execution checkout; on coord topologies its sparse-checkout must
  exclude the coordination status artifacts.
- **Claim markers** — the `agent` / `shell_pid` frontmatter fields recording who holds a WP; their
  liveness governs the stale indicator (the allocator makes no claim-staleness decision).

## Assumptions

- `resolve_planning_read_dir(..., kind=TASKS_INDEX)` is the canonical primary-surface resolver and
  is not itself in scope for change beyond call-site adoption.
- The canonical liveness primitive is `core/process_liveness.is_process_alive` (psutil), promoted
  from `sync/daemon._is_process_alive` to keep `core`/`lanes` off a `sync` dependency; a full
  process-identity (start-time) check to defeat PID recycling is out of scope (conservative
  not-provably-alive is acceptable per NFR-004).
- Checkbox-insensitive analysis freshness already ships (#1764 `_normalize_tasks_md`); this mission
  only pins it with a regression guard, it does not re-implement it.

## Out of Scope

- Any change to the already-resolved #2160 write/validate authority split or its closed children.
- The `_mt_reset_for_planned_rollback` co-location beyond routing existing behavior through one seam
  (no new reset behavior).
- **Re-implementing the analysis-freshness checkbox-insensitivity** — it already ships (#1764). WS5
  as originally scoped is **dropped**; #1862 is closed verified-already-fixed and only a regression
  guard (FR-009) remains. The mission is four workstreams: WS1 (unify `subtask_rows`), WS2 (#2514
  sparse-checkout regression), WS3 (close the emit-layer fail-open), WS4 (#1231 claim liveness).
- Changing the already-correct native `move-task` subtask guard (`tasks_shared`).
- **Allocator-side claim-liveness (withdrawn).** The post-tasks squad verified the lane allocator has
  no stale-claim decision — it branches only on worktree/branch existence and never reads `shell_pid` —
  so the originally-drafted "allocator consults liveness" requirement pointed at nonexistent code and was
  withdrawn. #2512 is closed by the aggregate's worktree recovery + rollback marker-clear (FR-006 /
  FR-010). Liveness has exactly one new consumer: the stale indicator (FR-007). Any genuine
  allocator-side reallocation-on-dead-claim behavior would be a separate, respecced mission.
