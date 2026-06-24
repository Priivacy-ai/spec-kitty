# Mission Specification: Decompose agent/tasks.py god-module

**Mission ID**: 01KVWVARJKSH9T2QNHJVE4ZC7Y
**Slug**: decompose-agent-tasks-god-module-01KVWVAR
**Mission type**: software-dev
**Target branch**: main
**Source**: [Priivacy-ai/spec-kitty#2058](https://github.com/Priivacy-ai/spec-kitty/issues/2058) (parent #1797); scope addition from PR #2060 adversarial review
**Created**: 2026-06-24

---

## Overview

`src/specify_cli/cli/commands/agent/tasks.py` is a proven god-module — **4633 LOC, maxCC ~178** — the highest-complexity of the three "crime-scene" god-modules (`merge` / `mission` / `tasks`) identified by metric shift in the 3.2.x forensic review. It accrued **47 bugfix commits** in `v3.1.10..v3.2.0`, confirming it is where defects actually cluster.

This mission decomposes the module into cohesive, independently-testable seams while **preserving the public `agent tasks` CLI surface exactly**. It additionally centralizes commit routing surfaced by the PR #2060 post-merge review: three planning-commit tails open-code their routing instead of going through the canonical `commit_for_mission` router. (Phase 0 research found the original "silently skips → coord worktree" framing outdated — see `research.md §3` — so the work is re-aimed at router centralization with byte-identical output.)

The mission opens with a **research phase (Phase 0)** that proposes and validates the seam boundaries before any code is moved — two design decisions (the no-regression verification strategy and the residual-size target) are deliberately deferred to that phase.

---

## User Scenarios & Testing

The "users" of this surface are (a) the AI coding agents that drive the `agent tasks` workflow and (b) the spec-kitty maintainers who fix defects in this module.

### Scenario 1 — Agent runs `agent tasks` commands unchanged (behavior preservation)
An AI agent invokes any `agent tasks` subcommand (status, outline, materialize packages, finalize, map-requirements, etc.) with the same arguments and flags it uses today. **Expected:** identical command names, flags, output, and exit codes before and after the decomposition. The agent observes no difference.

### Scenario 2 — Maintainer fixes a defect in a single seam
A maintainer needs to change the package-materialization logic. **Expected:** the relevant logic lives in a focused, separately-importable module with its own tests, so the maintainer can locate it, change it, and verify it in isolation — without navigating a 4600-line file or running the entire CLI integration suite.

### Scenario 3 — Planning commit on a protected primary branch (router centralization, output-preserving)
An agent triggers a WP/subtask status commit, or the `map-requirements` commit tail, while the primary branch is protected. **Expected (after this mission):** the commit decision is made by the single canonical `commit_for_mission` router (not by a bespoke per-call `is_protected` pre-check), and the **user-visible error message and exit code are byte-identical to today** — the router result is mapped back to the existing message text at the call site. **Why it matters:** the routing decision is centralized (removing duplicated guard logic that drifts), with zero observable change to the agent.

> Research note: the original #2058/PR-2060 "silently skips → should route to coord worktree" framing is **outdated**. The protected-primary refusal (→ "use a feature branch") was already introduced by WP02/WP03, and the tails are already kind-aware. This mission centralizes the *routing path* through `commit_for_mission` while preserving the current messages verbatim. See `research.md §3`.

### Edge cases
- A seam is invoked with malformed/partial input → parsing-validation helpers reject it with the same error message and exit code as today.
- A subcommand depends on another seam's output (e.g. finalize consumes outline) → seam composition preserves current ordering and data flow.
- Commit routing on a non-protected/normal branch → behavior unchanged (commits land as before).

---

## Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | The public `agent tasks` CLI surface — command names, subcommand names, arguments, flags, help text semantics, output structure, and exit codes — MUST remain unchanged after decomposition. | Approved |
| FR-002 | A top-of-file decomposition pointer comment referencing issue #2058 MUST be added to `agent/tasks.py`, matching the convention already applied for #2056 (`agent/mission.py`) and #1623 (`doctor.py`). | Approved |
| FR-003 | The module MUST be decomposed into cohesive, independently-importable seams. Research-resolved seam set: `tasks_outline`, `tasks_materialization`, `tasks_finalize_validation`, `tasks_dependency_graph`, `tasks_parsing_validation`, plus the residual `tasks.py` command-registration shim (final layout confirmable in plan). The 6 mega-functions (`move_task`, `status`, `map_requirements`, `_validate_ready_for_review`, `mark_status`, `finalize_tasks`) MUST be internally decomposed, not merely relocated. | Approved |
| FR-004 | Each extracted seam MUST carry focused tests that execute its logic directly (not only via broad CLI integration tests). | Approved |
| FR-005 | `agent/tasks.py` MUST be reduced toward a thin command-registration shim, delegating substantive logic to the extracted seams. | **Partial** — the pure/helper logic was relocated into 5 seams, but the 6 mega-function command bodies were NOT internally decomposed (see FR-003/NFR-004 notes). `tasks.py` is 3365 LOC, not the ≤~1200 shim target. The binding ruff `C901`/Sonar `S3776` ceiling (maxCC ≤15) IS met. Residual body-thinning deferred — follow-up #2116. |
| FR-006 | The **three** planning-commit tails — `move_task` WP-file commit (`tasks.py:2486`), `mark_status` tasks.md commit (`tasks.py:3131`), and the `map_requirements` WP-file commit (`tasks.py:3947`) — MUST route through `commit_for_mission` (`coordination/commit_router.py`) instead of open-coding `resolve_placement_only`+`safe_commit` (and, for the third, the `_planning_commit_worktree` import from `mission.py`). Tail 3 MUST thread `target_branch=` for the WP09 ff-advance. | Approved |
| FR-007 | The bespoke `is_protected` pre-checks — `_skip_target_branch_commit()`, `_protected_branch_status_commit_error()`, their guard conditionals in `move_task`/`mark_status` — to be deleted once the tails route through `commit_for_mission`. | **DEFERRED** — the spec's premise (these are "now superseded by the router") was **incorrect**. `commit_for_mission` runs *after* the WP-file write and only governs the commit step (it returns `no_op_wrong_surface` → exit 1). `_skip_target_branch_commit` governs a distinct, load-bearing **command-flow** arm the router cannot reproduce: in the coord-topology + protected-primary case it (a) suppresses the WP-file write entirely, (b) reshapes the `--json` envelope (`wp_file_update: skipped`, coord `status_events_path`, `frontmatter_fields_skipped`), (c) drives the `WP_METADATA_UNSUPPORTED_ON_PROTECTED_COORD_BRANCH` loud-rejection gate, and (d) **succeeds with exit 0** (the status event on the coord branch is authoritative). Naive deletion would convert this exit-0 silent-skip to the router's exit-1 refusal — a behavior change that breaks pinned regression #1615-1618 (`test_issue_1615_1616_1617_1618.py::TestIssue1618MoveTaskGuard`) and violates C-003 byte-identity. Literal deletion / true consolidation (teaching the router the exit-0 coord arm + envelope reshaping) is a router-contract change affecting all callers — out of scope for this behavior-neutral mission. Tracked as follow-up #2116. The 3 commit tails DO route through `commit_for_mission` (FR-006 ✓); the pre-check remains only as the command-flow gate, not as a duplicate commit-routing authority. |
| FR-008 | The protected-primary error message text and exit code surfaced by all three tails MUST remain byte-identical to current behavior: the `commit_for_mission` `no_op_wrong_surface` result MUST be mapped back to the existing message strings at the call site. A regression test MUST prove (a) each tail reaches git only via `commit_for_mission`, and (b) the protected-primary message/exit code is preserved verbatim. Extend the existing `test_wp03_bypass_writers_fr008.py` rather than duplicating it. | Approved |

## Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | Cyclomatic complexity of every function in the residual `agent/tasks.py` AND every extracted function MUST satisfy the repo ceiling. | maxCC ≤ 15 (ruff C901 / Sonar S3776 aligned) | Approved |
| NFR-002 | New and extracted code MUST meet the charter coverage bar. | ≥ 90% line coverage on new/changed code | Approved |
| NFR-003 | Static analysis MUST pass with zero new issues introduced by this mission. | `ruff check` clean; `mypy --strict` clean; no new blanket suppressions | Approved |
| NFR-004 | Residual size target for the `agent/tasks.py` shim (research-resolved). | `agent/tasks.py` ≤ ~1200 LOC (from 4633); ~1800 LOC of helper logic relocated into the 5 seams. The binding constraint is NFR-001 (maxCC ≤15); the LOC figure is the realistic floor given the genuine orchestration the 9 command bodies carry. | **Partial / honest miss** — **actual `tasks.py` = 3365 LOC**, ~2.8× the ≤~1200 target. The 5 seams (`tasks_outline` 229, `tasks_materialization` 287, `tasks_finalize_validation` 324, `tasks_dependency_graph` 200, `tasks_parsing_validation` 997) hold genuine extracted logic, but the 6 mega-function command bodies were NOT internally decomposed, so the residual is far above the shim target. The **binding** constraint NFR-001 (maxCC ≤15) IS met: `ruff check --select C901` is clean on all 6 modules. Body-thinning toward the ≤~1200 shim is deferred — follow-up #2116. |

## Constraints

| ID | Constraint | Status |
|----|-----------|--------|
| C-001 | No command-name, subcommand-name, or flag changes — the public `agent tasks` contract is frozen for this mission. | Approved |
| C-002 | Commit routing MUST use the canonical `commit_for_mission` router; bespoke per-call protected-branch guards MUST NOT be reintroduced (regression class per CLAUDE.md "use canonical sources"). | Approved |
| C-003 | The decomposition MUST be fully behavior-preserving, **including** the commit-routing centralization: the protected-primary message text and exit codes stay byte-identical (FR-008). No opportunistic behavior changes anywhere. | Approved |
| C-004 | No new `# noqa`, `# type: ignore`, or per-file ignore additions to pass gates; fix the code instead (narrowly-justified exceptions only, with inline rationale). | Approved |
| C-005 | No-regression verification strategy (research-resolved): **golden CLI characterization tests MUST be captured BEFORE refactoring** (command names, flags, help text, exit codes, `--json` envelope), then kept green throughout. The existing 72 unit tests are import-based and would mask contract drift, so they are necessary but not sufficient. | Approved |
| C-006 | `mission.py`'s own use of `_planning_commit_worktree` is OUT OF SCOPE — this mission only removes `tasks.py`'s dependency on it. | Approved |

---

## Success Criteria

| ID | Criterion |
|----|-----------|
| SC-001 | The existing `agent tasks` test suite passes with zero regressions before and after the change. |
| SC-002 | `agent/tasks.py` maxCC drops from ~178 to ≤ 15 (every function) — **MET** (`ruff --select C901` clean). The file shrinks to ≤ ~1200 LOC — **NOT met**: actual 3365 LOC (the mega-function bodies were not internally decomposed; body-thinning deferred, follow-up #2116). Helper logic lives in the 5 seams — MET. |
| SC-003 | All three planning-commit tails reach git only via `commit_for_mission` — **MET** (AST-asserted router-only). Protected-primary message text + exit codes byte-identical (FR-008) — MET. "No bespoke `is_protected` pre-checks remain" — **NOT met / DEFERRED**: `_skip_target_branch_commit` / `_protected_branch_status_commit_error` are retained because they govern the coord-topology exit-0 silent-skip command-flow arm the router cannot reproduce (see FR-007 note). They are no longer a duplicate commit-routing authority. Follow-up #2116. |
| SC-006 | A golden CLI characterization test (captured pre-refactor) pins the `agent tasks` command/flag/exit-code/`--json` contract and passes unchanged post-refactor. |
| SC-004 | Every extracted seam is exercised by focused, directly-importing tests at ≥90% coverage on new code. |
| SC-005 | The decomposition pointer comment referencing #2058 is present at the top of `agent/tasks.py`. |

---

## Key Entities

- **`agent/tasks.py` shim** — the residual command-registration module; declares the typer commands and delegates to seams.
- **Extracted seam modules** — `tasks_outline`, `tasks_materialization`, `tasks_finalize_validation`, `tasks_dependency_graph`, `tasks_parsing_validation` (research-resolved set).
- **`commit_for_mission` router** (`coordination/commit_router.py`) — the canonical entry point for planning commits; the three tails route through it.
- **Planning-commit tails** — the three call sites: `move_task` (`tasks.py:2486`), `mark_status` (`tasks.py:3131`), `map_requirements` (`tasks.py:3947`).

---

## Assumptions

- The current `tasks.py` on `main` (commit `c3814ec5a`, 4633 LOC) is the authoritative version to decompose.
- `commit_for_mission` already implements the protected-primary → coordination-worktree routing the tails should adopt (per PR #2060 mission 01KVMBD6).
- Extracted seams may live in a new internal package adjacent to `agent/tasks.py`; the exact layout is a research/plan decision and does not affect the public CLI contract.
- "Independently testable" means each seam can be imported and exercised without spinning up the full CLI app.

---

## Research outcomes (Phase 0 — see `research.md`)

All Phase-0 questions are resolved; the spec above reflects the answers:

1. **Seam boundaries** — Resolved: 5 seams + shim (FR-003). The 6 mega-functions need internal decomposition.
2. **Residual-size target (NFR-004)** — Resolved: ≤ ~1200 LOC, with maxCC ≤15 as the binding constraint.
3. **No-regression strategy (C-005)** — Resolved: capture golden CLI characterization tests before refactoring.
4. **Dependency-graph wiring** — Resolved: low risk; `core/dependency_graph.py` has no cycle with the CLI layer; its two call sites stay in the shim.
5. **Commit-router fit** — Resolved: 3 tails (not 4), already kind-aware; route through `commit_for_mission` and **preserve the protected-primary message text verbatim** (FR-006/007/008, C-003). Tail 3 must thread `target_branch=`.

**Residual risk carried into `/spec-kitty.plan`:** the mission is large (~1800 LOC moved + 6 mega-functions decomposed + golden-test capture + ~410 LOC new tests) and should be sliced into independently-mergeable WPs in dependency order (one per seam + commit-routing + golden-test capture).
