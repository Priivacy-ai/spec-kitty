# Implementation Plan: Mission Retrospective Learning Loop

**Mission ID**: `01KQ6YEGT4YBZ3GZF7X680KQ3V` (mid8: `01KQ6YEG`)
**Mission slug**: `mission-retrospective-learning-loop-01KQ6YEG`
**Branch contract**: planning base `main` → final merge `main` (matches target ✅)
**Date**: 2026-04-27
**Spec**: [./spec.md](./spec.md)
**Checklists**: [./checklists/requirements.md](./checklists/requirements.md), [./checklists/release-gate.md](./checklists/release-gate.md)
**Issues covered**: [#468](https://github.com/Priivacy-ai/spec-kitty/issues/468) (epic), [#507](https://github.com/Priivacy-ai/spec-kitty/issues/507), [#506](https://github.com/Priivacy-ai/spec-kitty/issues/506), [#508](https://github.com/Priivacy-ai/spec-kitty/issues/508), [#509](https://github.com/Priivacy-ai/spec-kitty/issues/509), [#511](https://github.com/Priivacy-ai/spec-kitty/issues/511), [#510](https://github.com/Priivacy-ai/spec-kitty/issues/510)

---

## Summary

Spec Kitty already governs how missions run. This tranche makes it *learn from* every mission it runs.

The implementation introduces a single new package, `src/specify_cli/retrospective/`, that owns the governance contract: `retrospective.yaml` schema, atomic writer, mode detection, the eight retrospective events, the lifecycle gate, and the cross-mission summary read model. Doctrine, DRG, and glossary mutation stay where they belong — behind a synthesizer hook in the doctrine area (`src/specify_cli/doctrine/synthesizer/`) that the retrospective package calls when staged proposals are approved. The lifecycle gate is implemented once in `specify_cli.retrospective.gate` and consulted thinly from `specify_cli.next` (the canonical control loop) and from any status transition surface that needs mission-level mode policy. Operators invoke the retrospective lifecycle via `spec-kitty next` (built-in missions reach the `retrospect` action through a lifecycle terminus hook; custom missions reach the same action through their existing required `retrospective` marker step). They read findings via `spec-kitty retrospect summary`. They apply staged proposals via `spec-kitty agent retrospect synthesize`.

Eight new event names are defined locally in `specify_cli.retrospective.events` for this tranche, with an upstream PR opened in parallel against the external `spec_kitty_events` PyPI package. Once the upstream release lands, this tranche switches imports and removes the local module. No prompt-builder filtering is added; per-mission action surface calibration outcomes are expressed strictly as DRG edge changes in `src/doctrine/graph.yaml` and project-local graph overlays.

---

## Technical Context

**Language/Version**: Python 3.11+ (existing spec-kitty codebase).

**Primary Dependencies** (all already adopted):
- `pydantic` v2 — schema for `retrospective.yaml`, proposals, events.
- `ruamel.yaml` — round-trip-safe YAML writer.
- `typer` — CLI surface for `spec-kitty retrospect summary` and `spec-kitty agent retrospect synthesize`.
- `rich` — operator-facing report rendering.
- `pytest` — testing, including real-runtime integration tests.
- `mypy --strict` — type checking, charter requirement.
- `spec_kitty_events` (external PyPI) — eventual home of the eight retrospective events; consumed via the public boundary once upstream release lands.

**Storage**: filesystem only.
- Per-mission durable: `.kittify/missions/<mission_id>/retrospective.yaml`.
- Per-mission events: appended to the existing `kitty-specs/<slug>/status.events.jsonl` event log used by other lifecycle events (FR-018).
- Project-local doctrine/DRG/glossary surfaces remain where they already live (`src/doctrine/graph.yaml`, project overlays under `.kittify/`).

**Testing**:
- Unit tests for schema validation, writer round-trip, mode detection, gate decisions, summary reduction.
- Real-runtime integration tests that drive a fixture mission through autonomous and HiC terminus paths end-to-end (FR-033). No private-helper-only acceptance.
- Architectural test asserting no prompt-builder filtering call sites are added (C-011).
- Property/fuzz test for malformed `retrospective.yaml` corpus tolerance (NFR-004).

**Target Platform**: macOS / Linux developer environments and CI; same surface as the rest of the spec-kitty CLI.

**Project Type**: single — Python CLI package with embedded subsystems.

**Performance Goals** (from spec NFRs, restated for measurement environment):
- NFR-001: schema validation of a typical (≤200 findings) `retrospective.yaml` < 200 ms on a developer laptop (warm interpreter, SSD).
- NFR-003: cross-mission summary on a 200-mission corpus < 5 s on a developer laptop.
- NFR-007: gate adds < 500 ms to mission completion when `retrospective.completed` is already present.

**Constraints** (mapped from spec):
- C-006: no imports from the retired `spec_kitty_runtime` package; only the CLI-internal runtime under `src/specify_cli/next/_internal_runtime/` is in scope.
- C-007: use canonical typed `Lane`, `WPState`, status `emit/reduce` primitives.
- C-011: calibration outcomes are DRG edges only — no prompt-builder filtering.
- C-013: charter override is sovereign in mode detection.
- C-014: canonical path is keyed by `mission_id` (ULID), not `mission_number`.

**Scale/Scope**:
- Single project at a time; per-project mission corpus expected up to ~200 missions for the lifetime of this tranche's design assumptions.
- Eight new event names; ~1 new top-level CLI command (`retrospect`) with two subcommands; ~1 new `agent` subcommand (`retrospect synthesize`); 1 new package; 1 new module under `doctrine/synthesizer/`.

---

## Charter Check

*Gate: must pass before Phase 0 research. Re-checked after Phase 1 design.*

Charter source: `.kittify/charter/charter.md`. Action doctrine for `plan` includes:

| Charter item | Conformance | Evidence |
|---|---|---|
| typer / rich / ruamel.yaml / pytest / mypy strict / 90%+ coverage | ✅ Pass | All listed deps already adopted; this plan adds no new toolchain. NFR-009/NFR-010 explicitly bind us to ≥90% coverage and `mypy --strict`. |
| DIRECTIVE_003 (Decision Documentation Requirement) | ✅ Pass | This plan documents Q1–Q4 architecture decisions inline with rationale; an ADR will be drafted under `architecture/2.x/adr/` for the gate-ownership decision (Q1-C). |
| DIRECTIVE_010 (Specification Fidelity Requirement) | ✅ Pass | All FR/NFR/C IDs from `spec.md` are mapped to concrete artifacts in §Phase 1 / §Module Plan below. Any deviation will be captured in `research.md` decision records. |
| Action tactic: premortem-risk-identification | Applied | §Risk Premortem section below enumerates failure modes and mitigations. |
| Action tactic: problem-decomposition | Applied | §Module Plan decomposes the tranche into seven independent sub-problems already aligned with the suggested WP shape in `start-here.md`. |
| Action tactic: ADR drafting workflow | Applied | One ADR planned for the gate-ownership decision (Q1-C), justifying the new shared module instead of reusing existing seams. |

Re-check after Phase 1: ✅ no new violations introduced. No Complexity Tracking entries required.

---

## Architecture Decisions (locked from planning interrogation)

These decisions answer the four planning questions and govern Phase 0/Phase 1.

### AD-001 — Lifecycle gate is a single shared module (Q1-C)

The retrospective gate logic lives in **`src/specify_cli/retrospective/gate.py`**. It exposes a small typed API (e.g., `is_completion_allowed(mission_id, mode, …)` returning a structured `GateDecision`). The two callers stay thin:

- `src/specify_cli/next/` calls `gate.is_completion_allowed(...)` immediately before signaling mission completion.
- Any status transition surface that ever needs to refuse mission-level completion calls the same function.

Mission-level policy does not live inside WP-level status code (`specify_cli.status.transitions`). That module already encodes per-WP transition guards; mission-level mode policy would be the wrong layering.

**Why not (A)**: WP-level transition guards aren't the right place for mission-mode policy.
**Why not (B)**: Burying the gate in `next` would require status-transition callers to reach into runtime internals.
**Why (C)**: Keeps the gate as one source of truth without lying to either existing seam. ADR will be drafted.

### AD-002 — Retrospective package layout (Q2-C)

```
src/specify_cli/retrospective/
├── __init__.py            # Public API surface
├── schema.py              # Pydantic models for retrospective.yaml + findings + proposals
├── writer.py              # Atomic round-trip-safe YAML writer (NFR-002)
├── reader.py              # Schema-validating reader; structured-error on malformed
├── mode.py                # Mode detection: charter > flag > env > parent process (FR-016)
├── events.py              # Eight event Pydantic models, factory, names; LOCAL until upstream lands (Q4-C)
├── gate.py                # Lifecycle gate (AD-001)
├── lifecycle.py           # Terminus-hook integration point invoked by `next`
├── summary.py             # Cross-mission summary reducer + report renderer
└── cli.py                 # `spec-kitty retrospect summary` typer surface
```

Doctrine/DRG/glossary mutation stays in:

```
src/specify_cli/doctrine/
└── synthesizer/
    ├── __init__.py
    ├── apply.py            # Applies accepted proposals (auto + staged-then-approved)
    ├── conflict.py         # Conflict detection between staged proposals (FR-023)
    └── provenance.py       # Provenance metadata writer (FR-022)
```

The retrospective package depends on `doctrine.synthesizer` only at the point of `retrospect synthesize`. The schema/writer/gate/summary do not depend on doctrine internals.

### AD-003 — CLI surfaces (Q3-C)

- **Operator-facing read** (top-level): `spec-kitty retrospect summary [--project <path>] [--json] [--limit N]`.
  Backed by `specify_cli.retrospective.cli`. Emits both human-readable Rich output and a structured JSON artifact (FR-025).
- **Agent-facing mutation** (under `agent`): `spec-kitty agent retrospect synthesize --mission <handle> [--apply | --dry-run]`.
  Backed by a new module under `src/specify_cli/cli/commands/agent_retrospect.py` that wires through `doctrine.synthesizer.apply`. The default is `--dry-run`; `--apply` is opt-in to make staged-application explicit (FR-021).

The `retrospect` action / `retrospective-facilitator` profile (FR-001, FR-002) are DRG artifacts, not CLI commands; they are surfaced via the existing profile/action lookup and consumed through `spec-kitty next`. Operators who want to *invoke* the retrospective explicitly can run `spec-kitty next --agent <name> --mission <handle>` and the runtime drives the action through the same DRG context as any other action.

### AD-004 — Event-package boundary (Q4-C)

The eight retrospective events (FR-017) are first defined locally in `specify_cli.retrospective.events` so this tranche stays self-contained. In parallel, an upstream PR is opened against `spec_kitty_events` to add the same eight events with the same names and payload shapes. Once the upstream release lands:

1. `specify_cli.retrospective.events` switches its imports to `from spec_kitty_events import retrospective as ev`.
2. The local Pydantic models are deleted.
3. `pyproject.toml` bumps the `spec_kitty_events` version pin.

A boundary test (under `tests/architectural/test_shared_package_boundary.py`) is added that asserts: once the upstream release is consumed, no Pydantic model for retrospective events lives outside `spec_kitty_events.*`. Until then, the test is skipped with a clear "pending upstream release" reason and a TODO comment naming the upstream issue.

This tranche's acceptance does **not** require the upstream release to land. It requires the local-then-upstream migration path to be documented in `research.md` and held to in code.

---

## Project Structure

### Documentation (this feature)

```
kitty-specs/mission-retrospective-learning-loop-01KQ6YEG/
├── spec.md                  # /spec-kitty.specify output (already committed)
├── meta.json                # Mission identity (already committed)
├── plan.md                  # This file
├── research.md              # Phase 0 output (this command)
├── data-model.md            # Phase 1 output (this command)
├── quickstart.md            # Phase 1 output (this command)
├── contracts/               # Phase 1 output (this command)
│   ├── retrospective_yaml_v1.md   # retrospective.yaml schema contract
│   ├── retrospective_events_v1.md # Eight event names + payload contracts
│   ├── gate_api.md                # Lifecycle gate Python API contract
│   ├── synthesizer_hook.md        # doctrine.synthesizer hook contract
│   └── cli_surfaces.md            # CLI surfaces contract
├── checklists/
│   ├── requirements.md            # /specify self-validation (already committed)
│   └── release-gate.md            # /checklist release-gate (already committed)
├── tasks.md                 # Phase 2 output (/spec-kitty.tasks command — NOT created here)
└── tasks/                   # Phase 2 output (/spec-kitty.tasks command — NOT created here)
```

### Source code (repository root)

New code in this tranche, all under `spec-kitty/src/`:

```
src/specify_cli/
├── retrospective/                              # NEW package (AD-002)
│   ├── __init__.py
│   ├── schema.py
│   ├── writer.py
│   ├── reader.py
│   ├── mode.py
│   ├── events.py
│   ├── gate.py
│   ├── lifecycle.py
│   ├── summary.py
│   └── cli.py
├── doctrine/                                   # Existing area; NEW synthesizer subpackage
│   └── synthesizer/                            # NEW subpackage (AD-002)
│       ├── __init__.py
│       ├── apply.py
│       ├── conflict.py
│       └── provenance.py
├── cli/commands/
│   └── agent_retrospect.py                     # NEW: `spec-kitty agent retrospect synthesize`
├── next/
│   └── _internal_runtime/
│       └── retrospective_hook.py               # NEW thin caller into retrospective.lifecycle/gate
└── status/
    └── (no changes; gate is consulted via specify_cli.retrospective.gate)
```

```
src/doctrine/
└── graph.yaml                                  # Existing; calibration tranche edits edges here

.kittify/
└── missions/<mission_id>/
    └── retrospective.yaml                      # NEW canonical durable retrospective record
```

```
tests/
├── retrospective/
│   ├── test_schema_roundtrip.py
│   ├── test_writer_atomicity.py
│   ├── test_mode_detection.py
│   ├── test_gate_decision.py
│   ├── test_summary_tolerance.py
│   ├── test_events_shapes.py
│   └── test_cli_surfaces.py
├── doctrine/synthesizer/
│   ├── test_apply.py
│   ├── test_conflict_failclosed.py
│   └── test_provenance.py
├── integration/retrospective/
│   ├── test_autonomous_terminus_e2e.py         # FR-033 acceptance
│   ├── test_hic_terminus_e2e.py                # FR-033 acceptance
│   └── test_silent_skip_blocked.py             # Negative case (FR-012)
└── architectural/
    └── test_no_prompt_filtering_added.py       # C-011 enforcement
```

```
architecture/2.x/adr/
└── 2026-04-27-1-retrospective-gate-shared-module.md  # AD-001 ADR

docs/
├── retrospective-learning-loop.md              # Operator overview
└── migration/
    └── retrospective-events-upstream.md        # AD-004 cutover runbook
```

**Structure decision**: single-project Python CLI; the retrospective package owns the governance contract and the synthesizer subpackage owns doctrine/DRG/glossary mutation. No worktrees during planning; planning artifacts are committed on `main`.

---

## Module Plan (decomposition for /spec-kitty.tasks)

This decomposition is non-binding for plan but maps cleanly to the suggested WP shape in `start-here.md` and to the spec's FR/NFR/C IDs. Tasks will refine boundaries.

| Sub-problem | Spec coverage | Surfaces touched |
|---|---|---|
| 1. Profile + action + DRG contract | FR-001, FR-002, FR-003, FR-004 | `src/doctrine/graph.yaml`, profile/action artifacts |
| 2. Schema + writer + reader + events | FR-005, FR-006, FR-007, FR-008, FR-009, FR-017, FR-018, NFR-001, NFR-002, NFR-005 | `retrospective/{schema,writer,reader,events}.py` |
| 3. Mode detection + lifecycle gate | FR-011, FR-012, FR-013, FR-014, FR-015, FR-016, NFR-007, NFR-008, C-013 | `retrospective/{mode,gate,lifecycle}.py`, thin caller in `next/_internal_runtime/retrospective_hook.py` |
| 4. Synthesizer hook + provenance | FR-019, FR-020, FR-021, FR-022, FR-023, FR-024, NFR-006, C-012 | `doctrine/synthesizer/{apply,conflict,provenance}.py`, `cli/commands/agent_retrospect.py` |
| 5. Cross-mission summary | FR-025, FR-026, FR-027, NFR-003, NFR-004 | `retrospective/{summary,cli}.py` |
| 6. Action-surface calibration reports + DRG edge changes | FR-030, FR-031, FR-032, C-011 | `src/doctrine/graph.yaml`, calibration report markdown under `architecture/calibration/` (one per mission) |
| 7. Real-runtime integration gate + dogfood across built-in and ERP custom missions | FR-028, FR-029, FR-033, NFR-009, NFR-010, C-001 through C-010 | `tests/integration/retrospective/*`, `tests/architectural/*`, fixture missions |

---

## Risk Premortem (charter tactic: premortem-risk-identification)

Failure modes considered and mitigation chosen now (vs. deferred to plan-time addenda):

| Risk | Severity | Mitigation in plan |
|---|---|---|
| Drift between event names and payloads | High | Contracts file `contracts/retrospective_events_v1.md` pins names and payload field minimums *before* implementation; schema tests validate. |
| Synthesizer staleness (staged proposal applied against moved doctrine) | Medium | Synthesizer reads target doctrine state at apply time and re-runs conflict detection (FR-023); a staleness check refuses apply if the cited evidence event ids are no longer reachable. |
| Calibration churn (fixing §4.5.1 for one step regresses another) | Medium | Each calibration report includes per-step before/after evidence; calibration tests are per-mission, not aggregate. |
| Mode misattribution (CI looks autonomous when operator intended HiC) | Medium | Source signal is recorded in the retrospective record and in mission events (FR-016, FR-018); operator can audit via `spec-kitty retrospect summary --json`. |
| Privacy of evidence references | Medium | Evidence event ids treated as opaque references; schema disallows embedding event payload content; documented in `contracts/retrospective_yaml_v1.md`. |
| Upstream `spec_kitty_events` release slips | Low | Local module compiles cleanly; cutover is mechanical; cutover runbook lives in `docs/migration/retrospective-events-upstream.md`. Acceptance does not block on upstream. |
| Staged-proposal queue grows unbounded | Low | Retrospective record stores proposals in-line with status; there is no separate queue store. Cross-mission summary surfaces stale proposals so they are visible. |

These risks are also reflected in `research.md` as decision records.

---

## Phase 0: Research

See [./research.md](./research.md). Phase 0 closes every research task created from spec ambiguities and from the architecture decisions above. After research closes, no `[NEEDS CLARIFICATION]` markers remain in `plan.md` or any Phase 1 artifact.

Research tasks executed:

- R-001 Mode-detection precedence: charter > flag > env > parent — formal lookup order, observable signals, and audit trail format.
- R-002 Canonical retrospective path resolution rules under the post-083 mission identity model (`mission_id`-keyed).
- R-003 Atomic-write strategy on POSIX filesystems for `retrospective.yaml`; tempfile + `os.replace` semantics; behavior on partial writes.
- R-004 Append-only event log integration: how retrospective events join `status.events.jsonl` without breaking the existing reducer.
- R-005 Action-surface inequality (architecture §4.5.1) — concrete predicate suitable for calibration tests.
- R-006 Conflict predicates between paired proposal kinds (e.g., `add_edge(E)` vs. `remove_edge(E)`, `update_glossary_term(T)` vs. `add_glossary_term(T)`).
- R-007 Upstream `spec_kitty_events` boundary test pattern (skipped-until-released).
- R-008 Cross-mission summary reduction strategy: streaming, tolerance to malformed records (NFR-004), 200-mission corpus performance target.

---

## Phase 1: Design & Contracts

Phase 1 outputs derive entirely from confirmed spec + research. Files produced:

- [./data-model.md](./data-model.md) — entities, fields, validation rules, state transitions for retrospective record, finding, proposal, mode, gate decision.
- [./contracts/retrospective_yaml_v1.md](./contracts/retrospective_yaml_v1.md) — `retrospective.yaml` schema contract (required vs. optional fields, required provenance, status enum, proposal types).
- [./contracts/retrospective_events_v1.md](./contracts/retrospective_events_v1.md) — eight event names and payload contracts (FR-017).
- [./contracts/gate_api.md](./contracts/gate_api.md) — lifecycle gate Python API contract (AD-001).
- [./contracts/synthesizer_hook.md](./contracts/synthesizer_hook.md) — doctrine.synthesizer hook contract; provenance fields; conflict failclosed shape.
- [./contracts/cli_surfaces.md](./contracts/cli_surfaces.md) — `spec-kitty retrospect summary` and `spec-kitty agent retrospect synthesize` contracts (input flags, exit codes, output shape).
- [./quickstart.md](./quickstart.md) — operator quickstart: how a HiC run looks, how an autonomous run looks, how to skip with audit trail, how to read summary, how to apply staged proposals.

Charter re-check after Phase 1: ✅ no new violations.

---

## Bulk-Edit Detection

Not applicable. This tranche **adds** new identifiers, files, and DRG edges; it does not rename an existing string across many files. `meta.json` does not get `change_mode: bulk_edit`. No `occurrence_map.yaml` is required.

If calibration (sub-problem 6) ends up renaming an existing DRG edge identifier, that single rename is local to `src/doctrine/graph.yaml` and would not constitute a bulk edit.

---

## Acceptance Mapping

Every spec acceptance gate maps to a concrete artifact below. (Plan-time map; tasks will refine.)

| Acceptance Gate (spec) | Plan artifact / module |
|---|---|
| 1. profile + action exist in DRG | `src/doctrine/graph.yaml` (sub-problem 1) |
| 2. schema validates and round-trips | `retrospective/schema.py` + `retrospective/writer.py` + tests |
| 3. canonical durable path | `retrospective/writer.py` writes to `.kittify/missions/<mission_id>/retrospective.yaml` |
| 4. autonomous blocks until completed | `retrospective/gate.py` + `next/_internal_runtime/retrospective_hook.py` |
| 5. HiC offers + permits explicit skip | `retrospective/lifecycle.py` + gate |
| 6. silent auto-run impossible (HiC) | gate refuses non-explicit invocations in HiC; integration test |
| 7. silent skip impossible (autonomous) | gate; integration test |
| 8. synthesized changes from finding set | `doctrine/synthesizer/apply.py` + `cli/commands/agent_retrospect.py` |
| 9. provenance references source | `doctrine/synthesizer/provenance.py` |
| 10. later mission sees updated context | covered by integration test that runs a follow-up mission against post-synthesis project state |
| 11. summary handles rich/brief/skipped/missing/malformed | `retrospective/summary.py` + tolerance tests |
| 12. calibration reports for 4 missions | `architecture/calibration/<mission>.md` × 4 |
| 13. calibration changes are DRG-only | architectural test enforces no new prompt-filter call sites (C-011) |
| 14. existing built-in mission tests pass | regression-only; no removal of existing tests |
| 15. existing custom-mission loader tests pass | regression-only; no change to loader contract; FR-029 keeps marker requirement |
| 16. real-runtime integration tests drive lifecycle | `tests/integration/retrospective/*` |

---

## Complexity Tracking

No charter-violation justifications required. This tranche reuses the project's existing dependency set, adds one new package and one new subpackage, and introduces no new third-party tools.

---

## Open Items Carried Into /spec-kitty.tasks

These are intentional plan-time hand-offs (not unresolved clarifications):

- Per-proposal-type payload field minimums beyond the contract baseline. The contract pins required *envelope* fields per proposal kind; sub-fields like "what does `synthesize_directive`'s body shape look like" can be refined when the first WP implements it. Captured in `research.md` R-006 with the rule: payload schema must be explicit before the WP merging it lands.
- Calibration report template format (markdown column shape). One representative template will be drafted in the calibration WP and cloned across the four in-scope missions.

---

## Branch Contract Restated (final)

- Current branch at plan completion: `main`.
- Planning/base branch for this feature: `main`.
- Final merge target: `main`.
- `branch_matches_target`: ✅ true.

Plan complete after Phase 1 outputs land. **Do not run `/spec-kitty.tasks` automatically.** The user invokes it explicitly when ready to break this plan into work packages.
