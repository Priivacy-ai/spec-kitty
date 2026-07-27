# API Contract: MissionTemplateRepository

**Mission**: 058 - Mission Repository Encapsulation
**Date**: 2026-03-27
**Status**: Draft
**Module**: `src/doctrine/missions/repository.py`

## Overview

`MissionTemplateRepository` (renamed from `MissionRepository`) is the single authoritative API for all mission asset access. Public methods return content or structured data via value objects. Private `_*_path()` methods return filesystem `Path` objects for internal callers only.

## Value Objects

### `TemplateResult`

Returned by all template-reading and guidelines-reading methods. Dict-backed with named accessor methods.

```python
class TemplateResult:
    """Value object wrapping template content with origin metadata.

    Constructed internally by MissionTemplateRepository.
    Consumers should not instantiate directly.
    """

    __slots__ = ("_data",)

    def __init__(self, content: str, origin: str, tier: ResolutionTier | None = None) -> None:
        self._data: dict[str, Any] = {
            "content": content,
            "origin": origin,
            "tier": tier,
        }

    @property
    def content(self) -> str:
        """Raw template text (UTF-8)."""
        return self._data["content"]

    @property
    def origin(self) -> str:
        """Human-readable origin label.

        Examples:
            "doctrine/software-dev/command-templates/implement.md"
            "override/software-dev/command-templates/implement.md"
            "doctrine/software-dev/actions/implement/guidelines.md"
        """
        return self._data["origin"]

    @property
    def tier(self) -> ResolutionTier | None:
        """Resolution tier (only set for resolve_* methods).

        None for doctrine-level lookups (get_command_template, etc.)
        that don't go through the 5-tier resolver.
        """
        return self._data["tier"]

    def __repr__(self) -> str:
        return f"TemplateResult(origin={self.origin!r}, tier={self.tier})"
```

**Invariants**:
- `content` is always a non-empty `str` (methods return `None` instead of an empty `TemplateResult`)
- `origin` is always a human-readable label, never a filesystem path
- `tier` is `None` for doctrine-level lookups, a `ResolutionTier` value for `resolve_*` calls

### `ConfigResult`

Returned by all YAML-reading methods. Dict-backed with named accessor methods.

```python
class ConfigResult:
    """Value object wrapping parsed YAML config with origin metadata.

    Constructed internally by MissionTemplateRepository.
    Consumers should not instantiate directly.
    """

    __slots__ = ("_data",)

    def __init__(self, content: str, origin: str, parsed: dict | list) -> None:
        self._data: dict[str, Any] = {
            "content": content,
            "origin": origin,
            "parsed": parsed,
        }

    @property
    def content(self) -> str:
        """Raw YAML text (UTF-8)."""
        return self._data["content"]

    @property
    def origin(self) -> str:
        """Human-readable origin label.

        Examples:
            "doctrine/software-dev/mission.yaml"
            "doctrine/software-dev/expected-artifacts.yaml"
            "doctrine/software-dev/actions/implement/index.yaml"
        """
        return self._data["origin"]

    @property
    def parsed(self) -> dict | list:
        """Pre-parsed YAML data.

        Parsed using ruamel.yaml YAML(typ="safe").
        Return type depends on the YAML document structure:
        - mission.yaml -> dict
        - expected-artifacts.yaml -> dict or list
        - action index.yaml -> dict
        """
        return self._data["parsed"]

    def __repr__(self) -> str:
        return f"ConfigResult(origin={self.origin!r})"
```

**Invariants**:
- `content` is always the raw YAML text (non-empty)
- `parsed` is always the result of `YAML(typ="safe").load()` -- never `yaml.unsafe_load()`
- Methods return `None` instead of a `ConfigResult` with empty/invalid data

## Class: `MissionTemplateRepository`

### Constructor

```python
class MissionTemplateRepository:
    """Single authority for mission asset access.

    All public methods return content (via TemplateResult or ConfigResult)
    or enumeration lists. Private _*_path() methods return Path objects
    for internal callers that need filesystem access.
    """

    def __init__(self, missions_root: Path) -> None:
        """Initialize with a missions root directory.

        Args:
            missions_root: Root directory containing mission subdirectories.
                           Each subdirectory has command-templates/, templates/,
                           actions/, mission.yaml, etc.
        """
        self._root = missions_root
```

### Class Methods

```python
    @classmethod
    def default_missions_root(cls) -> Path:
        """Return the missions root bundled with the doctrine package.

        Uses importlib.resources so the path is valid both from editable
        installs and built wheels.

        Returns:
            Path to doctrine/missions/ package directory.
        """
```

```python
    @classmethod
    def default(cls) -> MissionTemplateRepository:
        """Return a repository instance for the doctrine-bundled missions.

        Convenience shortcut for MissionTemplateRepository(MissionTemplateRepository.default_missions_root()).

        Returns:
            MissionTemplateRepository instance pointed at doctrine package assets.
        """
```

### Enumeration Methods

```python
    def list_missions(self) -> list[str]:
        """Return names of all missions that contain a mission.yaml.

        Returns:
            Sorted list of mission directory names.
            Empty list if missions_root doesn't exist.
        """
```

```python
    def list_command_templates(self, mission: str) -> list[str]:
        """Return names of all command templates for a mission.

        Args:
            mission: Mission name (e.g. "software-dev").

        Returns:
            Sorted list of template names WITHOUT .md extension
            (e.g. ["implement", "plan", "specify", "tasks"]).
            Empty list if mission or command-templates/ dir doesn't exist.
        """
```

```python
    def list_content_templates(self, mission: str) -> list[str]:
        """Return filenames of all content templates for a mission.

        Args:
            mission: Mission name.

        Returns:
            Sorted list of template filenames WITH extension
            (e.g. ["plan-template.md", "spec-template.md"]).
            Empty list if mission or templates/ dir doesn't exist.
        """
```

### Template Methods (return `TemplateResult | None`)

```python
    def get_command_template(self, mission: str, name: str) -> TemplateResult | None:
        """Read a command template's content from doctrine assets.

        Looks for <missions_root>/<mission>/command-templates/<name>.md.

        Args:
            mission: Mission name (e.g. "software-dev").
            name: Template name without .md extension (e.g. "implement").

        Returns:
            TemplateResult with content and origin, or None if not found.
            The tier property is None (doctrine-level lookup).
        """
```

```python
    def get_content_template(self, mission: str, name: str) -> TemplateResult | None:
        """Read a content template's content from doctrine assets.

        Looks for <missions_root>/<mission>/templates/<name>.

        Args:
            mission: Mission name.
            name: Template filename with extension (e.g. "spec-template.md").

        Returns:
            TemplateResult with content and origin, or None if not found.
            The tier property is None (doctrine-level lookup).
        """
```

```python
    def resolve_command_template(
        self, mission: str, name: str, project_dir: Path | None = None
    ) -> TemplateResult:
        """Resolve a command template through the 5-tier override chain.

        Resolution order: OVERRIDE > LEGACY > GLOBAL_MISSION > GLOBAL > PACKAGE_DEFAULT.

        Uses lazy import of specify_cli.runtime.resolver to avoid circular
        dependencies at module load time.

        Args:
            mission: Mission name.
            name: Template name without .md extension.
            project_dir: Project root for override/legacy lookups.
                         If None, only GLOBAL and PACKAGE_DEFAULT tiers are checked.

        Returns:
            TemplateResult with content, origin, and tier.

        Raises:
            FileNotFoundError: If template not found at any tier.
        """
```

```python
    def resolve_content_template(
        self, mission: str, name: str, project_dir: Path | None = None
    ) -> TemplateResult:
        """Resolve a content template through the 5-tier override chain.

        Same resolution logic as resolve_command_template but for
        content templates (templates/ subdirectory).

        Args:
            mission: Mission name.
            name: Template filename with extension.
            project_dir: Project root for override/legacy lookups.

        Returns:
            TemplateResult with content, origin, and tier.

        Raises:
            FileNotFoundError: If template not found at any tier.
        """
```

### Config Methods (return `ConfigResult | None`)

```python
    def get_action_index(self, mission: str, action: str) -> ConfigResult | None:
        """Read and parse an action's index.yaml from doctrine assets.

        Looks for <missions_root>/<mission>/actions/<action>/index.yaml.
        Parsed using ruamel.yaml YAML(typ="safe").

        Args:
            mission: Mission name.
            action: Action name (e.g. "implement").

        Returns:
            ConfigResult with raw YAML text and parsed dict, or None if not found.
        """
```

```python
    def get_action_guidelines(self, mission: str, action: str) -> TemplateResult | None:
        """Read an action's guidelines.md from doctrine assets.

        Looks for <missions_root>/<mission>/actions/<action>/guidelines.md.

        Note: Returns TemplateResult (not ConfigResult) because guidelines
        are markdown content, not YAML config.

        Args:
            mission: Mission name.
            action: Action name.

        Returns:
            TemplateResult with content and origin, or None if not found.
        """
```

```python
    def get_mission_config(self, mission: str) -> ConfigResult | None:
        """Read and parse a mission's mission.yaml from doctrine assets.

        Args:
            mission: Mission name.

        Returns:
            ConfigResult with raw YAML text and parsed dict, or None if not found.
        """
```

```python
    def get_expected_artifacts(self, mission: str) -> ConfigResult | None:
        """Read and parse a mission's expected-artifacts.yaml.

        Args:
            mission: Mission name.

        Returns:
            ConfigResult with raw YAML text and parsed data, or None if not found.
        """
```

### Private Path Methods (return `Path | None`)

These methods are for internal callers only (resolver tier-5, bootstrap, template copying). They retain the current behavior of returning filesystem paths.

```python
    def _command_template_path(self, mission: str, name: str) -> Path | None:
        """Return path to <missions_root>/<mission>/command-templates/<name>.md.

        Args:
            mission: Mission name.
            name: Template name without .md extension.

        Returns:
            Path if file exists, else None.
        """
```

```python
    def _content_template_path(self, mission: str, name: str) -> Path | None:
        """Return path to <missions_root>/<mission>/templates/<name>.

        Args:
            mission: Mission name.
            name: Template filename with extension.

        Returns:
            Path if file exists, else None.
        """
```

```python
    def _action_index_path(self, mission: str, action: str) -> Path | None:
        """Return path to <missions_root>/<mission>/actions/<action>/index.yaml."""
```

```python
    def _action_guidelines_path(self, mission: str, action: str) -> Path | None:
        """Return path to <missions_root>/<mission>/actions/<action>/guidelines.md."""
```

```python
    def _mission_config_path(self, mission: str) -> Path | None:
        """Return path to <missions_root>/<mission>/mission.yaml."""
```

```python
    def _expected_artifacts_path(self, mission: str) -> Path | None:
        """Return path to <missions_root>/<mission>/expected-artifacts.yaml."""
```

```python
    @property
    def _missions_root(self) -> Path:
        """Return the missions root directory.

        For internal callers that need the root path (e.g., bootstrap bulk copy).
        """
        return self._root
```

## Backward Compatibility

### Alias

```python
# In doctrine/missions/__init__.py:
from .repository import MissionTemplateRepository

# Backward-compat alias for shipped migrations and external consumers
MissionRepository = MissionTemplateRepository
```

### Import Compatibility

| Old Import | After Rename | Works? |
|-----------|-------------|--------|
| `from doctrine.missions import MissionRepository` | Resolves to `MissionTemplateRepository` via alias | Yes |
| `from doctrine.missions.repository import MissionRepository` | Resolves to `MissionTemplateRepository` via alias in module | Yes |
| `MissionRepository(root).get_command_template(m, c)` | Method renamed to `_command_template_path()` -- **breaking for direct callers** | No* |
| `MissionRepository(root).list_missions()` | Unchanged | Yes |
| `MissionRepository.default_missions_root()` | Unchanged | Yes |

\* The old `get_command_template()` returned `Path | None`. The new `get_command_template()` returns `TemplateResult | None`. Callers that expected a `Path` must migrate to `_command_template_path()`. Since only 2 production files actually call repository methods (and both are rerouted in Phase 2), this is acceptable.

## Origin Label Convention

Origin labels follow the pattern `<source>/<mission>/<asset-type>/<name>`:

| Source | Example |
|--------|---------|
| Doctrine default | `"doctrine/software-dev/command-templates/implement.md"` |
| Project override | `"override/software-dev/command-templates/implement.md"` |
| Legacy project | `"legacy/software-dev/command-templates/implement.md"` |
| Global mission | `"global/software-dev/command-templates/implement.md"` |
| Global | `"global/command-templates/implement.md"` |

For `resolve_*` methods, the origin is derived from the `ResolutionTier`. For doctrine-level `get_*` methods, the origin always starts with `"doctrine/"`.

## Error Handling

| Scenario | Behavior |
|----------|----------|
| Mission doesn't exist | Return `None` (for `get_*`) or empty list (for `list_*`) |
| Template doesn't exist | Return `None` |
| YAML parse error | Return `None` with warning logged |
| File read error (permissions, encoding) | Return `None` with warning logged |
| `resolve_*` finds nothing at any tier | Raise `FileNotFoundError` |
| `missions_root` directory doesn't exist | Return `None` / empty list (no exception) |

## YAML Parsing Convention

All YAML parsing uses `ruamel.yaml`:

```python
from ruamel.yaml import YAML

yaml = YAML(typ="safe")
data = yaml.load(text)
```

Never use `yaml.load()` from stdlib or `yaml.unsafe_load()`. The `YAML(typ="safe")` matches the existing pattern in `action_index.py`.

## Thread Safety

`MissionTemplateRepository` instances are safe to share across threads for read operations. No internal mutable state is modified after construction. File reads are not cached -- each call reads fresh from disk (NFR-003 compliance).

## Testing Contract

New test module: `tests/doctrine/test_mission_template_repository.py`

### Required Test Categories

1. **Value object construction**: Verify `TemplateResult` and `ConfigResult` properties
2. **Doctrine-level reads**: All `get_*` methods against real doctrine assets
3. **None returns**: Nonexistent missions, templates, actions
4. **Enumeration**: `list_missions()`, `list_command_templates()`, `list_content_templates()`
5. **YAML parsing**: `get_action_index()`, `get_mission_config()`, `get_expected_artifacts()`
6. **Backward compat**: `MissionRepository` alias resolves correctly
7. **Resolver integration**: `resolve_*` methods (may require mock project dir)
8. **Edge cases**: Empty missions root, missing directories, malformed YAML

### Coverage Target

90%+ line coverage for all new code (constitution requirement).
