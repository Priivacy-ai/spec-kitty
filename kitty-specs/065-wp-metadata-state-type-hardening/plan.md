# Implementation Plan: WP Metadata & State Type Hardening

**Branch**: `feature/metadata-state-type-hardening` | **Date**: 2026-04-06 | **Spec**: [spec.md](spec.md)  
**Research**: [research.md](research.md) | **Data Model**: [data-model.md](data-model.md)

---

## Summary

Three related structural defects in the WP layer are addressed together because they share a root cause (WP data treated as unvalidated string bags) and their fixes reinforce each other:

1. **#417** (bug): `finalize-tasks --validate-only` silently writes frontmatter before the dry-run fork. Fix: guard `write_frontmatter()` calls with `not validate_only` at `feature.py:1620`; document all 8 mutated fields.
2. **#410** (enhancement): `tasks.md` header regex doesn't match `####` depth (silent F015 parse failure); WP frontmatter has no schema. Fix: standardize 5 regex sites to `#{2,4}`; introduce `WPMetadata` Pydantic model in `status/wp_metadata.py`; migrate 15+ consumers; tighten to `extra="forbid"`.
3. **#405** (enhancement): Lane transition logic scattered across 46 files with 358 string literals. Fix: `WPState` ABC + 9 concrete classes + `TransitionContext` dataclass in `status/`; property test harness proves equivalence; migrate `orchestrator_api`, `next/decision`, `dashboard/scanner`.
4. **CI (WP07)**: Extract status test suite into a dedicated parallel CI stage, laying the foundation for further core sub-module splits.

---

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: Pydantic v2 (already present), ruamel.yaml (frontmatter), pytest, typer  
**Storage**: Filesystem only (YAML frontmatter in `.md` files, JSONL event log)  
**Testing**: pytest; property-based equivalence tests (explicit enumeration, not Hypothesis)  
**Target Platform**: Linux/macOS developer environment + GitHub Actions CI  
**Project Type**: Single Python package (`src/specify_cli/`)  
**Performance Goals**: `WPState` construction < 1 ms; snapshot materialization regression < 5%  
**Constraints**: Event log JSONL format byte-identical; old `validate_transition()` API preserved for non-migrated consumers

---

## Doctrine Check

*Applicable artifacts from issues #405, #410, and #417.*

### Governing Procedures

| Artifact | Path | Applies to |
|----------|------|-----------|
| Refactoring discipline | `src/doctrine/procedures/shipped/refactoring.procedure.yaml` | WP03–WP06: 5-step discipline (identify smell → select tactic → smallest steps → verify preservation → commit separately) |
| Test-first bug fixing | `src/doctrine/procedures/shipped/test-first-bug-fixing.procedure.yaml` | WP01: understand bug → choose test level → write failing test → verify it fails for right reason → fix → full suite → commit together |

### Tactics

| Artifact | Path | Applies to |
|----------|------|-----------|
| State Pattern for Behavior | `src/doctrine/tactics/shipped/refactoring/refactoring-state-pattern-for-behavior.tactic.yaml` | WP05: primary extraction; its 6 steps map to the WPState design |
| Encapsulate Record | `src/doctrine/tactics/shipped/refactoring/refactoring-encapsulate-record.tactic.yaml` | WP03: replace raw `dict[str, Any]` frontmatter access with typed model; WP05: replace `wp_states: dict[str, Any]` accesses |
| Extract First-Order Concept | `src/doctrine/tactics/shipped/refactoring/refactoring-extract-first-order-concept.tactic.yaml` | WP03: `WPMetadata` is the hidden concept behind 15+ `.get()` calls; WP05: `TransitionContext` from the implicit 8-arg kwargs bag |
| Strangler Fig | `src/doctrine/tactics/shipped/refactoring/refactoring-strangler-fig.tactic.yaml` | WP04: `extra="allow"` coexists with legacy dict access; tighten after migration. WP06: new State Object built alongside old procedural API |
| Apply Smallest Viable Diff | `src/doctrine/tactics/shipped/change-apply-smallest-viable-diff.tactic.yaml` | All WPs: one consumer migration per commit in WP04 and WP06 |
| Entity–Value Object Classification | `src/doctrine/tactics/shipped/entity-value-object-classification.tactic.yaml` | WP03/WP05: confirms `WPMetadata`, `TransitionContext`, and concrete `WPState` instances are value objects (`frozen=True`, equality by attributes, no identity) |
| Connascence Analysis | `src/doctrine/tactics/shipped/connascence-analysis.tactic.yaml` | WP05: dominant coupling is CoM (46 files sharing lane string semantics); extraction reduces to CoN (single import) |
| ADR Drafting Workflow | `src/doctrine/tactics/shipped/adr-drafting-workflow.tactic.yaml` | WP05: the State Pattern vs. alternatives decision must be captured in an ADR before implementation (per Directive 003) |
| Acceptance Test First | `src/doctrine/tactics/shipped/acceptance-test-first.tactic.yaml` | WP01–WP06: spec acceptance scenarios (Given/When/Then) drive ATDD; write acceptance test before implementation |
| TDD Red-Green-Refactor | `src/doctrine/tactics/shipped/tdd-red-green-refactor.tactic.yaml` | WP03, WP05: unit-level complement to ATDD for new model/ABC creation |
| Quality Gate Verification | `src/doctrine/tactics/shipped/quality-gate-verification.tactic.yaml` | All WPs: run focused tests → static gates → coverage → separate introduced vs inherited failures |
| Test Boundaries by Responsibility | `src/doctrine/tactics/shipped/test-boundaries-by-responsibility.tactic.yaml` | WP05: draw test scope boundaries for property test harness (real vs stubbed boundaries) |
| ZOMBIES TDD | `src/doctrine/tactics/shipped/zombies-tdd.tactic.yaml` | WP05: Zero/One/Many/Boundary/Interface/Exception/Simple progression for 9 concrete state classes |

### Directives

| Artifact | Path | Implication |
|----------|------|------------|
| 001 Architectural Integrity Standard | `src/doctrine/directives/shipped/001-architectural-integrity-standard.directive.yaml` | Justifies both extractions: "cross-boundary interactions mediated by explicit interfaces" |
| 003 Decision Documentation Requirement | `src/doctrine/directives/shipped/003-decision-documentation-requirement.directive.yaml` | WPState design decision (ABC vs Protocol, module placement) must be in an ADR in WP05 |
| 032 Conceptual Alignment | `src/doctrine/directives/shipped/032-conceptual-alignment.directive.yaml` | Pin "lane" vs "state" vs "status" as canonical domain terms before building the WPState API |
| 034 Test-First Development | `src/doctrine/directives/shipped/034-test-first-development.directive.yaml` | Property test harness (WP05) must be written before any consumer migration (WP06) |
| 030 Test and Typecheck Quality Gate | `src/doctrine/directives/shipped/030-test-and-typecheck-quality-gate.directive.yaml` | All WPs: tests and type checks must pass before `for_review` handoff (`enforcement: required`) |
| 025 Boy Scout Rule | `src/doctrine/directives/shipped/025-boy-scout-rule.directive.yaml` | All WPs: leave touched files in slightly better state — address SonarCloud smells proportional to task scope (`enforcement: advisory`) |

---

## Cross-Cutting: Boy Scout Cleanup (DIRECTIVE_025)

SonarCloud reports 99 issues in mission 065 files (66 CRITICAL, 34 MAJOR). The following
mechanical fixes apply when the file is already open for mission work. These are committed
alongside the WP that modifies each file — never in isolation.

**Tier 1 — Quick wins (< 10 min each):**
- `requirement_mapping.py:88` — extract duplicated regex to module constant (WP04)
- `orchestrator_api/commands.py:135` — handle empty except clause (WP06)
- `status/emit.py:441` — remove unused `repo_root` param (WP02)
- `dashboard/scanner.py:278` — remove unused `features` param (WP04/WP06)
- `dashboard/handlers/api.py:159` — rename reassigned `path` variable (WP08)
- `acceptance.py:448` — remove unused `use_legacy` variable (WP04)
- `dashboard.js:629` — remove unused `artifactKey` variable (WP08)
- `dashboard.js:1151` — `.find()` → `.some()` (WP08)
- `dashboard.js:307` — `isNaN()` → `Number.isNaN()` (WP08)
- `dashboard.js:132` — use `RegExp.exec()` instead of `match()` (WP08)

**Tier 2 — Moderate wins (10-20 min each):**
- `orchestrator_api/commands.py` — extract 3 duplicated help strings to constants (WP06)
- `status/transitions.py` — extract 2 duplicated error messages to constants (WP05/WP06)
- `acceptance.py:313-317` — extract 6 duplicated artifact filenames to constants (WP04)
- `dashboard.js` — 9 optional chaining fixes, 8 Promise rejection fixes (WP08)

**NOT in scope:** Cognitive complexity reduction on functions > 50 complexity. These
require dedicated refactoring missions. Mission 065 changes to `feature.py` (complexity
247) and `tasks.py` (complexity 155) are localized and do not justify rewriting those
functions (per DIRECTIVE_024 Locality of Change constraint).

---

## Cross-Cutting: Self Observation Protocol

Agents working on this mission (implementation, review, or coordination) must write
structured work logs to `work/observations/` during WP execution. These logs enable
post-mission analysis of agent behavior, tooling friction, and system-level issues.

**Directory**: `work/observations/` (gitignored via `/work/`)

**When to write**: At the end of each WP implementation or review session, and whenever
a noteworthy observation occurs mid-session (tooling bug, unexpected codebase state,
doctrine ambiguity, spec gap, coordination friction, etc.).

**File naming**: `065-<wp>-<agent>-<date>.md` (e.g., `065-wp03-opencode-2026-04-07.md`)

**Required sections**:

```markdown
# Observation Log: WP<nn> — <title>

**Agent**: <agent name>
**Date**: <ISO date>
**Session**: implement | review | coordination

## Work Summary
<What was accomplished, what was attempted, what was deferred>

## Observations
<Numbered list of noteworthy observations — tooling issues, spec gaps,
doctrine friction, unexpected codebase state, coordination problems, etc.>

## Recommendations
<Optional: suggestions for process/tooling/doctrine improvements>
```

**Scope**: This protocol is advisory — it must not block WP progression. If an agent
cannot write the log (e.g., context limit), it should note this in the WP activity log
instead. The `work/observations/` directory is distinct from `work/implementation-observations/`
(which holds pre-task review notes from the planning phase).

---

## Project Structure

### Documentation (this mission)

```
kitty-specs/065-wp-metadata-state-type-hardening/
├── spec.md          ✓ created
├── plan.md          ✓ this file
├── research.md      ✓ created
├── data-model.md    ✓ created
└── tasks.md         → /spec-kitty.tasks
```

### Source Code (affected paths)

```
src/specify_cli/
├── cli/commands/agent/
│   ├── feature.py           WP01 (validate-only fix), WP02 (regex fix)
│   └── tasks.py             WP02 (regex fix)
├── status/
│   ├── emit.py              WP02 (regex fix)
│   ├── models.py            WP05 (add Lane.IN_REVIEW)
│   ├── transitions.py       WP05 (update transitions, guards, aliases, canonical lanes)
│   ├── transition_context.py  WP05 (NEW: TransitionContext + ReviewResult)
│   ├── wp_metadata.py         WP03 (NEW)
│   └── wp_state.py            WP05 (NEW)
├── orchestrator_api/
│   └── commands.py          WP06 (consumer migration)
├── next/
│   └── decision.py          WP06 (consumer migration)
├── dashboard/
│   ├── scanner.py           WP04 (WPMetadata), WP06 (WPState consumer migration)
│   ├── handlers/            WP08 (TypedDict response construction)
│   └── api_types.py         WP08 (NEW: TypedDict response shapes)
├── [15+ other modules]      WP04 (WPMetadata consumer migration)
├── tasks_support.py         WP06 (LANES dedup)
└── scripts/tasks/
    └── task_helpers.py      WP06 (LANES dedup, remove stale 4-lane tuple)

architecture/                WP05 (ADR for State Pattern + in_review promotion design decision)

.github/workflows/
└── ci-quality.yml           WP07 (new fast-tests-status + integration-tests-status stages)

docs/
├── explanation/kanban-workflow.md  WP05 (update to 9-lane model)
├── status-model.md                WP05 (update to 9-lane model)
└── 2x/runtime-and-missions.md     WP05 (update state machine reference)

README.md                    WP05 (update Mermaid state diagram to 9-lane model)
CLAUDE.md                    WP05 (update stale 7-lane section to 9-lane model)

tests/specify_cli/status/
├── test_wp_metadata.py      WP03/WP04 (NEW)
├── test_wp_state.py         WP05 (NEW — property equivalence harness)
└── test_transition_context.py  WP05 (NEW)

tests/test_dashboard/
└── test_api_contract.py     WP08 (NEW — TypedDict ↔ JS key contract test)
```

---

## Work Package Breakdown

Dependencies govern sequencing. `WP02` and `WP07` are independent and can start immediately. `WP08` depends on WP04 and WP06 completing.

```
WP01 (validate-only fix)
├── WP02 (regex fix)              ← independent of WP03+
├── WP03 (WPMetadata model)
│   └── WP04 (consumer migration + extra=forbid)
│       └── WP08 (dashboard API TypedDict contracts)  ← also depends on WP06
└── WP05 (WPState + TransitionContext + property tests)
    └── WP06 (consumer migration: orchestrator_api, next/decision, dashboard)
        └── WP08 (dashboard API TypedDict contracts)
WP07 (CI stage split)             ← independent of all above
```

### WP01 — Validate-Only Bootstrap Fix (#417)

**Scope**: Guard `write_frontmatter()` calls in `finalize_tasks()` with `not validate_only`; audit and document the full mutation surface; update the JSON output schema (remove `bootstrap` key from validate-only response); add/update tests for the guard.

**Files**: `src/specify_cli/cli/commands/agent/feature.py` (lines 1583–1622), `tests/specify_cli/` (finalize-tasks tests)

**Key change** (from research.md Finding 1):
```python
if frontmatter_changed and not validate_only:   # add "and not validate_only"
    write_frontmatter(wp_file, frontmatter, body)
    updated_count += 1
```

**Acceptance**: `git diff` empty after `--validate-only` invocation; JSON output contains no `bootstrap.newly_seeded` mutations field; tests cover the guard in both modes.

**Doctrine**: `test-first-bug-fixing.procedure.yaml` (canonical bug fix flow); `acceptance-test-first.tactic.yaml` (spec scenarios drive test); `refactoring.procedure.yaml` (identify smell, apply targeted fix); `change-apply-smallest-viable-diff.tactic.yaml`.

---

### WP02 — tasks.md Header Regex Standardization (#410)

**Scope**: Update 5 regex sites across 3 files to accept `##`, `###`, and `####` WP headers (no deeper). Add regression tests for each depth.

**Files**:
- `src/specify_cli/cli/commands/agent/feature.py:1953` — `_parse_wp_sections_from_tasks_md()`
- `src/specify_cli/status/emit.py:148,151` — `_infer_subtasks_complete()`
- `src/specify_cli/cli/commands/agent/tasks.py:305,310` — subtask checker

**Pattern changes** (from research.md Finding 2):
- Header match: `^#{2,4}` prefix instead of `^##` or `^###`
- Section boundary: `^#{2,4}\s+` instead of `^##\s+`

**Acceptance**: `finalize-tasks` correctly parses `dependencies` from a `tasks.md` using `#### WP01` headers; existing `##` / `###` behavior unchanged.

**Doctrine**: `acceptance-test-first.tactic.yaml` (spec scenarios drive test); `change-apply-smallest-viable-diff.tactic.yaml`; `034-test-first-development.directive.yaml`.

---

### WP03 — WPMetadata Pydantic Model (#410)

**Scope**: Create `src/specify_cli/status/wp_metadata.py` with `WPMetadata` Pydantic v2 model (`frozen=True`, `extra="allow"`) and `read_wp_frontmatter()` loader. Add CI test that validates all active WP files in `kitty-specs/` pass `WPMetadata.model_validate()` without modification.

**Files**: `src/specify_cli/status/wp_metadata.py` (NEW), `src/specify_cli/status/__init__.py`, `tests/specify_cli/status/test_wp_metadata.py` (NEW)

**Model fields**: See `data-model.md → WPMetadata`.

**Acceptance**: All `kitty-specs/` WP files pass CI validation; `read_wp_frontmatter()` raises `ValidationError` on a malformed WP file; unknown extra fields are preserved (round-trip safe).

**Doctrine**: `tdd-red-green-refactor.tactic.yaml` (new model creation); `acceptance-test-first.tactic.yaml`; `refactoring-encapsulate-record.tactic.yaml`; `refactoring-extract-first-order-concept.tactic.yaml`; `entity-value-object-classification.tactic.yaml`; `refactoring-strangler-fig.tactic.yaml` (`extra="allow"` coexists with legacy).

---

### WP04 — WPMetadata Consumer Migration + extra=forbid (#410)

**Scope**: Migrate all consumer modules from `frontmatter.get("...")` to `wp_meta.<field>`. After all consumers migrated and CI test passes, change `extra="allow"` → `extra="forbid"`. One consumer migration per commit.

**Consumer modules** (from issue #410 + code sweep):
- `dependency_graph.py`
- `cli/commands/agent/feature.py` (WP frontmatter reads)
- `task_profile.py`
- `dashboard/scanner.py`
- `acceptance.py`
- `status/bootstrap.py`
- `requirement_mapping.py`
- Others identified during implementation

**Acceptance**: `grep -r 'frontmatter\.get\|\.get("work_package_id\|\.get("dependencies\|\.get("title"' src/specify_cli/` returns no matches (outside `frontmatter.py` itself); `WPMetadata` is `extra="forbid"`; full test suite passes; dashboard `/api/features` and `/api/kanban/{id}` endpoints return identical JSON structure and values before and after migration (NFR-006).

**Doctrine**: `quality-gate-verification.tactic.yaml` (per-commit verification during consumer migration); `refactoring-strangler-fig.tactic.yaml`; `change-apply-smallest-viable-diff.tactic.yaml` (one consumer per commit); `001-architectural-integrity-standard.directive.yaml`.

---

### WP05 — WPState ABC + TransitionContext + Property Tests (#405)

**Scope**: Create `src/specify_cli/status/wp_state.py` (WPState ABC + 9 concrete classes + factory) and `src/specify_cli/status/transition_context.py` (TransitionContext). Promote the `in_review` alias to a first-class `Lane.IN_REVIEW` enum member with `InReviewState` concrete class, resolving the parallel-execution review contention blind spot (FR-012a, FR-012b). Update `ALLOWED_TRANSITIONS` and `_GUARDED_TRANSITIONS` accordingly; remove the `in_review` alias from `LANE_ALIASES`. Write ADR (per Directive 003) for the design decision. Write property test harness proving transition equivalence with the updated `ALLOWED_TRANSITIONS` + `_run_guard()` for all allowed pairs and guard-relevant combinations.

**Baseline note after upstream rebase**: Review-feedback persistence and prompt handoff guidance are already present in the current baseline (`workflow.py`, `orchestrator_api/commands.py`, and `docs/explanation/kanban-workflow.md`). WP05 remains responsible for canonical lane/state modeling and read-model surfacing of review evidence through `WPState` / `TransitionContext`, but it must extend that behavior rather than redesigning or replacing the newly landed review-handoff semantics.

**Files**: `status/wp_state.py` (NEW), `status/transition_context.py` (NEW), `status/models.py` (add `Lane.IN_REVIEW`), `status/transitions.py` (update transitions, guards, aliases, canonical lanes), `tests/specify_cli/status/test_wp_state.py` (NEW), `architecture/` (ADR), `README.md` (Mermaid state diagram), `docs/explanation/kanban-workflow.md` (lane definitions + transition table), `docs/status-model.md` (state machine section), `docs/2x/runtime-and-missions.md` (state machine reference), `CLAUDE.md` (stale 7-lane section update)

**Interface**: See `data-model.md → WPState` and `TransitionContext`.

**Acceptance**: Property tests pass and prove identical transition matrix; `wp_state_for(lane)` returns correct concrete class for all 9 lanes; `WPState.is_terminal` matches `TERMINAL_LANES`; `WPState.allowed_targets()` matches `ALLOWED_TRANSITIONS`; `for_review` is a pure queue state (outbound: `in_review`, `blocked`, `canceled` only); `in_review` carries the reviewer's active-work transitions; `(for_review, in_review)` transition has actor-required guard with conflict detection; all outbound `in_review` transitions require a structured `ReviewResult`; ADR committed before any consumer migration; all lane model documentation updated to 9-lane model (FR-012d).

**Doctrine**: `tdd-red-green-refactor.tactic.yaml` (new ABC creation); `zombies-tdd.tactic.yaml` (Zero/One/Many progression for 8 state classes); `test-boundaries-by-responsibility.tactic.yaml` (property test scope); `refactoring-state-pattern-for-behavior.tactic.yaml` (6-step extraction); `refactoring-extract-first-order-concept.tactic.yaml` (TransitionContext); `entity-value-object-classification.tactic.yaml`; `connascence-analysis.tactic.yaml`; `003-decision-documentation-requirement.directive.yaml` (ADR required); `032-conceptual-alignment.directive.yaml` (pin terminology); `034-test-first-development.directive.yaml` (property tests before migration).

---

### WP06 — WPState Consumer Migration (High-Touch Trio) (#405)

**Scope**: Migrate `orchestrator_api/commands.py`, `next/decision.py`, and `dashboard/scanner.py` to use `WPState` methods. Deduplicate the 3 `LANES` tuple definitions (import from canonical `status` package; remove stale 4-lane tuple in `scripts/tasks/task_helpers.py`).

**Baseline note after upstream rebase**: `orchestrator_api/commands.py` now already exposes review-handoff evidence and stricter review transition semantics (`--review-ref`, policy/evidence validation). WP06 must preserve those behaviors and their tests while replacing raw lane-string branching with `WPState` usage. This WP is no longer allowed to treat `orchestrator_api/commands.py` as a pre-review-evidence baseline.

**Files**: `orchestrator_api/commands.py`, `next/decision.py`, `dashboard/scanner.py`, `tasks_support.py`, `scripts/tasks/task_helpers.py`

**Key eliminations**:
- `_RUN_AFFECTING_LANES = frozenset(["claimed", "in_progress", "for_review"])` in `orchestrator_api/commands.py` → `state.affects_run` property or an equivalent canonical helper, without weakening the current review/policy guard behavior
- `if current_lane == "planned" / elif "claimed"` cascades → `state.allowed_targets()` / `state.progress_bucket()`
- 4-lane `LANES` tuple in `task_helpers.py` → removed

**Acceptance**: `grep -r 'current_lane ==' src/specify_cli/orchestrator_api src/specify_cli/next src/specify_cli/dashboard` returns zero matches; full test suite passes; old `validate_transition()` still callable by non-migrated consumers; dashboard kanban lane bucketing produces identical results via `WPState.display_category()` (NFR-006).

**Doctrine**: `quality-gate-verification.tactic.yaml` (per-commit verification); `refactoring-strangler-fig.tactic.yaml` (old API preserved); `change-apply-smallest-viable-diff.tactic.yaml` (one consumer per commit); `001-architectural-integrity-standard.directive.yaml`.

---

### WP07 — Status Test Suite CI Stage Split

**Scope**: Add `fast-tests-status` and `integration-tests-status` CI jobs to `.github/workflows/ci-quality.yml`. Update `fast-tests-core` and `integration-tests-core` to ignore `tests/status/` and `tests/specify_cli/status/`. The new stage runs in parallel with `fast-tests-doctrine` and `fast-tests-core`.

**Files**: `.github/workflows/ci-quality.yml`

**New CI graph** (from research.md Finding 4):
```
kernel-tests
├── fast-tests-doctrine     (unchanged)
├── fast-tests-status       (NEW: tests/status/ + tests/specify_cli/status/)
└── fast-tests-core         (modified: --ignore these paths)
    ├── integration-tests-doctrine    (unchanged)
    ├── integration-tests-status      (NEW: needs fast-tests-status + fast-tests-core)
    └── integration-tests-core        (modified: same ignores)
```

**Acceptance**: New CI jobs run; `fast-tests-core` no longer runs status tests (verified by job output); total wall-clock time for fast stages does not increase.

**Note**: This WP is independent of all others and can be implemented at any point during the mission.

---

### WP08 — Dashboard API TypedDict Contracts (#361 Phase 1)

**Scope**: Define `TypedDict` response shapes in `src/specify_cli/dashboard/api_types.py` for all JSON dashboard endpoints (~5 endpoints, ~4 distinct response shapes). Migrate handler methods in `dashboard/handlers/` to construct responses through these types (type annotation only — no behavioral change). Write a pytest contract test that validates the JS frontend (`dashboard.js`) references the same response keys the Python types declare. Apply Boy Scout fixes to `dashboard.js` (optional chaining, proper Error rejection, unused vars) and `dashboard/handlers/api.py` (variable shadowing).

**Baseline note after upstream rebase**: Review-feedback evidence exposure is already documented and partially surfaced in the current baseline. WP08 is strictly responsible for dashboard/API contract typing and the human-facing rendering of canonically sourced review feedback. It must not introduce new persistence semantics or re-specify how `review_ref` is recorded.

**Files**: `src/specify_cli/dashboard/api_types.py` (NEW), `src/specify_cli/dashboard/handlers/features.py`, `src/specify_cli/dashboard/handlers/api.py`, `src/specify_cli/dashboard/static/dashboard/dashboard.js`, `tests/test_dashboard/test_api_contract.py` (NEW)

**TypedDict definitions**: See `data-model.md → Dashboard API Response Types`.

**Acceptance**: All JSON dashboard endpoints construct responses through `TypedDict` types; `mypy` passes on handler files; contract test validates JS ↔ Python key alignment; `dashboard.js` SonarCloud issues reduced (optional chaining, Error rejection, unused vars).

**Doctrine**: `030-test-and-typecheck-quality-gate.directive.yaml` (mypy on handlers); `025-boy-scout-rule.directive.yaml` (JS cleanup); `change-apply-smallest-viable-diff.tactic.yaml`.

---

## Sequencing Summary

| WP | Depends on | Can run in parallel with |
|----|-----------|--------------------------|
| WP01 | — | WP07 |
| WP02 | WP01 | WP03, WP07 |
| WP03 | WP01 | WP02, WP05, WP07 |
| WP04 | WP03 | WP05, WP07 |
| WP05 | WP01 | WP02, WP03, WP07 |
| WP06 | WP05 | WP04, WP07 |
| WP07 | — | all |
| WP08 | WP04, WP06 | WP07 |
