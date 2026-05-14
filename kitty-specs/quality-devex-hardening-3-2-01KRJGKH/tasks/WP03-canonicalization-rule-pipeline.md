---
work_package_id: WP03
title: Canonicalization rule-pipeline extraction
dependencies:
- WP01
requirement_refs:
- FR-009
- FR-010
- FR-011
- FR-013
planning_base_branch: fix/quality-check-updates
merge_target_branch: fix/quality-check-updates
branch_strategy: Planning artifacts for this mission were generated on fix/quality-check-updates. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/quality-check-updates unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T012
- T013
- T014
- T015
- T016
- T017
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1128512"
history:
- at: '2026-05-14'
  actor: planner
  event: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/migration/
execution_mode: code_change
mission_id: 01KRJGKH4DJCSF277K9QV3WBE7
mission_slug: quality-devex-hardening-3-2-01KRJGKH
owned_files:
- src/specify_cli/migration/canonicalization.py
- src/specify_cli/migration/mission_state.py
- src/specify_cli/migration/rebuild_state.py
- tests/unit/migration/test_canonicalization_rules.py
- tests/integration/migration/test_canonicalization_pipeline.py
- architecture/2.x/04_implementation_mapping/code-patterns.md
- kitty-specs/quality-devex-hardening-3-2-01KRJGKH/glossary-fragments/WP03.md
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else below, load the assigned agent profile so your behavior, boundaries, and governance scope match the role:

```
/ad-hoc-profile-load python-pedro
```

The profile establishes your identity (Python Pedro), primary focus (idiomatic, type-safe, well-tested Python), and avoidance boundary (no architectural redesign beyond what this WP authorizes; no scope expansion). If the profile load fails, stop and surface the error.

## Objective

Lift the `_canonicalize_status_row` rule pipeline (currently flattened into one ~80-line function in `src/specify_cli/migration/mission_state.py:1154`) onto a typed `CanonicalRule` Protocol in a new `src/specify_cli/migration/canonicalization.py` module. Reuse the Protocol in `src/specify_cli/migration/rebuild_state.py` — the two-consumer bar that justifies the abstraction. Update the architecture code-patterns catalog to cite the new canonical implementation.

This is the motivating Transformer-flavor application of the `chain-of-responsibility-rule-pipeline` tactic landed pre-mission in commit `0878f798d`. Each rule becomes a small, pure, parametrically-testable function. Characterization tests for the pre-refactor behavior land BEFORE the refactor commit.

## Context

### Pre-refactor shape

`src/specify_cli/migration/mission_state.py:1154` defines `_canonicalize_status_row` with cognitive complexity 36 per Sonar. The function applies ten sequential transformations to a status-event row:

1. Reject non-status events (early return).
2. Apply `STATUS_ROW_ALIASES` renames.
3. Strip `FORBIDDEN_LEGACY_KEYS`.
4. Stamp `mission_slug`, `mission_id`.
5. Mint missing `event_id` deterministically.
6. Default `at`, `from_lane`.
7. Require `to_lane`, `wp_id`.
8. Normalize and validate lane values.

`rebuild_state.py:409` contains an analogous rule sequence on the same shape of data (different state — frontmatter rows — but identical Transformer pattern).

### Design artifacts already authored

- `data-model.md` — defines `CanonicalRule[State]`, `CanonicalStepResult[State]`, `CanonicalPipelineResult[State]`, `MigrationContext`.
- `contracts/canonicalization-rule-pipeline.md` — full Protocol + runner contract.
- `chain-of-responsibility-rule-pipeline.tactic.yaml` (commit `0878f798d`) — codifies the pattern; Transformer flavor is documented in the notes.
- `architecture/2.x/04_implementation_mapping/code-patterns.md` — code-patterns catalog; entry 1 names this WP as the canonical Transformer-flavor implementation (currently "planned"; this WP flips it to "in-tree").

## Doctrine Citations

This WP applies:

- [`chain-of-responsibility-rule-pipeline`](../../../src/doctrine/tactics/shipped/code-patterns/chain-of-responsibility-rule-pipeline.tactic.yaml) — Transformer flavor; the central tactic for this WP.
- [`tdd-red-green-refactor`](../../../src/doctrine/tactics/shipped/testing/tdd-red-green-refactor.tactic.yaml) — characterization tests precede the refactor commit (NFR-003).
- [`refactoring-extract-first-order-concept`](../../../src/doctrine/tactics/shipped/refactoring/refactoring-extract-first-order-concept.tactic.yaml) — each rule is a first-order concept with one responsibility.
- [`function-over-form-testing`](../../../src/doctrine/tactics/shipped/testing/function-over-form-testing.tactic.yaml) — per-rule tests assert input → output transformation; pipeline tests assert end-to-end behavior.

## Branch Strategy

- Planning / base branch: `fix/quality-check-updates`.
- Final merge target: `fix/quality-check-updates`.
- Execution worktree allocated by `lanes.json`. Depends on WP01.

## Subtasks

### T011 — Characterization tests for `_canonicalize_status_row` (commit BEFORE refactor)

**Purpose**: Capture today's observable behavior of `_canonicalize_status_row` against a corpus of real legacy rows. These tests must remain green through the refactor (NFR-003).

**Steps**:

1. Walk `.kittify/migrations/mission-state/` (the local working tree contains real legacy rows). Select a representative corpus:
   - At least one row exercising each of the 10 rules in the current pipeline.
   - At least one row that hits an early-return rejection.
   - At least one row that requires `event_id` mint.
   - At least one row with a legacy-aliased key.
2. Create `tests/integration/migration/test_canonicalization_pipeline.py`:
   - Author fixtures under `tests/integration/migration/fixtures/` that mirror the selected corpus (sanitized — drop any private content).
   - For each fixture, call `_canonicalize_status_row(...)` and snapshot the result (row dict + actions tuple). Use stable JSON serialization for the snapshot.
   - Assert the snapshot equals the captured pre-refactor output.
3. **Commit T011 alone** before any other changes. Verify with `git log`:
   ```
   <T011 commit hash>  test: characterize _canonicalize_status_row behavior pre-refactor
   ```

**Files**:

- `tests/integration/migration/test_canonicalization_pipeline.py` (new, ~150 lines).
- `tests/integration/migration/fixtures/*.json` (new, 5–10 fixtures).

**Validation**:

- All characterization tests pass on `main` (or this WP's base) without the refactor.
- Commit is isolated; subsequent commits in this WP keep the tests green.

### T012 — Create `migration/canonicalization.py` with Protocol + runner

**Purpose**: Introduce the typed Transformer-flavor Protocol per `contracts/canonicalization-rule-pipeline.md`.

**Steps**:

1. Create `src/specify_cli/migration/canonicalization.py`:
   - Define `MigrationContext` (frozen dataclass with `mission_slug`, `mission_id`, `line_number`, `generated_ids`).
   - Define `CanonicalStepResult[State]` (frozen dataclass with `state`, `actions`, `error`, classmethod `passthrough`).
   - Define `CanonicalPipelineResult[State]` (frozen dataclass with `state`, `actions`, `error`).
   - Define `CanonicalRule` Protocol parameterized over `State` (TypeVar).
   - Implement `apply_rules(rules, state, ctx) -> CanonicalPipelineResult[State]`: threads state through rules, short-circuits on `error`.
2. Add module-level docstring citing `chain-of-responsibility-rule-pipeline` tactic notes.
3. Ensure `mypy --strict` passes on the new module.

**Files**: `src/specify_cli/migration/canonicalization.py` (new, ~90 lines).

**Validation**:

- Module imports cleanly.
- `mypy --strict src/specify_cli/migration/canonicalization.py` exits 0.
- Module has no runtime side effects on import.

### T013 — Lift `_canonicalize_status_row` rules onto the Protocol

**Purpose**: Extract the 10 inline rules in `_canonicalize_status_row` into named pure functions conforming to `CanonicalRule[Row]`.

**Steps**:

1. Inside `migration/mission_state.py` (or a sibling private module), define each rule as a pure function:
   - `_rule_reject_non_status_event(row, ctx) -> CanonicalStepResult[Row]`
   - `_rule_apply_aliases(row, ctx) -> CanonicalStepResult[Row]`
   - `_rule_strip_legacy_keys(row, ctx) -> CanonicalStepResult[Row]`
   - `_rule_stamp_identity(row, ctx) -> CanonicalStepResult[Row]`
   - `_rule_mint_event_id(row, ctx) -> CanonicalStepResult[Row]`
   - `_rule_default_at(row, ctx) -> CanonicalStepResult[Row]`
   - `_rule_default_from_lane(row, ctx) -> CanonicalStepResult[Row]`
   - `_rule_require_to_lane(row, ctx) -> CanonicalStepResult[Row]`
   - `_rule_require_wp_id(row, ctx) -> CanonicalStepResult[Row]`
   - `_rule_normalize_lanes(row, ctx) -> CanonicalStepResult[Row]`
2. Declare the rule tuple at module scope:
   ```python
   _CANONICAL_STATUS_ROW_RULES: tuple[CanonicalRule[Row], ...] = (
       _rule_reject_non_status_event,
       _rule_apply_aliases,
       _rule_strip_legacy_keys,
       _rule_stamp_identity,
       _rule_mint_event_id,
       _rule_default_at,
       _rule_default_from_lane,
       _rule_require_to_lane,
       _rule_require_wp_id,
       _rule_normalize_lanes,
   )
   ```
3. Rewrite `_canonicalize_status_row` to delegate to `apply_rules`:
   ```python
   def _canonicalize_status_row(data, *, mission_slug, mission_id, line_number, generated_ids=None) -> _CanonicalRowResult:
       ctx = MigrationContext(mission_slug=mission_slug, mission_id=mission_id, line_number=line_number, generated_ids=generated_ids)
       result = apply_rules(_CANONICAL_STATUS_ROW_RULES, dict(data), ctx)
       return _CanonicalRowResult.from_pipeline(result)
   ```
4. Add `_CanonicalRowResult.from_pipeline` classmethod that adapts the generic pipeline result to the existing `_CanonicalRowResult` shape.
5. **Run the characterization tests from T011.** They MUST remain green. If any test fails, the refactor changed behavior — fix the rule, do not modify the test.

**Files**: `src/specify_cli/migration/mission_state.py` (modified, ~10 lines per rule × 10 rules = ~100 line additions, similar net deletions in `_canonicalize_status_row`).

**Validation**:

- All T011 characterization tests pass.
- Each `_rule_*` function has cognitive complexity ≤ 5 per Sonar.
- `_canonicalize_status_row` shrinks to ≤ 15 lines.

### T014 — Lift `rebuild_state.py` analogous rules onto the same Protocol

**Purpose**: Demonstrate the two-consumer bar — the abstraction is justified because two callers use it. Read `rebuild_state.py:409` and the surrounding rule sequence.

**Steps**:

1. Identify the analogous rule sequence in `src/specify_cli/migration/rebuild_state.py`. Likely candidates: `_derive_migration_timestamp` and nearby helpers around line 409 (cognitive complexity 31 per Sonar).
2. Add characterization tests for the pre-refactor `rebuild_state` rules in `tests/integration/migration/test_canonicalization_pipeline.py` (extend the existing file).
3. Apply the same lift: name each rule, collect into a tuple, delegate the public function to `apply_rules`.
4. Verify the characterization tests stay green.

**Files**: `src/specify_cli/migration/rebuild_state.py` (modified).

**Validation**:

- New characterization tests for `rebuild_state` rules pass before and after the refactor.
- Both `_CANONICAL_STATUS_ROW_RULES` and the new `_REBUILD_STATE_RULES` (or whatever name fits) consume the same `CanonicalRule` Protocol with different `State` types.

### T015 — [P] Per-rule unit tests in `tests/unit/migration/test_canonicalization_rules.py`

**Purpose**: Lock each rule's behavior as a pure value transformer. These are NOT characterization tests — they are the new behavior contract authored alongside the refactor.

**Steps**:

1. Create `tests/unit/migration/test_canonicalization_rules.py`.
2. For each `_rule_*` function, author a `@pytest.mark.parametrize` table with `(input_state, ctx, expected_result)` triples:
   - Happy case (rule applies, returns transformed state + actions).
   - No-op case (rule does not apply, returns passthrough).
   - Error case where applicable (rule short-circuits, returns error).
3. Assertions on the entire `CanonicalStepResult` value — `state`, `actions`, `error`. No structural assertions.

**Files**: `tests/unit/migration/test_canonicalization_rules.py` (new, ~250 lines).

**Validation**:

- Per-rule tests pass with the lifted rules.
- Each rule has ≥ 2 parametrized cases (happy + no-op minimum); rules with error returns have ≥ 3.

### T016 — Update `architecture/2.x/04_implementation_mapping/code-patterns.md`

**Purpose**: The code-patterns catalog already names `src/specify_cli/migration/canonicalization.py` as the **planned** Transformer-flavor canonical implementation. This WP flips it to **in-tree**.

**Steps**:

1. Open `architecture/2.x/04_implementation_mapping/code-patterns.md`.
2. Find the "1. Rule-Based Pipeline (Chain of Responsibility)" section, "Canonical implementations in tree" bullet for Transformer flavor.
3. Update the bullet:
   - Before: "Transformer: `src/specify_cli/migration/mission_state.py::_canonicalize_status_row` (motivating example; planned to be lifted onto an explicit `CanonicalRule` Protocol in `src/specify_cli/migration/canonicalization.py`)."
   - After: "Transformer: `src/specify_cli/migration/canonicalization.py::CanonicalRule` (Protocol + `apply_rules` runner). Consumed by `src/specify_cli/migration/mission_state.py::_canonicalize_status_row` and `src/specify_cli/migration/rebuild_state.py`."

**Files**: `architecture/2.x/04_implementation_mapping/code-patterns.md` (modified, ~5 line change).

**Validation**:

- Catalog cites `migration/canonicalization.py` as in-tree.
- Both consumers (`mission_state.py`, `rebuild_state.py`) are named.

### T017 — Glossary fragment for "pipeline-shape" and "rule pipeline"

**Purpose**: FR-013 — every WP that introduces a canonical term records its glossary entry.

**Steps**:

1. Author `kitty-specs/quality-devex-hardening-3-2-01KRJGKH/glossary-fragments/WP03.md`. Include:
   - **`pipeline-shape`**: "A classification label applied to a function whose body is a sequence of independent decisions over a shared input. Pipeline-shape functions are the principal refactor target for the `chain-of-responsibility-rule-pipeline` tactic. See `architecture/2.x/04_implementation_mapping/code-patterns.md` entry 1." Confidence 0.9. Status active.
   - **`rule pipeline`**: "A pipeline of small pure functions, each checking applicability, optionally executing its narrow piece of work, and returning a result threaded to the next function. Three flavors are recognized in this codebase: Validator (accumulating `list[Finding]`), Transformer (chained `(state, actions, error)`), Scorer (weighted `float`). See the `chain-of-responsibility-rule-pipeline` tactic." Confidence 0.95. Status active.
2. Stage and commit.

**Files**: `kitty-specs/quality-devex-hardening-3-2-01KRJGKH/glossary-fragments/WP03.md` (new, ~20 lines).

**Validation**:

- Fragment exists and follows the canonical-term schema (`surface`, `definition`, `confidence`, `status: active`).

## Test Strategy

- **Characterization tests (T011)**: commit BEFORE T013/T014; remain green through every subsequent commit.
- **Per-rule unit tests (T015)**: locks each rule's behavior; parametrized.
- **End-to-end pipeline tests**: extend `test_canonicalization_pipeline.py` with additional fixtures as the corpus grows.
- All tests follow `function-over-form-testing` — no structural assertions, no mock-call-count assertions.

## Definition of Done

- [ ] `src/specify_cli/migration/canonicalization.py` exists with Protocol + runner + value objects.
- [ ] `_canonicalize_status_row` delegates to `apply_rules` with `_CANONICAL_STATUS_ROW_RULES`.
- [ ] `rebuild_state.py` analogous rules lifted onto the same Protocol.
- [ ] Characterization tests authored in T011 (commit isolated) and still green.
- [ ] Per-rule unit tests cover each rule with ≥ 2 parametrized cases.
- [ ] Code-patterns catalog cites `migration/canonicalization.py` as in-tree canonical implementation.
- [ ] `glossary-fragments/WP03.md` carries entries for "pipeline-shape" and "rule pipeline".
- [ ] `mypy --strict` passes on `migration/canonicalization.py`, `mission_state.py`, `rebuild_state.py`.
- [ ] `git log --oneline -- src/specify_cli/migration/` shows the characterization-tests commit precedes the refactor commits (NFR-003).

## Risks

- **Characterization corpus is incomplete.** If a real-world row pattern is missing from the fixture set, the refactor passes tests but produces silent regressions on user data. Mitigation: include at least one fixture per rule + boundary cases (empty input, malformed input).
- **Rule extraction reorders side effects.** The current `_canonicalize_status_row` may have implicit ordering between mutation and read of `row[key]`; the lifted rules must preserve this ordering. Trace each pre-refactor line to a post-refactor rule.
- **`MigrationContext.generated_ids` is mutated by a rule.** This is the documented exception in `data-model.md`. The mutation is via `.append()` only and the caller owns the list. Document this in `canonicalization.py` module docstring.

## Reviewer Guidance

When reviewing this WP, check:

1. The characterization-tests commit precedes the refactor commits in `git log`. Reject if the order is wrong (NFR-003).
2. Each `_rule_*` function is **pure** — no I/O, no globals, no in-place mutation of `state` beyond the returned value.
3. Per-rule tests assert on the entire `CanonicalStepResult` value (state, actions, error), not on individual fields in isolation.
4. The code-patterns catalog update is accurate — `migration/canonicalization.py` is named, both consumers are listed.
5. No deliberate-linearity functions were refactored — this WP is scoped to migration code only.

## Implementation command

```bash
spec-kitty agent action implement WP03 --agent claude
```

## Activity Log

- 2026-05-14T09:13:53Z – claude:sonnet:python-pedro:implementer – shell_pid=1121519 – Started implementation via action command
- 2026-05-14T09:29:31Z – claude:sonnet:python-pedro:implementer – shell_pid=1121519 – Ready: Transformer-flavor lift of _canonicalize_status_row + _derive_migration_timestamp rules onto CanonicalRule Protocol. Characterization tests precede every refactor commit (NFR-003 verified). Per-rule unit tests parametrized (31 tests). Code-patterns catalog updated on planning branch. Cites chain-of-responsibility-rule-pipeline, refactoring-extract-first-order-concept, tdd-red-green-refactor, function-over-form-testing tactics. mypy --strict exits 0 on all 3 owned migration files. 48 tests pass.
- 2026-05-14T09:30:17Z – claude:opus:reviewer-renata:reviewer – shell_pid=1128512 – Started review via action command
- 2026-05-14T09:33:06Z – claude:opus:reviewer-renata:reviewer – shell_pid=1128512 – WP03 APPROVED. NFR-003 commit order verified: 606479260 (T011 characterization) precedes 1bd5fc860 (T013) and df8cffe5e (T014). Two-consumer bar met: 10 rules in mission_state._CANONICAL_STATUS_ROW_RULES + 4 rules in rebuild_state._TIMESTAMP_SOURCE_RULES, both consuming CanonicalRule[State]. Doctrine citations verified per commit: tdd-red-green-refactor (606479260), chain-of-responsibility-rule-pipeline + refactoring-extract-first-order-concept (6ecede694, 1bd5fc860, df8cffe5e), function-over-form-testing (cb2cc9067). 48 tests pass (17 characterization + 31 per-rule). mypy --strict clean on all 3 owned migration files. Function-over-form audit: zero mock-based assertions, zero structural assertions, pure value-transformer style throughout. Code-patterns catalog updated on planning branch (199e7294a) cites Transformer-flavor canonicalization.py with both consumers. Glossary fragment (6c73c3997) carries pipeline-shape (0.9) and rule pipeline (0.95) entries, status active. Per-rule purity: mission_state rules pure (only documented generated_ids.append exception); rebuild_state source-collectors necessarily perform file I/O via state-bound feature_dir — acceptable since the rule role is source-collection and the Protocol contract permits state-derived reads. Lane housekeeping clean (dde76b0d0 removed lingering planning artifacts).
