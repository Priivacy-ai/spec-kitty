# Implementation Plan: Doctrine Public API Surface

**Branch**: `feat/doctrine-public-api-surface` | **Date**: 2026-08-10 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/doctrine-public-api-surface-01KZPDSR/spec.md`

## Summary

Give `src/doctrine/` a single curated public surface (`doctrine/api.py` + `__all__`), route
every non-exempt runtime consumer through **symbol-level** `charter.*` facades (closing both
direct `doctrine.*` reach-through and the first-party re-export laundering conduit), fix the
raw `DoctrineService` sole-door bypasses, and land a lazy-import architectural ratchet that
keeps the boundary from silently regrowing. Sonar debt on the doctrine tree is cleared, with
the high-risk complexity refactor isolated and behavior-locked by a golden DRG snapshot. This
is the unblocked **precondition** to the #3101 kernel→doctrine→charter wheel cutover — it does
not build or publish the wheel.

**Engineering Alignment (confirmed, no open planning questions):** design is settled by the
hardened spec and the post-spec squad. Mechanism = charter facades (not a widened
`doctrine.__all__` for runtime); enforcement = pytestarch/AST architectural tests written
red-first (ATDD-C-011); the classification census is re-run at implementation start rather
than trusting the 2026-08-10 snapshot counts. No `[NEEDS CLARIFICATION]` markers.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: internal only — `src/doctrine`, `src/charter`, `src/specify_cli`; test/enforcement tooling `pytest`, `pytestarch`, `ast` (stdlib), `ruff` (C901), `mypy --strict`; SonarCloud (`Priivacy-ai_spec-kitty`) for maintainability metrics. No new third-party runtime dependency.
**Storage**: N/A (source tree + architectural test fixtures; one golden DRG snapshot fixture for FR-010)
**Testing**: `pytest` (`tests/architectural/` for boundary/ratchet/facade-identity gates; unit tests for extracted helpers; a regenerate-graph golden round-trip for the FR-010 refactor). Regression-delta gate per charter Pre-existing Failure Reporting Rule — targeted runs, not the ~1h full suite (CI is the release authority).
**Target Platform**: cross-platform CLI (Linux/macOS/Windows), Python package
**Project Type**: single
**Performance Goals**: new lazy-import ratchet completes ≤ 3 s within the architectural suite; zero runtime performance regression (imports move between call sites, not added).
**Constraints**: strictly behavior-preserving (C-006); symbol-level object-identity re-exports (`X is doctrine.X`); no new blanket suppressions and no Sonar-UI Won't-Fix/False-Positive triage (NFR-005); atomic-precondition boundary — no wheel build, no `src/charter/pyproject.toml` (C-004).
**Scale/Scope**: census snapshot (measured on-branch 2026-08-10) — 26 reached doctrine paths, **34 lazy-import runtime files / 70 lazy import lines (0 module-level)**, 5 raw-service sites (`RawDoctrineService(`), 6 true gaps, ~8 facade doors (2 widened + 3 new clusters + 3 narrow), 45 CRITICAL Sonar smells, 14 committed `packs/built-in/**/*.graph.yaml` golden fragments; re-census at implement start.

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Charter item | Bearing on this mission | Verdict |
|---|---|---|
| **Shared Package Boundary** (runtime→charter→doctrine) | This mission *strengthens* the boundary; it is the reason the mission exists. | ✅ Aligned |
| **charter C-007 `__all__` convention** (binds `charter`/`kernel` today) | Mission consciously **extends** it to `src/doctrine/` and records the extension (spec C-007-mission). Per-mission scope decision, which C-007 explicitly permits. | ✅ Aligned (extension recorded) |
| **ATDD-First (C-011)** | Every boundary/facade/ratchet gate is written red-first as an architectural test before the migration that greens it. | ✅ Method adopted |
| **Complexity ≤ 15 standing order** (ruff C901 / Sonar S3776) | FR-010 brings 8 functions under the ceiling; extracted helpers carry their own tests (no complexity-shuffling). | ✅ Aligned |
| **Pre-existing Failure Reporting Rule / DIR-013** | NFR-001 regression-delta gate: no merge-base-green test goes red; known reds classified, never green-washed. | ✅ Adopted |
| **Terminology Canon (Mission not Feature)** | Spec/plan use Mission; `feat/` is a git prefix only. | ✅ Clean |
| **DIR-006 / DIR-007 / DIR-009** | `mypy --strict` + docstrings on the public surface; CHANGELOG entry for the surface/boundary change (DIR-009 — it is an internal-contract change, note it). | ✅ Planned (see IC-02) |
| **Disciplined-refactoring / semantic-compression doctrine** | Governs *how* FR-010 preserves behavior; activate the tactic for this mission if not already active. | ⚠ Activate for mission (see IC-09) |
| **No direct pushes to origin/main** | Mission lands via PR from `feat/doctrine-public-api-surface`; `spec-kitty merge` → local main only. | ✅ Understood |

No unjustified violations → **Charter Check PASS**. One action item (activate the
refactoring tactic for IC-09) tracked, not a blocker.

## Project Structure

### Documentation (this mission)

```
kitty-specs/doctrine-public-api-surface-01KZPDSR/
├── plan.md              # This file
├── research.md          # Phase 0: settled design decisions (census, api.py-vs-__all__, ratchet shape)
├── data-model.md        # Phase 1: the surface taxonomy + facade→doctrine mapping table
├── contracts/
│   └── public-api-contract.md   # Phase 1: architectural invariants as testable contracts
├── quickstart.md        # Phase 1: how to run the new gates + re-census
└── tasks.md             # Phase 2 (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)

```
src/doctrine/
├── api.py                       # NEW — the single curated public surface (__all__)
├── __init__.py                  # keep minimal (ArtifactKind/BaseDoctrineRepository/DoctrineService)
├── drg/migration/
│   ├── hand_authored_overlay.py # FR-009 URN-literal hoist (campsite)
│   └── extractor.py             # FR-010 complexity refactor (isolated, last)
├── artifact_kinds.py            # FR-011 malformed-suppression fix (campsite)
└── (per-kind + drg/missions/model_task_routing/assets subpackages — classified, mostly untouched)

src/charter/
├── drg.py                       # WIDEN: DRGLoadError, DRGValidationError, resolve_org_roots, OrgDRGConflict
├── mission_steps.py             # WIDEN: GateBinding
├── missions.py                  # NEW facade cluster: MissionTemplateRepository, MissionsRootNotFound,
│                                #   MissionTypeRepository, builtin_mission_type_ids, project_template_set
├── model_routing.py             # NEW: load, evaluate, RoutingRecommendation (symbol-level)
├── assets.py                    # NEW: AssetRepository, AssetManifest, AssetNotFoundError, AssetPathEscapeError
└── (narrow doors: glossary_packs, spdd_reasons, pack_paths built_in_dir/built_in_root)

src/specify_cli/                 # ~29 lazy-import files migrated onto charter.* facades
└── doctrine/                    # exempt management surface — inbound-only (no outbound re-export)

tests/architectural/
├── test_runtime_charter_doctrine_boundary.py  # EXTEND: sibling lazy-import ratchet + laundering rule
├── test_charter_facades_reexport_doctrine.py  # GROW: _FACADE_TABLE for new/widened doors
├── test_doctrine_public_surface.py            # NEW: api.py __all__ pins surface; INTERNAL negative test
└── test_doctrine_wheel_closure.py             # UPDATE: pin real surface, not just shape
```

**Structure Decision**: Single-project Python. The mission edits three existing source
areas (`src/doctrine`, `src/charter`, `src/specify_cli`) and the `tests/architectural/` gate
suite. No new package, no new top-level directory (C-004 forbids minting `src/charter/pyproject.toml`).

## Complexity Tracking

No Charter Check violations require justification. (FR-010 *reduces* complexity; it is not a
new-complexity violation.)

## Implementation Concern Map

> Concerns are architectural areas, not work packages. `/spec-kitty.tasks` translates these
> into WPs; the dependency arrows below drive lane ordering.

### IC-01 — Census, classification & behavior baseline (foundation)

- **Purpose**: Re-run the reach-through census (AST sweep for direct + laundered `doctrine.*` consumption, fresh Sonar pull) and produce the authoritative per-path disposition table (PUBLIC / FACADE-ONLY / enumerated-management / ticketed-baseline / INTERNAL). **IC-01 is the SOLE owner of the management-surface enumeration** — no later concern reclassifies a module into the exempt surface. **IC-01 also captures the behavior baseline**: the base-commit golden `regenerate-graph` output (already committed at `packs/built-in/**/*.graph.yaml`) is the shared golden that IC-08 and IC-09 both depend on.
- **Relevant requirements**: FR-002, and the disposition of `glossary_packs`, `spdd_reasons`, `pack_paths`, `drg.override_policy`, `missions.mission_step_repository`, `missions.step_projection`.
- **Affected surfaces**: `kitty-specs/.../data-model.md` (the table lands here), a reusable census script under `tests/architectural/` or `scripts/`.
- **Sequencing/depends-on**: none (foundation). IC-06, IC-07, IC-08, IC-09 all consume its outputs.
- **Risks**: census drift vs the on-branch snapshot; the INTERNAL-vs-migrate reconciliation must resolve every non-exempt consumer to exactly one disposition or SC-001 is unsatisfiable. **Choosing MANAGEMENT for `step_projection`/`mission_step_repository`/`override_policy`/`hand_authored_overlay` widens boundary exemptions — the very thing this mission tightens — so each MANAGEMENT tag needs explicit per-instance justification, not a silent default; prefer FACADE-ONLY where a clean door exists.**

### IC-02 — Doctrine public surface (`doctrine/api.py`)

- **Purpose**: Author `doctrine/api.py` with an explicit `__all__` enumerating the PUBLIC surface; update `test_doctrine_wheel_closure.py` to pin the real surface. Record the charter-C-007 extension + a CHANGELOG entry (DIR-009). **Dead-symbol wiring decision (from post-plan gate-efficacy review):** the charter facades re-export PUBLIC symbols **from `doctrine.api`** (not from the origin submodule), so `doctrine.api` has *live* callers and `test_no_dead_symbols.py` does real work rather than collapsing to a blanket allowlist. Only genuinely caller-less wheel-only exports use the gate's `_SYMBOL_ALLOWLIST` with a tracker ref. Identity still holds: `charter.X is doctrine.api.X is doctrine.<submodule>.X` (same object).
- **Relevant requirements**: FR-001, FR-008, NFR-004, C-007-mission.
- **Affected surfaces**: `src/doctrine/api.py`, `src/doctrine/__init__.py`, `tests/architectural/test_doctrine_wheel_closure.py`, `tests/architectural/test_no_dead_symbols.py` (allowlist only for true wheel-only exports), `CHANGELOG.md`, charter C-007 note.
- **Sequencing/depends-on**: IC-01. `_FACADE_TABLE` entries for PUBLIC symbols point at `doctrine.api` (coordinated with IC-03).
- **Risks**: if facades kept re-exporting from origin submodules, every api.py symbol reads "dead" and the gate degrades to blanket allowlist — the from-`doctrine.api` wiring above is what avoids that.

### IC-03 — Charter facade growth (symbol-level)

- **Purpose**: Widen `charter.drg` / `charter.mission_steps` and add `charter.missions`, `charter.model_routing`, `charter.assets`, plus narrow doors for `glossary_packs` / `spdd_reasons` / FACADE-ONLY `pack_paths` symbols — all **symbol-level** object-identity re-exports in `__all__`; grow `test_charter_facades_reexport_doctrine.py::_FACADE_TABLE`.
- **Relevant requirements**: FR-003, NFR-002, C-002.
- **Affected surfaces**: `src/charter/{drg,mission_steps,missions,model_routing,assets}.py` (+ glossary/spdd/pack_paths doors), `tests/architectural/test_charter_facades_reexport_doctrine.py`.
- **Sequencing/depends-on**: IC-01 (needs the door list from classification). Coordinated with IC-02 (PUBLIC symbols re-export from `doctrine.api`).
- **WP fault line (pre-signal for /tasks):** splits **per-door** (drg-widen, mission_steps-widen, missions, model_routing, assets, narrow-doors) — each door WP is independent and parallelizable; no door depends on a migrated call site (verified: no IC-04→IC-03 back-edge).
- **Risks**: whole-module-vs-symbol trap (`model_routing` consumers use submodules as modules — door must re-export the callables `load`/`evaluate`/`RoutingRecommendation`, and IC-04 migrates call sites to symbol access); `DoctrineService` must NOT be added to the identity table (it is a wrapper — IC-05).

### IC-04 — Runtime migration + laundering closure

- **Purpose**: Migrate the ~34 lazy-import runtime files onto the charter facades (consuming the management-surface enumeration IC-01 owns — IC-04 does not itself reclassify); convert whole-module call sites to symbol imports; close the first-party re-export laundering conduit by de-exporting doctrine symbols from `specify_cli.doctrine.config.__all__` and routing its ~10-30 non-exempt consumers through the charter `resolve_org_roots` door.
- **Relevant requirements**: FR-004, C-005; SC-001.
- **Affected surfaces**: ~34 files under `src/specify_cli/` (`invocation/executor.py`, `cli/commands/doctrine.py`, `_doctrine_collect.py`, `tool_surface/bundles/{claude,codex}.py`, `runtime/resolver.py`, migrations, …); `src/specify_cli/doctrine/config.py` (stop outbound re-export).
- **Sequencing/depends-on**: IC-03 (facade must exist before the file that needs it migrates; facade-blocked files wait on their door); IC-01 (management enumeration).
- **WP fault lines (pre-signal for /tasks):** (1) **conduit closure is ONE atomic WP** — `config.py` de-export + all its non-exempt consumers repointed together, else a partial WP breaks imports at runtime between WPs; (2) the rest splits **per-consuming-door-cluster**, each cluster depending on exactly one IC-03 door WP.
- **Risks**: facade-blocked ordering; keeping genuinely load-bearing lazy shapes (circular-import/optional-dep/`try-except`) while only changing the *target* to `charter.*`.

### IC-05 — Sole-door bypass fix

- **Purpose**: Remove the raw `doctrine.service.DoctrineService` construction from the 5 sites so the sole-door test passes — **but preserve each site's current filtering semantics (C-006).** Post-plan feasibility review found 4 of 5 sites (`_doctrine_collect.py:209/314/468/920`) deliberately construct with `pack_context=None` (unfiltered by intent, per their docstrings); only `_doctrine_asset.py:93` passes a real `pack_context`. Blindly routing the 4 unfiltered sites through `build_activation_aware_doctrine_service` would **add** activation filtering and change behavior. Correct move: the filtered site uses the builder; the intentionally-unfiltered sites obtain the raw repository via `raw_repository()` off the wrapped door (or the builder's documented unfiltered path), never a direct `RawDoctrineService(...)`.
- **Relevant requirements**: FR-005, C-006; `test_charter_sole_door_doctrine_service.py`.
- **Affected surfaces**: `cli/commands/_doctrine_asset.py`, `cli/commands/_doctrine_collect.py`.
- **Sequencing/depends-on**: IC-03 (builder path available) — parallelizable with IC-04.
- **Risks**: the C-006 trap above — do not convert the 4 `pack_context=None` sites into filtered ones. Verify per-site filtering semantics before/after.

### IC-06 — Lazy-import ratchet (+ laundering rule)

- **Purpose**: Add the sibling ratchet in `test_runtime_charter_doctrine_boundary.py`. **Use a parent-tracking recursive descent, NOT a bare `ast.walk`** — `ast.walk` flattens the tree and loses the enclosing-block context needed to (a) skip `if TYPE_CHECKING:` imports and (b) distinguish module-level from nested. The descent tracks `(depth, under_TYPE_CHECKING)`; matches absolute `doctrine`/`doctrine.*` with `ImportFrom.level == 0`; excludes the enumerated management surface; uses an only-shrink frozenset baseline seeded at the census. **The laundering rule is SOURCE-side** (from the gate-efficacy review): assert that no `src/specify_cli/doctrine/*` module lists a doctrine-origin symbol in its `__all__` — this is cleanly static and matches IC-04's "stop outbound re-export," whereas a consumer-side check cannot distinguish a laundered symbol from a genuine first-party one (identical import syntax). State the `import doctrine` (metadata introspection, `codex.py`) + aliased-import + dynamic-import (`importlib`, 0 today) disposition explicitly. Closes the runtime→doctrine half of #2986.
- **Relevant requirements**: FR-006; SC-003.
- **Affected surfaces**: `tests/architectural/test_runtime_charter_doctrine_boundary.py`; fixtures proving a `TYPE_CHECKING` doctrine import is NOT flagged and a nested-function one IS.
- **Sequencing/depends-on**: IC-01 (baseline seed + management enumeration — no back-edge to IC-04). **Lands early with the full baseline (red-first), then IC-04 shrinks it** — the stale-entry check proves each migration.
- **Risks**: false positives on exempt relative imports; must not double-count the module-level ratchet's domain (the descent's depth-tracking handles this).

### IC-07 — INTERNAL negative guard

- **Purpose**: Add a negative architectural test asserting the truly-internal paths (no non-exempt consumer) are absent from both `doctrine/api.py __all__` and every `charter.*` facade — turning "kept hidden" from intent into enforcement.
- **Relevant requirements**: FR-007.
- **Affected surfaces**: `tests/architectural/test_doctrine_public_surface.py`.
- **Sequencing/depends-on**: IC-01 (the INTERNAL set), IC-02/IC-03 (surfaces to assert against).
- **Risks**: the set is only "truly internal" after IC-01 reconciles non-exempt consumers; guard must track that set, not the stale brief list.

### IC-08 — Campsite Sonar (duplicate literals + suppression)

- **Purpose**: Hoist duplicate DRG-URN literals in `hand_authored_overlay.py` to named constants (FR-009); fix the malformed suppression at `artifact_kinds.py:118` (FR-011). Both behavior-preserving, guarded by the round-trip.
- **Relevant requirements**: FR-009, FR-011; C-006.
- **Affected surfaces**: `src/doctrine/drg/migration/hand_authored_overlay.py`, `src/doctrine/artifact_kinds.py`.
- **Sequencing/depends-on**: **IC-01 (the golden baseline)** — `hand_authored_overlay.py` writes the reference graph, so FR-009 mutates DRG-regeneration-affecting code and its behavior-preservation is unguarded without the golden snapshot captured first. (Corrected from "none" per post-plan seams review.)
- **Risks**: over-DRY collapsing two coincidentally-equal-but-independent URNs into one constant — caught by the byte-identical `regenerate-graph --check` round-trip.

### IC-09 — Complexity refactor (isolated, governed, last)

- **Purpose**: Reduce `extractor.py:545` (cc 183) and 7 other `S3776` functions to ≤ 15, behavior-preserving, verified against IC-01's golden `regenerate-graph` output via the existing `regenerate-graph --check` mechanism (no bespoke fixture needed). Each extracted helper carries its own focused test. Governed by the disciplined-refactoring / semantic-compression doctrine (activate tactic for mission).
- **Relevant requirements**: FR-010; NFR-003; C-006; C-007-mission.
- **Affected surfaces**: `src/doctrine/drg/migration/extractor.py` (+ `versioning.py`, `agent_profiles/repository.py`, `base.py`, `drg/validator.py`, `drg/merge.py`, `drg/org_pack_loader.py`); a `regenerate-graph --check` round-trip test in CI.
- **Sequencing/depends-on**: IC-01 (golden baseline); otherwise **last**, independently revertable — sequenced last to isolate refactor risk from the boundary deliverable.
- **WP fault lines (pre-signal for /tasks):** golden baseline (IC-01, shared) → `extractor.py` cc-183 refactor (its own WP) → the remaining 7 `S3776` functions (parallel, per-file, each independently revertable). Do not treat IC-09 as one unrevertable block.
- **Risks**: highest-risk slice; complexity-shuffling into untested no-op helpers (mitigated by per-helper tests + real cc measurement); DRG output drift (mitigated by golden byte-identity). No file-collision with IC-08 — `extractor.py` and `hand_authored_overlay.py` are distinct with no import edge; only the shared golden couples them.
