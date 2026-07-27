# Closeout Deep-Dive — Architecture & Design Conformance

**Mission:** execution-context-unification-01KTPKST
**Reviewer:** architect-alphonso (ad-hoc profile)
**Branch reviewed:** `fixups/code-engine-stabilization` (12 WPs merged + rebased onto upstream/main)
**Date:** 2026-06-10
**Scope:** Architecture & design conformance — does the merged result *structurally* drain the
coord-vs-primary split-brain via ONE `MissionExecutionContext` (doc-09 fragments) + ONE
Mission-Management status facade?

---

## VERDICT: PASS (with two documented-scope deviations, both defensible; no surviving parallel mechanism)

The mission achieved its structural intent. The split-brain class is drained by **one** resolver
(`resolve_action_context`), **one** read-path primitive (`resolve_mission_read_path`), **one**
worktree-pointer parser (`core/paths.resolve_canonical_root`), **one** status-surface authority
(`resolve_status_surface`/`MissionStatus`), **one** daemon reaper wired to the spawn path, and **one**
liveness probe. The doc-09 fragment/op-composite model is genuinely implemented as cohesive,
self-validating value objects — NOT a flat field bag. C-005 (no parallel mechanism) holds. The two
deviations are scope reductions on FR-013 and a literal-reading of SC-7's "exactly one reaper," neither
of which reintroduces split-brain.

---

## doc-09 Conformance — PASS (genuine fragment/op-composite)

`src/mission_runtime/context.py` implements the doc-09 model faithfully:

- Six cohesive `@dataclass(frozen=True)` fragments: `IdentityFragment` (F0), `BranchRefFragment` (F3),
  `WorkspaceFragment` (F2), `StatusSurfaceFragment` (F5 read-locus), `ArtifactPlacementFragment`,
  `PromptSourceFragment`. Each is a value object owning its domain values.
- **`CommitTarget`** (ADR-2026-06-03-2) is a self-validating VO with `CommitTargetKind{PRIMARY,
  COORDINATION,FLATTENED}` — the FR-004 invariant ("artifacts AND status resolve to the same ref") is
  made a *type*, not a runtime check, exactly as doc-09 §6/§8-Q5 prescribed.
- **Single-derivation invariants enforced at construction**: `IdentityFragment.__post_init__` rejects any
  `mid8 != mission_id[:8]` (FR-012/C-CTX-3); `mid8` is derived exactly once in `.derive()`.
- The fragments are *attached* to the historical flat `ExecutionContext` substrate (NFR-001/C-004
  strangler compat) and **excluded from `to_dict()`** so the serialized wire shape is byte-identical to
  pre-fragment — fragments are an in-process composition concern. This is the correct deep-module move:
  it did NOT drift back to a god-bag.
- Builder (`resolution.py:_assemble_core_fragments` / `_assemble_*_fragment`) is the single assembly path
  (doc-09 §5 layer law: VOs in the canonical module, builder in `mission_runtime`). Each operation
  assembles only the fragments it needs (op-composite); fragments are `None` when not consumed.

Minor note (not a finding): doc-09 §5 sketched VO dataclasses living in `charter` and distinct
`Read/Write/Prompt` composites. The implementation pragmatically kept the fragments on the existing
`mission_runtime.ExecutionContext` substrate and attaches all assembled fragments to one object rather
than minting per-op composite classes. This is consistent with doc-09's own revision note (`11`: "internal
structure of a hardened ActionContext, not six new public objects") and is the lower-risk strangler cut.
Conformant.

## C-005 (the binding test) — PASS: ONE resolution path, no surviving parallel mechanism

Hunted for surviving parallel mechanisms across every cluster. Result: collapsed, not duplicated.

| Cluster / surface | Claimed collapse | Verified in merged tree |
|---|---|---|
| A — read-path resolver | fold `candidate_feature_dir_for_mission` → `_read_path_resolver` | **PASS.** Canonical impl moved to `_read_path_resolver.py:339`; `missions/feature_dir_resolver.py` is now a pure re-export shim. One `resolve_mission_read_path` def. 30+ callers route through it. |
| A — `_find_feature_directory` silent fallback | replace with structured error (C-CTX-4) | **PASS (both copies).** `agent/context.py:31` AND `agent/mission.py:802` both call `resolve_mission_read_path(require_exists=True)` and raise `FEATURE_CONTEXT_UNRESOLVED` / `MISSION_AMBIGUOUS_SELECTOR`. No silent primary fallback survives. |
| B — `_identity_for_request` coord re-derivation (#1737) | consume resolved surface | **PASS (functionally).** Now anchors on the CWD-invariant canonical dir via `_canonical_primary_feature_dir` → `resolve_status_surface`/`candidate_feature_dir_for_mission`. See half-seam note below. |
| B — `CoordinationWorkspace.resolve` lock (#1357) | lock-serialize | **PASS.** Per-path `threading.Lock` (`workspace.py:44/180`). C-FAC-2 satisfied. |
| C — worktree-pointer parser | delete `workspace/root_resolver` parser, keep `core/paths` | **PASS.** `root_resolver.py` parser GONE; module now re-exports `resolve_canonical_root` from `core/paths` and retains only the consumer `canonicalize_feature_dir`. One parser. |
| D — artifact placement (#1816) | adopt `placement_ref` at implement | **PASS.** `implement.py:_resolve_placement_ref` → `resolve_action_context().artifact_placement.placement_ref`; same `CommitTarget` as status. C-PLACE-1 structural. |
| D — record-analysis (#1814) | context-aware placement | **PASS (structural).** Caller resolves `feature_dir` via the read-path; flattened topology has no primary↔coord split to deadlock on (`kind==FLATTENED`). |
| E — `materialize_if_stale` git-op guard (#1789/#1062) | guard | **PASS.** `views.py:291` guards on `git_operation_in_progress()` (rebase-merge/-apply, MERGE_HEAD, cherry-pick, revert, index.lock). |
| E — stale-key context-aware (#1764) | key on canonical slug | **PASS.** `views.py` keys derived-view dir on canonical `mission_slug`, not CWD-relative name. |

- **`def resolve_action_context`**: exactly ONE (`resolution.py:494`).
- **`class ExecutionContext` (context object)**: exactly ONE (`context.py:185`). The
  `core/context_validation.py:ExecutionContext` is an unrelated `StrEnum` — no collision.
- **`target_branch`** single source: one `get_feature_target_branch` def (`core/paths.py:441`), resolved
  once in `resolve_action_context` and carried on `BranchRefFragment` (FR-012).
- **Parity ratchet EXTENDED, not forked**: single `test_execution_context_parity.py` grew 1,323 → 2,015
  LOC with `test_dual_cwd_*` assertions + a `FLATTENED`-topology synthetic fixture
  (`test_flattened_topology_*`). No second parity test exists. NFR-001/C-2/C-4 upheld.

## ADR conformance — PASS

- **ADR-2026-06-03-2 ExecutionContext-owner + CommitTarget**: `MissionExecutionContext`/`ExecutionContext`
  is the owner; `destination_ref`/`placement_ref` are the named `CommitTarget`. Names reused, none coined.
- **Lane FSM (2026-06-07-1)**: untouched authority; resolution reads lanes via the event log
  (`get_wp_lane`/`reduce`), `Lane.GENESIS` honoured. No regression.
- **Mission-runtime surface (2026-06-07-1)**: internal submodules import-forbidden; public `__all__` clean;
  compat names via `__getattr__` without widening the surface. Conformant.

## Post-rebase composition — PASS

Upstream's `resolution.py:_resolve_review_wp_id` (the `for_review`-then-review-claimed two-pass scan, now
event-log-driven) composes cleanly with the mission's resolution changes: it sits inside `_resolve_wp_id`,
which runs *after* the fragment assembly (`_assemble_core_fragments`) on the same resolved `feature_dir`.
No double-resolution, no conflicting WP-id derivation. The mission's fragment work and the upstream review
resolver are orthogonal and correctly ordered.

---

## FINDINGS

### F1 — FR-013 partially met: 3 of 5 "dead" symbols are NOT deleted (LOW; defensible, but a scope miss)

**Severity: LOW.** FR-013/SC mandated deleting 5 dead `coordination/status_service.py` symbols.
Verified in merged tree:
- DELETED: `append_event_log_batch`, `read_wp_lane_actor` (2/5). ✓
- RETAINED: `StatusReadSource` (`status_service.py:34`), `EventLogWriteTarget` (:42),
  `StatusContractError` (:50) — all three are **load-bearing** for `EventLogReadContract` /
  `EventLogWriteContract` / `read_event_log` / `append_event_log`, which now have **live callers**:
  `coordination/transaction.py`, `coordination/status_transition.py`, `cli/commands/agent/workflow.py`.

The reducer-randy research premise ("5 dead symbols, zero live callers") was incorrect for these three —
the facade-adoption work (IC-01) made the explicit read/write contract layer the *live* path, so deleting
them would break the build. The mission correctly did NOT delete live code. This is the right call but it
is an **undocumented divergence from FR-013's stated scope** (the FR/NFR-005 LOC-subtraction claim is
overstated by 3 symbols). **Action:** record in the retro/issue-matrix that FR-013 delivered 2/5 deletions
and the other 3 are retained-because-live (re-classify, don't re-delete). No code change needed.

### F2 — SC-7 "exactly ONE reaper" met in spirit, not as a single function (LOW)

**Severity: LOW.** SC-7 reads "exactly one daemon-lifecycle reaper remains." The merged tree still has
`reap_orphan_daemons` (owner.py — the canonical reaper wired to `ensure_sync_daemon_running`),
`scan_sync_daemons` (daemon.py — enumeration), `sweep_orphans` (orphan_sweep.py), and
`cleanup_orphan_sync_daemons` (daemon.py — `sync status`/`doctor` diagnostic surface). However:
- **Kill path is genuinely ONE**: all routes delegate to `owner._sweep_daemon_process`.
- **Reaper wired to spawn is genuinely ONE**: `reap_orphan_daemons`, executable-scoped, called once from
  `_ensure_sync_daemon_running_locked`.
- **Liveness probe is genuinely ONE**: `dashboard/lifecycle._is_process_alive` now delegates to
  `sync.daemon._is_process_alive` (single source of truth).

The remaining functions are thin discovery/diagnostic wrappers (port-scan vs cmdline-scan vs record-based)
that no longer carry independent kill or reaper logic — so there is no *parallel mechanism*, which is what
C-005/NFR-005 actually protect. A literal `rg` for "reaper-shaped function names" finds >1, so SC-7's exact
wording is not satisfiable by name-count, but the load-bearing invariant (one kill path, one spawn-reaper,
one liveness probe) holds. **Action:** none required for correctness; optionally tighten SC-7 wording in
future to "one kill path + one spawn-wired reaper" to match the achieved design.

### F3 — Half-seam: `status_transition` re-runs the resolver instead of reading the carried fragment (LOW)

**Severity: LOW (architectural smell, not split-brain).** `StatusSurfaceFragment` exists and is carried on
the context, but `_identity_for_request` / `_canonical_primary_feature_dir` (status_transition.py) do not
*receive* an `ExecutionContext` — they re-invoke `resolve_status_surface` / `candidate_feature_dir_for_mission`
directly. This is functionally correct (it consumes the SAME single authority, so it is CWD-invariant and
not a parallel resolver) but it is a not-fully-threaded seam: the low-level transactional emit path resolves
the surface itself rather than reading the fragment the composite already computed. FR-003's "carried
StatusSurfaceFragment, consumers must NOT re-derive it" is met in *authority* (one resolver) but not in
*threading* (the fragment is recomputed, not passed). **Action:** track as a follow-up to thread the
context/fragment into the emit path; low priority because there is no divergence risk — both arms call the
one resolver.

---

## Net assessment

The architecture delivers the durable fix it promised: split-brain is now *structurally* precluded for
flattened topology (one `CommitTarget` with `kind==FLATTENED`, no primary↔coord placement to reconcile) and
collapsed-to-one for coord topology. doc-09 is honoured as a real fragment model. C-005 holds — I found no
surviving parallel resolver, second status surface, duplicate worktree parser, or parallel daemon
kill/reaper. The three findings are all LOW and none reintroduce the split-brain class; F1 is the only one
worth a tracker note (FR-013 scope was 2/5 deliverable as written).
