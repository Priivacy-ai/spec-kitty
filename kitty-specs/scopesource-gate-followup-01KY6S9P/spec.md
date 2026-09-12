# Mission Specification: ScopeSource gate follow-up — cleanup & correctness

**Mission Branch**: `fix/scopesource-gate-followup`
**Created**: 2026-07-23
**Status**: Draft (post-spec + post-plan squad hardened)
**Input**: Follow-ups from the #2873 adversarial investigation of the doctrine-controlled transition gates (half A, PR #2871, epic #2535). All four items verified against merged `main` (`564522eb8`); file:line evidence in the #2873 issue comment. Hardened by a 3-lens post-spec adversarial squad (correctness / deletion-safety / roadmap) — record in `reviews/post-spec-squad.md`.

## Overview

Half A of the doctrine-controlled transition gates shipped three deliberately-deferred follow-ups (#2873). This mission closes all four investigated items in three work packages (WP-A cleanup, WP-B contract, WP-C correctness), sequenced **A→C** (WP-C reuses WP-A's hoisted factory) with **WP-B parallel/independent**.

- **Cleanup** — retire a fully-duplicated, production-dead census-derivation tier and a dead compat helper; decouple a port contract that welds two orthogonal concerns onto one type check.
- **Correctness** — close the unrealized "one command authority for baseline and head" promise. Today baseline capture reads a config test command while the head run derives its command from the injected `ScopeSource`; the two draw failure identities from potentially-disjoint namespaces, which mis-reports **every** review as `NEW_FAILURES` the moment a consumer configures a non-pytest command or half B (#2599) introduces a second head command source. **The naive fix (merely activating the dormant `_capture_baseline_via_scope_source`) reintroduces the same bug** for artifact-based declared commands via a parse-after-teardown asymmetry (see FR-008/US1) — so the correctness work is specified to close that too.

Half B (executable gate assets, #2599) remains **out of scope**; this mission makes the gate correct and clean *before* half B builds on it.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Reviews are not falsely blocked when baseline and head share one command authority (Priority: P1)

A repository using the doctrine-controlled pre-review gate runs a work-package review. Baseline (captured at implement time on the base branch) and head (at `for_review`) derive their test command from the **same** `ScopeSource` **and read their test artifacts through the same parse mode**, so failure identities live in one namespace and the baseline diff reports only genuinely-new failures. A source/parse-mode mismatch is surfaced as a distinct, warn-shaped `SOURCE_MISMATCH` outcome — never a silent false block.

**Why this priority**: This is the mission's correctness reason. Without it, a consumer with a non-pytest `review.test_command`, or the arrival of a second head source (half B), gets a false `NEW_FAILURES` hard-block on every review — the gate becomes actively wrong. It is the prerequisite that unblocks half B (#2599).

**Independent Test**: Run the gate over a zero-new-failure change with (a) `GateCoverageScopeSource`, (b) `DeclaredCommandScopeSource` whose command writes a **worktree-relative** JUnit artifact, and (c) a `DeclaredCommandScopeSource` using the FAIL-text convention; the gate must NOT raise `NEW_FAILURES` in any case. A parity test asserts baseline and head land in the same failure-identity namespace across all three.

**Acceptance Scenarios**:

1. **Given** a head run using a `ScopeSource` and a change with zero new failures, **When** the gate captures baseline and evaluates head, **Then** both derive the test command from the same shared factory, the baseline artifact is read before its worktree is torn down, and the gate does not raise `NEW_FAILURES`.
2. **Given** a baseline produced by one source/parse-mode and a head run whose source/parse-mode differs, **When** the diff runs, **Then** the gate emits a warn-shaped `SOURCE_MISMATCH` outcome (fail-open, distinct reason), NOT a `NEW_FAILURES` block and NOT a silent pass.
3. **Given** a repo with no `review.test_command` (spec-kitty itself), **When** the gate runs, **Then** behavior is unchanged (baseline skipped → `UNVERIFIED_BASELINE` warn).
4. **Given** an old `BaselineTestResult` artifact lacking the source-identity field (straddling upgrade), **When** the diff runs, **Then** it degrades to an unverified warn, never a `KeyError` or a spurious mismatch.

---

### User Story 2 - The dead census-derivation tier is retired without touching the live gate (Priority: P2)

The production-dead census-derivation tier in `pre_review_gate.py` (`derive_test_scope` and its private helpers/constants) — a full duplicate of the live logic in `scope_source.py` — and the dead `_mt_pre_review_gate_verdict` helper are removed. The live gate verdict is provably identical before and after, across BOTH the registry path and the kept override tier.

**Why this priority**: ~450 LoC of dead duplicate is a standing anti-duplication liability and enlarges the surface the correctness and contract work reason about. Retiring it also hoists the shared `ScopeSource` factory that WP-C reuses.

**Independent Test**: A golden captured from the pre-mission commit against BOTH the live `for_review` hook and the FR-004 override tier proves identical verdicts, metadata, and exit codes; the C-002 keep-live set survives (import + functional assertion); the dead-symbol, compat-surface, and census-parity gates pass (or are retired together with their target); the migrated verdict-diff tests stay green.

**Acceptance Scenarios**:

1. **Given** the live registry dispatch always injects a non-`None` `GateCoverageScopeSource`, **When** the census tier and `_mt_pre_review_gate_verdict` are deleted, **Then** the live for_review gate AND the override tier produce byte-identical verdicts + metadata (behavior-preservation golden passes).
2. **Given** the pre-deletion audit proves the census branch is the sole live `scope_source=None` entry, **When** the deletion lands, **Then** no live caller is broken.
3. **Given** the census tests exercised only the deleted duplicate (or used `derive_test_scope` as an oracle) and 8 verdict-diff tests passed the dropped `filter_groups`/`composite_routing` params, **When** the former are retired/repointed and the latter are migrated to `scope_source=` injection, **Then** no live-path coverage is lost and the suite is green.

---

### User Story 3 - The ScopeBreakdownSource contract expresses its two decisions independently (Priority: P3)

The single `isinstance(scope_source, ScopeBreakdownSource)` check that today decides *both* "an empty derived scope is a coverage gap" (policy) and "this source exposes breakdown metadata" (capability) is replaced by two **independently-evaluable** named predicates, and `file_to_scope` becomes a default projection over `scope_breakdown` so a breakdown-capable source implements one method.

**Why this priority**: Internal API hygiene with zero behavior change. It removes the weld so a future source can express one decision without the other; it does not further couple the two.

**Independent Test**: The two predicates are asserted independently by a migrated test; both shipped implementations behave identically to before; `GateCoverageScopeSource` implements only `scope_breakdown` (inheriting `file_to_scope`); a synthetic source can satisfy one predicate without the other.

**Acceptance Scenarios**:

1. **Given** the two consumer sites, **When** each calls its intent-appropriate predicate (`empty_scope_is_coverage_gap` vs `exposes_scope_breakdown`), **Then** verdicts are unchanged for both shipped sources.
2. **Given** a base class provides `file_to_scope` as a projection over `scope_breakdown`, **When** `GateCoverageScopeSource` inherits it, **Then** it defines only `scope_breakdown`; `DeclaredCommandScopeSource` remains a structural implementer with no `scope_breakdown` and reports "empty ≠ gap".
3. **Given** the two predicates are backed by independent signals, **When** a synthetic source declares breakdown capability while opting out of empty-is-gap (or vice versa), **Then** each predicate returns the declared value independently (proving the weld is gone, not merely renamed).

### Edge Cases

- Repo with no `review.test_command`: baseline is skipped → `UNVERIFIED_BASELINE` — must remain unchanged.
- Baseline runs the whole command (broad) while head runs a narrowed target set: command **authority** is unified but **scope** legitimately differs; correctness depends only on failure-identity alignment. The `pre_existing` count (a superset under a broad baseline) stays correct.
- `diff_baseline`'s "fixed" element is not surfaced by any live consumer today; a broad baseline would make it inaccurate, but it is latent and harmless until a consumer reads it — the mission does **not** fix it, and MUST NOT claim to (documented, not asserted).
- Mixed source/parse-mode (baseline `GateCoverageScopeSource`, head `DeclaredCommandScopeSource`, or artifact-vs-text): must emit `SOURCE_MISMATCH`, not silently block.
- `_CompositeRoute` is referenced live (bound as `pre_review_gate._CompositeRoute`, consumed via `_mt_resolve_scope_source`) even though it sits in the census cluster — it must survive the deletion.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Retire the dead census tier | As a maintainer, I want `derive_test_scope` and its census helpers/constants (`_glob_matches_file`, `_glob_to_pytest_target`, `_src_dir_segment`, `resolve_excluded_catchall_groups`, `NAMED_CATCHALL_GROUPS`, `_WHOLE_SRC_TREE_GLOB`, `_live_filter_groups`, `_live_composite_routing`, `_SRC_PACKAGE_PREFIX`, `_TESTS_PREFIX`, `_EMPTY_COMPOSITE_ROUTE`) removed from `pre_review_gate.py`; the live private duplicate in `scope_source.py` is untouched. | High | Open |
| FR-002 | Delete the dead verdict helper + simplify the signature, gated by a pre-deletion audit | As a maintainer, I want `_mt_pre_review_gate_verdict` (and its `tasks.py:442` re-export + `test_tasks_compat_surface.py:247` entry, golden count decremented by exactly 1 for the removed symbol — 156→155 on current `main`, but **157→156 once PR #2874 lands** (it adds `_binding_role_for_lane` to the same tuple); restate the exact numbers against the base at plan time) deleted so `evaluate_pre_review_gate` can drop `filter_groups`/`composite_routing` and the `scope_source=None` default — **preceded by a test/documented audit proving the census branch is the sole live caller reaching `evaluate_pre_review_gate` without a `scope_source`** (the load-bearing precondition). | High | Open |
| FR-003 | Hoist the ScopeSource factory to a shared home with its seams | As a maintainer, I want `_mt_resolve_scope_source` extracted to a shared module both the `for_review` hook and the implement-time baseline path import, **with its override seams (`_pre_review_gate_filter_groups`/`_pre_review_gate_composite_routing`) moved with it or passed as parameters so no import cycle back into `tasks_move_task` is created**. | High | Open |
| FR-004 | Exhaustively migrate/retire the affected tests with a coverage-parity inventory | As a maintainer, I want: (a) census-only tests retired (`test_census_parity.py`, `test_pre_review_scope_singlesource.py`, the 6 `_derive`-based tests in `test_pre_review_gate_engine.py`); (b) the two `derive_test_scope`-oracle tests repointed onto `GateCoverageScopeSource`/`_scope_result_from_source`; (c) **the 8 verdict-diff tests in `test_pre_review_gate_engine.py` (`:827,843,868,897,918,936,961,996`) MIGRATED from `filter_groups=/composite_routing=` to `scope_source=` injection** (the `_gate_coverage_source` helper at `:293` already exists); and (d) an inventory mapping each retired test to its surviving equivalent OR an explicit "intentionally not carried forward because X", so no live-path coverage is lost; the coverage-parity inventory is a **committed artifact reviewed at gate** (each retired test → a named surviving test id or explicit "not carried forward because X"), and the **mutation-bite** assertions of `test_pre_review_scope_singlesource.py` (proving census derivation consults LIVE CI topology) are **migrated FORWARD** onto `GateCoverageScopeSource`'s private census helpers, not merely retired. | High | Open |
| FR-005 | Split the welded check into two independent predicates | As a maintainer, I want the single `isinstance(scope_source, ScopeBreakdownSource)` decision replaced by two **independently-evaluable** named predicates — `empty_scope_is_coverage_gap` (the empty⇒NO_COVERAGE policy, `pre_review_gate.py:881`) and `exposes_scope_breakdown` (the metadata capability, `:1013`) — backed by separate signals so a source can satisfy one without the other, with no verdict change for the shipped sources. | Medium | Open |
| FR-006 | file_to_scope as a default projection | As a maintainer, I want a base class (ABC/mixin — NOT a Protocol default, which won't reach the structural implementers) to provide `file_to_scope` as a projection over `scope_breakdown`, so `GateCoverageScopeSource` implements only `scope_breakdown`; `DeclaredCommandScopeSource` retains no `scope_breakdown` and still satisfies the port structurally. | Medium | Open |
| FR-007 | Migrate the intent-encoding test | As a maintainer, I want the test that pins "membership ⇒ empty-is-gap" migrated to assert the two predicates independently (incl. a synthetic source that satisfies one but not the other) rather than the raw `isinstance`. | Medium | Open |
| FR-008 | Unify command authority AND artifact lifecycle | As a repo owner, I want the shared `ScopeSource` factory injected into the implement-time baseline capture (activating `_capture_baseline_via_scope_source`) so baseline and head derive their command from one authority, **and the baseline artifact read/parsed (or relocated to a stable out-of-worktree path) BEFORE the base worktree is torn down**, so artifact-based `parse_results` is symmetric with the head path (closes the parse-after-teardown asymmetry). The red-first carrier is a **direct** `capture_baseline`/`_capture_baseline_via_scope_source` unit test with `DeclaredCommandScopeSource` + a **worktree-relative** `--junitxml`, red on the base commit *before* the relocate fix (the workflow-routed path is dormant on base); the relative `--junitxml` resolves against `cwd=tmp_worktree`. | High | Open |
| FR-009 | Record + assert source/parse-mode identity, fail-open | As a repo owner, I want the baseline's producing-source identity — including **parse mode / artifact-presence**, not just class/command-shape — recorded in `BaselineTestResult` and asserted against the head source **in the injected-`ScopeSource` head path only** (not the shared override tier). The diff-time baseline read MUST consume PR #2874's kind-aware `_resolve_workflow_read_dir(kind=WORK_PACKAGE_TASK)` seam (which #2874 rewrote `_mt_resolve_gate_baseline` to use), NOT a reconstructed `feature_dir`. `from_dict` defaults a missing identity to an "unknown → unverified warn", so a mismatch fails loud and legacy artifacts never crash. | High | Open |
| FR-010 | Dual-implementation, dual-parse-mode baseline↔head parity test | As a repo owner, I want a parity test proving baseline and head land in the same failure-identity namespace under `GateCoverageScopeSource` AND under `DeclaredCommandScopeSource` for BOTH a **worktree-relative JUnit artifact** case and a FAIL-text case (the cases B1 exposed). | High | Open |
| FR-011 | Dedicated SOURCE_MISMATCH outcome | As an operator, I want a source/parse-mode mismatch to surface as a dedicated warn-shaped `GateOutcome.SOURCE_MISMATCH` (fails open, distinct reason string), NOT an overloaded `NO_COVERAGE` (empty-scope) and NOT a hard `NEW_FAILURES` block, so operators and future half-B code can branch on it unambiguously. MUST add an explicit `SOURCE_MISMATCH` branch to `_mt_pre_review_gate_console_warning` AND convert its trailing `return "…no new failures"` fall-through into an explicit `NO_NEW_FAILURES` branch + a defensive `else` (rendering the raw `outcome.value`), so no future `GateOutcome` member can silently render as a clean pass. The block/terminal paths are member-explicit allowlists (`verdict_aggregation._TERMINAL_OUTCOMES`, the `NEW_FAILURES` block) → `SOURCE_MISMATCH` is fail-open by construction: assert this with a test, do NOT edit those filters. | High | Open |
| FR-012 | Anti-narrowing guard for the baseline | As a maintainer, I want a focused test asserting the baseline command is run WITHOUT head's per-file `scope.test_targets` appended, so a future refactor cannot silently narrow the baseline and break the broad-baseline/narrow-head invariant (C-005). | Medium | Open |
| FR-013 | Docs + comment hygiene for the deletion | As a maintainer, I want no docs-code-sync/anti-sprawl gate to reference the deleted symbols as live, and the stale docstrings referencing the dropped `filter_groups`/`composite_routing` params cleaned, so NFR-002 (ruff/mypy) and the docs gates stay green. **Campsite fold (baseline.py is already rewritten by WP-C):** delete the unused `timezone` import (`baseline.py:25`) and tighten its `ruff.toml` legacy-debt entry from `["ARG001","F401","S314","S602"]` to `["ARG001","S314"]` (F401 clears once the import is gone; S602 is already stale — no `shell=True` in the file). | Low | Open |
| FR-014 | Config-driven ScopeSource selection (delivers SC-001) | As a repo owner, I want `resolve_scope_source` to SELECT the source from config — `DeclaredCommandScopeSource` when `review.test_command` is present (non-pytest), else `GateCoverageScopeSource` — so a real non-pytest consumer repo runs baseline + head through ONE command authority and SC-001 is achievable against an actual repository (not only a synthetic injected test), keeping the `_capture_baseline_via_config` behavior alive via the portable source. Also fix the now-stale `scope_source.py:51-55` "lands with #2873" comment + `docs/development/review-gates.md:174` single-authority line. | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Behavior preservation (registry-path golden) | The live `for_review` gate verdict — all `GateOutcome` members, transition metadata, console output, exit codes — is identical before and after the WP-A deletions, proven by a golden captured from the pre-mission commit against the live `_mt_run_transition_gates` hook (not regenerated post-deletion). | Correctness | High | Open |
| NFR-002 | Static-analysis clean | New/changed code passes `mypy --strict` and `ruff` with zero issues and zero warnings; cyclomatic complexity ≤ 15 per function. No new `# noqa` / `# type: ignore` / suppression. | Maintainability | High | Open |
| NFR-003 | New-code coverage | ≥ 90% line+branch coverage on new/changed code; every new predicate/helper/branch/outcome has a focused test. | Testability | High | Open |
| NFR-004 | No gate regressions | The dead-symbol (`__all__`), compat-surface (`SYMBOL_TO_MODULE` + the compat golden count decremented by 1 — restate against the post-#2874 base, expected 157→156), census-parity, and ratchet gates pass — or are retired atomically with their target — with no orphaned or missing entries. | Maintainability | High | Open |
| NFR-005 | Factory resolves identically (defined) | For the same mission and config, the shared factory yields sources that are **equivalent = equal `test_command()` output AND equal parse-mode/identity**, verified under BOTH real call-site roots (baseline `main_repo_root` vs head `gate_repo_root`, not one shared root); a **structural** assertion pins that capture and diff reference the SAME `scope_source_identity` helper; `source_identity` deliberately EXCLUDES the command by design (NFR-005 carries command equality). A test pins this so the split cannot re-open. | Correctness | High | Open |
| NFR-006 | Kept-tier behavior preservation | A behavior-preserving golden ALSO covers the FR-004 override tier (frontmatter `pre_review_test_scope` / config override → `_mt_pre_review_gate_with_override_scope` → `evaluate_with_scope(scope_source=None)`), and an import+functional assertion proves the C-002 keep-live set survives — because NFR-001's registry-path golden does not exercise the override tier the deletion could sever. The override golden MUST drive a **non-empty derived scope** so `evaluate_with_scope → run_scoped_tests_at_head` actually execute (not just the empty-scope path) — "functional" means each kept symbol's body runs in ≥1 golden case, not merely imports. | Correctness | High | Open |
| NFR-007 | Non-circular golden via the canonical harness | The NFR-001/006 goldens are captured with the EXISTING canonical harness (`tests/review/fixtures/parity/_capture.py` + `tests/review/test_transition_gate_parity.py`), pinned to base `eb06ca176`, asserting `HEAD==base` at capture, machine-emitting the `base_commit` provenance, committed BEFORE the WP-A deletion — no improvised snapshot, no hand-typed SHA (CLAUDE.md canonical-sources). | Correctness | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Half B is out | Executable gate assets (#2599, half B) are out of scope; `handler_kind: asset` stays inert. This mission only makes the half-A gate correct and clean. | Scope | High | Open |
| C-002 | Deletions are behavior-preserving | The live path (registry dispatch → `GateCoverageScopeSource`) is never routed through the removed census tier. KEEP `_CompositeRoute` (bound `pre_review_gate._CompositeRoute`, live via `_mt_resolve_scope_source:1262`), `_pre_review_gate_filter_groups`/`_pre_review_gate_composite_routing`, `evaluate_with_scope`, `run_scoped_tests_at_head`, `ScopeResult` (+ `from_override`/`describe_empty_reason`/`is_empty`), `_mt_pre_review_gate_with_override_scope`, `_mt_empty_scope_verdict`. | Technical | High | Open |
| C-003 | Sequencing A→C, B parallel | The only hard dependency is **WP-A→WP-C**: WP-C reuses WP-A's hoisted factory (FR-003). **WP-B is independent** (its predicate/mixin edits fold into WP-A's `GateCoverageScopeSource` work or run in parallel); it is NOT a prerequisite for WP-C. | Technical | High | Open |
| C-004 | Frozen compat surface edited via the sanctioned path | Removing `_mt_pre_review_gate_verdict` updates the `tasks.py:442` re-export AND `test_tasks_compat_surface.py` (tuple entry + the compat golden count decremented by 1 — post-#2874 base is 157, so 157→156) in one atomic change — never an accidental import break. | Technical | High | Open |
| C-005 | Unify command authority, not scope | Baseline runs the whole command (broad); head runs the narrowed target set. Do not force baseline to narrow; correctness depends only on baseline and head drawing failure identities from one namespace (guarded by FR-012). | Technical | High | Open |
| C-006 | ATDD red-first | Every requirement lands test-first: the failing test (or the behavior-preservation golden / audit) exists and is red before the code change that greens it. | Process | High | Open |

### Key Entities

- **`ScopeSource` / `ScopeBreakdownSource`**: the injectable port (`test_command`/`file_to_scope`/`parse_results`) and its breakdown-capable refinement (`scope_breakdown`); post-mission the two gate decisions are separate predicates.
- **`GateCoverageScopeSource`**: incumbent census-narrowing impl; JUnit at an absolute out-of-worktree tempfile (survives teardown).
- **`DeclaredCommandScopeSource`**: portable impl (no `scope_breakdown`; empty scope not a gap); its command may write a worktree-relative artifact — the B1 risk surface.
- **`BaselineTestResult`**: the persisted baseline artifact; gains a source/parse-mode identity field (FR-009), compared at diff time; `from_dict` defaults it to "unknown → unverified warn".
- **`GateOutcome.SOURCE_MISMATCH`**: new warn-shaped, fail-open outcome for source/parse-mode mismatch (FR-011).
- **Shared `ScopeSource` factory**: the hoisted `_mt_resolve_scope_source` (+ its seams) consumed by both baseline capture and the head hook.

## Rebase & Fold Notes (fold/boyscout squad, 2026-07-23)

A 3-lens fold/boyscout squad (carla ticket-mining / paula boyscout / alphonso collision — record in `reviews/fold-boyscout-squad.md`) confirmed **#2873's 13-FR envelope is the right scope — no external ticket is worth folding in.** Plan-time watch-items (the mission is HELD until PRs #2874 + #2820 land):

- **Plan against the post-#2874/#2820 tree.** #2874 (`remediation/coord-trust-2841`) is the only real adjacency: it shifts the compat golden base to 157 (FR-002/C-004/NFR-004 restate to 157→156) and rewrote `_mt_resolve_gate_baseline` to a kind-aware read seam that FR-009 must consume (folded into FR-009). Its edits do NOT touch the census tier, the factory def, the predicates, or `GateOutcome` — only golden numbers (rebase-around) + the baseline read seam (fold).
- **#2820 is disjoint** (dossier `BaselineSnapshot` ≠ our `BaselineTestResult`; zero shared files). One benign watch-item: FR-009's new `baseline-tests.json` field changes that file's content hash → shifts a mission's dossier parity hash (per-mission runtime data, not a collision; no fixture/symbol shared).
- **Boyscout: one trivial fold only** — the `baseline.py` unused `timezone` import + its over-broad `ruff.toml` entry (folded into FR-013). A `verdict_aggregation.py:48` comment fix rides along only if FR-011 opens that file. The dead `capture_baseline(mission_slug=…)` param is explicitly OUT (ripples into ~8 test callsites; separate ticket if ever wanted).
- **Side-findings (not this mission):** #2741 (pre-review diffs working tree) appears **already fixed** by mission merge-base-diff-ssot (`55d060016`) → candidate to close as fixed. #2825's pre-existing `test_no_dead_symbols` / `test_golden_count_ban` reds on `main` are the SAME gate family FR-002/FR-004 touch → confirm their pre-existing status on the base before attributing any golden-count/dead-symbol failure to this mission's diff (baseline-red-gotcha).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A repository configured with a non-pytest `review.test_command` (including a worktree-relative-artifact command) completes a pre-review gate over a zero-new-failure change **without** a false `NEW_FAILURES` block.
- **SC-002**: The live `for_review` gate AND the override tier on spec-kitty produce byte-identical verdicts and transition metadata before and after the mission (behavior-preservation goldens pass across all `GateOutcome` members).
- **SC-003**: The dead census duplicate (~450 LoC across source + tests) is removed, the 8 verdict-diff tests are migrated (not lost), and the dead-symbol / compat-surface / census-parity / ratchet gates are green (or retired with their target); zero net new dead symbols.
- **SC-004**: A head `ScopeSource` whose source/parse-mode mismatches the baseline produces a `GateOutcome.SOURCE_MISMATCH` warn (not a silent block, not `NO_COVERAGE`) — demonstrated by a test.
- **SC-005**: `GateCoverageScopeSource` implements exactly one narrowing method (`scope_breakdown`) and the two orthogonal gate decisions are each expressed by an independently-evaluable named predicate (a synthetic source can satisfy one without the other).
