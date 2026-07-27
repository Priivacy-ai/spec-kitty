# Implementation Plan: Landing-Pass Campsite Follow-ups

**Branch**: `feat/landing-pass-campsite-followups` | **Date**: 2026-07-16 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/landing-pass-campsite-followups-01KXKWD7/spec.md`

## Summary

Clear the four pre-existing debt items surfaced by the #2670 landing pass so the
shared `main` branch stops going red for process reasons. The technical approach
is settled by the verified pre-spec research (`research-notes-csf-2670.md`) and
the post-spec sizing review: (1) add a per-group opt-in default-shard fallback to
the shard registry so unregistered architectural test files auto-cover without
manual bin-packing edits (Direction A); (2) isolate the bite-battery source
mutation to a tmp copy via a process-local scan-root monkeypatch so parallel
runs stop racing; (3) route the color/synthesis-manifest hygiene fix through the
`CliConsole` deterministic proxy; (4) consolidate sync remediation prose into one
registry the command-name guard scans; (5) fix the type-debt at its shared roots,
decomposed **by file** so the `workflow_executor.py` hotspot stays a single unit.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: pytest, pytest-xdist (`-n auto --dist loadfile`), mypy (--strict), ruff, typer, rich (via `CliConsole`)
**Storage**: N/A (no persistent data; test-infra + CLI internals)
**Testing**: Red-first ATDD per WP; targeted test surfaces (not the full suite) per charter; architectural suite validated under `-n auto --dist loadfile`; `mypy` on in-scope surfaces; each new branch/helper covered by a focused test in the same WP
**Target Platform**: Cross-platform developer CLI + CI (Linux/macOS/Windows)
**Project Type**: single (CLI library `src/specify_cli/` + `src/charter/` + test infrastructure `tests/`)
**Performance Goals**: N/A — this mission reduces CI friction; it introduces no runtime hot path and must not regress CLI startup
**Constraints**: fix-the-code-not-suppress (no new `# type: ignore`/`# noqa`); the #2671 fallback is additive (manual bin-packing preserved as override); the bite-battery must still exercise the real detector; no version numbers in scope; proceeds in parallel with the in-flight #2651/S0 resolver-seam mission
**Scale/Scope**: 4 workstreams → ~6 work packages across ~10 files; two rigour tiers (mechanical burn-down + one topology decision)

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Charter rule | Applies | Status |
|--------------|---------|--------|
| Canonical sources & unification (single authority) | #2674 remediation registry; #2671 registry seam | ✅ Each fix collapses to one authority, not parity patches |
| Fix-not-suppress (C-001, NFR-004) | #2675 type-debt | ✅ Root-boundary fixes; zero new suppressions |
| Red-first ATDD (C-005, C-011) | all WPs | ✅ Each WP reproduces its failure through the pre-existing entry point first |
| Architectural gate discipline (non-vacuous) | #2671 keeps the GC-1 union invariant as the fallback's correctness net | ✅ No gate weakened; only the manual-registration RED becomes unreachable for arch files |
| Terminology canon (Mission not Feature) | prose/docs | ✅ No `feature*` introduced |
| Tiered rigour (core vs glue) | #2675 lane-reader/enum change is core; casts are glue | ✅ Sentinel promotion gets a real caller-impact check; casts are mechanical |
| PRs only, operator merges (DIRECTIVE_045) | landing | ✅ Draft PR to upstream; operator merges |
| No version numbers in scope (C-007) | — | ✅ None assigned |

No unjustified violations → Complexity Tracking is empty.

## Project Structure

### Documentation (this mission)

```
kitty-specs/landing-pass-campsite-followups-01KXKWD7/
├── plan.md              # This file
├── research.md          # Phase 0 — decision consolidation (points to research-notes-csf-2670.md)
├── data-model.md        # Phase 1 — the small structural entities this mission adds/changes
├── quickstart.md        # Phase 1 — how to verify each workstream
└── tasks.md             # Phase 2 (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)

```
tests/
├── _shard_registry.py                      # IC-01: add opt-in default-fallback branch in shard_for()
├── _arch_shard_map.py                      # IC-01: opt-in flag on the arch ShardGroup + doctrine-header rewrite (FR-011)
└── architectural/
    ├── test_single_mission_surface_resolver.py   # IC-02: isolate _SourceMutation (S0-contended)
    ├── test_surface_resolution_audit.py          # IC-02: second scanner (#2638) — immune once mutation isolated
    ├── untrusted_path_audit/audit.py             # IC-02: (optional) test-support root param, else monkeypatch SRC_ROOT
    └── <color/synthesis hygiene test>            # IC-03: #2672

src/specify_cli/
├── cli/console.py                          # IC-03: CliConsole deterministic seam (#2672)
├── sync/preflight.py                       # IC-04: remediation registry + guard target (#2674)
├── status/lane_reader.py                   # IC-05: promote legacy sentinel to a Lane member (#2675 cluster 1 root)
├── status/status_transition.py             # IC-05: local Optional narrowing (:854)
├── cli/commands/agent/workflow_executor.py # IC-05: str→Lane (4) + no-any-return (2) + Optional (668/873) — ONE unit
├── missions/plan/specify_interview.py      # IC-06: decision_id narrowing via shared helper
├── missions/plan/plan_interview.py         # IC-06: same shared helper (de-dup)
├── missions/plan/widen/interview_helpers.py# IC-06: consolidated narrow-once seam
├── missions/_read_path_resolver.py         # IC-06: mechanical cast drop
├── status/emit.py                          # IC-06: mechanical cast drop
└── upgrade/migrations/m_2_1_4_enforce_command_file_state.py  # IC-06: mechanical cast drop

tests/specify_cli/sync/test_preflight_remediation_hints.py    # IC-04: widen guard to the registry
```

**Structure Decision**: Single project; no new top-level directories. Changes
split between test infrastructure (`tests/_*`, `tests/architectural/`) and CLI
internals (`src/specify_cli/`, `src/charter/` deferred). The
`charter/mission_type_profiles.py` casts are **out of scope** (owned by the
in-flight mission-type work).

## Complexity Tracking

*No Charter Check violations — section intentionally empty.*

## Implementation Concern Map

> Concerns are NOT work packages. `/spec-kitty.tasks` translates these into WPs.
> The by-file grouping in IC-05 is load-bearing (see Risks) and should survive
> into the WP decomposition.

### IC-01 — Shard-registry default fallback + doctrine header (#2671)

- **Purpose**: Stop `main` going red when a contributor adds a
  `tests/architectural/*.py` file without hand-editing the shard table, by
  auto-assigning unregistered arch files to one shard via a deterministic
  hash-bucket fallback — while keeping explicit entries and the union invariant.
- **Relevant requirements**: FR-001, FR-002, FR-003, FR-004, FR-011, NFR-001, NFR-006, C-002, C-008.
- **Affected surfaces**: `tests/_shard_registry.py` (new optional `ShardGroup`
  field + fallback branch in `shard_for()`), `tests/_arch_shard_map.py` (opt-in
  flag on the arch row + doctrine-header rewrite), a new red-first registry unit
  test.
- **Sequencing/depends-on**: none — but **land first**: it is a soft enabler for
  any later WP that adds an arch test file, and de-frictions the in-flight
  #2651/S0 missions hitting the same gap.
- **Risks**: shared seam consumed by both `arch` and `next` groups → per-group
  opt-in bounds blast radius (the `next` row must keep returning `None` for
  unregistered files). The fallback **must gate on group-root membership** (only
  files under the group's roots get a fallback shard — never a stray non-arch
  file). Use hash-modulo (not "lightest") to avoid pile-on; keep the GC-1 union
  invariant as the correctness net. `_arch_shard_map.py` is cross-mission
  contended — the just-shipped #2666/#2668 mission added *yet another* manual
  registration append (`27eed6c9f`), which is the recurrence this WP eliminates.

### IC-02 — Bite-battery mutation isolation (#2673 + #2638)

- **Purpose**: Remove the shared-mutable-real-file hazard so a concurrent
  scanner can never read `core/mission_creation.py` mid-mutation; both scanner
  victims (#2673 and #2638) are fixed by the one isolation change.
- **Relevant requirements**: FR-005, FR-006, NFR-002, C-003, C-006.
- **Affected surfaces**: `tests/architectural/test_single_mission_surface_resolver.py`
  (`_SourceMutation` → isolate to tmp copy + process-local monkeypatch of
  `audit.SRC_ROOT`), `tests/architectural/test_surface_resolution_audit.py`
  (verified immune), optionally an added test-support `root` param in
  `tests/architectural/untrusted_path_audit/audit.py`.
- **Sequencing/depends-on**: none.
- **Risks**: 🔴 **SHARP cross-mission contention** — this file (~1372 LOC) is the
  #2651/S0 resolver-seam mission's primary, still-growing test surface, and the
  fix edits the mid-file (~line 822) high-churn zone. Per C-006 this WP must land
  in a **quiescent window** of that mission or be **folded into its lane**; do
  not budget a free rebase. Must preserve what the bite-battery proves (real
  detector code path, root-agnostic).

### IC-03 — Color/synthesis-manifest hygiene via CliConsole (#2672)

- **Purpose**: Make the ANSI/synthesis-manifest test deterministic without
  mutating a real repo file or ambient color env, by routing through the
  `CliConsole` proxy (determinism is a property of the object).
- **Relevant requirements**: FR-007, C-004.
- **Affected surfaces**: the affected color/synthesis-manifest test + its use of
  `src/specify_cli/cli/console.py` (`CliConsole`).
- **Sequencing/depends-on**: none. Disjoint from IC-02 (different mechanism).
- **Risks**: confirm the exact failing test + that `CliConsole` covers its output
  path during implementation.

### IC-04 — Sync remediation registry + guard (#2674)

- **Purpose**: Single-source every remediation sentence and point the
  command-name guard at the full registry so inline commands (`sync migrate`,
  `orphan-daemons`, `auth login`) are validated to resolve, closing the
  duplication and the coverage gap together.
- **Relevant requirements**: FR-008, FR-009.
- **Affected surfaces**: `src/specify_cli/sync/preflight.py` (hoist remedy prose
  to constants; expose an `ALL_REMEDIATION_TEXTS` registry; both the dict and the
  inline builder reference it), `tests/specify_cli/sync/test_preflight_remediation_hints.py`
  (widen the guard iterators to the registry).
- **Sequencing/depends-on**: none.
- **Risks**: whack-a-field trap — hoisting the two duplicated literals without
  widening the guard leaves the inline commands unvalidated; the WP is incomplete
  unless the guard scans the registry. Output must stay byte-identical.

### IC-05 — Lane sentinel unification + workflow_executor type-debt (#2675 clusters 1, 2, 4)

- **Purpose**: Retire the `Lane | str` union at its source by promoting the
  legacy read sentinel to a **new canonical `Lane.UNINITIALIZED` member** (operator
  decision: full unification, not a pragmatic call-site coerce), so `get_wp_lane`
  returns a pure `Lane`; then clear the dependent `workflow_executor.py` errors.
- **Decision (resolves the data-model/research contradiction)**: add a NEW member
  `Lane.UNINITIALIZED = "uninitialized"` — **do NOT reuse `Lane.GENESIS`**. The
  two states are semantically distinct: `get_wp_lane` returns the sentinel when a
  WP is *absent from the snapshot* (empty event log, or WP not present), whereas
  `GENESIS` is a WP that *is* seeded but carries no explicit lane
  (`lane_reader.py:72` `wp_state.get("lane", Lane.GENESIS)`). Reusing `GENESIS`
  would conflate them and regress `worktree_topology` (unseeded→"planned") and
  `merge/done_bookkeeping` (done-detection). The StrEnum value stays
  `"uninitialized"`, so existing `== "uninitialized"` equality via StrEnum holds.
- **Relevant requirements**: FR-010 (clusters 1/2/4), NFR-003, NFR-004, NFR-005, C-001.
- **Affected surfaces (full enumerated blast radius — verified)**:
  - `src/specify_cli/status/models.py` — add `Lane.UNINITIALIZED` (a *non-display,
    non-transitionable* read sentinel; document it like GENESIS).
  - `src/specify_cli/status/lane_reader.py` — `get_wp_lane` returns
    `Lane.UNINITIALIZED`; `get_all_wp_lanes` annotation → `dict[str, Lane]`.
  - `src/specify_cli/status/wp_state.py` — add a **dedicated `UninitializedState`
    with empty `allowed_targets()`** (NOT a `GenesisState` alias, which would
    inject transition edges → break the ==29 count and make the sentinel
    transitionable) and register it in `_STATE_MAP`/`_FACTORY_ALIASES`, else
    `transitions.py:44` (`for lane in Lane: wp_state_for(lane)`) **crashes at import**.
  - `src/specify_cli/status_lanes.py` (`CANONICAL_LANES`) — exempt UNINITIALIZED
    from the parity check like genesis (do not add to the tuple).
  - `src/specify_cli/status/lifecycle.py:119` — a FIFTH display-summary site with
    no genesis filter; route through the canonical non-display-lane authority.
  - ~12 pre-existing lane-roster tests (`tests/status/`, `tests/specify_cli/status/`,
    `tests/specify_cli/cli/commands/agent/`, `tests/integration/test_dashboard_counters.py`,
    `tests/test_dashboard/test_scanner.py`) derive "all non-genesis lanes" and must
    also exclude UNINITIALIZED — WP05's GREEN gate must RUN these dirs (not just
    `tests/specify_cli/status/`) to avoid false-green.
  - Display filters that exclude GENESIS must also exclude UNINITIALIZED:
    `status/reducer.py:134,166`, `status/wp_metadata.py:385`,
    `cli/commands/agent/tasks_status_view.py:163`, `status/lifecycle.py:119`.
  - `src/specify_cli/merge/done_bookkeeping.py:149-160,373-378` — `Lane("uninitialized")`
    now succeeds (no `ValueError`); treat `Lane.UNINITIALIZED` explicitly as
    not-done so the current except-branch behavior is preserved.
  - `src/specify_cli/core/worktree_topology.py:81` — compare to `Lane.UNINITIALIZED`
    (still map to "planned").
  - `src/specify_cli/status/aggregate.py:691`, `src/specify_cli/coordination/status_transition.py:558,564`
    — sentinel consumers.
  - `src/specify_cli/workspace/context.py:497,513` — `.get(wp_id, "uninitialized")`
    str default vs a now-`dict[str, Lane]`; may surface a *new* mypy diagnostic —
    fix in-WP.
  - `src/specify_cli/cli/commands/agent/workflow_executor.py` — the 4 str→Lane
    errors clear once the loader returns pure `Lane`; plus a typed `_locate_wp`
    wrapper (no-any-return ×2) and the independent Optional narrowings at 668/873.
  - `src/specify_cli/coordination/status_transition.py` (the real file; the
    `StatusEvent | None` narrowing is here, **not** at the plan's earlier
    `status/status_transition.py:854` — that path does not exist).
  - `src/specify_cli/dashboard/scanner.py:623,633,914-918` — already defensive
    (accepts `{GENESIS, "genesis", "uninitialized"}`); verify still correct.
- **Behavior tests (required, type-invisible regressions)**: pin the unseeded
  path — WP absent from snapshot → `worktree_topology` "planned",
  `done_bookkeeping` "not done", and both display filters exclude UNINITIALIZED.
  Every downstream consumer already `str(...)`-coerces, so mypy alone will NOT
  catch a regression here.
- **Sequencing/depends-on**: none across other ICs. **Internal order**: enum +
  `_STATE_MAP` + loader land first; consumers + workflow_executor after.
- **Risks**: 🔴 This is the mission's **heaviest** WP and is no longer "mechanical"
  — it touches the lane state-machine, display, and merge bookkeeping. At /tasks
  it may split into (a) enum+loader+FSM core and (b) consumer updates, but **all
  `workflow_executor.py` edits stay in one WP/lane** (it carries three clusters;
  a by-error-category split manufactures a parallel-lane collision). `workflow_executor.py`
  is a 1855-LOC god-surface — deliberately **not** campsite-extracted here
  (extraction mid-type-fix would explode the diff and collide with the very lanes
  this consolidation protects; recorded per DIRECTIVE_025 as an explicit no-extract
  call, not an oversight).

### IC-06 — Type-debt disjoint: interview helper + mechanical casts (#2675 cluster 3 + in-scope casts)

- **Purpose**: De-duplicate the byte-identical `decision_id` interview block into
  the shared helper and narrow once; drop the three in-scope redundant casts.
- **Relevant requirements**: FR-010 (cluster 3 + mechanical casts), NFR-003, NFR-005, C-001.
- **Affected surfaces**: `src/specify_cli/missions/plan/specify_interview.py:181`,
  `.../plan_interview.py:181`, and the **existing** canonical seam
  `src/specify_cli/widen/interview_helpers.py` (`render_already_widened_prompt` at
  :224; both interviews already import it at line 110 — this WP EDITS it to add the
  narrow-once consolidation, it does NOT create a new file); plus the three in-scope
  redundant-cast drops: `src/specify_cli/missions/_read_path_resolver.py:1473`,
  `src/specify_cli/status/emit.py:302`,
  `src/specify_cli/upgrade/migrations/m_2_1_4_enforce_command_file_state.py:78`.
- **Sequencing/depends-on**: none. Disjoint file set from IC-05 → safe parallel lane.
- **Risks**: (a) the casts are **config-verified, not blindly mechanical**: the
  `_read_path_resolver.py:1473` and `emit.py:302` casts carry inline rationale
  comments tying them to `pyproject.toml [[tool.mypy.overrides]] follow_imports=skip`.
  Reproduce the `redundant-cast` verdict under the **canonical** mypy invocation
  before dropping (a different config can flip `redundant-cast`→`no-any-return`),
  and **delete the now-stale rationale comment together with the cast**.
  (b) soft adjacency — the interview files and `_read_path_resolver.py` sit on the
  actively-churned read-surface/resolver family (recent #2574/#2173 touches);
  quick `git log` check before consolidating the shared helper.
  `charter/mission_type_profiles.py` casts are **excluded** here (owned by the
  shipped mission-type work).

### Cross-cutting deliverable

- **SC-006**: file a tracked follow-up issue for the remaining 6 un-migrated
  real-file mutation sites (hazard class beyond IC-02). These are all in **one
  file** — `tests/architectural/test_single_mission_surface_resolver.py`
  (`_SourceMutation` calls at `:788,:900,:1032,:1087,:1293` + `_SourceInsertion`
  at `:714`; the #2673 target is `:745`) — so the follow-up is a bounded
  single-file migration, not a codebase hunt. Mission output, not code — assign
  to a WP closeout or mission wrap-up.

## Phase 0 / Phase 1 outputs

- `research.md` — consolidates the settled decisions (Direction A, isolation
  Option (i), CliConsole seam, remediation registry, 6-root type fixes) and
  points to the full verified `research-notes-csf-2670.md`.
- `data-model.md` — the small structural entities changed: the `ShardGroup`
  opt-in field, the `Lane` sentinel member, and the remediation registry.
- `quickstart.md` — per-workstream verification recipe.
- `contracts/` — **N/A**: this mission changes no external API, route, or wire
  payload (CLI-internal + test-infra only). Recorded here so its absence is
  intentional, not an omission.

## Branch contract

- **Current branch**: `feat/landing-pass-campsite-followups`
- **Planning/base branch**: `feat/landing-pass-campsite-followups`
- **Final merge target**: `feat/landing-pass-campsite-followups` (then rebased
  onto `upstream/main` for a draft PR at mission wrap-up; the operator merges).
- `branch_matches_target`: true.
