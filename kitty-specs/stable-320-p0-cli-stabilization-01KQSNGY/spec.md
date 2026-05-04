# 3.2.0 Stable P0 CLI Stabilization

**Mission ID**: `01KQSNGYG5B5AGH90CB81JEVMG`
**Mission slug**: `stable-320-p0-cli-stabilization-01KQSNGY`
**Mission type**: `software-dev`
**Status**: Draft
**Target branch**: `main`
**Planning/base branch**: `main`
**Created**: 2026-05-04
**Input source**: `../start-here.md`
**Scoped issues**: #967, #904, #968, #964

---

## Primary Intent

Prepare the Spec Kitty CLI for the stable `3.2.0` release by fixing the remaining P0 stabilization bugs that make the command surface, review state, generated agent assets, and status-test confidence untrustworthy.

This mission is intentionally narrow. It follows the `v3.2.0a10` prerelease and the GitHub issue queue hygiene pass where PR #959 and PR #969 blockers were closed. The mission must not reopen or reimplement those fixed areas unless a current repro on this branch proves a regression.

The mission addresses four open release-blocking issue classes:

- #967: the status test suite can hang in bootstrap and emit paths.
- #904: a stale rejected `review-cycle-N.md` verdict can coexist with approved or done WP state.
- #968: retired `checklist` command leftovers can leave registries, templates, and generated command counts inconsistent.
- #964: generated Spec Kitty skill files can miss YAML frontmatter, including the Codex `.agents/skills/spec-kitty.advise/SKILL.md` repro.

The result must be stable-release evidence, not a broad runtime redesign. Fixes should be targeted, deterministic, and covered by focused regression tests for each issue.

## Product Decision: Rejected Review Verdicts

Spec Kitty must use a fail-closed policy for stale rejected review artifacts.

A WP must not silently move to `approved` or `done`, and mission review or merge signoff must not silently pass, when the latest applicable review-cycle artifact for that WP still has `verdict: rejected`.

Valid paths are:

1. The latest review-cycle artifact has a non-rejected terminal verdict, such as `approved`.
2. An explicit arbiter or orchestrator override is supplied, and Spec Kitty records that override durably in review-cycle metadata or a linked override artifact before the state transition is accepted.
3. The command fails before mutating state, with a diagnostic that names the WP, the latest rejected artifact, and the required repair or override action.

Warning-only behavior is not acceptable for stable `3.2.0`.

## User Scenarios & Testing

### Primary actors

| Actor | Description |
|---|---|
| CLI operator | Runs Spec Kitty mission, status, review, merge, install, and generation commands during release stabilization. |
| Agent orchestrator | Moves WPs through implementation and review lanes and must receive consistent review-state signals. |
| Release maintainer | Needs deterministic local and CI evidence before cutting stable `3.2.0`. |
| Contributor | Installs or regenerates Spec Kitty agent assets and expects no retired commands or malformed skills. |

### Scenario 1 - Status tests finish deterministically

**Given** the previously hanging status bootstrap and emit paths, **when** the relevant status tests run locally or in CI, **then** they finish within bounded timeouts and failures include actionable diagnostics instead of blocking indefinitely.

### Scenario 2 - Rejected review artifacts block unsafe WP completion

**Given** a WP whose latest review-cycle artifact has `verdict: rejected`, **when** an operator or agent attempts to move that WP to `approved` or `done`, **then** Spec Kitty fails before mutating state unless a supported explicit override is supplied and durably recorded.

### Scenario 3 - Mission review and merge detect review contradictions

**Given** a mission where a done or approved WP is contradicted by the latest rejected review-cycle artifact, **when** mission status, mission review, and merge preflight evaluate release readiness, **then** the contradiction is surfaced and stable-release unsafe paths are blocked.

### Scenario 4 - Retired checklist command stays retired

**Given** a fresh command or skill generation path, **when** Spec Kitty generates agent assets, **then** no active `spec-kitty.checklist*` command is generated and active registries, packaged templates, diagnostics, and command counts agree.

### Scenario 5 - Stale checklist files are handled intentionally

**Given** an older installation that still contains stale `spec-kitty.checklist*` command files, **when** upgrade or install cleanup runs, **then** the stale files are removed or ignored intentionally without resurrecting the retired command.

### Scenario 6 - Generated skill files have valid frontmatter

**Given** a fresh generated Spec Kitty skill surface, including Codex global `.agents/skills` output, **when** generated `SKILL.md` files are inspected by host agents, **then** each file has required YAML frontmatter or is generated through a documented host-accepted schema without warnings.

### Scenario 7 - Release evidence covers all scoped issues

**Given** all fixes are implemented, **when** the mission is accepted, **then** evidence exists for the status hang fix, review-verdict consistency gate, retired-checklist cleanup, generated-skill frontmatter, and fresh generation smoke validation.

## Functional Requirements

| ID | Requirement | Status |
|---|---|---|
| FR-001 | Spec Kitty must diagnose and fix the root cause of the #967 `tests/status` hang around bootstrap and emit paths, or isolate the cause at the fixture or adapter boundary with a narrowly justified deterministic fix. | Draft |
| FR-002 | The broad status test suite, or at minimum the previously hanging bootstrap and emit paths, must run with bounded local and CI timeouts so future hangs fail with diagnostics instead of blocking indefinitely. | Draft |
| FR-003 | When a WP is being moved to `approved` or `done`, Spec Kitty must inspect the latest applicable `review-cycle-N.md` artifact for that WP. | Draft |
| FR-004 | If the latest applicable review-cycle artifact has `verdict: rejected`, Spec Kitty must fail closed before mutating state unless a supported explicit override is used. | Draft |
| FR-005 | Failure diagnostics for rejected-review contradictions must name the WP, the latest rejected artifact, and the required repair or override action. | Draft |
| FR-006 | Mission status, mission review, and merge preflight must each surface review-cycle/WP lane contradictions and block stable-release unsafe paths when a done or approved WP still has a latest rejected review-cycle artifact. | Draft |
| FR-007 | Spec Kitty must provide a clear arbiter or orchestrator override path for intentionally superseding a rejected review. | Draft |
| FR-008 | Explicit review overrides must be persisted as structured state in review-cycle metadata or a linked override artifact so later operators can see that the rejected verdict was superseded. | Draft |
| FR-009 | The retired `checklist` command must not remain in active consumer command or skill registries if it is no longer packaged or generated. | Draft |
| FR-010 | Registry data, packaged command templates, generated command counts, runtime doctor expectations, installer cleanup, and docs or comments that name active command counts must agree. | Draft |
| FR-011 | Upgrade and install cleanup must intentionally remove or ignore stale `spec-kitty.checklist*` files from older installations without resurrecting the command. | Draft |
| FR-012 | Generated Spec Kitty skill files, including Codex `.agents/skills/.../SKILL.md` outputs, must include required YAML frontmatter or use a documented schema accepted by the host without warnings. | Draft |
| FR-013 | The `.agents/skills/spec-kitty.advise/SKILL.md` missing-frontmatter repro from #964 must be fixed. | Draft |
| FR-014 | Fresh install or generation tests must verify that no retired checklist command is generated, active registry entries match packaged templates, generated skill files have required frontmatter, and command or skill counts match reality. | Draft |
| FR-015 | The mission must verify a fresh generated command and skill surface from the local branch before acceptance. | Draft |

## Non-Functional Requirements

| ID | Requirement | Status |
|---|---|---|
| NFR-001 | Each scoped issue (#967, #904, #968, #964) must have focused regression coverage before acceptance. | Draft |
| NFR-002 | Status test fixes must preserve status semantics; any timeout or fixture hardening must fail in 30 seconds or less for the previously hanging paths during validation. | Draft |
| NFR-003 | Tests added or changed by this mission must be local and deterministic by default, requiring no hosted auth, tracker, SaaS sync, or network access. | Draft |
| NFR-004 | If any command path intentionally touches hosted auth, tracker, SaaS, or sync behavior on this computer, it must run with `SPEC_KITTY_ENABLE_SAAS_SYNC=1`. | Draft |
| NFR-005 | Any JSON-producing command touched by this mission must continue to emit parseable JSON on stdout, with warnings and diagnostics routed so JSON output remains valid. | Draft |
| NFR-006 | The mission must keep the change set small enough for a stable-release blocker: targeted fixes, fixture hardening, and consistency checks are preferred over broad refactors. | Draft |
| NFR-007 | New code must satisfy the project charter expectations for pytest coverage of new behavior and strict type checking where applicable. | Draft |

## Constraints

| ID | Requirement | Status |
|---|---|---|
| C-001 | Only GitHub issues #967, #904, #968, and #964 are in implementation scope. | Draft |
| C-002 | Lower-priority issues #848, #662, #825, #595, #771, #630, #629, #631, #726, #728, #729, #644, #740, #323, #306, #303, and #317 are out of scope unless a current test failure proves they directly block one of the four scoped issues. | Draft |
| C-003 | PR #959 stabilization work must not be reimplemented unless a current repro on this branch proves a regression. | Draft |
| C-004 | PR #969 stabilization work must not be reimplemented unless a current repro on this branch proves a regression. | Draft |
| C-005 | Active user-facing command names must not be renamed unless required to remove the retired checklist surface. | Draft |
| C-006 | The mission must not change `spec-kitty-saas`, tracker provider behavior, hosted auth, or direct sync protocols. | Draft |
| C-007 | The canonical product term is Mission; new user-facing language must not introduce legacy domain-object aliases for active systems. | Draft |

## Key Entities

| Entity | Definition |
|---|---|
| Mission | The canonical unit of Spec Kitty work moving through specify, plan, tasks, implement, review, accept, and merge. |
| Work Package (WP) | A task package whose lane and review state determine whether implementation can advance. |
| Review-cycle artifact | A `review-cycle-N.md` record that captures the latest terminal review verdict for a WP. |
| Arbiter/orchestrator override | Structured evidence that an authorized operator intentionally superseded a rejected review verdict. |
| Command registry | The active inventory that determines which Spec Kitty commands are installed, generated, counted, and diagnosed. |
| Generated skill file | A host-agent skill package output, including Codex `.agents/skills/.../SKILL.md`, that must satisfy host metadata requirements. |

## Success Criteria

| ID | Criterion |
|---|---|
| SC-001 | The previously hanging status bootstrap and emit paths complete under a 30-second timeout with actionable failure output if they regress. |
| SC-002 | A WP with latest `verdict: rejected` cannot silently become `approved` or `done`; it is either blocked before mutation or superseded by a durable explicit override. |
| SC-003 | Mission status, mission review, and merge preflight cannot pass silently when a done or approved WP is contradicted by a latest rejected review-cycle artifact. |
| SC-004 | A fresh generated command and skill surface contains zero active `spec-kitty.checklist*` commands. |
| SC-005 | Active command and skill registry counts, packaged templates, installer cleanup, runtime diagnostics, and generated outputs agree in fresh generation tests. |
| SC-006 | Generated `SKILL.md` files include required YAML frontmatter, and the #964 Codex skill repro no longer emits missing-frontmatter warnings. |
| SC-007 | Local verification evidence is sufficient to close #967, #904, #968, and #964. |

## Assumptions

- The user-provided `../start-here.md` brief is authoritative discovery input for this mission.
- The intended branch contract is `main` for current branch, planning/base branch, and final merge target.
- `software-dev` is the correct mission type.
- PR #959 and PR #969 are treated as already fixed unless a current repro on this branch proves a regression.
- Hosted SaaS, tracker, auth, and sync behavior are not required for the default tests in this mission.

## Suggested Work Packages

### WP01 Status Test Hang Stabilization

Investigate #967, identify the hanging condition, add bounded diagnostics, and make the status bootstrap and emit suite reliable.

### WP02 Review Verdict Consistency Gate

Implement the fail-closed stale rejected verdict policy for #904, including explicit override behavior and regression tests.

### WP03 Retired Checklist Command Cleanup

Fix #968 by removing retired `checklist` from active registries and counts while preserving cleanup for stale installed files.

### WP04 Generated Skill Frontmatter

Fix #964 by ensuring generated skills include valid frontmatter and by adding generation tests for Codex/global skill outputs.

### WP05 Fresh Surface Smoke And Release Evidence

Run focused local validation proving all four issue classes are fixed together and collect release-ready evidence.

## Verification Guidance

Run focused tests first, then broader relevant gates:

```bash
uv run pytest tests/status -q --timeout=30
uv run pytest tests/post_merge tests/review tests/tasks -q
uv run pytest tests/runtime tests/specify_cli -q
uv run ruff check src tests
uv run mypy --strict src/specify_cli src/charter src/doctrine
```

The exact test selection may be adjusted based on touched files, but acceptance must include the previously hanging status paths under a timeout and fresh command/skill generation evidence.
