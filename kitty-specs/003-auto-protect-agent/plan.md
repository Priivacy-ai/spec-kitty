# Implementation Plan: Auto-protect Agent Directories

**Branch**: `003-auto-protect-agent` | **Date**: 2025-11-10 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/kitty-specs/003-auto-protect-agent/spec.md`

## Summary

Extend the existing gitignore protection from just `.codex/` to comprehensively protect ALL AI agent directories during spec-kitty initialization. This will be achieved by refactoring the current fragmented approach into a unified GitignoreManager system that handles all agent directories consistently, preventing accidental commits of sensitive files and credentials.

## Technical Context

**Language/Version**: Python 3.11+ (existing spec-kitty codebase)
**Primary Dependencies**: pathlib, Rich (for console output), subprocess (for git operations)
**Storage**: File system (.gitignore file management)
**Testing**: pytest (existing test framework)
**Target Platform**: Cross-platform (Linux, macOS, Windows)
**Project Type**: CLI tool enhancement (single project)
**Performance Goals**: < 1 second for gitignore update operations
**Constraints**: Must maintain backward compatibility, preserve existing .gitignore content
**Scale/Scope**: ~12 agent directories, single .gitignore file per project

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Since the constitution file is currently a template, standard software engineering principles apply:
- ✅ Single Responsibility: GitignoreManager handles only gitignore operations
- ✅ Open/Closed: Extensible for new agents without modifying core logic
- ✅ Dependency Inversion: Abstract interfaces for file operations
- ✅ Testing: Comprehensive unit and integration tests required
- ✅ Backward Compatibility: Maintain existing API through deprecation wrapper

## Project Structure

### Documentation (this feature)

```
kitty-specs/003-auto-protect-agent/
├── plan.md              # This file (Phase 1 output)
├── research.md          # Phase 0 output (completed)
├── data-model.md        # Phase 1 output (completed)
├── quickstart.md        # Phase 1 output (to be created)
├── contracts/           # Phase 1 output (to be created)
├── research/            # Research artifacts
│   ├── evidence-log.csv
│   └── source-register.csv
└── tasks.md             # Phase 2 output (/spec-kitty.tasks command)
```

### Source Code (repository root)

```
src/
├── specify_cli/
│   ├── __init__.py           # Current location of gitignore functions
│   └── gitignore_manager.py  # NEW: GitignoreManager class (to be created)
│
tests/
├── unit/
│   └── test_gitignore_manager.py  # NEW: Unit tests for GitignoreManager
└── integration/
    └── test_gitignore_management.py  # EXISTING: Extend with new tests
```

**Structure Decision**: Single project structure is appropriate as this is an enhancement to the existing CLI tool. The new GitignoreManager will be a separate module within the existing `specify_cli` package to maintain clean separation of concerns while allowing easy integration.

## Phase 0: Research (Completed)

Research artifacts have been generated:
- ✅ `research.md` - Technical decisions and architecture approach documented
- ✅ `data-model.md` - Data structures and entity relationships defined
- ✅ `research/evidence-log.csv` - Evidence from codebase analysis logged
- ✅ `research/source-register.csv` - Sources and references tracked

Key findings:
- Existing `ensure_gitignore_entries()` provides solid foundation
- Agent directory registry exists at lines 1835-1848
- Special handling needed for `.github/` (dual use with Actions)

## Phase 1: Design & Contracts

### API Contracts

The GitignoreManager will expose the following public API:

```python
class GitignoreManager:
    """Manages gitignore entries for AI agent directories."""

    def __init__(self, project_path: Path):
        """Initialize with project root path."""

    def protect_all_agents(self) -> ProtectionResult:
        """Add all known agent directories to gitignore."""

    def protect_selected_agents(self, agents: List[str]) -> ProtectionResult:
        """Add specific agent directories to gitignore."""

    def ensure_entries(self, entries: List[str]) -> bool:
        """Core method to add entries (backward compatible)."""

    @classmethod
    def get_agent_directories(cls) -> List[AgentDirectory]:
        """Get registry of all known agent directories."""
```

### Internal Refactoring

Since `handle_codex_security` is an internal function and not a public API, we can directly replace it with the new GitignoreManager without maintaining backward compatibility. The function will be removed entirely and replaced with direct calls to GitignoreManager methods.

### Integration Points

1. **During `spec-kitty init`**:
   - Replace `handle_codex_security()` call with `GitignoreManager.protect_all_agents()`
   - Display results using existing Rich console

2. **Testing Integration**:
   - Extend existing test suite in `test_gitignore_management.py`
   - Add comprehensive unit tests for new GitignoreManager

3. **Configuration**:
   - Future: Support for `.speckittyrc` configuration file
   - Future: Environment variable overrides

## Phase 2: Implementation Tasks

Implementation tasks will be generated by `/spec-kitty.tasks` command. Expected task breakdown:

1. **Create GitignoreManager Module**
   - Implement GitignoreManager class
   - Migrate ensure_gitignore_entries logic
   - Add agent directory registry

2. **Implement Core Methods**
   - protect_all_agents()
   - protect_selected_agents()
   - Error handling and logging

3. **Replace Existing Implementation**
   - Remove handle_codex_security function
   - Update init flow to use GitignoreManager
   - Remove old ensure_gitignore_entries after migration

4. **Testing**
   - Unit tests for GitignoreManager
   - Integration tests for init flow
   - Edge case testing

5. **Documentation**
   - Update CLI help text
   - Add migration guide
   - Update CHANGELOG

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking tests | Medium | Update all existing tests to use new implementation |
| .github/ directory confusion | Medium | Clear documentation and warning messages |
| Line ending issues | Low | Preserve existing line endings, extensive testing |
| Performance regression | Low | Single file I/O operation, benchmarking |

## Success Metrics

1. **Functional**: 100% of agent directories protected after init
2. **Quality**: Zero duplicate entries in .gitignore
3. **Performance**: < 1 second execution time
4. **Code Quality**: Clean removal of old implementation with all tests passing
5. **Testing**: > 90% code coverage for new module

## Next Steps

1. Run `/spec-kitty.tasks` to generate detailed implementation tasks
2. Begin implementation following TDD approach
3. Update documentation
4. Release as internal improvement