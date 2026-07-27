# Research: Doctrine Stack Init and Profile Integration

**Feature**: 057-doctrine-stack-init-and-profile-integration
**Date**: 2026-03-20

## R1: Profile Inheritance Merge Semantics

**Decision**: List fields merge by default (union, no duplicates). `excluding` key supports both field-level and value-level exclusion.

**Rationale**: Merge-by-default aligns with the inheritance metaphor — a child specialist *adds* capabilities to a parent role, not replaces them. The `excluding` mechanism provides escape hatches for profiles that need to *drop* inherited governance (e.g., a "lightweight" profile that removes heavy directives).

**Alternatives considered**:
- Replace-by-default: Simpler, but forces children to redeclare all parent values. Violates DRY and makes parent changes invisible to children.
- Config-per-field: Maximum flexibility, but excessive schema complexity for a rarely-needed feature.

**Implementation notes**:
- `AgentProfileRepository.resolve_profile()` (line 432-487 in `repository.py`) currently uses "child replaces parent" for lists. Must change to union merge.
- `excluding` field added to `AgentProfile` model. Two forms:
  - Field-level: `excluding: [directives, canonical_verbs]` — removes entire inherited field
  - Value-level: `excluding: {directives: [DIRECTIVE_010]}` — removes specific items from merged list
- Exclusion of nonexistent values is silently ignored (no error).
- Cycle detection already exists in `validate_hierarchy()` (line 357-398). Verify it runs during `resolve_profile()`, not just during explicit validation calls.

## R2: `--feature` → `--mission` Rename Pattern

**Decision**: Shared utility function `resolve_mission_or_feature()` handles all flag resolution logic. Each of the 16 commands delegates to this function.

**Rationale**: Centralizes deprecation logic. Prevents inconsistent warning messages or missing alias handling across commands.

**Alternatives considered**:
- Per-command inline logic: Simpler per file, but 16 copies of deprecation logic. Maintenance nightmare.
- Typer callback/middleware: Typer doesn't support global option middleware cleanly. Would require custom framework extension.

**Implementation notes**:
- 16 commands identified with `--feature` flag (see plan.md Project Structure)
- Pattern per command:
  ```python
  def my_command(
      mission: Optional[str] = typer.Option(None, "--mission", help="Mission slug"),
      feature: Optional[str] = typer.Option(None, "--feature", hidden=True, help="Deprecated: use --mission"),
  ):
      resolved = resolve_mission_or_feature(mission, feature)
  ```
- Deprecation warning uses `rich.console.Console().print()` with `[yellow]` styling (consistent with existing warnings)
- Community feedback (issue #241 comment): Users also type `--spec` expecting it to work. Out of scope for this feature but noted.

## R3: Init Doctrine Integration Points

**Decision**: Insert doctrine stack choice after `.kittify/constitution/` directory creation (line 188 in `init.py`). Delegate to existing `constitution interview` and `constitution generate` commands.

**Rationale**: Init orchestrates, doesn't reimplement. The existing constitution CLI (C-002) must continue working independently.

**Alternatives considered**:
- Inline interview logic in init: Violates SRP. Would duplicate `interview.py` logic.
- Separate post-init command: Current state (disconnected step users must discover). Explicitly rejected by spec.

**Implementation notes**:
- `_prepare_project_minimal()` already creates `.kittify/constitution/` directory
- Insertion point: after skeleton creation, before agent asset generation
- "Accept defaults" path: load `src/doctrine/constitution/defaults.yaml`, pass selections to `constitution generate`
- "Configure manually" path: prompt for depth (minimal/comprehensive), delegate to `constitution interview` with depth parameter
- Skip logic: check if `.kittify/constitution/constitution.md` exists before prompting
- `--non-interactive` flag: apply defaults automatically, no prompt

## R4: Constitution Defaults File Format

**Decision**: YAML file at `src/doctrine/constitution/defaults.yaml` with predefined selections for paradigms, directives, and tools.

**Rationale**: Versioned with the doctrine package. Can be updated as new directives ship. Overridable by project-level constitution without code changes.

**Implementation notes**:
- Format mirrors the structure `constitution generate` expects as input
- Default selections should include all shipped directives that are broadly applicable (not role-specific)
- Tools section populated from existing tool registry (`git`, `python`, `pytest`, `ruff`, `mypy`, `spec-kitty`)
- Paradigm selections: default to shipped paradigms (e.g., `test-first`)

## R5: Workflow Profile Injection Pattern

**Decision**: Follow `_render_constitution_context()` pattern. New function `_render_profile_context()` in `workflow.py`.

**Rationale**: Proven pattern already in production. Constitution context and profile context are complementary governance layers injected at the same point.

**Implementation notes**:
- Read `agent_profile` from WP frontmatter using existing ruamel.yaml parsing
- Default to `generic-agent` when field absent
- Resolve via `AgentProfileRepository.resolve_profile(profile_id)`
- Render markdown fragment with: name, role, purpose, specialization (primary focus, avoidance boundary), directive references, initialization declaration
- Inject into prompt after constitution context (profile specializes within governance)
- Warning path: catch `ProfileNotFoundError` (or equivalent), emit warning, return empty string
- Performance: resolution + rendering must complete in ≤500ms (NFR-002). Profile YAML files are small; repository caches loaded profiles in memory.
