# Plan Review — python-pedro (Implementation Feasibility)

**Mission**: tooling-stability-guard-coherence-01KTRC04
**Date**: 2026-06-10
**Reviewer lens**: IMPLEMENTATION FEASIBILITY — will implement these WPs
**Verdict**: **GREEN with one hard flag (IC-04) and one sizing flag (IC-02)**

---

## Overall Assessment

The spec + plan are concrete, well-anchored to live code, and the ICs are
correctly sequenced. The ATDD-first ordering (IC-01 → IC-02 spine → IC-03/04 →
closures) is implementable. Three items need precise sizing decisions before
`/spec-kitty.tasks` runs.

---

## Per-IC Feasibility

### IC-01 — Protection-preserved negative suite
**Feasible, LOW risk.**
The guard path is fully in `git/commit_helpers.py:978-991`. Tests can exercise
the live path using `tmp_path` git repos. No mocking needed. The `#1334` repro
is a `(tmp_repo, message="release: …", protected_branch)` → `ProtectedBranchRefused`
assertion — literal 10-line test. Confirmed: `_is_protected_branch_exception` at
`:466` is the live bypass we must ratchet against.

**One WP.** Output: 3–5 test functions, all RED before IC-02 conversion.

---

### IC-02 — Guard spine: caller census + CommitTarget + SK policy module
**Feasible. LARGEST blast radius. 4 genuinely awkward callers.**

The research.md count of ~15 is confirmed at 17 call-sites across 18 files
(including `commit_helpers.py` itself). Breakdown by conversion complexity:

**Mechanical (pair → CommitTarget, no context gap):**
| File | Call-site | Notes |
|------|-----------|-------|
| `coordination/transaction.py:1002` | `destination_ref` already a string param on the `AtomicTransaction` | Wrap: `CommitTarget(ref=self.destination_ref, kind=<from topology field>)` |
| `invocation/executor.py:442` | passes explicit `destination_ref` | same |
| `cli/commands/merge.py:2322` | `destination_ref` from lane metadata | same |
| `cli/commands/implement.py:1136,2284,2921,3697` | 3 call sites all pass explicit `destination_ref` from the resolved workspace | mechanical |
| `cli/commands/accept.py` | uses `assert_not_protected_branch` only, no `safe_commit` | convert to `GuardCapability(kind=standard)` guard |
| `cli/commands/agent/tasks.py:2284,2921,3697` | explicit `destination_ref` from context | mechanical |
| `cli/commands/agent/workflow.py:409,530,1470` | `destination_ref` passed through explicitly | mechanical |
| `orchestrator_api/commands.py:1077` | explicit `destination_ref` | mechanical |

**Awkward callers — CommitTarget not naturally resolvable:**

1. **`cli/commands/upgrade.py:201`** — `destination_ref` is inferred at
   call-time by reading `git symbolic-ref HEAD` (lines 193–196); there is no
   `MissionExecutionContext` at all. The upgrade flow is the canonical
   `upgrade_bookkeeping` capability case. Conversion: pass
   `CommitTarget(ref=destination_ref, kind=CommitTargetKind.FLATTENED)` +
   `GuardCapability(kind=upgrade_bookkeeping)`. The topology kind is opaque here
   (upgrade runs on whatever branch the consumer is on), so `FLATTENED` is the
   safe fallback. **Must flag this as an explicit design decision in WP.**

2. **`events/decision_log.py:193` (via `runtime/next/runtime_bridge.py:181`)**
   — `DecisionGitLog` holds a raw `destination_ref: str` injected at
   construction from the bridge. No `CommitTarget` flows in. Two options:
   (a) change `DecisionGitLog.__init__` to accept `CommitTarget` and update the
   one instantiation site (`runtime_bridge.py:181`); or
   (b) build `CommitTarget` inside `_trigger_commit` from the stored `str`. The
   runtime-bridge caller knows the topology (it builds the context), so option (a)
   is cleaner but requires a cross-boundary change (runtime_bridge → specify_cli
   API change). **Flag for WP as design decision.**

3. **`core/mission_creation.py:178`** — uses `destination_ref=current_branch`
   where `current_branch` is read from git at call time. This commit is for
   planning artifact creation (before lanes), so the relevant capability is
   `standard` and the ref is whatever branch is currently checked out. Under
   the new model this is an `ArtifactPlacementFragment` scenario, but at
   `mission create` time no `MissionExecutionContext` exists yet (pre-spec).
   Conversion: `CommitTarget(ref=current_branch, kind=FLATTENED)` +
   `GuardCapability(kind=standard)`. **Low risk, just flag it.**

4. **`cli/commands/agent/mission.py:770` (record-analysis) and
   `:1789/:1826/:3165` (setup-plan/finalize-tasks)** — these already have
   partial `CommitTarget` threading (the `record-analysis` path has
   `_resolve_record_analysis_placement_ref` at `:492`). The setup-plan path at
   `:1723` calls `_commit_to_branch` which uses `destination_ref=current_branch`
   — **this is IC-04's primary target**, not purely IC-02. Split here: IC-02
   converts the guard mechanics; IC-04 threads the placement for these paths.

**Capability assertion sites for the 3 legacy prefix flows:**
| Flow | Current bypass | Where capability is asserted |
|------|---------------|------------------------------|
| `upgrade` | `"chore: apply spec-kitty upgrade changes"` prefix | `upgrade.py:201` — the one caller; capability declared here |
| `merge bookkeeping` | `"chore(<mission>): record done transitions …"` prefix | `merge.py:2322` — the bookkeeping commit; capability declared at the call site |
| `release` | `"chore: release "` + `"release: "` prefix | Not found as a `safe_commit` call in `specify_cli` — release commits appear to be outside this codebase (external release workflows). If there is no internal caller, the release prefixes in `_PROTECTED_BRANCH_COMMIT_EXCEPTIONS` may be dead code. **Flag for census step.** |

**WP sizing**: IC-02 is large but parallelizable after the policy module lands.
Recommend splitting into **2 WPs**: IC-02a (create `core/commit_guard.py` + convert
the 11 mechanical callers) and IC-02b (convert the 4 awkward callers + delete
`_is_protected_branch_exception`). IC-02b depends on IC-02a and IC-01.

---

### IC-03 — safe-commit ergonomics (dir/bulk, --to-branch)
**Feasible, LOW risk.**
`safe_commit_cmd.py:133–188` is self-contained (63 LOC). The `SPEC_KITTY_INFER_ENV`
path is already present — fix is replacing the "No requested changes" gate logic at
`:163`. Directory expansion is new logic (~20 LOC). Depends on IC-02 (CommitTarget
in place). **One WP.**

---

### IC-04 — Planning-phase placement threading (catch-22 killer)
**Feasible but HARD. Two distinct code surfaces; one is pre-lanes with no context.**

**Root cause confirmed from code:**
- `_commit_to_branch` at `:741–790` uses `destination_ref=current_branch` (git
  HEAD at call time, not resolved placement). On a protected-main repo, HEAD IS
  `main` → `ProtectedBranchRefused`. There is no `ArtifactPlacementFragment` in
  scope because `setup-plan` and `finalize-tasks` run pre-lanes.
- `finalize-tasks` at `:3138–3172` has a hand-rolled coord worktree resolution
  (`:3144–3163`) that duplicates placement logic. This is the bug IC-04 kills.

**The `ArtifactPlacementFragment` resolvability question:**
`ArtifactPlacementFragment` is only attached to `ExecutionContext` when
`resolve_action_context` builds it (via `mission_runtime/resolution.py:383`).
`setup-plan` and `finalize-tasks` currently do NOT call `resolve_action_context`
— they use ad-hoc `_resolve_planning_branch()`/`_show_branch_context()`. So
`ArtifactPlacementFragment` is **not resolvable at these points** without first
wiring these commands through `resolve_action_context`.

**Options:**
a) Wire `setup-plan`/`finalize-tasks` through `resolve_action_context` to get a
   full context (correct, non-trivial — may require mission_id to exist in
   meta.json, which it should at this stage).
b) Introduce a lightweight `resolve_placement_only(repo_root, mission_slug)` that
   reads `meta.json` + topology + returns an `ArtifactPlacementFragment` without
   building a full context — smaller blast radius.

**Recommendation**: Option (b) for the IC-04 WP; defer full context threading to
a follow-up. This keeps IC-04 scoped to the catch-22 fix without requiring all of
setup-plan to be context-aware. **Flag as explicit design decision in WP.**

**IC-04 is likely 2 subtasks beyond a single WP** (or a complex 8+ subtask WP):
the `_commit_to_branch` fix + the `finalize-tasks` coord-worktree dedup + the
guard refusal message update + the `#1784` e2e test. Still one WP if subtasks are
well-scoped.

---

### IC-05 — Structured findings carrier + verdict derivation
**Feasible, INDEPENDENT, LOW risk.**
`analysis_report.py` (313 LOC) is self-contained. `write_analysis_report` already
writes frontmatter (`:211–224`) — adding the `analysis-findings/v1` block is
additive. `infer_verdict` (`:173–183`) and `infer_issue_counts` (`:157–170`) are
deleted after cutover; the one caller is `write_analysis_report` itself.

**Migration story**: `write_analysis_report` is the write path (agent provides
body; recorder writes frontmatter). The agent-facing template needs updating
so agents emit the `analysis-findings/v1` block in the report body for the
recorder to parse — OR the recorder computes it independently. The plan says
"recorder validates; analyze template updated." Code confirms `write_analysis_report`
is the recorder entry point and agents pass the full body text. The schema
validation at read time (`check_analysis_report_current` at `:237`) already reads
frontmatter. **One WP, ~150 LOC change.**

The legacy fallback (`verdict: unknown` for pre-v1 reports) is straightforward:
check for `schema: analysis-findings/v1` in frontmatter; if absent, emit
`verdict: unknown`.

---

### IC-06 — StatusSurfaceFragment threading
**Feasible, LOW risk, SMALLEST IC.**
`MissionStatus.load` at `:186–268` re-derives the coord path inline. The
`StatusSurfaceFragment` is built by `mission_runtime/resolution.py:438` but not
yet consumed by `MissionStatus.load` (load takes `repo_root, mission_slug` only —
no context parameter). Threading requires adding a `surface: StatusSurfaceFragment | None`
param and short-circuiting the coord-path derivation when it is non-None.

No callers of `MissionStatus.load` currently pass a fragment (fragment is None
everywhere it is read). IC-06 must identify which callers CAN supply the fragment
(those that already have a resolved context) vs. which genuinely cannot (legacy
non-context paths). The parity-ratchet extension is 5–10 LOC.

**One WP, ~80 LOC change.**

---

### IC-07 — doctor.py health-render extraction
**Feasible, LOW risk, MECHANICAL.**
The extraction target is 292 LOC (`:2082–2374`), 9 functions:
`_render_pack_invalid_profiles`, `_render_doctrine_pack`, `_collect_profile_health`,
`_attach_pack_health`, `_emit_doctrine_human`, `_emit_doctrine_json`,
`_emit_doctrine_no_packs`, `_build_pack_entries`, and `doctrine_check`.

`doctor.py` already imports `_doctrine_health` from the same directory (`:33`).
Pure extraction: new file `_profile_health_render.py`, repoint 9 function
definitions + update `doctor.py` imports. Zero logic change.
**C-DOC-1** (golden/snapshot check) can be a pytest parameterized fixture against
the pre-extraction output. **One WP, ~0 net LOC change (move, not rewrite).**

---

### IC-08 — DRG Provenanced[T] + consumer migration
**Feasible. Consumer inventory is SMALLER than feared.**

Actual `getattr(node, "provenance", None)` call sites confirmed:
1. `doctrine/drg/merge.py:480` — internal, in the conflict-warn path
2. `glossary/entity_pages.py:164` — reads for display rendering

Code confirms: **2 active consumer call sites, plus docstrings and comments**.
The `charter/drg.py` docstring references the pattern but has no actual call site
in the charter layer for this specific sidecar (the charter provenance
references are for a different `.provenance` concept in `synthesizer/`).

3-layer inventory:
- **doctrine layer** (`doctrine/drg/merge.py`): producer (`_tag_source`) + 1 consumer
- **specify_cli layer** (`glossary/entity_pages.py:164`): 1 consumer
- **charter layer**: 0 active call sites (only docs)

This is NOT the 3-layer ripple the spec warns about — the actual migration is
6–8 LOC in 2 files plus the `_tag_source` rework. The `Provenanced[T]` wrapper
(~15 LOC dataclass) replaces the `object.__setattr__` at `:219`, and consumers
change from `getattr(node, "provenance", None)` to `node.provenance` (typed).

**Recommendation**: Inventory-first as the IC specifies is correct; the STOP-and-
escalate guardrail is right but the risk is low given the actual consumer count.
**One WP, ~50–80 LOC change including tests.**

---

### IC-09 — Spine closure: import ratchet + ADR addendum
**Feasible, TRIVIAL.**
The ratchet (`test_safe_commit_import_boundary`) is existing infra — tighten the
allowed-importer list once IC-02 callers are converted. ADR addendum is prose.
**One WP, <30 LOC.**

---

### IC-10 — Deep review / sign-off
**Not a code WP.** Architect-alphonso review task only.

---

## WP Decomposition Proposal

Recommended cut: **9 implementation WPs + 1 review WP = 10 WPs total**

| WP | IC(s) | Content | Subtasks | Deps |
|----|-------|---------|----------|------|
| WP01 | IC-01 | Protection-preserved negative suite (ATDD-first) | 4 | — |
| WP02 | IC-02a | `core/commit_guard.py` policy module + 11 mechanical caller conversions | 8 | WP01 |
| WP03 | IC-02b | 4 awkward callers (upgrade/decision_log/mission_creation/agent-mission) + delete `_is_protected_branch_exception` | 6 | WP02 |
| WP04 | IC-03 | safe-commit ergonomics (dir/bulk, `--to-branch`, INFER misfire fix) | 4 | WP02 |
| WP05 | IC-04 | Planning-phase placement threading (catch-22 killer): `_commit_to_branch` fix + finalize-tasks dedup + guard messages + SC-6 e2e | 6 | WP02 |
| WP06 | IC-05 | `analysis-findings/v1` frontmatter schema + verdict-from-structure + delete substring logic + template update | 5 | — |
| WP07 | IC-06 | `StatusSurfaceFragment` threading in `MissionStatus.load` + parity ratchet extension | 3 | — |
| WP08 | IC-07 | `doctor.py` health-render extraction to `_profile_health_render.py` (pure move, snapshot check) | 3 | — |
| WP09 | IC-08 | `Provenanced[T]` wrapper + `_tag_source` rework + 2-consumer migration + mypy clean | 5 | — |
| WP10 | IC-09/IC-10 | Import-boundary ratchet tighten + ADR addendum + architect-alphonso sign-off | 3 | WP03, WP05 |

WP06–WP09 are independent lanes (no deps on spine WPs); can parallelize with
WP02 or run before/after. Total subtask estimate: ~47 subtasks. No single WP
exceeds 8 subtasks.

---

## Flags for Tasks Phase

1. **IC-02 / WP03 — release prefix fate**: the `"chore: release "` and
   `"release: "` prefixes in `_PROTECTED_BRANCH_COMMIT_EXCEPTIONS` have no
   matching `safe_commit` call site in `specify_cli` (release appears external).
   During the census step, confirm whether these prefixes are dead or whether
   the release workflow calls `safe_commit` from outside this repo. If dead:
   delete without replacement. If alive: expose `GuardCapability(kind=release_flow)`
   and document the external caller.

2. **IC-04 / WP05 — `ArtifactPlacementFragment` resolution**: `setup-plan` and
   `finalize-tasks` do NOT currently go through `resolve_action_context`. Recommend
   option (b): lightweight `resolve_placement_only(repo_root, mission_slug)` in
   `mission_runtime.resolution` rather than full context threading. This scopes WP05
   to the catch-22 fix and avoids pulling all of setup-plan into the context model
   in one shot.

3. **IC-02 / WP02-03 — `upgrade.py` CommitTarget topology**: `FLATTENED` is the
   correct default when topology is unknown (upgrade runs on arbitrary branches).
   Confirm this is acceptable in the policy module design before WP02 lands.

4. **IC-08 / WP09 — consumer count confirmed low**: the plan warns of "3-layer
   ripple" but actual getattr call sites are 2 (merge.py internal + entity_pages.py).
   Charter layer has no active call sites for this sidecar. WP09 is smaller than
   the spec implies; no escalation expected.
