---
work_package_id: WP01
title: Library reconciliation seam (preserve-and-succeed)
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-004
- FR-005
- FR-006
- FR-007
- FR-009
planning_base_branch: fix/charter-synthesize-reconciliation
merge_target_branch: fix/charter-synthesize-reconciliation
branch_strategy: Planning artifacts for this mission were generated on fix/charter-synthesize-reconciliation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/charter-synthesize-reconciliation unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-charter-synthesize-reconciliation-01KZJQN6
base_commit: ea45202256c9684565c6cffdeab52c744f8a9a2d
created_at: '2026-08-10T02:09:35.195950+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
phase: Phase 1 - Foundation
agent: claude
history:
- timestamp: '2026-08-09T00:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/charter/synthesizer/
create_intent:
- src/charter/synthesizer/reconcile.py
- tests/charter/synthesizer/test_synthesize_reconcile.py
execution_mode: code_change
mission_id: 01KZJQN68SWZ7T1YKGDB4Q4EVH
owned_files:
- src/charter/synthesizer/orchestrator.py
- src/charter/synthesizer/write_pipeline.py
- src/charter/synthesizer/resynthesize_pipeline.py
- src/charter/synthesizer/reconcile.py
- src/doctrine/drg/validator.py
- tests/charter/synthesizer/test_synthesize_reconcile.py
- tests/charter/synthesizer/test_synthesize_node_preservation.py
role: implementer
tags: []
tracker_refs: []
wp_code: WP01
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned agent profile via `/ad-hoc-profile-load`
(profile: `python-pedro`, role: implementer). It sets your identity, boundaries, and governance
scope for this work package. Then read `kitty-specs/charter-synthesize-reconciliation-01KZJQN6/`
`plan.md`, `research.md`, `data-model.md`, and `contracts/synthesize-seam.md`.

# Work Package Prompt: WP01 – Library reconciliation seam (preserve-and-succeed)

## Objectives & Success Criteria

- `charter.synthesizer.orchestrator.synthesize` reconciles the freshly-emitted project DRG
  overlay **and** synthesis manifest against what is already on disk, instead of rebuilding both
  from the current target set and whole-file-swapping them in.
- The default behavior **preserves backed content** (drops nothing), exits normally, and returns
  a `ReconciliationDelta` describing retained / added / removable content.
- The committed red-first test `tests/charter/synthesizer/test_synthesize_node_preservation.py`
  turns **green**.
- An identical re-synthesis is byte-stable for `graph.yaml` **and** the manifest (NFR-002).

**Traceability note (FR-006 split, FR-007):** FR-006 is split across two WPs — **WP01 detects and
classifies** conflicts (populating `delta.conflicts`), **WP02 routes** them (suppress preserved /
raise new-emit). FR-007 (corrupt-overlay fail-closed) lives **here** at the library seam (amendment
#2 / T006 case 5), not only in WP03's CLI, because the in-process `activate`/`deactivate` path
bypasses the CLI.

## Context & Constraints

- **Root cause** (see `research.md`): today `orchestrator.synthesize._validation_callback`
  (`src/charter/synthesizer/orchestrator.py:179-188`) calls `emit_project_layer(targets=targets)`
  and persists a brand-new overlay with no read of the on-disk graph; `write_pipeline.promote`
  whole-file-swaps it in, and the manifest is rebuilt from the current `results` only
  (`orchestrator.py:193-198` passes no `manifest_override`).
- **Canonical reuse (C-002)**: the node/edge-preserving merge already exists on the resynthesize
  path — `resynthesize_pipeline._merge_project_overlay` (graph) and `_rewrite_manifest`
  (manifest). Reuse these; do **not** hand-roll a parallel merge.
- **Preserve-and-warn contract** (ledger `01KZJV6H7TW63M6ZGNM05XKM2S`): the library seam default
  is `preserve` (never silently drops); `prune`/`dry_run` are other modes. Do **not** bake a
  `--prune` default into the signature — keep `synthesize(request, adapter, repo_root)` callers
  working.
- Conflict **detection + classification** is WP01's job (amendment #3): populate `delta.conflicts`
  in-memory and pass the classified conflicts to `validation_gate.validate(...)`. WP02 owns only
  the **suppress-vs-raise decision** on that partition. This WP must not lose content and must hand
  the merged overlay + classified conflicts to validation.

## Subtasks & Detailed Guidance

### Subtask T001 – Reconcile value objects
- **Purpose**: Give the seam a typed vocabulary for the delta and modes (data-model.md).
- **Steps**: Create `src/charter/synthesizer/reconcile.py` with:
  - `class SynthesizeMode(enum.Enum)`: `preserve` (default), `prune`, `dry_run`.
  - `@dataclass(frozen=True) ReconciliationConflict`: `kind`, `target_id`, `backing_artifact`,
    `remediation`, `provenance` (`"preserved" | "new_emit"`).
  - `@dataclass(frozen=True) ReconciliationDelta`: `retained`, `added`, `removable`,
    `manifest_delta`, `conflicts` (lists). Add a `has_backed_removals`/`is_empty` helper.
- **Files**: `src/charter/synthesizer/reconcile.py` (new). Keep it dependency-light; import DRG
  models where needed.

### Subtask T002 – Share the merge primitives
- **Purpose**: Make `_merge_project_overlay` + `_rewrite_manifest` callable from the synthesize
  path without duplication.
- **Steps**: In `resynthesize_pipeline.py`, ensure both helpers are importable (module-level, not
  closures). If needed, lift them to `reconcile.py` and re-import in `resynthesize_pipeline.py` so
  both paths share one implementation. Do not change resynthesize behavior.
- **Validation**: existing `tests/charter/synthesizer/test_orchestrator_resynthesize.py` stays green.
- **Also extract the structured detection SSOT (for amendment #3):** in
  `src/doctrine/drg/validator.py`, extract `duplicate_edge_triples(graph) -> list[DRGEdge]` and
  `dangling_endpoints(graph) -> list[DRGEdge]` and re-express the existing `_validate_duplicate_edges`
  / `validate_dangling_references` (which return `list[str]`) as string formatters over these
  structured helpers — one definition of "duplicate"/"dangling" that `validate_graph` and
  `reconcile.py` both consume. Keep `validate_graph`'s existing `list[str]` output byte-for-byte.

### Subtask T003 – Reconcile the graph overlay at the seam
- **Purpose**: Preserve on-disk nodes/edges the current target set omits.
- **Steps**: In `orchestrator.synthesize._validation_callback`, after `emit_project_layer(...)`
  builds the fresh overlay, load the on-disk overlay (`load_graph_or_dir`) if present and call
  `_merge_project_overlay(existing_overlay=…, updated_overlay=fresh)`. Persist the **merged**
  overlay. Compute the graph portion of `ReconciliationDelta` (retained = on-disk∖target,
  added = target, removable = on-disk∖target only relevant under prune — here default preserve
  retains them).
- **Notes**: The merged overlay is what flows into validation (WP02 handles conflicts). Preserve
  edges atomically with their `source` node (FR-002) — `_merge_project_overlay` already does this.

### Subtask T004 – Reconcile the manifest
- **Purpose**: Keep the manifest consistent with the merged graph (avoid version-skew).
- **Steps**: Compute a merged manifest via `_rewrite_manifest(existing_manifest, new_results,
  run_id, repo_root)` and pass it to `write_pipeline.promote(..., manifest_override=merged)`.
  Mirror the resynthesize path (`resynthesize_pipeline.py:453,483`).
- **Validation**: manifest registers all preserved artifacts (no "manifest ⊂ graph" skew).

### Subtask T005 – Return the delta (back-compatible)
- **Purpose**: Expose the reconciliation delta for the CLI (WP03) and boundary (WP04).
- **Steps**: Add a keyword-only `mode: SynthesizeMode = SynthesizeMode.preserve` param to
  `synthesize`. Thread it: `preserve`/`prune` write, `dry_run` computes+returns without writing.
  Attach/return the `ReconciliationDelta` (extend `SynthesisResult` or return a tuple/attribute —
  keep existing positional callers working). Default path = preserve.
- **Notes**: `prune` removal logic may be minimal here (WP03 drives it); the key is the mode seam
  exists and `preserve` never drops.

### Subtask T006 – Tests
- Confirm `test_synthesize_node_preservation.py` (committed) passes.
- New `tests/charter/synthesizer/test_synthesize_reconcile.py`, with these **numbered** cases:
  1. **No-op byte-stability**: synthesize twice with identical inputs → `graph.yaml` and manifest
     byte-identical (extends the #1912 assertion to the reconcile path).
  2. **Manifest version-skew**: seed a manifest registering fewer artifacts than the graph → after
     synthesize, manifest registers the preserved artifacts (no skew).
  3. **Delta shape**: a superset on-disk overlay yields `retained` non-empty, `removable` populated.
  4. **[BLOCKER #1 — FR-009 unlink path] Zero/subset-emit over a backed overlay.** Synthesize with
     a target set that emits **ZERO or a strict SUBSET** of the on-disk project nodes over a
     **backed** on-disk overlay → assert `graph.yaml` still exists AND the preserved node/edges
     survive. This is the case the committed preservation test does **not** exercise (it emits
     nodes, so `has_project_graph=True`); it directly pins amendment #1 (drive the post-condition
     from the merged graph, not the fresh emit — otherwise `apply_post_condition` unlinks the
     preserved `graph.yaml`).
  5. **[BLOCKER #2 — FR-007 fail-closed AT THE SEAM] Corrupt on-disk overlay via a direct
     `synthesize(...)` call.** Write an unparseable/half-written `graph.yaml`, call the library
     seam `synthesize(...)` **directly** (not the CLI) → assert it raises (`DRGLoadError` / no
     wholesale rebuild) and writes nothing. This must be proven at the seam because the in-process
     `activate`/`deactivate` path (WP05) bypasses WP03's CLI guard.

## Branch Strategy

- Planning-base / merge-target: `fix/charter-synthesize-reconciliation` (PRs into `main`).
- Execution worktree is allocated per computed lane from `lanes.json` (created by
  `finalize-tasks`); run `spec-kitty agent action implement WP01 --agent <name>`.

## Definition of Done

- [ ] `synthesize` reconciles graph + manifest; default preserves backed content.
- [ ] Committed preservation test green; no-op byte-stability + version-skew tests green.
- [ ] No `--prune` default baked into the library signature; existing callers unaffected.
- [ ] `ruff` + `mypy` clean on touched files; complexity ≤ 15; no new suppressions.

## Risks & Reviewer Guidance

- **Risk**: preserved content will collide/dangle in validation → that is WP02's job; here just
  ensure the merged overlay is handed to validation intact (don't pre-filter it away).
- **Reviewer**: verify the merge reuses `_merge_project_overlay`/`_rewrite_manifest` (not a new
  merge), and that the manifest override is actually passed on the synthesize path.

## 🔴 Post-tasks squad amendments (MUST READ before implementing)

1. **[BLOCKER] Drive the FR-009 post-condition from the MERGED graph, not the fresh emit.**
   The seam guards persist with `if project_graph.nodes:` and then runs
   `apply_post_condition(_repo_root, has_project_graph=emitted_project_graph["value"])`, which
   **unlinks a pre-existing `.kittify/doctrine/graph.yaml`** when `has_project_graph=False`
   (`project_drg.py:265-270`). If you wire the merge inside the existing `if project_graph.nodes:`
   block, an empty/subset current target set (fresh emit has 0 nodes) leaves
   `emitted_project_graph=False` → the post-condition **deletes the preserved graph** — the exact
   P0. Set `emitted_project_graph`/`has_project_graph` from the **merged** graph's nodes; persist
   the merged overlay unconditionally when merged content exists.
2. **[BLOCKER] Corrupt/unparseable on-disk overlay fails closed AT THE SEAM (FR-007).** The
   reconcile load (`load_graph_or_dir`) must abort with **no write** on `DRGLoadError` — never
   fall back to the emit-only rebuild. This guard lives in WP01 (not only WP03's CLI), because the
   in-process `activate`/`deactivate` path (WP05) bypasses the CLI. Add a test.
3. **[BLOCKER] Own conflict detection + populate `delta.conflicts` IN-MEMORY (NO sidecar).** WP01
   owns the `ReconciliationDelta`, so it detects preserved-content conflicts and **populates
   `delta.conflicts` in memory** before returning the delta. There is **NO**
   `.reconcile-conflicts.json` staging file — filesystem IPC inside a single in-process
   `synthesize()` call would contradict the in-memory contract-of-record. Detect via the
   **structured duplicate-`(source,target,relation)` / dangling-endpoint helpers in
   `src/doctrine/drg/validator.py`** — extract `duplicate_edge_triples(graph) -> list[DRGEdge]` and
   `dangling_endpoints(graph) -> list[DRGEdge]` **in `validator.py`** (this WP owns that extraction —
   it is the mission foundation and the first consumer, and WP02 depends on WP01) as the single SSOT
   that BOTH `validate_graph` (string formatting) and `reconcile.py` (provenance classification)
   consume; `validator.py` already states "Exposed rather than copied so there is one definition of
   'dangling'". Do NOT parse `validate_graph` strings and do NOT re-implement the checks in
   `reconcile.py`. Classify each `ReconciliationConflict` by whether the offending
   edge/node is in the current target (emitted → `provenance="new_emit"`) or on-disk∖target
   (preserved → `provenance="preserved"`) set. WP01 also **changes the call site** into
   `validation_gate.validate(...)` to pass the classified conflicts (WP02 widens that signature —
   suppress/raise only). **Define the reconciliation remediation set in `reconcile.py`** with
   DISTINCT kind names — `duplicate_triple` and `preserved_dangling_endpoint` (deliberately NOT
   `merge.py`'s `unresolved_edge_endpoint`, to avoid forking that closed-`Literal` string) — plus
   a completeness test mirroring `merge.py`'s `test_every_conflict_class_carries_a_remediation_line`.
   Do NOT edit `src/doctrine/drg/merge.py` (org-pack layer-merge model; different subsystem, and
   its `_CONFLICT_REMEDIATIONS` has no `duplicate_triple` key).
4. **[MAJOR] Classify backed vs orphaned by probing the filesystem.** `removable`/`retained` must
   distinguish a node whose backing `.kittify/doctrine/**/*.yaml` still exists (backed → preserve)
   from one whose artifact is gone (orphaned → prune/refuse). Populate `backing_artifact` and
   `has_backed_removals` from a real existence check (T001's fields are otherwise never set).
5. **[MAJOR] Atomic write (no lost-update race).** The seam is now read-modify-write; persist the
   merged overlay + manifest via temp-file + `os.replace` (or an overlay lock) so a manual run and
   boundary `auto_refresh` cannot interleave a partial write. Add a regression note.
6. **[MAJOR] Perf gate (NFR-004).** T006 must keep the existing performance-envelope test green
   (≤20% overhead on a ≤200-node overlay); name it in the DoD.
7. **[MINOR] First-run manifest guard (T004).** Seed an empty manifest before `_rewrite_manifest`
   when no on-disk manifest exists (mirror the graph "if present" guard) — first-ever synthesize.
