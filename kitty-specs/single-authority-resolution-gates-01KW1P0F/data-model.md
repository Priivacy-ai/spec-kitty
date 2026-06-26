# Data Model — Single-Authority Resolution Gates (Phase 1)

This mission adds no datastore. The "model" is the set of **resolution-boundary objects**, their authority relationships, and the invariants the gates enforce.

## Boundary objects

| Object | Role | Where | Invariant |
|--------|------|-------|-----------|
| **Handle** | The mission selector: one of `mission_id` (ULID) · `mid8` · `<slug>-<mid8>` dir name · bare human slug · numeric prefix | input to every resolution | A handle is NOT a path; it must be canonicalized to a `dir_name` before composing a primary path |
| **Canonical fold** | `_canonicalize_primary_read_handle(handle) -> dir_name` | `_read_path_resolver.py:1244` | Idempotent; raises `MissionSelectorAmbiguous` on >1 match; fail-closed on cold-miss; NEVER called from inside the primitive (C-001) |
| **Blind primitive** | `primary_feature_dir_for_mission(repo_root, dir_name) -> Path` | `_read_path_resolver.py:1212` | Topology- and handle-blind by design (TBYD); composes the literal dir; must remain blind — input MUST already be canonical |
| **Kind-aware authority** | `commit_for_mission(kind=)`, `resolve_planning_read_dir(kind=)`, `resolve_status_surface_with_anchor` | status/tasks paths | The single decider of coord-vs-primary write/read target for a given artifact kind; a mission-artifact WRITE must route through it |
| **Kind-blind resolver** | `resolve_feature_dir_for_mission` | callers (~58, mostly reads/probes) | Returns `context.feature_dir` (topology-aware but kind-blind); legitimate for reads/probes AND for some by-design coord-owned writes (decision_log, widen); **forbidden for a mandated kind-aware write** |
| **Coordination transaction** | `BookkeepingTransaction` / `workflow.py:_commit_workflow_change` | status/WP bundle commits | Re-anchors coord-owned status writes into the coord worktree so the guard passes by coupling; the model the two #2155 callers must adopt |
| **`safe_commit` guard** | refuses staged path whose 1st segment *relative to `worktree_root`* is `.worktrees/` | `git/commit_helpers.py:983-991` | The #1887 wrong-surface backstop; **NOT modified** by this mission (C-006) |
| **Gate allowlist** | `(enclosing_qualname, token_line) -> rationale` | `tests/architectural/…` | Composite-keyed (net-new; survives line drift); shrink-only vs pre-sweep baseline; every entry must match a live call site (staleness twin-guard) + name an already-canonical provenance |

## Authority relationships

```
WRITE of a mission artifact (tasks.md, status.events.jsonl, …)
   └─ MUST go through ─▶ kind-aware authority (commit_for_mission(kind=) / resolve_planning_read_dir(kind=))
                              └─ decides coord vs primary by artifact kind + topology

Compose of a PRIMARY mission dir from a handle
   └─ Handle ─▶ canonical fold (at the seam) ─▶ dir_name ─▶ blind primitive ─▶ Path
        (folding the fold INTO the primitive recurses — C-001)
```

## State / lifecycle of a gate allowlist entry

`discovered (raw bypass found)` → `sanctioned (added with rationale)` → `retired (site routed through authority → entry removed)`.
- The count only ever **decreases** across the mission (NFR-003, shrink-only).
- A `stale` entry (no longer matching a live site) **fails the build** (the twin-guard) — forcing removal, not silent drift.

## Invariants the gates enforce (testable)

1. **Single authority** — no mission-artifact write composes its target via the kind-blind resolver where the kind-aware authority is mandated (IC-03 gate; FR-003).
2. **Canonical-before-compose** — no un-canonicalized handle reaches `primary_feature_dir_for_mission` (IC-02 gate, scan-by-name; FR-004).
3. **No silent fallback** — every seam raises `MissionSelectorAmbiguous` on ambiguity; cold-miss fails closed-loud (C-002).
4. **Seam-not-primitive** — canonicalization logic never lives inside the blind primitive (C-001, FR-011).
5. **Non-vacuous, shrink-only governance** — each gate has a floor + a self-mutation test; the allowlist only shrinks and carries no stale entries (NFR-002/003).
