# CLI Bug Sweep & Tool Surface Self-Registration

**Mission:** cli-bug-sweep-tool-surface-self-registration-01KV5AWE
**Type:** software-dev
**Status:** Specifying

---

## Background

Spec Kitty accumulates maintenance debt when bug fixes land without removing the temporary markers that masked them, when structural patterns enable recurring merge conflicts, and when validation tooling fails on valid repositories. This mission closes four such gaps, all surfaced during mission `tool-surface-contract-01KV2K2P` and its retrospective.

## Problem Statement

Four unresolved defects degrade contributor productivity and CI signal quality:

1. A test in `tests/adversarial/test_distribution.py` carries an `xfail` marker whose stated reason — that `spec-kitty init` prompts for agent strategy despite `--ai` being passed — is factually wrong. That bug was already fixed. The marker now suppresses all regression detection for the init-with-`--ai` code path.

2. The branch naming composer's idempotency guard (which prevents `mid8` double-appending) has no test coverage for the pathological case where the slug's embedded `mid8` differs from the `mission_id` argument. A silent double-append can occur without the test suite catching it.

3. `spec-kitty charter bundle validate` fails on any fresh checkout of the spec-kitty repository. The synthesizer writes generated doctrine artifacts into plural-named directories (`directives/`, `tactics/`, `styleguides/`), while the gitignore policy only whitelists singular names. Seven provenance sidecar placeholders were committed without the artifacts they reference, and the validator's early-exit logic does not account for the fresh-seed (`built_in_only: true`) manifest state.

4. Adding a provider to the tool surface subsystem requires hand-editing four co-located regions of a single coordinator file simultaneously. Every parallel-lane mission that adds a provider therefore produces a near-certain merge conflict on that file, requiring manual union resolution.

## Users

All four fixes affect **Spec Kitty contributors and maintainers** — people who run the test suite, extend the tool surface, validate charter state, or work on parallel lanes. There is no behavior change visible to operators who use the CLI to manage their own projects.

---

## User Scenarios & Testing

### Scenario 1 — Distribution test produces a clear signal
A contributor runs the distribution test suite. After this mission, `test_upgrade_updates_templates` produces a deterministic PASS or FAIL. If the init-with-`--ai` behavior regresses in the future, the test catches it immediately instead of masking it as an XFAIL.

### Scenario 2 — Branch naming handles all slug shapes correctly
A contributor's mission slug already ends with its own `mid8` (post-083 on-disk format). The branch naming system produces the correct single-suffix branch name. The test suite covers the matching case (slug mid8 equals argument mid8), the bare case (no mid8 in slug), and the pathological case (slug mid8 differs from argument mid8), with the pathological case's behavior explicitly asserted.

### Scenario 3 — Charter bundle validate passes on a fresh checkout
A contributor clones the spec-kitty repository and runs `spec-kitty charter bundle validate`. On a repository with no project-level synthesis state (built-in-only configuration), the command exits 0. No generated artifact files are expected or required.

### Scenario 4 — Two parallel lanes add providers without conflict
Two contributors working in parallel lanes each create a new tool surface provider. When their lanes are merged, there is no conflict in the central coordinator file — each provider declares its own registration in its own module, and the coordinator derives its configuration from the registration store at assembly time.

---

## Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | The `xfail` decorator and its accompanying comment on `TestUpgradeWithAllMissions::test_upgrade_updates_templates` in `tests/adversarial/test_distribution.py` must be removed. The test must run undecorated. | Proposed |
| FR-002 | A test must be added to the branch naming test suite covering the pathological case: a slug whose embedded `mid8` differs from the `mission_id` argument. The test must assert the exact output of that case so any future behavioral change is caught as an explicit test failure, not a silent regression. | Proposed |
| FR-003 | The function that maps doctrine kinds to their output subdirectory names must map each kind to its singular directory name (`directive`, `tactic`, `styleguide`), matching the gitignore whitelist and the existing tracked directory structure. | Proposed |
| FR-004 | The seven stale provenance sidecar files in `.kittify/charter/provenance/` that reference non-existent generated artifacts must be removed from the repository. These are placeholder records committed without corresponding artifact files. | Proposed |
| FR-005 | The charter bundle validator must recognize the built-in-only fresh-seed state — a manifest with `built_in_only: true` and an empty artifact list — and return successfully without checking for generated artifact files in that state. | Proposed |
| FR-006 | Adding a new tool surface provider must require only creating one new module. It must not require editing any central coordinator file, import list, kind-token mapping, provider-factory list, or definition-registration block. | Proposed |
| FR-007 | Each tool surface provider must declare its own registration — covering its kind tokens, definition factories, and any synthetic-key scope — within its own module. | Proposed |
| FR-008 | The provider registration mechanism must support providers that contribute multiple definitions (one-to-many), providers that register under a synthetic key rather than the standard per-tool-key fan-out, and providers that declare multiple CLI token aliases for a single kind. | Proposed |
| FR-009 | The tool surface coordinator must derive all provider configuration — kind-token mapping, provider list, and definition registration — entirely from the registration store. A conformance test must assert that the coordinator file contains no central provider literal lists. | Proposed |
| FR-010 | Provider registration ordering must be deterministic across Python processes. It must not depend on import order or filesystem enumeration order. | Proposed |

---

## Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | All modified and new code must pass the project's static type checker with zero errors and zero warnings. | 0 errors, 0 warnings | Proposed |
| NFR-002 | All modified and new code must pass the project's linter with zero issues. | 0 issues | Proposed |
| NFR-003 | New code paths introduced by the tool surface self-registration seam must be covered by tests at the level required by the project charter. | ≥ 90% branch coverage on new code | Proposed |
| NFR-004 | The tool surface refactor must not change the observable behavior of any existing tool surface CLI command or flag. Operators who invoke these commands must observe identical output before and after. | Zero behavioral regressions on existing tool surface CLI tests | Proposed |
| NFR-005 | The charter validation changes must not break existing charter bundle validate behavior for repositories that have committed synthesis artifacts (non-fresh-seed configurations). | All pre-existing charter validation tests pass unchanged | Proposed |

---

## Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | The provider discovery mechanism must use an explicit enumeration of provider modules, not a filesystem scan, in order to remain compatible with the project's dead-symbol static analysis gate. | Accepted |
| C-002 | The provider self-registration abstraction must support the full contract of every existing provider: including those that contribute multiple definitions and those that register under a synthetic key. No existing provider behavior may be silently dropped or altered. | Accepted |
| C-003 | The fix to the doctrine kind-to-subdirectory mapping must align synthesizer output to the existing tracked singular directory structure. The gitignore whitelist must not be changed to accommodate plural directories. | Accepted |
| C-004 | No new command-line flags, prompts, or configuration fields may be introduced. All four fixes are internal behavioral corrections with no new user-facing surface. | Accepted |

---

## Success Criteria

1. `tests/adversarial/test_distribution.py::TestUpgradeWithAllMissions::test_upgrade_updates_templates` produces PASS or FAIL — never XFAIL or XPASS — and a future regression in init-with-`--ai` is immediately visible as a test failure.
2. `spec-kitty charter bundle validate` exits 0 on a fresh clone of the spec-kitty repository with no project-level synthesis artifacts committed.
3. Two contributors can each add a separate tool surface provider in parallel lanes and complete a merge with zero conflicts in the coordinator file.
4. The full test suite passes with no new failures, type errors, or linter issues introduced by this mission.

---

## Domain Language

| Canonical term | Avoid |
|----------------|-------|
| built-in-only state | shipped-only, no-synthesis state |
| provenance sidecar | sidecar file, provenance record (these are acceptable as informal synonyms but the canonical form should be used in code and docs) |
| self-registration seam | auto-discovery (implies filesystem scan, which is prohibited by C-001) |
| kind token | kind string (the canonical user-facing term for the `--kind` argument values in tool surface commands) |

---

## Key Entities

| Entity | Description |
|--------|-------------|
| SurfaceRegistration | A declaration unit produced by each provider module carrying the provider's kind tokens, definition factories, and synthetic-key scope. The registration store aggregates these at import time. |
| Provenance sidecar | A YAML file in `.kittify/charter/provenance/` recording the synthesis lineage of a generated doctrine artifact. Sidecars are git-tracked; the artifacts they reference may or may not be tracked depending on project configuration. |
| Built-in-only state | A project configuration where all active doctrine artifacts are shipped with the spec-kitty package, not generated by `charter synthesize`. In this state no synthesized artifact files should be expected in the repository. |
| Dead-symbol gate | A static analysis test that asserts every named symbol in the codebase has at least one traceable non-test caller. Provider discovery must be traceable through an explicit import to pass this gate. |

---

## Assumptions

- The `_human_slug_for_mid8_branch` guard in `branch_naming.py` correctly handles the matching case (slug already ends in its own `mid8`). The new test required by FR-002 covers only the non-matching (pathological) case.
- The seven stale provenance sidecars being removed by FR-004 contain no information that cannot be reconstructed by re-running `charter synthesize`. They are bootstrap placeholders, not authoritative records.
- Aligning the synthesizer's kind-to-subdirectory mapping to singular names (FR-003) does not break any downstream `charter synthesize` consumer outside this repository.

---

## Out of Scope

- The `AI_CHOICES` / `AGENT_DIRS` fan-out pattern (a same-class dormant mask noted in issue #1950) is deferred to a follow-up mission.
- The `ensure_runtime()` bootstrap flakiness observed in some CI environments is a separate concern. If it manifests as a test failure after FR-001's xfail removal, it requires its own investigation.
- Issue #1951 (host-CLI ⇄ source provenance contract) was dropped from this mission as a maintainer-only concern; it is closed on GitHub as won't-fix.

---

## Related Issues

- Closes #1953 (stale xfail in test_distribution)
- Closes #1950 (tool_surface provider-discovery seam)
- Closes #1949 (branch_naming mid8 test coverage gap)
- Closes #1947 (charter bundle validate + gitignored artifacts)
- Dropped: #1951 (closed as won't-fix)
