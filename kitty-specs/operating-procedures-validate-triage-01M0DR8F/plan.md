# Implementation Plan: Operating-Procedures Validate, Triage, Data-Drive

**Branch**: `feat/operating-procedures-validate-triage` | **Date**: 2026-08-19 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/operating-procedures-validate-triage-01M0DR8F/spec.md`

## Summary

Make every `collaboration.operating-procedures` entry on a built-in agent profile resolve to a real
`procedure:` DRG node — loud on failure — then triage the 44 that don't, then teach the DRG extractor to
derive `agent_profile --requires--> procedure` edges from the field (guarded to resolvable procedure
targets), retiring the two operating-procedures-sourced hand-pins. Ride along the unwired RECONCILE third
trigger edge. Hard internal order (load-bearing): **validate → triage → data-drive**; emitting before
triage would mint dangling edges and fail `assert_valid`.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: pydantic (profile model), ruamel.yaml (YAML I/O), the in-repo `doctrine.drg` graph stack. No new dependency.
**Storage**: N/A — build-time doctrine artifacts (`packs/built-in/*.agent.yaml`, `packs/built-in/*.graph.yaml`).
**Testing**: pytest (targeted: `tests/doctrine/drg/migration/`, `tests/doctrine/agent_profiles/`, `tests/architectural/`), plus `mypy --strict` and `ruff`.
**Target Platform**: Linux/macOS/Windows CLI (doctrine build path).
**Project Type**: single (library + CLI).
**Performance Goals**: N/A (build-time; no runtime hot path). Graph build stays well under the CLI <2 s budget.
**Constraints**: `charter` must not import `specify_cli` (C-004); `extract_artifact_edges` stays ≤ C901 15 (NFR-004); zero ruff/mypy suppressions (NFR-001); fail-closed exact-id resolution (NFR-003).
**Scale/Scope**: 16 built-in profiles, 50 op-proc declarations, 24 procedures; +10 graph edges, 0 new nodes.

## Constitution Check

*GATE: charter `.kittify/charter/charter.md`.*

| Charter rule | Compliance |
|--------------|------------|
| Single canonical authority | Validator is one pure function (`resolve_operating_procedures`) read by both extractor and doctor; procedure set derived from the graph, not restated. No second authority. |
| ATDD-first (C-011) | Each WP commits a failing-first test before the fix. WP01: empty-set gate RED@44→GREEN@0. WP02: extractor emission test RED→GREEN. |
| Architectural gate discipline | WP01's empty-set gate is non-vacuous (concrete floor + self-mutation check), mirroring `test_no_authored_applies_edge.py`. |
| Single-authority / no cross-boundary import | Validator lives in `doctrine/`; `specify_cli` (doctor) importing `doctrine` is allowed; `charter → specify_cli` is not introduced (C-004). |
| Canonical sources | Uses `spec-kitty doctrine regenerate-graph` for graph regen; no hand-edit of `*.graph.yaml`. |
| Terminology canon | No `feature*` aliases; "procedure"/"tactic"/"directive" are canonical doctrine kinds. Run `test_no_legacy_terminology.py` pre-push. |
| Tracer files + tracker hygiene | Mission tracer files seeded at plan; the 3 issues (#2994, #3352, #3488 op-proc channel) get issue-matrix rows + assignment + comments during implement. |

No violations → Complexity Tracking empty.

## Project Structure

### Documentation (this mission)

```
kitty-specs/operating-procedures-validate-triage-01M0DR8F/
├── plan.md              # this file
├── research.md          # census, seam map, decisions, triage disposition table, graph delta
├── data-model.md        # UnresolvedOpProc, resolution relation, invariants
├── quickstart.md        # commands to prove defect + validate the fix
├── contracts/
│   └── validator-and-emission-contract.md
└── tasks.md             # (/spec-kitty.tasks output — NOT created here)
```

### Source Code (repository root)

```
src/doctrine/agent_profiles/
├── operating_procedures.py     # NEW: resolve_operating_procedures() + UnresolvedOpProc
├── profile.py                  # (read) CollaborationContract.operating_procedures
├── repository.py               # (read) list_all(), skipped_profiles(), self._drg
└── diagnostics.py              # (pattern) SkippedProfile frozen-dataclass shape

src/doctrine/drg/migration/
└── extractor.py                # extract_artifact_edges: emit guarded op-proc→procedure edges;
                                #   retire 2 op-proc pins; add RECONCILE edge; fail-closed raise

src/specify_cli/cli/commands/
├── _doctrine_collect.py        # _collect_profile_health: add op-proc unresolved diagnostic
└── _doctrine_health.py         # DoctrineHealthReport passthrough (if a field is added)

packs/built-in/
├── agent_profiles/*.agent.yaml # TRIAGE: 36 delete, 5 migrate→tactic-references, 3 delete-redundant
└── *.graph.yaml                # regenerated (committed) fragments

tests/
├── architectural/test_operating_procedures_resolve.py   # NEW empty-set gate (WP01 ATDD)
├── doctrine/drg/migration/test_extractor.py             # extend: emission + guard (WP02 ATDD)
├── doctrine/drg/migration/test_extractor_projection.py  # update pinned node/edge counts
├── doctrine/agent_profiles/                             # validator unit tests
└── specify_cli/cli/commands/test_doctor*.py             # doctor diagnostic assertion
```

**Structure Decision**: single-project library layout; all new logic under `src/doctrine/` (single-authority),
consumed by the CLI doctor surface. No new top-level packages.

## Parallel Work Analysis

### Dependency Graph

```
WP01 (validate → triage → data-drive → RECONCILE → regen)   — single lane, no parallelism
    hard internal order (C-001), enforced by ordered commits within the WP
```

**Single work package, single lane.** The work is inherently coupled and sequential and cannot be
cleanly split without a forbidden file-ownership overlap: migrating the wrong-kind tactics to
`tactic-references` (to rescue their orphaned intent) changes the tactic-edge graph, so the *same*
`packs/built-in/*.graph.yaml` regen is required by both the triage step and the data-drive step, and
the same `*.agent.yaml` files carry both fictional deletions and tactic migrations. A two-WP split
would force overlapping `owned_files` (graph fragments + profiles), which `finalize-tasks` rejects.
Coord topology gives a single lane; there is no parallelism to exploit. The load-bearing order is
enforced *inside* the WP by commit sequencing with a red-first test at each sub-phase (validator gate,
then extractor emission).

### Work Distribution (WP01, ordered subtasks)

1. **Validate (red-first)**: commit the empty-set gate test + `resolve_operating_procedures` pure validator (RED — 44 unresolved).
2. **Triage → green**: delete 36 fictional; migrate 5 wrong-kind tactics to `tactic-references` (rescue orphaned intent); delete 3 redundant → gate GREEN (0).
3. **Diagnostic**: wire the unresolved set into `doctor doctrine`.
4. **Data-drive (red-first)**: extractor emission test (resolvable → one `requires` edge; non-procedure/absent → none), then teach `extract_artifact_edges` to emit guarded `agent_profile→procedure` edges + fail-closed raise + a C901 helper.
5. **Wire**: retire the two op-proc-sourced `_CURATED_ARTIFACT_EDGES` entries (keep the two prose pins); add the RECONCILE third edge.
6. **Regen + reconcile counts**: `spec-kitty doctrine regenerate-graph`; update `test_extractor_projection.py` pins + confirm `regenerate-graph --check` golden green; verify `assert_valid`, ruff, mypy --strict.

### Coordination Points

- **Integration tests**: `regenerate-graph --check` (freshness), `test_extractor_projection.py` (counts), the empty-set gate, `doctor doctrine --json` (diagnostic), `assert_valid` via the graph build.
- **Graph-delta review** (NFR-002): reconcile the regenerated `*.graph.yaml` against the +10 table in research.md — every removed pin re-derived, every net-new edge traced, zero dangling.

## Out of Scope (guards)

- `REFERENCE_RELATIONS` / kind-complete cascade (#2829 = M5) — untouched (C-002).
- Procedure delivery/render to the agent, `procedures[]` array (#3488 render, #3176 = M4) — untouched (C-003).
- Authoring net-new procedure nodes for fictional refs (C-007) — deferred to a doctrine-content mission.
- Org/project-tier hard load-failure gate — built-in-scoped here; org/project protected by the emission guard (C-006).

## Branch Contract

- Current branch at plan start: `feat/operating-procedures-validate-triage`
- Planning/base branch: `feat/operating-procedures-validate-triage`
- Final merge target: `feat/operating-procedures-validate-triage` (→ draft PR to `main`; the operator merges)
- `branch_matches_target`: true
