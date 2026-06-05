---
work_package_id: WP06
title: Skill reconciliation + doc/CLI parity guard + glossary
dependencies:
- WP04
requirement_refs:
- FR-017
- FR-018
- FR-019
tracker_refs:
- '1636'
planning_base_branch: feature/status-writepath-profile-surface-remediation
merge_target_branch: feature/status-writepath-profile-surface-remediation
branch_strategy: Planning artifacts for this mission were generated on feature/status-writepath-profile-surface-remediation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/status-writepath-profile-surface-remediation unless the human explicitly redirects the landing branch.
subtasks:
- T027
- T028
- T029
- T030
- T031
phase: 'Lane B-core — #1636'
agent: claude
history:
- at: '2026-06-05T08:32:05Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: curator-carla
authoritative_surface: src/doctrine/skills/ad-hoc-profile-load/
execution_mode: code_change
model: ''
owned_files:
- src/doctrine/skills/ad-hoc-profile-load/SKILL.md
- tests/architectural/test_docs_cli_reference_parity.py
- glossary/contexts/governance.md
role: curator
tags: []
task_type: implement
---

# Work Package Prompt: WP06 – Skill reconciliation + doc/CLI parity guard + glossary

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load `curator-carla` (role `curator`) before proceeding.

---

## Objectives & Success Criteria

Close the documentation half of #1636 and lock it against regression.

- **FR-017**: reconcile `src/doctrine/skills/ad-hoc-profile-load/SKILL.md` — adopt/invoke steps point to `spec-kitty ask` / `advise`; profile-detail steps point to the new `profile show`; `hierarchy` / `init` / `create` references are either implemented elsewhere or removed. No step references a non-existent command.
- **FR-018**: a doc/CLI parity guard test asserts every `spec-kitty agent profile <subcommand>` referenced in shipped skill docs maps to a registered Typer command.
- **FR-019**: glossary entries for *abstract base profile*, *activation chokepoint*, and *activated vs available profile* (DIRECTIVE_032 — vocabulary before the `profile show` warning string ships).

**Done when**: parity guard passes; the skill references only implemented commands; the glossary defines the three terms.

## Context & Constraints

- **C-006**: edit the **source** template `src/doctrine/skills/ad-hoc-profile-load/SKILL.md`, never the generated agent copies (`.claude/`, `.codex/`, …). Those propagate on `spec-kitty upgrade`.
- Depends on **WP04** (the `profile show` command must exist for the skill to reference it and for the parity guard to pass).
- Canonical invoke surfaces already exist: `spec-kitty ask <profile> <request>`, `spec-kitty advise --profile`.

## Branch Strategy

- **Planning base / merge target**: `feature/status-writepath-profile-surface-remediation` · **Depends on**: WP04.

## Subtasks & Detailed Guidance

### Subtask T027 – Reconcile SKILL.md

- **Steps**: replace `agent profile show <id>` Step-1 usages so they resolve correctly (now a real command after WP04). Repoint adopt/invoke guidance to `spec-kitty ask` / `advise`. For `hierarchy` / `init` / `create`: remove them or replace with the supported equivalent. Ensure no remaining reference to an unimplemented command.
- **Files**: `src/doctrine/skills/ad-hoc-profile-load/SKILL.md`

### Subtask T028 – Doc/CLI parity guard [P]

- **Steps**: add `tests/architectural/test_docs_cli_reference_parity.py` (or extend if present) to scan shipped skill docs for `spec-kitty agent profile <sub>` tokens and assert each `<sub>` is a registered command on the `profile` Typer app. Fail on any orphan reference.
- **Files**: `tests/architectural/test_docs_cli_reference_parity.py`

### Subtask T029 – Glossary terms [P]

- **Steps**: add to `glossary/contexts/governance.md`: *abstract base profile* (a profile referenced via `specializes_from` that is not itself activated — a shared-element store, not directly selectable), *activation chokepoint* (the `charter.resolver.DoctrineService` activation filter), *activated vs available profile*. Follow the existing entry format in that file.
- **Files**: `glossary/contexts/governance.md`

### Subtask T030 – Cross-link `profile show`

- **Steps**: in SKILL.md, reference the new `profile show` for the "inspect a profile" path and note `--all` for abstract bases.

### Subtask T031 – Verify

- **Steps**: run the parity guard; grep the SKILL.md for any `profile (hierarchy|init|create|show)` token and confirm each resolves to a real command.

## Test Strategy

- `pytest tests/architectural/test_docs_cli_reference_parity.py`.

## Risks & Mitigations

- **Editing generated copies** → only touch the `src/doctrine/skills/...` source (C-006).
- **Parity guard too broad** → scope the scan to the `ad-hoc-profile-load` skill (and any other doc that names `agent profile` subcommands), matching only `agent profile <token>`.

## Review Guidance

- Confirm only the source SKILL.md changed (no generated copies).
- Confirm the parity guard fails if a phantom command is reintroduced.
- Confirm glossary entries match the house format.

## Activity Log

- 2026-06-05T08:32:05Z – system – Prompt created.
