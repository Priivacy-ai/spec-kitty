---
work_package_id: WP06
title: Workflow Profile Injection
lane: done
dependencies: [WP05]
requirement_refs:
- FR-006
- FR-007
- FR-008
- FR-009
planning_base_branch: feature/agent-profile-implementation
merge_target_branch: feature/agent-profile-implementation
branch_strategy: Planning artifacts for this feature were generated on feature/agent-profile-implementation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/agent-profile-implementation unless the human explicitly redirects the landing branch.
subtasks:
- T021
- T022
- T023
- T024
- T025
phase: Phase B - Core Profile Infrastructure
assignee: ''
agent: ''
shell_pid: ''
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-03-22T11:50:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent_profile: implementer
---

# Work Package Prompt: WP06 – Workflow Profile Injection

## ⚠️ IMPORTANT: Review Feedback Status

Check `review_status` field above. If `has_feedback`, address the Review Feedback section first.

---

## Review Feedback

*[Empty — populated by `/spec-kitty.review` if work is returned.]*

---

## Dependency Rebase Guidance

Depends on **WP05**. Sentinel field and human-in-charge profile must exist before T023.

```bash
spec-kitty implement WP06 --base WP05
```

---

## Objectives & Success Criteria

- `_render_profile_context(repo_root, wp_frontmatter, allow_missing)` function exists in `workflow.py`.
- Implement prompt output includes the agent identity fragment when `agent_profile` is set.
- `agent_profile: human-in-charge` → no injection, "Human-in-charge WP: no agent identity injected" logged.
- `agent_profile` absent → defaults to `generic-agent`; if not found, warns and continues.
- Explicit unresolvable `agent_profile` without `--allow-missing-profile` → blocking error (exit 1).
- Explicit unresolvable `agent_profile` with `--allow-missing-profile` → warning, continues without injection.
- All 5 ATDD scenarios pass.
- NFR-002 (≤500ms injection overhead) met.
- Requirements FR-006, FR-007, FR-008, FR-009, NFR-002, NFR-003, SC-002, SC-003 satisfied.

## Context & Constraints

- **Plan**: `kitty-specs/057-doctrine-stack-init-and-profile-integration/plan.md` → WP-B3
- **Spec**: US-3, FR-006-FR-009, NFR-002-NFR-003
- **Pattern**: Follow `_render_constitution_context()` at line 114 of `workflow.py` as the model.
- **WP frontmatter access**: In `workflow.py`'s implement command, the WP frontmatter is already parsed — use `extract_scalar(wp.frontmatter, "agent_profile")`.
- **Start command**: `spec-kitty implement WP06 --base WP05`

## Subtasks & Detailed Guidance

### Subtask T021 – Write ATDD acceptance tests (tests first)

- **Purpose**: 5 scenarios from US-3 must be red before implementation.
- **Files**: Create `tests/agent/cli/commands/test_workflow_profile_injection.py`.
- **Steps**:
  1. Study `tests/agent/cli/commands/` for existing test patterns. Look for how the `implement` command is invoked in tests.
  2. Write 5 test functions:
     - `test_implementer_profile_injected` — WP frontmatter has `agent_profile: implementer`; implement output contains the implementer identity fragment (name, purpose, specialization).
     - `test_architect_profile_injected` — WP with `agent_profile: architect`; architect profile loaded.
     - `test_no_agent_profile_defaults_to_generic_agent` — WP with no `agent_profile` field; `generic-agent` profile loaded (if available) or warning emitted (if not promoted yet).
     - `test_human_in_charge_skips_injection` — WP with `agent_profile: human-in-charge`; output does NOT contain an "Agent Identity" section; "Human-in-charge WP: no agent identity injected" message appears. **This is the authoritative test for the sentinel skip behaviour** — WP05 T017 only tests profile schema/kanban, not workflow injection.
     - `test_unresolvable_profile_blocking_error` — WP with `agent_profile: nonexistent-profile`; without `--allow-missing-profile` → exit code 1. With `--allow-missing-profile` → exit 0, warning in output.
  3. Run `pytest tests/agent/cli/commands/test_workflow_profile_injection.py -v` — all must FAIL.

### Subtask T022 – Implement `_render_profile_context()`

- **Purpose**: Core function that reads WP frontmatter, resolves the profile, and returns a formatted markdown fragment.
- **Files**: `src/specify_cli/cli/commands/agent/workflow.py`
- **Steps**:
  1. Read lines 114-122 of `workflow.py` for the `_render_constitution_context()` pattern.
  2. Add `_render_profile_context()` after the existing function:
     ```python
     def _render_profile_context(
         repo_root: Path,
         wp_frontmatter: dict,
         allow_missing: bool = False,
     ) -> str:
         """Render agent profile identity fragment for implement prompt.

         Returns an empty string if:
         - Profile is a sentinel (HiC WP)
         - Profile not found and allow_missing=True (warning emitted)

         Raises typer.Exit(1) if:
         - Explicit profile is set and cannot be resolved and allow_missing=False
         """
         from doctrine.agent_profiles.repository import AgentProfileRepository

         agent_profile_id = extract_scalar(wp_frontmatter, "agent_profile") or "generic-agent"
         explicit = extract_scalar(wp_frontmatter, "agent_profile") is not None

         try:
             repo = AgentProfileRepository(repo_root=repo_root)
             profile = repo.resolve_profile(agent_profile_id)
         except (KeyError, FileNotFoundError):
             if explicit and not allow_missing:
                 typer.echo(
                     f"Error: agent_profile '{agent_profile_id}' cannot be resolved. "
                     "Pass --allow-missing-profile to degrade to a warning.",
                     err=True,
                 )
                 raise typer.Exit(1)
             typer.echo(
                 f"⚠️  Profile '{agent_profile_id}' not found, proceeding without specialist identity.",
                 err=True,
             )
             return ""

         if profile.sentinel:
             typer.echo("Human-in-charge WP: no agent identity injected.", err=True)
             return ""

         # Render identity fragment
         directives = ", ".join(
             d.directive_id for d in profile.directive_references
         ) or "none"
         return (
             f"\n## Agent Identity\n\n"
             f"**Profile**: {profile.name} (`{profile.profile_id}`)\n"
             f"**Role**: {profile.role}\n"
             f"**Purpose**: {profile.purpose.strip()}\n"
             f"**Primary Focus**: {profile.specialization.primary_focus}\n"
             f"**Directives**: {directives}\n\n"
             f"{profile.initialization_declaration.strip()}\n"
         )
     ```
  3. Run `mypy` on the function and fix any type errors.

### Subtask T023 – Sentinel check and fallback logic (within T022)

- **Purpose**: The sentinel check and missing-profile fallback are part of `_render_profile_context()`. This subtask documents the logic clearly for review.
- **Files**: `src/specify_cli/cli/commands/agent/workflow.py` (same function as T022).
- **Logic matrix**:

  | `agent_profile` field | Resolved? | `sentinel`? | `allow_missing` | Result |
  |---|---|---|---|---|
  | Absent (default to generic-agent) | Yes | No | - | Inject identity |
  | Absent (generic-agent not found) | No | - | - | Warn, no injection |
  | Set → found | Yes | No | - | Inject identity |
  | Set → found | Yes | Yes (HiC) | - | No injection, HiC message |
  | Set → not found | No | - | False | Exit 1 (error) |
  | Set → not found | No | - | True | Warn, no injection |

- **Steps**: Verify the implementation from T022 matches this matrix exactly. Write a comment above the function referencing this table.

### Subtask T024 – Add `--allow-missing-profile` flag to implement command

- **Purpose**: Expose the flag so agents/users can opt into degraded behavior for unresolvable profiles.
- **Files**: `src/specify_cli/cli/commands/agent/workflow.py` (the `implement` command function, line ~356).
- **Steps**:
  1. Locate the `implement` command definition.
  2. Add the flag parameter:
     ```python
     allow_missing_profile: Annotated[bool, typer.Option(
         "--allow-missing-profile/--no-allow-missing-profile",
         help="When set, an unresolvable agent_profile degrades to a warning instead of an error.",
     )] = False,
     ```
  3. Pass `allow_missing=allow_missing_profile` to `_render_profile_context()` in T025.

### Subtask T025 – Wire profile context into implement prompt output

- **Purpose**: The profile fragment must be injected into the implement prompt output, alongside the constitution context.
- **Files**: `src/specify_cli/cli/commands/agent/workflow.py` (inside the `implement` command body).
- **Steps**:
  1. Locate the constitution context injection at approximately line 576: `lines.append(_render_constitution_context(repo_root, "implement"))`.
  2. Immediately after that line, inject the profile context:
     ```python
     profile_fragment = _render_profile_context(repo_root, wp.frontmatter, allow_missing=allow_missing_profile)
     if profile_fragment:
         lines.append(profile_fragment)
     ```
  3. Ensure `wp.frontmatter` is the correct parsed frontmatter dict at that point in the function. If the variable name is different, use the correct one.
  4. Run `pytest tests/agent/cli/commands/test_workflow_profile_injection.py -v` — all 5 tests should now pass (green).
  5. Run `pytest tests/ -x` — full suite must pass.

## Test Strategy

```bash
# ATDD acceptance tests
rtk test pytest tests/agent/cli/commands/test_workflow_profile_injection.py -v

# Full suite regression
rtk test pytest tests/ -x

# Coverage gate (90%+ on new modules — constitution requirement)
rtk test pytest tests/ --cov=specify_cli --cov=doctrine --cov=constitution --cov-fail-under=90 -q

# Type check
mypy --strict src/specify_cli/cli/commands/agent/workflow.py

# Lint
rtk ruff check src/specify_cli/cli/commands/agent/workflow.py
```

## Risks & Mitigations

- **`AgentProfileRepository` instantiation path**: Verify the correct import path. It may be `from doctrine.agent_profiles.repository import AgentProfileRepository` or `from specify_cli.doctrine.agent_profiles...` depending on packaging. Check existing imports in `workflow.py`.
- **Performance**: NFR-002 requires ≤500ms. Profile YAML parsing should be well under that. If performance is a concern, instantiate the repo once per command invocation (not per function call).
- **WP frontmatter variable**: In the implement command body, the WP object may be `wp_obj`, `wp`, or similar. Read the existing code carefully before adding `wp.frontmatter` reference.

## Review Guidance

- Run implement on a WP with `agent_profile: implementer` and confirm "Agent Identity" section appears in output.
- Run on a HiC WP and confirm "Human-in-charge WP: no agent identity injected." appears and NO identity section is in the output.
- Run on a WP with bogus `agent_profile` — confirm exit 1 without `--allow-missing-profile`, and exit 0 with warning with `--allow-missing-profile`.

## Activity Log

- 2026-03-22T11:50:00Z – system – lane=planned – Prompt created.
