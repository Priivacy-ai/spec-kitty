# Research: Write-Side Seam: Matrix & Tracer Writers

Phase 0 output. Most unknowns were resolved by two profile-loaded grounding squads (see [`pre-planning-ledger.md`](./pre-planning-ledger.md)); this file records the decisions that shape the design.

## D-1 — This is an adoption mission, not a construction mission
- **Decision**: Extend the existing write seam (`PlacementSeam.write_target(kind)` → `resolve_placement_only`) at bypassing call sites; do not build a new resolver.
- **Rationale**: The seam predates #3060 (ADR `2026-06-24-1`); its C-006 explicitly rejects a parallel write-only resolver. Metric: ~80 seam-routed reads vs ~3 seam-routed writes — the gap is adoption.
- **Alternatives rejected**: A new write resolver (ADR-forbidden, re-leaks the read-side defect three times).

## D-2 — Matrix storage format = JSON, single canonical artifact (Decision `plan.matrix.storage-format`)
- **Decision**: Both matrices are JSON. `issue-matrix.json` becomes the single canonical artifact; **no `issue-matrix.md` render** — the dashboard parses JSON directly.
- **Rationale**: Consistency with the existing `acceptance-matrix.json` and the JSON-parsing merge drivers; a duplicate markdown render only confuses operators/agents.
- **Alternatives rejected**: YAML (diverges from acceptance-matrix, second format for drivers/readers); dual JSON+markdown (duplicate source of truth).

## D-3 — Back-compat = migrate-on-write + failover-read + bulk command (Decision `plan.matrix.issue-backcompat`)
- **Decision**: A shared migration sub-module: (a) **failover-read** the legacy `issue-matrix.md` when `issue-matrix.json` is absent; (b) **migrate-on-write** — the first structured write converts a mission to JSON; (c) a dedicated **bulk-migration command** for one-shot swap-over, using the same sub-module.
- **Rationale**: No in-flight consumer mission breaks; the migration logic is authored once and reused (FR-013).
- **Alternatives rejected**: Forward-only (in-flight missions lose the new tooling); a permanent dual-format reader (drift risk).

## D-4 — Row-aware matrix merge driver on structured JSON (FR-008)
- **Decision**: Replace the whole-file `_write_more_filled_side` acceptance/issue-matrix drivers with **row-aware** drivers that union disjoint rows keyed by a stable row identity.
- **Rationale**: Grounding refuted the "already row-aware" assumption — the current drivers clobber the lower-scoring side when two lanes fill disjoint rows. Structured JSON (D-2) makes row-level merge tractable and testable in isolation.
- **Alternatives rejected**: Keep "more-filled-side" (satisfies #2482 stale-residue only, not the disjoint-row gap); markdown row-merge (fragile).

## D-5 — FR-009 lane base = recorded planning-artifact SHA (new ADR)
- **Decision**: Branch execution lanes from the **recorded finalize-tasks tip** (captured in `lanes.json`/`meta.json`), not the pre-planning coordination tip nor a moving `target_branch` tip. A new ADR (amending `2026-04-03-1`) governs this and MUST resolve whether the base also carries coord-status lineage.
- **Rationale**: The coord branch is minted before planning artifacts exist, so lanes lack a common ancestor with the consolidation base (#2993). Pinning to a recorded SHA avoids the moving-tip guard trap; a moving tip would re-introduce base-strand bugs.
- **Alternatives rejected**: Branch from current `target_branch` tip (moves; guard-strand); keep coord tip (the defect itself).
- **Constraint**: No consolidation-time abort path (ADR `2026-07-23-2`); `merge/ordering.py` is a pure frontmatter topo-sort and is untouched.

## D-6 — FR-010 kept to "Move A" by design
- **Decision**: Design the new writers to route COORD dirs **purely** through `write_target`/`commit_for_mission`. The coord-authority gate scans only `resolve_feature_dir_for_mission`, so seam-routed writers are invisible to it — FR-010 reduces to **Move A** (route `decisions/emit.py` off the allowlist; re-pin census floor 4→3). Move B (widening the gate predicate) is only authored if a writer must resolve via the kind-blind resolver.
- **Rationale**: Move A strengthens the gate (one fewer sanctioned bypass); avoiding Move B avoids predicate-widen risk. If Move B is unavoidable, it must be def-use gated with an alias-bite non-vacuity test.
- **Alternatives rejected**: Widen the gate by module/name proxy (weakens it; ADR `2026-06-26-1` confirmation criterion forbids a vacuous gate).

## D-7 — FR-011 = zero-write refusal on unroutable writes
- **Decision**: On a deleted `target_branch` / missing coord surface, the write **refuses** with a structured, recoverable result that discloses #3033 as the deferred real fix — never a fallback write, never a consolidation abort.
- **Rationale**: The existing degrade path falls back to writing the configured primary (`main`), resurrecting a closed defect and foreclosing #3033's `CONSOLIDATED`-surface decision (ADR `2026-07-23-2`: refuse rather than fabricate a surface).
- **Alternatives rejected**: Reuse the fallback-write degrade (regression); implement the post-merge mode here (#3033 out of scope, C-006).

## D-8 — One-seam discipline (enforced across the writer concerns)
- **Decision**: One write-surface resolution + one materialization authority + parameterized scanner/writer cores with thin per-kind wrappers.
- **Rationale**: FR-001 confirms the pattern is clean (computed verdict property, no re-authoring). Giving FR-001/003/006 independent compute-and-commit paths reproduces the pre-#3060 read-side leak three times.
- **Alternatives rejected**: Per-writer bespoke compute+commit (whack-a-field regression).

## Out-of-scope confirmations (C-006)
- Post-merge write mode #3033 (FR-011 guards only); finalize-tasks cluster; status-writer *behavioural* unification (only #3027's mark-status-roster campsite is in-core); review-verdict integrity P0s (#3044); mission-card-as-alternative-source #1742/#1740 (`at_tension_with`; this mission commits to the scanner + structured-artifact path).
