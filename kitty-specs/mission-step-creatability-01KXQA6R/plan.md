# Implementation Plan: Mission-Type Creatability via Rich Step Model

**Branch**: `feat/mission-step-creatability` | **Date**: 2026-07-17 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/mission-step-creatability-01KXQA6R/spec.md`

## Summary

Complete the step-authority cutover for `template_set` and make the `documentation`/`research`/`plan` mission types creatable again, then graph-back the `mission_type → step → template` chain. Three sequenced concerns, **tidy-first**: **(A)** retire the persisted `MissionType.template_set` field and read the step authority at the consumption boundary (behavior-preserving, atomic); **(B)** author the three types' content on their own step names so they project a non-null template mapping (Q1-gated); **(C)** mint `template:` DRG nodes + `step → template instantiates` edges and add a resolve-by-URN lane. Design is locked by the ADR (2026-07-16-2 D3 + 2026-07-17 Amendment), a research squad, an adversarial verification squad (LAND), a Q1 code trace, and a spec-review squad (plan-ready). Follow-up `#2751` carries the `action_sequence` symmetry.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: pydantic (frozen models, `extra="forbid"`), ruamel.yaml (doctrine YAML), typer/rich (CLI) — no new dependencies
**Storage**: doctrine YAML on disk (`src/doctrine/missions/`, `src/doctrine/*.graph.yaml`); no database
**Testing**: pytest; ATDD red-first through pre-existing entry points; `tests/doctrine/`, `tests/charter/`, `tests/architectural/`, `tests/doctrine/drg/` freshness; `PWHEADLESS=1` for any UI-adjacent runs (none here)
**Target Platform**: cross-platform CLI (Linux/macOS/Windows)
**Project Type**: single project (doctrine layer + charter/runtime consumers)
**Performance Goals**: no regression to the FSM `<100ms` hot path (unaffected — `template_set` is off it); FR-002 seam performs exactly one `mission-steps/` resolution per `(mission_type, pack_context)` (NFR-003)
**Constraints**: behavior-preserving except the intentional field retirement + new content + new `instantiates` edges; ruff + mypy --strict clean, zero new suppressions; complexity ≤15; hoist ≥3× literals; DRG baseline 280/757/10 fresh
**Scale/Scope**: ~4-5 code sites for the cutover + ~6 test-file migrations (Concern A); 16 authored prompts + per-type template refs (Concern B); 1 new extractor pass + 1 resolver lane + DRG re-baseline (Concern C)

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Single canonical authority** ✅ — the mission collapses a duplicate projection onto the one step authority (net *improvement*).
- **Architectural alignment / DDD-tiered rigour** ✅ — changes stay in the doctrine layer + its charter/runtime consumers; the C-002 scalar fence prevents cross-domain leakage.
- **ATDD-first / red-first** ✅ — every concern lands a red test through the pre-existing entry point first (creation path, projection, extractor, resolver).
- **Terminology canon** ✅ — no `feature`/legacy terms; Mission canon respected (terminology guard run on prose).
- **Canonical sources** ✅ — content authored on the doctrine step surface; no improvised substitutes.
- **Git/workflow** ✅ — PR-bound, operator merges; no direct origin/main push.

No violations → Complexity Tracking left empty.

## Project Structure

### Documentation (this mission)

```
kitty-specs/mission-step-creatability-01KXQA6R/
├── plan.md              # This file
├── spec.md              # committed
├── research.md          # 2-squad grounding + Q1 (committed)
├── data-model.md        # schema/graph deltas (this command)
├── quickstart.md        # validation scenarios (this command)
├── contracts/           # creation artifact_key + name↔URN + DRG-delta contracts (this command)
├── checklists/requirements.md   # spec-quality checklist (committed)
├── traces/              # 3 tracer files (this command)
└── tasks.md             # /spec-kitty.tasks output — NOT created here
```

### Source Code (repository root)

```
src/doctrine/missions/
├── models.py                     # MissionType (retire template_set field) [Concern A]
├── mission_type_repository.py    # _inject_projected_fields (drop template_set overlay, keep action_sequence) [A]
├── mission_step_repository.py    # memoise default() [A]
├── step_projection.py            # order steps by sequence_index (determinism) [A — sole owner]
├── mission_types/*.yaml          # unchanged (already carry neither field)
└── mission-steps/
    ├── documentation/<step>/{prompt.md,step.yaml}   # author 7 prompts + template refs [Concern B]
    ├── research/<step>/{prompt.md,step.yaml}         # author 5 prompts + template refs [B]
    └── plan/<step>/{prompt.md,step.yaml}             # author-fresh 4 prompts + scaffolds [B]
src/doctrine/missions/{documentation,research,plan}/templates/   # per-type template files [B]
src/doctrine/drg/migration/extractor.py              # new instantiates pass [Concern C — sole owner]
src/doctrine/*.graph.yaml                            # regenerated (action.graph.yaml gains edges) [C]
src/doctrine/template_catalog.py                     # URN authority (consumed) [C]
src/charter/mission_type_profiles.py                 # _resolve_template_set_slot :744 (in-scope slot only) [A]
src/specify_cli/runtime/resolver.py                  # add resolve-by-URN lane (signature stable) [C]
src/specify_cli/cli/commands/mission_type.py         # migrate :1491/:1509 reads [A]
tests/doctrine/missions/test_prompt_emptiness.py     # coupled edit + scaffold retirement [Concern B — sole owner]
tests/doctrine/drg/ + test_extractor_projection.py   # DRG count bump + instantiates assertion [C]
```

**Structure Decision**: single-project doctrine layer. Ownership is partitioned along the A→B→C sequence with the shared seams assigned to a single concern each (see C-009..C-012 in the IC map).

## Implementation Concern Map

> Concerns are NOT work packages. `/spec-kitty.tasks` translates these into WPs. Sequencing: **A (IC-01) → B (IC-02/03/04, then IC-05) → C (IC-06/07, IC-08 verifies)**.

### IC-01 — Atomic structural cutover (Concern A)

- **Purpose**: Retire the persisted `MissionType.template_set` field and source the projection from the step authority, behavior-preserving — a single atomic change (C-009) so no intermediate tree has a dangling `.template_set` read under `extra="forbid"`.
- **Relevant requirements**: FR-001, FR-002, FR-003, FR-011 (step ordering), NFR-001, NFR-003, C-001, C-002, C-005, C-006, C-007, C-009.
- **Affected surfaces**: `models.py` (remove field), `mission_type_repository.py:_inject_projected_fields` (drop the `template_set` overlay `:200-202`; **keep** the `action_sequence` overlay `:199`), `mission_step_repository.py` (**memoise `resolve_all_for_mission_type` keyed by `(mission_type, pack_context)`** — NOT just `default()`; the filesystem walk lives in `resolve_all_for_mission_type`, and after the cutover **two** consumers hit it per resolution [the retained `action_sequence` overlay + the new `template_set` slot], so the cache must be **shared**, with a `.cache_clear()` test seam — paula d3), `step_projection.py` (**sole owner** — order steps by `sequence_index`, mirroring `project_action_sequence`; **expose a public `iter_template_refs(steps) -> list[(MissionStep, MissionStepTemplateRef)]`** promoting the private `_step_template_ref:111`, consumed by BOTH `project_template_set` AND IC-06's pass so there is one traversal of `step.template`, not two — paula fold-in), `charter/mission_type_profiles.py:744` (`_resolve_template_set_slot` → `project_template_set(steps)`; **never** the scalar `:145/:1001`), `cli/commands/mission_type.py:1491,1509-1511` (migrate to resolved context + `dict()`-wrap). Tests: from `TestMissionTypeRepositoryLiveProjection` (class `:115`) retire **only** `test_default_resolves_software_dev_template_set` (`:131-135`) — **KEEP** `test_default_resolves_software_dev_action_sequence` (`:125-129`, validates the C-007-retained overlay); migrate every `.template_set` read on a `MissionType` instance (grep-driven — explicitly **includes `test_mission_type_repository.py:47`**, outside the `:89-105/:181-197` ranges — paula d1) → `project_template_set`/`ResolvedMissionType`; **keep** `TestSoftwareDevProjectionParity`; add the missing CLI test, the one-walk **shared-cache** call-count test (NFR-003), the pack-authored-`template_set`-fails-loudly regression, and the software-dev filename + canonical-`--json`-order parity. Optional campsite: freshen the stale `tests/runtime/test_runtime_seam.py:18-24` docstring if touched.
- **Sequencing/depends-on**: none (lands first).
- **Risks**: atomicity (C-009 — one WP or strictly-ordered same tree); the scalar co-habits `mission_type_profiles.py` (C-002 — no blind grep-replace); must not rename the resolved property (C-006); must not touch the `action_sequence` overlay (C-007). Behavior-preservation is provable today (software-dev steps already carry refs → identical projection).

### IC-02 — Documentation content authoring (Concern B)

- **Purpose**: Make `documentation` creatable by authoring its 7 step prompts + template refs on its own step names.
- **Relevant requirements**: FR-004, FR-007 (doc), NFR-004, C-003, C-010.
- **Affected surfaces**: `src/doctrine/missions/mission-steps/documentation/{discover,audit,design,generate,validate,publish,accept}/{prompt.md,step.yaml}`; `src/doctrine/missions/documentation/templates/**` (rename/replace the existing software-dev-shaped files to documentation vocabulary). Promote content from the existing `guidelines.md`.
- **Sequencing/depends-on**: IC-01 (clean surface); Q1 contract (C-010) — author `artifact_key: "spec"` on a step + `"plan"` on another.
- **Risks**: genuine content not gamed (NFR-004); do not touch `test_prompt_emptiness.py` (IC-05 owns it).

### IC-03 — Research content authoring (Concern B)

- **Purpose**: Make `research` creatable by authoring its 5 step prompts + template refs on its own step names.
- **Relevant requirements**: FR-005, FR-007 (research), NFR-004, C-003, C-010.
- **Affected surfaces**: `mission-steps/research/{scoping,methodology,gathering,synthesis,output}/{prompt.md,step.yaml}`; `research/templates/**` (rename/replace to research vocabulary). Promote from `guidelines.md`.
- **Sequencing/depends-on**: IC-01; Q1 (C-010).
- **Risks**: as IC-02.

### IC-04 — Plan content authoring (Concern B — HEAVIEST, author-fresh)

- **Purpose**: Make `plan` creatable — author 4 step prompts **and** its scaffold template files from scratch (no `guidelines.md`, empty `templates/`).
- **Relevant requirements**: FR-006, FR-007 (plan), NFR-004, C-003, C-010.
- **Affected surfaces**: `mission-steps/plan/{specify,research,plan,review}/{prompt.md,step.yaml}`; `plan/templates/**` (author-fresh scaffolds). Plan-domain (decomposition/decision, no code); do **not** clone the software-dev shape despite the `specify`/`plan` name collision.
- **Sequencing/depends-on**: IC-01; Q1 (C-010) — Q1 fixes plan's requested `artifact_key`s (`spec`/`plan`) and thus the scaffold set.
- **Risks**: largest concern — do not size symmetric with IC-02/03; name-collision contamination (C-003 — per-type `template_file`, NFR-006 guard).

### IC-05 — Emptiness-test ownership + retirement (Concern B, single owner)

- **Purpose**: Keep the emptiness guard truthful as prompts fill, then retire the seeded-blank scaffold.
- **Relevant requirements**: FR-008, NFR-004, C-011.
- **Affected surfaces**: `tests/doctrine/missions/test_prompt_emptiness.py` (**sole owner**) — shrink `_SEEDED_BLANK_STEPS`, drop each `xfail`, decrement golden `16`, update `_SEQUENCE_STEPS_BY_TYPE`; once empty, retire the scaffold and add a positive "every sequence step has a non-empty prompt" assertion + the reviewer-checklist substance gate hook.
- **Sequencing/depends-on**: IC-02, IC-03, IC-04 (their authored prompts are inputs).
- **Risks**: C-011 — a single owner prevents three WPs merge-conflicting on the golden count.

### IC-06 — Graph-back extractor pass + DRG re-baseline (Concern C)

- **Purpose**: Emit the `mission_type → step → template` chain into the shipped graph.
- **Relevant requirements**: FR-009, FR-011 (edge-emission sort), NFR-002.
- **Affected surfaces**: `src/doctrine/drg/migration/extractor.py` (**sole owner** — new pass modeled on `extract_mission_type_edges`, consuming IC-01's shared `iter_template_refs(steps)` helper — NOT a second private step-iteration — because the ref is a structured `MissionStepTemplateRef` field, not a `references:` entry); regenerated `action.graph.yaml` (gains edges) + `template.graph.yaml` (nodes-only; 16 bare exemplars untouched); `tests/doctrine/drg/` + `test_extractor_projection.py` (bump `_EXPECTED_NODE/EDGE_COUNT` to `280+N`/`757+N`, orphans stay 10) + positive instantiates assertion; sweep every arch marker (orphan-residual, `_ARCH_SHARD_N_FILES`, cardinality golden-counts).
- **Sequencing/depends-on**: IC-02/03/04 (refs exist) — **N is computed here, after authoring, never pinned upfront**. Reads `step_projection.py` (owned by IC-01, read-only).
- **Risks**: determinism (relies on IC-01's `sequence_index` ordering); arch-marker sweep completeness.

### IC-07 — Resolve-by-URN lane (Concern C)

- **Purpose**: Add URN-addressed resolution as a second lane alongside resolve-by-name.
- **Relevant requirements**: FR-010, C-002, C-004.
- **Affected surfaces**: `src/specify_cli/runtime/resolver.py` (add a URN function converging on `template_catalog.resolve_template_by_id`, mission-qualified form; signature of `resolve_configured_template` unchanged) + a by-URN==by-name equivalence test incl. override-wins (US3.3).
- **Sequencing/depends-on**: IC-01 (cutover); IC-06 (qualified nodes exist).
- **Risks**: C-002 — `resolver.py` neighbours the scalar surfaces; the fence is on *referencing the scalar*, not on importing `ResolvedMissionType`. C-004 — two lanes, do not collapse; do not re-wire the name-based creation path.

### IC-08 — Cross-type uniqueness + NFR guards (verification)

- **Purpose**: Assert the cross-cutting invariants that no single authoring WP owns.
- **Relevant requirements**: NFR-006, C-003; SC-004 shipped-graph assertion.
- **Affected surfaces**: a guard test asserting no two mission types project the same `template_file`; may fold into IC-05/IC-06 at /tasks.
- **Sequencing/depends-on**: IC-02/03/04 (refs authored).
- **Risks**: minor; keep as a standalone guard so ownership is clear.
