# Data Model: Runtime-Bridge Decomposition

New types introduced by the decomposition. No persisted/serialized schema changes — these are in-process seam contracts. Full grounding in research.md §Seams.

## ArtifactPresenceSnapshot (FR-009 — the guard fact-port output)
A plain, I/O-free value object carrying the filesystem/status facts the guards need, gathered once by the port so `evaluate_guards` can be pure.
| Field | Type | Notes |
|-------|------|-------|
| `present_artifacts` | frozenset[str] | which mission artifacts exist (spec/plan/tasks/…) |
| `status_facts` | Mapping | status-log / bulk-edit / requirement-mapping facts the guards read |
| `mission_family` | str | software-dev / research / documentation (drives the fail-closed default) |
| `step_id` / `legacy_step_id` | str | the step under evaluation |
Produced by `gather_artifact_presence(feature_dir, …)` (port, `runtime_bridge_io.py`). Consumed by `evaluate_guards(snapshot) -> list[str]` (pure, `runtime_bridge_cores.py`).

## DecisionEnvelope + step_or_blocked (FR-011 — the Decision-builder core)
Collapses the 29 open-coded `Decision(...)` constructions + the 4× `_state_to_action → _build_prompt_or_error → step-or-blocked` triad.
- `DecisionEnvelope` — the normalized inputs a `Decision` is built from (kind, agent, mission identity, state, action, wp_id, step_id, guard_failures, progress, question/options, …).
- `step_or_blocked(envelope, guard_failures, *, prompt_exists) -> Decision` — the **blocked/query/terminal branch is pure**; the **step branch is port-injected**. `Decision.__post_init__` (`decision.py:129`) runs `Path(prompt).is_file()` for `kind="step"`, so constructing a step Decision is intrinsically I/O-bearing and the builder cannot be pure for that branch. The step-existence check is injected as a `prompt_exists: Callable[[str], bool]` predicate (real `Path.is_file` in production; an in-memory stub in the pure unit test) so the core stays deterministic and NFR-003/SC-004-testable. All non-deterministic fields (timestamp/ULIDs — see contracts/parity-oracle.md) are stamped by the caller/residual, NOT the builder (`timestamp` is a required field threaded from `bridge:2542`).

## DecideNextContext (FR-010 — residual phase-split state)
A frozen dataclass (~14 fields, per #2464 Decision 6) threading the shared locals through the 4 phases so `decide_next_via_runtime` becomes a linear early-return chain.
- Phases: **bootstrap** → **dependency-gate** → **composition-dispatch** → **decision-materialize**, each `(ctx) -> Decision | None`.

## Engine-adapter surface (FR-013)
`runtime_bridge_engine.py` — the single seam wrapping the `_internal_runtime` privates (`_read_snapshot`, `_load_frozen_template`, `_append_event`, `_write_snapshot` from `.engine`; `plan_next` from `.planner`). **Site list is grep-complete, not the earlier 5-site sample** — it MUST include the `_load_frozen_template` accesses at `:1322` (`_resolve_step_binding`) and `:1375` (`_resolve_step_agent_profile`), in addition to `:1800`/`:1840`/`:2606`/`:3261`/`:3416`. No core imports engine internals (arch-guarded: FR-013 requires ALL engine-private access concentrated here). `_advance_run_state_after_composition` (CC23; duplicates the engine's `next_step` success branch) is **adapter logic** — its body lives in the engine adapter (reducing it ≤15), reconciling the compat requirement via a **thin residual delegate** kept at `runtime_bridge._advance_run_state_after_composition` for the heavy patch/attr surface (see contracts/compat-surface.md). This supersedes the earlier "KEEP-IN-PLACE in the residual" note: the residual keeps only the compat shim, the logic is adapter-owned.

## Ports (runtime_bridge_io.py — I/O boundaries)
- `feature-runs.json` index: `load_feature_runs(path) -> dict` / `save_feature_runs(path, dict)` (textbook narrow port).
- template/pack discovery; run lifecycle (start/lookup); operational-context builder.
- `resolve_commit_target(...)` — the **pure** decision lifted out of `_wrap_with_decision_git_log:226–261` (the one port that interleaved a pure decision inside I/O).

## Identity port (runtime_bridge_identity.py — extracted LAST)
Coord-branch naming + mission-ULID + primary-feature-dir resolution. Correctness-critical (malformed coord branch → `git worktree` exit-128). Several of its symbols are KEEP-IN-PLACE for the compat surface (contracts/compat-surface.md).
