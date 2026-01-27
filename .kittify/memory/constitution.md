# Spec Kitty Constitution

> Created: 2026-01-27
> Version: 1.0.0

## Purpose

This constitution captures the technical standards, architectural principles, and development practices for Spec Kitty. All features and pull requests should align with these principles.

---

## Technical Standards

### Languages and Frameworks

**Python 3.11+** is required for all CLI and library code.

**Key dependencies:**
- **typer** - CLI framework
- **rich** - Console output
- **ruamel.yaml** - YAML parsing (frontmatter)
- **pytest** - Testing framework
- **mypy** - Type checking (strict mode)

### Testing Requirements

- **pytest** with **90%+ test coverage** for new code
- **mypy --strict** must pass (no type errors)
- **Integration tests** for CLI commands
- **Unit tests** for core logic

### Performance and Scale

- CLI operations must complete in **< 2 seconds** for typical projects
- Dashboard must support **100+ work packages** without lag
- Git operations should be efficient (no unnecessary clones/checkouts)

### Deployment and Constraints

- **Cross-platform:** Linux, macOS, Windows 10+
- **Python 3.11+** (no legacy Python 2 support)
- **Git required** (all worktree features depend on Git)
- **PyPI distribution** via automated release workflow

---

## Architecture: Private Dependency Pattern

### spec-kitty-events Library

**Repository:** https://github.com/Priivacy-ai/spec-kitty-events (PRIVATE)

**Purpose:** Shared event sourcing library providing:
- Lamport clocks for causal ordering
- CRDT merge rules for conflict resolution
- Event storage adapters (JSONL, SQLite)
- Deterministic conflict detection

**Used by:**
- spec-kitty CLI (current)
- spec-kitty Django backend (future SaaS platform)

### Development Workflow Requirements

**Primary workflow (required for CI/CD autonomy):**

1. Make changes in spec-kitty-events repository
2. Commit and push to GitHub
3. Get commit hash: `git rev-parse HEAD`
4. Update spec-kitty `pyproject.toml` with new commit hash:
   ```toml
   spec-kitty-events = { git = "https://github.com/Priivacy-ai/spec-kitty-events.git", rev = "abc1234" }
   ```
5. Run `poetry lock --no-update && poetry install`
6. Test integration, commit spec-kitty changes

**Local rapid iteration (use sparingly):**
- Temporary only: `pip install -e ../spec-kitty-events`
- **Must revert to Git dependency before committing**

**Forbidden practices:**
- ❌ Never commit spec-kitty with local `pip -e` path dependency
- ❌ Never use `rev = "main"` (breaks determinism, causes CI flakiness)
- ❌ Never assume spec-kitty-events is available locally

### CI/CD Authentication

**GitHub Actions** uses a **deploy key** to access the private spec-kitty-events repository:
- Secret name: `SPEC_KITTY_EVENTS_DEPLOY_KEY`
- Access: Read-only to spec-kitty-events
- Key rotation: Every 12 months or when compromised

**SSH setup in CI:**
```yaml
- name: Setup SSH for private repo
  run: |
    mkdir -p ~/.ssh
    echo "${{ secrets.SPEC_KITTY_EVENTS_DEPLOY_KEY }}" > ~/.ssh/id_ed25519
    chmod 600 ~/.ssh/id_ed25519
    ssh-keyscan github.com >> ~/.ssh/known_hosts
```

### PyPI Release Process

**Current strategy (until spec-kitty-events goes public):**
1. Vendor events library into `src/specify_cli/_vendored/events/`
2. Run release script: `python scripts/vendor_and_release.py`
3. Publish to PyPI (users don't need GitHub access)

**Future strategy (when events is open source):**
1. Remove vendoring
2. Use standard Git dependency in published wheel
3. Update release documentation

### Testing Integration Changes

**For changes spanning both repositories:**

1. Create feature branch in spec-kitty-events: `feature/lamport-clocks`
2. Create matching branch in spec-kitty: `feature/004-cli-event-log`
3. Pin spec-kitty to events feature branch during development
4. Iterate until tests pass
5. Merge events feature → main
6. Update spec-kitty to pin to events main commit hash
7. Merge spec-kitty feature

**Why commit pinning:**
- Deterministic CI builds (exact same behavior every time)
- Explicit integration points (you control when updates happen)
- Prevents silent breakage from upstream changes

**Details:** See [ADR-11: Dual-Repository Pattern](../../architecture/adrs/2026-01-27-11-dual-repository-pattern.md)

---

## Architecture: Two-Branch Release Strategy

### 1.x vs 2.x Branch Strategy

**Branch Purpose:**
- **1.x branch** - Stable local-only CLI tool (maintenance mode)
- **2.x branch** - SaaS transformation with event sourcing and sync protocol (active development)

### 1.x Branch (Maintenance Mode)

**Status:** Maintenance-only after initial v1.0.0 release

**Characteristics:**
- YAML activity logs (existing system)
- No event sourcing or sync protocol
- No spec-kitty-events dependency
- Local-only operation

**Allowed changes:**
- Security fixes
- Critical bug fixes
- Documentation updates

**Forbidden changes:**
- ❌ New features
- ❌ Architectural changes
- ❌ Breaking changes to stable APIs

### 2.x Branch (Active Development)

**Status:** Active SaaS development (no releases until substantially complete)

**Characteristics:**
- Event sourcing with Lamport clocks
- spec-kitty-events library integration (Git dependency per ADR-11)
- Sync protocol for CLI ↔ Django communication
- Distributed state management with CRDT merge rules
- Greenfield architecture (no 1.x backward compatibility)

**Development principles:**
- ✅ No 1.x compatibility constraints
- ✅ Greenfield architectural freedom
- ✅ Breaking changes allowed (pre-release)
- ✅ Integration with private dependencies (spec-kitty-events)

### Migration Strategy

**Deferred until 2.x nears completion:**
- No progressive migration from 1.x → 2.x during development
- No dual state systems (YAML + events) to maintain
- Migration tool built when 2.x is proven stable

**When 2.x approaches beta:**
1. Build migration tool: `spec-kitty migrate-to-2x`
2. Convert YAML activity logs → event log
3. User-initiated migration (not automatic)

**Rationale:** Deferred migration is simpler than progressive migration (avoids dual state complexity)

### Communication

**Users:**
- README badges: "1.x (Maintenance)" vs "2.x (Active Development)"
- Clear documentation separation
- GitHub issue tags: `1.x` and `2.x`

**Contributors:**
- All new features target 2.x branch
- 1.x PRs limited to security/critical fixes
- ADRs indicate target branch if applicable

**Details:** See [ADR-12: Two-Branch Strategy for SaaS Transformation](../../architecture/adrs/2026-01-27-12-two-branch-strategy-for-saas-transformation.md)

---

## Code Quality

### Pull Request Requirements

- **1 approval required** (self-merge allowed for maintainer)
- **CI checks must pass** (tests, type checking, linting)
- **Pre-commit hooks** must pass (UTF-8 encoding validation)

### Code Review Checklist

- Tests added for new functionality
- Type annotations present (mypy --strict passes)
- Docstrings for public APIs
- No security issues (credentials, secrets handling)
- Breaking changes documented in CHANGELOG.md

### Quality Gates

- All tests pass (pytest)
- Type checking passes (mypy --strict)
- No regressions in existing functionality
- Documentation updated (README, CLI help text)

### Documentation Standards

- **CLI commands:** Help text must be clear and include examples
- **Public APIs:** Docstrings with parameter types and return values
- **Breaking changes:** Update migration guide in docs/
- **Architecture decisions:** Capture in ADRs (architecture/decisions/)

---

## Governance

### Amendment Process

Any maintainer can propose amendments via pull request. Changes are discussed and merged following standard PR review process.

**For major architectural changes:**
1. Write ADR (Architecture Decision Record)
2. Open PR with ADR + implementation
3. Discuss trade-offs and alternatives
4. Merge after review

### Compliance Validation

Code reviewers validate compliance during PR review. Constitution violations should be flagged and addressed before merge.

### Exception Handling

Exceptions discussed case-by-case. Strong justification required.

**If exceptions become common:** Update constitution instead of creating more exceptions.

---

## Attribution

**Spec Kitty** is inspired by GitHub's [Spec Kit](https://github.com/github/spec-kit). We retain the original attribution per the Spec Kit license while evolving the toolkit under the Spec Kitty banner.

**License:** MIT (All Rights Reserved for Priivacy AI code)
