# Tasks: Opt-in SPDD and REASONS Canvas Doctrine Pack

**Mission**: `spdd-reasons-doctrine-pack-01KQC4AX` (mission_id `01KQC4AX9R4BJ40WWND37CCCJT`)
**Branch**: `doctrine/spdd-reasons-pack`
**Spec**: [spec.md](./spec.md)
**Plan**: [plan.md](./plan.md)
**Generated**: 2026-04-29

## Overview

Six work packages deliver an opt-in SPDD/REASONS Canvas doctrine pack: shipped artifacts (WP01), charter activation wiring (WP02), the agent skill (WP03), conditional prompt fragment rendering (WP04), the opt-in review gate (WP05), and documentation (WP06).

**Dependency order**: WP01 → (WP02 ∥ WP03) → WP04 → WP05 → WP06.

WP02 and WP03 can run in parallel after WP01 lands. WP04 depends on the activation helper from WP02 and the artifacts from WP01. WP05 depends on the prompt-fragment seam from WP04. WP06 depends on the rest because the docs reference real artifacts and behavior.

## Subtask Index

| ID    | Description                                                            | WP   | Parallel |
|-------|------------------------------------------------------------------------|------|----------|
| T001  | Author `structured-prompt-driven-development.paradigm.yaml`            | WP01 | [P]      | [D] |
| T002  | Author `reasons-canvas-fill.tactic.yaml`                               | WP01 | [D] |
| T003  | Author `reasons-canvas-review.tactic.yaml`                             | WP01 | [D] |
| T004  | Author `reasons-canvas-writing.styleguide.yaml`                        | WP01 | [D] |
| T005  | Author `038-structured-prompt-boundary.directive.yaml`                 | WP01 | [D] |
| T006  | Author `templates/fragments/reasons-canvas-template.md`                | WP01 | [D] |
| T007  | Add `tests/doctrine/test_spdd_reasons_artifacts.py`                    | WP01 |          | [D] |
| T008  | Implement `is_spdd_reasons_active()` helper                            | WP02 |          | [D] |
| T009  | Extend `build_charter_context` to inject SPDD/REASONS guidance         | WP02 |          | [D] |
| T010  | Verify `bundle.py`/`targets.py` paradigm flow; patch if needed         | WP02 |          | [D] |
| T011  | Add `tests/charter/test_charter_context_spdd_reasons.py`               | WP02 |          | [D] |
| T012  | Author `src/doctrine/skills/spec-kitty-spdd-reasons/SKILL.md`          | WP03 |          | [D] |
| T013  | Wire skill discovery test (smoke assertion the skill loads)            | WP03 |          | [D] |
| T014  | Add SPDD reasons-block markers to `specify.md` template                | WP04 | [D] |
| T015  | Add SPDD reasons-block markers to `plan.md` template                   | WP04 | [D] |
| T016  | Add SPDD reasons-block markers to `tasks.md` template                  | WP04 | [D] |
| T017  | Add SPDD reasons-block markers to `implement.md` template              | WP04 | [D] |
| T018  | Implement renderer hook that strips/keeps blocks based on activation   | WP04 |          | [D] |
| T019  | Add `tests/prompts/test_prompt_fragment_rendering.py` (golden)         | WP04 |          | [D] |
| T020  | Add SPDD reasons-block to `review.md` template (drift gate content)    | WP05 |          |
| T021  | Add `tests/reviews/test_review_gate_activation.py`                     | WP05 |          |
| T022  | Author `docs/doctrine/spdd-reasons.md` (philosophy + activation + examples) | WP06 |          |
| T023  | Add inbound links from existing doctrine/charter/mission docs          | WP06 |          |

23 subtasks across 6 WPs. Distribution: WP01=7, WP02=4, WP03=2, WP04=6, WP05=2, WP06=2. Average WP size 3.8 subtasks (within ideal 3–7 range).

---

## WP01 — Add Shipped Doctrine Artifacts (#876)

**Priority**: foundational (blocks all other WPs)
**Parallel?**: No (WP01 must land first)
**Dependencies**: none
**Estimated prompt size**: ~360 lines
**Independent test**: `uv run pytest tests/doctrine -q` plus the new `test_spdd_reasons_artifacts.py` passes; existing schema/compliance tests pass with no modification.
**Issue**: closes #876

### Goal

Ship six new doctrine library artifacts that validate against existing schemas and that are discoverable via `DoctrineService` without service-level changes.

### Included subtasks

- [x] T001 Author `src/doctrine/paradigms/shipped/structured-prompt-driven-development.paradigm.yaml`
- [x] T002 Author `src/doctrine/tactics/shipped/reasons-canvas-fill.tactic.yaml`
- [x] T003 Author `src/doctrine/tactics/shipped/reasons-canvas-review.tactic.yaml`
- [x] T004 Author `src/doctrine/styleguides/shipped/reasons-canvas-writing.styleguide.yaml`
- [x] T005 Author `src/doctrine/directives/shipped/038-structured-prompt-boundary.directive.yaml`
- [x] T006 Author `src/doctrine/templates/fragments/reasons-canvas-template.md`
- [x] T007 Add `tests/doctrine/test_spdd_reasons_artifacts.py` validating all six artifacts load via repositories and conform to schemas.

### Implementation sketch

1. Create the six new files using shapes spelled out in `data-model.md`.
2. Run existing schema/compliance tests; iterate until green.
3. Add a small new test that imports the artifacts via `DoctrineService` and asserts they appear in the relevant repositories without any project-side selection (i.e., they are discoverable but not active).
4. Confirm `DIRECTIVE_038` enforcement is `lenient-adherence` with the four explicit allowances enumerated.

### Risks

- Schema field names may differ slightly from `data-model.md` examples. Run `pytest tests/doctrine` after each file.
- `DIRECTIVE_038` ID format must match the regex `^[A-Z][A-Z0-9_-]*$` — file name and `id` field must agree.

---

## WP02 — Charter Selection & Context Injection (#879)

**Priority**: critical-path foundation for activation
**Parallel?**: yes, with WP03 after WP01 lands
**Dependencies**: WP01
**Estimated prompt size**: ~430 lines
**Independent test**: `tests/charter/test_charter_context_spdd_reasons.py` passes for both active and inactive fixtures; `charter context --action <action> --json` performance ≤2s.
**Issue**: closes #879

### Goal

Wire the new artifacts through the charter interview/library flow so charter selection drives activation. Implement `is_spdd_reasons_active()` and inject SPDD/REASONS guidance into `build_charter_context()` only when the active selection includes the pack.

### Included subtasks

- [x] T008 Implement `is_spdd_reasons_active(repo_root) -> bool` per `contracts/activation.md`. Place in `src/doctrine/spdd_reasons/__init__.py` with helper module `activation.py`.
- [x] T009 Extend `src/charter/context.py` to call a new `_append_spdd_reasons_guidance()` helper after `_append_action_doctrine_lines()` only when active. Action-scoped content per `contracts/charter-context.md`.
- [x] T010 Verify `src/charter/bundle.py` and `src/charter/synthesizer/targets.py` write paradigms when selected. Patch minimally if not. No schema changes.
- [x] T011 Add `tests/charter/test_charter_context_spdd_reasons.py` covering: (a) inactive fixture byte-identical to baseline; (b) active fixture contains scoped guidance for each of specify/plan/tasks/implement/review; (c) only-paradigm/only-tactic/only-directive activation each enable injection; (d) malformed governance.yaml propagates loader error.

### Implementation sketch

1. Build the activation helper first; unit-test it in isolation.
2. Capture baseline of `charter context --json` output for an inactive fixture.
3. Add `_append_spdd_reasons_guidance(lines, mission, action)` that emits an "SPDD/REASONS Guidance (action: …)" subsection with bullets keyed by action.
4. Hook the helper into `_render_action_scoped()` after `_append_action_doctrine_lines()` (line 537 region).
5. Ensure inactive output is byte-identical to the baseline.
6. Add tests; run full `pytest tests/charter` and `pytest tests/doctrine`.

### Risks

- Charter loader may treat paradigms differently from directives/tactics. Validate `bundle.py` paradigm support; expose a clean integration point if needed.
- Snapshot tests are sensitive to whitespace and trailing newlines. Use `repr()` comparisons in failures to surface diffs.

### Dependencies
- Depends on **WP01** (artifacts must exist for charter to select them).

---

## WP03 — `spec-kitty-spdd-reasons` Skill (#878)

**Priority**: agent-facing entry point
**Parallel?**: yes, with WP02 after WP01 lands
**Dependencies**: WP01
**Estimated prompt size**: ~250 lines
**Independent test**: skill file is discoverable by skill loader; manual smoke confirms triggers and instructions render.
**Issue**: closes #878

### Goal

Author the agent-facing skill that drives canvas authoring and review per spec FR-010, FR-011, FR-012.

### Included subtasks

- [x] T012 Author `src/doctrine/skills/spec-kitty-spdd-reasons/SKILL.md` matching the shape of `spec-kitty-charter-doctrine/SKILL.md` (frontmatter + body). Triggers, instructions, and warnings per `data-model.md`.
- [x] T013 Add or extend an existing skill discovery test in `tests/doctrine/` to include `spec-kitty-spdd-reasons` among loaded skills.

### Implementation sketch

1. Read `src/doctrine/skills/spec-kitty-charter-doctrine/SKILL.md` to align frontmatter shape exactly.
2. Write SKILL.md per `data-model.md`. Include a "What this skill does NOT do" section and an explicit escalation rule.
3. Confirm the skill is discovered by existing skill loader machinery (a single assertion in an existing test, or a tiny new test, suffices).

### Risks

- Skill triggers must not collide with existing skills. Verified during planning; re-confirm via `grep -r 'use SPDD\|use REASONS' src/doctrine/skills/`.

### Dependencies
- Depends on **WP01** (the skill references the new tactics/paradigm/directive).

---

## WP04 — Conditional Prompt Fragment Rendering (#875)

**Priority**: lifecycle activation across actions
**Parallel?**: no
**Dependencies**: WP01, WP02
**Estimated prompt size**: ~480 lines
**Independent test**: `tests/prompts/test_prompt_fragment_rendering.py` golden snapshot passes byte-or-semantic identical for an inactive fixture across all five command templates; active fixture contains the action-scoped REASONS block.
**Issue**: closes #875

### Goal

Inject conditional REASONS guidance into the four mission-action command templates (`specify`, `plan`, `tasks`, `implement`) using the marker convention from `contracts/prompt-fragment.md`. Implement the renderer hook that excises blocks when inactive, producing byte-identical inactive output.

### Included subtasks

- [x] T014 Add `<!-- spdd:reasons-block:start -->` … `<!-- spdd:reasons-block:end -->` block to `src/specify_cli/missions/software-dev/command-templates/specify.md` covering Requirements + Entities guidance.
- [x] T015 Add the equivalent block to `plan.md` covering Approach + Structure guidance.
- [x] T016 Add the equivalent block to `tasks.md` covering Operations + WP-boundary guidance.
- [x] T017 Add the equivalent block to `implement.md` covering full WP-scoped canvas (R/E/A/S/O/N/S).
- [x] T018 Implement renderer hook that, at template materialization time, calls `is_spdd_reasons_active(repo_root)` and either keeps the block (stripping marker comment lines only) or removes the block and its delimiters in their entirety. Locate the hook at the existing template-materialization seam used during agent prompt deployment.
- [x] T019 Add `tests/prompts/test_prompt_fragment_rendering.py` with: (a) baseline snapshot of inactive output for each of the four templates; (b) active output containing the expected REASONS block headlines; (c) malformed marker (missing end) raises a clear renderer error.

### Implementation sketch

1. Identify the template-materialization function that copies command templates to `.claude/commands/spec-kitty.*.md` (and peers). Add a single post-process step that processes `spdd:reasons-block` markers.
2. Define the block content (action-scoped) using `contracts/prompt-fragment.md`.
3. Capture baseline (inactive) snapshots of all four template outputs.
4. Insert blocks into the four source templates.
5. Implement the renderer hook; verify inactive output byte-or-semantic identical to baseline.
6. Add tests.

### Risks

- Multiple agents (`.claude/`, `.amazonq/`, `.kiro/`, etc.) consume materialized templates. The hook must run for all of them. Confirm via `migrations/m_0_9_1_complete_lane_migration.py:get_agent_dirs_for_project()` integration.
- Whitespace handling: removing the block should not leave an extra blank line. Strip the trailing newline of the closing marker.

### Dependencies
- Depends on **WP01** (artifacts referenced in block content) and **WP02** (`is_spdd_reasons_active`).

---

## WP05 — Opt-in Review Gate & Drift Handling (#877)

**Priority**: review-time enforcement
**Parallel?**: no
**Dependencies**: WP04
**Estimated prompt size**: ~310 lines
**Independent test**: `tests/reviews/test_review_gate_activation.py` covers the seven cases in `contracts/review-gate.md`.
**Issue**: closes #877

### Goal

Add the conditional REASONS Canvas Comparison subsection to `review.md` (using the same marker convention from WP04) so that, when the pack is active, reviewers receive instructions to (a) load `kitty-specs/<mission>/reasons-canvas.md`, (b) trace the diff against Requirements/Operations/Norms/Safeguards, and (c) classify divergences. Charter directives take precedence over canvas content.

### Included subtasks

- [ ] T020 Add `<!-- spdd:reasons-block:start --> … <!-- spdd:reasons-block:end -->` to `src/specify_cli/missions/software-dev/command-templates/review.md` containing the REASONS Canvas Comparison subsection (load canvas → trace → classify drift). Use seam after `### 2a. Load Agent Profile`.
- [ ] T021 Add `tests/reviews/test_review_gate_activation.py` with the seven cases from `contracts/review-gate.md`.

### Implementation sketch

1. Mirror the marker block convention from WP04 inside `review.md`.
2. Encode the drift-classification taxonomy (approved / approved_with_deviation / canvas_update_needed / glossary_update_needed / charter_follow_up / follow_up_mission / scope_drift_block / safeguard_violation_block).
3. Confirm reviewer behavior is unchanged when the pack is inactive (covered by WP04 baseline; add one explicit check here).
4. Tests cover the gate decision points.

### Risks

- The reviewer prompt is human-read by an agent. Keep instructions concise (≤80 lines of new content) so the prompt remains within model-friendly bounds.

### Dependencies
- Depends on **WP04** (renderer hook + marker convention must already exist).

---

## WP06 — Documentation (#874)

**Priority**: must-ship for the user-facing rollout
**Parallel?**: no
**Dependencies**: WP01, WP02, WP03, WP04, WP05
**Estimated prompt size**: ~280 lines
**Independent test**: docs build cleanly (no broken inbound links); reviewer manually confirms required sections.
**Issue**: closes #874

### Goal

Author `docs/doctrine/spdd-reasons.md` and link it from existing doctrine, charter, and mission workflow docs. Cover philosophy, activation, mission-and-WP canvas generation/review, contrast with "prompts/specs as source of truth", non-uses, and two examples (lightweight + high-risk).

### Included subtasks

- [ ] T022 Author `docs/doctrine/spdd-reasons.md` with all required sections (per spec FR-019).
- [ ] T023 Add inbound links from one or more of: `docs/doctrine/README.md`, `docs/charter.md` (or equivalent), and the mission workflow docs.

### Implementation sketch

1. Use `quickstart.md` from this mission as the seed; expand into a full doctrine doc.
2. Include a short "When NOT to use" section.
3. Link from existing doctrine index and charter index docs (`grep -l doctrine docs/` to find candidates).

### Risks

- Doc paths may shift with the doctrine doc tree. Confirm canonical doctrine doc index file(s) before adding inbound links.

### Dependencies
- Depends on **WP01..WP05** (docs reference real artifacts and behavior).

---

## Verification

```bash
cd /Users/robert/spec-kitty-dev/spec-kitty-20260429-095938/spec-kitty
uv run pytest tests/doctrine -q
uv run pytest tests/charter -q
uv run pytest tests/prompts -q
uv run pytest tests/reviews -q
uv run pytest tests -q
uv run mypy --strict src/doctrine src/charter
```

## MVP Scope Recommendation

**MVP = WP01 + WP02 + WP03**: artifacts + charter wiring + skill. This delivers full activation through charter and ad-hoc canvas authoring via the skill, without prompt-template or review-gate changes. WP04/WP05 then enable lifecycle-wide guidance and review-gate enforcement. WP06 ships docs.

## Next Step

Run `/spec-kitty.implement` (or the implement-review orchestrator) starting at WP01.
