# Spec Kitty Charter

> Created: 2026-01-27
> Version: 1.1.4

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

## Architecture: Shared Package Boundaries

### External Contract Packages

`spec-kitty-events` and `spec-kitty-tracker` are true external package dependencies for the Spec Kitty CLI. Treat them like normal third-party Python libraries with Spec Kitty-owned governance:

- Consume released PyPI packages through the normal dependency graph.
- Do not vendor their source into the CLI package.
- Do not commit path dependencies, editable installs, or moving branch refs for production or release builds.
- Use SemVer-compatible dependency ranges in library/package metadata where compatibility allows; keep exact artifact resolution in lockfiles and release records.
- Validate cross-repo behavior with consumer tests and compatibility fixtures rather than forcing every sibling package to release in lockstep.

`spec-kitty-events` owns event envelopes, payload schemas, committed fixtures, replay helpers, and event compatibility rules.

`spec-kitty-tracker` owns tracker provider abstractions, hosted discovery/sync primitives, normalized tracker models, and tracker authority policy behavior.

### Internal Runtime Boundary

Mission runtime behavior is CLI-owned implementation code, not an external shared dependency for the CLI release path.

- Runtime code used by `spec-kitty next` and mission execution should live inside this repository.
- CLI runtime code may consume `spec-kitty-events` and `spec-kitty-tracker` as external package contracts where needed.
- The CLI must not require the standalone `spec-kitty-runtime` PyPI package at runtime.
- Do not add release gates that require publishing `spec-kitty-runtime` before the CLI can ship.
- If SaaS needs analogous mission execution behavior, establish an explicit SaaS-owned boundary or a new shared contract through a reviewed issue before reintroducing a shared runtime package.

### Development Workflow Requirements

For external package contract changes:

1. Change the owning package repository first.
2. Publish or prepare a versioned package artifact with compatibility notes.
3. Update CLI dependency constraints or lockfiles to consume that artifact.
4. Run CLI consumer tests that cover the changed contract.
5. Do not merge temporary path, git, branch, or editable-install overrides.

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

### Branch-Intent Terminology Governance

- Use **`repository root checkout`** for the non-worktree checkout where planning commands run.
- Use **`current branch`**, **`target branch`**, **`planning_base_branch`**, and **`merge_target_branch`** for branch semantics.
- Do **not** use **`main repository`**, **`main repo`**, or **`main repository root`** in user-facing docs or prompts.
- Do **not** use **`main`** as a generic default branch name. Only use `main` when the actual branch is `main`.
- When a document needs to talk about location and branch in the same sentence, name both explicitly instead of implying one from the other.

### Identifier Safety Rules

1. Database names, lane identifiers, and other storage-facing slugs generated from user, branch, lane, mission, or tracker input must remain ASCII-only and deterministic. Sanitizers must use an explicit ASCII allowlist such as `[A-Za-z0-9_]` or opt Python regular expressions into ASCII semantics with `re.ASCII`; do not rely on default Unicode `\w` or `\W` behavior for database-safe identifiers.
2. Any change to identifier normalization or slug sanitization must include regression coverage for non-ASCII input, including at least one accented Latin example and one case that proves the produced storage identifier is `.isascii()`.

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
- `spec-kitty-saas/docs/docker-development-modes.md` (sibling SaaS repo checkout)

---

## Central CLI-SaaS API Contract

- The published current-state CLI↔SaaS contract lives at `../spec-kitty-saas/contracts/cli-saas-current-api.yaml`.
- Any CLI change that alters hosted routes, request/response bodies, auth headers, websocket behavior, sync payloads, or tracker control-plane semantics must update that contract in the same change.
- ADRs, PRDs, and roadmap notes may describe future APIs, but the authoritative reference for what the CLI actually speaks to SaaS today is that contract file.

---

## Tracker Ticket Assignment Rule

1. When an agent starts implementing work from a tracker-backed issue for this repository, the agent must assign that ticket to the Human-in-Charge (HiC) before or as part of beginning the implementation. For Spec Kitty today, GitHub issues are the active tracker case and must follow this rule.

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
