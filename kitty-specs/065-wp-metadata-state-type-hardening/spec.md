# Mission Specification: WP Metadata & State Type Hardening

**Mission Branch**: `feature/metadata-state-type-hardening`
**Created**: 2026-04-06
**Status**: Draft
**Upstream issues**: #417 (bug), #410 (enhancement), #405 (enhancement), #361 (enhancement — Phase 1 only)
**Related issues (not in scope)**: #418 (bug — hardcoded branch template), #422 (task-generation ownership inference), #423 (lane computation parallelism collapse)

## Background

Three related structural problems exist in the work-package layer of spec-kitty:

1. **#417** — `finalize-tasks --validate-only` violates its own contract: bootstrap runs unconditionally, silently rewriting WP frontmatter (`dependencies`, `branch_strategy`, and potentially more fields) before the validate/commit fork. Users who invoke `--validate-only` to confirm a manual repair find their repair destroyed.

2. **#410** — WP frontmatter (`tasks/WP*.md`) has no formal schema. All 15+ consuming modules read it as `dict[str, Any]` via raw `.get()` calls with no validation. Separately, `tasks.md` header parsing is duplicated in four places with mismatched depth expectations (`##`, `###`, none match `####`), causing silent dependency-parse failures when LLM-generated files use deeper headings.

3. **#405** — Lane/status transition logic is scattered across 46 files with 358 hardcoded lane string literals. Three separate `LANES` tuple definitions exist (one stale at 4 lanes). All intelligence about what a lane *can do* lives in module-level data structures and procedural guard functions rather than in the `Lane` enum itself.

These three issues share a root: the WP layer treats its own data structures as bags of unvalidated strings rather than typed domain objects.

## User Scenarios & Testing

### User Story 1 — Safe Feature State Inspection (Priority: P1)

A developer has manually patched WP frontmatter (e.g., restored stripped `dependencies` fields) and wants to confirm the feature is in a valid state before committing. They run `finalize-tasks --validate-only` expecting a read-only report.

**Why this priority**: This is a correctness bug. The current behavior silently destroys manual repairs, making it impossible to safely verify feature state. Fixing it unblocks all users who rely on `--validate-only` as a safe inspection tool.

**Independent Test**: Run `--validate-only` against a feature with manually edited WP frontmatter; verify `git diff` shows no changes afterward.

**Acceptance Scenarios**:

1. **Given** a WP file with manually set `dependencies: [WP01, WP02]`, **When** `finalize-tasks --validate-only` runs, **Then** the `dependencies` field is unchanged on disk and `git diff` is empty.
2. **Given** any feature, **When** `finalize-tasks --validate-only` runs, **Then** no files on disk are modified (zero `git diff` output, no new commits).
3. **Given** `--validate-only` is invoked, **When** the feature has validation errors, **Then** errors are reported in the output without modifying any files.

---

### User Story 2 — Bootstrap Mutation Transparency (Priority: P1)

A developer runs `finalize-tasks` (without `--validate-only`) and wants to understand exactly which frontmatter fields bootstrap can overwrite, so they know which fields are safe to set manually and which will be regenerated.

**Why this priority**: Without a documented mutation surface, users cannot predict what `finalize-tasks` will do to their WP files. This leads to silent data loss (as documented in #417's F015 evidence).

**Independent Test**: A developer documentation artifact (mutation surface doc or ADR) exists and is accurate against the code.

**Acceptance Scenarios**:

1. **Given** the bootstrap implementation, **When** a developer reads the mutation surface document, **Then** every frontmatter field that bootstrap can write or overwrite is listed with its source (parsed from `tasks.md`, computed, or preserved).
2. **Given** a WP file with a non-empty `dependencies` field, **When** bootstrap runs in non-validate-only mode, **Then** the behavior (preserve or overwrite) matches what is documented.

---

### User Story 3 — Robust `tasks.md` Header Parsing (Priority: P2)

A developer or LLM generates a `tasks.md` file that uses `####` headings for work packages (nested under phase groupings). They run `finalize-tasks` and expect WP dependencies to be parsed correctly.

**Why this priority**: The immediate cause of the F015 silent dependency-strip incident. A one-line regex change per site eliminates the entire class of problem.

**Independent Test**: Run `finalize-tasks` against a `tasks.md` with `#### WP01` headings; verify `dependencies` frontmatter is populated correctly.

**Acceptance Scenarios**:

1. **Given** a `tasks.md` with WP headers at `##` depth, **When** parsing runs, **Then** all WPs are detected (regression: existing behavior preserved).
2. **Given** a `tasks.md` with WP headers at `###` or `####` depth, **When** parsing runs, **Then** all WPs and their dependencies are detected correctly.
3. **Given** a `tasks.md` with WP headers at `#####` depth (deeper than allowed), **When** parsing runs, **Then** those headings are NOT detected (boundary enforced).

---

### User Story 4 — Typed WP Frontmatter (Priority: P2)

A developer adds a new consumer of WP frontmatter. Instead of guessing field names and types by reading source files, they import `WPMetadata` and get IDE completion, type checking, and a validation error at load time if a required field is missing.

**Why this priority**: Eliminates the category of runtime failures caused by field-name typos, missing required fields, and type mismatches across 15+ consumer modules.

**Independent Test**: A consumer module that previously used `frontmatter.get("dependencies", [])` now uses `wp_meta.dependencies` with full type safety; a WP file missing a required field raises a validation error on load.

**Acceptance Scenarios**:

1. **Given** a WP frontmatter file with all required fields, **When** loaded via `read_wp_frontmatter()`, **Then** a valid `WPMetadata` object is returned with typed attribute access.
2. **Given** a WP frontmatter file missing a required field (e.g., `work_package_id`), **When** loaded via `read_wp_frontmatter()`, **Then** a `ValidationError` is raised immediately at load time.
3. **Given** all active WP files in `kitty-specs/`, **When** a CI test runs `WPMetadata.model_validate()` against each, **Then** all pass without modification.
4. **Given** `extra="forbid"` is set after consumer migration, **When** a WP file contains an unrecognized field, **Then** a validation error is raised (strict schema enforced).

---

### User Story 5 — Single Source of Lane Transition Truth (Priority: P3)

A developer needs to add a new guard condition for a lane transition. Instead of searching 46 files for the right place, they open `src/specify_cli/status/` and find the `WPState` protocol and its concrete implementations as the definitive source.

**Why this priority**: Reduces the surface area for transition-logic bugs and makes the status model self-documenting.

**Independent Test**: The `WPState` protocol and 9 concrete lane state classes exist; a property test harness proves their transition matrix is identical to the updated `ALLOWED_TRANSITIONS` frozenset (including the new `in_review` lane transitions).

**Acceptance Scenarios**:

1. **Given** the `WPState` protocol, **When** a developer calls `state.allowed_targets()`, **Then** they get the same set as the current `ALLOWED_TRANSITIONS` lookup for that lane.
2. **Given** the `TransitionContext` value object, **When** guard evaluation runs, **Then** the result is identical to the current string-keyed `_run_guard()` dispatch for every input combination.
3. **Given** the property test harness, **When** it runs against both old procedural code and the new `WPState` implementation, **Then** both produce identical results for all 25 allowed transition pairs (22 current + 3 net new from `in_review` promotion) and all guarded combinations.

---

### User Story 6 — High-Touch Consumers Use State Object (Priority: P3)

A developer reading `orchestrator_api/commands.py`, `next/decision.py`, or `dashboard/scanner.py` no longer sees `if current_lane == "planned"` / `elif "claimed"` cascades. All lane-conditional logic in these three files delegates to `WPState` methods.

**Why this priority**: These three files account for the majority of the scattered lane logic (22 occurrences in `orchestrator_api` alone). Migrating them proves the pattern works and reduces the highest-density hotspot.

**Independent Test**: `grep -r 'current_lane ==' src/specify_cli/orchestrator_api src/specify_cli/next src/specify_cli/dashboard` returns no matches after migration.

**Acceptance Scenarios**:

1. **Given** `orchestrator_api/commands.py`, **When** lane-conditional logic executes, **Then** it delegates to `WPState` methods; no direct lane string comparisons remain in the file.
2. **Given** `next/decision.py` and `dashboard/scanner.py`, **When** lane bucketing or progress computation runs, **Then** it uses `state.progress_bucket()` or `state.display_category()`; no ad-hoc lane string sets remain.
3. **Given** the three migrated files, **When** the full test suite runs, **Then** all existing tests pass without modification.

---

### Edge Cases

- What happens when `--validate-only` is combined with `--json`? The JSON output must not report any `bootstrap` mutations (or must report zero mutations).
- What happens when a WP file contains both known fields and unknown extra fields during the `extra="allow"` migration phase? Unknown fields must be preserved (round-trip safe).
- What happens when `WPMetadata.model_validate()` is called on a pre-0.11.0 WP file that lacks newer optional fields (e.g., `planning_base_branch`)? Optional fields must default gracefully.
- What happens when a `WPState` concrete class is asked to transition to a lane not in its `allowed_targets()`? Must raise the same error as the current `validate_transition()` call.
- What happens when two agents concurrently attempt to claim a `for_review` WP for review? The first agent's `for_review` -> `in_review` transition succeeds; the second agent's attempt must fail with `WP_ALREADY_CLAIMED` (FR-012b).
- What happens when the property test harness encounters a guarded transition where the guard requires context the test doesn't supply? Test must use explicit `TransitionContext` fixtures for all guard-relevant cases.

## Requirements

### Functional Requirements

| ID | Title | Description | Priority | Status |
|----|-------|-------------|----------|--------|
| FR-001 | Validate-only skips bootstrap | `finalize-tasks --validate-only` must not run the bootstrap step; no files on disk may be modified during a validate-only invocation. | High | Open |
| FR-002 | Validate-only JSON contract | When `--validate-only --json` is used, the JSON output must not contain a `bootstrap` key reporting mutations; it may contain a `validation` key with the report only. | High | Open |
| FR-003 | Bootstrap mutation audit | A documentation artifact (ADR or developer note) lists every frontmatter field that bootstrap can write or overwrite, with source (parsed, computed, or conditionally preserved). | High | Open |
| FR-004 | tasks.md header depth flexibility | All four `tasks.md` header-parsing regex sites accept WP headings at `##`, `###`, and `####` depth; headings at `#####` or deeper are not matched. | High | Open |
| FR-005 | WPMetadata Pydantic model | A `WPMetadata` Pydantic model exists with typed fields for all known frontmatter keys, field validators, `frozen=True`, and `extra="allow"` initially. | Medium | Open |
| FR-006 | WPMetadata load function | A `read_wp_frontmatter(path)` convenience function returns a `(WPMetadata, body)` tuple; it raises `ValidationError` on load if required fields are absent or malformed. | Medium | Open |
| FR-007 | Consumer migration | All consumer modules currently accessing WP frontmatter via `dict.get()` are migrated to use `WPMetadata` typed attribute access. | Medium | Open |
| FR-008 | extra="forbid" tightening | After all consumers are migrated and all active WP files in `kitty-specs/` pass validation, `WPMetadata` is tightened to `extra="forbid"`. A CI test validates all WP files pass. | Medium | Open |
| FR-009 | WPState protocol | A `WPState` protocol (or abstract base class) defines the interface: `lane`, `is_terminal`, `is_blocked`, `allowed_targets()`, `can_transition_to(target, ctx)`, `transition(target, ctx)`, `progress_bucket()`, `display_category()`. | Medium | Open |
| FR-010 | Concrete lane state classes | Nine concrete `WPState` implementations exist, one per canonical lane: `planned`, `claimed`, `in_progress`, `for_review`, `in_review`, `approved`, `done`, `blocked`, `canceled`. The `doing` alias is resolved at input boundaries and does not get its own class. The former `in_review` alias is promoted to a first-class lane to resolve the parallel-execution review contention blind spot. | Medium | Open |
| FR-011 | TransitionContext value object | A `TransitionContext` dataclass (frozen) replaces the current 8-argument kwargs bag in guard evaluation. Fields: `actor`, `workspace_context`, `subtasks_complete`, `evidence`, `review_ref` (legacy compat), `review_result` (structured `ReviewResult` for `in_review` exits), `reason`, `force`, `implementation_evidence_present`. | Medium | Open |
| FR-012 | Property test equivalence harness | A property test suite proves the new `WPState` transition matrix and guard outcomes are identical to the current `ALLOWED_TRANSITIONS` frozenset and `_run_guard()` dispatch for all 25 allowed pairs (post-`in_review` promotion) and all guard-relevant combinations. | Medium | Open |
| FR-012a | in_review lane promotion | The `in_review` alias (`LANE_ALIASES["in_review"] = "for_review"`) is removed and replaced with a first-class `Lane.IN_REVIEW` enum member, `InReviewState` concrete class, and associated transitions. `for_review` becomes a pure queue state (outbound: `in_review`, `blocked`, `canceled` only). `in_review` carries the reviewer's active-work transitions (outbound: `approved`, `done`, `in_progress`, `planned`, `blocked`, `canceled`). The `(for_review, in_review)` transition has an actor-required guard with conflict detection, preventing concurrent review claims on the same WP. | Medium | Open |
| FR-012b | Review claim conflict detection | When an agent attempts to transition a WP from `for_review` to `in_review`, and another actor has already claimed it (WP is in `in_review` with a different actor), the transition must fail with a `WP_ALREADY_CLAIMED` error analogous to the implementation claiming mechanism. | Medium | Open |
| FR-012c | Structured ReviewResult on in_review exit | Every outbound transition from `in_review` must carry a structured review result in the `TransitionContext`. Approval transitions (`in_review` -> `approved`, `in_review` -> `done`) require a `ReviewResult` with `verdict="approved"`, reviewer identity, and reference. Rejection transitions (`in_review` -> `in_progress`, `in_review` -> `planned`) require a `ReviewResult` with `verdict="changes_requested"` and a review feedback reference. This unifies the currently asymmetric approval (`DoneEvidence.review`) and rejection (`review_ref` string) recording paths. | Medium | Open |
| FR-012d | Lane model documentation consistency | All user-facing and developer-facing documentation reflecting the lane model must be updated to the 9-lane state machine. Affected files: `README.md` (Mermaid state diagram), `docs/explanation/kanban-workflow.md` (lane definitions + transition table), `docs/status-model.md` (state machine section + guard table), `docs/2x/runtime-and-missions.md` (state machine reference), `CLAUDE.md` (stale 7-lane section). The WP05 ADR supersedes `architecture/2.x/adr/2026-04-03-2-review-approval-and-integration-completion-are-distinct.md`. | Medium | Open |
| FR-013 | LANES deduplication | The three duplicate `LANES` tuple definitions are collapsed: `tasks_support.py` and `scripts/tasks/task_helpers.py` import from the canonical `status` package; the stale 4-lane tuple in `task_helpers.py` is removed. | Low | Open |
| FR-014 | High-touch consumer migration | `orchestrator_api/commands.py`, `next/decision.py`, and `dashboard/scanner.py` are migrated to use `WPState` methods; no direct lane string comparisons remain in these three files. | Low | Open |
| FR-015 | Dashboard API TypedDict contracts | `TypedDict` response shapes are defined in `src/specify_cli/dashboard/api_types.py` for all JSON dashboard endpoints. Handler methods construct responses through these types. | Low | Open |
| FR-016 | Dashboard API contract test | A pytest contract test validates that the JS frontend references the same response keys that the Python `TypedDict` definitions declare (#361 Phase 1). | Low | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Test suite regression-free | The full existing test suite passes without modification after each work package (beyond import path updates). Zero new test failures introduced. | Correctness | High | Open |
| NFR-002 | Event log format unchanged | The `StatusEvent` JSONL format is byte-for-byte identical before and after; no new fields added, no field renames in the event log. | Compatibility | High | Open |
| NFR-003 | Emit pipeline contract preserved | `emit_status_transition()` remains the single entry point for state changes; its public signature does not change; callers require no updates outside the three migrated consumer files. | Compatibility | High | Open |
| NFR-004 | WPMetadata round-trip safe | Any WP frontmatter file that passes `WPMetadata.model_validate()` must produce identical YAML when serialized back to disk (no field reordering, no value coercion, no loss of unknown extra fields during the `extra="allow"` phase). | Correctness | Medium | Open |
| NFR-005 | WPState instantiation cost | Constructing a `WPState` object from a lane string must complete in under 1 ms on reference hardware; bulk snapshot materialization must not regress by more than 5% compared to the current reducer. | Performance | Low | Open |
| NFR-006 | Dashboard operability preserved | The dashboard remains operationally functional throughout and after the migration. Dashboard API JSON responses produce identical structure and values before and after WP04 and WP06 consumer migrations. | Correctness | High | Open |
| NFR-007 | Linter non-regression | New and modified code must not increase the mypy or ruff error count for touched files. Boy Scout improvements (DIRECTIVE_025) should decrease the count where proportional. | Maintainability | Medium | Open |
| NFR-008 | CI stage isolation for status tests | Status-layer tests run in a dedicated CI stage parallel to core tests, providing faster feedback on status-layer regressions. | Efficiency | Low | Open |
| NFR-009 | Self Observation Protocol | Agents write structured work logs to `work/observations/` during WP execution (implement, review, or coordination sessions). Logs capture work summaries, tooling friction, spec gaps, and recommendations for post-mission analysis. Advisory — must not block WP progression. | Observability | Low | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | No event log format change | `StatusEvent` JSONL field names, types, and ordering must not change. | Technical | High | Open |
| C-002 | Reducer and store untouched | `status/reducer.py` and `status/store.py` may not have behavioral changes; only import-path updates are permitted. | Technical | High | Open |
| C-003 | No WP file modifications required | All active WP files in `kitty-specs/` must pass `WPMetadata.model_validate()` without any manual edits to those files. | Technical | High | Open |
| C-004 | Non-migrated consumers still work | The 40+ consumer modules NOT migrated in this feature must continue to function with the existing procedural API unchanged. The old `validate_transition()` and `ALLOWED_TRANSITIONS` remain accessible during the transition period. | Technical | High | Open |
| C-005 | No new runtime dependencies | This feature introduces no new third-party runtime dependencies beyond Pydantic (already present). | Technical | Medium | Open |

### Key Entities

- **`WPMetadata`**: Value object (Pydantic, `frozen=True`) representing the structured frontmatter of a WP prompt file. Fields cover identity (`work_package_id`, `title`), dependency graph (`dependencies`), branch contract (`base_branch`, `base_commit`, `planning_base_branch`, `merge_target_branch`), and optional planning metadata. Equality by attribute values; no mutable identity.
- **`WPState`**: Protocol (or ABC) representing a work package's behavioral state at a given lane. Encapsulates allowed transitions, guard evaluation, terminal/blocked classification, and progress/display categorization. Nine concrete implementations (one per canonical lane, including the promoted `in_review` lane). Stateless value-like objects instantiated from a `Lane` enum value.
- **`TransitionContext`**: Frozen dataclass carrying all inputs needed for guard evaluation. Replaces the heterogeneous 8-argument kwargs bag currently passed to `_run_guard()`. Immutable; equality by attributes.

## Success Criteria

### Measurable Outcomes

- **SC-001**: `finalize-tasks --validate-only` produces zero bytes of `git diff` output against any feature directory in a clean working tree.
- **SC-002**: A developer documentation artifact accurately lists every frontmatter field that the bootstrap step can write or overwrite (verified by code review against the implementation).
- **SC-003**: `finalize-tasks` correctly parses dependencies from a `tasks.md` file using `####` WP headers; previously silent failures now produce correct frontmatter.
- **SC-004**: A CI test validates all WP files in `kitty-specs/` against `WPMetadata.model_validate()` and passes with zero failures, without modifying any WP file.
- **SC-005**: The property test harness asserts 100% equivalence between the new `WPState` transition matrix and the updated `ALLOWED_TRANSITIONS` for all allowed transition pairs (including `in_review` lane transitions) and all guarded transition combinations.
- **SC-006**: After consumer migration, `grep -r 'current_lane ==' src/specify_cli/orchestrator_api src/specify_cli/next src/specify_cli/dashboard` returns zero matches.
- **SC-007**: The full test suite (unit + integration) passes with zero regressions after each work package merges to the feature branch.
- **SC-008**: A dashboard API contract test validates that all JSON endpoint response shapes match their `TypedDict` definitions and that the JS frontend references the same keys.

## Assumptions

- Pydantic is already a runtime dependency of spec-kitty (v2.x API assumed).
- All WP files in `kitty-specs/` use UTF-8 YAML frontmatter delimited by `---`.
- The `doing` lane alias is resolved at input boundaries and never persisted in the event log; `WPState` for `doing` can delegate to `InProgressState`. The former `in_review` alias is promoted to a first-class lane; see FR-012a.
- The partial Phase 2 consumer migration (three files) does not require the remaining consumers to be migrated before it can be merged; the old procedural API coexists with the State Object during the transition period.
- The bootstrap mutation audit (FR-003) requires reading the `finalize_tasks` implementation in detail; this is scoped to the implementation research WP.

## Related Issues (Not In Scope)

- **#418** — `tasks/README.md` template hardcoded `2.x` branch instead of using resolved branch context. This was discovered during mission planning but has since been fixed in the rebased baseline (`core/feature_creation.py`). It is no longer active scope for mission 065 and must not be reintroduced while editing planning artifacts or dashboard surfaces.
- **#422** — `/spec-kitty.tasks` can generate impossible WPs (ownership inference picks up read-only references, nonexistent files, overly broad wildcards) and incomplete lane graphs (WPs dropped from `lanes.json`). Mission 065's `WPMetadata` type hardening (WP03/WP04, `extra="forbid"`) partially mitigates this by enabling validation of `owned_files` at parse time. The task-generation tooling fix itself is a separate mission.
- **#423** — Lane computation silently erases declared parallelism via ownership/write-scope collapse. The typed `owned_files: list[str]` field in `WPMetadata` provides a foundation for future ownership-precision validation, but the lane planner reconciliation logic is outside this mission's scope.
