# Spec Kitty Charter

> Created: 2026-01-27
> Version: 1.3.0
> Updated: 2026-07-01 — interactive charter intake (doctrine-catfooding-2196-01KWE16N)
>
> **v1.3.0 note:** retains the full v1.1.5 substance; adds the activated catfooding
> doctrine set and an interactive-intake pass that foregrounds actionable governance. `config.yaml` `activated_*` keys were
> produced by the canonical `spec-kitty charter activate --cascade all` CLI
> (DIRECTIVE_044 compliant). The interactive charter intake (2026-07-01) wired
> `directive→artifact` `suggests` edges from DIRECTIVE_043/044/045 so **all 14
> catfooding artifacts are directive-reachable and resolve in `references.yaml`**,
> and states the eight standing orders as actionable policy in the section below
> (superseding the earlier deferral-and-status framing).

## Purpose

This charter captures the technical standards, architectural principles, and development practices for Spec Kitty. All features and pull requests should align with these principles.

---

## Governing Principles

These bind every action; detail lives in the referenced doctrine and the sections below.

- **Single canonical authority.** Every rule, surface, and identity has ONE owning
  source. Reconcile (extend/reference) existing doctrine rather than add a second
  authority; prefer require-canonical + migration over no-canonical-field fallback
  branches; chase unification, not parity with a dead quirk. (Principle — reviewers
  weigh it; not an automated rejection.) → `DIRECTIVE_044`, `canonical-source-unification`.
- **Architectural alignment.** Respect the declared architecture — shared-package
  boundaries (external contract packages vs the internal runtime) and the integrity of
  module seams. New surfaces align to the existing structure, not around it.
  → `DIRECTIVE_001` (architectural-integrity), the Architecture sections below.
- **Domain-driven splits + tiered rigour.** Model bounded contexts; keep aggregates
  well-formed; apply MORE rigour to core domain logic than to glue/IO.
  → `domain-driven-design` paradigm, `tiered-standards` + `aggregate-design-rules` styleguides.
- **ATDD-first.** Drive features outside-in from acceptance criteria; the acceptance
  test is the contract. → `acceptance-test-first`, the ATDD-First Discipline section below.
- **Glossary & terminology adherence.** Use the canonical terms; keep domain language
  precise across specs, code, and docs; the terminology canon (Mission, not Feature) is
  enforced. → the Terminology Canon section below, `contextive` toolguide.

## Quality & Tech-Debt Standing Orders

Eight standing practices that keep spec-driven missions honest, now activated
doctrine (14 artifacts) and compiled into this charter. Each rule below is
binding actionable guidance; the full how-to lives in the referenced doctrine
artifact. **Throughline:** never trust a green check, a clean diff, or a confident
summary — verify against live code, witness the bug in a real run, and let
independent adversarial perspectives try to break the work *before* it lands, at
the cheapest point in the lifecycle.

1. **Adversarial squad cadence.** Run a bounded, profile-loaded adversarial squad
   at every planning point-cut (pre-spec / post-spec / post-plan / post-tasks)
   before proceeding — one lens per agent, strongest model for the hard lenses.
   Optional and advisory, never a hard gate. → `adversarial-squad-cadence` styleguide.
2. **Campsite cleaning & incremental debt paydown.** *Open* a mission/WP by
   campsite-cleaning the surfaces it will touch **first** — resolve their Sonar
   findings, extract/decompose over-long functions/files, refactor the methods
   about to change — *before* the functional change, as a tidy-first enabler
   (behavior-preserving, focused tests, a distinct preceding step; dispatch a
   campsite scout on god-surfaces). Then fold only *domain-matched* debt at each
   point-cut; freeze current offenders as a baseline when a litter class cannot be
   cleared in-mission (debt stops growing while you chip at it). → `DIRECTIVE_025`.
3. **Mission tracer files.** Seed three tracer files (tooling-friction, approach,
   design-decisions) at planning, append during implementation, assess at close —
   friction and rationale feed the next mission. → `mission-tracer-files` procedure.
4. **Test remediation & bug-fix discipline.** Judge the test, not git-blame
   (stale → re-pin, stub → delete, valid → fix the product); reproduce RED-FIRST
   through the pre-existing entry point; require live evidence over "looks fixed";
   use realistic data; never retry-to-green. → `DIRECTIVE_041`, `DIRECTIVE_034`.
5. **Architectural gate discipline.** Close defect classes by construction with a
   NON-VACUOUS call-site gate (concrete floor + self-mutation test + shrink-only
   allowlist); a gate-unmask cannot self-validate. After merge, run the full
   arch-gate sweep with a cross-base pre-existing check. → `DIRECTIVE_043`,
   `architectural-gate-non-vacuity`, `frozen-baseline-shrink-only-ratchet`,
   `post-merge-arch-gate-adjudication`.
6. **Canonical sources & unification.** Use canonical templates/skills/CLI, never
   improvise or copy an older mission; chase unification, not parity; a missing
   command is a gap to file upstream; guard the terminology canon. → `DIRECTIVE_044`,
   `canonical-source-unification`, `terminology-guard`.
7. **Git & workflow discipline.** PRs only, the operator merges; read intent before
   any high-risk op; isolate PR-touching agents in a worktree; no version numbers
   in scope. → `DIRECTIVE_045`, `pr-agent-worktree-isolation`.
8. **Mission hygiene.** Reviewer and implementer are distinct roles; every addressed
   issue gets an issue-matrix row + claim + tracker comment naming the mission;
   give implementers ownership-map leeway (no-overlap is the real guard); apply
   tiered rigour. → `planning-and-tracking` styleguide,
   `reviewer-implementer-role-separation`, `ownership-map-leeway`.

All 14 catfooding artifacts are activated (`.kittify/config.yaml`) and
directive-reachable, so each resolves in the compiled reference set
(`references.yaml`). This section states the rules; the referenced artifacts carry
the detailed procedures, examples, and anti-patterns.

## Agent Operating Discipline

How agents and orchestrators should work so quality and context survive long missions.

- **Model discipline.** Match model strength to the task: the strongest model for hard
  judgment — sizing, fakeability, code-truth, review, architecture — and a cheaper model
  for grounded or mechanical passes. Never run high-stakes review or design on a light
  model. → `model-task-routing`.
- **Delegate to preserve context.** Use subagents for work that can run in an isolated
  context — a work package in its own worktree, a review against a fixed diff, a focused
  investigation — so the orchestrator's context stays clean. Each delegation LOADS the
  relevant doctrine profile (not merely a persona name). Compact after task pivots; do not
  combine architecture, debugging, and implementation in one long context.
  → `autonomous-operation-protocol`.

## Collaboration Strategy

How missions are executed between the operator (human-in-command) and the agent fleet.

- **Dispatch a governed profile to run the mission.** The operator delegates mission
  execution to a governed orchestrator; planning and tracker work runs under
  `planner-priti` (profile LOADED, not a persona name). The orchestrator **claims** the
  mission's tickets (assign the operator + a comment naming the mission), **plans**
  (spec → plan → tasks, with an adversarial squad at each planning point-cut), and
  **runs** the implement→review loop to completion.
- **Draft PR first.** Completed mission work is opened as a DRAFT pull request to the
  protected branch, with history compressed (admin bunched, code by slice).
- **Ready-for-review only when green.** The agent marks the PR ready-for-review **only
  after** self-review (an adversarial review pass, findings folded) AND CI pass — i.e.
  it prepares the PR merge-ready (green, un-drafted, issues linked) and hands off.
- **The operator merges.** Agents never merge to protected main; the human-in-command
  performs the merge. → git/workflow discipline (`DIRECTIVE_045`), Agent Operating
  Discipline above.

## Governance by Workflow Action

Quick map from workflow action to the rules that bind it (load the action's doctrine
context for the detail).

- **Specify / Plan** — reconcile-don't-duplicate (check for an existing authority before
  adding one); run an adversarial squad at each planning point-cut (advisory, never a
  gate); fold only domain-matched debt; model bounded contexts with tiered rigour; assign
  no version numbers in scope.
- **Implement** — ATDD / red-first through the pre-existing entry point; close defect
  classes with non-vacuous gates; use canonical sources (no improvise); keep the
  terminology canon; append the mission tracer files.
- **Review** — reviewer ≠ implementer; run the FULL compliance suite (not a subset);
  verify no duplicate authority, no dead code, and live evidence; apply tiered rigour;
  grant ownership-map leeway (no-overlap is the real guard).
- **Merge** — PRs only, the operator merges; isolated PR-review agents; post-merge full
  arch-gate sweep with a cross-base pre-existing check; issue-matrix + tracker hygiene.

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
- **Run only the affected test packages, not the full suite, whenever the change is scoped to a known surface.** The repository's test suite has ~17,000 tests and a full run is expensive in wall-clock time and orchestrator context budget. Per-WP and per-PR validation should target the directories that bound the change (e.g., `tests/specify_cli/audit/` for an audit-detector change, `tests/specify_cli/cli/commands/test_sync*.py` for a sync surface change). The full `pytest tests/` gate is reserved for: (a) post-merge mission-level validation against the merged mission branch, (b) explicit cross-cutting changes that touch shared infrastructure, and (c) release-candidate verification. Each WP must declare its targeted test surface in the WP prompt's validation section so reviewers can confirm scope.

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

**All changes must land on `main` through a pull request. Direct pushes to `main` are never allowed — not for mission merges, hotfixes, doc updates, or any other reason.**

`main` has a **Protect Main Branch** GitHub Actions workflow that enforces this. A "Protect Main Branch: failure" on CI is a real failure, not an expected artifact. It means code bypassed the PR requirement and must be addressed.

### Agent Push Authorization (binding)

Agents are **not allowed** to push directly to `origin/main` under any circumstances. This includes `spec-kitty merge`.

**Required workflow for mission merges:**
1. Run `spec-kitty merge` locally — this merges lane branches into local `main`.
2. Immediately create a PR branch: `git checkout -b pr/<mission-slug>`
3. Push the PR branch: `git push origin pr/<mission-slug>`
4. Open a PR targeting `main`: `gh pr create --title "..." --body "..."`
5. Do **not** run `spec-kitty merge --push` or `git push origin main`.

**Required workflow for all other changes (hotfixes, docs, config):**
1. Start work on a named branch, never on `main` directly.
2. Push the branch and open a PR.
3. Never push `main` directly.

**When `safe_commit` refuses on a protected branch, agents must:**
1. Use the mission lane branch/worktree as intended by the workflow.
2. If planning artifacts need to land on `main`, create a PR branch instead of bypassing the guard.
3. Never silently work around the guard with raw git commands or `SPEC_KITTY_ALLOW_PROTECTED_BRANCH_COMMITS=1`.

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

- Required pytest surface passes (targeted packages for scoped changes; full suite only for the cases named in Testing Requirements)
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

## Pre-existing Failure Reporting Rule

1. When an agent encounters pre-existing test failures while working in this repository, the agent MUST open a GitHub issue reporting them before treating those failures as accepted baseline context or continuing past them. The issue must include the command run, the relevant failure summary, and why the agent believes the failures are pre-existing rather than introduced by its current change.

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

---

## Charter Resolution Hints

These declarations are read by `spec-kitty charter sync` (per FR-007 / FR-008 of mission
`wp-prompt-governance-payload-01KRR8HS`). They drive the action-scoped governance
resolver so that `spec-kitty charter context --action <name>` does not need to fall
back to runtime defaults. Keep this block up to date as the project adopts new
template sets, tools, or authority directories.

```yaml
template_set: software-dev-default
available_tools: [git, spec-kitty, pytest, mypy, ruff]
authority_paths:
  # Mission B dual-read (C-003): legacy + new homes listed together so the
  # authority-path read resolves both before and after the docs/ fold (WP03).
  # The legacy branches are dropped in WP08's reference sweep.
  - glossary/contexts/        # canonical terminology (legacy home)
  - docs/context/             # canonical terminology (new home, FR-009)
  - architecture/3.x/adr/    # canonical architectural decisions (legacy, 3.x era)
  - docs/adr/3.x/             # canonical architectural decisions (new home)
  - architecture/adrs/        # active ADR directory (legacy de-facto convention)
```

---

## Burn-down Policy (binding per HiC §5a.2 / C-004)

(a) Every mutable architectural allowlist is governed by a baseline in
`tests/architectural/_baselines.yaml`. Growth above baseline **FAILS CI**;
shrinkage WARNS (informational, non-fatal).

(b) `test_no_dead_modules._CATEGORY_7_GRANDFATHERED` (Cat-7) shrinks by ≥2
entries per major release; **target 0 by 4.0**.

(c) Pure-shim files (`test_compat_shims._ADAPTER_FILES`) **target 0 by 4.0**.

---

## `__all__` Declaration Convention (binding per C-007)

Every module under `src/charter/` and `src/kernel/` MUST declare `__all__`.
The symbol-level dead-code gate (`tests/architectural/test_no_dead_symbols.py`)
walks `__all__` and asserts every name has at least one caller in `src/`.

Future expansion to other subpackages is a per-mission scope decision.

---

## ATDD-First Discipline (binding per C-011)

Every implementation work package follows the red-green-refactor cycle.
The WP cannot start coding until at least one failing-first ATDD test
exists that pins the user-observable behaviour the WP delivers. The ATDD
test is committed as a separate commit (often the first commit of the lane)
**BEFORE** any implementation commits.

The reviewer verifies red→green: the test was RED on the WP's
`planning_base_branch` AND GREEN on the WP's final commit.

This mirrors Mission B's executable-contract pattern (the 7-file ATDD spec
at `bd95f1f5` was the canonical contract).
