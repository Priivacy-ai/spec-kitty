# Implementation Plan: Opt-in SPDD and REASONS Canvas Doctrine Pack

**Branch**: `doctrine/spdd-reasons-pack` | **Date**: 2026-04-29 | **Spec**: [spec.md](./spec.md)
**Mission**: `spdd-reasons-doctrine-pack-01KQC4AX` (mission_id `01KQC4AX9R4BJ40WWND37CCCJT`)
**Input**: Feature specification from `kitty-specs/spdd-reasons-doctrine-pack-01KQC4AX/spec.md`

## Summary

Ship six work packages that add an **opt-in** Structured-Prompt-Driven-Development (SPDD) and REASONS Canvas doctrine pack. Activation is fully gated through charter selection. Inactive projects must observe **zero** behavior change in prompts, charter context output, and review behavior.

The implementation reuses Spec Kitty's existing doctrine artifact kinds (paradigm, tactic, styleguide, directive, skill, template fragment) — no new artifact kind, no schema change. Conditional rendering is wired into the existing `build_charter_context()` action-doctrine pipeline at `src/charter/context.py` and into mission/WP prompt templates via the existing context-injection seam.

## Technical Context

**Language/Version**: Python 3.11+ (existing Spec Kitty codebase).
**Primary Dependencies**: `typer`, `rich`, `ruamel.yaml`, `pytest`, `mypy --strict`. No new runtime dependencies.
**Storage**: Filesystem only — YAML doctrine artifacts under `src/doctrine/`, project-side selections in `.kittify/charter/` (governance.yaml, directives.yaml, metadata.yaml, synthesis-manifest.yaml), runtime canvas at `kitty-specs/<mission>/reasons-canvas.md`.
**Testing**: `pytest` with ≥90% coverage on new modules. Existing `tests/doctrine/` schema/compliance suite must pass with new artifacts. New tests for charter context, prompt rendering, and review-gate activation.
**Target Platform**: Cross-platform CLI (Linux, macOS, Windows 10+).
**Project Type**: Single project (Spec Kitty CLI).
**Performance Goals**: `spec-kitty charter context --action <action>` ≤2s for typical projects (NFR-002).
**Constraints**: No schema changes to `src/doctrine/schemas/*.schema.yaml`. No global template edits that always render REASONS. No new artifact kind.
**Scale/Scope**: 6 shipped artifacts + 1 skill + 1 template fragment + charter wiring + prompt-fragment rendering + review-gate logic + docs.

## Charter Check

The Spec Kitty charter at `.kittify/charter/charter.md` is in scope. Relevant items:

- **Testing**: ≥90% coverage and `mypy --strict` clean — covered by NFR-005 and NFR-006.
- **Performance**: CLI ops <2s — covered by NFR-002.
- **DIRECTIVE_010 (Specification Fidelity)**: All shipped artifacts trace to FR-### IDs in this spec; review-gate behavior in WP5 explicitly enforces canvas-fidelity for active projects only.
- **DIRECTIVE_003 (Decision Documentation)**: ADR for "shipped doctrine pack vs new artifact kind" recorded in research.md (Phase 0).

**Gate status: PASS.** No violations. No complexity-tracking entries needed.

## Architectural Map (verified via repo inspection)

These are the integration seams the WPs will touch. Full citations live in research.md.

| Concern | Source location | Integration approach |
|---|---|---|
| Paradigm schema | `src/doctrine/schemas/paradigm.schema.yaml` (req: `schema_version`, `id`, `name`, `summary`) | Add `structured-prompt-driven-development.paradigm.yaml` under `src/doctrine/paradigms/shipped/` |
| Tactic schema | `src/doctrine/schemas/tactic.schema.yaml` (req: `id`, `schema_version`, `name`, `steps[]`) | Add `reasons-canvas-fill.tactic.yaml`, `reasons-canvas-review.tactic.yaml` under `src/doctrine/tactics/shipped/` |
| Styleguide schema | `src/doctrine/schemas/styleguide.schema.yaml` (req: `id`, `schema_version`, `title`, `scope`, `principles[]`) | Add `reasons-canvas-writing.styleguide.yaml` (scope: `docs`) under `src/doctrine/styleguides/shipped/` |
| Directive schema | `src/doctrine/schemas/directive.schema.yaml` (req: `id` UPPERCASE, `schema_version`, `title`, `intent`, `enforcement`) | Add `038-structured-prompt-boundary.directive.yaml` (id `DIRECTIVE_038`, enforcement `lenient-adherence` with explicit allowances) under `src/doctrine/directives/shipped/` |
| Template fragment | `src/doctrine/templates/` (existing subdirs: `diagrams/`, `triage/`, `architecture/`, `guides/`, `sets/`, `structure/`) | Add `src/doctrine/templates/fragments/reasons-canvas-template.md` (new `fragments/` subdir) |
| Action doctrine resolution | `src/doctrine/missions/software-dev/actions/<action>/index.yaml` (lists directives/tactics/styleguides/toolguides) | Do **not** modify shipped action indices. Inject SPDD artifacts via project-side selection only — they appear in the active set when the project's charter selected them. |
| Charter context output | `src/charter/context.py:build_charter_context()` line 69; `_load_action_doctrine_bundle()` lines 213–249; `_render_action_scoped()` lines 507–555; `_append_action_doctrine_lines()` line 537 | Extend renderer so that when the active selection includes the new paradigm/tactics/directive, an "SPDD/REASONS Guidance (action: `<action>`)" block is appended. The block content is action-scoped (specify→Requirements/Entities; plan→Approach/Structure; tasks→Operations/WP boundaries; implement→full canvas; review→comparison surface). When inactive, output is byte-identical to today. |
| Charter library/governance | `src/charter/bundle.py` (writes governance.yaml, directives.yaml, metadata.yaml, synthesis-manifest.yaml); `src/charter/synthesizer/targets.py`; `src/charter/synthesizer/write_pipeline.py` | New artifacts flow through existing `SynthesisTarget` machinery (kinds: paradigm, tactic, styleguide, directive). Verify paradigm targets are supported; if not, add minimal target plumbing without breaking existing charter writes. |
| DoctrineService | `src/doctrine/service.py` lines 19–99 (`directives`, `tactics`, `styleguides`, `paradigms` repository properties) | New artifacts discovered automatically via existing repositories. No service changes required. |
| Skill loader | `src/doctrine/skills/<skill>/SKILL.md` (existing pattern: YAML frontmatter `name`/`description`/triggers + Markdown body) | Add `src/doctrine/skills/spec-kitty-spdd-reasons/SKILL.md` |
| Mission/WP prompt templates | `src/specify_cli/missions/software-dev/command-templates/{specify,plan,tasks,implement,review}.md` | Add a conditional REASONS section (rendered only if active doctrine includes SPDD pack) at well-defined seams. Keep current output byte-identical when inactive. The seam design is described in research.md. |
| Reviewer prompt | `src/specify_cli/missions/software-dev/command-templates/review.md` lines 1–60 (frontmatter + section headers + `### 2a. Load Agent Profile` seam) | Append a conditional "REASONS Canvas Comparison" subsection to the review action that activates only when the pack is active. Drift outcomes (approved deviation / scope drift / safeguard violation) are encoded as instructions to the reviewer agent. |
| Tests | `tests/doctrine/` (`test_artifact_compliance.py`, `test_directive_consistency.py`, `test_tactic_compliance.py`, `test_artifact_kinds.py`, `test_service.py`, `test_nested_artifact_discovery.py`) | New artifacts validated by existing tests. Add new tests for charter-context activation, prompt-fragment rendering, and review-gate behavior. |

## Project Structure

### Documentation (this mission)

```
kitty-specs/spdd-reasons-doctrine-pack-01KQC4AX/
├── spec.md                # /spec-kitty.specify output (done)
├── plan.md                # this file
├── research.md            # Phase 0 output
├── data-model.md          # Phase 1 output (artifact shapes)
├── quickstart.md          # Phase 1 output (activation walkthrough)
├── contracts/             # Phase 1 output (artifact-kind contracts)
├── checklists/
│   └── requirements.md    # spec quality checklist (done)
└── tasks/                 # /spec-kitty.tasks output (next phase)
```

### Source Code (touched paths)

```
src/
├── doctrine/
│   ├── paradigms/shipped/
│   │   └── structured-prompt-driven-development.paradigm.yaml          # WP1 (NEW)
│   ├── tactics/shipped/
│   │   ├── reasons-canvas-fill.tactic.yaml                             # WP1 (NEW)
│   │   └── reasons-canvas-review.tactic.yaml                           # WP1 (NEW)
│   ├── styleguides/shipped/
│   │   └── reasons-canvas-writing.styleguide.yaml                      # WP1 (NEW)
│   ├── directives/shipped/
│   │   └── 038-structured-prompt-boundary.directive.yaml               # WP1 (NEW)
│   ├── templates/fragments/
│   │   └── reasons-canvas-template.md                                  # WP1 (NEW)
│   └── skills/spec-kitty-spdd-reasons/
│       └── SKILL.md                                                    # WP3 (NEW)
├── charter/
│   ├── context.py                                                      # WP2 (extend renderer)
│   ├── bundle.py                                                       # WP2 (verify paradigm flow)
│   └── synthesizer/
│       └── targets.py                                                  # WP2 (verify paradigm targets)
└── specify_cli/missions/software-dev/command-templates/
    ├── specify.md                                                      # WP4 (conditional fragment)
    ├── plan.md                                                         # WP4 (conditional fragment)
    ├── tasks.md                                                        # WP4 (conditional fragment)
    ├── implement.md                                                    # WP4 (conditional fragment)
    └── review.md                                                       # WP5 (conditional review gate)

tests/
├── doctrine/
│   └── test_spdd_reasons_artifacts.py                                  # WP1 (NEW)
├── charter/
│   └── test_charter_context_spdd_reasons.py                            # WP2 (NEW: active vs inactive)
├── prompts/
│   └── test_prompt_fragment_rendering.py                               # WP4 (NEW: byte-identical inactive)
└── reviews/
    └── test_review_gate_activation.py                                  # WP5 (NEW: drift behavior)

docs/
└── doctrine/
    └── spdd-reasons.md                                                 # WP6 (NEW: user-facing doc)
```

**Structure Decision**: Standard single-project layout. New code lives in existing packages (`src/doctrine/`, `src/charter/`, `src/specify_cli/`) and existing test trees. The single new test directory if any (`tests/charter/`, `tests/prompts/`, `tests/reviews/`) follows existing convention; if those directories exist, tests go inside; if not, the simplest existing test file path is used (will be confirmed in WP-level docs).

## Phase 0: Research

See [research.md](./research.md) for:
- ADR: "Reuse existing artifact kinds vs introduce a new 'doctrine pack' kind" — decision: reuse, supported by FR-006/C-003.
- DIRECTIVE_038 enforcement choice (`lenient-adherence` with explicit allowances) — supports approved deviations without blocking inactive projects.
- Conditional prompt rendering mechanism — selected approach: action-doctrine activation check inside the prompt template (a Jinja-style `{% if %}` is not introduced; instead the prompt template references a runtime-rendered "active doctrine context" variable, and the renderer omits the section entirely when inactive).
- Action scoping: `specify`→Requirements/Entities; `plan`→Approach/Structure; `tasks`→Operations/WP boundaries; `implement`→full WP canvas; `review`→canvas comparison.

## Phase 1: Design Artifacts

See [data-model.md](./data-model.md), [contracts/](./contracts/), and [quickstart.md](./quickstart.md) for:
- Artifact shape contracts (paradigm, tactic, styleguide, directive, template fragment, skill).
- Active-doctrine detection contract (how charter context decides "is the pack active").
- Drift classification state machine (approved deviation / scope drift / safeguard violation / canvas update / glossary update / charter follow-up / follow-up mission).
- Quickstart: how a user activates the pack via charter and runs a full lifecycle.

## Work Package Plan (high-level — finalized in `/spec-kitty.tasks`)

| WP | Issue | Title | Scope summary |
|---|---|---|---|
| WP1 | #876 | Add Shipped Doctrine Artifacts | 6 YAML/MD files: paradigm, two tactics, styleguide, directive, template fragment. Validates against existing schemas. |
| WP2 | #879 | Charter Selection & Context Injection | Wire paradigm/tactics/directive through charter interview → governance.yaml → references.yaml → `charter context --action`. Active vs inactive snapshots. |
| WP3 | #878 | spec-kitty-spdd-reasons Skill | New SKILL.md with triggers and instructions. Detects activation, generates `kitty-specs/<mission>/reasons-canvas.md`, warns and escalates. |
| WP4 | #875 | Conditional Prompt Fragment Rendering | Inject conditional REASONS sections in specify/plan/tasks/implement prompt templates. Inactive output byte-identical. |
| WP5 | #877 | Opt-in Review Gate & Drift Handling | Conditional reviewer block; drift classification; only activates when pack selected. |
| WP6 | #874 | Documentation | `docs/doctrine/spdd-reasons.md` with philosophy, activation, examples (lightweight + high-risk), and inbound links. |

**Dependency order**: WP1 → (WP2, WP3 in parallel) → WP4 → WP5 → WP6. WP4 depends on WP2 because activation detection lives there; WP5 depends on WP4 because the review prompt seam mirrors implement-prompt seam.

## Verification Plan

```bash
cd /Users/robert/spec-kitty-dev/spec-kitty-20260429-095938/spec-kitty

# Per-WP and full-suite verification
uv run pytest tests/doctrine -q
uv run pytest tests/charter -q                  # WP2 active/inactive snapshots
uv run pytest tests/prompts -q                  # WP4 byte-identical guarantee
uv run pytest tests/reviews -q                  # WP5 gate behavior
uv run pytest tests -q                          # full suite
uv run mypy --strict src/doctrine src/charter   # type-check touched modules
```

If any subset is too slow, document which subsets ran in the WP completion notes.

## Branch Strategy (restated)

- **Current branch**: `doctrine/spdd-reasons-pack`
- **Planning/base branch**: `doctrine/spdd-reasons-pack`
- **Final merge target**: `doctrine/spdd-reasons-pack` (per `setup-plan` JSON; the PR will retarget `main` when opened)
- **`branch_matches_target`**: true at plan time

## Complexity Tracking

*Charter Check passed; no violations.*

## Next Step

Run `/spec-kitty.tasks` to break this plan into work packages with explicit acceptance criteria and execution lanes.
