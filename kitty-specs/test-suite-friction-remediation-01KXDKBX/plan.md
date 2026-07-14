# Implementation Plan: Test-Suite Friction Remediation

**Branch**: `feat/test-suite-friction-remediation` | **Date**: 2026-07-13 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/test-suite-friction-remediation-01KXDKBX/spec.md`
**Tracker**: mission #2620 (sub-issue of #2071 under #1931); WPs close #2559/#2561/#2293/#2564/#2076/#2075/#2074/#2553/#2295 + new #2621/#2622/#2623.

## Summary

Pay down the residual test-as-scaffold friction remaining after the 2026-07-12 wave, across **four lanes** on a `lanes` topology: (Lane 0) a tidy-first deshim gated on a dead-code-gate tooling upgrade, (Lane A) a small set of direct test-intrinsic fixes, (Lane C) a systematic golden-count remediation sweep (kept in scope per operator directive — don't kick the can), and (Lane B) the structural CI-topology guard seams from the perf mission's tail. The single hard sequencing rule is **NFR-001**: the dead-code gate must learn to see first-party dynamic access (IC-01/#2559) *before* any Cluster-0 deletion runs, so the gate — not manual grep — proves each deletion safe. Every change is test-first with a non-fakeable definition of done (NFR-002). The mission also carries an **operator hypothesis** (FR-016): ratchet/no-regression-pinning and behavioural-parity suites, mass-added recently, are suspected net-negative scaffold — the mission catalogs them in the tracer files toward a close-out keep/consolidate/retire verdict (it does not remediate them wholesale).

## Technical Context

**Language/Version**: Python 3.11+ (repo standard; `ruff`/`mypy` clean, complexity ceiling 15)
**Primary Dependencies**: pytest (+ pytest-xdist), the in-repo architectural-test infrastructure (`tests/architectural/_ratchet_keys.py`, `_symbol_key.py`, `_gate_coverage.WorkflowModel`, `_arch_shard_map.py`), and GitHub Actions workflows (`.github/workflows/ci-quality.yml`, `ui-e2e.yml`). No new runtime dependencies.
**Storage**: N/A (test code, test tooling, CI YAML, and two behaviour-preserving production edits: FR-003 delegate deletions, FR-008 `create_mission_core` test entrypoint).
**Testing**: pytest, ATDD/red-first for behaviour changes; each guard change carries a focused regression proving the new failure mode is caught and the old false-red is gone. Parallel run `PWHEADLESS=1 pytest tests/ -n auto --dist loadfile`; UI-e2e headless per `docs/development/ui-e2e.md`.
**Target Platform**: Linux CI + local dev; the "user" is the maintainer and the CI quality gate.
**Project Type**: single project (the spec-kitty CLI repo and its test suite / CI).
**Performance Goals**: N/A — this mission does not change runtime performance; it may only reduce CI false-reds and gate-maintenance churn. (Do not add perf assertions; #2342 perf work is out of scope.)
**Constraints**: No production behaviour change (NFR-003); no retry-to-green (NFR-005); coverage/Sonar treated as indicative, no frivolous padding (NFR-006); canonical sources only (C-003); no version prescription (C-005); tidy-first — deshim lands this cycle (C-006).
**Scale/Scope**: ~10 WPs across 3 lanes; touches `tests/architectural/`, `tests/status/`, `tests/adversarial`-adjacent wiring tests, `tests/_factories/`, `tests/_arch_shard_map.py`/`_next_shard_map.py`, `src/runtime/next/runtime_bridge*`, `src/specify_cli/.../mission_creation.py` (test entrypoint only), and `.github/workflows/`.

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Charter present (`.kittify/charter/charter.md`); context mode `compact`. Governing constraints applied:
- **ATDD-first / red-first (DIR-041, tests-as-scaffold)**: every behaviour change and every guard change ships a failing-first proof; the mission *is* the tests-as-scaffold-not-friction remediation, so its own DoDs are non-fakeable (NFR-002). ✅
- **Test-remediation discipline**: judge each red test (stale→re-pin to behaviour; stub→delete; valid→fix product); never retry-to-green (NFR-005). ✅
- **Architectural gate discipline**: guard changes (IC-01/04/10/11/12) pin negative/behavioural invariants, not code shape; positive-literal scans converted or deleted. ✅
- **Canonical sources**: use `_ratchet_keys.composite_key`, `_gate_coverage.WorkflowModel`, `create_mission_core()` — no improvised parallels (C-003). ✅
- **Campsite-first / tidy-first**: deshim deletions land this cycle, gated only by IC-01 safety ordering (C-006, NFR-001). ✅
- **No god-module decomposition inlined**: full degods routed out to #1797/#2173 (C-001). ✅
No charter violations to justify — Complexity Tracking left empty.

## Project Structure

### Documentation (this mission)

```
kitty-specs/test-suite-friction-remediation-01KXDKBX/
├── plan.md              # This file
├── research.md          # Phase 0 output (already-done verification + seam confirmations)
├── data-model.md        # Phase 1 output (guard/entity contracts, no persistent data model)
├── quickstart.md        # Phase 1 output (how to run the affected guards + suite)
├── contracts/           # Phase 1 output (guard behaviour contracts)
└── tasks.md             # Phase 2 output (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)

```
tests/
├── architectural/
│   ├── test_no_dead_symbols.py         # IC-01 dead-code gate (dynamic-access awareness) [#2559]
│   ├── _symbol_key.py                   # IC-01 reachability key
│   ├── test_ratchet_positional_anchor_ban.py   # IC-04 seed-tuple hole [#2564]
│   ├── test_no_write_side_rederivation.py       # IC-04 residual seed tuples
│   ├── test_trio_seam_only.py                   # IC-04 residual seed tuples
│   └── test_arch_shard_marker_completeness.py   # IC-10 shard-registry guard [#2621]
├── status/
│   ├── test_models.py                   # IC-05 golden-count → lane frozenset [#2076]
│   └── test_agent_status_emit_aggregate_wiring.py  # IC-06 source-as-text → observable [#2075]
├── _factories/__init__.py               # IC-07 make_mission() delegating factory [#2074]
├── _arch_shard_map.py / _next_shard_map.py         # IC-10 explicit register() seam [#2621]
└── (contract/quarantine)                # IC-08 #2553 verify-close, IC-09 #2295 recount
src/
├── runtime/next/runtime_bridge*.py      # IC-02 retire compat delegates [#2561]
└── specify_cli/.../mission_creation.py  # IC-07 create_mission_core test entrypoint (behaviour-preserving)
.github/workflows/
├── ci-quality.yml                       # IC-11 quality-gate.needs guard [#2622], IC-12 sonar discovery [#2623]
└── ui-e2e.yml                           # IC-12 UI-e2e coverage source [#2623]
```

**Structure Decision**: Single-project repo. Changes are concentrated in `tests/architectural/` (guards + tooling), a broad `tests/` sweep (Lane C golden-count), a few `tests/status`/`tests/_factories` files, two behaviour-preserving `src/` edits, and `.github/workflows/`. Lane grouping = the four lanes (see the IC map's Lane & WP shaping directives).

## Mission Tracers & ratchet/parity catalog (FR-016)

Three tracer files are seeded in the mission dir (`tracer-design-decisions.md`, `tracer-approach.md`, `tracer-tooling-friction.md`) per the `mission-tracer-files` procedure. Beyond the standard friction/approach/decision logging, `tracer-design-decisions.md` carries a **standing catalog of ratchet/no-regression-pinning and behavioural-parity suites** (the operator's net-negative-scaffold hypothesis). Every WP that touches or observes such a suite MUST append a catalog row (invariant-vs-shape discriminator + CaaCS churn); the mission-close assess step produces a keep/consolidate/retire verdict and files a follow-up for the net-negative suites. This is evidence-gathering, not wholesale remediation — the follow-up mission owns the actual retirement.

## Complexity Tracking

*No Charter Check violations — section intentionally empty.*

## Implementation Concern Map

> Concerns are NOT work packages. `/spec-kitty.tasks` translates these into executable WPs and lanes. This map was hardened by a post-planning brownfield squad (architect-alphonso, paula-patterns, planner-priti, 2026-07-13); their adjustments are folded below.

### Lane & WP shaping directives (post-plan squad — binding for /tasks)

- **Four lanes** (was three): **Lane 0** deshim/tooling · **Lane A** test-intrinsic (small) · **Lane C** golden-count remediation (large sweep) · **Lane B** CI-topology guards.
- **Lane 0 is a STRICT SERIAL CHAIN `IC-01 → IC-02 → IC-03` in a single worktree — no parallel WPs inside Lane 0.** All three co-tenant the allowlist in `tests/architectural/test_no_dead_symbols.py`; the earlier "IC-01 is the only cross-lane predecessor" claim was incomplete — IC-02 and IC-03 also collide on that file. `/tasks` MUST emit them as one ordered chain (or add explicit `IC-02→IC-03` edge), never as concurrent WPs.
- **Single-file ownership** (avoid split-brain merge conflicts): `tests/architectural/test_no_dead_symbols.py` → Lane 0 only; `tests/conftest.py` → **IC-10 only** (it co-tenants the quarantine-deselection block and the shard-marker hook); `.github/workflows/ci-quality.yml` → Lane B, IC-11 then IC-12 serialized.
- **New-guard-file DoD** (applies to IC-10, IC-11, IC-12, and any IC that adds a `tests/architectural/*.py` file): register the new file in `tests/_arch_shard_map.py` AND re-freeze both gate-coverage baselines — gc3b `tests/architectural/_gate_coverage_baseline.json` (`--update-baseline`) and gc2b `tests/architectural/baselines/*.txt` (`--freeze-baselines`); the residual must negate every `next_shard`/`arch_shard` marker. **IC-01 stays Lane-0-local by EXTENDING existing files — it must NOT spawn a new arch file** (which would drag it onto the Lane-B `_arch_shard_map.py` surface).
- **DAG is clean** (`IC-01→IC-02→IC-03`; all else roots) — the flat/lanes allocator's post-finalize DFS cycle-check passes.

### Cluster 0 → Lane 0 — tidy-first deshim & tooling (STRICT SERIAL CHAIN)

### IC-01 — Dead-code gate: first-party dynamic-access awareness (PURE TOOLING)
- **Purpose**: Teach the dead-code scanner to resolve first-party `module.attr` dynamic access (e.g. `_runtime_bridge_module().<name>`) as a live reference. **Pure tooling — no allowlist-row edits** (those move to IC-02/IC-03, the single allowlist owners).
- **Relevant requirements**: FR-001, FR-002.
- **Affected surfaces**: `tests/architectural/_symbol_key.py` + EXTEND the existing AST tests in `tests/architectural/test_no_dead_symbols.py` in place. **No new `tests/architectural/*.py` file** (stay Lane-0-local; see directives).
- **Sequencing/depends-on**: none — **first in the Lane-0 chain; precedes IC-02 and IC-03** (NFR-001).
- **Risks**: false-positive liveness could hide a truly-dead symbol; focused AST tests prove both directions (dynamic-access→live, unreferenced→dead). Do NOT special-case `runtime_bridge` by name — resolve the dynamic-accessor shape generally (contract: `contracts/dead-code-dynamic-access.md`).

### IC-02 — Retire the runtime_bridge compat-delegate surface (CRITICAL PATH)
- **Purpose**: Delete the ~37 thin re-export delegates in `runtime.next.runtime_bridge`, repoint the monkeypatch sites at their owning seam modules, and remove the deleted delegates' allowlist rows in `test_no_dead_symbols.py`.
- **Relevant requirements**: FR-003.
- **Affected surfaces**: `src/runtime/next/runtime_bridge*.py`; the allowlist rows in `tests/architectural/test_no_dead_symbols.py`; **audit surface is ~157 `setattr(runtime_bridge…/"runtime.next.runtime_bridge.")` occurrences across ~76 test files** (grep-classify forwarding-vs-real-seam FIRST; only the forwarding subset repoints). Do NOT inline the #2560 strangler route-out.
- **Sequencing/depends-on**: **IC-01** (gate proves each deleted delegate truly dead). **Precedes IC-03** (both edit the allowlist).
- **Risks**: **the mission's critical-path pole** — size for the full 157-site audit, claim first after IC-01. Patch-target drift; a missed repoint red-fails a sibling test.

### IC-03 — Partial grandfathered-legacy burndown (SOLE remaining allowlist owner)
- **Purpose**: Remove from `category_b_grandfathered_legacy` only the subset IC-01 reclassifies as genuinely dead; keep live-by-dynamic-access and load-bearing `doctrine.*` re-exports. Owns the final allowlist mutation + baseline recount.
- **Relevant requirements**: FR-004.
- **Affected surfaces**: the allowlist in `tests/architectural/test_no_dead_symbols.py` (baseline **193**, not 237).
- **Sequencing/depends-on**: **IC-02** (last in the Lane-0 chain; rebases on IC-02's allowlist-row deletions and baseline-count shift).
- **Risks**: over-deletion of a live `doctrine.*` re-export; the count must *decrease* but not reach 0.

### Cluster A → Lane A — genuine test-intrinsic friction (fix-directly, no degod; WPs parallelizable)

### IC-04 — Close the seed-tuple laundering hole in the positional-anchor ban
- **Purpose**: Extend `test_ratchet_positional_anchor_ban.py` to flag a raw `(rel, int)` seed laundered through a loop/local into `composite_key(source, N)`, and convert the residual raw seed tuples to content-addressed keys.
- **Relevant requirements**: FR-005 (P1).
- **Affected surfaces**: `test_ratchet_positional_anchor_ban.py` (guard extension) + `test_trio_seam_only.py` (`_IO_ALLOWLIST_SITES` ~L463 — **the single remaining launderer**). NOTE: `test_no_write_side_rederivation.py` already uses content-addressed `ContentDescriptor` seeds (clean), and the `\.py", *[0-9]{3}\)` grep in `tests/architectural/` is **already 0** — the direct anchors were closed by the #2077 wave. Real work = guard extension + the one `trio_seam` conversion.
- **Sequencing/depends-on**: none (zero `runtime_bridge` refs — no hidden Lane-0 edge).
- **Risks**: the AST detector must not flag legitimate `composite_key` calls whose 2nd arg is a genuine live line from `code_tokens_by_line` — keep the int-to-seed-sink predicate precise (contract: `contracts/positional-anchor-ban-hole.md`).

### IC-05 — Lane-enum golden count → content assertion (flagship exemplar)
- **Purpose**: Replace `len(Lane) == N` with an exact `Lane` member-name frozenset (rename the test off "…nine_values"). This is the exemplar for the systematic sweep (IC-14).
- **Relevant requirements**: FR-006.
- **Affected surfaces**: `tests/status/test_models.py` (~L30) only.
- **Sequencing/depends-on**: none. **Precedes/anchors IC-14** as the pattern reference.
- **Risks**: minimal — one file, one assertion shape.

### IC-06 — Source-as-text wiring test → observable contract (+ sibling audit)
- **Purpose**: Re-point the confirmed source-as-text twin to an observable contract; AUDIT the 3 siblings and re-point any that the audit confirms are genuine source-as-text/wiring twins (fix in-mission, do not defer).
- **Relevant requirements**: FR-007.
- **Affected surfaces**: **confirmed twin** `tests/status/test_agent_status_emit_aggregate_wiring.py:211` (`test_command_module_has_no_direct_transactional_reference`, `read_text()`); **audit-then-fix-if-real**: `test_dashboard/test_api_handler.py`, `agent/glossary/test_event_emission.py`, `sync/tracker/test_service.py` (paula's read: largely already observable-outcome with incidental `@patch` — fix only where a real twin exists; do NOT hand-roll a false shared helper across four different seams).
- **Sequencing/depends-on**: none.
- **Risks**: over-deleting a legitimate boundary-verification test — keep the real-outcome one; assert a persisted artifact with no `@patch` on the SUT.

### IC-07 — Production-delegating mission factory
- **Purpose**: Add `tests/_factories.make_mission()` as a thin wrapper over `create_mission_core()` (`src/specify_cli/core/mission_creation.py:206`); if that seam lacks a side-effect-free / no-coordination-branch entrypoint, add it (production edit, behaviour-preserving). Do not migrate the 329-writer tail (Directive 024).
- **Relevant requirements**: FR-008.
- **Affected surfaces**: `tests/_factories/__init__.py`, `src/specify_cli/core/mission_creation.py`.
- **Sequencing/depends-on**: none.
- **Risks**: forking the schema instead of delegating — DoD is byte-identical meta vs a direct `create_mission_core()` call + `_factories/__init__.py` non-empty with ≥1 real importer.

### IC-08 — Verify-and-close hygiene (folds former IC-09)
- **Purpose**: One housekeeping WP with two terminal, zero-production-code tasks: (a) #2553 legacy-contract backfill — verify the shipped work is a real fix (not a warning suppression), close or minimal-fix; (b) #2295 CI-quarantine recount — the "17" is stale (exactly **one** active `@pytest.mark.quarantine` remains, `tests/retrospective/test_summary_tolerance.py:704`), triage the residual marker.
- **Relevant requirements**: FR-009, FR-010.
- **Affected surfaces**: `tests/contract/test_example_round_trip.py` (read-only unless a real gap surfaces — stay bounded, do NOT drift into #2323's baseline accounting); quarantine markers + `tests/_support/quarantine.py`. **Does NOT touch `tests/conftest.py`** (that hook is IC-10's).
- **Sequencing/depends-on**: none.
- **Risks**: #2295 recount must **cross-reference #2309** (the routed-out reaper bug) for reaper-family ownership and must NOT drive quarantine to 0 or re-enable a #2309-owned test. If #2553 uncovers a real backfill gap, this grows back into its own WP.

### Cluster C → Lane C — golden-count remediation sweep (ambitious, bounded by a baseline + guard)

### IC-14 — Systematic golden-count assertion remediation
- **Purpose**: Solve the CT5 tail rather than defer it (#2076). Across the suite there are ~2102 `len(<collection>) == <int>` assertions in ~646 files; a large subset are brittle golden counts that break on benign set changes where a set/frozenset-equality is the real contract. Classify, convert the convertible subset, and prevent regrowth.
- **Relevant requirements**: FR-006, FR-014.
- **Approach (bounded, non-fakeable)**: (1) build an AST **inventory** of `len(...) == int` in `tests/`, classified `keep` (cardinality *is* the contract) vs `convert` (a set/dict-equality already or better expresses it); (2) add a **recurrence guard** (AST) that fails on a NEW un-annotated golden-count assertion, closing the class going forward; (3) establish a **baseline count** of the `convert` set and burn it down in batches — the baseline strictly decreases and never regrows.
- **Affected surfaces**: broad across `tests/` (the `convert` subset); a new guard beside the other architectural guards (subject to the new-guard-file DoD: shard-register + baseline re-freeze).
- **Sequencing/depends-on**: **IC-05** anchors the exemplar pattern. `/tasks` SHOULD fan this into: one inventory+guard WP, then N conversion-batch WPs (parallelizable by directory) — this is where the mission's added ambition lives.
- **Risks**: converting a `len==N` where cardinality genuinely IS the contract (keep those); the guard must not flag legitimate cardinality assertions — the annotation escape hatch (`# golden-count: cardinality-is-contract`) keeps it precise. Boil-the-ocean risk is contained by the baseline (measurable per-WP) + guard (no regrowth).

### Cluster B → Lane B — CI-topology guard seams (PR #2609 tail; IC-10 first, then IC-11/IC-12 serialized on ci-quality.yml)

### IC-10 — Explicit shard-registry seam (owns tests/conftest.py)
- **Purpose**: Replace the import-side-effect assembly of `SHARD_GROUPS` with an idempotent `register()`/`all_groups()` + expected-group manifest so the completeness guard fails diagnosably (never a bare `KeyError`) and an unmarked `tests/next` universe fails loud.
- **Relevant requirements**: FR-011 (#2621).
- **Affected surfaces**: new `tests/_shard_registry.py`, `tests/_arch_shard_map.py`, `tests/_next_shard_map.py`, `tests/architectural/test_arch_shard_marker_completeness.py`, **`tests/conftest.py` (sole owner — co-tenants the quarantine-deselection block + shard-marker hook)**. New-guard-file DoD applies.
- **Sequencing/depends-on**: none — **first in Lane B** so its registry/markers land before IC-11/IC-12 add more arch files.
- **Risks**: registration-order regressions during the seam swap — keep idempotent + manifest-asserted (contract: `contracts/shard-registry-seam.md`).

### IC-11 — quality-gate.needs ⊇ pytest-jobs guard
- **Purpose**: Assert every `pytest`-invoking CI job is a member of `quality-gate.needs`, minus a reasoned `NON_BLOCKING_ALLOWLIST`; force `slow-tests`/`mutation-testing` to declare non-blocking-with-reason or become gate-blocking.
- **Relevant requirements**: FR-012 (#2622).
- **Affected surfaces**: new guard beside `test_workflow_coherence.py`, using `_gate_coverage.WorkflowModel` (`tests/architectural/_gate_coverage.py:372`); possibly `.github/workflows/ci-quality.yml` if a job must join `needs`. New-guard-file DoD applies.
- **Sequencing/depends-on**: after IC-10; serialized with IC-12 on `ci-quality.yml`.
- **Risks**: mis-detecting pytest steps — anchor on `\bpytest\b` in run-cmds; each allowlist entry carries a rationale (contract: `contracts/quality-gate-needs-containment.md`).

### IC-12 — Sonar UI-e2e coverage denominator
- **Purpose**: Make the sonarcloud job discover the `ui-e2e.yml`-run `coverage-ui-e2e.xml` (cross-workflow, head-SHA-keyed) and add a wiring guard that the path is in the discovered set.
- **Relevant requirements**: FR-013 (#2623).
- **Affected surfaces**: `.github/workflows/ci-quality.yml` (sonarcloud job), a `test_coverage_consumer_needs`-style guard. New-guard-file DoD applies.
- **Sequencing/depends-on**: after IC-11 (same `ci-quality.yml`).
- **Risks**: cross-workflow artifact lookup auth/run-id edge cases — mirror the existing `prev_run` fallback shape; verifiable only post-merge, so pair with the pre-merge wiring guard.

### IC-13 — gc2b exact-selection ratchet: stop over-firing on routine test add/remove
- **Purpose**: Fold #2616 — the gc2b exact-selection baseline fires on every routine test-file add/remove (which THIS mission does 4–5× via new guard/regression files). Resolve per the issue's own options: scope the ratchet to orphans, or make it advisory, so the mission (and future ones) stop fighting their own guard.
- **Relevant requirements**: FR-015 (#2616).
- **Affected surfaces**: the gc2b selection guard + `tests/architectural/baselines/*.txt` handling.
- **Sequencing/depends-on**: **land early in Lane B** — once it relieves the exact-selection firing, the other new-guard-file ICs' baseline-refreeze burden shrinks (keep the refreeze DoD as fallback until IC-13 lands).
- **Risks**: loosening the ratchet too far (losing real orphan-detection signal) — scope-to-orphan preserves the load-bearing invariant; advisory-only is the weaker fallback.
