# Quickstart: Feature 048 Implementation Reference

**Feature**: Structured Agent Identity & Constitution-Profile Integration

## At a Glance

| Track | Scope | Key Files |
|-------|-------|-----------|
| **A — Identity** (WP01–03) | `ActorIdentity` dataclass, frontmatter, CLI | `identity.py`, `models.py`, `transitions.py`, `frontmatter.py`, `tasks.py` |
| **B — Constitution** (WP04–07) | Catalog expansion, transitive resolver, compiler wiring | `catalog.py`, `reference_resolver.py`, `compiler.py`, `resolver.py` |
| **Convergence** (WP08) | Integration tests | `tests/integration/` |

## WP Implementation Cheat Sheet

### WP01: ActorIdentity Dataclass

```python
# src/specify_cli/identity.py (NEW)
@dataclass(frozen=True)
class ActorIdentity:
    tool: str
    model: str = "unknown"
    profile: str = "unknown"
    role: str = "unknown"

    @classmethod
    def from_compact(cls, s: str) -> ActorIdentity: ...
    @classmethod
    def from_legacy(cls, s: str) -> ActorIdentity: ...
    def to_compact(self) -> str: ...
    def to_dict(self) -> dict[str, str]: ...
    @classmethod
    def from_dict(cls, d: dict[str, str]) -> ActorIdentity: ...

# Modify StatusEvent in src/specify_cli/status/models.py
# actor: str → actor: ActorIdentity
# Update to_dict()/from_dict() for backwards compat
```

### WP02: Frontmatter Structured Agent

```python
# src/specify_cli/frontmatter.py — update extract_scalar for agent field
# Read: str → ActorIdentity.from_legacy(); dict → ActorIdentity.from_dict()
# Write: always structured YAML mapping

# src/specify_cli/tasks_support.py — WorkPackage.agent
# Return type: str | None → ActorIdentity | None
```

### WP03: CLI Flags

```python
# src/specify_cli/identity.py — add parser
def parse_agent_identity(
    agent: str | None,
    tool: str | None, model: str | None,
    profile: str | None, role: str | None,
) -> ActorIdentity | None:
    # Mutual exclusion: raise if both agent and any individual flag provided
    ...

# Add --tool/--model/--profile/--role to:
# - src/specify_cli/cli/commands/agent/tasks.py (move-task)
# - src/specify_cli/cli/commands/agent/workflow.py (implement, review)
```

### WP04: DoctrineCatalog Expansion

```python
# src/specify_cli/constitution/catalog.py
# Add: tactics, styleguides, toolguides, procedures, profiles frozensets
# Reuse _load_yaml_id_catalog() with appropriate glob patterns
```

### WP05: Transitive Reference Resolver

```python
# src/specify_cli/constitution/reference_resolver.py (NEW)
def resolve_references_transitively(
    directive_ids: list[str],
    doctrine_service: DoctrineService,
) -> ResolvedReferenceGraph:
    # DFS with visited set (cf. engine.py:depth_first_order pattern)
    ...
```

### WP06: Compiler + DoctrineService

```python
# src/specify_cli/constitution/compiler.py
def compile_constitution(
    *, mission, interview, template_set=None,
    doctrine_catalog=None,
    doctrine_service=None,  # NEW optional param
) -> CompiledConstitution:
    if doctrine_service is not None:
        # Use transitive resolution via DoctrineService
        ...
    else:
        # Fallback: existing _index_yaml_assets() path
        diagnostics.append("DoctrineService unavailable; using YAML scanning fallback")
```

### WP07: Profile-Aware Governance

```python
# src/specify_cli/constitution/resolver.py
def resolve_governance_for_profile(
    profile_id: str, role: str | None,
    doctrine_service: DoctrineService,
    interview: ConstitutionInterview,
) -> GovernanceResolution:
    # 1. Load profile via doctrine_service.agent_profiles.resolve_profile()
    # 2. Extract directive_references from profile
    # 3. Merge with interview.selected_directives (union, profile first)
    # 4. Run transitive resolution
    # 5. Build extended GovernanceResolution
    ...
```

## Test Commands

```bash
# Run all status tests
pytest tests/specify_cli/status/ -v

# Run all constitution tests
pytest tests/specify_cli/constitution/ -v

# Run integration tests
pytest tests/integration/ -v -k "structured_identity or profile_constitution"

# Type check
mypy src/specify_cli/identity.py src/specify_cli/status/ src/specify_cli/constitution/

# Lint
ruff check src/specify_cli/identity.py src/specify_cli/status/ src/specify_cli/constitution/
```

## Key Patterns to Follow

1. **Frozen dataclasses** for all new value objects (ActorIdentity, ResolvedReferenceGraph)
2. **`to_dict()` / `from_dict()`** for serialisation (match StatusEvent pattern)
3. **Cycle detection via visited set** (match `depth_first_order()` pattern)
4. **Optional fallback** for DoctrineService (match constraint C-003)
5. **`_load_yaml_id_catalog()`** reuse for new artifact types in catalog
