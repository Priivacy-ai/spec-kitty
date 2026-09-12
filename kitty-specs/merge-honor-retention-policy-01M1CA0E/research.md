# Research: Merge Honors Mission Retention Policy (#3131)

No NEEDS CLARIFICATION markers remain; the design was resolved by a profile-loaded
scout squad (2 lenses) and an adversarial squad (2 lenses) against live code.
This document records the decisions, rationale, alternatives, and the adversarial
evidence dispositions per `contracts/adversarial-evidence-contract.md`.

## Decision 1 — Retention authority location

- **Decision**: Persist retention in mission `meta.json` as two flat booleans
  `retain_branches` / `retain_worktrees` (added to `MissionMetaOptional`).
- **Rationale**: `meta.json` is the only per-mission policy store `merge`
  already reads (`target_branch`, `coordination_branch`, `merged_push`,
  `topology`), with a validated single-writer (`write_meta`) and fail-closed
  reader (`load_meta_fail_closed`). `validate_meta` preserves unknown fields, so
  two flat bools round-trip cleanly and match the flat convention; they map 1:1
  to the two independent cleanup flags.
- **Alternatives considered**:
  - *Parse a prose constraint (C-005 style)* — rejected: mission constraints are
    unstructured prose; only requirement-ID token matching exists
    (`requirement_mapping.py`), never a value. Fragile, unvalidated,
    charter-prohibited improvisation.
  - *Explicit merge flag only* — rejected as authority: no persisted per-mission
    default, so a mission cannot express standing intent — exactly the #3131
    failure. Retained as the enforcement surface.
  - *Nested `retention: {branches, worktrees}` block* — rejected: would be the
    only nested policy block in `meta.json`; flat is more consistent and models
    the two independent resolutions directly.
  - *Project-level `config.yaml` default* — deferred to a separate mission:
    a repo-wide retain flag has a broader blast radius than the per-mission bug
    and recreates the silent-override failure at another layer.

## Decision 2 — Resolution precedence, provenance, and partition

- **Decision**: One pure `resolve_merge_retention(...)` in `core/paths.py`,
  precedence `explicit CLI flag > meta.json retention > default`, returning
  resolved booleans + `source` provenance, mirroring `resolve_merge_target_branch`.
  It reads the PRIMARY partition (`primary_meta_dir`) and is called once in the
  UNLOCKED `_run_lane_based_merge`; the forecast reuses the same function.
- **Rationale**: Retention is a PRIMARY-partition per-mission policy exactly like
  `target_branch`. The locked driver's `feature_dir` is the coord STATUS husk
  (no `meta.json` for coord topology) — resolving there would silently fall back
  to delete, the exact partition trap the target-branch resolver was written to
  avoid. Resolving once in the unlocked driver (downstream of the resume branch)
  honors fresh + `--resume` exactly once with no double-resolution.
- **Alternatives considered**: *Resolve in the locked driver / `_MergeRunState`
  build* — rejected (husk trap). *Resolve in the CLI layer only* — rejected: the
  forecast bypasses the CLI-effect path and would diverge; a single pure fn with
  two call sites avoids two implementations.

## Decision 3 — Tri-state flags & fail direction

- **Decision**: `--delete-branch/--keep-branch` and
  `--remove-worktree/--keep-worktree` become `Optional[bool]` default `None`.
  `None` consults meta; explicit `True`/`False` wins. Fail closed toward
  retention: meta retain + no explicit override → keep + warn; explicit delete
  override on a retaining mission → delete + recorded override notice; malformed
  (non-boolean) retention value → retain + warn (never truthiness-coerced).
- **Rationale**: A `bool` default `True` cannot distinguish "operator chose
  delete" from "operator said nothing" — the root ambiguity behind #3131. Tri-state
  resolves it. Fail-closed toward retention is mandatory for a data-loss fix.
- **Migration risk**: existing internal callers pass explicit `True`/`False`
  (unaffected). `orchestrator_api/commands.py` merge entry hard-codes cleanup
  intent — audited (C-007). Forecast + its golden-key test updated.

## Decision 4 — Coupled coordination-topology teardown (BLOCKER-1)

- **Decision**: The coord marker-flatten (`executor.py:1557`) and coord-worktree
  destroy (`executor.py:1570`) are driven by ONE coord-retention value: tear down
  the coordination topology only if BOTH `delete_branch` and `remove_worktree`
  resolve to delete/remove; otherwise retain the whole triple.
- **Rationale**: The coordination branch, worktree, and `coordination_branch`
  marker are one consistency unit. Independent resolution would manufacture the
  #2062 `coord`-empty / husk hazard that later resolves treat as corruption.
- **Alternatives considered**: *Gate each half by its own flag* — rejected
  (half-torn topology). *Always tear down coord regardless of retention* —
  rejected (destroys a retained worktree).

## Decision 5 — Abort path honors retention (BLOCKER-2)

- **Decision**: `_teardown_coordination_for_abort` consults the same
  coord-retention decision and skips + warns for a worktree-retaining mission.
- **Rationale**: `merge --abort` destroying the coord worktree the mission asked
  to keep is a silent-deletion bypass that would make NFR-003/SC-002 false.
- **Alternatives considered**: *Scope abort out with a documented rationale +
  regression proving the coord worktree survives* — kept as the fallback if
  honoring proves to break rollback correctness; the plan's default is to honor.

## Decision 6 — Scratch worktree stays ungated (C-006)

- **Decision**: `cleanup_merge_workspace` (internal `.kittify/runtime/merge/<id>/workspace`)
  keeps running unconditionally; retention does NOT gate it.
- **Rationale**: It is merge-internal plumbing (detached HEAD scratch worktree on
  a different path from lane worktrees); retaining it would leak a registered git
  worktree. `state.json`/`lock` are already preserved for resume.

## Decision 7 — Create-time mint (FR-009)

- **Decision**: `create_mission_core` gains keyword-only
  `retain_branches=False`/`retain_worktrees=False`; mint site writes each field
  only when true. CLI `mission create` gains `--retain-branches`/`--retain-worktrees`.
- **Rationale**: Closes the loop that made #3131 possible (retention lived only
  as prose). Field-absent-when-false keeps non-retaining missions byte-identical.

## Adversarial Evidence (planning point-cut)

Per `contracts/adversarial-evidence-contract.md`. Two lenses ran post-spec.

| Finding (source) | Severity | Disposition |
|------------------|----------|-------------|
| Partial retention splits coord triple → half-torn topology (data-loss lens) | BLOCKER | **changed** — FR-011 + D-4 coupled coord teardown |
| `merge --abort` destroys retained coord worktree (data-loss lens) | BLOCKER | **changed** — FR-012 + abort honors retention |
| Malformed non-boolean retention value truthiness-coerced to delete (data-loss lens) | MAJOR | **changed** — NFR-001 extended, malformed-value edge case |
| Regression vacuously green (planning lane / scratch worktree) (data-loss lens) | MAJOR | **changed** — NFR-002 non-vacuous: coord mission, non-planning lane, `.worktrees/` paths |
| Do NOT gate `cleanup_merge_workspace` (data-loss lens Q1) | MINOR | **accepted** — C-006, ungated by design |
| Retrospective persistence must stay unconditional (data-loss lens) | MINOR | **accepted** — edge case note |
| Flat bools over nested block (canonical lens Q1) | — | **accepted** — C-003 flat fields |
| Resolve from primary_meta_dir, not locked husk (canonical lens Q2) | BLOCKER-class | **changed** — D-5 |
| No config.yaml tier (canonical lens Q3) | — | **accepted** — C-002 defers it |
| Tri-state migration + forecast needs resolver + audit orchestrator_api (canonical lens Q4) | MAJOR | **changed** — C-007, forecast reuse |
| retain⇔keep terminology mapping documented (canonical lens Q5) | MINOR | **accepted** — C-004 |

No contested finding was silently dropped.
