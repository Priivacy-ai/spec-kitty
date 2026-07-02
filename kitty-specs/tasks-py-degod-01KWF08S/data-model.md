# Data Model — Degod tasks.py (Wave 1)

Phase 1 output. This is a refactor, so the "entities" are the **port protocols**, the **pure
decision/aggregation value objects**, and the **characterization contract** — not persisted data.
Signatures are indicative (the plan, not the code); the real types land in WP02/03/04/05.

## Ports (`tasks_ports.py`)

Injected via `*, ports: TasksPorts | None = None` at the extracted-orchestrator boundary (C-005).
Each protocol has a Real adapter (production) and a Fake (tests). **Stratified** (D2):

### Program-reference ports (Wave 2 reuses these)

**`FsReader`** — coord **READ** authority (C-001). Wraps the kind-aware read seam; never conflates with write.
- `planning_read_dir(mission, *, kind) -> Path` — via `resolve_planning_read_dir` (folds canonicalization internally).
- `wp_tasks_dir(mission) -> Path`, `primary_anchor_dir(mission) -> Path` — the blind primitive stays **inside** the adapter, co-located with its `_canonicalize_primary_read_handle` fold (C-002).

**`CoordCommitRouter`** — coord **WRITE** authority, **two capability methods over two disjoint seams** (D2; NOT a fused `commit()`).
- `feature_write_dir(mission) -> Path` — via `resolve_feature_dir_for_mission` (the coord-husk write leg).
- `commit_status(mission, event, *, capability) -> CommitStatusResult` — over `emit_status_transition_transactional` (keyed `GuardCapability`); self-atomic via `BookkeepingTransaction`. Encodes the coord skip-exit-0 decision as `CommitStatusResult.skipped` (no side-effect fork in the caller). Used by `implement.py` and `move_task`.
- `commit_artifact(mission, paths, message, *, kind, policy) -> CommitArtifactResult` — over `commit_for_mission` (keyed `MissionArtifactKind` + `ProtectionPolicy`), **event-less**. Used by `acceptance` (protected-primary routing) and `move_task`.
- *(Result types renamed off `CommitResult` — collides with `git/commit_helpers.py:424`.)*

### Mission-local seams (NOT program-reference; #2173 DROPs; test scaffolding only)

**`GitOps`** — porcelain/rev-parse reads used by tasks.py only.
**`Render`** — dual-arm: `human(view) -> None` (rich tables/panels) **and** `json_envelope(payload) -> str` (the **13** `json.dumps` sites). tasks.py holds 0 inline `json.dumps` post-WP09 (AST-verified, alias-proof).

## Pure decision / aggregation cores

**`TransitionDecision`** (`tasks_transition_core.py`, from `move_task`) — **reproduces move_task's exact current behavior** (D4; no cross-command change).
- Input: `TransitionRequest(from_lane, to_lane, wp_id, actor, topology, protected_target, ownership, verdict_state, feedback_ptr, force, arbiter, review_currency, planning_artifact_wp)`.
- Output: `TransitionOutcome = Emit(event, commit_paths, skip_primary: bool) | SkipExit0(reason, json_keys) | RefuseExit1(error)`.
- Pure: no I/O; the caller (orchestrator) executes the outcome through ports. `skip_primary` encodes the coord skip-exit-0 arm; `RefuseExit1` carries the guard failures (agent-ownership, rejected-verdict, protected-branch-without-skip, feedback-required, done-override).

**`MappingPlan`** (`tasks_mapping_core.py`, from `map_requirements`) — pure FR↔WP mapping/validation.
- Input: `MappingRequest(spec_fr_ids, wp_refs, mode: wp_refs | batch | tracker_only, replace: bool)`.
- Output: `MappingPlan(to_write: dict[wp, refs], offenders: {malformed, unknown_spec_id}, unmapped_fr)`; the frontmatter write is a port side-effect the orchestrator applies.

**`StatusView`** (`tasks_status_view.py`, from `status`) — pure aggregation (D6; the missing core the sizing squad flagged).
- Input: `StatusRequest(events, workspaces, threshold, clock, dependency_graph)`.
- Output: `StatusView(lanes: kanban rollup, stale: verdicts, progress: percentages, dependency_readiness)`; rendering is the Render port's job.

## Characterization contract (IC-01)

**`TasksGoldenContract`** — the frozen behavioral snapshot the harness asserts:
- per subcommand (×9): the flag/option surface (help introspection), exit codes {0,1,2}, and the `--json` top-level keys.
- for the mutating commands under a **coord-topology + protected-branch fixture**: the skip-exit-0 arm vs the exit-1 refuse arm, the *conditional* `--json` keys (`wp_file_update`, `status_events_path`, `review_feedback`), and the side-effect set (coord-vs-primary event path, WP-file write, tracker-ref frontmatter, review-artifact override to both dirs).
- Normalizers: ULIDs/timestamps/paths (existing) — must never widen enough to mask the skip-arm keys.

## Invariants

- **INV-1** CoordRead (`FsReader`) and CoordWrite (`CoordCommitRouter`) are never the same object/path (C-001).
- **INV-2** coord status emission occurs only via `CoordCommitRouter.commit_status(...)`, never as a raw standalone `emit_status_transition` call from a command body. Atomicity is guaranteed **inside** `emit_status_transition_transactional` (`BookkeepingTransaction`), so `commit_status` is a co-equal capability, not a hidden sub-step of `commit_artifact` (D2, corrected).
- **INV-3** The blind primitive is called only inside `FsReader`, co-located with its canonicalization fold (C-002).
- **INV-4** Cores are pure: given the same request, identical outcome, no I/O (verifiable with Fakes).
- **INV-5** Every `TransitionOutcome`/`MappingPlan`/`StatusView` branch is reachable from a golden-frozen input (NFR-002).
