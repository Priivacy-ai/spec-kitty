---
work_package_id: WP04
title: Retrospect tracer ingestion
dependencies: []
requirement_refs:
- FR-007
- FR-008
tracker_refs: []
planning_base_branch: mission/lifecycle-tooling-friction
merge_target_branch: mission/lifecycle-tooling-friction
branch_strategy: Planning artifacts for this mission were generated on mission/lifecycle-tooling-friction. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/lifecycle-tooling-friction unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T012
phase: Mission-Lifecycle Tooling Friction
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1801725"
history:
- at: '2026-06-27T00:00:00Z'
  actor: system
  action: Prompt created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/retrospective/
create_intent:
- tests/specify_cli/retrospective/__init__.py
- tests/specify_cli/retrospective/test_generator_traces_ingest.py
execution_mode: code_change
owned_files:
- src/specify_cli/retrospective/generator.py
- tests/specify_cli/retrospective/__init__.py
- tests/specify_cli/retrospective/test_generator_traces_ingest.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP04 – Retrospect tracer ingestion

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile named in the frontmatter and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## ⚠️ IMPORTANT: Review Feedback

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_ref` field in the event log (via `spec-kitty agent status` or the Activity Log below).
- **You must address all feedback** before your work is complete.
- **Report progress**: update the Activity Log as you address each item.

---

## Markdown Formatting

Wrap HTML/XML tags in backticks: `` `<div>` ``. Use language identifiers in code blocks: ` ```python `, ` ```bash `.

---

## Objectives & Success Criteria

- `retrospect create`/synthesize sources findings/proposals (helped / not_helpful / gaps / proposals) from `kitty-specs/<slug>/traces/*.md` via the **existing** ingestor seam — not a generator rewrite.
- A mission with `traces/tooling-friction.md` content yields ≥ 1 tracer-sourced finding.
- A no-domain-entity mission does NOT get a false "missing data-model.md" gap (the data-model gap is conditional on domain entities).
- Ingestion is best-effort: a malformed/empty tracer file must NOT crash the generator.
- **SC-004** is satisfied. `ruff` + `mypy` clean.

## Context & Constraints

- Spec: [spec.md](../spec.md) — User Story 4, FR-007/008, SC-004, Edge Cases (malformed tracer must not crash).
- Plan: [plan.md](../plan.md) — IC-04.
- Research: [research.md](../research.md) — `generator.py` already ingests free-text artifacts via `_build_ingestor_findings` (workflow-failures-log / analysis-report / mission-review); slot a tracer reader into that exact seam.
- **NFR-002 — EXTEND, don't fork**: add a `_load_traces` reader to the existing `_build_ingestor_findings` seam; do not duplicate the generator.
- **C-006 — red-first** through `spec-kitty retrospect create`.

## Branch Strategy

- **Strategy**: {{branch_strategy}}
- **Planning base branch**: {{planning_base_branch}}
- **Merge target branch**: {{merge_target_branch}}

> Populated automatically by `spec-kitty agent mission tasks`. Do NOT edit manually.

## Subtasks & Detailed Guidance

### Subtask T011 – RED test: tracer-sourced finding + no false data-model gap

- **Purpose**: Reproduce #2217 through the pre-existing surface (red-first).
- **Steps**:
  1. Create the test package dir `tests/specify_cli/retrospective/` with an `__init__.py` (the test packages in this repo carry `__init__.py`), then add `tests/specify_cli/retrospective/test_generator_traces_ingest.py`.
  2. Seed a realistic scratch mission with `kitty-specs/<slug>/traces/tooling-friction.md` containing helped/not_helpful/gaps/proposals content (C-007).
  3. Run `spec-kitty retrospect create`; assert ≥ 1 finding/proposal is sourced from the tracer.
  4. NEGATIVE case: seed a no-entity (governance/wiring) mission with no `data-model.md`; assert the record does NOT flag a "missing data-model.md" gap.
  5. POSITIVE paired case (pins "conditional-on-entities", not "always-off"): seed a mission WITH domain entities (a real spec Key Entities / entity section) and no `data-model.md`; assert the record STILL flags the missing-`data-model.md` gap. The negative + positive pair together prove the gap is gated on entity presence, not silently disabled.
  6. Confirm RED against current `generator.py` (no `traces/` glob; data-model gap unconditional).
- **Files**: `tests/specify_cli/retrospective/test_generator_traces_ingest.py` (new — in `owned_files` + `create_intent`) plus the new `__init__.py` for the package.
- **Parallel?**: Parallel-safe with WP01/WP02/WP05/WP06.
- **Notes**: The new `__init__.py` is a packaging stub for the new test dir; keep it empty.

### Subtask T012 – `_load_traces` reader + conditional data-model gap

- **Purpose**: Extend the ingestor seam and make the data-model gap conditional.
- **Steps**:
  1. In `src/specify_cli/retrospective/generator.py`, add a `_load_traces` reader and wire it into the existing `_build_ingestor_findings` seam so `traces/*.md` feed the same finding/proposal channels as the other ingested artifacts.
  2. Make the absent-`data-model.md` gap conditional on the presence of domain entities (no false gap for no-entity missions).
  3. Best-effort: guard the tracer read so a malformed/empty file is skipped (logged/translated, not crashing) — no empty/effect-free `except` (Sonar).
  4. Keep additions ≤ 15 complexity; type-annotate the new reader.
- **Files**: `src/specify_cli/retrospective/generator.py`.
- **Parallel?**: After T011 red.
- **Notes**: Reuse the existing finding model the seam emits; do not introduce a parallel ingest path.

## Test Strategy

- New test: `tests/specify_cli/retrospective/test_generator_traces_ingest.py` (+ package `__init__.py`).
- Red-first via `spec-kitty retrospect create` (the pre-existing surface).
- Add a malformed-tracer case asserting the generator still completes (best-effort).
- Run: `PWHEADLESS=1 pytest tests/specify_cli/retrospective/test_generator_traces_ingest.py -q`.
- Realistic tracer content (C-007).

## Risks & Mitigations

- **Forking the generator**: extend `_build_ingestor_findings`; a parallel code path would diverge (NFR-002).
- **Crash on malformed tracer**: wrap the read best-effort with concrete recovery/logging (no silent empty `except`).
- **Over-suppressing the data-model gap**: gate strictly on domain-entity presence so entity-bearing missions still get the gap.

## Review Guidance

- Confirm `_load_traces` plugs into the existing seam (not a new pipeline).
- Confirm tracer content produces ≥ 1 sourced finding; a no-entity mission has no false data-model gap AND an entity-bearing mission with no `data-model.md` STILL gets the gap (the negative+positive pair pins conditional-on-entities).
- Confirm a malformed tracer does not crash `retrospect create`.
- Confirm `ruff`/`mypy` clean, complexity ≤ 15.

## Activity Log

> **CRITICAL**: Append new entries at the END in chronological order. Format: `- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <action>`.

- 2026-06-27T00:00:00Z – system – Prompt created.
- 2026-06-27T16:23:48Z – claude:opus:python-pedro:implementer – shell_pid=1735250 – Assigned agent via action command
- 2026-06-27T16:45:19Z – user – shell_pid=1735250 – WP04 implementation committed in lane-d (90e73c818)
- 2026-06-27T16:45:20Z – user – shell_pid=1735250 – WP04 implementation committed in lane-d (90e73c818)
- 2026-06-27T16:45:31Z – claude:opus:python-pedro:implementer – shell_pid=1735250 – Ready: tracer-sourced finding produced; no-entity mission has no false data-model gap; malformed tracer non-crashing
- 2026-06-27T16:46:44Z – claude:opus:reviewer-renata:reviewer – shell_pid=1801725 – Started review via action command
- 2026-06-27T16:50:58Z – user – shell_pid=1801725 – Review APPROVE (reviewer-renata, isolated): tracer ingest extends _build_ingestor_findings seam; 3-tuple change justified (new gap channel, not relocation); data-model gap entity-gated; 9 re-pins preserved verbatim; fixture Key Entities legit, snapshot un-loosened; gates green
