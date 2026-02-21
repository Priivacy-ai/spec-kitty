# Research: Agent Profile Domain Model

**Feature**: 047-agent-profile-domain-model
**Date**: 2026-02-16

## Decision 1: Modeling Approach — Frozen Dataclasses

**Decision**: Use `@dataclass(frozen=True)` with manual `to_dict()`/`from_dict()` classmethods.

**Rationale**: Consistency with the established status model pattern (feature 034). The codebase convention uses frozen dataclasses for domain entities (`StatusEvent`, `DoneEvidence`, `RepoEvidence`). While Pydantic (`>=2.0`, already a dependency) would reduce serialization boilerplate, dataclasses keep the domain model aligned with existing patterns and avoid dual-convention confusion.

**Alternatives considered**:

- Pydantic BaseModel — built-in validation/serialization/JSON Schema, but inconsistent with domain model convention
- Hybrid (Pydantic for complex types, dataclasses for simple) — would create confusion about which pattern to use when

## Decision 2: Package Distribution — Single Distribution

**Decision**: `src/doctrine/` is a subpackage within the `spec-kitty-cli` PyPI distribution. Add `"src/doctrine"` to `pyproject.toml` `[tool.hatch.build.targets.wheel] packages` list.

**Rationale**: Simplest distribution model during alpha. The zero-import boundary between `doctrine` and `specify_cli` is enforced by a CI test (AST-level import scan), not by package isolation. This provides the architectural benefit (loose coupling) without the operational cost (separate PyPI package, separate versioning, dependency edge).

**Alternatives considered**:

- Separate PyPI package `spec-kitty-doctrine` — true isolation but adds release complexity; no external consumers justify the overhead yet
- Namespace package within `specify_cli` (e.g., `specify_cli.doctrine`) — violates the conceptual separation; doctrine should not be "under" the CLI

**Implementation note**: `pyproject.toml` change:

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/specify_cli", "src/doctrine"]
```

## Decision 3: ToolConfig Rename Strategy — Alias-First

**Decision**: Create `tool_config.py` with new names, replace `agent_config.py` with a deprecated alias module, then iteratively update all 7 importing files with tests passing at each step.

**Rationale**: Alias-first approach ensures backward compatibility at every step. No single commit breaks imports. The alias module can be removed in a future version after downstream features (044, 045, 046) are implemented and any external consumers have migrated.

**Alternatives considered**:

- Big-bang rename in single commit — higher risk of breaking imports if any are missed
- New-name-only (keep AgentConfig forever) — perpetuates terminology conflation

**Files requiring import updates** (7 files):

1. `src/specify_cli/agent_utils/directories.py`
2. `src/specify_cli/orchestrator/scheduler.py` (2 import sites)
3. `src/specify_cli/upgrade/migrations/m_0_14_0_centralized_feature_detection.py`
4. `src/specify_cli/cli/commands/init.py`
5. `src/specify_cli/cli/commands/agent/config.py`
6. `src/specify_cli/orchestrator/monitor.py`
7. `src/specify_cli/orchestrator/config.py`

## Decision 4: Shipped Profile Format — Pure YAML (not Markdown)

**Decision**: Shipped profiles use `.agent.yaml` format (pure structured YAML), not the `.agent.md` Markdown format used in the doctrine reference repository.

**Rationale**: The doctrine reference repository uses Markdown (`.agent.md`) because it prioritizes human readability in a documentation context. Spec-kitty's internal profiles need machine-parseable structured data for the repository loader, hierarchy builder, and schema validator. YAML provides this without Markdown frontmatter parsing complexity.

**Alternatives considered**:

- `.agent.md` with YAML frontmatter + Markdown body — matches doctrine format but requires dual parsing (frontmatter extraction + Markdown section parsing). The 6 sections would need to be extracted from Markdown headings, which is fragile.
- `.agent.toml` — less common for config files in this codebase; YAML is the established format

**Migration from doctrine_ref**: Each doctrine `.agent.md` profile is manually adapted to `.agent.yaml` during WP06 (reference profile catalog). The adaptation extracts frontmatter fields and converts Markdown sections to YAML keys.

## Decision 5: `importlib.resources` for Shipped Profiles

**Decision**: Use `importlib.resources` (Python 3.11+) to locate shipped profile YAML files within the installed package, rather than `__file__`-relative paths.

**Rationale**: `importlib.resources` is the standard way to access package data files in installed packages (wheels, editable installs). It handles all installation modes (wheel, sdist, editable) and is the recommended approach since Python 3.9+.

**Alternatives considered**:

- `Path(__file__).parent / "agents/"` — works for development but may break in zipped wheel distributions
- `pkg_resources` — deprecated, slower, heavier dependency

**Implementation pattern**:

```python
from importlib.resources import files

def _shipped_profiles_dir() -> Path:
    return files("doctrine") / "agents"
```

## Decision 6: Custom Role Support

**Decision**: The `Role` field accepts both `Role` enum values and arbitrary strings. The enum provides the controlled vocabulary; custom strings allow extension.

**Rationale**: The spec requires a controlled vocabulary (`implementer`, `reviewer`, `architect`, `planner`, `researcher`, `curator`, `manager`) but also allows "custom roles" (FR-2.5). Using a union type `Role | str` provides type safety for known roles while allowing extension.

**Implementation approach**: Parse the role field as a string. If it matches a known `Role` enum value, convert it. Otherwise, keep it as a string. Validation warns on unknown roles but does not reject them.

## Decision 7: JSON Schema Location

**Decision**: Ship `agent_profile.schema.json` as a static file in `src/doctrine/schema/`, loaded via `importlib.resources`.

**Rationale**: Static JSON Schema file allows:

1. IDE validation of `.agent.yaml` files (via YAML language server)
2. External tool consumption (CI validators, pre-commit hooks)
3. Documentation generation
4. Runtime validation via `jsonschema` library (already a dependency)

The schema is authored manually (not generated from dataclasses) to keep the source of truth as a human-readable JSON Schema document that matches the spec's requirements.
