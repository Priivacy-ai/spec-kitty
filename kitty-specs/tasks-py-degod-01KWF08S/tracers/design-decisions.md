# Tracer: Design Decisions

**Mission**: tasks-py-degod-01KWF08S
**Created**: 2026-07-02 (retrospectively at close — not seeded at planning; captured from the implement-loop history)
**Lifecycle**: seed at planning → append during implement → assess at close (experiment #2095)

The load-bearing design decisions + their rationale (the ones a future maintainer / the follow-up mission must respect).

## Port design

- **Coord WRITE is a TWO-CAPABILITY port, not a fused `commit()`.** `CoordCommitRouter.commit_status(event,*,capability)` (over `emit_status_transition_transactional`, `GuardCapability`, self-atomic via `BookkeepingTransaction`) + `commit_artifact(paths,message,*,kind,policy)` (over `commit_for_mission`, event-less). Rationale (architect squad, verified against live Wave-2 seams): the three Wave-2 consumers use **disjoint halves** — `implement.py`=commit_status only, `acceptance`=commit_artifact only (it IS a writer — the earlier "acceptance does zero writes" premise was factually inverted), `move_task`=both. A single fused `commit()` would be re-cut in Wave 2. StatusEmit atomicity lives in the transactional emitter, NOT in port packaging — so `commit_status` is a co-equal capability, not a hidden sub-step.
- **CoordRead ≠ CoordWrite** (C-001): `FsReader` (READ) and `CoordCommitRouter` (WRITE) are distinct ports; the split is proven by capability-disjointness.
- **C-002 canonicalizer fold co-located** inside the `FsReader` adapter method (the gate's def-use check is intra-function; splitting turns it RED). `primary_anchor_dir` is the named consumer of the `map_requirements` fold (WP07).
- **Port-seam adapters bound to `tasks.py` module symbols** (`_MoveTaskCoordRouter`/`_MapReqCoordRouter`/`_MarkStatusCoordRouter`/`_StatusRender`) so the ~900 existing `@patch("...tasks.<sym>")` seams keep intercepting. A deliberate parity-preservation choice; the follow-up mission decides whether to keep or re-point it when relocating.

## Extraction discipline

- **Delete-not-shadow + sentinel.** Wiring a core into a command DELETES the inline decision block (not a discarded call beside it) and ships a fake-core sentinel test proving the core's return value DRIVES observable behavior. "grep-for-callers" is insufficient (a result-discarding call passes it).
- **Reproduce, do NOT unify.** move_task skips-exit-0 where mark_status/map_requirements refuse-exit-1 — the divergence is PRESERVED (deferred to #2300), not reconciled. WP08 added a **structural non-import AST gate** (with a positive control) so mark_status/finalize can't be thinned by borrowing move_task's core.
- **Side-effect TIMING is parity-critical.** Guard-consolidation must NOT move durable side-effects relative to later-guard refusals: move_task's override/arbiter persists fire at their OLD guard positions (via pure guard-slice signals) so a partial-write-on-refusal is preserved; map_requirements writes frontmatter BEFORE its post-merge stale-refs gate (partial-write preserved). Each pinned by a red-first regression test.
- **Per-core `--cov-branch`** with the branch set enumerated FROM the golden harness (not implementer intuition); the per-core unit test is the C-011 failing-first artifact for these pure-parity WPs.

## FR-010 (pre-3.0 read-authority fold)

- **NOT one-size.** Guard-outcome equivalence (the reads feed a no-op pre30 guard), not dir-equivalence. Per-site pin table (proven in WP02): `finalize_tasks:2373` + `list_dependents:3568` are guard-only (var reassigned right after) → `WORK_PACKAGE_TASK`→primary; **`move_task:1138` is a SHARED coord-status var** (feeds `_read_transactional_wp_lane` + review-override persist, never reassigned) → **stays coord-husk / `STATUS_STATE`** (repointing it = split-brain regression). A red-first hazard test pins it.

## Census / ratchet

- **Shrink-only** (DIRECTIVE_043): the census may only go DOWN. Rewires drain write-classified sites → census 12→9; the floor lowers to match (never raise); stale `(qualname, line)` entries are re-pinned (moved) or drained (removed), each justified by the cross-base diff + reviewer sign-off. Never ADD an allowlist entry to pass a gate.

## Scope

- **Descoped to a follow-up mission** (8/9 decision): the Render seam (former FR-008: 13 json.dumps → Render port + AST gate + status-indent unification) and the whole-file ≤1400 shim relocation (former SC-005/NFR-004). Rationale: core value (decision logic → tested cores, bodies thinned, byte-identical) complete at 8 WPs; the ~3150-LOC relocation is low-risk-per-move but large + orthogonal → its own reviewed mission. See `docs/plans/tasks-py-degod-followup-mission-debrief.md`.
