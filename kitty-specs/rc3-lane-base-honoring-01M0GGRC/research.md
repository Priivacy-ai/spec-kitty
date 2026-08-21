# Phase 0 Research: Lane base honoring (M1, P0)

No open `[NEEDS CLARIFICATION]` markers — operator decisions D1/D2/D3 are locked and the
post-spec squad resolved the design tensions. This document records the grounded decisions.

## Decision 1 — Where to thread `base` (single write authority)

**Decision**: Thread `base: str | None = None` from the CLI seam through `create_lane_workspace`
into the topology-aware `allocate_lane_worktree`; drop the `mission_branch=base` smuggle in
`_resolve_active_lanes_manifest`.
**Rationale**: `allocate_lane_worktree` is the one place that already discriminates coord vs legacy
(`_read_coordination_branch`). Routing base there lets a single authority honor base on BOTH routes;
the seam stays topology-blind and simple. Removing the smuggle eliminates the divergent second source
that caused #3571 (write to `mission_branch`, read from `coordination_branch`).
**Alternatives considered**: (a) make `_resolve_active_lanes_manifest` topology-aware and keep patching
`mission_branch` for legacy only — rejected: pushes topology discovery into the seam and keeps the
smuggle alive on one route (split authority persists). (b) layer base on top of `coordination_branch` —
rejected: violates operator decision D1 (base fully replaces the coord parent).

## Decision 2 — Caller enumeration (C-001, authoritative)

**Production callers of `allocate_lane_worktree` (2):**
- `src/specify_cli/lanes/implement_support.py:92` (`create_lane_workspace`) — the `implement --base` path.
- `src/specify_cli/orchestrator_api/commands.py:903` (`_resolve_start_workspace`) — passes `base=None`, inert.

**Provenance consumers inside `create_lane_workspace`** (must consume threaded `base` when supplied):
`implement_support.py:112` (`_has_commits_beyond_base` reuse detection), `:117` (`base_branch`),
`:130` (`base_commit`), `:138-139` (frontmatter), `:156-157` (`WorkspaceContext`), `:174`
(`LaneWorkspaceResult.mission_branch`).

**~30 test call sites** all use the existing 4-arg form → the new param MUST be defaulted (`= None`,
NFR-005) so they stay green without edits.

## Decision 3 — FR-010: detached base vs planning commit ⇒ fail loud

**Decision**: When `<base>` shares no common ancestor with the recorded planning commit, hard-error with
a typed message. Do NOT `--allow-unrelated-histories`; do NOT leak a raw `PlanningCommitMergeConflictError`.
**Rationale**: silently minting an unrelated-histories merge fabricates a lineage the operator did not ask
for — the same class of "silently did something other than intent" harm this P0 kills. Fail-loud is
consistent with D2/D3.
**Alternatives**: skip the planning-commit merge when base supplied (rejected — the lane needs the mission
spec/tasks artifacts to function); `--allow-unrelated-histories` (rejected — fabricates lineage).

## Decision 4 — C-004: for_review gate reads the actual honored base (in-scope M1 fix)

**Decision (operator ruling 2026-08-21, via AskUserQuestion)**: M1 fixes `for_review_gate` to measure
against the lane's **actual honored base** (FR-011), not a hardcoded coordination branch.
**Operator principle (verbatim intent)**: *the coordination branch is itself a perfectly valid `--base`
value; explicit-base and coord-as-base are not contradictory — this is about opening the mechanics so the
gate measures against whatever the lane was actually parented on.*
**Mechanics**: the recorded `base_branch` provenance becomes the SSOT for "the ref the lane was parented
on" — `base` when `--base` supplied, else the topology parent the allocator used (`coordination_branch`
for coord, `mission_branch` for legacy). `resolve_lane_base_ref` prefers that recorded honored base.
**Verified subtlety**: today `base_branch` frontmatter = `mission_branch_name(...)` which can DIFFER from
the actual coord parent `coordination_branch`; the recording must be corrected to the true parent so the
default no-`--base` coord lane still resolves to `coordination_branch` (no-regression pin, Test 9b).
**Rationale**: M1 makes `--base` honored, which desyncs the gate for exactly the lanes M1 ships; shipping a
known-wrong measurement on the fixed path is worse than the bounded surface expansion. The dep-lane
re-parenting reconciliation remains M8 (FR-009 fail-loud); the gate's base *reading* is not that
reconciliation — it just honors the recorded parent.
**Alternatives**: defer to M8 + document (rejected by operator — ships a wrong measurement on the shipped
no-dep path). Re-parent coord branch (out of scope — that IS the M8 two-route reconciliation).

## Post-plan squad dispositions (2026-08-21)

A second 3-lens squad reviewed the plan. Dispositions:

| Finding | Disposition | Where |
|---|---|---|
| FR-010/FL4 non-atomic retry-wedge (architect HIGH) | **changed** | FR-010 → pre-create guard; plan design + Test 5 |
| Typed error base class: StructuredError not Exception (architect MED vs reviewer caution) | **changed** (adjudicated from source) | plan design; NFR-004 reframed as documentary tuple listing |
| "Mission branch:" mislabel (architect LOW) | **changed** | keep base_branch/base_commit distinct from mission_branch print |
| for_review gate cheap fix exists (architect MED) | **changed** (operator elevated) | FR-011, Decision 4 |
| test_implement_base_flag.py pins retired smuggle (reviewer HIGH) | **changed** | Test 8 rewrite; touched-files widened |
| FR-007 cites nonexistent test (reviewer MED) | **changed** | Test 7 added |
| AC-1 fixture-fidelity caveat (reviewer MED) | **changed** | Test 1 fidelity gate |
| C-003 swap-back not proceduralized (reviewer MED) | **changed** | procedural swap steps in test plan |
| Success-line anchor 1886→~1897 + guard predicate (implementer MED) | **changed** | plan design + Test 4 silence case |
| Caller enumeration complete + confined (implementer PASS) | **accepted** | confirms C-001 |

No contested finding silently dropped.

## Decision 5 — Typed fail-loud exception + envelope discipline

**Decision**: Introduce `UnhonorableBaseError(route, wp_id, base)` (subclass of `Exception`, not
`RuntimeError`) in `worktree_allocator.py`; raise at the 4 fail-loud sites; add it to the orchestrator
except-tuple (`orchestrator_api/commands.py`) and ensure the CLI wrapper surfaces its message.
**Rationale**: NFR-002 wants a typed error; NFR-004 wants it caught by both entry seams so it never escapes
as a raw traceback. The orchestrator passes `base=None` so the raise is latent there, but the defensive
catch is cheap and correct.

## Supply-chain security (advisory)

No dependency added/upgraded/removed. `supply_chain_security_check` is N/A for this mission — recorded, not
silently skipped. Registry authenticity / lifecycle-script / LTS checks do not apply.

## Adversarial evidence disposition (plan-phase)

The post-spec adversarial squad (4 lenses) ran BEFORE this plan; its findings F1–F9 are folded into the
spec and this plan. Contested-finding dispositions (per `contracts/adversarial-evidence-contract.md`):

| Finding | Disposition | Where |
|---|---|---|
| F1 caller enumeration incomplete | **changed** | C-001, Decision 2 |
| F2 topology-blind seam / legacy starvation | **changed** | C-005, Decision 1 |
| F3 D2 phantom trigger | **changed** | D2 attachment point → FR-009 |
| F4.1 dep-tip ancestry re-import | **changed** | FR-009 fail-loud |
| F4.2 detached-base planning merge | **changed** | FR-010, Decision 3 |
| F4.3 for_review gate coupling | **changed** (operator elevated to in-scope, see below) | C-004, Decision 4, FR-011 |
| F5 red-first bypasses seam | **changed** | AC-1, C-003 |
| F6 fakeable AC-3/AC-4 | **changed** | AC-3/AC-4 no-mock |
| F7 print relocation / envelope / default param | **changed** | NFR-004/005, design |
| F8 D3 reuse on sequential WPs | **accepted** (documented) | Risks |

No contested finding silently dropped.

## Data model & contracts

**N/A** — this is a behavior point-fix. No new entities, no persisted schema change (the `base_branch`/
`base_commit` provenance fields already exist), no new API/contract surface. `data-model.md`, `contracts/`,
and `quickstart.md` are intentionally omitted; the FR→site map + test plan in `plan.md` are the design
contract.
