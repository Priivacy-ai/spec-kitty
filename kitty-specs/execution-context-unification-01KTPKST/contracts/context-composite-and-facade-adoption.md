# Contract — Context Composite + Facade Adoption (01KTPKST)

Behavioural contracts the implementation must satisfy. These are assertions for the parity ratchet
(IC-08) and per-WP DoD, not API signatures.

## C-CTX-1 — Single resolution
`resolve_action_context(...)` is the ONLY function that resolves a `MissionExecutionContext`. No command
surface re-derives mission state/branch/status/prompt/artifact paths independently.
- **Given** any command surface (specify/plan/tasks/finalize/analyze/implement/review/merge/retrospect)
- **When** it needs a mission's state/branch/status/artifact/prompt location
- **Then** it consumes the resolved context; a static check finds no second resolver (SC-4).

## C-CTX-2 — CWD invariance (parity)
- **Given** the same mission
- **When** the context is resolved from the primary checkout AND from a lane/coord CWD
- **Then** every fragment value is identical (IdentityFragment, BranchRefFragment, StatusSurfaceFragment,
  ArtifactPlacementFragment, WorkspaceFragment.primary_root, PromptSourceFragment).

## C-CTX-3 — mid8 / target_branch single derivation
- `mid8` is derived once in IdentityFragment (`mission_id[:8]`); no other call site recomputes it.
- `target_branch` has one resolution source carried on BranchRefFragment; no surface re-derives it from
  meta.json or git independently.

## C-CTX-4 — No silent fallback (read-path)
- **Given** a mission whose coord surface is missing/misconfigured
- **When** the read-path resolver cannot resolve the feature directory
- **Then** it raises a structured error (e.g. `FEATURE_CONTEXT_UNRESOLVED` / `StatusReadPathNotFound`),
  NOT a silent fallback to the primary checkout returning a wrong-but-plausible dir.
- *(The `decision open` mid8-resolution failure observed during planning is an instance to fix here.)*

## C-FAC-1 — Status facade is the sole status surface
- **Given** any status read or write
- **When** a consumer needs status
- **Then** it goes through `MissionStatus` (`status/aggregate.py`) using the carried StatusSurfaceFragment;
  no raw primary/coord directory reads remain (esp. `status_transition._identity_for_request`).

## C-FAC-2 — Lock-serialized coord resolution
- **Given** concurrent `CoordinationWorkspace.resolve` calls
- **Then** they are serialized; no two callers materialize divergent surfaces (#1357).

## C-PLACE-1 — One artifact-placement ref
- **Given** planning artifacts (spec/plan/tasks/analysis-report) and status events for a mission
- **Then** both resolve to the same `destination_ref` (CommitTarget); under flattened topology
  `kind == flattened` and there is no primary↔coord placement split.
- record-analysis (#1814) and implement-claim (#1816) must not deadlock/stall on placement.

## C-RT-1 — Runtime writers respect git ops
- **Given** an in-progress git op (rebase/reset) on a mission branch
- **When** a daemon/dashboard would `materialize_if_stale`
- **Then** it does NOT re-materialize tracked status during the op (#1789/#1062); and the staleness key
  is context-aware so it does not false-positive across CWDs (#1764).

## C-DEL-1 — Strangler-ordered deletion (burn-down C-004)
- A surface is deleted only AFTER its consumers are converted and the parity ratchet is green.
- Applies to: duplicate read-path resolver (IC-03), `root_resolver` parser (IC-04), 5 dead
  `status_service` symbols (IC-09). Never delete-then-rewire.

## C-OMAP-1 — Occurrence-map backward compatibility (IC-10, #1815)
- **Given** an existing single-term occurrence-map (8 categories, no `moves:` block)
- **Then** it validates and gates exactly as before the schema extension.
- **Given** a map with a `moves:` block (multi-path structural moves)
- **Then** the implement-gate validates the move mappings and the reference-integrity check covers them.
