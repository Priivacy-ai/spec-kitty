# Spec Kitty Charter

> Created: 2026-01-27
> Version: 1.1.1

## Purpose

This charter captures the technical standards, architectural principles, and development practices for Spec Kitty. All features and pull requests should align with these principles.

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
5. Run `uv sync` (the project uses PEP 621 + Hatch via `pyproject.toml`; `uv` is the canonical dependency manager — see `CONTRIBUTING.md`)
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

## Architecture: Branch and Release Strategy

### Current Branch Strategy (3.x)

**Active development** happens on `main`. The current version is **3.x** (3.1.0a3+).

**Branch layout:**
- **`main`** — Active development. All new features, bug fixes, and releases target `main`.
- **`remotes/origin/1.x-maintenance`** — Historical. The 1.x local-only CLI is in maintenance mode. Only security and critical bug fixes are accepted.

The former `2.x` branch was merged into `main` when the SaaS transformation reached maturity. There is no separate `2.x` branch.

### Release Versioning

- **3.x** — Current active version. Event sourcing, sync protocol, mission identity model, spec-kitty-events integration.
- **1.x** — Historical maintenance branch. YAML activity logs, local-only operation, no spec-kitty-events dependency.

### Development Principles

- All new features target `main`
- Breaking changes are allowed during pre-release alpha/beta cycles
- The `spec-kitty agent mission branch-context --json` command resolves the deterministic branch contract for any feature
- Do not hardcode branch names in templates or scaffolding; use the resolved branch context

### CI and Branch Protection

`main` has a **Protect Main Branch** GitHub Actions workflow that fails whenever code is pushed directly without going through a PR. The `spec-kitty merge` command pushes directly to main by design. This causes a **known, expected** CI failure on every feature merge. It is not a code bug and must not be treated as one.

**Rule for agents:** When CI shows "Protect Main Branch: failure" after `spec-kitty merge`, ignore it. Monitor **CI Quality** only — that is the authoritative signal for code correctness.

### Historical Context

The 1.x/2.x branch split was originally documented in [ADR-12: Two-Branch Strategy for SaaS Transformation](../../architecture/adrs/2026-01-27-12-two-branch-strategy-for-saas-transformation.md). That strategy served its purpose during the SaaS transformation and is now superseded by single-branch development on `main`.

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

## User Customization Preservation

### Ownership Boundaries for Mutating Flows

- This section governs **Spec Kitty development itself**. It is a maintainer rule for the Spec Kitty codebase and release process; it is not a substitute for end-user project charters, which users generate for their own repositories.
- Package-owned mutation flows (`init`, `upgrade`, install/remove/sync commands, shipped-asset refresh, and migrations) must treat user-authored custom commands, custom skills, and project overrides as **user-owned assets** by default.
- No mutating flow may overwrite, delete, rename, or chmod a user-owned customization unless the exact path is explicitly package-managed or manifest-tracked.
- Name-based heuristics alone are not sufficient proof of package ownership. Historical broad matching of `spec-kitty.*` command names has created a real risk of clobbering user-authored slash commands that were never shipped by Spec Kitty.
- When package-managed files share a directory with user-authored files, cleanup and migration logic must scope destructive changes only to known package-owned paths and leave unknown or third-party files untouched.
- If ownership cannot be proven from manifest data or an explicit managed-path contract, the safe behavior is to preserve the file and emit a warning instead of deleting or rewriting it.

### Proof Trail

- `src/specify_cli/runtime/merge.py` already encodes the intended ownership model for runtime assets: package-managed paths may be refreshed, while user-owned data must be preserved.
- `src/specify_cli/skills/command_installer.py` already codifies the same boundary for shared skills roots: third-party paths under `.agents/skills/` are never touched unless they are manifest-owned.
- `src/specify_cli/upgrade/migrations/m_3_1_2_globalize_commands.py` is the motivating hazard: broad `spec-kitty.*` filename matching can incorrectly classify user-authored custom slash commands as shipped assets and remove them.
- Any future migration, installer, or cleanup path that mutates user-visible command or skill directories must document its ownership proof and show why it cannot hit custom user files.

---

## Local Docker Development Governance (`spec-kitty-saas`)

When work in this program touches the SaaS repository, all contributors and agents must use a two-mode Docker workflow:

1. **`dev-live` mode** for active implementation loops
- Live code volumes
- Django autoreload
- Vite dev server
- Primary commands: `make docker-app-up-live`, `make docker-app-down-live`

2. **`prod-like` mode** for pre-merge and pre-deploy validation
- Image-based parity stack
- Primary commands: `make docker-app-up`, `make docker-auth-check`, `make docker-app-down`

Mandatory gate:
- A `prod-like` authenticated preflight must pass before Fly promotion and before considering SaaS integration work complete.

Operational reference:
- `/Users/robert/ClaudeCowork/Spec-Kitty-Cowork/spec-kitty-saas/docs/docker-development-modes.md`

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

Code reviewers validate compliance during PR review. Charter violations should be flagged and addressed before merge.

### Exception Handling

Exceptions discussed case-by-case. Strong justification required.

**If exceptions become common:** Update charter instead of creating more exceptions.

---

## Attribution

**Spec Kitty** is inspired by GitHub's [Spec Kit](https://github.com/github/spec-kit). We retain the original attribution per the Spec Kit license while evolving the toolkit under the Spec Kitty banner.

**License:** MIT (All Rights Reserved for Priivacy AI code)

---

## Terminology Canon (Mission vs Feature)

- Canonical product term is **Mission** (plural: **Missions**).
- `Feature` / `Features` are prohibited in canonical, operator, and user-facing language for active systems.
- Hard-break policy: do not introduce or preserve `feature*` aliases (API/query params, routes, fields, flags, env vars, command names, or docs) when the domain object is a Mission.
- Use `Mission` / `Missions` as the only canonical term in active codepaths and interfaces.
- Historical archived artifacts may retain legacy wording only as immutable snapshots and must be explicitly marked legacy.

### Regression Vigilance (2026-04-06)

The `--feature` → `--mission` rename has been a persistent source of regressions. Mission 065 swept ~45 user-facing references, but the pattern keeps recurring because:
1. New code copies from old code that still uses `feature` as variable names (the internal Python parameter name is `feature` even when the CLI flag is `--mission`)
2. Error messages and guidance strings are written ad-hoc without checking the canon
3. Subagent-implemented code may not see this charter

**Hyper-vigilance rules:**
- Every PR that adds a new `typer.Option` or `argparse.add_argument` for a mission slug MUST use `--mission` as the primary name. `--feature` is only acceptable as a hidden secondary alias.
- Every PR that adds an error message mentioning a CLI flag MUST reference `--mission`, not `--feature`.
- Every PR that adds a command example in templates or docstrings MUST use `--mission`.
- Code reviewers MUST grep for `--feature` in new/changed lines and reject any non-alias usage.
- The upstream contract at `src/specify_cli/core/upstream_contract.json` lists `--feature` as a **forbidden CLI flag** for new code. This is authoritative.
