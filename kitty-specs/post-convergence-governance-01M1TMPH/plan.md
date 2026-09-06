# Implementation Plan: Post-Convergence Governance & Enforcement

**Branch**: `tier3/governance-enforcement` | **Date**: 2026-09-06 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/post-convergence-governance-01M1TMPH/spec.md`

## Summary

Bring three governance surfaces back into agreement with the code the Convergence (#3881) shipped:
(A1) mark four retired-subsystem ADRs `Superseded` and author one convergence-retirement ADR that also
records the client-repo inversion; (A2) name the enforced pair (`pyproject [wheel].packages` +
`conftest.landscape`/`test_layer_rules`) as the canonical modularity SSOT, delete the stale
self-authoritative ownership manifest and its key-pinning schema gate (D7), and reduce the ownership map
to narrative-only; (A3) close the ungated `runtime→specify_cli` boundary with a shrink-only ledger that
exactly mirrors the existing `mission_runtime` ledger, and refresh `_PRODUCTION_ROOTS`. Docs + tests
only — no runtime code-behavior change.

## Technical Context

**Language/Version**: Python 3.11
**Primary Dependencies**: pytest, pytestarch (`LayerRule`), PyYAML (test-side), ruamel not required
**Storage**: N/A (docs + tests)
**Testing**: `pytest` architectural gates; each new gate carries a red-first non-vacuity test
**Target Platform**: Linux (CI Blacksmith / local)
**Project Type**: single project
**Performance Goals**: each touched gate ≤5 s (suite NFR-002)
**Constraints**: shrink-only ledger (never exact count); enforced pair wins on conflict; no
zeitgeist/SaaS redesign epic in this repo (client-repo inversion is binding)
**Scale/Scope**: 4 ADRs edited + 1 new ADR; 2 ownership docs demoted/removed; 3 test files touched;
1 pyproject exclude-list line removed; CLAUDE.md/AGENTS.md + `00_landscape` SSOT note

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **ATDD-first / red-first**: every gate change (A1 ADR-hygiene test, A3 runtime ledger) ships with a
  non-vacuity/red-first test proving teeth. ✅ planned (WP03 tests co-located).
- **Canonical sources, never improvise**: A3 mirrors the *existing* `_MISSION_RUNTIME_ALLOWED_SPECIFY_CLI`
  ledger + `TestMissionRuntimeBoundary` pattern verbatim rather than a new bespoke gate. ✅
- **Architectural gate discipline**: D7 is resolved by deleting the gate *with* the artifact it pins
  (not by suppressing it); `_PRODUCTION_ROOTS` refresh keeps the retired-import scan non-vacuous. ✅
- **Terminology adherence**: ADR + doc prose use canonical terms (Mission, charter/offering). ✅
- **Git/workflow discipline**: draft PR; operator merges; commit per WP. ✅

No violations → Complexity Tracking empty.

## Project Structure

### Documentation (this mission)

```
kitty-specs/post-convergence-governance-01M1TMPH/
├── spec.md
├── plan.md              # this file
├── tasks.md
└── tasks/WP01..WP03.md
```

### Source Code (repository root) — files this mission touches

```
docs/adr/3.x/2026-06-30-1-sync-daemon-identity-and-cleanup-classification.md   # A1: status→Superseded
docs/adr/3.x/2026-04-11-1-saas-rollout-and-readiness.md                        # A1: status→Superseded
docs/adr/3.x/2026-08-09-1-project-sync-store-boundary.md                       # A1: status→Superseded
docs/adr/2.x/2026-02-27-1-cli-tracker-surface-gated-by-saas-sync-flag.md       # A1: status→Superseded
docs/adr/3.x/2026-09-06-1-convergence-retirement-and-client-repo-inversion.md  # A1: NEW ADR
docs/adr/3.x/2026-04-25-1-shared-package-boundary.md                           # A1: LEFT Accepted (precedent)

docs/architecture/05_ownership_manifest.yaml                                   # A2: DELETE
docs/architecture/05_ownership_map.md                                          # A2: reduce to narrative-only
docs/architecture/00_landscape/README.md                                      # A2: name enforced pair as SSOT; client framing
CLAUDE.md (→ AGENTS.md)                                                         # A2: name enforced pair as SSOT
pyproject.toml                                                                  # A2: drop deleted test from ruff-format exclude

tests/architecture/test_ownership_manifest_schema.py                           # A2/D7: DELETE (pins stale 8 keys)
tests/architectural/test_layer_rules.py                                        # A3: add runtime→specify_cli ledger + tests
tests/architectural/test_shared_package_boundary.py                            # A3/D6: refresh _PRODUCTION_ROOTS
tests/architectural/test_adr_hygiene_convergence_retirement.py                 # A1: NEW ADR-hygiene gate + red-first
```

**Structure Decision**: single project; changes confined to `docs/` and `tests/` plus one pyproject
exclude-list line. No `src/**` production logic changes (NFR-002).

## Complexity Tracking

*No Charter Check violations — section intentionally empty.*

## Implementation Concern Map

> Concerns are not WPs. `tasks` translates these into WPs; here IC ↔ WP is 1:1 for clarity.

### IC-01 — ADR hygiene & convergence-retirement record (→ WP01)

- **Purpose**: Stop the decision record asserting deleted subsystems; add one governed record of the
  retirement + client-repo inversion.
- **Relevant requirements**: FR-001, FR-002, FR-003.
- **Affected surfaces**: the four ADRs (front-matter `status` + a supersession note), the new ADR,
  `2026-04-25-1` (unchanged/verified), new `test_adr_hygiene_convergence_retirement.py`.
- **Sequencing/depends-on**: none (pure docs + one test).
- **Risks**: ADR front-matter shape varies (2.x vs 3.x); the hygiene test must parse the real
  front-matter keys. Mitigate by reading each ADR's actual header first.

### IC-02 — Modularity SSOT canonicalization & ownership-doc demotion (→ WP02)

- **Purpose**: Make the enforced pair the named SSOT; remove the stale self-authoritative manifest and
  the D7 gate that pins its stale keys; keep the map as narrative pointing at the enforced pair.
- **Relevant requirements**: FR-004, FR-005, FR-006, FR-007; C-002.
- **Affected surfaces**: delete `05_ownership_manifest.yaml` + `test_ownership_manifest_schema.py`;
  remove that test's line from `pyproject.toml [tool.ruff.format].exclude` (guarded by
  `test_ruff_format_exclude_ratchet`); rewrite `05_ownership_map.md`; SSOT note in `00_landscape` +
  `CLAUDE.md`; client-repo framing for `zeitgeist_client`/`saas_client`.
- **Sequencing/depends-on**: none.
- **Risks**: (1) deleting the test while leaving its `exclude` entry reds the ruff-format ratchet →
  remove both together. (2) Overlaps Tier-1 PR #3885 which edited the ownership pair; this mission
  supersedes those edits by deleting the manifest — flag merge-ordering in the PR. (3) A hidden
  consumer of the manifest → verified: only historical `kitty-specs/**` + the schema test reference it.

### IC-03 — runtime→specify_cli boundary gate + `_PRODUCTION_ROOTS` refresh (→ WP03)

- **Purpose**: Make a new `runtime→specify_cli` inversion red CI (#3522); make the retired-import scan
  cover the real roots (D6).
- **Relevant requirements**: FR-008, FR-009; NFR-001, NFR-003; C-003.
- **Affected surfaces**: `test_layer_rules.py` (new `_RUNTIME_ROOT`, `_RUNTIME_ALLOWED_SPECIFY_CLI`
  frozenset of the 23 live first-level subpackages + bare-import sentinel, `TestRuntimeSpecifyCliLedger`
  with within-ledger / rejects-out-of-ledger / no-stale-entries — reusing the existing
  `_collect_specify_cli_imports` / `_out_of_ledger_specify_cli_imports` / `_specify_cli_subpackage`
  helpers); `test_shared_package_boundary.py` `_PRODUCTION_ROOTS`.
- **Sequencing/depends-on**: none (independent of WP01/WP02).
- **Risks**: (1) the ledger must be shrink-only (allow ≤ current), matching `mission_runtime`'s
  `test_ledger_has_no_stale_entries` — never an exact count (C-003). (2) `specify_cli.cli`/`.next` must
  NOT enter the ledger (they stay hard-forbidden by the existing `TestRuntimeBoundary`); verified the 23
  live subpackages exclude them. (3) The bare `import specify_cli` (2 edges in `runtime_bridge_io.py`,
  subpackage `""`) must be an explicit ledger entry with rationale. (4) Keep runtime cost ≤5 s — the
  AST scan of `src/runtime` is small.

### Ledger ground-truth (live AST scan of `src/runtime/`, 2026-09-06)

93 edges across 23 first-level `specify_cli.<sub>` subpackages: `bulk_edit, coordination, core, events,
invocation, lanes, migration, mission, mission_loader, mission_metadata, mission_step_contracts,
mission_v1, missions, requirement_mapping, retrospective, review, runtime, shims, status, status_lanes,
task_utils, workspace` plus the bare-`import specify_cli` sentinel (`""`, 2 edges in
`runtime/next/runtime_bridge_io.py` resolving the legacy missions package path). `cli`/`next` are
absent (they remain hard-forbidden by `TestRuntimeBoundary`).
