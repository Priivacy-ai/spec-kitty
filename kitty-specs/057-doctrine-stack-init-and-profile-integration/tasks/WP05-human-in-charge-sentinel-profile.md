---
work_package_id: WP05
title: Human-in-Charge Sentinel Profile
lane: done
dependencies: [WP04]
requirement_refs:
- FR-007
- FR-008
planning_base_branch: feature/agent-profile-implementation
merge_target_branch: feature/agent-profile-implementation
branch_strategy: Planning artifacts for this feature were generated on feature/agent-profile-implementation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/agent-profile-implementation unless the human explicitly redirects the landing branch.
subtasks:
- T017
- T018
- T019
- T020
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

# Work Package Prompt: WP05 – Human-in-Charge Sentinel Profile

## ⚠️ IMPORTANT: Review Feedback Status

Check `review_status` field above. If `has_feedback`, address the Review Feedback section first.

---

## Review Feedback

*[Empty — populated by `/spec-kitty.review` if work is returned.]*

---

## Dependency Rebase Guidance

Depends on **WP04**. Profile model from WP03 must be stable; `_proposed/` directory must exist.

```bash
spec-kitty implement WP05 --base WP04
```

---

## Objectives & Success Criteria

- `AgentProfile` model has an optional `sentinel: bool = False` field.
- `src/doctrine/agent_profiles/_proposed/human-in-charge.agent.yaml` exists with `sentinel: true`.
- `AgentProfileRepository.get("human-in-charge").sentinel` is `True`.
- Profile does NOT exist in `shipped/` (C-001).
- `spec-kitty agent tasks status` renders a 👤 marker before the WP ID when a WP has `agent_profile: human-in-charge`.
- All ATDD acceptance scenarios pass.

## Context & Constraints

- **Plan**: `kitty-specs/057-doctrine-stack-init-and-profile-integration/plan.md` → WP-B2.5
- **Spec**: WP-B2.5 design, FR-007 (extends), FR-008, SC-002
- **Architecture**: The HiC sentinel is a workflow routing signal, not an agent identity. The workflow checks `profile.sentinel` and skips injection entirely. This check is implemented in WP06 (WP-B3), not here.
- **Start command**: `spec-kitty implement WP05 --base WP04`

## Subtasks & Detailed Guidance

### Subtask T017 – Write ATDD acceptance tests (tests first)

- **Purpose**: Tests must be red before any implementation. Covers the profile schema and the kanban rendering only — **not** the workflow injection skip (that is WP06 scope; see note below).
- **Files**: Create `tests/doctrine/test_human_in_charge_profile.py`.
- **Steps**:
  1. Write 4 test functions:
     - `test_human_in_charge_exists_in_proposed` — `AgentProfileRepository.get("human-in-charge")` returns a non-None profile.
     - `test_human_in_charge_sentinel_true` — `profile.sentinel is True`.
     - `test_human_in_charge_not_in_shipped` — profile YAML does NOT exist in `shipped/`.
     - `test_kanban_shows_hic_marker` — create a mock WP frontmatter with `agent_profile: human-in-charge`, invoke the kanban status renderer (or the relevant function), and assert the output contains `👤`.
  2. Run `pytest tests/doctrine/test_human_in_charge_profile.py -v` — all must FAIL (red).
- **⚠️ Scope boundary**: Do NOT write tests asserting that the implement workflow skips injection for sentinel profiles. That assertion lives in `test_workflow_profile_injection.py` under WP06 T021, because the inject-skip logic lives in `workflow.py` (WP06 scope). Writing it here would require touching WP06 code before WP05 is complete, violating phase isolation.

### Subtask T018 – Add `sentinel` field to `AgentProfile` model

- **Purpose**: The sentinel field allows workflows to distinguish between agent profiles (inject identity) and routing sentinels (skip injection).
- **Files**: `src/doctrine/agent_profiles/profile.py`
- **Steps**:
  1. In the `AgentProfile` class (line ~126), add after `specializes_from`:
     ```python
     sentinel: bool = Field(default=False, alias="sentinel")
     ```
  2. No existing profiles specify `sentinel: true`, so the default `False` means zero impact on all existing shipped profiles.
  3. Run `mypy src/doctrine/agent_profiles/profile.py` — no new errors.
  4. Run `pytest tests/doctrine/ -x` — all existing tests must pass.

### Subtask T019 – Create `human-in-charge.agent.yaml`

- **Purpose**: The sentinel profile YAML is the actual artifact that gets assigned in WP frontmatter.
- **Files**: Create `src/doctrine/agent_profiles/_proposed/human-in-charge.agent.yaml`.
- **Steps**:
  1. Create the YAML. Note that this is a minimal profile — no `specializes-from`, no `directive-references`, no `initialization-declaration` (the model must allow these to be empty/absent):
     ```yaml
     profile-id: "human-in-charge"
     name: "Human in Charge"
     description: "Workflow sentinel indicating this work package requires direct human execution. No agent identity is injected. The HIC remains accountable for the deliverable."
     schema-version: "1.0"
     role: implementer
     sentinel: true
     capabilities:
       - "Human judgment"
       - "Direct action"
     routing-priority: 100
     max-concurrent-tasks: 1

     context-sources:
       doctrine-layers: []
       directives: []

     purpose: |
       Signal that this work package is assigned to a human executor.
       No agent context injection occurs. The Human in Charge is responsible
       for the deliverable and its quality.

     specialization:
       primary-focus: "Human execution — this WP requires direct human action or collaborative human-AI work"
       avoidance-boundary: "Fully automated execution without human oversight"

     collaboration:
       handoff-partners:
         - "reviewer"
       output-artifacts:
         - "Human-executed deliverable"
       canonical-verbs:
         - "approve"
         - "decide"
         - "execute"

     mode-defaults:
       - mode: "direct"
         default: true

     directive-references: []

     initialization-declaration: ""
     ```
  2. Validate YAML parses cleanly: `python -c "import yaml; yaml.safe_load(open('src/doctrine/agent_profiles/_proposed/human-in-charge.agent.yaml'))"`.
  3. If schema validation requires non-empty `directive-references`, add a placeholder note comment or adjust the model to allow empty lists (it should already allow them since `default_factory=list`).

### Subtask T020 – Add 👤 kanban marker for HiC WPs

- **Purpose**: Humans scanning the kanban board need to immediately identify which WPs require human execution, not just AI execution.
- **Files**: `src/specify_cli/cli/commands/agent/status.py` (locate the kanban row rendering function).
- **Steps**:
  1. Read `src/specify_cli/cli/commands/agent/status.py`. Find where WP rows are rendered in the kanban display — look for where `wp_id` is formatted into a table cell or line.
  2. Identify the WP frontmatter parsing location. WP data comes from reading `tasks/*.md` files.
  3. For each WP row, check if `agent_profile` field is set in frontmatter. If so, attempt to resolve it via `AgentProfileRepository`:
     ```python
     def _get_hic_marker(agent_profile: str | None, repo_root: Path) -> str:
         """Return 👤 if the profile is a sentinel, else empty string."""
         if not agent_profile:
             return ""
         try:
             from doctrine.agent_profiles.repository import AgentProfileRepository
             repo = AgentProfileRepository(repo_root=repo_root)
             profile = repo.get(agent_profile)
             if profile and profile.sentinel:
                 return "👤 "
         except Exception:
             pass  # Degrade gracefully — missing profile doesn't break kanban
         return ""
     ```
  4. Prepend the marker to the WP ID display string in the kanban row:
     ```python
     marker = _get_hic_marker(wp_frontmatter.get("agent_profile"), repo_root)
     display_id = f"{marker}{wp_id}"
     ```
  5. Run `pytest tests/doctrine/test_human_in_charge_profile.py::test_kanban_shows_hic_marker -v` — should pass.
  6. Run `pytest tests/ -x` — all tests must pass.

## Test Strategy

```bash
# ATDD acceptance tests
rtk test pytest tests/doctrine/test_human_in_charge_profile.py -v

# Full suite regression
rtk test pytest tests/ -x

# Coverage gate (90%+ on new modules — constitution requirement)
rtk test pytest tests/ --cov=specify_cli --cov=doctrine --cov=constitution --cov-fail-under=90 -q

# Type check
mypy --strict src/doctrine/agent_profiles/profile.py src/specify_cli/cli/commands/agent/status.py

# Lint
rtk ruff check src/doctrine/agent_profiles/ src/specify_cli/cli/commands/agent/status.py
```

## Risks & Mitigations

- **Kanban resolution overhead**: `AgentProfileRepository` reads YAML files on every kanban render. If the kanban renders many WPs, this could be slow. Instantiate the repo once per kanban render, not per WP row. Pass `repo` as a parameter to `_get_hic_marker`.
- **Profile not found**: Degrade gracefully — if profile resolution fails, show WP without 👤 marker.
- **Empty directive-references**: If the schema validator rejects empty `directive-references`, add a comment in the YAML or patch the validator to accept the sentinel case.

## Review Guidance

- Set `agent_profile: human-in-charge` in any WP frontmatter and run `spec-kitty agent tasks status` — confirm 👤 appears.
- Confirm the profile is in `_proposed/`, not `shipped/`.
- Confirm `profile.sentinel` is `True` after `AgentProfileRepository.get("human-in-charge")`.

## Activity Log

- 2026-03-22T11:50:00Z – system – lane=planned – Prompt created.
