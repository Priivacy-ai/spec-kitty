# Mission Specification: M8 — Lane-allocation single-seam (recurrence prevention for #3571)

> **Status:** LIGHT spec — specify-phase draft only. NOT finalized. Authored by analyst-annie.
> One of eight specs feeding a single-branch PR before rc2; runs later in the sequence.
> **M8 is the structural home for the #3571 class; M1 ships the point-fix. This mission
> generalizes so the class cannot recur.** Every code reference below was verified against
> `main` (worktree_allocator.py, write_target_degrade.py, status_transition.py).
>
> **Operator decisions applied (scope EXPANDED):** All three issues fold into M8 —
> **#3460** (authoritative topology predicate) + **#3462** (read-side degrade helper) +
> **#3536** (protected-primary no-coord refusal). The mission = the shared allocation seam +
> an anti-bypass guard test + the authoritative predicate + the read-side degrade helper +
> the #3536 refusal fix. **M1 (#3571) is a soft dependency:** M1 ships the point-fix first;
> M8 generalizes *around* M1's `base` param — references it, does not duplicate it. Open
> Questions OQ-1/OQ-2/OQ-3 are **resolved** below.

---

## Problem & Impact (BLUF)

A recurring hazard in the coordination subsystem: **an allocation/resolution decision has
two (or more) disjoint routes, and an override, flag, or field reaches only one of them.**
The dominant route silently ignores the input while a subordinate route honors it, so the
system reports success while discarding operator intent.

The load-bearing instance is **#3571 (P0)**: `spec-kitty implement WP## --base <ref>` patches
only `lanes_manifest.mission_branch` and prints a fabricated success line, but
`allocate_lane_worktree` (`src/specify_cli/lanes/worktree_allocator.py`) parents coord-topology
missions — the modern default — from the **coordination branch** (`~:262`) and reads
`mission_branch` **only** in the legacy `else` (`~:272-276`). So `--base` is a no-op on the
dominant path; the lane silently inherits the coord branch's original ancestry (the "unrelated
branch became an ancestor" symptom). The reuse early-return (`~:191`) and crash-recovery
early-return (`~:235`) do not consult `base` at all.

The same shape recurs across the coordination core:
- **#3460 (P1):** `emit_inner_state_changed_transactional` gates coord-vs-uncommitted routing
  on the `coordination_branch is None` **surrogate** instead of the authoritative
  `_transaction_topology_available(identity, mission_slug)` predicate — a coarse proxy in
  front of a finer capability. Two edge cells disagree with the authority.
- **#3462 (P2):** the write side converged on **one** shared helper
  `resolve_write_target_or_degrade` (`src/mission_runtime/write_target_degrade.py:67`,
  4 consumers); the symmetric **read-side** degrade is hand-rolled at 6+ sites with divergent
  fallback targets and caught-exception sets — no shared companion, and the family is still
  growing.
- **#3536 (P2):** on a `lanes` topology with a protected `target_branch`, the commit-router
  routes bookkeeping to `target_branch`, the policy refuses it (`PROTECTED_BRANCH_REFUSED`),
  and the prescribed remedy ("use the coordination branch") **has no target** because a
  `lanes` topology mints no coord branch. The two layers disagree; lane state silently drifts.

**Impact:** operator intent is discarded silently, review scope is invalidated, blocked
evidence can be merged, and lane state drifts from reality — all while the CLI reports success
or emits an un-followable remedy. Each point-fix closes one cell; without a structural seam the
next new flag/field/topology re-opens the class. This is the same meta-pattern the investigation
names the **operator-signal contract** (epic **#3410**): *an input that is dropped, defaulted,
or short-circuited must fail loud or surface the delta at the decision point.*

---

## In Scope / Out of Scope

**In scope — generalization only:**
- A **single shared lane-topology resolver** (working name `resolve_lane_base_or_degrade` /
  a `LaneTopologyDecision` seam) that every allocation and degrade path routes through, so a
  new flag/field/topology **cannot** bypass a route.
- Threading the explicit `base` override into the seam as a first-class parameter (retiring the
  `mission_branch`-smuggling proxy), covering **all** allocator routes: fresh-create (coord +
  legacy), reuse, and crash-recovery.
- A **guard test** that fails when a new allocation/degrade route is added without routing
  through the seam (structural anti-bypass test).
- Making the **topology-availability predicate authoritative and single** — swap the
  `coordination_branch is None` surrogate gate for the existing authoritative
  `_transaction_topology_available(identity, mission_slug)` so no bypassing site can disagree
  with the authority (#3460).
- A **read-side degrade companion** `resolve_read_dir_or_degrade` to the existing write-side
  `resolve_write_target_or_degrade`, parameterized on fallback strategy (degrade-to-dir vs
  fail-closed) and caught-exception set, migrating the ~6 hand-rolled sites onto it (#3462).
- The **#3536 refusal fix:** on `lanes`/`single-branch` topologies with a protected
  `target_branch`, replace the un-followable "use the coordination branch" remedy with a real
  destination or an accurate no-coord remedy — noting the `commit_router`/`policy` coupling and
  the relationship to epic **#2739** (protected-primary refusals).
- **Fail-loud contract:** any route that structurally cannot honor an explicit `base` or a
  topology must refuse with an accurate, followable remedy — never print success or an
  un-followable one.

**Out of scope:**
- **#3571's point-fix — that is Mission M1** (soft dependency). M8 references M1's `base` param
  and generalizes around it; it does not duplicate M1's diff. M8 lands after M1 closes the P0.
- Cluster-A charter/doctrine DRG-reach issues (#3605/#3604/#3596/#3598) — separate missions.
- Cluster-B operator-signal siblings #3578 and #3590 — separate missions.
- The terminal-state epic (#3550/#3432/#2745) and the enum consolidation (#3416).
- Any change to the coord/primary partition *semantics* — this mission unifies the *routing
  seam*, not the topology model.

---

## Functional Requirements

| ID | Title | Requirement | Priority | Status |
|----|-------|-------------|----------|--------|
| FR-001 | Single allocation seam | All lane-base/allocation decisions (fresh-create coord, fresh-create legacy, reuse, crash-recovery) resolve their parent ref through **one** shared resolver, not per-route inline logic. | High | Open |
| FR-002 | Explicit base is first-class | The explicit `base` override is a typed parameter threaded to the seam, not smuggled through `lanes_manifest.mission_branch`; every route consults it identically. | High | Open |
| FR-003 | Fail loud on unhonorable topology | When a route structurally cannot honor an explicit `base` (e.g. reuse/recovery early-returns, or a topology with fixed parentage), the seam refuses with an accurate, followable message — never a fabricated success line. | High | Open |
| FR-004 | Authoritative topology predicate | Topology-availability is decided by a single authoritative predicate; surrogate proxies (e.g. `coordination_branch is None`) are removed from routing gates so no bypassing site can disagree with the authority (#3460). | High | Open |
| FR-005 | No-coord fallback is defined (#3536) | On `lanes`/`single-branch` topologies with a protected `target_branch`, bookkeeping/allocation routing has a real, followable destination or an accurate no-coord remedy — the coord-branch remedy is never emitted when no coord branch exists. Fix spans `commit_router` + `policy`; aligns with epic #2739. | High | Open |
| FR-006 | Read-side degrade companion (#3462) | Ship `resolve_read_dir_or_degrade` as a companion to `resolve_write_target_or_degrade`, parameterized on fallback strategy (degrade-to-dir vs fail-closed) and caught-exception set; migrate the ~6 hand-rolled read-side sites onto it. | High | Open |
| FR-007 | Anti-bypass guard | A structural/architectural test fails when a new allocation or degrade route is introduced that does not route through the shared seam. | High | Open |
| NFR-001 | Behavior preserved for the common path | The dominant coord path and the legacy `mission_branch` path retain current parentage behavior where the operator supplied no override; only the bypass hazard is removed. | High | Open |
| C-001 | Reference M1, do not duplicate | M8 consumes M1's #3571 point-fix (its `base` param) as prior art and generalizes it; it must not re-land M1's diff. | — | Open |
| C-002 | M1 soft dependency | M8 sequences after M1; if M1 slips, M8's seam still subsumes the `base` threading but must not block on M1's merge to begin design. | — | Open |

---

## User Scenarios & Acceptance Criteria (Given/When/Then)

### US-1 — Explicit base is honored on every route (P1)

1. **Given** a coord-topology mission and `spec-kitty implement WP01 --base <ref>`,
   **When** the lane worktree is freshly created,
   **Then** the created lane descends from `<ref>` alone, and `<ref>` is resolved through the
   shared seam (not the legacy-only `mission_branch` field).
2. **Given** a lane worktree already exists (reuse path) or its branch exists but the directory
   was lost (crash-recovery path), **When** `--base <ref>` is supplied and the existing lane
   does **not** descend from `<ref>`, **Then** the command **fails loud** with a followable
   remedy — it never silently reuses a divergent base nor prints success.

### US-2 — A new route cannot bypass the seam (P1) — the recurrence guard

1. **Given** the shared lane-topology resolver is the single decision point,
   **When** a developer adds a new allocation/degrade route that computes a parent ref inline
   instead of calling the seam, **Then** the anti-bypass guard test (FR-007) fails in CI,
   naming the offending site.
2. **Given** a new topology or a new override field is introduced,
   **When** it reaches allocation, **Then** it flows through the seam's typed inputs — an
   override that reaches only one route is structurally impossible.

### US-3 — Topology predicate is single and authoritative (P2)

1. **Given** a legacy coord mission (coord branch on disk, `coordination_branch` absent from
   `meta.json`), **When** a transactional emit / allocation routes, **Then** it consults the
   authoritative topology predicate and routes transactionally — the `coordination_branch is
   None` surrogate no longer decides (#3460).
2. **Given** a `lanes` topology on a protected `target_branch`,
   **When** a lane transition/allocation is recorded, **Then** the outcome is a followable
   destination or an accurate no-coord remedy — never the impossible "use the coordination
   branch" instruction (#3536).

### US-4 — Read-side degrade goes through one helper (P2)

1. **Given** the ~6 hand-rolled read-side degrade sites (see anchors),
   **When** a coord surface read hits `CoordinationBranchDeleted` / `StatusReadPathNotFound`,
   **Then** the site routes through `resolve_read_dir_or_degrade`, which enacts the caller's
   declared strategy (degrade-to-`feature_dir`, degrade-to-`primary_feature_dir`,
   zero-evidence sentinel, or fail-closed) — behavior at each site is unchanged after migration.
2. **Given** a site that must NOT swallow a deleted coord branch carrying unmerged status
   (data-loss guard, `status/aggregate.py:351`, #1848), **When** it is migrated,
   **Then** the helper's per-caller exception set preserves the re-raise — the helper never
   collapses distinct fallback contracts into one hardcoded try/except.

### Edge Cases
- Explicit `base` no longer resolvable (merged-and-deleted): warn + fall back per the existing
  `--base main` recovery surface, consistently across all routes (not per-route).
- Dependency-lane tips still compose on top of the seam-chosen base (must not regress #1684).
- Non-git `repo_root` with `coordination_branch` set: degrade, do not raise (the #3460 cell 1).

---

## Key Design Decisions

1. **Shape of the shared seam — mirror the write side.** The write side already proves the
   pattern: `resolve_write_target_or_degrade(repo_root, mission_slug, kind, *, degrade_ref)`
   centralizes port-resolution + pre-gate while letting each caller pick fail-open vs
   fail-closed via `degrade_ref`. M8's allocation seam should follow the same contract shape:
   a single resolver that takes the topology inputs + an explicit `base` + a caller-chosen
   degrade/fail strategy, and returns a `LaneBaseDecision` (chosen parent ref + honored-flag +
   refusal reason). This makes "input reaches its consumer via one seam, not a mutated proxy"
   a structural invariant, not a convention.
2. **Relationship to `resolve_write_target_or_degrade`.** Three sibling seams share one family
   and one vocabulary, and **M8 delivers all three** (operator decision): (a) **write** —
   `resolve_write_target_or_degrade` (exists, unchanged); (b) **read** —
   `resolve_read_dir_or_degrade` companion (#3462, new); (c) **allocate** — the M8 lane-base
   seam (new). The topology-availability predicate underneath all three is the single
   authoritative `_transaction_topology_available` (#3460), not per-site surrogates. Build order:
   land the authoritative predicate first (#3460, low-risk gate swap), then the allocation seam
   (subsumes M1's `base` param), then the read-side companion (design pass over ~6 sites), then
   wire the #3536 refusal onto the unified predicate's no-coord answer.
3. **Fail-loud over fabricated success.** The seam's default on an unhonorable route is refusal
   with a followable remedy; printing success while dropping intent (the #3571 signature) is
   prohibited. This aligns with epic #3410's operator-signal contract — cite #3410/#3549
   rather than minting new vocabulary.
4. **Preserve legacy behavior.** The legacy `mission_branch` route must keep working; the seam
   subsumes it as one branch of the decision, it does not delete it (backward-compat with
   pre-coord missions, per NFR-001).

---

## RESOLVED DECISIONS (operator, scope EXPANDED)

### RD-1 — Scope: one coherent mission folding all three (was OQ-1).
**Decision: fold #3460 + #3462 + #3536 into M8 as one coherent mission** (not an epic of
sub-missions). M8 = shared allocation seam + anti-bypass guard test + authoritative topology
predicate (#3460) + read-side degrade helper (#3462) + #3536 refusal fix. The investigation's
"epic-sized, cite don't fold" steer is superseded by the operator's expanded-scope call; the
mission carries the larger surface as one delivery. Suggested WP slicing at plan-time:
(WP1) authoritative predicate swap #3460; (WP2) allocation seam + `base` threading (around M1);
(WP3) anti-bypass guard; (WP4) `resolve_read_dir_or_degrade` + 6-site migration #3462;
(WP5) #3536 `commit_router`/`policy` refusal fix.

### RD-2 — Sequence after M1: soft dependency (was OQ-2).
**Decision: M1 (#3571) ships the point-fix first; M8 generalizes AROUND M1's `base` param —
references, does not duplicate (C-001).** M1 is encoded as a **soft dependency** (C-002): M8's
design and the seam work may begin before M1 merges, but M8's allocation seam subsumes M1's
`base` threading rather than re-inventing it. If M1 has already added `base` to
`allocate_lane_worktree`, M8 refactors that param into the shared seam.

### RD-3 — All three issues are IN this mission (was OQ-3).
- **#3460 — IN.** Swap the `coordination_branch is None` surrogate gate in
  `emit_inner_state_changed_transactional` for `_transaction_topology_available`; red-first
  legacy-coord test (coord branch on disk, no `coordination_branch` in meta). Land first (low-risk).
- **#3462 — IN.** Design `resolve_read_dir_or_degrade` (companion to
  `resolve_write_target_or_degrade`), parameterized on fallback strategy + caught-exception set;
  migrate the ~6 hand-rolled sites. This is a design pass, not a mechanical dedup — budget for it.
- **#3536 — IN.** Fix the protected-primary no-coord refusal in `commit_router` + `policy`;
  emit an accurate no-coord remedy (or a real destination) instead of the impossible
  coord-branch instruction. **Note the coupling to epic #2739** (same protected-primary seam);
  cross-reference #2739 so the two do not diverge, and ensure the unified predicate exposes the
  no-coord answer #2739's sub-issues also need.

---

## Risks / Blast-radius

- **Touches the coord-topology core.** The seam sits on the allocation + degrade + routing hot
  path; a broad consumer set (allocator, transactional emitter, commit-router, 6+ read-side
  sites). Regression risk to reuse (#2993), crash-recovery (#2512/#2514), sparse-checkout
  registration, and dependency-tip propagation (#1684) — all must stay green.
- **Legacy backward-compat.** The legacy `mission_branch` route and legacy coord missions
  (coord branch on disk, no `coordination_branch` in meta) must keep working; the predicate
  unification (#3460) changes routing for exactly those legacy cells — needs red-first coverage.
- **Expanded surface (all three IN).** Folding #3462's read-side design pass + #3536's
  `commit_router`/`policy` fix into one mission widens the blast radius and the WP count
  (see RD-1 slicing). Mitigation: land the low-risk predicate swap (#3460) first, sequence the
  design-heavy #3462 helper after the seam's shape is proven, keep #3536 cross-referenced to
  #2739 so the two protected-primary fixes converge rather than diverge.
- **Coordination with M1 (soft dependency).** M8 must reference M1's `base` param, not
  re-invent it (C-001/C-002); if M1 slips, M8's seam still subsumes the threading but the P0
  stays open on M1's timeline. Sequence discipline (RD-2) is load-bearing.
- **Stale docstring drift.** `worktree_allocator.py:~450-453` documents the current
  `mission_branch`-smuggling contract for `--base`; it must be corrected when the seam retires
  the proxy (else the doc re-teaches the bypass).

---

## Issues / Traceability

- **#3571 (P0)** — load-bearing instance; point-fix is **Mission M1** (soft dependency),
  generalized here. Parent: #1795.
- **#3460 (P1)** — surrogate predicate; **IN this mission** (RD-3, land first). Parent: #2160.
- **#3462 (P2)** — read-side degrade companion `resolve_read_dir_or_degrade`; **IN this mission**
  (RD-3, design pass over ~6 sites). Parent: #1878.
- **#3536 (P2)** — lanes-topology no-coord fallback; **IN this mission** (RD-3); coupled to
  `commit_router`/`policy`, **cross-reference epic #2739** (protected-primary refusals).
- **Epic #3410** — "Charter/doctrine silent-drop — must fail loud, never fake-green"; the
  operator-signal-contract vocabulary this mission cites (with #3549) rather than minting new terms.
- **Related twins** (same override-written-to-one-field-read-from-another shape, per investigation §11):
  **#3122**, **#3029** — candidate future consumers of the seam / guard.
- Guardrails to keep green: #2993 (reuse self-heal), #2512/#2514 (crash-recovery + sparse-checkout),
  #1684 (dependency-tip propagation), #1915 (atomic dep-merge rollback).

### Code anchors (verified against `main`)
- `src/specify_cli/lanes/worktree_allocator.py` — `allocate_lane_worktree` (`:136`, signature has
  no `base` param); reuse early-return (`~:191`); crash-recovery early-return (`~:235`); the two
  create routes coord/legacy (`~:260-276`); stale `--base` docstring (`~:450-453`).
- `src/mission_runtime/write_target_degrade.py:67` — `resolve_write_target_or_degrade` (the
  write-side precedent to mirror), consumed at `status_transition.py:735`, `safe_commit_cmd.py`,
  `git/bookkeeping_commit.py:196`, `events/decision_log.py:136`.
- `src/specify_cli/coordination/status_transition.py` — `_transaction_topology_available`
  (authoritative predicate) vs the `coordination_branch is None` surrogate gate (#3460).
- Read-side hand-rolled degrade sites (#3462): `status/aggregate.py:351`,
  `retrospective/generator.py:271`, `cli/commands/_review_cycle_reconcile_doctor.py:282`,
  `cli/commands/agent/status.py:158` & `:197`, `core/worktree_topology.py:172`.
- `src/specify_cli/coordination/commit_router.py` + `coordination/policy.py` — the #3536 seam.
