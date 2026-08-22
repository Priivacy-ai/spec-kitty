# Implementation Plan: Deliver Loaded Doctrine to the Agent

**Branch**: `m4-doctrine-delivery` | **Date**: 2026-08-19 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/deliver-loaded-doctrine-01M0DSQM/spec.md`

## Summary

Close four silent delivery/render no-ops so authored doctrine that loads and validates clean actually reaches the dispatched agent (#3489, #3176, #3389, #3488 render half). The work splits into three file-disjoint groupings: (A) the action-bundle delivery-table/render family — give `GLOSSARY_PACK` a real slot + term-name render row, restore the stated reason for every remaining `None` row (close the class, incl. `ANTI_PATTERN`), render procedure/tactic step `description`, and document the deliberate styleguide/toolguide pointer-only choice; (B) the `#3176` builder overlay seam — thread an optional `agent_profile_overlay_dir` through the doctrine-service builders so `.kittify/agent_profiles` is reachable and `default_profile_repository` can migrate onto it; (C) the `#3389` `procedures[]` typed array in `context --json` — a deliberate versioned-contract bump. NFR-001 token budget is respected throughout (glossary is names-only + fetch pointer; styleguide/toolguide stay pointer-only).

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: pydantic (doctrine models), typer (CLI), ruamel.yaml; no new dependencies added
**Storage**: Filesystem doctrine packs (`packs/built-in`, org roots, `.kittify/doctrine`, `.kittify/agent_profiles`); no database
**Testing**: pytest (targeted per-module; `tests/charter/`, `tests/doctrine/`, `tests/specify_cli/tool_surface/profiles/`), red-first per fix; `ruff` + `mypy --strict` zero new suppressions
**Target Platform**: Linux/macOS developer + CI (spec-kitty CLI)
**Project Type**: single (Python package under `src/`)
**Performance Goals**: NFR-001 token budget — no full glossary definitions inlined (names-only surface list + `--include` fetch pointer); existing per-entry inline-body cap (`_PROFILE_INLINE_BODY_LIMIT_CHARS`) unchanged
**Constraints**: `charter` must not import `specify_cli` (C-001); overlay param default `None` byte-identical (NFR-002); single-wrapper-body invariant (C-006); `procedures[]` schema bump atomic with ledger (C-005); OUT — op-proc edge wiring (M3) / cascade completeness (M5), no golden-count ripple beyond the deliberate schema-version bump (C-004)
**Scale/Scope**: ~10 source files across `src/charter/`, `src/doctrine/`, `src/specify_cli/tool_surface/profiles/`; 3 parallel work packages

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Charter (`.kittify/charter/charter.md`) present — compact governance context loaded for `plan`. Relevant governing rules and how this plan satisfies them:

- **Single canonical authority** — the delivery table (`_ACTION_BUNDLE_DELIVERY_BY_KIND`) and the JSON key ledger (`CONTEXT_CONTRACT_TOP_LEVEL_KEYS`) stay the single totality-guarded authorities; we grow them, we do not add parallel copies. The overlay seam adds one parameter threaded through the single builder body (no second construction site — C-006).
- **DDD + tiered rigour** — render/delivery is a seam between the doctrine model and the agent; changes stay in the render/builder layer, model shapes (`ProcedureStep.description` etc.) are already present and unchanged.
- **ATDD-first / red-first** — every fix lands with a failing test proven red on the merge-base first (C-003). No green-washing.
- **Architectural gate discipline** — `charter` must not import `specify_cli` (C-001); the overlay authority lives in `charter.doctrine_service_builder` / `doctrine.service`, consumed by `specify_cli.tool_surface.profiles`.
- **Canonical sources** — versioned-contract bump (`CONTEXT_SCHEMA_VERSION` + ledger) is deliberate and atomic (C-005), not incidental.
- **Terminology canon** — no `feature*` aliases introduced; "Mission" canon respected; no new user-facing prose that would trip the terminology guard (run `pytest tests/architectural/test_no_legacy_terminology.py` before push since WP-A/WP-C touch renderer prose + docs).

No Constitution violations requiring justification. Complexity Tracking below is empty.

## Project Structure

### Documentation (this mission)

```
kitty-specs/deliver-loaded-doctrine-01M0DSQM/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output (seam→home map, entity shapes)
├── quickstart.md        # Phase 1 output (verification walkthrough)
├── contracts/           # Phase 1 output (delivery-table + context-json contracts)
└── tasks.md             # Phase 2 output (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)

```
src/charter/context_renderers/
├── delivery_table.py        # WP-A: GLOSSARY_PACK slot + gate + stated-reason class-close
├── bootstrap_text.py        # WP-A: _ACTION_RENDER_ROWS glossary render row
├── artifact_bodies.py       # WP-A: _format_inline_procedure_body / _format_inline_tactic_body step description; glossary term-list body
└── profile_sections.py      # WP-A: format_inline_named_body step description; document styleguide/toolguide pointer-only

src/charter/
├── doctrine_service_builder.py   # WP-B: thread agent_profile_overlay_dir through both builders
├── _doctrine_paths.py            # WP-B: (read-only ref) project-root candidate list — overlay is a distinct seam
├── progressive_disclosure.py     # WP-C: _ARRAY_BY_KIND add "procedure"
├── context.py                    # WP-C: move procedure from extra_delivered to repos_by_kind
└── context_contract.py           # WP-C: bump CONTEXT_SCHEMA_VERSION + add "procedures" to ledger

src/doctrine/
└── service.py                    # WP-B: agent_profiles property honours the overlay dir override

src/specify_cli/tool_surface/profiles/
└── projection.py                 # WP-B: default_profile_repository migrates onto the overlay seam; delete carve-out

tests/
├── charter/                      # WP-A + WP-C: delivery-table, render, context-parity, totality
├── doctrine/                     # WP-A: kind-mapping totality / unknown-kind-fails-loudly
└── specify_cli/tool_surface/profiles/  # WP-B: test_projection*, collision_precedence, org_visibility (un-carve)
```

**Structure Decision**: Single Python package (`src/`). The three work packages are file-disjoint (WP-A owns `context_renderers/*`, WP-B owns the builder/service/projection chain, WP-C owns `progressive_disclosure`/`context`/`context_contract`), so they run as parallel lanes with no cross-file contention.

## Complexity Tracking

*No Constitution Check violations — section intentionally empty.*

## Parallel Work Analysis

### Dependency Graph

```
        ┌── WP-A (lane-a): delivery-table/render family ──┐
(none) ─┼── WP-B (lane-b): builder overlay seam #3176    ─┼─► consolidate → PR to main
        └── WP-C (lane-c): procedures[] JSON contract #3389┘
```

All three WPs are independent: no shared source files, no ordering constraint. Each carries its own red-first tests and its own totality/ledger guard. There is no foundation WP and no separate gate WP — the totality guards (`test_action_bundle_delivery.py`, `test_kind_mapping_totality.py`, `test_context_parity.py`) already exist; each WP extends the one it touches.

### Work Distribution

- **Sequential work**: none — the WPs are file-disjoint.
- **Parallel streams**:
  - **WP-A** — `src/charter/context_renderers/{delivery_table,bootstrap_text,artifact_bodies,profile_sections}.py` + their `tests/charter` + `tests/doctrine` guards + docs for the pointer-only ratification.
  - **WP-B** — `src/charter/doctrine_service_builder.py`, `src/doctrine/service.py`, `src/specify_cli/tool_surface/profiles/projection.py` + `tests/specify_cli/tool_surface/profiles/*`.
  - **WP-C** — `src/charter/{progressive_disclosure,context,context_contract}.py` + `tests/charter/test_context_parity.py` and a new procedures[] JSON test.
- **Agent assignments**: one lane per WP (lane-a/b/c), each in its own `.worktrees/deliver-loaded-doctrine-01M0DSQM-lane-<x>` worktree.

### Coordination Points

- **Sync schedule**: WPs merge into `m4-doctrine-delivery` independently on approval; consolidation review runs a squad on the combined diff before the PR to `main`.
- **Integration tests**: after all three merge, run the touched-module targeted suites together (`tests/charter`, `tests/doctrine/drg`, `tests/specify_cli/tool_surface/profiles`) plus `tests/architectural/test_no_legacy_terminology.py`; CI is the release authority.
