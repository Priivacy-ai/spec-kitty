# Mission Specification: Test-Suite Friction Remediation

**Mission ID**: `01KXDKBXDCDVZPXAHBKVGP9MWS` · **Slug**: `test-suite-friction-remediation` · **Type**: software-dev
**Epic**: [#2071](https://github.com/Priivacy-ai/spec-kitty/issues/2071) (Tests as scaffold, not friction), sub-issue of [#1931](https://github.com/Priivacy-ai/spec-kitty/issues/1931) (Test quality & suite hygiene)
**Sibling**: second of the "two missions, perf first" pair; the CI test-topology performance mission shipped as [PR #2609](https://github.com/Priivacy-ai/spec-kitty/pull/2609) (merged).

## Purpose

Pay down the residual test-as-scaffold friction that remains **after** the 2026-07-12 remediation wave already landed the biggest levers (composite-key ratchet re-key #2072/#2547/#2548, relocation-hardened dead-code scanners #2546/#2556, security xfail de-theater #2073, and the #2077 positional-anchor recurrence guard). What is left is a small, well-bounded set: a dead-code gate blind spot that forces live symbols onto permanent allowlists, a retired-but-still-present runtime_bridge compat-delegate surface, a handful of tests that assert *how* code is wired rather than *what* it does, and three structural CI guard holes surfaced while shipping the sibling performance mission. The mission also lands the tidy-first deshim in the **current** cycle so the deletions are not deferred into permanent debt.

This spec was authored from a pre-spec adversarial research squad (planner-priti, reviewer-renata, architect-alphonso, python-pedro), each profile-loaded and read-only, plus source-verified tracker states. The squad's dominant finding — that ~60% of the original briefing's premise was already merged — is reflected in the tightly-scoped requirement set below and the explicit **Out of Scope** section.

## Domain Language (canonical terms)

| Canonical term | Meaning | Avoid |
|---|---|---|
| **Architectural ratchet** | A test under `tests/architectural/` that pins a codebase invariant via an allowlist/baseline that shrinks over time. | "lint test", "gate test" (imprecise) |
| **Content-addressed key** (`composite_key`) | `(enclosing_qualname, normalized_token_line)` key from `tests/architectural/_ratchet_keys.py` that survives benign line drift. | "line key", "file:line anchor" |
| **Positional line-anchor** | A raw `(rel_path, int_line)` pair (or `path:NNN` string) used as a comparand; banned by the #2077 guard. | — |
| **Seed-tuple laundering** | Storing a raw `(rel, N)` tuple in a module-level seed constant, then feeding `N` through a loop variable into `composite_key(source, N)` — evading the int-to-line-sink detector. This is the #2564 hole. | — |
| **Compat delegate** | A thin re-export in `runtime.next.runtime_bridge` that forwards to a relocated seam module so `monkeypatch.setattr(runtime_bridge, …)` keeps working post-#2531. | "shim" (ambiguous with removed `specify_cli/next`) |
| **Source-as-text test** | A test that `read_text()`s a module and asserts a substring is/ isn't present, instead of exercising behaviour. | "wiring test" |
| **Observable contract** | A persisted artifact a test can assert on without patching the unit under test (event in `status.events.jsonl`, HTTP response body, rendered output, config on disk). | — |
| **Shard registry** | The `SHARD_GROUPS` mapping (`tests/_arch_shard_map.py`) that assigns test roots to CI shard groups. | — |
| **Suite job** | A CI job whose steps invoke `pytest`. | — |

## User Scenarios & Testing

**Primary actor**: a Spec Kitty maintainer refactoring production code, and the CI quality gate that guards their PR.

### Scenario 1 — a correct refactor must not be penalised (Cluster A / Cluster 0)
- **Trigger**: a maintainer makes a behaviour-neutral edit (inserts a line above a guarded site, relocates a symbol, renames an internal helper).
- **Happy path**: every architectural ratchet stays green because it keys on content, not position; no test asserts module source-as-text; the dead-code gate correctly recognises dynamically-accessed symbols as live, so no live symbol lands on a permanent allowlist.
- **Exception the mission closes**: today a maintainer can launder a positional line-anchor through a seed tuple (#2564), a `module.attr` dynamic access reads as dead (#2559), and a status-emit wiring test breaks on a behaviour-preserving rename (#2075).

### Scenario 2 — the tidy-first deshim lands cleanly (Cluster 0)
- **Trigger**: the retired `runtime.next.runtime_bridge` compat delegates and the grandfathered dead-symbol carry-over are removed.
- **Happy path**: the dead-code gate (now dynamic-access-aware, #2559) proves each deleted delegate is truly dead; the 26 `monkeypatch.setattr(runtime_bridge, …)` sites are repointed at their seam modules; the partial grandfathered burndown removes only symbols that flip to genuinely-dead.
- **Rule that must always hold**: **#2559 lands before any deletion.** A deletion that runs before the gate is dynamic-access-aware either kills a live façade symbol or re-adds a permanent allowlist row.

### Scenario 3 — no suite job or coverage source slips through un-gated (Cluster B)
- **Trigger**: someone adds a new CI job that runs `pytest`, or a new coverage source, or drops the shard-registry import line.
- **Happy path**: a guard fails loudly — the new suite job must be a member of `quality-gate.needs` (or explicitly declared non-blocking with a reason); the shard-registry completeness guard fails with a diagnosable "next not registered" instead of a bare `KeyError`; UI-e2e dashboard coverage reaches Sonar's denominator.
- **Exception the mission closes**: today `slow-tests`/`mutation-testing` are un-gated by convention only; a missing `_next_shard_map` import silently leaves `tests/next` unmarked; `coverage-ui-e2e.xml` never enters Sonar.

### Test strategy
Each work package is a test-first change with a **non-fakeable** definition of done (see NFR-002). Because the mission edits the very guards that police the suite, each guard change carries a focused regression proving the *new* failure mode is caught and the *old* false-red is gone.

## Functional Requirements

### Cluster 0 — tidy-first deshim & tooling (land in this cycle; strict internal order)

| ID | Requirement | Source | Status |
|---|---|---|---|
| FR-001 | The dead-code gate (`tests/architectural/test_no_dead_symbols.py` + `_symbol_key.py`) MUST recognise first-party `module.attr` dynamic access (e.g. `_runtime_bridge_module().<name>`) as a live reference, so a symbol reachable only via dynamic access is classified live, not dead. | #2559 | Planned |
| FR-002 | After FR-001, at least the 4 `runtime.next.runtime_bridge` façade symbols currently on the permanent allowlist because the gate could not see their dynamic access (`get_or_start_run`, `query_current_state`, `answer_decision_via_runtime`, `QueryModeValidationError`) MUST be removed from the permanent allowlist and pass as genuinely-live reachability checks. | #2559 | Planned |
| FR-003 | The `runtime.next.runtime_bridge` compat-delegate surface MUST be retired: each thin delegate whose only role is re-export forwarding is deleted, and every test that patches it via `monkeypatch.setattr(runtime_bridge, <name>)` / `"runtime.next.runtime_bridge.<name>"` is repointed at the owning seam module. | #2561 | Planned |
| FR-004 | The `category_b_grandfathered_legacy` dead-symbol carry-over MUST be burned down by the subset that FR-001 reclassifies as genuinely-dead; symbols that remain live-by-dynamic-access or are load-bearing `doctrine.*` re-exports MUST NOT be deleted, and the allowlist count MUST decrease from its current baseline (193, not the historical 237). | #2293 | Planned |

### Cluster A — genuine test-intrinsic friction (the #2071 core)

| ID | Requirement | Source | Status |
|---|---|---|---|
| FR-005 | The seed-tuple laundering hole in the positional-anchor ban MUST be closed: `test_ratchet_positional_anchor_ban.py` MUST flag a raw `(rel_path, int)` tuple stored in a module-level allowlist seed even when the `int` reaches `composite_key(source, N)` via an intermediate loop/local variable, and the residual raw seed tuples in `test_no_write_side_rederivation.py` / `test_trio_seam_only.py` MUST be converted to content-addressed keys. (`test_no_write_side_rederivation.py` was verified already content-addressed — WP06 records-and-skips it; only `test_trio_seam_only.py` converts.) | #2564 (P1) | Planned |
| FR-006 | The flagship stale golden-count MUST be corrected: `status/test_models.py` MUST assert the exact frozenset of `Lane` member names (not `len(Lane) == N`) and be renamed off "…nine_values". This is the exemplar pattern for the systematic sweep (FR-014). | #2076 (CT5) | Planned |
| FR-007 | The confirmed source-as-text wiring test MUST be re-pointed to an observable contract: the `read_text()`-based guard in `status/test_agent_status_emit_aggregate_wiring.py` MUST assert a persisted event / rendered output with no `@patch` on the module under test. Its three siblings (`test_dashboard/test_api_handler.py`, `agent/glossary/test_event_emission.py`, `sync/tracker/test_service.py`) MUST be audited and re-pointed **only where a genuine source-as-text/wiring twin is confirmed** (they are largely already observable-outcome); no false shared helper is manufactured across the four distinct seams. | #2075 (CT4) | Planned |
| FR-008 | A production-delegating mission factory MUST be introduced: `tests/_factories/make_mission()` MUST be a thin wrapper over `create_mission_core()` applying test-specific overrides on production-shaped meta, so one schema authority flows a new required field to every consumer. If `create_mission_core()` lacks a side-effect-free / no-coordination-branch entrypoint, adding that entrypoint is in scope; forking the schema is not. | #2074 (CT3) | Planned |
| FR-009 | The legacy-contract-backfill warning drain (#2553) MUST be resolved to a verified state: confirm whether the shipped work is a real contract fix or a warning suppression, then either close the issue as fixed or land the missing backfill. This requirement is bounded to verification + close/minimal-fix, not a re-open of the round-trip contract. | #2553 | Planned |
| FR-010 | The CI-quarantine triage backlog MUST be re-counted against current `main` (the historical "17 quarantined" is stale — ~1 quarantine mark remains, `tests/retrospective/test_summary_tolerance.py`) and the genuinely-quarantined residue triaged (re-enable, fix-root, or record a tracked reason). Cross-reference #2309 for reaper-family ownership; do NOT drive the count to 0 or re-enable a #2309-owned test. | #2295 | Planned |
| FR-016 | The mission MUST catalog every ratchet / no-regression-pinning suite and every behavioural-parity / equivalence test it touches or observes into the design-decisions tracer, applying the invariant-vs-shape discriminator, and MUST produce a keep / consolidate / retire verdict per suite at mission close — filing a follow-up mission/issue for the net-negative ones. (Operator hypothesis: these mass-added suites are net-negative development scaffold; this mission gathers the evidence, it does not remediate them wholesale.) | #2071 / operator | Planned |

### Cluster C — systematic golden-count remediation (kept in scope; ambitious, bounded)

| ID | Requirement | Source | Status |
|---|---|---|---|
| FR-014 | The stale golden-count friction MUST be solved across the batch-owned clean directories; excluded (co-owned) directory convert-sites are ledgered + deferred to follow-up #2625, not silently grandfathered: (1) an AST **inventory** of `len(<collection>) == <int>` in `tests/` classified `keep` (cardinality *is* the contract) vs `convert` (a set/frozenset-equality expresses it better); (2) a **recurrence guard** that fails on a NEW un-annotated golden-count assertion (escape hatch `# golden-count: cardinality-is-contract`); (3) a **baselined burndown** of the `convert` set that strictly decreases and never regrows. Bounded per-batch by the baseline; fanned into batch WPs by directory. | #2076 (CT5) | Planned |

### Cluster B — CI-topology guard seams (fenced cluster; PR #2609 tail)

| ID | Requirement | Source | Status |
|---|---|---|---|
| FR-011 | The shard registry MUST be assembled by an explicit, order-independent seam rather than an import side-effect: introduce a registry owner exposing an idempotent `register(group)` / `all_groups()` and an expected-group manifest, so the completeness guard fails as a diagnosable "group not registered" (never a bare `KeyError`) and a missing `tests/next` registration fails loud instead of silently leaving those tests unmarked. | #2621 | Planned |
| FR-012 | A guard MUST assert that every suite job (a CI job whose steps invoke `pytest`) is a member of `quality-gate.needs`, minus a reasoned `NON_BLOCKING_ALLOWLIST` in which each entry carries a why-non-blocking rationale. Jobs currently un-gated by convention (`slow-tests`, `mutation-testing`) MUST become either gate-blocking or explicitly-declared non-blocking. | #2622 | Planned |
| FR-013 | The UI-e2e dashboard coverage (`coverage-ui-e2e.xml`, `--cov=src/specify_cli/dashboard`) MUST reach Sonar's denominator: the sonarcloud job MUST discover the `ui-e2e.yml`-run artifact (cross-workflow, keyed to the head SHA's latest successful run), and a wiring guard MUST assert that path is among the discovered coverage set so it cannot silently rot. | #2623 | Planned |
| FR-015 | The gc2b exact-selection ratchet MUST stop over-firing on routine test-file add/remove (which this mission does 4–5× via new guard files): resolve #2616 by scoping the ratchet to orphans or making it advisory, preserving its load-bearing orphan-detection signal. | #2616 | Planned |

## Non-Functional Requirements

| ID | Requirement | Threshold / measure | Status |
|---|---|---|---|
| NFR-001 | Deletion safety ordering: FR-001 (dead-code gate dynamic-access awareness) MUST be merged before any Cluster-0 deletion (FR-003, FR-004). | Verified by WP dependency graph: the deletion WPs declare a dependency on the FR-001 WP; a deletion WP that lands first is a process violation. | Planned |
| NFR-002 | Every requirement's definition of done MUST be non-fakeable, asserting an observable artifact rather than a restatement. | Ratchet re-key: `test_ratchet_positional_anchor_ban.py` green on the real tree AND `git grep -E '\.py", *[0-9]{3}\)'` in `tests/architectural/` returns 0. Factory: output `meta.json` byte-identical AFTER normalizing the auto-minted `{mission_id, mid8, created_at}` (minus overrides) to a direct `create_mission_core()` call, and `tests/_factories/__init__.py` non-empty with ≥1 real importer. CT4 re-point: assertion on a persisted artifact with no `@patch` on the SUT. CT5: assertion on the exact lane-name frozenset. Golden-count sweep (FR-014): the `convert`-set baseline count strictly decreases per burndown WP and the recurrence guard fails on a fresh un-annotated `len==int` fixture. Deshim delete: dead-code gate green post-delete AND `git grep <symbol>` = 0 across `src` and `tests`. | Planned |
| NFR-003 | No production behaviour change. The mission edits tests, test tooling, and CI workflow wiring only; the sole production edits permitted are the FR-003 delegate deletions and the FR-008 `create_mission_core` test entrypoint, both behaviour-preserving. | Full suite green on the mission branch; no FR alters a runtime code path exercised in production. | Planned |
| NFR-004 | New and changed code passes `ruff` and `mypy` with zero issues/warnings, and complexity stays ≤ 15; no new blanket `# noqa` / `# type: ignore` / per-file ignore. | `ruff check .` and `mypy` clean on the diff. | Planned |
| NFR-005 | No retry-to-green. A test that goes red is judged (stale → re-pin to behaviour; stub → delete; valid → fix product); flakes are fixed at the root or budget-tuned, never retried. | Zero added retry decorators; flakiness policy followed. | Planned |
| NFR-006 | Diff-coverage / quality-gate / Sonar signals are treated as indicative; the mission MUST NOT pad with frivolous tests to move a gate, and any residual red gate is surfaced to the operator with rationale rather than silenced. | PR body records any advisory-gate residue. | Planned |
| NFR-007 | The three mission tracer files (`tracer-design-decisions.md`, `tracer-approach.md`, `tracer-tooling-friction.md`) MUST be appended in-the-moment during implement — in particular the ratchet/parity catalog (FR-016) and every ratchet-reanchor / parity false-red friction hit — and assessed at close (retroactive fill-in is a violation). | Dated entries exist per WP touching a pinning/parity suite; close-out verdict + follow-up filed. | Planned |

## Constraints

| ID | Constraint | Status |
|---|---|---|
| C-001 | **Out of scope — routed out.** #2463 (legacy mission support / empty-mid8 3-meaning sentinel), #2603 (`next_step` CC36), #2604 (`_mt_commit_wp_file`), #2465 (`workflow.py` resolver), and the full god-decompositions #2059/#2057/#2026/#2056/#2532/#2560/#2595/#2600 are NOT inlined; they route to #1797 / #2173 or their own slices. #2463 in particular is unsafe to delete now (its `""` sentinel conflates 3 live meanings; ~51 test files pin it; tests must be *split*, not bulk-deleted). | Fixed |
| C-002 | **Out of scope — split out of the test-hygiene framing.** #2309 (daemon-reaper kill-gate contract) is a **product bug** → red-first bugfix mission, not test scaffold. #2342 (retrospective 200-mission summary) is a **perf/reliability** item. #2323 (round-trip allowlist backfill) is count-keyed baseline accounting (inherent churn, not fixable friction). | Fixed |
| C-003 | **Canonical sources only.** Use doctrine templates, published skills, and the `spec-kitty` CLI; do not improvise paths or copy structure from older missions. | Fixed |
| C-004 | **Model & profile discipline.** Implement = sonnet (`python-pedro` for Python), review = opus (`reviewer-renata`); each delegation loads the profile YAML, never a persona name. | Fixed |
| C-005 | **No version prescription.** This spec assigns no patch/release number; the product owner superimposes release targeting at merge. | Fixed |
| C-006 | **Tidy-first, this cycle.** The deshim deletions (FR-003, FR-004) land in this mission, not deferred — gated only by the FR-001 safety ordering (NFR-001). | Fixed |
| C-007 | **Tracker hygiene.** The mission issue is a native sub-issue of #2071 (itself a native sub-issue of #1931). The three Thread-B items (FR-011/012/013) are filed as new issues under #1931/#2585 with blocks/related to #2609. Routed-out issues stay open under their existing parents (blocked_by/related #1797), never re-parented or closed by this mission. Attach via native sub-issue links, never epic-body checklists. | Fixed |
| C-008 | **Lanes topology (no coordination branch).** WPs implement in per-lane worktrees (`.worktrees/<slug>-<mid8>-lane-<id>`) and merge into `feat/test-suite-friction-remediation`, which becomes one PR to `upstream/main` at wrap-up. **Four lanes**: Lane 0 (deshim/tooling, strict serial IC-01→IC-02→IC-03), Lane A (test-intrinsic small fixes), Lane C (golden-count sweep, FR-014), Lane B (CI guards). Single-file ownership prevents cross-lane split-brain: `test_no_dead_symbols.py`→Lane 0, `tests/conftest.py`→IC-10, `ci-quality.yml`→Lane B. | Fixed |

## Success Criteria

- **SC-001** — A behaviour-neutral edit (line insertion above a guarded site, internal symbol relocation) produces zero architectural-ratchet false-reds across the mission's touched guards, demonstrated by a regression that inserts such an edit and stays green.
- **SC-002** — The dead-code gate classifies at least the 4 known dynamically-accessed `runtime_bridge` façade symbols as live without a permanent allowlist entry, and the retired compat-delegate surface is removed with the gate green and zero live-symbol regressions.
- **SC-003** — The seed-tuple laundering vector is provably blocked: a test that attempts to launder a `(rel, N)` seed through a loop variable into `composite_key` fails the ban guard.
- **SC-004** — No test in the mission's touched set asserts module source-as-text or `len(...) == N` where a content/set assertion is the real contract; each was converted to an observable-contract or exact-membership assertion.
- **SC-005** — Adding a new `pytest`-invoking CI job without wiring it into `quality-gate.needs` fails a guard; dropping the shard-registry registration fails with a diagnosable message (not a bare `KeyError`); UI-e2e dashboard coverage appears in Sonar's denominator.
- **SC-006** — The full test suite is green on the mission branch with `ruff`/`mypy` clean and no retry-to-green, no frivolous coverage padding.

## Key Entities

- **Dead-code gate** — `tests/architectural/test_no_dead_symbols.py`, `test_no_dead_modules.py`, `_symbol_key.py`: the whole-codebase symbol/module reachability scanners.
- **Ratchet key primitives** — `tests/architectural/_ratchet_keys.py` (`composite_key`, `composite_key_from_file`, `code_tokens_by_line`) and the ban guard `test_ratchet_positional_anchor_ban.py`.
- **runtime_bridge façade** — `src/runtime/next/runtime_bridge.py` and its post-#2531 seam modules (`runtime_bridge_{cores,io,identity,engine,composition}`).
- **Mission factory seam** — `create_mission_core()` (`mission_creation.py`) and the empty `tests/_factories/__init__.py`.
- **Shard registry** — `tests/_arch_shard_map.py` (`SHARD_GROUPS`), `tests/_next_shard_map.py`, `tests/architectural/test_arch_shard_marker_completeness.py`.
- **CI gate model** — `.github/workflows/ci-quality.yml` (`quality-gate`, `sonarcloud`), `ui-e2e.yml`, and the `_gate_coverage.WorkflowModel` parse engine.

## Assumptions

- **A-001** — The 2026-07-12 wave (#2072/#2073/#2077/#2546/#2547/#2548/#2556) is merged into `upstream/main` and is NOT re-scoped here (source-verified closed/merged).
- **A-002** — `create_mission_core()` is the documented programmatic mission-creation API; the FR-008 factory delegates to it. If it lacks a side-effect-free entrypoint, adding one is the real finding (in scope).
- **A-003** — The Thread-B follow-ups (FR-011/012/013) were declared in PR #2609's "Known follow-ups" and are not yet filed; they are filed as new issues during this mission.
- **A-004** — Radon cyclomatic complexity is the structural proxy aligned with the C901/S3776 ceiling of 15.
- **A-005** — The mission is orchestrated in one clone (`spec-kitty-gate-doctrine`) on a `lanes` topology (branch-flat, no coordination branch); WPs run in per-lane worktrees and the whole branch becomes one PR.

## Out of Scope (explicit)

Already shipped (do not re-scope): CT1 file:line→composite_key re-key (#2072/#2547/#2548), CT2 security xfail de-theater (#2073), dead-code scanner rewrite (#2546/#2556), #2077 positional-anchor recurrence guard, tasks.py degod (#2308).
Routed out (C-001/C-002): #2463, #2603, #2604, #2465, #2059, #2057, #2026, #2056, #2532, #2560, #2595, #2600, #2309, #2342, #2323, #2499 (optional consolidation — deferred unless the operator explicitly pulls it).
