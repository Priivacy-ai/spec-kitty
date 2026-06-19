# Mission Specification: Single Mission-Surface Resolver

**Mission slug**: `single-mission-surface-resolver-01KVGCE8`
**Mission type**: software-dev (refactor / consolidation — strangler)
**Target / merge branch**: `feat/single-mission-surface-resolver` → `main` (via PR)
**Status**: Draft
**Source**: GitHub #2040 (residual of closed #2010; epic #2007)

## Purpose

When a mission's **coordination worktree** and **primary checkout** hold divergent
on-disk artifacts, several spec-kitty commands resolve the **wrong** surface — the
recurring read/write desync (#2007 / #2010 / #1716) that repeatedly disrupted even
this project's own mission loops (lane-vs-primary status divergence, forced
flattening). The root cause is that the *selection* decision — *given a valid slug,
which divergent surface is authoritative?* — is duplicated across **4+ parallel
resolvers** that are **not behavior-equivalent across input classes** (#2010's own
unclosed caveat).

This mission **strangles those resolvers down to one canonical mission-surface
resolver**, proven safe to consolidate by a cross-resolver equivalence test and
locked by a load-bearing architectural guard. It is the *selection* counterpart to
the *validation* seam already shipped by mission `untrusted-path-containment-hardening`
(01KVFTFV), and it reuses that mission's audit + guard scaffolding.

## User Scenarios & Testing

**Primary actor:** any spec-kitty command/runtime that locates a mission's on-disk
surface (status read, `next`, review, merge, materialize).

**Primary scenario (must become consistent):** A mission whose coord worktree and
primary checkout diverge is acted on by several commands. Today they can disagree on
which directory is authoritative. After this mission, **every** entry point routes
the single canonical resolver and agrees on the same directory (or the same typed
error) for the same `(slug, mid8, topology)`.

**Coord-empty scenario (the decided policy — hard-fail):** A coordination worktree
exists but is **materialized-but-empty** (created, no status yet). The resolver
**hard-fails** with `STATUS_READ_PATH_NOT_FOUND` whose message instructs the operator
to either (a) **collapse/flatten** the mission (drop `coordination_branch`) **or**
(b) **recreate/populate** the coordination branch. It does NOT silently fall back to
primary. (Distinct from the *no-coord* case — a mission with no coordination branch at
all — where the primary checkout is the sole, authoritative, non-divergent surface.)

**Exception / edge cases:**
- `--mission <mid8>` ambiguous → single typed `MISSION_AMBIGUOUS_SELECTOR` from the one
  resolver (no silent first-match), preserved through `next` (not flattened to
  `MISSION_NOT_FOUND`).
- A new callsite joins `repo_root / KITTY_SPECS_DIR / <slug>` directly, bypassing the
  resolver → fails CI (the guard).
- Create→first-write window (primary has spec, coord not yet created) → primary
  authoritative; NOT a coord-empty hard-fail.

## Domain Language

| Canonical term | Meaning | Avoid |
|----------------|---------|-------|
| mission-surface resolution (**selection**) | choosing *which* divergent on-disk surface (coord worktree vs primary checkout) is authoritative for a mission | "path resolution" (conflates with validation) |
| canonical resolver | the single seam that owns surface selection (`resolve_status_surface_with_anchor`) | "a resolver" (implies many) |
| topology-blind-by-design | a deliberately primary-only resolver (e.g. for `meta.json` reads) — legitimate, not a desync | "raw bypass" |
| raw-bypass | a callsite that joins `repo_root/KITTY_SPECS_DIR/<slug>` itself instead of routing the resolver | — |
| materialized-but-empty coord | a coordination worktree that exists but holds no status surface yet | "missing coord" (that is no-coord) |

## Requirements

### Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | A **single canonical mission-surface resolver** (`resolve_status_surface_with_anchor`, or the chosen owner) MUST be the sole authority for coord-vs-primary surface selection; every mission-surface read MUST route through it (directly or via a blessed delegator). | Draft |
| FR-002 | A **differential equivalence test** MUST feed the same `(slug, mid8, topology)` matrix to every resolution entry point and assert each returns an **identical directory OR identical typed error**. This test MUST pass before any duplicate resolver is deleted (the safety gate). | Draft |
| FR-003 | A **reproducible audit** (repointing the 01KVFTFV AST walker, `tests/architectural/untrusted_path_audit/audit.py`) MUST enumerate every mission-surface-resolution callsite, classified `routed-through-resolver` / `topology-blind-by-design` / `raw-bypass`, recorded so a reviewer can re-run it. | Draft |
| FR-004 | A **load-bearing architectural guard** (cloning `test_untrusted_path_containment.py`) MUST fail when a `raw-bypass` join is introduced outside the canonical resolver/delegator set; proven load-bearing by a real-code mutation + non-empty coverage assertion. | Draft |
| FR-005 | **Typed-error pass-through (#2010 bug #15)**: `STATUS_READ_PATH_NOT_FOUND` and `MISSION_AMBIGUOUS_SELECTOR` MUST be preserved end-to-end through `next` / `mission_runtime` instead of being flattened to `MISSION_NOT_FOUND`. (No resolver change — the cheapest first behavioral slice.) | Draft |
| FR-006 | **Coord-empty hard-fail policy (#1716)**: a materialized-but-empty coordination worktree MUST hard-fail with `STATUS_READ_PATH_NOT_FOUND` whose message instructs the operator to either collapse/flatten the mission OR recreate/populate the coordination branch — never a silent primary fallback. The decision MUST be recorded in an ADR and bound to the single resolver. | Draft |
| FR-007 | **Collapse to one resolver**: `aggregate._resolve_read_dir` MUST become a thin adapter over the canonical resolver (dropping its duplicate re-gate); the C-004 `missions/feature_dir_resolver.py` re-export shim MUST be retired (callers migrated). No parallel selection logic remains. | Draft |
| FR-008 | **Single mid8 disambiguation**: `aggregate._find_meta_path`'s silent-first-match `glob("{slug}-*/meta.json")` MUST be eliminated and routed through the one canonical handle resolver, so `--mission <mid8>` resolves identically everywhere (closes the S8 selection ambiguity). | Draft |

### Non-Functional Requirements

| ID | Requirement | Threshold / Measure | Status |
|----|-------------|---------------------|--------|
| NFR-001 | New/changed code passes the quality gates. | `ruff` + `mypy --strict` 0 errors on changed files; no new `# noqa`/`# type: ignore`; complexity ≤ 15. | Draft |
| NFR-002 | No regression for the non-divergent happy path. | 100% of pre-existing status/merge/next/agent suites pass unchanged. | Draft |
| NFR-003 | Behavior-equivalence is provable, not asserted. | The FR-002 differential test covers ≥ the (no-coord, coord-fresh, coord-behind, coord-empty, ambiguous-mid8) input classes; each guard/fix carries a mutation-killing test. | Draft |
| NFR-004 | Errors are actionable. | The coord-empty hard-fail message names both recovery paths (collapse OR recreate/populate); 0 silent fallbacks on the divergent path. | Draft |

### Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | MUST reuse the 01KVFTFV audit AST walker and load-bearing guard pattern — do not fork new tooling. | Draft |
| C-002 | Migrate, don't wrap: collapse the existing resolvers; MUST NOT add a new parallel resolver/shadow path (the #1993 risk). | Draft |
| C-003 | MUST NOT prescribe a version/patch number (focus/milestone framing; PO assigns at release). | Draft |
| C-004 | The FR-002 equivalence test MUST be green before deleting any duplicate resolver (deletion safety gate). | Draft |
| C-005 | Cite related artifacts/findings by canonical id/issue number. | Draft |

## Success Criteria

- **SC-001**: The differential equivalence test is green across the (slug, mid8, topology) matrix — all entry points agree on dir-or-typed-error.
- **SC-002**: Introducing a raw-bypass join makes the architectural guard FAIL (mutation-verified); removing the guard makes that fixture pass.
- **SC-003**: A reproduction of #2010 bug #15 (typed error flattened through `next`) is shown failing pre-fix and passing post-fix (`STATUS_READ_PATH_NOT_FOUND`/`MISSION_AMBIGUOUS_SELECTOR` preserved).
- **SC-004**: The known desync symptoms (#1716 stale-coord, lane-vs-primary divergence) are reproduced then closed.
- **SC-005**: The audit shows **0 `raw-bypass`** callsites; exactly one resolver owns surface selection (others are thin adapters / topology-blind-by-design / retired).
- **SC-006**: The coord-empty hard-fail emits the actionable two-path message; no silent primary fallback on a divergent surface.

## Key Entities

- **Canonical mission-surface resolver** — the single seam owning surface selection.
- **Resolution entry points** — `_read_path_resolver.resolve_mission_read_path`, `coordination/surface_resolver.resolve_status_surface_with_anchor`, `aggregate.MissionStatus.load/_resolve_read_dir`, the C-004 shim (to be unified/retired).
- **Topology** — the (no-coord / coord-fresh / coord-behind / coord-empty) state of a mission's surfaces.
- **Typed errors** — `STATUS_READ_PATH_NOT_FOUND`, `MISSION_AMBIGUOUS_SELECTOR` (must survive caller flattening).

## Findings / Issue Matrix (seed — expanded by the adjacent-issues squad)

| Issue | Role | Verdict |
|-------|------|---------|
| #2040 | Driver (this mission brief) | in-mission |
| #2010 | Closed residual being completed (resolver unification not behavior-equivalent) | in-mission |
| #2007 | Parent epic (read/write desync) | in-mission |
| #1716 | Coordination topology coherence / coord-empty fallback (FR-006) | in-mission |
| #1868 | Canonical seams "exist in name only" (FR-001/FR-004 bind authority to a seam+guard) | in-mission |
| #1993 | Extraction-without-adoption shadow-path risk (C-002 forbids) | in-mission |

## Assumptions

- The threat/operability model is divergent on-disk surfaces under normal multi-worktree
  operation (not adversarial) — same family that forced this project's own flattening.
- `resolve_status_surface_with_anchor` is the intended canonical owner (richest topology
  logic); confirmed candidate, final pick recorded at plan.
- The create→first-write window (no coord branch) keeps primary as the sole authoritative
  surface and is NOT subject to the FR-006 coord-empty hard-fail.

## Out of Scope

- The *validation* seam (slug→safe-segment) — already shipped by 01KVFTFV.
- Any version/patch-number assignment (C-003).
- Adding new topology states or a SaaS-side surface authority.
