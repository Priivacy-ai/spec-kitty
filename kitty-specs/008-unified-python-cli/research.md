# Research Findings

## Decision: Unified `spec-kitty agent` CLI namespace

- **Rationale**: Consolidating all agent-facing commands under `spec-kitty agent` eliminates the need for bash scripts to be copied to worktrees. The CLI can detect execution location (main repo vs worktree) and resolve paths automatically using Python's `pathlib` and git operations. This addresses the core problem: agents struggle with bash script locations and path resolution.
- **Evidence**: EV001, EV002, EV003 - Current codebase already has Python path resolution (`src/specify_cli/core/paths.py`) and Typer CLI framework. Agents currently retry commands due to path errors (user-reported issue).
- **Alternatives considered**:
  - Keep bash scripts but improve symlink handling (rejected: doesn't solve Windows compatibility or agent confusion)
  - Hybrid approach with some bash, some Python (rejected: maintains complexity, defeats purpose)
  - Backward compatibility wrappers (rejected: violates clean migration requirement)

## Decision: Complete bash script elimination (~2,600 lines)

- **Rationale**: All bash functionality in `.kittify/scripts/bash/` and `.github/workflows/scripts/` can be migrated to Python. Analysis shows most bash scripts are thin wrappers around Python (`tasks_cli.py`) or perform git/file operations easily replicated in Python. Eliminating bash entirely simplifies maintenance, enables testing, and ensures cross-platform compatibility.
- **Evidence**: EV004, EV005, EV006 - Bash script inventory shows 24 scripts with majority being wrappers. Existing Python utilities in `src/specify_cli/core/` already replicate most `common.sh` functionality.
- **Alternatives considered**:
  - Keep git hooks as bash (deferred: out of scope for this phase, noted in spec)
  - Keep CI scripts as bash (rejected: `spec-kitty agent build-release` provides better testability)
  - Partial migration (rejected: doesn't solve agent confusion, maintains dual systems)

## Decision: Path resolution strategy using `.kittify/` marker and git

- **Rationale**: Three-tier resolution: (1) Check `SPECIFY_REPO_ROOT` env var, (2) Use `git rev-parse --show-toplevel`, (3) Walk up directory tree for `.kittify/` marker. This handles all edge cases: worktrees, nested directories, broken symlinks, Windows (no symlink support). Worktree detection checks if `.worktrees` appears in path hierarchy.
- **Evidence**: EV007, EV008, EV009 - Existing `resolve_worktree_aware_feature_dir()` in `src/specify_cli/core/project_resolver.py` already implements similar logic. Windows fallback pattern exists in codebase (copy instead of symlink).
- **Alternatives considered**:
  - Always require env var (rejected: fragile, agent-unfriendly)
  - Git-only resolution (rejected: breaks in non-git contexts, doesn't handle symlinks)
  - Hardcoded paths (rejected: inflexible, breaks portability)

## Decision: `spec-kitty upgrade` migration for existing projects

- **Rationale**: Automated migration via `spec-kitty upgrade` infrastructure eliminates manual steps. Migration script detects bash scripts in `.kittify/scripts/bash/`, updates slash command templates (`.claude/commands/*.md`) to call `spec-kitty agent` commands, cleans up worktree script copies, and validates idempotency. Warns on custom bash modifications that cannot be auto-migrated.
- **Evidence**: EV010, EV011 - Existing upgrade infrastructure in `src/specify_cli/upgrade/migrations/` provides pattern. Similar migration (`m_0_9_0_frontmatter_only.py`) successfully migrated task lane structure.
- **Alternatives considered**:
  - Manual migration guide only (rejected: error-prone, adoption friction)
  - Destructive migration without backup (rejected: too risky)
  - No migration support (rejected: breaks existing projects)

## Decision: JSON output mode for all agent commands

- **Rationale**: All `spec-kitty agent` commands support `--json` flag outputting machine-parseable JSON. Agents parse structured output for workflow orchestration. Human users get rich console output (default). Dual-mode approach balances agent needs (programmatic) with developer needs (debugging).
- **Evidence**: EV012, EV013 - Existing pattern in proposed plan shows JSON mode with error handling. Typer supports optional flags naturally.
- **Alternatives considered**:
  - JSON-only output (rejected: poor developer experience)
  - Separate agent vs human commands (rejected: doubles maintenance, violates DRY)
  - Structured logging instead of JSON (rejected: harder for agents to parse reliably)

## Decision: Preserve existing CLI registration with Typer sub-app pattern

- **Rationale**: Register `agent` as Typer sub-app under main `spec-kitty` CLI. Pattern: `src/specify_cli/cli/commands/agent/__init__.py` registers feature.py, context.py, tasks.py, release.py sub-modules. Keeps user commands (`spec-kitty init`) separate from agent commands (`spec-kitty agent create-feature`) while sharing core utilities.
- **Evidence**: EV014 - Typer documentation supports sub-app pattern. Existing codebase structure aligns.
- **Alternatives considered**:
  - Separate CLI binary for agents (rejected: complicates deployment, PATH issues)
  - Flat namespace (rejected: pollutes user CLI with 20+ agent commands)
  - Plugin architecture (rejected: over-engineered for current needs)

## Decision: 90%+ test coverage requirement for agent namespace

- **Rationale**: Agent workflows are mission-critical and currently untestable (bash). Python enables unit and integration tests. Coverage target ensures quality and catches regressions. Tests verify commands work from main repo and worktrees, JSON mode functions correctly, and edge cases are handled.
- **Evidence**: EV015 - Spec requirement FR-026, FR-027. Existing Python tests in `tests/` provide patterns.
- **Alternatives considered**:
  - No coverage target (rejected: defeats testability benefit)
  - 100% coverage (rejected: diminishing returns, pragmatic 90% balances cost/benefit)
  - Manual testing only (rejected: regression risk, unsustainable)

## Decision: Research phase validates approach before implementation

- **Rationale**: P0 (prerequisite) research phase validates: (1) All bash functionality can migrate to Python, (2) Path resolution handles all edge cases, (3) Upgrade migration is safe. Research produces go/no-go recommendation and documents risks. Prevents committing to invalid approach.
- **Evidence**: EV016, EV017 - User explicitly requested research validation. Spec prioritizes research as P0.
- **Alternatives considered**:
  - Skip research, start implementation (rejected: risk of discovering blockers mid-implementation)
  - Concurrent research + implementation (rejected: wastes effort if approach invalidates)

## Validation Results

### ✅ All bash functionality can migrate to Python

**Finding**: Comprehensive inventory shows 24 bash scripts fall into categories:

- **Wrappers** (15 scripts): Already call Python (`tasks_cli.py`) - trivial to migrate
- **Path utilities** (`common.sh`): Functionality exists in `src/specify_cli/core/paths.py`
- **Git operations** (worktree management): Python `subprocess` + `pathlib` handles
- **Template processing** (`update-agent-context.sh`): String manipulation, trivial in Python
- **CI scripts** (6 scripts): Git log parsing, file manipulation - all Python-friendly

**Exception**: Git hooks (`pre-commit-task-workflow.sh`) - marked out of scope, can defer

**Evidence**: EV004, EV005, EV006

**Recommendation**: ✅ Proceed with complete elimination

### ✅ Path resolution handles all edge cases

**Finding**: Proposed three-tier resolution strategy addresses:

- ✅ **Worktrees**: `.worktrees/feature-name/` detection via path inspection
- ✅ **Symlinks**: Check `is_symlink()` before `exists()` (existing pattern in codebase)
- ✅ **Broken symlinks**: Graceful degradation with error message
- ✅ **Windows**: Fall back to file copy when symlinks unsupported (existing pattern)
- ✅ **Nested directories**: Walk up tree to find `.kittify/` or git root
- ✅ **Non-git contexts**: `.kittify/` marker works even without git

**Evidence**: EV007, EV008, EV009

**Recommendation**: ✅ Proposed strategy is sound

### ✅ Upgrade migration is safe and feasible

**Finding**: Existing migration infrastructure (`src/specify_cli/upgrade/migrations/`) supports:

- ✅ **Detection**: Scan `.kittify/scripts/bash/` for bash scripts
- ✅ **Template updates**: Parse `.claude/commands/*.md`, replace bash script calls with `spec-kitty agent` equivalents
- ✅ **Cleanup**: Remove bash scripts, remove worktree copies
- ✅ **Validation**: Idempotency via migration version tracking
- ✅ **Custom modifications**: Detect changes vs template, warn user

**Precedent**: `m_0_9_0_frontmatter_only.py` successfully migrated task structure across all projects

**Evidence**: EV010, EV011

**Recommendation**: ✅ Upgrade migration is viable using existing patterns

### ⚠️ Risks Identified

**Risk 1: Cross-platform compatibility edge cases**

- **Description**: Windows, macOS, Linux may have subtle path separator or permission differences
- **Mitigation**: Comprehensive CI testing on all platforms, use `pathlib` (cross-platform by design)
- **Severity**: Low (existing codebase already cross-platform)

**Risk 2: Custom bash script modifications**

- **Description**: Users may have customized bash scripts in ways migration cannot detect
- **Mitigation**: Migration warns on modifications, provides manual migration guide
- **Severity**: Medium (affects subset of users, documented exit path)

**Risk 3: Agent retry behavior measurement**

- **Description**: SC-005 requires 95% reduction in retry behavior, but baseline may be hard to measure
- **Mitigation**: Track error logs before/after, qualitative feedback from agents acceptable
- **Severity**: Low (qualitative measurement acceptable for user-facing metric)

## Research Recommendation

**Go/No-Go**: ✅ **GO - Proceed with Implementation**

**Confidence Level**: High

**Rationale**:

1. All bash functionality confirmed migratable to Python (no blockers identified)
2. Path resolution strategy validated against existing codebase patterns
3. Upgrade migration feasible using proven infrastructure
4. Risks identified are low-to-medium severity with clear mitigations
5. Benefits (agent reliability, testability, maintainability) significantly outweigh risks

**Next Steps**:

1. Proceed with `/spec-kitty.plan` to create implementation plan
2. Follow proposed 7-phase approach with adjustments based on research findings
3. Prioritize cross-platform CI testing early in implementation
4. Document custom bash script migration guide for edge cases

## Outstanding Questions

**Q1**: Should we provide a "compatibility shim" for users who want to delay migration?

- **Recommendation**: No - clean cut migration preferred per spec, reduces long-term maintenance burden
- **Rationale**: Compatibility shims add complexity, delay adoption, create technical debt

**Q2**: Should we migrate git hooks (`pre-commit-task-workflow.sh`) in this phase or defer?

- **Recommendation**: Defer - marked out of scope in spec
- **Rationale**: Git hooks are lower priority, can be separate feature. Focus on agent commands first.

**Q3**: Should we version the `spec-kitty agent` CLI separately from main CLI?

- **Recommendation**: No - single versioning simplifies deployment
- **Rationale**: Agent commands are core functionality, not a plugin. Unified versioning prevents compatibility issues.
