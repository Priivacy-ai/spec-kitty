# Implementation Plan: Post-Consolidation Write Surface and Authoring Finish

**Branch**: `feat/post-merge-write-authoring-finish` | **Date**: 2026-07-30 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/post-merge-write-authoring-finish-01KYRRM5/spec.md`

## Summary

Finish PR #3076's deferred write-side pieces, and land the tidy-first foundation of the `consolidate` terminology effort (#3080). The load-bearing correction from the grounding squad: the #3033 fix is to **wire the already-declared `TopologySurface.CONSOLIDATED`** as the phase-resolved integrated-tree surface — *not* a ref-swap and *not* a new `merge_target_branch` field. `CONSOLIDATED` resolves to the **Target Ref tree** while it exists (lane-consolidation, "E1") and to the **repository-root checkout on the Primary Branch** once the Target Ref is deleted (publish-to-trunk, "E2"). Phase is derived **inside** `resolve_placement_only` (never threaded), preserving the single-write-resolver invariant (C-006). Authoring finish-work (#2318 negative invariants + stale-verdict + prompt; #1738 same-repo URL refs + provenance) is independent (Lane D).

**Technical approach**: (1) tidy-first terminology foundation (ADR + glossary + drift-ratchet guard); (2) red-first #3033 `safe-commit` repro; (3) internal lifecycle-phase resolution + `SurfaceLocations.consolidated` wiring with a squash-robust E2 predicate; (4) route post-consolidation writes through the wired surface; (5) seam-level no-residue thunk; (6) additive acceptance authoring + issue-ref recognition.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer, rich, ruamel.yaml, GitPython-free `git` subprocess wrappers (`core/git_ops.py`), the existing `mission_runtime` placement seam
**Storage**: git (branches/commits/worktrees), `meta.json` (durable mission state), JSONL status event log, JSON matrices
**Testing**: pytest (`tests/`), ATDD-first red-first regressions through pre-existing entry points; `tests/architectural/` gates; `PWHEADLESS=1`
**Target Platform**: Linux/macOS developer + CI (spec-kitty CLI)
**Project Type**: single (CLI tool + `mission_runtime` library)
**Performance Goals**: no new git subprocess on the pre-consolidation write happy path (NFR-004); phase resolution = durable-meta reads only; E2 content probe runs only when the Target Ref is absent
**Constraints**: single write resolver preserved (C-006); phase derived internally (C-001); ruff + `mypy --strict` clean, `tests/architectural/` green, no suppressions (NFR-003); scope boundary C-005 (no emit.py/#2980/#2549/#2960/#3029)
**Scale/Scope**: 16 FR / 4 NFR / 12 C / 11 SC; ~9 implementation concerns; touches `src/mission_runtime/resolution.py`, `coordination/write_seam.py`, the three composed writers, `acceptance/`, `tasks/` issue-ref modules, one new ADR, glossary, one arch-gate entry

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Charter present (`.kittify/charter/charter.md`, compact context loaded). This mission is strongly charter-aligned — it advances several governing principles rather than tensioning them:

- **Single canonical authority** — CONSOLIDATED becomes the single surface for the integrated tree across the E1→E2 lifecycle; C-001/C-002 forbid a parallel/second write resolver. ✅
- **Architectural alignment** — wires an existing, declared seam (`translate_surface` CONSOLIDATED arm) rather than inventing a mechanism. ✅
- **DDD + tiered rigour** — `resolve_placement_only` / `SurfaceLocations` are core-tier (full rigour); the authoring CLIs are glue-tier. ✅
- **ATDD-first / red-first** — NFR-002 mandates a failing-first #3033 `safe-commit` test as the first functional WP; every behavioural change lands a red-first regression. ✅
- **Terminology adherence** — the mission *strengthens* the canon: FR-014/015/016 canonicalize `consolidate` and add a drift guard; C-007/C-012 enforce sense-naming and boyscouting. ✅

**No violations.** Complexity Tracking not required.

## Project Structure

### Documentation (this mission)

```
kitty-specs/post-merge-write-authoring-finish-01KYRRM5/
├── plan.md              # This file
├── research.md          # Phase 0 output (design decisions resolved)
├── data-model.md        # Phase 1 output (entities/state)
├── quickstart.md        # Phase 1 output (operator/agent walkthrough)
├── contracts/           # Phase 1 output (seam contracts + ADR pointer)
└── tasks.md             # Phase 2 (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)

```
src/mission_runtime/
├── resolution.py                # resolve_placement_only (internal phase), SurfaceLocations.consolidated, translate_surface, resolve_artifact_surface
└── artifacts.py                 # TopologySurface.CONSOLIDATED (already declared), MissionArtifactKind

src/specify_cli/
├── coordination/write_seam.py   # write_artifact staging-thunk (no-residue), _probe_write_target
├── core/paths.py                # get_feature_target_branch (unrouted), resolve_merge_target_branch, new phase-signal reader
├── merge/baseline.py            # baseline_merge_commit (phase/anchor signal — read only)
├── tasks/
│   ├── issue_matrix.py          # detect_issue_references (single regex widen), IssueReference (+source_file), to_dict/from_dict
│   └── issue_reference_discovery.py  # dedup rule preserving provenance
├── acceptance/
│   ├── matrix.py                # NegativeInvariant persist/execute, fresh overall_verdict
│   └── gates_core.py            # persist recomputed verdict
├── cli/commands/
│   ├── agent/acceptance_verdict.py   # negative-invariant register/execute (extend)
│   ├── accept.py                # --diagnose hardening (report-not-raise)
│   └── safe_commit_cmd.py       # #3033 entry point (red-first repro)
└── post_merge/retrospective_terminus.py  # UNCHANGED (C-009 — stays fail-open)

src/doctrine/missions/mission-steps/   # accept mission-step prompt (SOURCE only; FR-011)
docs/adr/3.x/                          # NEW ADR (CONSOLIDATED wiring + consolidate canonical)
docs/context/orchestration.md          # glossary canonicalization (FR-015)
tests/architectural/test_no_legacy_terminology.py  # drift-ratchet guard (FR-016)
tests/                                 # red-first regressions per FR
```

**Structure Decision**: Single-project CLI + library. The core change lands in `src/mission_runtime/resolution.py` (the one write resolver) and `coordination/write_seam.py`; authoring is additive in `acceptance/` and `tasks/`. No new package.

## Implementation Concern Map

> Implementation concerns are NOT work packages. `/spec-kitty.tasks` translates these into WPs.

### IC-01 — Terminology foundation (tidy-first)

- **Purpose**: Land the "do not make it worse" foundation of #3080 before any functional work: canonicalize `consolidate` for the lane-consolidation sense, document it, and ratchet against drift.
- **Relevant requirements**: FR-014, FR-015, FR-016; C-012, C-007.
- **Affected surfaces**: new ADR in `docs/adr/3.x/`; `docs/context/orchestration.md` (glossary + "do NOT use when" guards); `tests/architectural/test_no_legacy_terminology.py` (curated forbidden lane-consolidation-sense phrasings + red-first bite fixture); any glossary pack.
- **Sequencing/depends-on**: none — FIRST (tidy-first enabler, C-010).
- **Risks**: the drift guard must NOT false-positive on git-merge/publish "merge" uses — scope to curated phrasings, prove a bite fixture AND green on grandfathered/legit uses (SC-011). The ADR is shared with IC-04 (one ADR: CONSOLIDATED wiring + consolidate canonical).

### IC-02 — #3033 red-first repro

- **Purpose**: Author the failing-first `safe-commit` regression that evidences the #3033 P0 through the pre-existing entry point, independently mergeable ahead of the fix.
- **Relevant requirements**: NFR-002, C-006, SC-001.
- **Affected surfaces**: `tests/` (regression); exercises `cli/commands/safe_commit_cmd.py` → `resolve_placement_only`. Fixture: consolidated mission (baseline present) with Target Ref deleted (E2), asserting the HEAD-guard refusal today.
- **Sequencing/depends-on**: after IC-01; first *functional* concern.
- **Risks**: fixture must construct a genuine E2 state (deleted Target Ref, integrated content on the Primary Branch checkout) without the fix present.

### IC-03 — Lifecycle-phase resolution (internal)

- **Purpose**: Derive the mission's phase (pre-consolidation / consolidated-E1 / published-E2) inside the resolver from durable meta, so writes route without callers threading phase.
- **Relevant requirements**: FR-001; C-001, C-003, NFR-001, NFR-004.
- **Affected surfaces**: `src/mission_runtime/resolution.py` (`resolve_placement_only` internal derivation; `PlacementSeam.write_target` + `commit_for_mission` derive the identical phase — no split-brain); `core/paths.py` (new phase-signal reader; `get_feature_target_branch` stays unrouted); reads `baseline_merge_commit` + status event log.
- **Sequencing/depends-on**: after IC-02.
- **Risks**: E2 disambiguation — "Target Ref absent" alone is insufficient (never-created vs deleted); conjoin with terminal-completion evidence (all WPs `done` / `mission_number` assigned) + `baseline_merge_commit` present (C-003). Probe/commit phase agreement (NFR-001).

### IC-04 — CONSOLIDATED surface location wiring

- **Purpose**: Populate `SurfaceLocations.consolidated` so `translate_surface(CONSOLIDATED, …)` resolves the integrated tree by phase; author the ADR (first production wiring, extends 2026-07-23-2, reaffirms C-006, canonicalizes `consolidate`).
- **Relevant requirements**: FR-002; C-002; FR-014 (shared ADR).
- **Affected surfaces**: `resolution.py` (`SurfaceLocations`, `resolve_artifact_surface`, `translate_surface` consumers); the new ADR.
- **Sequencing/depends-on**: with/after IC-03.
- **Risks**: **squash-robust E2 predicate** — under a squash publish-to-trunk the E1 consolidation commit is not a commit-ancestor of the Primary Branch; the E2 resolution must key on the mission's consolidated *content* being present on the checkout (see research.md decision), not naive commit ancestry.

### IC-05 — Post-consolidation write routing

- **Purpose**: Route post-consolidation PRIMARY-kind (safe-commit) and coord-kind (write_seam) writes through the wired CONSOLIDATED surface so the #3033 P0 turns green; verify the shared-resolver consequence for `STATUS_STATE`/`DECISION_LOG` is non-regressive.
- **Relevant requirements**: FR-003, FR-004; C-005, SC-001, SC-002, SC-005, SC-009.
- **Affected surfaces**: `resolution.py` `resolve_placement_only`; `coordination/write_seam.py`; `safe_commit_cmd.py`. NOTE: `coordination/commit_router.py` (`commit_for_mission`) + `git/commit_helpers.py` stay **byte-frozen** — they re-derive phase through the single `resolve_placement_only`, so the fix is resolver-only (no WP owns them; a needed change there is a design escalation).
- **Sequencing/depends-on**: after IC-03, IC-04.
- **Risks**: C-005 shared-resolver reconciliation — do NOT per-kind-branch in the resolver (reintroduces the kind-conditioning C-006 forbids); prove `STATUS_STATE`/`DECISION_LOG` pre-consolidation resolution unchanged.

### IC-06 — No-residue seam thunk

- **Purpose**: Make `write_seam.write_artifact` materialize a composed writer's staging file only after the routability probe passes, at a single seam-level locus.
- **Relevant requirements**: FR-005; SC-003 (#3073).
- **Affected surfaces**: `coordination/write_seam.py` (accept a staging thunk); the three composed writers `tasks/issue_matrix.py`, `retrospective/tracer_writer.py`, `acceptance/matrix.py` (pass thunks instead of pre-staging).
- **Sequencing/depends-on**: with-or-before IC-05 (so the E2 refusal window is exercised cleanly).
- **Risks**: `write_acceptance_matrix` has many no-commit/fixture callers — the thunk must wrap, not break, them.

### IC-07 — Off-checkout refuse-with-recovery

- **Purpose**: When the current checkout does not carry the mission's consolidated content, refuse post-consolidation writes with a branch-named recovery instruction; never force a checkout.
- **Relevant requirements**: FR-006; C-004, SC-004.
- **Affected surfaces**: the resolution/probe path (`resolve_placement_only` / `write_seam` / `safe_commit_cmd`); `core/git_ops.py` current-branch read.
- **Sequencing/depends-on**: after IC-04 (uses the E2 content/ancestry check).
- **Risks**: the recovery message must name a concrete, checkoutable ref, derived from the same durable signal (not a fabricated branch).

### IC-08 — Acceptance authoring (#2318)

- **Purpose**: Register/execute acceptance negative invariants via the canonical `acceptance-verdict` command; harden `--diagnose` to report-not-crash; persist a fresh `overall_verdict`; rewire the accept mission-step prompt to drive the CLI.
- **Relevant requirements**: FR-007, FR-008, FR-009, FR-010, FR-011; C-008.
- **Affected surfaces**: `cli/commands/agent/acceptance_verdict.py` (extend — no new command); `acceptance/matrix.py` (`NegativeInvariant` persist/execute via existing engine; fresh verdict); `acceptance/gates_core.py`; `cli/commands/accept.py` (`--diagnose` load hardening); `src/doctrine/missions/mission-steps/` accept prompt (SOURCE only, never the 12 agent copies).
- **Sequencing/depends-on**: after IC-01 (terminology); otherwise independent (Lane D).
- **Risks**: `NegativeInvariant` dataclass already carries the fields — NO acceptance-matrix schema migration (C-008). FR-011 prompt-rewire must assert the prompt *drives* the CLI, not merely mentions it.

### IC-09 — Issue-reference URL + provenance (#1738)

- **Purpose**: Recognize same-repo GitHub-URL issue references (single regex widened in place) and record `source_file` provenance with a defined dedup rule.
- **Relevant requirements**: FR-012, FR-013; C-011, SC-008.
- **Affected surfaces**: `tasks/issue_matrix.py` (single `detect_issue_references` pattern; `IssueReference` + `source_file` + `to_dict`/`from_dict`); `tasks/issue_reference_discovery.py` (dedup keyed to preserve provenance).
- **Sequencing/depends-on**: independent (Lane D).
- **Risks**: same-repo-only scoping (cross-repo URLs must NOT newly block the completeness gate — SC-008); the dict-keyed-by-number dedup currently collapses provenance — change the key or define a winning rule.
