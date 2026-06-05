---
work_package_id: WP04
title: Activation-aware profile list + profile show
dependencies:
- WP03
requirement_refs:
- FR-011
- FR-012
- FR-013
- FR-014
- FR-015
tracker_refs:
- '1636'
planning_base_branch: feature/status-writepath-profile-surface-remediation
merge_target_branch: feature/status-writepath-profile-surface-remediation
branch_strategy: Planning artifacts for this mission were generated on feature/status-writepath-profile-surface-remediation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/status-writepath-profile-surface-remediation unless the human explicitly redirects the landing branch.
subtasks:
- T015
- T016
- T017
- T018
- T019
- T020
- T021
- T022
phase: 'Lane B-core — #1636'
agent: "claude"
assignee: "claude"
history:
- at: '2026-06-05T08:32:05Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/profiles_cmd.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/profiles_cmd.py
- tests/specify_cli/invocation/cli/test_profiles_activation.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP04 – Activation-aware profile list + profile show

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load `python-pedro` (role `implementer`) before proceeding.

---

## Objectives & Success Criteria

Deliver the #1636 user-facing surfaces, routed through charter activation.

- **FR-011**: `agent profile list` defaults to **activated-only** by **filtering** the existing `ProfileRegistry.list_all()` rows by `PackContext.from_config(repo_root).activated_agent_profiles` (do **not** swap the data source — preserves descriptor schema / NFR-001).
- **FR-012**: `--all` / `--show-available` flags (mirroring `charter list`) show the full catalog, annotated by source layer and `activated | available`.
- **FR-013**: new `agent profile show <id>` (alias `get`) prints the full resolved profile definition, with `--json`.
- **FR-014**: `show` is activation-gated on the leaf id; non-activated → structured `profile_not_activated` error listing activated candidates; `--all` bypasses for inspection.
- **FR-015**: lineage **Option A** — resolution may traverse non-activated `specializes_from` parents (abstract base profiles); emit a user-facing warning naming any non-activated ancestor.

**Done when**: configured projects list only activated profiles; unconfigured projects are byte-identical to today (NFR-001); `show` renders/gates/warns per the contracts in [data-model.md](../data-model.md).

## Context & Constraints

- Today `profiles_cmd.py:30` builds rows from `ProfileRegistry.list_all()` — keep that source for `list` and **filter** it (FR-011), per the dialectic-review correction. Use the WP03 factory's `.agent_profiles` for `show` (where no legacy schema is at stake).
- Lineage warning text and `profile_not_activated` schema are specified in [data-model.md](../data-model.md).
- **C-005** layer rule preserved (factory already handles it).

## Branch Strategy

- **Planning base / merge target**: `feature/status-writepath-profile-surface-remediation` · **Depends on**: WP03 (factory).

## Subtasks & Detailed Guidance

### Subtask T015 – `profile list` activation filter (FR-011)

- **Steps**: after building the `ProfileRegistry` descriptor rows, filter by `PackContext.from_config(repo_root).activated_agent_profiles` when it is not `None`; when `None`, return all (unchanged default). Do not alter the descriptor schema.
- **Files**: `src/specify_cli/cli/commands/profiles_cmd.py`

### Subtask T016 – `--all` / `--show-available` (FR-012)

- **Steps**: add the two flags; when set, list the unfiltered rows and add `source` (built-in/org/project) + `state` (`activated`/`available`) columns. Mirror `charter list`'s flag semantics.

### Subtask T017 – `profile show <id>` render (FR-013)

- **Steps**: add `show` (alias `get`) accepting a profile id + `--json`. Resolve via the WP03 factory; render `initialization_declaration`, `specialization` (primary/secondary/avoidance/success), `collaboration` (handoff_to/from, works_with, canonical_verbs), `mode_defaults`, directive/tactic references, source layer. `--json` emits a sorted-key schema (NFR-004).

### Subtask T018 – Activation gate + not-found (FR-014)

- **Steps**: `svc.agent_profiles.get(id)`; if absent and not `--all`, emit the `profile_not_activated` structured error (see data-model.md) and exit 1.

### Subtask T019 – Lineage Option A + warning (FR-015)

- **Steps**: compose the full definition via the inner `AgentProfileRepository.resolve_profile(id)` (may traverse non-activated parents). If any traversed ancestor ∉ `svc.agent_profiles`, append the lineage warning (stderr yellow in human mode; `warnings[]` in JSON).

### Subtask T020 – Tests: list (FR-011/012, NFR-001) [P]

- **Steps**: assert configured project filters; **unconfigured project output is byte-identical** to the pre-change command (capture a baseline); `--all`/`--show-available` annotations correct.
- **Files**: `tests/specify_cli/invocation/cli/test_profiles_activation.py`

### Subtask T021 – Tests: show gating + warning [P]

- **Steps**: activated id renders; non-activated id → `profile_not_activated` with sorted candidates; abstract-parent child resolves **with** warning; `show <non-activated-parent>` gated without `--all`.

### Subtask T022 – `--all` bypass on show

- **Steps**: `show <non-activated> --all` renders the profile (inspection) and still includes the lineage warning where applicable.

## Test Strategy

- `pytest tests/specify_cli/invocation/cli/test_profiles_activation.py`; `mypy --strict`; `ruff check`.

## Risks & Mitigations

- **NFR-001 regression** → filter, do not swap the data source; snapshot the unconfigured-project output.
- **Mixing dict vs repo surfaces** → `svc.agent_profiles` is a `dict[str, AgentProfile]` (visibility gate); use the inner `AgentProfileRepository.resolve_profile` only for lineage composition.

## Review Guidance

- Confirm `list` default is byte-identical for unconfigured projects.
- Confirm the lineage warning fires for non-activated parents and never silently hides inheritance.
- **NFR-003**: confirm existing `runtime/next` profile-resolution tests stay green (the activation path is shared; this surface must not regress runtime behavior).

## Activity Log

- 2026-06-05T08:32:05Z – system – Prompt created.
- 2026-06-05T12:58:47Z – claude – Moved to in_progress
- 2026-06-05T12:58:49Z – claude – Implemented via bypass; tests green
