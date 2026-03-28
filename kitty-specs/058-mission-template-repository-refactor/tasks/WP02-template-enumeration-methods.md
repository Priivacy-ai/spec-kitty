---
work_package_id: WP02
title: Template + Enumeration Public Methods
lane: "doing"
dependencies: [WP01]
requirement_refs:
- FR-002
- FR-003
- FR-006
- FR-007
- FR-008
planning_base_branch: feature/agent-profile-implementation
merge_target_branch: feature/agent-profile-implementation
branch_strategy: Planning artifacts for this feature were generated on feature/agent-profile-implementation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/agent-profile-implementation unless the human explicitly redirects the landing branch.
base_branch: 058-mission-template-repository-refactor-WP01
base_commit: ae43d3dbd44e490e23faa97dce25fff9c293f7ea
created_at: '2026-03-28T05:27:38.951687+00:00'
subtasks:
- T006
- T007
- T008
- T009
phase: Phase 1 - New API Foundation
assignee: ''
agent: ''
shell_pid: "19021"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-03-27T04:37:32Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent_profile: implementer
---

# Work Package Prompt: WP02 – Template + Enumeration Public Methods

## Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback and begin addressing it, update `review_status: acknowledged` in the frontmatter.

---

## Review Feedback

> **Populated by `/spec-kitty.review`**

*[This section is empty initially.]*

---

## Markdown Formatting

Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`, ````bash`

---

## Objectives & Success Criteria

1. `get_command_template(mission, name)` returns `TemplateResult | None` with correct content
2. `get_content_template(mission, name)` returns `TemplateResult | None` with correct content
3. `list_command_templates(mission)` returns sorted `list[str]` of names (without .md extension)
4. `list_content_templates(mission)` returns sorted `list[str]` of filenames (with extension)
5. All methods return `None` / empty list for nonexistent missions or templates
6. Origin labels follow the convention: `"doctrine/<mission>/<asset-type>/<name>"`

**Success gate**: Manual smoke test -- `MissionTemplateRepository.default().get_command_template("software-dev", "implement")` returns non-empty `TemplateResult`.

## Context & Constraints

- **Contract**: `kitty-specs/058-mission-template-repository-refactor/contracts/mission-template-repository.md`
- **Prerequisite**: WP01 must be complete (class renamed, value objects exist, `_*_path()` methods exist)
- **Constraint NFR-003**: No caching -- each call reads fresh from disk
- **Pattern**: Each public method calls the corresponding private `_*_path()`, returns `None` if path is `None`, otherwise reads the file and wraps in `TemplateResult`

## Branch Strategy

- **Strategy**: workspace-per-WP
- **Planning base branch**: feature/agent-profile-implementation
- **Merge target branch**: feature/agent-profile-implementation

**Implementation command**: `spec-kitty implement WP02 --base WP01`

## Subtasks & Detailed Guidance

### Subtask T006 – Add get_command_template() public method

- **Purpose**: Primary public API for reading command template content. Replaces the old `get_command_template()` that returned `Path`.
- **Steps**:
  1. Add method to `MissionTemplateRepository` in `repository.py`:
     ```python
     def get_command_template(self, mission: str, name: str) -> TemplateResult | None:
         """Read a command template's content from doctrine assets.

         Looks for ``<missions_root>/<mission>/command-templates/<name>.md``.

         Args:
             mission: Mission name (e.g. ``"software-dev"``).
             name: Template name without ``.md`` extension (e.g. ``"implement"``).

         Returns:
             TemplateResult with content and origin, or ``None`` if not found.
         """
         path = self._command_template_path(mission, name)
         if path is None:
             return None
         try:
             content = path.read_text(encoding="utf-8")
             origin = f"doctrine/{mission}/command-templates/{name}.md"
             return TemplateResult(content=content, origin=origin)
         except (OSError, UnicodeDecodeError):
             return None
     ```
  2. Note: the `tier` parameter defaults to `None` in `TemplateResult.__init__` -- correct for doctrine-level lookups
- **Files**: `src/doctrine/missions/repository.py`
- **Parallel?**: Yes, independent of T007-T009

### Subtask T007 – Add get_content_template() public method

- **Purpose**: Public API for reading content templates (spec-template.md, plan-template.md, etc.).
- **Steps**:
  1. Add method to `MissionTemplateRepository`:
     ```python
     def get_content_template(self, mission: str, name: str) -> TemplateResult | None:
         """Read a content template's content from doctrine assets.

         Looks for ``<missions_root>/<mission>/templates/<name>``.

         Args:
             mission: Mission name.
             name: Template filename with extension (e.g. ``"spec-template.md"``).

         Returns:
             TemplateResult with content and origin, or ``None`` if not found.
         """
         path = self._content_template_path(mission, name)
         if path is None:
             return None
         try:
             content = path.read_text(encoding="utf-8")
             origin = f"doctrine/{mission}/templates/{name}"
             return TemplateResult(content=content, origin=origin)
         except (OSError, UnicodeDecodeError):
             return None
     ```
- **Files**: `src/doctrine/missions/repository.py`
- **Parallel?**: Yes, independent of T006, T008, T009

### Subtask T008 – Add list_command_templates() method

- **Purpose**: Enumerate all command templates for a mission. Replaces manual directory listing in `show_origin.py`.
- **Steps**:
  1. Add method to `MissionTemplateRepository`:
     ```python
     def list_command_templates(self, mission: str) -> list[str]:
         """Return names of all command templates for a mission.

         Args:
             mission: Mission name (e.g. ``"software-dev"``).

         Returns:
             Sorted list of template names WITHOUT ``.md`` extension
             (e.g. ``["implement", "plan", "specify", "tasks"]``).
             Empty list if mission or command-templates dir doesn't exist.
         """
         cmd_dir = self._root / mission / "command-templates"
         if not cmd_dir.is_dir():
             return []
         return sorted(
             p.stem for p in cmd_dir.iterdir()
             if p.is_file() and p.suffix == ".md"
         )
     ```
  2. Note: Returns stems (without `.md`) to match the `name` parameter convention used by `get_command_template()`
- **Files**: `src/doctrine/missions/repository.py`
- **Parallel?**: Yes

### Subtask T009 – Add list_content_templates() method

- **Purpose**: Enumerate all content templates for a mission. Replaces manual directory listing in `show_origin.py`.
- **Steps**:
  1. Add method to `MissionTemplateRepository`:
     ```python
     def list_content_templates(self, mission: str) -> list[str]:
         """Return filenames of all content templates for a mission.

         Args:
             mission: Mission name.

         Returns:
             Sorted list of template filenames WITH extension
             (e.g. ``["plan-template.md", "spec-template.md"]``).
             Empty list if mission or templates dir doesn't exist.
         """
         tpl_dir = self._root / mission / "templates"
         if not tpl_dir.is_dir():
             return []
         return sorted(
             p.name for p in tpl_dir.iterdir()
             if p.is_file()
         )
     ```
  2. Note: Returns full filenames (with extension) to match the `name` parameter convention used by `get_content_template()`
  3. Consider: Should README.md files be excluded? The `templates/` directory has a `README.md` that is metadata, not a content template. If so, add a filter: `and p.name != "README.md"`
- **Files**: `src/doctrine/missions/repository.py`
- **Parallel?**: Yes

## Test Strategy

After implementing all 4 methods, verify with a quick smoke test:
```bash
source .venv/bin/activate && python -c "
from doctrine.missions import MissionTemplateRepository
repo = MissionTemplateRepository.default()
# Test get_command_template
result = repo.get_command_template('software-dev', 'implement')
assert result is not None, 'implement template not found'
assert len(result.content) > 0, 'empty content'
print(f'get_command_template: {result}')
# Test get_content_template
result = repo.get_content_template('software-dev', 'spec-template.md')
assert result is not None, 'spec-template not found'
print(f'get_content_template: {result}')
# Test list_command_templates
names = repo.list_command_templates('software-dev')
assert 'implement' in names, f'implement not in {names}'
print(f'list_command_templates: {names}')
# Test list_content_templates
names = repo.list_content_templates('software-dev')
assert 'spec-template.md' in names, f'spec-template.md not in {names}'
print(f'list_content_templates: {names}')
# Test None returns
assert repo.get_command_template('nonexistent', 'implement') is None
assert repo.list_command_templates('nonexistent') == []
print('All smoke tests passed!')
"
```

Also run:
```bash
source .venv/bin/activate && .venv/bin/python -m pytest tests/doctrine/missions/ -v
```

## Risks & Mitigations

1. **README.md in templates directory**: The `templates/` dir may contain `README.md` which is metadata, not a template. Consider filtering it out in `list_content_templates()`. Check actual directory contents.
2. **File encoding issues**: All doctrine assets should be UTF-8, but the try/except handles `UnicodeDecodeError` gracefully.

## Review Guidance

- Verify each method follows the pattern: call `_*_path()` → check None → read file → wrap in `TemplateResult`
- Verify origin label format matches the contract convention
- Verify `list_*` methods return correct format (stems vs. full names)
- Verify `None` returns for nonexistent inputs
- Run the smoke test above

## Activity Log

- 2026-03-27T04:37:32Z – system – lane=planned – Prompt created.
