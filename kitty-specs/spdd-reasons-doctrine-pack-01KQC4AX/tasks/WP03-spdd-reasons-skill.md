---
work_package_id: WP03
title: spec-kitty-spdd-reasons Skill
dependencies:
- WP01
requirement_refs:
- FR-010
- FR-011
- FR-012
planning_base_branch: doctrine/spdd-reasons-pack
merge_target_branch: doctrine/spdd-reasons-pack
branch_strategy: Planning artifacts for this feature were generated on doctrine/spdd-reasons-pack. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into doctrine/spdd-reasons-pack unless the human explicitly redirects the landing branch.
created_at: '2026-04-29T08:15:46Z'
subtasks:
- T012
- T013
agent: "claude:opus:curator-carla:implementer"
shell_pid: "39132"
history:
- date: '2026-04-29'
  author: spec-kitty.tasks
  note: Initial WP generated
agent_profile: curator-carla
authoritative_surface: src/doctrine/skills/spec-kitty-spdd-reasons/
execution_mode: code_change
model: claude-opus-4-7
owned_files:
- src/doctrine/skills/spec-kitty-spdd-reasons/SKILL.md
- tests/doctrine/test_spdd_reasons_skill.py
role: implementer
tags:
- doctrine
- skills
---

## ⚡ Do This First: Load Agent Profile

- Run `/ad-hoc-profile-load` with profile `curator-carla` and role `implementer`.
- Profile file: `src/doctrine/agent_profiles/shipped/curator-carla.agent.yaml`.
- After load, restate identity, governance scope, and boundaries before continuing.

# WP03 — `spec-kitty-spdd-reasons` Skill

## Branch Strategy

- **Planning base branch**: `doctrine/spdd-reasons-pack`
- **Merge target**: `doctrine/spdd-reasons-pack`
- **Execution workspace**: allocated by `lanes.json` at `spec-kitty agent action implement WP03 --agent claude --mission spdd-reasons-doctrine-pack-01KQC4AX`. Do not guess the worktree path.

## Objective

Author the agent-facing skill that drives REASONS Canvas authoring and review for missions that opted in to SPDD via charter (FR-010, FR-011, FR-012).

The skill must:
- Detect activation status (call `is_spdd_reasons_active(repo_root)` from WP02 conceptually; the SKILL.md instructs the agent how to use it).
- Load mission context: `spec.md`, `plan.md`, `tasks.md`, WP prompts, charter context, glossary, research, contracts, and relevant code.
- Generate or update `kitty-specs/<mission>/reasons-canvas.md`.
- Compile per-WP REASONS summaries when useful.
- In review mode, compare implementation against the canvas and classify divergences.

The skill must explicitly warn:
- Do NOT use REASONS as a complete system mirror.
- Do NOT overwrite user-authored mission artifacts.
- Escalate (do not silently enforce) if the charter has not selected SPDD/REASONS but the user demands enforcement.

## Context

### Reference skill (mirror this shape exactly)
- `src/doctrine/skills/spec-kitty-charter-doctrine/SKILL.md`

Read it first. Match the YAML frontmatter shape, body section ordering, and "Does NOT handle" framing.

### Spec references
- FR-010, FR-011, FR-012 — see [spec.md](../spec.md).
- [data-model.md §Skill](../data-model.md) — body content.

### Trigger phrases (per FR-010)
- "use SPDD"
- "use REASONS"
- "generate a REASONS canvas"
- "apply structured prompt driven development"
- "make this mission SPDD"

## Subtasks

### T012 — Author `src/doctrine/skills/spec-kitty-spdd-reasons/SKILL.md`

**Path**: `src/doctrine/skills/spec-kitty-spdd-reasons/SKILL.md`

Frontmatter:
```yaml
---
name: spec-kitty-spdd-reasons
description: |
  Drive REASONS Canvas authoring and review for Spec Kitty missions that opted in to
  Structured-Prompt-Driven Development (SPDD) via charter selection.
  Triggers: "use SPDD", "use REASONS", "generate a REASONS canvas",
  "apply structured prompt driven development", "make this mission SPDD".
  Does NOT handle: enforcing SPDD on projects whose charter has not selected the
  doctrine pack (escalate to charter workflow instead). Does NOT mirror code as
  prose; code remains the source of truth for current behavior.
---
```

Body sections (mirror `spec-kitty-charter-doctrine`):

1. **Title** — `# spec-kitty-spdd-reasons`
2. **What this skill does** — bullets for activation detection, context loading, canvas generation/update, WP summary compilation, review-mode comparison.
3. **What this skill does NOT do** — bullets for mirror-the-code, overwrite-without-merge, silent-enforce.
4. **Activation rules**:
   - If active (charter selected SPDD/REASONS): proceed with canvas authoring or review using the seven-section template at `src/doctrine/templates/fragments/reasons-canvas-template.md`.
   - If inactive and user requests ad-hoc canvas generation: proceed but add a "not formally opted in" note to the canvas header.
   - If inactive and user demands enforcement: escalate; suggest running the charter interview to select the doctrine pack.
5. **How to detect activation** — explain that the skill should look at `.kittify/charter/governance.yaml` for paradigm `structured-prompt-driven-development` or related tactics/directive, or call any equivalent tooling exposed by the host.
6. **How to author the canvas** — instruct the agent to:
   - Read mission artifacts (spec, plan, tasks, contracts, research).
   - Map content to the seven sections (Requirements, Entities, Approach, Structure, Operations, Norms, Safeguards).
   - Use links to source artifacts rather than duplicating spec/plan content.
   - Preserve user-authored content; merge rather than overwrite.
   - Append (never rewrite) the Deviations section.
7. **How to review with the canvas** — instruct the reviewer to trace diff to Requirements/Operations, detect uninvented entities/files, verify Norms and Safeguards, and classify divergences per the taxonomy in [data-model.md §Drift classification](../data-model.md).
8. **Charter precedence** — directives from the charter take precedence over canvas content.
9. **Glossary discipline** — when canvas authoring surfaces a term conflict, escalate to the glossary skill.

Aim for ≤200 lines. Concise, agent-friendly Markdown.

### T013 — Add skill discovery test

**Path**: `tests/doctrine/test_spdd_reasons_skill.py`

Test (≤40 lines):

```python
def test_skill_file_exists():
    path = Path("src/doctrine/skills/spec-kitty-spdd-reasons/SKILL.md")
    assert path.exists(), "spec-kitty-spdd-reasons/SKILL.md missing"

def test_skill_frontmatter_has_name_and_description():
    # parse YAML frontmatter; assert name == "spec-kitty-spdd-reasons"
    # and description contains the FR-010 trigger phrases.
    ...

def test_skill_body_mentions_seven_canvas_sections():
    text = path.read_text()
    for section in ("Requirements", "Entities", "Approach", "Structure",
                    "Operations", "Norms", "Safeguards"):
        assert section in text
```

## Definition of Done

- SKILL.md present, schema-correct YAML frontmatter, ≤200 lines body.
- Body mentions all seven canvas sections, all five trigger phrases, the three "does NOT" rules, and the escalation rule.
- New skill discovery test passes.
- `uv run pytest tests/doctrine -q` passes.

## Reviewer guidance

- Check that the skill mirrors the shape of `spec-kitty-charter-doctrine/SKILL.md`.
- Check the skill warns explicitly against three dangers: full system mirror, overwriting user content, and silent enforcement on non-opted-in projects.
- Check that all five FR-010 trigger phrases appear in the description.
- Check the skill does NOT include implementation code or modify other modules.

## Risks

- **Trigger collision**: confirm "use SPDD" / "use REASONS" / "generate a REASONS canvas" / "apply structured prompt driven development" / "make this mission SPDD" do not collide with existing skill triggers. Run `grep -r 'use SPDD\|use REASONS' src/doctrine/skills/` before writing.
- **Frontmatter drift**: if the existing skill loader expects a specific frontmatter shape (e.g., a `triggers:` list rather than triggers embedded in `description`), follow the host loader's expectation. Inspect peer skills to confirm.

## Out of scope

- Charter wiring (WP02).
- Prompt fragment rendering (WP04).
- Review gate (WP05).
- Docs (WP06).

## Activity Log

- 2026-04-29T08:50:05Z – claude:opus:curator-carla:implementer – shell_pid=39132 – Started implementation via action command
- 2026-04-29T08:54:46Z – claude:opus:curator-carla:implementer – shell_pid=39132 – Ready for review: SKILL.md + discovery test
