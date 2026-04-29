---
work_package_id: WP04
title: Conditional Prompt Fragment Rendering (REASONS)
dependencies:
- WP01
- WP02
requirement_refs:
- FR-013
- FR-014
- FR-015
- NFR-001
- NFR-005
- C-004
planning_base_branch: doctrine/spdd-reasons-pack
merge_target_branch: doctrine/spdd-reasons-pack
branch_strategy: Planning artifacts for this feature were generated on doctrine/spdd-reasons-pack. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into doctrine/spdd-reasons-pack unless the human explicitly redirects the landing branch.
created_at: '2026-04-29T08:15:46Z'
subtasks:
- T014
- T015
- T016
- T017
- T018
- T019
agent: claude
history:
- date: '2026-04-29'
  author: spec-kitty.tasks
  note: Initial WP generated
agent_profile: python-pedro
authoritative_surface: src/specify_cli/missions/software-dev/command-templates/
execution_mode: code_change
model: claude-opus-4-7
owned_files:
- src/specify_cli/missions/software-dev/command-templates/specify.md
- src/specify_cli/missions/software-dev/command-templates/plan.md
- src/specify_cli/missions/software-dev/command-templates/tasks.md
- src/specify_cli/missions/software-dev/command-templates/implement.md
- src/doctrine/spdd_reasons/template_renderer.py
- tests/prompts/__init__.py
- tests/prompts/test_prompt_fragment_rendering.py
- tests/prompts/fixtures/baseline/.gitkeep
role: implementer
tags:
- prompts
- templates
---

## ⚡ Do This First: Load Agent Profile

- Run `/ad-hoc-profile-load` with profile `python-pedro` and role `implementer`.
- Profile file: `src/doctrine/agent_profiles/shipped/python-pedro.agent.yaml`.
- After load, restate identity, governance scope, and boundaries before continuing.

# WP04 — Conditional Prompt Fragment Rendering (REASONS)

## Branch Strategy

- **Planning base branch**: `doctrine/spdd-reasons-pack`
- **Merge target**: `doctrine/spdd-reasons-pack`
- **Execution workspace**: allocated by `lanes.json` at `spec-kitty agent action implement WP04 --agent claude --mission spdd-reasons-doctrine-pack-01KQC4AX`. Do not guess the worktree path.

## Objective

Add a single conditional REASONS guidance block to each of the four mission-action source command templates (`specify`, `plan`, `tasks`, `implement`). Implement a small renderer hook that, at template materialization time:

- Keeps the block content (stripping the marker comment lines only) when `is_spdd_reasons_active(repo_root)` is `True`.
- Removes the block AND its delimiters in their entirety when inactive — producing byte-or-semantic identical output to the pre-feature template.

## Context

### Spec & contracts
- FR-013, FR-014, FR-015, NFR-001 (byte-identical inactive), NFR-005 (mypy strict), C-004 (no always-on REASONS).
- [contracts/prompt-fragment.md](../contracts/prompt-fragment.md) — the renderer contract.

### Marker convention (verbatim)
```
<!-- spdd:reasons-block:start -->
... markdown content ...
<!-- spdd:reasons-block:end -->
```

### Action-scoped block headlines (per FR-014 and contracts/prompt-fragment.md)
- specify.md → `### REASONS Guidance — Specify` (Requirements + Entities)
- plan.md → `### REASONS Guidance — Plan` (Approach + Structure)
- tasks.md → `### REASONS Guidance — Tasks` (Operations + WP boundaries)
- implement.md → `### REASONS Guidance — Implement WP<id>` (Full canvas: R, E, A, S, O, N, S)
- review.md is owned by **WP05**, not this WP.

### Materialization seam
Command templates flow via `m_0_9_1_complete_lane_migration.AGENT_DIRS` and `get_agent_dirs_for_project()` to `.claude/commands/`, `.amazonq/prompts/`, `.kiro/prompts/`, etc. (12 agent directories total — see CLAUDE.md). Find the function(s) that copy `src/specify_cli/missions/*/command-templates/*.md` into agent directories and add the post-process step there. Do NOT duplicate the materialization logic.

### Where to find materialization
Search for callers of `AGENT_DIRS` / `get_agent_dirs_for_project()` and any module that reads `command-templates/*.md` and writes them under `.claude/`, `.amazonq/`, etc. Likely candidates:
- `src/specify_cli/skills/command_renderer.py`
- `src/specify_cli/skills/command_installer.py`
- migrations that update slash commands

The post-process MUST run for ALL agents that consume the templates.

## Subtasks

### T014 — Add SPDD reasons-block to `specify.md`

**Path**: `src/specify_cli/missions/software-dev/command-templates/specify.md`

Insert near the start of the body content (just after the front-matter / version header), or at a more natural narrative seam if one exists. Use markers exactly as in the convention.

Block content (concise, ≤25 markdown lines):

```
<!-- spdd:reasons-block:start -->

### REASONS Guidance — Specify

This project's charter selected the SPDD/REASONS doctrine pack. While capturing
the spec, populate or update these REASONS canvas sections:

- **Requirements** — problem statement, acceptance criteria, definition of done.
- **Entities** — domain concepts, relationships, canonical glossary terms.

Reference: `kitty-specs/<mission>/reasons-canvas.md` if present. Use the
template at `src/doctrine/templates/fragments/reasons-canvas-template.md` if
the canvas does not yet exist.

Charter directives take precedence over canvas content.

<!-- spdd:reasons-block:end -->
```

### T015 — Add SPDD reasons-block to `plan.md`

**Path**: `src/specify_cli/missions/software-dev/command-templates/plan.md`

Block content covers Approach + Structure:

```
<!-- spdd:reasons-block:start -->

### REASONS Guidance — Plan

While composing the plan, fill or update:

- **Approach** — chosen strategy and rejected alternatives with rationale.
- **Structure** — code surfaces, components, dependencies, ownership boundaries.

Link to source artifacts (spec, contracts) instead of duplicating them.

<!-- spdd:reasons-block:end -->
```

### T016 — Add SPDD reasons-block to `tasks.md`

**Path**: `src/specify_cli/missions/software-dev/command-templates/tasks.md`

Block content covers Operations + WP boundaries:

```
<!-- spdd:reasons-block:start -->

### REASONS Guidance — Tasks

While breaking the plan into work packages, capture:

- **Operations** — ordered implementation and test steps per WP.
- **WP boundaries** — explicit `owned_files` and `authoritative_surface` for each WP, plus what each WP must NOT touch (Safeguards subset).

If multiple WPs are proposed for the same surface, surface that as a Safeguard
rather than dividing it implicitly.

<!-- spdd:reasons-block:end -->
```

### T017 — Add SPDD reasons-block to `implement.md`

**Path**: `src/specify_cli/missions/software-dev/command-templates/implement.md`

Block content references the full canvas:

```
<!-- spdd:reasons-block:start -->

### REASONS Guidance — Implement WP<id>

Before coding, load the WP-scoped REASONS section from
`kitty-specs/<mission>/reasons-canvas.md`:

- Requirements (WP-scoped)
- Entities (WP-relevant)
- Approach (chosen strategy for this WP)
- Structure (files this WP owns)
- Operations (ordered steps)
- Norms (testing, observability, style)
- Safeguards (hard constraints — what not to break)

If the canvas is missing, invoke the `spec-kitty-spdd-reasons` skill to
generate it before continuing.

Do not invent files, entities, or scope outside the canvas without recording a
deviation.

<!-- spdd:reasons-block:end -->
```

### T018 — Implement renderer hook

**New module**: `src/doctrine/spdd_reasons/template_renderer.py`

Public surface:

```python
from pathlib import Path

REASONS_BLOCK_START = "<!-- spdd:reasons-block:start -->"
REASONS_BLOCK_END = "<!-- spdd:reasons-block:end -->"

def process_spdd_blocks(template_text: str, *, active: bool) -> str:
    """Process SPDD reasons-block markers.

    - active=True: strip ONLY the marker comment lines; keep block content.
    - active=False: remove the block and its delimiters entirely. Result must
      be byte-or-semantic identical to the pre-feature template (no extra
      blank line left behind).
    Raises if a start marker has no matching end marker.
    """
```

Hook the function into the existing template-materialization seam (the function that reads `command-templates/*.md` and writes per-agent prompt files). Pass `active=is_spdd_reasons_active(repo_root)`.

If multiple seams exist (one per agent kind), use a single shared helper to avoid drift.

### T019 — Add `tests/prompts/test_prompt_fragment_rendering.py`

**Path**: `tests/prompts/test_prompt_fragment_rendering.py`

Tests:

```python
class TestProcessSpddBlocks:
    def test_active_keeps_content_strips_markers(self): ...
    def test_inactive_removes_block_entirely(self): ...
    def test_inactive_no_extra_blank_line_left(self): ...
    def test_unmatched_start_raises(self): ...
    def test_no_block_present_returns_input_unchanged(self): ...

class TestInactiveBaselineEquivalence:
    # NFR-001 and FR-013 enforcement
    @pytest.mark.parametrize("template", ["specify.md", "plan.md", "tasks.md", "implement.md"])
    def test_inactive_template_byte_equivalent_to_baseline(self, template): ...

class TestActiveTemplatesContainBlock:
    @pytest.mark.parametrize("template,headline", [
        ("specify.md", "REASONS Guidance — Specify"),
        ("plan.md", "REASONS Guidance — Plan"),
        ("tasks.md", "REASONS Guidance — Tasks"),
        ("implement.md", "REASONS Guidance — Implement"),
    ])
    def test_active_template_contains_headline(self, template, headline): ...
```

For inactive baselines: capture each template's pre-feature output as `tests/prompts/fixtures/baseline/<template>.expected.md`. Compare against the rendered output for an inactive project. Bytes must match.

## Definition of Done

- All four templates contain a `spdd:reasons-block` block at a sensible seam.
- `process_spdd_blocks()` exists, is unit-tested for all five behaviors, and is wired into the template materialization path.
- Inactive rendering of all four templates is byte-identical to baseline.
- Active rendering of all four templates contains the expected headline.
- `uv run pytest tests/prompts -q` passes.
- `uv run pytest tests -q` (full) passes.
- `uv run mypy --strict src/doctrine/spdd_reasons` clean.

## Reviewer guidance

- Confirm the block appears at a natural seam in each template (not jammed mid-section).
- Confirm the renderer is wired ONCE (single helper) and called for ALL agent template materializations.
- Confirm the baseline fixtures lock the pre-feature byte content of each template.
- Confirm no other behavior of the materialization path changed.

## Risks

- **Multi-agent materialization**: 12 agent directories consume templates. If only `.claude/commands/` is processed, other agents render with marker comments visible. Trace ALL callers.
- **Trailing newline**: a common source of byte-non-identity. Test explicitly that block removal does not add or remove trailing newlines.
- **Pre-existing comments**: the markers are HTML comments. Other HTML comments in templates must not be confused with the SPDD markers — match the EXACT marker strings.

## Out of scope

- `review.md` template (owned by WP05).
- Charter wiring (WP02).
- Skill (WP03).
- Docs (WP06).
