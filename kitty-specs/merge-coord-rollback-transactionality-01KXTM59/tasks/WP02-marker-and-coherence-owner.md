---
work_package_id: WP02
title: MergeState marker + single coherence owner + repair primitive
dependencies: 
- WP01
requirement_refs:
- FR-004
- FR-009
tracker_refs: []
planning_base_branch: fix/merge-coord-rollback-transactionality
merge_target_branch: fix/merge-coord-rollback-transactionality
branch_strategy: Planning artifacts for this mission were generated on fix/merge-coord-rollback-transactionality. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/merge-coord-rollback-transactionality unless the human explicitly redirects the landing branch.
subtasks:
- T004
- T005
- T006
- T007
phase: Phase 2 - Foundations
assignee: ''
agent: "claude"
shell_pid: "674338"
shell_pid_created_at: "1784390676.55"
history:
- at: '2026-07-18T14:30:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/coordination/
create_intent:
- src/specify_cli/coordination/coherence.py
- tests/coordination/test_coherence.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/merge/state.py
- src/specify_cli/coordination/coherence.py
- tests/coordination/test_coherence.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP02 – MergeState marker + single coherence owner + repair primitive

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

---

## Objectives & Success Criteria

Build the three foundations the executor (WP03) and doctor (WP04) consume: the durable marker field,
the ONE coordination-layer coherence owner, and the coordination-homed `git revert` repair primitive.

- **FR-004**: `MergeState.pending_coord_reconcile: dict[str, Any] | None`, persisted via `save_state` to the canonical per-mission runtime state; `from_dict` rehydrates it as a plain dict (no migration).
- **FR-009**: one `coord_incoherent_done_wps(coord_ref, candidate_wps)` (committed-ref authority) + one repair primitive, both in `coordination/` — consumed by mark + heal + doctor, never re-implemented per call-site.
- **SC-007 / anti-fakeability**: in a ≥2-WP fixture, `coord_incoherent_done_wps` returns exactly the stranded WP; a hardcoded `["WP01"]` and an over-broad `all_wp_ids` both fail.

## Context & Constraints

- Spec: [spec.md](../spec.md) FR-004, FR-005 (marker shape), FR-009; data-model [derivation contract](../data-model.md).
- Research: [research.md](../research.md) D1 (marker home), D7 (committed-ref derivation), D9 (surfaces/repair transport).
- **The derivation is committed-ref, NOT a worktree diff** — a committed-vs-working diff is empty at the #2786 mark point (restore touches primary paths, not the coord worktree) → silent strand-drop.

### Code anchors (verified on base)
- `src/specify_cli/merge/state.py` — `MergeState`, `from_dict` (≈102-104, drops unknown keys), `save_state` (≈153-165, writes canonical `.kittify/runtime/merge/<mission_id>/state.json`; legacy `.kittify/merge-state.json` is `mission_id=None` back-compat only).
- `src/specify_cli/merge/done_bookkeeping.py:510` — `_durable_done_wps_on_coordination_ref(candidate_wps, ...)` reads `EventLogReadContract.coordination_branch_ref`. This is the reduction `coord_incoherent_done_wps` wraps. (It is merge-private; the coordination owner may either call it or re-derive via the same `EventLogReadContract` primitive to avoid a coordination→merge import — prefer re-deriving via `EventLogReadContract` to keep the layer clean.)
- `src/specify_cli/merge/executor.py:469-483` — the existing `_revert_coord_done_commit` `git revert` (env via `_make_merge_env`); its docstring already notes `advance_branch_ref` refuses the non-FF move. The repair primitive extracts this logic to `coordination/`.

## Branch Strategy

- **Planning base branch**: `fix/merge-coord-rollback-transactionality`
- **Merge target branch**: `fix/merge-coord-rollback-transactionality`
- Execution worktrees are allocated per computed lane from `lanes.json`.

## Subtasks & Detailed Guidance

### Subtask T004 – MergeState.pending_coord_reconcile field

- **Purpose**: The durable marker surface, persisted with the merge state, that survives `--resume`.
- **Steps**:
  1. Add `pending_coord_reconcile: dict[str, Any] | None = None` to `MergeState` (plain dict — `from_dict` rehydrates JSON objects as dicts; a nested dataclass would silently arrive as a dict).
  2. Ensure `to_dict`/`from_dict` round-trip it (unknown-key drop already handles old files → `None`).
  3. Confirm `save_state` writes the canonical runtime path; heal/doctor will load from there.
  4. **Add `iter_pending_coord_reconcile_markers(repo_root) -> Iterable[MergeState]`** in `state.py` — scan `.kittify/runtime/merge/*/state.json` and yield states carrying a `pending_coord_reconcile` (state.py owns the runtime path shape). `load_state(mission_id=None)` **raises** `MergeAmbiguousStateError` on ≥2 states, so the doctor (WP04) CANNOT use it to enumerate — it consumes this iterator instead. Give it a focused test.
- **Files**: `src/specify_cli/merge/state.py`
- **Marker keys** (see data-model): `coord_ref`, `captured_sha`, `coord_worktree`, `stranded_wp_ids`, `revert_error`, `detected_at`.

### Subtask T005 – coord_incoherent_done_wps (the single owner)

- **Purpose**: The one committed-ref coherence reducer consumed by mark (WP03), heal (WP03), and doctor (WP04).
- **Steps**:
  1. New `src/specify_cli/coordination/coherence.py`: `coord_incoherent_done_wps(coord_ref: str, candidate_wps: list[str]) -> list[str]` — returns the subset of `candidate_wps` still reducing to `DONE` on the committed coord ref.
  2. Read via `EventLogReadContract.coordination_branch_ref(...)` + the status reducer (mirror `_durable_done_wps_on_coordination_ref`). Do NOT read the working tree.
  3. `candidate_wps` is always *this merge's* pre-target done write-set — callers pass it; the function never enumerates all WPs.
- **Files**: `src/specify_cli/coordination/coherence.py` (NEW)

### Subtask T006 – Coordination-homed git-revert repair primitive

- **Purpose**: The single repair operation both executor-resume (WP03) and `doctor --fix` (WP04) call — avoids doctor→executor dependency inversion.
- **Steps**:
  1. In `coherence.py`, add a repair fn: forward `git revert` of the stranded coord commit in the coord worktree, env via `_make_merge_env`. **Import `_make_merge_env` function-locally** (module-top `from specify_cli.lanes.merge import _make_merge_env` creates the cycle `merge.executor → coordination.coherence → lanes.merge → merge.config`; executor.py:474 already uses the lazy pattern). NOT `advance_branch_ref` (refuses non-FF); no raw `git update-ref` (AC-B3).
  2. Make it **strand-gated**: re-derive via `coord_incoherent_done_wps`; if the ref is already coherent, no-op (so a double-heal cannot revert the revert / re-apply `done`).
  3. Keep it idempotent and safe under repeated invocation (NFR-002).
- **Files**: `src/specify_cli/coordination/coherence.py`

### Subtask T007 – ≥2-WP non-fakeability tests

- **Purpose**: Pin the anti-fakeable contract (renata) at the owner level.
- **Steps**:
  1. New `tests/coordination/test_coherence.py`: a fixture with a committed coord ref where WP-A is `done`, WP-B is `approved`.
  2. Assert `coord_incoherent_done_wps(ref, ["WP-A","WP-B"]) == ["WP-A"]` — WP-B excluded. A hardcoded `["WP01"]` and `== candidate_wps` both fail.
  3. **Pre-existing-done exclusion (the only test that distinguishes the write-set from `all_wp_ids`):** a fixture where WP-C is `done` on the ref *from before this merge* (NOT in the candidate write-set) → `coord_incoherent_done_wps(ref, candidate_wps_without_WPC)` excludes WP-C. This is what proves passing `run.all_wp_ids` would be wrong.
  4. Test the repair primitive's strand-gating: applied twice → byte-stable coord log; applied to an already-coherent ref → no-op.
  5. Test `iter_pending_coord_reconcile_markers` returns all markers across ≥2 runtime state dirs (where `load_state(None)` would raise) — keep this test in the owned `tests/coordination/test_coherence.py` (do not edit the unowned `tests/` state suite).
- **Files**: `tests/coordination/test_coherence.py` (NEW)

## Definition of Done

- [ ] `MergeState.pending_coord_reconcile` round-trips; old state files rehydrate to `None` (no migration).
- [ ] `iter_pending_coord_reconcile_markers(repo_root)` enumerates markers across ≥2 runtime state dirs (tested); doctor (WP04) consumes it — `load_state(None)` is NOT used to enumerate.
- [ ] `coord_incoherent_done_wps` derives from the committed ref only; `tests/coordination/test_coherence.py` green (≥2-WP specific-WP, **pre-existing-done exclusion**, gating, idempotency).
- [ ] Repair primitive uses `git revert` + a **function-local** `_make_merge_env` import; no `advance_branch_ref`, no raw `update-ref`, no `coordination→merge` module-top import.
- [ ] `ruff check .` + `mypy` clean on touched files; every new branch/helper has a focused test.
- [ ] No executor.py or doctor edits (those are WP03/WP04).

## Reviewer Guidance

Confirm the derivation reads the committed ref (not the worktree); confirm the ≥2-WP test would fail
a hardcoded or over-broad list; confirm the repair is `git revert` (not `advance_branch_ref`) and
strand-gated; confirm the owner is a single function both future callers can share (no duplication
seeded).

## Activity Log

- 2026-07-18T15:52:15Z – claude – shell_pid=643623 – Assigned agent via action command
- 2026-07-18T16:04:24Z – claude – shell_pid=643623 – Foundations green
- 2026-07-18T16:04:44Z – claude – shell_pid=674338 – Started review via action command
- 2026-07-18T16:10:09Z – user – shell_pid=674338 – Review passed (renata): committed-ref derivation + pre-existing-done falsifier + layer-clean + git-revert transport all verified
