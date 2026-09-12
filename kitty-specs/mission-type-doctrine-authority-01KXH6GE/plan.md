# Implementation Plan: Mission-Type Doctrine Authority

**Branch**: `mission/883-mission-type-governance-profiles` | **Date**: 2026-07-14 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/mission-type-doctrine-authority-01KXH6GE/spec.md`
**Design authority**: [ADR 2026-07-14-2](../../docs/adr/3.x/2026-07-14-2-doctrine-to-core-mission-type-resolution-unification.md) · [mission brief](../../docs/plans/engineering-notes/883-mission-type-authority-brief.md) · [research dossier](../../docs/plans/engineering-notes/883-research-synthesis.md)

## Summary

Make the doctrine **MissionType artefact the single, load-bearing source of truth**
for a mission type's governance, gates, and steps, resolved through one
charter-mediated `doctrine → charter → core` seam keyed off `meta.json`. Close the
`software-dev-default` leak on the governance and action paths, demote `software-dev`
to a peer mission type, author governance for documentation/research/plan, and swap
the dossier gate reader onto the doctrine tree (detachable lane) — slice 1 of the
`specify_cli/missions` retirement. The architecture is fixed by the ADR; this plan
decomposes it into implementation concerns and design contracts.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: pydantic v2 (models + `extra="forbid"`), ruamel.yaml (doctrine YAML), typer (CLI); internal subsystems `charter`, `doctrine`, `runtime.next`, `specify_cli.dossier`.
**Storage**: Doctrine YAML files under `src/doctrine/missions/` + the DRG (`src/doctrine/graph.yaml`); no database. N/A for runtime persistence.
**Testing**: pytest at two tiers — **doctrine-module unit** tests (no `specify_cli` import) and **integration** tests exercising a real mission resolution; `ruff` + `mypy --strict`; parallel `-n auto --dist loadfile`. Transitional parity scaffolds are added per swap and deleted before merge.
**Target Platform**: Linux CLI / library (Spec Kitty itself).
**Project Type**: single (Python package).
**Performance Goals**: N/A (governance resolution is not throughput-critical); **determinism is required** (identical inputs → byte-identical resolved governance, NFR-007).
**Constraints**: cyclomatic complexity ≤ 15 (ruff C901 / Sonar S3776); `charter/` must not import `specify_cli` (`tests/architectural/test_layer_rules.py`); no `# noqa`/`# type: ignore` additions; **no shim/compat code kept solely to avoid test churn**; **no surviving parity ratchet** (parity scaffolds are transitional).
**Scale/Scope**: 4 built-in mission types; ~10–12 WPs across 4 lanes; touches `charter`, `doctrine`, `runtime.next`, `specify_cli.dossier`, and `src/doctrine/missions/*`.

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Governing principle | This mission | Verdict |
|---------------------|--------------|---------|
| Single canonical authority | This mission *creates* the single authority (the doctrine MissionType artefact) and retires the duplicate tree; it does not add a competing surface. | ✅ Advances |
| Architectural alignment | Follows ADR 2026-07-14-2 (Accepted); the resolver seam reuses existing charter/doctrine machinery (extend-not-invent). | ✅ Pass |
| DDD + tiered rigour | Core resolution logic (charter/doctrine) is core-tier (full rigour); YAML authoring is glue. | ✅ Pass |
| ATDD-first / red-first | Leak closure and each swap begin with a RED behavioural test through the pre-existing entry point (DIRECTIVE_041). | ✅ Pass (enforced in ICs) |
| Architectural gate discipline | New enduring gate is the non-leakage + non-vacuity test (NFR-006); layer rule (C-001) respected. | ✅ Pass |
| Canonical sources & unification | Chases unification (one authority), not parity with the dead `governance_refs` quirk. | ✅ Pass |
| Terminology canon | "Mission", never "feature"; pre-push terminology guard runs on doctrine/prose. | ✅ Pass |

**No violations.** Layer-boundary note: the mission-type canonicalizer (IC-02) must live where both `charter` and `specify_cli` may consume it without `charter → specify_cli` import (C-001).

## Project Structure

### Documentation (this mission)

```
kitty-specs/mission-type-doctrine-authority-01KXH6GE/
├── plan.md              # This file
├── research.md          # Phase 0 output (design decisions, resolved)
├── data-model.md        # Phase 1 output (entities/contracts of the resolver bundle)
├── quickstart.md        # Phase 1 output (how to verify behaviour)
├── contracts/           # Phase 1 output (resolver / overlay / dossier / enforcement contracts)
└── tasks.md             # Phase 2 output (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)

```
src/
├── charter/
│   ├── mission_type_profiles.py   # resolver seam (resolve_mission_type_context, ResolvedMissionType/Governance), canonicalizer home
│   ├── context.py                 # action-path leak closure (_load_action_doctrine_bundle), thread mission_type
│   ├── scope_router.py            # thread feature_dir/mission_type
│   └── mission_type_repository / base.py (doctrine/)  # overlay adapter for per-type override
├── doctrine/
│   ├── base.py                    # builtin→org→project overlay stack (override adapter)
│   ├── missions/
│   │   ├── models.py              # MissionType model (retire governance_refs)
│   │   ├── mission_types/*.yaml   # MissionType artefacts (fix danglers)
│   │   ├── {documentation,research,plan}/governance-profile.yaml   # authored governance (Q1: referenced sibling)
│   │   ├── {…}/actions/*/index.yaml                                # action-grain governance
│   │   ├── repository.py          # get_expected_artifacts (dossier reader target)
│   │   └── */*.styleguide.yaml, */*.procedure.yaml                 # 6–8 net-new artifacts
│   └── graph.yaml                 # regenerated after authoring
├── runtime/next/
│   └── prompt_builder.py          # Surface B consumer → resolver
└── specify_cli/
    ├── mission.py                 # get_mission_type (remove sw-dev governance default)
    └── dossier/manifest.py        # gate reader flip (detachable lane) + adapter

tests/
├── doctrine/…                     # enduring doctrine-module tests (resolution, non-leakage, determinism)
├── integration/…                  # enduring integration tests (real mission resolution)
└── (transitional parity scaffolds, deleted before merge)
```

**Structure Decision**: Single Python package. No new top-level package; work lands
in the existing `charter`, `doctrine`, `runtime.next`, and `specify_cli.dossier`
subsystems plus doctrine YAML. Enduring tests split doctrine-module (unit) vs
integration; transitional parity scaffolds are removed at merge.

## Complexity Tracking

*No Charter Check violations to justify.* The one deliberate complexity note: the
resolver (`resolve_mission_type_context`) unifies two distinct hard-fail policies and
multiple slots — it MUST be kept ≤ 15 complexity via extracted private helpers
(`_resolve_type_key`, `_resolve_governance_slot`, `_resolve_action_slot`), not a flat
function. Tracked as an implementation constraint on IC-03, not a charter violation.

## Implementation Concern Map

> Concerns are NOT work packages. `/spec-kitty.tasks` translates these into WPs
> (IC-06 will fan out to three content WPs; IC-07/IC-08 carry transitional parity
> scaffolds). Do not read IC ordering as WP sequencing beyond the depends-on edges.

### Cross-cutting notes (post-plan squad reconciliation)

- **Dependency chain (corrected):** `IC-01` (independent tidy) · `IC-02 → IC-03 → {IC-04, IC-05, IC-06, IC-08} → IC-09` · `IC-07` is an independent, **detachable, non-blocking** lane with an internal hard edge (reconcile → migrate); **IC-09 does NOT depend on IC-07**.
- **Two distinct models — not a collision.** `MissionType` (the artefact model, `src/doctrine/missions/models.py`) is edited by IC-01; `MissionTypeProfile` (the governance-profile model, `src/charter/mission_type_profiles.py`) is edited by IC-05. Different files, different layers → **no `models.py` merge collision** (an earlier note calling this a collision was wrong). The existing `doctrine/missions/mission_type_repository.py::MissionTypeRepository` loads the *artefact* model and must not be confused with the new `MissionTypeProfile` overlay repo (IC-05).
- **Canonicalizer census (IC-02 owns):** `src/specify_cli/mission.py` has multiple `software-dev`-defaulting sinks — `get_mission_type:575`, `get_deliverables_path:605`, and the dead `get_mission_key:548` (no live src callers → retire). `get_mission_type` has **~13 live callers**; each must be classified (has `meta.json` → unaffected; typeless → neutral degrade, never software-dev; `next_cmd.py:658` documents reliance on the default). The census enumerates and routes all sinks/callers, or scopes specific ones OUT with rationale — a partial fix leaves the split half-closed.
- **Subsume-not-add (IC-03 owns):** the three subsumed functions (`resolve_action_sequence`, `resolve_mission_type_governance`, `load_profile`) are in `charter/__init__.py __all__` and have **8 live callers** (5 FSM/runtime + 3 CLI). WP-SEAM migrates all 8 and dispositions the exports — it must not add `resolve_mission_type_context` beside the old three.
- **`id == mission_type` invariant (IC-05 ↔ IC-06):** riding the overlay means every `governance-profile.yaml` (software-dev + the 3 authored) gains an `id` equal to its `mission_type` (`extra="forbid"`); the overlay repo subclass lives in **`charter/`** (layer rule: `doctrine ↛ charter`).
- **Terminal DRG regenerate (join-owned):** IC-01 (dangler removal) and IC-06 (authoring) both touch `graph.yaml`; the final `regenerate-graph --check` runs once, after both land (assigned to the IC-09 join), so neither clobbers the other's freshness. Run the terminology guard before push (CI-only gate).
- **Relate-to (no fold):** #2532 (context.py god-module — IC-04's dead-pair deletion is a ~100-LOC down-payment, do not grow into the decompose) · #2628 (source of the IC-07 reconcile deltas) · #832 / #1755 (overlay + DRG regen precedent, cite) · #1740, #901 (adjacent/parent, OUT). Per the #883 partial-close: **no auto-close keyword.**

### IC-01 — Retire the inert `governance_refs` field
- **Purpose**: Remove the dead, dangling per-type `governance_refs` field so the artefact's governance resolves only through the live path (no danglers).
- **Relevant requirements**: FR-010.
- **Affected surfaces**: `src/doctrine/missions/models.py` (`MissionType`), `src/specify_cli/cli/commands/mission_type.py` (display), **all four** `src/doctrine/missions/mission_types/{software-dev,documentation,research,plan}.yaml` (each carries `governance_refs: []`; `MissionType` is `extra="forbid"`, so leaving any unedited reds every load), plus the dangling `DIR-010/011` in `software-dev.yaml`; the `drg.py:169` comment; tests asserting the field.
- **Sequencing/depends-on**: none (tidy-first; independent). No `models.py` collision with IC-05 (that edits a *different* model in `charter/` — see cross-cutting notes).
- **Risks**: missing one of the four YAMLs reds all MissionType loads; DRG parity guard re-point; update (not preserve) the ~3–4 tests that asserted the field.

### IC-02 — Single mission-type canonicalizer (boundary-safe)
- **Purpose**: One canonicalizer for the mission-type key consumed by both `charter` and `specify_cli`, removing the `software-dev` governance default; closes the leak on the governance/dossier path.
- **Relevant requirements**: FR-012, FR-001, FR-003, FR-003a, C-001.
- **Affected surfaces**: a boundary-safe canonicalizer module both layers may import (respecting `charter ↛ specify_cli`; placement legal because `specify_cli → charter` is allowed), `charter/mission_type_profiles.py` (read at `:380`), and the `specify_cli/mission.py` sinks — `get_mission_type:575` (remove sw-dev default), `get_deliverables_path:605`, and the dead `get_mission_key:548` (retire). **Caller census:** classify the ~13 live `get_mission_type` callers (`runtime_bridge.py:1232,2244`, `mission_runtime/resolution.py:946`, `next_cmd.py:665` [note `:658` documents default reliance], `research.py:102`, `tasks_parsing_validation.py:982`, `mission_setup_plan.py:678`, `sync/dossier_pipeline.py:250`, `workflow_executor.py:564`, `mission.py:768`, …) — has-`meta.json` → unaffected; typeless → neutral degrade.
- **Sequencing/depends-on**: none (Lane-B root; precedes IC-03/IC-04).
- **Risks**: layer-rule violation if placed wrong; **partial census leaves the split half-closed**; converting a silent-software-dev default into a silent-empty/crash at an un-adjudicated caller; the degrade branch (FR-003a) must be per-entry, not a blanket hard-error.

### IC-03 — Unified resolver seam (`ResolvedMissionType` bundle)
- **Purpose**: One charter-mediated `resolve_mission_type_context(repo_root, *, mission_type=None, feature_dir=None) → ResolvedMissionType` that both consumers converge on; governance is ordered + structured; type-grain (referenced `governance-profile.yaml`) ∪ action-grain with a URN-normalized disjointness guard.
- **Relevant requirements**: FR-006, FR-013, FR-004, FR-003 (hard-error raised in the resolver), **FR-009** (software-dev resolved as a peer, behaviour preserved), NFR-007, **NFR-001** (transitional governance parity scaffold); Q1/Q3.
- **Affected surfaces**: `src/charter/mission_type_profiles.py` (new bundle + resolver, **subsuming** `resolve_action_sequence:266`/`resolve_mission_type_governance:325`/`load_profile:175`) — **migrate all 7 live call-sites** (4 runtime: `runtime_bridge_composition.py:186,319`, `decision.py:601`, `prompt_builder.py:346`; 3 CLI: `cli/commands/mission_type.py:1477`, `charter/activate.py:152`, `charter/mission_type.py:82`; `load_profile` has 0 callers — only the `__all__` export) and disposition the `charter/__init__.py __all__` exports + the stale docstring at `charter/resolver.py:299` (subsume-and-migrate, **not** add-beside). The bundle's `expected_artifacts` slot is populated by **IC-07** (after upward reconcile), not here.
- **Sequencing/depends-on**: IC-02.
- **Risks**: leaving any of the 8 callers on the old functions → a **third resolution path entrenched**; complexity ceiling (extract `_resolve_type_key`/`_resolve_governance_slot`/`_resolve_action_slot`); preserve the two hard-fail policies as explicit branches; transitional byte-parity scaffold for software-dev (deleted after).

### IC-04 — Action-path leak closure
- **Purpose**: Rewire the *live* action-doctrine path off `template_set` inference onto `meta.json mission_type`; delete the dead `_render_action_scoped`/`_append_action_doctrine_lines` pair; split `template_set`.
- **Relevant requirements**: FR-002, FR-001, FR-003a, C-004.
- **Affected surfaces**: `src/charter/context.py` (`_load_action_doctrine_bundle:865`, reached via `build_charter_context:252` + `build_charter_context_json:3254`; the second stale default at `:1465` lives inside the **dead** pair to delete), `src/charter/scope_router.py:66` (thread `feature_dir`/`mission_type`). Deleting the dead pair (`_render_action_scoped:1500` / `_append_action_doctrine_lines:1451`, ~100 LOC) orphans `tests/charter/test_context.py:716` — **delete that test in the same WP** (it covers dead code). Do **not** delete `_filter_references_for_action` (survives via the live caller at `context.py:1065`).
- **Sequencing/depends-on**: IC-03.
- **Risks**: ~6 `build_charter_context` callers + ~36 test files updated (not shielded); per-entry degrade for the two mission-less callers (`executor.py:270`, `workflow.py:675`); RED-first behavioural test through a shared action name. **Campsite: OUT →** the `context.py` god-module decompose is #2532 (3266 LOC, 45 pre-existing suppressions) — this IC is a ~100-LOC down-payment only; do not grow into the decompose.

### IC-05 — Per-type project override channel
- **Purpose**: A project can override a mission type's governance, ridden through the existing `doctrine/base.py` overlay stack (builtin → org → project + collision warnings).
- **Relevant requirements**: FR-011, C-005 (Q2).
- **Affected surfaces**: `src/doctrine/base.py` overlay (keys on `id`, skips id-less files at `:249-256`), `MissionTypeProfile` in `src/charter/mission_type_profiles.py` (add `id`; currently keyed on `mission_type`, `extra="forbid"`), and a `BaseDoctrineRepository[MissionTypeProfile]` subclass that **must live in `charter/`** (layer rule: `doctrine ↛ charter`; the base is importable charter→doctrine). Do **not** reuse/confuse the existing `doctrine/missions/mission_type_repository.py::MissionTypeRepository` (loads the *artefact* model).
- **Sequencing/depends-on**: IC-03. No collision with IC-01 (different model/file — see cross-cutting notes).
- **Risks**: **`id == mission_type` invariant** — every `governance-profile.yaml` (software-dev + the 3 authored by IC-06) must add `id` equal to `mission_type` or field-merge mis-keys silently (binds IC-05 ↔ IC-06); overlay keys on `id` (the real adapter cost); layer-rule trip if the subclass is placed under `doctrine/`.

### IC-06 — Author non-software governance (documentation / research / plan)
- **Purpose**: Populate the three non-software governance sets (type-grain profile + action-grain index) and author the 6–8 net-new DRG-resolvable artifacts.
- **Relevant requirements**: FR-005, SC-004; and FR-002/NFR-006 (content makes non-leakage non-vacuous).
- **Affected surfaces**: `src/doctrine/missions/{documentation,research,plan}/governance-profile.yaml` + `actions/*/index.yaml`; net-new styleguides (Divio-type, plain-language, accessibility, publication, freshness-SLA), a research citation-discipline artifact, the missing `spike-timebox-policy` procedure; `src/doctrine/graph.yaml` regenerate + freshness.
- **Sequencing/depends-on**: IC-03 (schema stable) and the IC-05 `id` invariant (each authored `governance-profile.yaml` must carry `id == mission_type`). Fans out to **3 WPs, unevenly sized** (documentation ≈ 5 styleguides is materially heavier than research/plan) — size off the artifact inventory, not equal thirds. Parallel to IC-04.
- **Risks**: undersizing (import the ADR artifact inventory, not the requirement count); DRG freshness gate; terminology guard. **Campsite bonus:** authoring `spike-timebox-policy` closes a pre-existing dangler (`researcher-robbie.agent.yaml:60` references a file that does not exist).

### IC-07 — Gates/dossier swap (detachable, non-blocking lane)
- **Purpose**: Reconcile the drifted `expected-artifacts.yaml` **upward** into the doctrine tree, adapt `ConfigResult → ExpectedArtifactManifest`, flip the dossier reader onto the doctrine tree, delete the `specify_cli` copies — proving reduced dependence.
- **Relevant requirements**: FR-007, NFR-004, SC-005, **NFR-001** (dossier parity scaffold). Also **owns** the `ResolvedMissionType.expected_artifacts` slot population (after reconcile) so the seam bundle never reads an un-reconciled tree.
- **Affected surfaces**: `src/specify_cli/dossier/manifest.py:178` (reader flip; `load_manifest`), `src/doctrine/missions/repository.py:304` (`get_expected_artifacts` → `ConfigResult`; adapter `ExpectedArtifactManifest.model_validate(config_result.parsed)` — no `from_dict` today, + cache preserve), the 5 consumer sites (`dossier/indexer.py:77,130,307,359`, `sync/namespace.py:98`), and the two `expected-artifacts.yaml` trees.
- **Reconcile deltas (upward, WP-GATES-RECONCILE):** port **all** of the `specify_cli`-ahead deltas into the doctrine tree — `runtime.charter-lint.decay` → `lint-report.json`, `blocking: false`, **and** the `occurrence_map.yaml` bulk-edit NOTE comment block (behaviourally load-bearing docs). Source: #2628.
- **Sequencing/depends-on**: WP-GATES-RECONCILE **before** the flip (hard edge). **Independent, detachable lane — NON-blocking for IC-09**; final flip may **defer to slice 2** on deep drift (reconciliation still lands, deferral recorded, never silent).
- **Risks**: type-boundary crossing (adapter + cache); already-drifted content; **~29 `load_manifest` assertions in `tests/dossier/test_manifest.py` shift** the moment the reader flips — the reconcile-before-flip edge + transitional parity scaffold keep them green; transitional dossier-parity scaffold deleted after.

### IC-08 — Steps swap (step-contract resolution through the artefact)
- **Purpose**: Route step-contract resolution through the MissionType artefact bundle; migrate the `specify_cli` step-contract readers.
- **Relevant requirements**: FR-008, SC-007, **NFR-001** (steps parity scaffold); Q3.
- **Affected surfaces**: step-contract resolution in `runtime`/`doctrine`; `specify_cli` step-contract readers (WPs must pin exact anchors); the `step_contracts` bundle slot.
- **Sequencing/depends-on**: IC-03. Same transitional-parity-then-delete discipline.
- **Risks**: preserve software-dev step behaviour; migrate readers off `specify_cli`.

### IC-09 — Enforcement + test posture
- **Purpose**: The enduring behavioural guards: non-leakage (URN-normalized denylist) + non-vacuity twin (shared action name), deterministic-ordering test; delete all transitional parity scaffolds.
- **Relevant requirements**: NFR-005, NFR-006, NFR-007, SC-001/002/003/006.
- **Affected surfaces**: `tests/doctrine/…` (module) + `tests/integration/…`; removal of transitional scaffolds; the terminal `graph.yaml` `regenerate-graph --check` (runs once, after IC-01 + IC-06 both land).
- **Sequencing/depends-on**: **IC-03, IC-04, IC-06** (+ IC-08 for steps enforcement). **Explicitly EXCLUDES IC-07** — the enduring governance guards need the seam + leak-closure + content, not the detachable dossier flip; making the enforcement join depend on IC-07 would gate the mission/merge on a deliberately non-blocking lane (violating FR-007/NFR-004).
- **Risks**: vacuity (twin must fire through a shared action name); keep enduring tests behavioural, not code-shape ratchets; the terminal DRG regenerate must be the single owner so IC-01/IC-06 don't clobber freshness.
