# Research — Execution-Context Unification (01KTPKST)

**Mode:** structural (align-to-design), not whack-a-bug.
**Method:** three-agent research squad inspected the live codebase against the draft spec and the
ratified #1619/#1666 design notes. This document records their findings and the resulting
spec corrections. **Read this before `/spec-kitty.plan`** — several draft FRs are re-anchored here.

Squad:
- **debugger-debby** — seam inventory: where the split-brain actually reproduces in code.
- **reducer-randy** — duplication / dead-code inventory: what collapses, what deletes.
- **architect-alphonso** — design-conformance: does the draft spec match the ratified to-be model.

Anchor facts verified on `fixups/code-engine-stabilization` (2026-06-09):
- Substrate exists: `src/mission_runtime/context.py` (`ExecutionContext`, 2.9 KB) + `src/mission_runtime/resolution.py` (`resolve_action_context`, 12.6 KB).
- Status aggregate exists: `src/specify_cli/status/aggregate.py` (`MissionStatus`, 23.5 KB).
- **Parity ratchet ALREADY EXISTS:** `tests/architectural/test_execution_context_parity.py` — **1,323 lines**. FR-011 must EXTEND this, not fork a new one.
- The to-be context contract is ratified in `docs/engineering_notes/runtime_and_state_overhaul/09-context-decomposition-model.md` (doc-09) — a fragment / op-composite model, NOT a flat field bag.
- Dead surface confirmed present: `src/specify_cli/coordination/status_service.py` (10.7 KB).

---

## R-A — Seam inventory (debugger-debby)

The split-brain is not one bug; it is a **class** produced by ~7 independent resolvers each
answering "where does this mission's state/branch/status/artifacts/prompts live?" with their own
logic. Grouped into clusters:

### Cluster A — Read-path resolution (the *good* primitive + its duplicate)
- `src/specify_cli/missions/_read_path_resolver.py:resolve_mission_read_path` — the **canonical**
  read-path primitive (coord-aware, falls back correctly). This is the pattern to generalize.
- `src/specify_cli/missions/feature_dir_resolver.py:candidate_feature_dir_for_mission` — a **near-duplicate**
  of the above with subtly different fallback ordering. Source of read/write divergence.
- `_find_feature_directory` (mission discovery) has a **silent fallback** to the primary checkout when
  the coord surface is missing → returns a *wrong but plausible* dir instead of erroring. (Matches the
  StatusReadPathNotFound class noted in memory `project_flatten_mission_coord_worktree_missing`.)

### Cluster B — Status surface resolution
- `src/specify_cli/coordination/surface_resolver.py:resolve_status_surface` — resolves where status
  events are read/written.
- `src/specify_cli/coordination/status_transition.py:_identity_for_request` (#1737) — **re-derives** the
  coord path independently rather than consuming a resolved surface → primary↔coord visibility skew (#1572).
- `src/specify_cli/coordination/workspace.py:CoordinationWorkspace.resolve` (#1357) — **not lock-serialized**;
  concurrent resolves can race and materialize divergent surfaces.

### Cluster C — Worktree-pointer parsing (duplicate parsers)
- `src/specify_cli/core/paths.py` and `src/specify_cli/workspace/root_resolver.py` each parse the
  git worktree pointer / resolve the primary root **independently** (~200 LOC of overlap). Two parsers ⇒
  two opinions about `primary_root`.

### Cluster D — Artifact placement (the dogfood failures)
- `src/specify_cli/cli/commands/implement.py:_ensure_planning_artifacts_committed_git` (#1816) — decides
  *which ref* planning artifacts must be committed on; splits primary vs coord.
- `record-analysis` path (#1814) — dirty-tree guard runs against the primary checkout while the artifact
  it wants is coord-owned → deadlock. (This is exactly what paused mission 01KTNWFC.)

### Cluster E — Runtime status writers vs git ops
- `src/specify_cli/status/views.py:materialize_if_stale` (#1789) — **no git-op guard**; can re-materialize
  tracked status mid-`rebase`/`reset` (#1062). Also a **stale-key** subtlety: the staleness key is computed
  without the resolved context, so it can false-positive across CWDs (#1764 adjacency).

### Seams the draft spec MISSED (debugger flagged 6)
1. **`mid8` derivation** happens in multiple call sites — must be derived **once** in the context, never recomputed.
2. **`prompt_source_dir`** — implement/review prompt files are resolved separately from artifacts; a coord/primary
   prompt-dir split is a latent instance of the same class. (Draft FR-001 listed the field but no FR routes it.)
3. **`target_branch` derivation** has more than one source of truth (meta.json vs resolver vs git) — must collapse.
4. **`_find_feature_directory` silent fallback** (Cluster A) — needs to be a structured error, not a guess
   (the C-009-style "no silent fallback" rule already applied to selector disambiguation; apply it here too).
5. **`materialize_if_stale` stale-key** (Cluster E) — context-aware keying, not just the git-op guard.
6. **merge coord-topology seams** (#1736/#1770) — PATH/env baking + mixed-JSONL handling re-derive coord paths
   during merge; must consume the context like every other surface.

---

## R-B — Duplication & dead-code inventory (reducer-randy)

Net: the unification is **mostly subtraction**. Threading one context lets ~500–650 LOC of parallel
resolution collapse, plus dead symbols delete outright.

### Collapsible duplication (~500–650 LOC)
- Two worktree-pointer parsers (Cluster C): delete `workspace/root_resolver.py`'s parser (~200 LOC), keep
  `core/paths.py` as the single parser feeding the context.
- `feature_dir_resolver.candidate_feature_dir_for_mission` folds into `_read_path_resolver` (Cluster A).
- `status_transition._identity_for_request` stops re-deriving coord path; consumes `resolve_status_surface`
  output carried on the context (Cluster B).
- Scattered `mid8` / `target_branch` derivations collapse to context-provided values.

### Dead symbols — `src/specify_cli/coordination/status_service.py` (#1622)
Confirmed **5 dead symbols** (zero live callers): `EventLogWriteTarget`, `StatusContractError`,
`StatusReadSource`, `append_event_log_batch`, `read_wp_lane_actor`. Delete as part of the strangle
(do not migrate them — they are pre-facade scaffolding). Tracked under #1622/#391.

### Reducer caution
Deletions must be **strangler-ordered** (C-004): convert the consumer to the context first, prove the
parity ratchet stays green, *then* delete the now-unreferenced resolver. Never delete-then-rewire.

---

## R-C — Design conformance (architect-alphonso)

The structural intent of the draft spec is correct, but **three draft FRs contradict or duplicate the
ratified design** and must change before plan:

### C-1 (BLOCKING for FR-001) — flat field list contradicts doc-09
Draft FR-001 enumerates a flat 13-field `MissionExecutionContext`. doc-09
(`09-context-decomposition-model.md`) ratifies a **fragment / op-composite** model: the context is
composed of cohesive **fragments** (identity, branch/ref, status-surface, workspace, artifact-placement,
prompt-source) and an operation assembles only the fragments it needs (an "op-composite"). A flat bag
re-introduces the god-object the decomposition was designed to retire.
→ **FR-001 must be re-anchored on the doc-09 fragment model.** The 13 fields become fragment *contents*,
not top-level fields. The existing `mission_runtime.ExecutionContext` is the substrate to grow into the
composite (it already carries feature_dir/target_branch/workspace_path/branch_name/execution_mode/mission_slug);
the **missing** pieces (primary_root, current_cwd, coord_worktree, status_read_dir, status_write_dir,
destination_ref, allowed_command_cwd, prompt_source_dir) attach as fragments.

### C-2 (BLOCKING for FR-011) — the parity ratchet already exists
`tests/architectural/test_execution_context_parity.py` is **1,323 lines** of existing parity coverage.
→ **FR-011 must say "EXTEND" not "create".** Add the dual-CWD (primary vs lane/coord) assertions and a
flattened-topology synthetic fixture to the existing module. Forking a second parity test would itself be
a C-005 "parallel mechanism" violation.

### C-3 (reframe FR-003 / FR-004) — adoption, not construction
The `MissionStatus` aggregate + OHS facade (`status/aggregate.py`) **already exists**. FR-003 is not
"build a facade"; it is "**route the remaining raw primary/coord readers through the existing facade**"
(adoption work). Likewise FR-004's artifact-placement invariant is enforced by *adopting* the resolved
context at the two placement sites (implement-claim, record-analysis), not by inventing a new invariant
engine.
→ Reword FR-003/FR-004 as **adoption/strangle** requirements with explicit "remaining consumers" call-outs.

### C-4 — flatten topology needs a parity fixture, not just config
C-001 flattens this mission to a single branch. The architect notes that "flattened" must be *proven*
by the ratchet, otherwise it is just an unverified config choice. Add a synthetic flattened-topology
fixture to the extended parity test (ties to C-2).

### C-5 — conformance to existing ADRs
Confirms NFR-004's ADR list (2026-06-03-1/2/3 domain model / ExecutionContext-owner+CommitTarget /
Effector-Actor, + 2026-06-07-1 lane FSM). The context is the **ExecutionContext-owner** from
ADR-2026-06-03-2; `destination_ref` is that ADR's **CommitTarget**. Use those names, don't coin new ones.

---

## Spec corrections required (applied to spec.md this pass)

| # | Draft | Correction | Source |
|---|-------|-----------|--------|
| S1 | FR-001 flat 13-field list | Re-anchor on doc-09 fragment/op-composite model; fields become fragment contents; grow `mission_runtime.ExecutionContext` | C-1 |
| S2 | FR-011 "an e2e that runs…" | **EXTEND** `tests/architectural/test_execution_context_parity.py` (1,323 LOC); add dual-CWD + flattened-topology fixture | C-2, C-4 |
| S3 | FR-003 "owned by Mission-Management" reads as build | Reframe as **adoption**: route remaining raw readers through existing `MissionStatus`/OHS facade | C-3 |
| S4 | FR-004 invariant reads as new engine | Reframe as **adoption** at the 2 placement sites (implement-claim #1816, record-analysis #1814) | C-3 |
| S5 | missed seams | Add `mid8` single-derivation, `prompt_source_dir` routing, `target_branch` single-source, `_find_feature_directory` no-silent-fallback, `materialize` stale-key | R-A (6 missed) |
| S6 | dead code unmentioned | Add the 5 dead `status_service` symbols (#1622) to scope as strangler-ordered deletion | R-B |
| S7 | NFR-004 ADR names | Name the context as ExecutionContext-owner and `destination_ref` as CommitTarget per ADR-2026-06-03-2 | C-5 |

## Open questions deferred to plan
- **Fragment boundary granularity:** doc-09 sketches the fragments; the exact fragment cut (e.g. is
  `allowed_command_cwd` part of the workspace fragment or its own?) is a **plan/IC decision**, informed by
  which ops actually co-consume them.
- **Deletion sequencing:** which consumer to strangle first (read-path Cluster A is lowest-risk and unblocks
  the dogfood failures fastest; runtime Cluster E is highest-risk). Order in plan ICs.
- **FR-010 (#1815 bulk-edit gap):** still "decide in plan" — extend occurrence-map to model multi-path moves
  vs. scope `bulk_edit` to terminology + separate reference-integrity gate. Out of the context-unification
  core; keep adjacent.
