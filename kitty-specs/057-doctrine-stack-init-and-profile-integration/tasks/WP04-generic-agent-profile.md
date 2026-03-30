---
work_package_id: WP04
title: Generic-Agent Profile in `_proposed/`
lane: done
dependencies: [WP03]
requirement_refs:
- FR-011
- FR-012
planning_base_branch: feature/agent-profile-implementation
merge_target_branch: feature/agent-profile-implementation
branch_strategy: Planning artifacts for this feature were generated on feature/agent-profile-implementation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/agent-profile-implementation unless the human explicitly redirects the landing branch.
subtasks:
- T014
- T015
- T016
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
agent_profile: curator
---

# Work Package Prompt: WP04 – Generic-Agent Profile in `_proposed/`

## ⚠️ IMPORTANT: Review Feedback Status

Check `review_status` field above. If `has_feedback`, address the Review Feedback section first.

---

## Review Feedback

*[Empty — populated by `/spec-kitty.review` if work is returned.]*

---

## Dependency Rebase Guidance

Depends on **WP03**. Profile model changes from WP03 must be merged before this WP starts.

```bash
spec-kitty implement WP04 --base WP03
```

---

## Objectives & Success Criteria

- `src/doctrine/agent_profiles/_proposed/generic-agent.agent.yaml` exists.
- `AgentProfileRepository.get("generic-agent")` returns the profile without error.
- Profile references exactly DIRECTIVE_028 (one directive reference) — C-004 minimum satisfied.
- Profile does NOT exist in `shipped/` — C-001 governance gate respected.
- Schema validation passes (C-004).
- All 3 US-5 acceptance scenarios pass.
- Requirements FR-011, FR-012, C-001, C-004, SC-005 satisfied.

## Context & Constraints

- **Plan**: `kitty-specs/057-doctrine-stack-init-and-profile-integration/plan.md` → WP-B2
- **Spec**: US-5, FR-011, FR-012, C-001, C-004, SC-005
- **Governance**: This profile MUST stay in `_proposed/` — only HIC curation can promote it to `shipped/`. Do not create it in `shipped/`.
- **Start command**: `spec-kitty implement WP04 --base WP03`

## Subtasks & Detailed Guidance

### Subtask T014 – Write ATDD acceptance tests (tests first)

- **Purpose**: 3 US-5 acceptance scenarios must fail before the YAML is created.
- **Files**: Create `tests/doctrine/test_generic_agent_profile.py`.
- **Steps**:
  1. Read an existing profile test (e.g., `tests/doctrine/test_profile_context_template.py` if it exists, or any doctrine test) to understand the test setup pattern.
  2. Write 3 test functions:
     - `test_generic_agent_exists_in_proposed` — `AgentProfileRepository.get("generic-agent")` returns a non-None profile. Profile YAML lives in `_proposed/`.
     - `test_generic_agent_references_directive_028` — resolved profile's `directive_references` contains exactly one entry referencing DIRECTIVE_028.
     - `test_generic_agent_not_in_shipped` — `(repo_root / "src/doctrine/agent_profiles/shipped/generic-agent.agent.yaml").exists()` is False.
  3. Run `pytest tests/doctrine/test_generic_agent_profile.py -v` — all 3 must FAIL (red). The first two fail because the profile doesn't exist yet; the third passes immediately (absence test) but that's fine.

### Subtask T015 – Create `generic-agent.agent.yaml`

- **Purpose**: The `generic-agent` is the default profile for WPs without an explicit `agent_profile`. It must be a valid, schema-compliant root profile (no `specializes-from`).
- **Files**: Create `src/doctrine/agent_profiles/_proposed/generic-agent.agent.yaml`.
- **Steps**:
  1. Read an existing shipped profile (e.g., `src/doctrine/agent_profiles/shipped/implementer.agent.yaml`) to understand the expected YAML structure and required fields.
  2. Create the profile:
     ```yaml
     profile-id: "generic-agent"
     name: "Generic Agent"
     description: "General-purpose task execution profile. Used as the default when no specialist profile is assigned to a work package."
     schema-version: "1.0"
     role: implementer
     capabilities:
       - "General task execution"
       - "Code implementation"
       - "Documentation"
     routing-priority: 10
     max-concurrent-tasks: 5

     context-sources:
       doctrine-layers:
         - "directives"
         - "toolguides"
       directives:
         - "DIRECTIVE_028"

     purpose: |
       Execute assigned work packages faithfully and completely, applying efficient local tooling
       and respecting the project's governance boundaries. Serve as the baseline agent identity
       when no specialist role has been assigned.

     specialization:
       primary-focus: "General-purpose task execution across all work package types"
       avoidance-boundary: "Architectural decisions that should be owned by a specialist profile (planner, architect, curator)"

     collaboration:
       handoff-partners:
         - "reviewer"
         - "planner"
       output-artifacts:
         - "Implemented work package"
         - "Updated lane status"
       canonical-verbs:
         - "implement"
         - "fix"
         - "create"
         - "update"

     mode-defaults:
       - mode: "implementation"
         default: true
       - mode: "review"
         default: false

     directive-references:
       - directive-id: "DIRECTIVE_028"
         directive-name: "Efficient Local Tooling"
         rationale: "All agents must use low-noise, efficient tooling for repository operations as a baseline governance requirement."

     initialization-declaration: |
       I am a generic agent operating under the baseline governance of this project.
       I will execute the assigned work package faithfully, using efficient local tooling (DIRECTIVE_028),
       and respecting the project's architectural boundaries. I have no specialist identity beyond
       the project constitution.
     ```
  3. Verify the YAML is valid: `python -c "import yaml; yaml.safe_load(open('src/doctrine/agent_profiles/_proposed/generic-agent.agent.yaml'))"`.
  4. Create the `_proposed/` directory if it does not exist: `mkdir -p src/doctrine/agent_profiles/_proposed/`.

### Subtask T016 – Verify schema validation

- **Purpose**: Confirm the profile passes the existing `AgentProfileRepository` validation (C-004).
- **Files**: No file changes — verification only.
- **Steps**:
  1. In a Python REPL or quick test script:
     ```python
     from pathlib import Path
     from doctrine.agent_profiles.repository import AgentProfileRepository

     repo = AgentProfileRepository(repo_root=Path("."))
     profile = repo.get("generic-agent")
     assert profile is not None, "generic-agent not found"
     assert len(profile.directive_references) >= 1, "Missing directive reference"
     print("Schema OK:", profile.name, "| Directives:", [d.directive_id for d in profile.directive_references])
     ```
  2. Run `pytest tests/doctrine/test_generic_agent_profile.py -v` — all 3 tests should now pass (green).
  3. Run `pytest tests/doctrine/ -x` — existing tests must still pass.

## Test Strategy

```bash
# ATDD acceptance tests
rtk test pytest tests/doctrine/test_generic_agent_profile.py -v

# Full doctrine suite (regression)
rtk test pytest tests/doctrine/ -x

# Coverage gate (90%+ on new test module)
rtk test pytest tests/doctrine/test_generic_agent_profile.py --cov=doctrine.agent_profiles --cov-fail-under=90

# Type check (strict)
mypy --strict src/doctrine/agent_profiles/profile.py src/doctrine/agent_profiles/repository.py

# Lint check on new YAML (Python parse)
python -c "import yaml; yaml.safe_load(open('src/doctrine/agent_profiles/_proposed/generic-agent.agent.yaml'))"
```

## Risks & Mitigations

- **Required fields missing**: The AgentProfile Pydantic model has required fields (`purpose`, `specialization`, `name`, `profile-id`). Check `profile.py` for the full list and ensure the YAML covers all of them.
- **Schema version drift**: Use `schema-version: "1.0"` matching shipped profiles.
- **DIRECTIVE_028 ID format**: Check an existing profile's `directive-references` section for the exact format expected (ID string format, required subfields).

## Review Guidance

- Confirm `generic-agent.agent.yaml` is in `_proposed/` not `shipped/`.
- Run `AgentProfileRepository.get("generic-agent")` manually and verify the returned object has the expected fields.
- Confirm exactly 1 directive reference (DIRECTIVE_028).

## Activity Log

- 2026-03-22T11:50:00Z – system – lane=planned – Prompt created.
