# Mission Specification: Worktree-Owned Root for Mission Create/Next

**Mission Branch**: `fix/worktree-owned-root-3328-v2` (coordination branch: `kitty/mission-worktree-owned-root-3328-01KZRG01`)
**Created**: 2026-08-11
**Status**: Draft
**Input**: User description: "Mission create/next cannot target the invoking worktree-owned root safely" — core issue [#3328](https://github.com/Priivacy-ai/spec-kitty/issues/3328), child of [#3129](https://github.com/Priivacy-ai/spec-kitty/issues/3129) ("Design: scoped shadow workspaces — the shared root behind 14 open worktree/write-path issues"), sibling of [#3128](https://github.com/Priivacy-ai/spec-kitty/issues/3128) ("Mission-mutating commands should fail closed when invoked from a checkout the mission does not own"), cross-linked with [#1907](https://github.com/Priivacy-ai/spec-kitty/issues/1907) (immutable-artifact validation hazard), and blocking Priivacy-ai/spec-kitty-saas#836 / draft PR Priivacy-ai/spec-kitty-saas#864.

## Problem Statement

`spec-kitty agent mission create` and `spec-kitty next` cannot explicitly target the invoking linked worktree as the mission's owned checkout.

Today, two independent and materially different refusal mechanisms gate mission-mutating commands against worktree invocation:

1. `create_mission_core()` (`src/specify_cli/core/mission_creation.py:309-314`) refuses whenever `is_worktree_context(Path.cwd())` is true, regardless of what `repo_root` the caller actually passed. `is_worktree_context()` (`src/specify_cli/core/paths.py:281-328`) is git-topology-generic — it follows the `.git` file's `gitdir:` pointer, so it recognizes any linked worktree, not only ones under `.worktrees/`.
2. `next` (`src/specify_cli/cli/commands/next_cmd.py:60`), `merge`, and `implement` are gated by `@require_main_repo` (`src/specify_cli/core/context_validation.py:190-216`), which calls `detect_execution_context()` (lines 65-111). That detector recognizes **only** the literal `.worktrees` path segment — a generic linked worktree created with `git worktree add /elsewhere/path` (not under `.worktrees/`) is invisible to it and is served normally, silently resolving state through whatever `locate_project_root()` returns.

Both refusal mechanisms are disconnected from the actual write target: every root-resolution helper in the codebase (`locate_project_root`, `get_main_repo_root`, `resolve_canonical_root`, `resolve_canonical_repo_root`) unconditionally collapses a worktree caller's location to the **primary checkout** ("ambient fallback"). This is intentional and correct for read-only status/dossier surfaces (`get_status_read_root`, `resolve_canonical_root` — see `tests/contract/test_canonical_root_when_in_worktree.py`, `tests/unit/workspace/test_root_resolver.py`), but it means there is no way for a command to say "yes, I mean *this* worktree, and I have validated that it is legitimately mine to write into." The only escape hatch, `allow_worktree_context=True` on `create_mission_core()`, bypasses the CWD guard with **zero validation of the caller-supplied `repo_root`** — it is deliberately restricted to test-only call sites and fenced by an architectural AST test (`tests/architectural/test_no_production_worktree_guard_bypass.py`) that fails the build if any `src/` file ever passes it. It is not, and must not become, a production affordance.

Consequently, an agent operating from a legitimate linked worktree — the normal shape of multi-agent, multi-lane, or SaaS-integrated operation — is either flatly refused (mission create, `.worktrees`-style locations reaching `next`) or silently served through the primary checkout (`next` for generic linked worktrees, since `require_main_repo`'s detector misses them). Neither outcome is safe: refusal blocks legitimate concurrent operation; silent redirection risks the exact cross-contamination #3129 documents (two agents' mission artifacts, refs, and runtime state landing in one shared checkout because the runtime trusted ambient location over explicit declaration).

This mission is the narrow, create/advance-time repair: give `mission create` and `next` an **explicit, git-topology-validated** way to target the invoking worktree as the mission's owned root, while preserving the existing fail-closed default for every caller that does not ask for this explicitly. It does not adopt the shadow-workspace redesign #3129 sketches (out of scope by that issue's own text), and it does not implement the post-ownership caller-vs-declared-workspace guard #3128 describes (that guard activates *after* ownership exists; this mission establishes ownership at creation/advancement time).

## User Scenarios & Testing *(mandatory)*

<!--
  "Users" here are spec-kitty CLI callers — human operators and AI agents driving
  the mission lifecycle from a linked worktree, plus the operators/CI that must be
  able to trust the refusal behavior for callers who have NOT asked for worktree
  ownership. Each story is independently testable against the real installed CLI.
-->

### User Story 1 - Agent creates and advances a mission from its own linked worktree (Priority: P1)

An agent (or operator) working inside a legitimate linked worktree — created by `git worktree add`, under any path, not only `.worktrees/<name>` — explicitly declares that worktree as the mission's owned checkout, creates a mission there, and advances it with `next`, without being redirected to or contending with the primary checkout or any other worktree.

**Why this priority**: This is the exact capability #3328 exists to add, and the capability SaaS #836/#864's real two-worktree concurrency proof depends on. Without it, every other acceptance criterion in this mission is unreachable.

**Independent Test**: In a real Git repository (not a fixture double), create a second linked worktree with `git worktree add <path> <branch>` at an arbitrary path outside `.worktrees/`. From inside it, run the real installed `spec-kitty` CLI with the new explicit-ownership affordance to create a mission and advance it once with `next`. Assert the mission's files, refs, and runtime state land under that worktree's own checkout and nowhere else.

**Acceptance Scenarios**:

1. **Given** a clean linked worktree at an arbitrary (non-`.worktrees`) path, whose `.git` file's `gitdir:` pointer resolves to the same `git rev-parse --git-common-dir` as the primary checkout, **When** the operator runs `mission create` with the new explicit-ownership flag from inside that worktree, **Then** the mission is created with its coordination/lane refs and `.kittify/runtime/` state rooted in that worktree, and the primary checkout and every other worktree remain byte-for-byte unchanged (`git status --short` clean in all three).
2. **Given** the mission created in Scenario 1, **When** the operator runs `spec-kitty next --mission <slug> --json` from inside the same worktree, **Then** `next` resolves the mission's owned root to that worktree (not the primary), returns a valid decision, and does not write into the primary checkout's `.kittify/runtime/feature-runs.json`.
3. **Given** two agents in two separate real linked worktrees, each created with `git worktree add` at generic (non-`.worktrees`) paths, **When** both run `mission create` and `next` concurrently, with process start/end timestamps forced to overlap, **Then** each produces a distinct mission ID, slug, ref set, and runtime-state file; neither worktree's files or state appear in the other's tree or in the primary checkout; and `git status --short` is clean in all three trees after both processes exit.

---

### User Story 2 - Default invocation from an unowned or ambiguous worktree remains refused (Priority: P1)

An agent that has **not** explicitly declared worktree ownership, or whose worktree fails topology validation, gets the same fail-closed refusal the codebase already provides today — no regression, no silent redirection, no new bypass.

**Why this priority**: The binding design constraint is "no ambient-root fallback… no production `allow_worktree_context=True` bypass." A new ownership affordance that weakens the existing default is a regression, not a fix, and would reopen exactly the silent-cross-contamination failure mode #3129 documents.

**Independent Test**: Run `mission create` and `next` from a linked worktree without the new explicit-ownership affordance and confirm both still refuse (create) or still behave exactly as today (next's existing `.worktrees`-literal detector), with no observable behavior change for callers who do not opt in.

**Acceptance Scenarios**:

1. **Given** a linked worktree under `.worktrees/<name>`, **When** `mission create` is run without the new ownership flag, **Then** it refuses with the existing `MissionCreationError` message ("Cannot create missions from inside a worktree…"), unchanged.
2. **Given** a nested worktree (a worktree created from inside another worktree's checkout, or whose `.git` gitdir-pointer resolves to a common-dir that does **not** match the invoking process's own `git rev-parse --git-common-dir`), **When** the new ownership flag is supplied, **Then** the command refuses with a structured, named error distinguishing "nested/foreign topology" from the plain "invoked from a worktree" case — it must NOT fall through to ambient-primary resolution.
3. **Given** a foreign worktree — a linked worktree of a *different* git repository entirely (unrelated common-dir) — pointed at as the target via the new flag, **When** the command runs, **Then** it refuses; the mismatched common-dir is named in the error.
4. **Given** a generic linked worktree path (not under `.worktrees/`) invoking `next` **without** the new ownership affordance, **When** `next` runs, **Then** behavior is unchanged from pre-mission baseline (ambient resolution to primary, exactly as today) — this mission does not retrofit `next`'s existing unscoped behavior into a refusal for callers who never opted in; it only adds the explicit, validated opt-in path.

---

### User Story 3 - No leaked locks or cross-worktree ref/state collisions after concurrent runs (Priority: P1)

After two agents finish concurrent, worktree-owned mission create/advance operations, no shared mutable artifact (lock file, ref, runtime-state record) is left in a state that would block, corrupt, or misattribute a third operation.

**Why this priority**: This is the acceptance bar SaaS #836 reruns against an immutable core artifact; a repair that proves isolation only while both processes are alive, and leaks state once they exit, does not satisfy the issue.

**Independent Test**: After both processes in User Story 1 Scenario 3 exit, inspect the shared git-common-dir lock namespace (`spec-kitty-locks/`), the coordination/mission refs, and each worktree's `.kittify/runtime/` directory. Assert no stale lock file remains, no ref collision occurred, and each worktree's runtime state names only its own mission.

**Acceptance Scenarios**:

1. **Given** the two concurrent runs from User Story 1 Scenario 3 have both exited (including non-zero-exit / interrupted paths), **When** the shared `spec-kitty-locks/` directory under the git common-dir is inspected, **Then** it contains no lock file whose holder process has exited (no orphaned `FileLock`).
2. **Given** the same two runs, **When** `git for-each-ref` is run against the shared object store, **Then** each mission's coordination/lane refs are distinct and neither run's ref overwrote or shadowed the other's.
3. **Given** the same two runs, **When** each worktree's own `.kittify/runtime/feature-runs.json` (or equivalent per-checkout runtime-state file) is inspected, **Then** it names only the mission created in that worktree — never the sibling worktree's mission.

### Edge Cases

- What happens when the invoking worktree's `.git` file exists but its `gitdir:` target has been deleted or corrupted (e.g., the worktree was removed with `rm -rf` instead of `git worktree remove`)? → Must refuse with a distinguishable error (not a `KeyError`/`FileNotFoundError` traceback), naming the broken pointer.
- How does the system handle a caller supplying the new ownership flag from the **primary checkout itself** (not a worktree at all)? → Must succeed unchanged (the primary checkout trivially "owns" itself); this is the existing `repo_root == worktree_root` case `safe_commit`'s docstring already documents.
- How does the system handle two *sequential* (not concurrent) worktree-owned mission creates in the same worktree, second one after the first mission is already `done`/committed? → Must succeed independently; no cross-mission state bleed within one worktree.
- What happens if the common-dir comparison (`git rev-parse --git-common-dir` from both the invoking worktree and the resolved primary) itself fails (e.g., git binary missing, corrupted repo)? → Must fail closed with a structured error, never silently fall back to treating the checkout as unowned-but-permitted.
- What happens when `SPECIFY_REPO_ROOT` is set in the environment at the same time as the new explicit-ownership flag, and they disagree? → The spec must state which wins; the plan phase resolves this against `locate_project_root()`'s existing precedence (`SPECIFY_REPO_ROOT` is documented as authoritative today) and documents any deliberate override.
- What happens if the `.venv`/wheel install used for validation is an editable install rather than the required immutable wheel? → Out of scope for this mission's implementation, but the validation plan itself (WP04) must refuse to accept editable-install evidence as satisfying the immutable-artifact acceptance criterion (per #1907's packaging/editable-install hazard).

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Explicit checkout-scope affordance for `mission create` | As an agent in a linked worktree, I want an explicit way to declare that worktree as the mission's owned root, so that I can create a mission there without ambient redirection or refusal. | High | Open |
| FR-002 | Explicit checkout-scope affordance for `next` | As an agent that created a mission in a worktree, I want `next` to recognize and honor that same explicit ownership, so that mission advancement stays rooted in the checkout that owns it. | High | Open |
| FR-003 | Git-topology ownership validation (generic linked worktrees) | As the runtime, I want to validate the invoking worktree's identity against the resolved primary's git common-dir before accepting ownership, so that only a genuinely-linked, non-nested, non-foreign worktree is accepted — regardless of its path naming convention. | High | Open |
| FR-004 | Preserve existing fail-closed default | As an operator relying on today's refusal behavior, I want every caller who does not explicitly request worktree ownership to be refused/redirected exactly as before, so that this mission introduces no regression and no new bypass. | High | Open |
| FR-005 | Refuse nested worktree topology | As the runtime, I want to refuse when the target worktree is itself nested inside another worktree's checkout, so that ownership cannot be claimed through an invalid topology. | High | Open |
| FR-006 | Refuse foreign/mismatched-common-dir topology | As the runtime, I want to refuse when the target worktree's common-dir does not match the resolved primary's common-dir, so that a worktree belonging to an unrelated repository can never be accepted as owned. | High | Open |
| FR-007 | Per-checkout runtime state isolation | As the runtime, I want mission runtime state (e.g., `feature-runs.json`-equivalent tracking, merge-lock directories) to be rooted in the explicitly-owned checkout rather than the ambiently-resolved primary, so that two worktree-owned missions never share or overwrite each other's runtime records. | High | Open |
| FR-008 | Per-checkout mission-content/ref isolation | As the runtime, I want mission-creation writes (coordination/lane refs, mission directory scaffolding) and subsequent explicitly-owned `next` mission-content reads/writes to stay in the explicitly-owned checkout's namespace, so that no other worktree or the primary checkout receives unintended files or becomes a fallback read authority. | High | Open |
| FR-009 | Thread `repo_root`/`worktree_root` through `safe_commit` for owned-checkout writes | As the implementer, I want mission-create's commit path to pass the correct, distinct `repo_root` (canonical common repository topology) and `worktree_root` (the explicitly-owned invocation checkout) into `safe_commit`, so that its existing `_is_worktree_of` git-topology check is exercised at create time, not only inside the coordination-worktree code path that already does this. | High | Open |
| FR-010 | No production `allow_worktree_context=True` bypass | As the codebase's own architectural fence enforces today, I want the new ownership affordance to be a distinct, validated, named mechanism — not a relaxation of `allow_worktree_context` into production use — so that `tests/architectural/test_no_production_worktree_guard_bypass.py` continues to hold (or is deliberately and visibly retired only if the guard itself is replaced by validation-based resolution, per that test's own documented intent). | High | Open |
| FR-011 | Structured, distinguishable refusal errors | As an agent/harness consuming CLI output, I want refusal reasons (plain worktree invocation without opt-in, nested topology, foreign/mismatched common-dir, broken gitdir pointer) to be structurally distinguishable — not one generic string — so that automation can branch on the failure class. | Medium | Open |
| FR-012 | Real installed-CLI, two-linked-worktree concurrency ATDD proof | As the acceptance authority for this issue, I want an automated test that builds/installs the CLI as an immutable artifact (never an editable install), creates two real linked worktrees via `git worktree add`, forces temporal overlap of two subprocess invocations, and asserts distinct mission IDs/slugs/refs/runtime state with no cross-write and clean trees afterward, so that the fix is proven against the real CLI surface rather than mocked or command-shaped evidence. | High | Open |
| FR-013 | Negative/adversarial test coverage | As the acceptance authority, I want negative tests for foreign targets, mismatched common-dirs, generic (non-`.worktrees`) linked-worktree paths, and nested-worktree misuse, so that the refusal paths are proven, not merely assumed from the positive path. | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Validation must not regress read-path performance | Git common-dir/topology validation added at create/advance time must add no more than one additional `git rev-parse` subprocess invocation per command, measured against current `mission create`/`next` baseline subprocess counts. | Performance | Medium | Open |
| NFR-002 | Concurrency proof runs deterministically in CI | The two-linked-worktree concurrency ATDD test (FR-012) must pass deterministically across at least 20 consecutive local runs with forced overlap (e.g., barrier/sleep synchronization) before being accepted as evidence — no flaky pass counted as satisfying the acceptance criterion. | Reliability | High | Open |
| NFR-003 | No production code path may construct `allow_worktree_context=True` | Static/AST enforcement (existing or extended `tests/architectural/test_no_production_worktree_guard_bypass.py`) must continue to fail the build if any `src/` file passes `allow_worktree_context=True`. | Security | High | Open |
| NFR-004 | Fail-closed on git-tooling failure | Any git subprocess failure during topology/common-dir validation (missing git binary, corrupted repo, permission error) must result in refusal, never in silent fallback to unvalidated ambient resolution. | Reliability | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Fail-closed default preserved | No change may weaken the current default refusal for callers that do not explicitly request worktree ownership. | Technical | High | Open |
| C-002 | No ambient-root fallback for the new affordance | The new explicit-ownership resolution path must never silently substitute the primary checkout when validation fails; it must refuse. | Technical | High | Open |
| C-003 | No shadow-workspace redesign | This mission implements the narrow create/advance-time ownership repair only; it does not adopt the scoped shadow-workspace topology #3129 describes as a structural alternative. | Business | High | Open |
| C-004 | Immutable artifact validation only | End-to-end concurrency evidence (FR-012) must be produced against an installed, immutable wheel/candidate artifact built from the reviewed core commit — never an editable (`pip install -e .`) install. | Technical | High | Open |
| C-005 | No production/provider/tracker mutation in this mission | This mission's implementation and validation must not touch production systems, secrets, SaaS sync, or perform releases, merges, pushes, or PR creation as a side effect of proving the fix. | Regulatory | High | Open |
| C-006 | Generic linked-worktree recognition required | The ownership-validation mechanism must recognize any git-linked worktree via topology (gitdir-pointer + common-dir), not only paths under the `.worktrees/<name>` convention — closing the gap `coordination/surface_resolver.classify_worktree_topology`'s `.worktrees`-literal-only detector currently leaves open. | Technical | High | Open |

### Key Entities

- **Owned checkout**: The specific git worktree (primary or linked) that a mission-mutating command has been explicitly and validly told to treat as its write root for a given invocation. Distinguished from "canonical common repository topology" (the shared object store/common-dir all worktrees of one repo share) and from "ambiently resolved primary" (today's default collapse target).
- **Checkout ownership validation result**: The outcome of comparing the invoking worktree's git identity (its `.git` gitdir pointer, its own `git rev-parse --show-toplevel` / `--git-common-dir`) against the resolved primary's common-dir — one of: owned (accepted), unowned-no-opt-in (existing refusal, unchanged), nested (new refusal), foreign/mismatched (new refusal), broken-pointer (new refusal).
- **Per-checkout runtime state**: Runtime bookkeeping (`feature-runs.json`-equivalent, merge-lock directories) rooted under the owned checkout's own `.kittify/runtime/` rather than the ambiently-resolved primary's — distinct from the intentionally-shared cross-worktree status lock (`status/locking.py`, which stays rooted at the shared common-dir by design and is out of scope for relocation).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An agent in any real linked worktree (any path, not only `.worktrees/<name>`) can explicitly create and advance a mission rooted in that worktree, with zero files or state appearing in the primary checkout or any sibling worktree, verified by `git status --short` clean in all trees.
- **SC-002**: Two agents running the real installed CLI concurrently in two separate linked worktrees, with forced temporal overlap, produce two missions with zero shared/collided identifiers (mission ID, slug, ref names, runtime-state file contents) across 20 consecutive deterministic runs.
- **SC-003**: Every caller that does not explicitly request worktree ownership is refused or behaves exactly as it does today — zero observable regression in the existing `mission create` / `next` / `merge` / `implement` worktree-invocation behavior for non-opted-in callers.
- **SC-004**: 100% of the four defined negative/adversarial ownership-validation scenarios (nested, foreign, broken-pointer, opt-in-without-validation-passing) produce a distinguishable refusal, verified by dedicated tests.
- **SC-005**: The end-to-end concurrency proof runs against an immutable installed artifact whose provenance (source commit SHA, wheel SHA-256, build options) is recorded and reproducible — zero acceptance of editable-install or mocked-CLI evidence.
