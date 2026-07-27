# Mission Specification: Auto-scoped review-time regression gate

**Status**: Draft
**Issues**: Closes [#572](https://github.com/Priivacy-ai/spec-kitty/issues/572) + the per-WP review-blind-spot facet of [#1979](https://github.com/Priivacy-ai/spec-kitty/issues/1979); Part of [#2283](https://github.com/Priivacy-ai/spec-kitty/issues/2283) (M5 of epic 1931 — Phase 1)

## User Scenarios & Testing *(mandatory)*

**Primary actor**: an orchestrator/reviewer whose WP changes a shared surface and breaks a **consumer outside the WP's `owned_files`** — today that breakage sails to approval and is only caught at PR-time CI (or after merge).

**Grounding** (verified against the code):
- The `move-task --to for_review` transition (`src/specify_cli/cli/commands/agent/tasks_move_task.py`) runs **NO tests** — it is a pure status transition. There is no "affected test set" computed at review time.
- Review scoping (`workflow.py`) is bounded to the WP's `owned_files`; ownership (`ownership/models.py`) computes no **consumer** set — a WP that edits `src/specify_cli/status/emit.py` never learns which other modules' tests exercise it.
- **`src/specify_cli/review/baseline.py` already exists**: a test runner + a **new-vs-preexisting** JUnit baseline diff. Today it only *annotates* the review prompt; it is not a gate. This mission promotes it to a gate — do NOT rebuild it.
- The dorny path-filter groups in `.github/workflows/ci-quality.yml` (parsed by `_gate_coverage.aggregate_filter_groups()` `:866` / `_parse_filter_groups` `:420`) come in **two shapes**, and the derivation key is **"does the file's group carry `tests/**` globs":**
  - **(a) per-shard groups** (`status`, `cli`, `merge`, `sync`, `review`, `lanes`, `dashboard`, `upgrade`, …) whose globs **already include `tests/**`** → the affected test scope is those test globs.
  - **(b) composite groups** (`auth_audit_git`, `lifecycle`, `agent_surface`, `closeout`, `governance`, `platform`) whose globs are **src-only** (no `tests/**`) → the test scope is NOT in the dorny group but in the census **`_COMPOSITE_ROUTING` cone_roots** (`_gate_coverage.py:784-851` / `ci_topology_census.json`, e.g. `git → tests/git`, `migration → tests/migration`). (The census worklist is NOT an "unmapped tail" — all its dirs are composite-group members; it is the cone-root source for the src-only composites.)
  - **Catch-all groups (`core_misc`, `e2e`, `any_src`) are EXCLUDED** from the review-time run: `core_misc` alone spans ~53 `tests/**` globs (`tests/architectural|integration|core|contract`, ~17min) and would defeat FR-005's bounded-cost goal. A file that lands ONLY in a catch-all group → the documented default (warn), not a whole-tree run.
  - All read-only, never hand-declared. The `status/emit.py` example → the focused `status` shard (it is excluded from `core_misc` per the exclusion above), NOT the catch-all cone.

The fix is a **warn-by-default, opt-in-block** regression gate at the `for_review` boundary: run the tests of the **shards that consume the WP's changed files** (auto-derived from the census), diff against a baseline, and surface/​block on **newly-introduced** failures only.

### User Story 1 - A WP that breaks a consumer is caught before approval (Priority: P1)
As an orchestrator, I want a WP's move to `for_review` to run the consuming shards' tests and flag any **new** failure it introduced, so a cross-surface breakage doesn't reach approval unnoticed.

**Independent test**: a WP edits a shared module and breaks a test in another shard's suite (not in `owned_files`) → the `for_review` gate surfaces the new failure (and blocks if opt-in block is on).

### User Story 2 - Pre-existing red doesn't block the WP (Priority: P1)
As an orchestrator, I want the gate to block only on failures **this WP introduced** (baseline diff), never on failures already red on the base — no retry-to-green pressure, no punishing a WP for inherited debt.

### User Story 3 - The scope is affordable and auto-derived (Priority: P2)
As a maintainer, I want the gate to run only the **affected shards** (derived from the census), not the whole `tests/` tree, so review-time cost stays bounded; and the scope map must be single-source (census-derived) so it can't drift from CI.

### Edge Cases
- **An empty affected-test set NEVER counts as "verified clean" → always WARN** (a "no-coverage-computed" verdict, distinct from a green "no new failures" verdict). Two ways it arises: **(a)** changed files land only in a catch-all/excluded group (`core_misc`/`e2e`/`any_src`) → warn ("excluded scope — unverified"); **(b)** a composite dir whose census `_COMPOSITE_ROUTING` cone_roots are **EMPTY** (`doc_analysis`, `validators`, `task_utils`, `intake` — real src dirs with no test dir) → warn ("unmapped composite dir — unverified"). Neither is a whole-tree run and neither is a silent "verified" — the mission's whole point is to never falsely claim coverage.
- The baseline can't be computed (base ref missing) → the gate degrades to **warn** (surface all failures as "unverified baseline"), never hard-blocks on an uncomputable diff.
- Recall > precision **within the focused/composite set**: an ambiguous focused-file → include its shard (over-run) rather than skip it; this never re-admits the excluded catch-all groups (`core_misc`/`e2e`/`any_src`).
- The gate must NOT become a **reverse-import-graph** analysis (A1 — a whole separate mission); scope is shard-group membership from the census only.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
| --- | --- | --- | --- | --- |
| FR-001 | Regression gate at `move-task --to for_review` | As an orchestrator, I want the `for_review` transition to run the affected-shard tests and evaluate a **new-failure** verdict. **Genuine reuse** = `review/baseline.py`'s JUnit parser + `diff_baseline`; the **shard-scoped test invocation + the head-side current-failure run are NET-NEW** (baseline.py's `capture_baseline` runs one whole `review.test_command` with no shard scoping, and `diff_baseline` takes `current_failures` as an input — there is no head-side runner today). **Warn by default** (surface new failures, allow the transition); **opt-in block** via config `review.fail_on_pre_review_regression` (+ a `--force` escape). Never blocks on the baseline's pre-existing failures. An **empty affected set** (excluded-only, or an empty-cone composite dir) yields a distinct **"no-coverage-computed" warn**, NEVER a green "verified" verdict (see edge cases) — an empty run must never read as "clean". **Prerequisite (pre-merge finding)**: `review.fail_on_pre_review_regression` is only EFFECTIVE when `review.test_command` is ALSO configured — the block can only fire on a `NEW_FAILURES` verdict, which needs a computed baseline, and `baseline.py`'s `capture_baseline` (run at implement time) skips capture (no artifact written) when `review.test_command` is unset; without one, the gate can only ever land on `no_coverage`/`unverified_baseline`, so an opted-in block with no `review.test_command` is otherwise silently inert. The console-warning path surfaces this explicitly (an escalated, non-dim warning) instead of leaving it a routine dim advisory. | High | Open |
| FR-002 | Auto-scope by group shape (test-globs vs composite cone_roots), excluding catch-alls | As a maintainer, for each changed file I want its dorny group(s) resolved via `aggregate_filter_groups()`: a **per-shard group** (carries `tests/**`) contributes its **test globs**; a **composite group** (src-only) contributes the census **`_COMPOSITE_ROUTING` cone_roots** for that dir. **Exclude the catch-all groups** (`core_misc`, `e2e`, `any_src`) from the run — they span the tree and defeat bounded cost. Recall > precision applies to the FOCUSED shards (ambiguous focused-file → include its shard); it does **not** re-admit the excluded catch-alls. Single-source, read-only, NOT hand-declared. | High | Open |
| FR-003 | New-failures-only verdict (reuse the JUnit parser + diff) | As an orchestrator, I want the verdict computed as `head_failures - base_failures` via `review/baseline.py`'s existing **JUnit parser + `diff_baseline`** — pre-existing red never counts. Note `diff_baseline` takes `current_failures` as an INPUT: producing that head-side `current_failures` (running the affected shards at head + parsing their JUnit) is the net-new runner from FR-001. If the baseline is uncomputable, degrade to warn (never hard-block). | High | Open |
| FR-004 | Overrides + precedence | As a maintainer, I want per-WP `pre_review_test_scope` (frontmatter) and repo `review.pre_review_test_command` (config) as explicit overrides of the auto-scope, with a defined precedence (frontmatter > config > census-derived default), plus a `--force` bypass recorded in the transition evidence. | Medium | Open |
| FR-005 | Bounded review-time cost (catch-alls excluded) | As a maintainer, I want the gate to run **only the affected focused shards / composite cone_roots**, never the whole `tests/` tree — enforced by the catch-all exclusion (`core_misc`/`e2e`/`any_src`), so a `status/emit.py` touch runs the `status` shard, not the ~17min `core_misc` cone. The affected-shard count + est. cost is surfaced so the ceiling is visible. | High | Open |
| FR-006 | Scope-derivation single-source invariant (both group shapes) | As a maintainer, I want an architectural test proving the derivation reads the **live authorities** for BOTH shapes — per-shard groups' `tests/**` globs via `aggregate_filter_groups()` AND composite groups' census `_COMPOSITE_ROUTING` cone_roots — and applies the catch-all exclusion; so the review scope can never drift from CI's actual routing and never silently under-covers a composite dir. | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
| --- | --- | --- | --- | --- | --- |
| NFR-001 | Non-breaking rollout | Default is **warn** (surface, don't block); blocking is opt-in — existing missions keep working with an added advisory. | Compatibility | High | Open |
| NFR-002 | Bounded runtime | Runs affected shards only (FR-005); a WP touching one shard's cone runs ~that shard, not `tests/`. No full-suite run at review time. | Performance | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
| --- | --- | --- | --- | --- | --- |
| C-001 | Reuse the parser+diff; the scoped runner is net-new | Genuine reuse = `review/baseline.py`'s **JUnit parser + `diff_baseline`**, and the live scope authorities (`aggregate_filter_groups()` + census worklist) read-only. Do NOT build a second topology map. The **shard-scoped invocation + head-side current-failure runner are net-new** (baseline.py has neither) — build them minimally, don't reinvent a full runner. | Technical | High | Open |
| C-002 | Phase-1 scope boundary (read-only on ci-quality.yml) | **Read-only** consumption of the dorny filter globs (`ci-quality.yml` via `aggregate_filter_groups()`) is the scope authority and is allowed. Do NOT **modify** CI dorny routing / venv (`ci-quality.yml` routing, `_test_env_check.py`) — those are #2283's later phases. Do NOT extend `stale_assertions.py` (the #1979 ownership facet / Phase 2, overlaps M3). No reverse-import-graph gate (A1). | Technical | High | Open |
| C-003 | No new suppressions | `ruff` + `mypy --strict` clean; no new `# noqa`/`# type: ignore`. | Technical | High | Open |

### Key Entities
- **`src/specify_cli/cli/commands/agent/tasks_move_task.py`** — the `for_review` transition; the gate hooks in here (before emitting the status event).
- **`src/specify_cli/review/baseline.py`** — reuse its **JUnit parser + `diff_baseline`** (the genuine reuse). Its `capture_baseline` runs one whole `review.test_command` (no shard scoping) and `diff_baseline` takes `current_failures` as input — so the **shard-scoped invocation + head-side runner are net-new** (built minimally here).
- **`tests/architectural/_gate_coverage.py`** — `aggregate_filter_groups()` (`:866`) yields per-group globs; **per-shard groups carry `tests/**`** (their test scope), **composite groups are src-only**. **`_COMPOSITE_ROUTING`** (`:784-851`) / `ci_topology_census.json` — the cone_roots (`git → tests/git`, …) supplying the composite groups' test scope. The **catch-all set (`core_misc`/`e2e`/`any_src`) is excluded** from the run. FR-006's invariant guards BOTH shapes + the exclusion.
- **WP frontmatter `pre_review_test_scope`** + **config `review.pre_review_test_command` / `review.fail_on_pre_review_regression`** — the override + block-toggle surfaces.

## Success Criteria *(mandatory)*
- **SC-001**: A WP that introduces a new failure in a consuming shard (outside `owned_files`) is surfaced at `for_review` (and blocked when block is opt-in on); a WP with no new failures **and a non-empty affected run** transitions cleanly (an empty run is a no-coverage warn per SC-007, not "clean").
- **SC-007**: A change to an **empty-cone composite dir** (e.g. `src/specify_cli/validators/**`) yields a **"no-coverage-computed" warn**, NOT a silent clean pass — asserted with a `validators`-shaped fixture (guards against reopening the mission's own silent-under-coverage anti-goal).
- **SC-002**: A pre-existing base failure in an affected shard does NOT block the WP (baseline diff proven with a fixture where base is already red).
- **SC-003**: The affected set is derived per group shape (per-shard `tests/**` globs + composite `_COMPOSITE_ROUTING` cone_roots), catch-alls excluded — `status/emit.py` → the bounded `status` shard (NOT `core_misc`); a change to a composite dir (`git`) → the `tests/git` cone_roots; an arch invariant fails if the derivation drifts from the live authorities (FR-006).
- **SC-004**: The gate runs only the affected focused shards / composite cone_roots — asserted: a `status/emit.py` touch runs the `status` shard, not the `core_misc` ~17min whole-tree cone (the catch-all exclusion holds).
- **SC-005**: Frontmatter + config overrides take precedence per FR-004; `--force` bypass is recorded. Default remains warn (NFR-001).
- **SC-006**: `ruff` + `mypy --strict` clean; no new suppressions.

## Out of Scope
- CI dorny-routing widening + local shard preflight + Typer/click venv fix (#2283 Phase 3 — its own mission, high blast radius).
- Extending `stale_assertions.py` to surface un-owned contract-pinning / duplicate-named tests into the review prompt (#1979 ownership facet — Phase 2, overlaps M3/#2031).
- Reverse-import-graph affected-test computation (A1 — a separate mission if ever pursued).

## Assumptions
- `review/baseline.py`'s runner + diff are reusable as the gate engine without a rewrite.
- The census's shard→globs map is complete enough that file→shard derivation gives useful recall (Phase-3 routing gaps are acknowledged + out of scope).
