---
work_package_id: WP01
title: Create MissionTemplateRepository Class
lane: planned
dependencies: []
subtasks:
- T001
- T002
- T003
phase: Phase 1 - Foundation
assignee: ''
agent: ''
shell_pid: ''
review_status: ''
reviewed_by: ''
review_feedback: ''
planning_base_branch: feature/agent-profile-implementation
merge_target_branch: feature/agent-profile-implementation
branch_strategy: Work is done on feature/agent-profile-implementation targeting PR #305.
history:
- timestamp: '2026-03-26T07:55:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated for mission-template-repository-refactor
---

# Work Package Prompt: WP01 - Create MissionTemplateRepository Class

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

- Create `src/doctrine/missions/template_repository.py` with the full `MissionTemplateRepository` API
- Implement doctrine-level static methods: `get_command_template()`, `get_content_template()`, `list_command_templates()`, `list_content_templates()`, `missions_root()`
- Implement project-aware static methods: `resolve_command_template()`, `resolve_content_template()`
- Export `MissionTemplateRepository` from `src/doctrine/missions/__init__.py`

**Success**: `MissionTemplateRepository.get_command_template("software-dev", "implement")` returns a valid `Path` to the bundled template. `MissionTemplateRepository.resolve_command_template("software-dev", "implement")` also works and falls back to doctrine defaults when no project context is provided.

## Context & Constraints

- **Spec reference**: `kitty-specs/058-mission-template-repository-refactor/spec.md` - Proposed API section
- **Circular import constraint**: `doctrine` package must NOT import `specify_cli` at module level. Project-aware methods (`resolve_*`) must use lazy imports inside the method body
- **Existing patterns**: `MissionRepository` at `src/doctrine/missions/repository.py` provides the doctrine-level pattern. `CentralTemplateRepository` at `src/doctrine/templates/repository.py` is a sibling example
- **5-tier resolver**: `src/specify_cli/runtime/resolver.py` contains the `resolve_template()` implementation that project-aware methods delegate to

## Detailed Steps

### T001: Create template_repository.py

Create `src/doctrine/missions/template_repository.py` with:

```python
class MissionTemplateRepository:
    """Single entry point for mission-scoped template resolution."""

    @staticmethod
    def get_command_template(mission: str, name: str) -> Path | None:
        """Get a command template from doctrine (tier 5 only).
        Looks for doctrine/missions/<mission>/command-templates/<name>.md
        Returns Path if exists, None otherwise.
        """

    @staticmethod
    def get_content_template(mission: str, name: str) -> Path | None:
        """Get a content template from doctrine (tier 5 only).
        Looks for doctrine/missions/<mission>/templates/<name>
        Returns Path if exists, None otherwise.
        """

    @staticmethod
    def list_command_templates(mission: str) -> list[str]:
        """List command template names (without .md extension) for a mission.
        Returns sorted list. Empty list if mission doesn't exist.
        """

    @staticmethod
    def list_content_templates(mission: str) -> list[str]:
        """List content template filenames for a mission.
        Returns sorted list. Empty list if mission doesn't exist.
        """

    @staticmethod
    def missions_root() -> Path:
        """Root path for all doctrine mission assets.
        Delegates to MissionRepository.default_missions_root().
        """

    @staticmethod
    def resolve_command_template(
        mission: str, name: str, project_dir: Path | None = None
    ) -> Path:
        """Resolve through 5-tier override chain.
        If project_dir is None, falls back to doctrine default.
        Raises FileNotFoundError if not found at any tier.
        Uses lazy import of specify_cli.runtime.resolver.
        """

    @staticmethod
    def resolve_content_template(
        mission: str, name: str, project_dir: Path | None = None
    ) -> Path:
        """Resolve content template through 5-tier override chain."""
```

Key implementation details:
- Use `MissionRepository.default_missions_root()` internally for doctrine-level methods
- Lazy-import `specify_cli.runtime.resolver` only in `resolve_*` methods
- `list_command_templates` strips `.md` extension from filenames
- `list_content_templates` keeps full filenames (consistent with `get_content_template` signature)

### T002: Export from __init__.py

Add `MissionTemplateRepository` to `src/doctrine/missions/__init__.py` exports.

### T003: Verify no circular imports

Run a quick smoke test:
```python
from doctrine.missions import MissionTemplateRepository
MissionTemplateRepository.get_command_template("software-dev", "implement")
```

Ensure no `ImportError` at module level.

## Verification

```bash
source .venv/bin/activate
python -c "from doctrine.missions import MissionTemplateRepository; print(MissionTemplateRepository.get_command_template('software-dev', 'implement'))"
python -c "from doctrine.missions import MissionTemplateRepository; print(MissionTemplateRepository.list_command_templates('software-dev'))"
python -c "from doctrine.missions import MissionTemplateRepository; print(MissionTemplateRepository.missions_root())"
```

All three should produce valid output without errors.
