# Tasks: Test-Suite Friction Remediation

**Mission**: test-suite-friction-remediation-01KXDKBX | **Branch**: `feat/test-suite-friction-remediation`
**Plan**: [plan.md](./plan.md) (14-IC / 4-lane map, post-plan-squad hardened) | **Spec**: [spec.md](./spec.md)

**17 work packages across 4 lanes.** Every WP is test-first with a **non-fakeable** definition of done
(NFR-002) and every WP that touches or observes a ratchet/pinning or behavioural-parity suite appends a
row to `tracer-design-decisions.md` (the standing catalog) + logs friction to `tracer-tooling-friction.md`
(FR-016 / NFR-007).

## Lane shape (binding — see plan.md "Lane & WP shaping directives")

- **Lane 0 — deshim/tooling (STRICT SERIAL CHAIN):** WP01 → WP02 (classify-only) → WP03 → WP04 → WP18
  (delete) → WP05. All co-tenant the dead-code gate's allowlist surface; they MUST run as one ordered chain,
  never concurrently. NFR-001: the dead-code gate (WP01) learns first-party dynamic access **before** any
  Cluster-0 deletion (WP18/WP05). **Re-sequence note:** the runtime_bridge src-delegate deletion was moved
  OUT of WP02 into the new WP18 (post-repoint), because a delegate cannot be deleted until WP03/WP04 repoint
  the test sites and the frozen compat baseline is updated — WP02 empirically proved 0-deletable-today.
- **Lane A — test-intrinsic (PARALLEL roots):** WP06, WP07, WP08, WP09, WP10 — independent, no cross edges.
- **Lane C — golden-count sweep:** WP11 (inventory + recurrence guard, deps WP07) → WP12, WP13, WP14
  (directory-disjoint conversion batches, each deps WP11).
- **Lane B — CI guards (SERIAL):** WP15 (gc2b scope-to-orphan, root — lands early to relieve the new-file
  baseline burden) → WP16 (shard-registry seam) → WP17 (CI gate + coverage guards).

**Single-file ownership invariants:** `tests/architectural/test_no_dead_symbols.py` → WP05 only;
`tests/conftest.py` → WP16 only; `.github/workflows/ci-quality.yml` → WP17 only; `tests/_arch_shard_map.py`
→ WP16 owns the seam (WP11/WP17 append their new-guard registration as recorded out-of-map edits);
`src/runtime/next/runtime_bridge*.py` + `tests/runtime/test_bridge_compat_surface.py` → **WP18** owns the
deletion (WP04's `tests/runtime/**` glob overlaps the compat file but is sequential-exempt: WP18 ← WP04).

## Dependency graph (edges)

```
WP01 → WP02 → WP03 → WP04 → WP18 → WP05  (Lane 0 serial; WP02 classify-only, WP18 delete)
WP06  (root)   WP07 (root)   WP08 (root)   WP09 (root)   WP10 (root)   (Lane A)
WP07 → WP11 → {WP12, WP13, WP14}        (Lane C)
WP15 → WP16 → WP17                       (Lane B serial)
```

Roots: WP01, WP06, WP07, WP08, WP09, WP10, WP15.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | First-party `module.attr` dynamic-access resolution in `_symbol_key.py` (general accessor shape) | WP01 | |
| T002 | Fixture-based AST test: dynamic-access → live (into `test_no_dead_symbols.py`, recorded out-of-map) | WP01 | |
| T003 | Fixture-based AST test: unreferenced → dead (negative direction still holds) | WP01 | |
| T004 | Verify the 4 known façade symbols classify live without an allowlist row; gate green | WP01 | |
| T005 | ruff/mypy clean; tracer catalog + friction rows | WP01 | |
| T006 | Grep-classify the ~416 `setattr(runtime_bridge…)` occurrences (53 files; WP03 ~241 + WP04 ~168) forwarding-vs-real-seam | WP02 | |
| T007 | Delete the pure re-export delegates in `runtime_bridge.py`; keep the 8 canonical `__all__` names | WP02 | |
| T008 | Delete pure re-export delegates in the seam modules (if any) | WP02 | |
| T009 | Dead-code gate green (proves each deleted delegate dead) + runtime suite green | WP02 | |
| T010 | ruff/mypy clean; NFR-001 dependency-on-WP01 recorded; tracer rows | WP02 | |
| T011 | Repoint forwarding monkeypatch sites in `tests/next/**` to their owning seam modules | WP03 | |
| T012 | Repoint the two heavy files (`test_query_mode_unit`, `test_runtime_bridge_unit`) | WP03 | |
| T013 | `tests/next` suite green; no `runtime_bridge`-forwarded patch remains | WP03 | |
| T014 | ruff/mypy clean; tracer rows | WP03 | |
| T015 | Repoint forwarding sites in `tests/runtime/**`, `tests/specify_cli/**` | WP04 | |
| T016 | Repoint forwarding sites in `tests/integration/**`, `tests/contract/**`, misc | WP04 | |
| T017 | Affected suites green (incl. `tests/runtime/test_bridge_parity.py`) | WP04 | |
| T018 | ruff/mypy clean; tracer rows (parity suite observed) | WP04 | |
| T019 | Remove the 4 `runtime_bridge` façade allowlist rows (now live via WP01 gate) | WP05 | |
| T020 | Burn down the `category_b_grandfathered_legacy` subset WP01 reclassifies as genuinely dead | WP05 | |
| T021 | Single baseline recount (193 → decreases, NOT to 0); keep live `doctrine.*` re-exports | WP05 | |
| T022 | DoD: dead-code gate green; `git grep <deleted symbol>` = 0 across `src`+`tests` | WP05 | |
| T023 | ruff/mypy clean; tracer catalog rows | WP05 | |
| T024 | Extend the ban guard to catch `(rel,int)` laundered via loop var into `composite_key(source,N)` | WP06 | [P] |
| T025 | Regression fixture that *attempts* the laundering fails the ban | WP06 | [P] |
| T026 | Convert `test_trio_seam_only._IO_ALLOWLIST_SITES` (~L463) to content-addressed keys | WP06 | [P] |
| T027 | DoD: `git grep -E '\.py", *[0-9]{3}\)' tests/architectural/` = 0; ban green on the real tree | WP06 | [P] |
| T028 | ruff/mypy clean; tracer rows | WP06 | [P] |
| T029 | Assert the exact `Lane` member-name frozenset (replace `len(Lane) == N`) | WP07 | [P] |
| T030 | Rename the test off "…nine_values" | WP07 | [P] |
| T031 | `tests/status/test_models.py` green | WP07 | [P] |
| T032 | ruff/mypy clean; tracer row (exemplar pattern for WP11) | WP07 | [P] |
| T033 | Re-point the confirmed twin (`:211` `read_text`) to an observable contract, no `@patch` on the SUT | WP08 | [P] |
| T034 | Audit `test_dashboard/test_api_handler.py` — repoint ONLY if a genuine source-as-text twin | WP08 | [P] |
| T035 | Audit `glossary/test_event_emission.py` + `sync/tracker/test_service.py` — repoint only genuine twins | WP08 | [P] |
| T036 | DoD: no `@patch` on the SUT in any re-pointed test; assert a persisted artifact | WP08 | [P] |
| T037 | ruff/mypy clean; tracer parity rows | WP08 | [P] |
| T038 | Add a side-effect-free / no-coordination entrypoint to `create_mission_core()` if missing | WP09 | [P] |
| T039 | Implement `make_mission()` delegating wrapper in `tests/_factories/__init__.py` | WP09 | [P] |
| T040 | Factory-parity test: `meta.json` byte-identical (minus overrides) to a direct core call | WP09 | [P] |
| T041 | DoD: `tests/_factories/__init__.py` non-empty with ≥1 real importer | WP09 | [P] |
| T042 | ruff/mypy clean; tracer row (parity assertion) | WP09 | [P] |
| T043 | Verify #2553 is a real contract fix, not a warning suppression → close or minimal-fix | WP10 | [P] |
| T044 | Recount #2295 quarantine (~1 active marker, `test_summary_tolerance.py:704`) | WP10 | [P] |
| T045 | Triage the residual marker; cross-ref #2309; do NOT drive to 0; MUST NOT edit `conftest.py` | WP10 | [P] |
| T046 | DoD evidence; confirm zero production behaviour change | WP10 | [P] |
| T047 | tracer row (quarantine ratchet observed) | WP10 | [P] |
| T048 | AST inventory of `len(<collection>) == <int>` in `tests/` → classify `keep` vs `convert` | WP11 | |
| T049 | Write the recurrence guard `test_golden_count_ban.py` (fails NEW un-annotated; escape hatch) | WP11 | |
| T050 | Regression: a fresh un-annotated `len==int` fixture fails the guard | WP11 | |
| T051 | Establish the `convert`-set baseline; emit the inventory artifact partitioned BY DIRECTORY | WP11 | |
| T052 | New-guard-file DoD: register in `_arch_shard_map.py` (out-of-map append) + refreeze gc3b & gc2b | WP11 | |
| T053 | DoD: guard green on the real tree; anchors WP07's exemplar pattern | WP11 | |
| T054 | ruff/mypy clean; tracer catalog rows | WP11 | |
| T055 | Pull WP11's inventory `convert`-set for this batch's owned directories | WP12 | [P] |
| T056 | Convert `len==N` → set/frozenset-equality per file (owned dirs only) | WP12 | [P] |
| T057 | Decrement the `convert`-set baseline (strictly decreases; never regrows) | WP12 | [P] |
| T058 | Affected suites + golden-count guard green | WP12 | [P] |
| T059 | ruff/mypy clean; tracer rows | WP12 | [P] |
| T060 | Pull WP11's inventory `convert`-set for this batch's owned directories | WP13 | [P] |
| T061 | Convert `len==N` → set/frozenset-equality per file (owned dirs only) | WP13 | [P] |
| T062 | Decrement the `convert`-set baseline (strictly decreases; never regrows) | WP13 | [P] |
| T063 | Affected suites + golden-count guard green | WP13 | [P] |
| T064 | ruff/mypy clean; tracer rows | WP13 | [P] |
| T065 | Pull WP11's inventory `convert`-set for this batch's owned directories | WP14 | [P] |
| T066 | Convert `len==N` → set/frozenset-equality per file (owned dirs only) | WP14 | [P] |
| T067 | Decrement the `convert`-set baseline (strictly decreases; never regrows) | WP14 | [P] |
| T068 | Affected suites + golden-count guard green | WP14 | [P] |
| T069 | ruff/mypy clean; tracer rows | WP14 | [P] |
| T070 | Scope the gc2b exact-selection ratchet to orphans (or advisory) per #2616 | WP15 | |
| T071 | Regression: routine test-file add/remove no longer trips red; orphan detection preserved | WP15 | |
| T072 | Verify the load-bearing orphan-detection signal is retained | WP15 | |
| T073 | DoD; ruff/mypy clean | WP15 | |
| T074 | tracer row (gc2b ratchet) | WP15 | |
| T075 | Introduce `_shard_registry.py`: idempotent `register()` / `all_groups()` + expected-group manifest | WP16 | |
| T076 | Refactor `_arch_shard_map.py` + `_next_shard_map.py` to register via the seam (drop `# noqa: F401`) | WP16 | |
| T077 | `test_arch_shard_marker_completeness.py`: diagnosable "group not registered", never bare `KeyError` | WP16 | |
| T078 | `conftest.py` shard-marker hook uses the registry; an unmarked `tests/next` universe fails loud | WP16 | |
| T079 | Regression: drop `_next_shard_map` registration → diagnosable message; unmarked universe fails | WP16 | |
| T080 | New-guard-file DoD (self-register + refreeze baselines); ruff/mypy; tracer | WP16 | |
| T081 | `test_suite_jobs_gate_blocking.py`: `pytest_jobs − NON_BLOCKING_ALLOWLIST ⊆ quality-gate.needs` | WP17 | |
| T082 | Resolve `slow-tests` / `mutation-testing` to explicit gated OR allowlisted-with-rationale | WP17 | |
| T083 | Regression: a fake pytest job added to the model → guard fails | WP17 | |
| T084 | `ci-quality.yml` sonarcloud discovers `ui-e2e.yml` `coverage-ui-e2e.xml` (cross-workflow, head-SHA) | WP17 | |
| T085 | `test_ui_e2e_coverage_discovered.py` wiring guard asserts the path is in the discovered set | WP17 | |
| T086 | `ci-quality.yml` `quality-gate.needs` edits if a job must join; new-guard-file DoD; ruff/mypy; tracer | WP17 | |
| T087 | Delete the WP02-classified forwarding delegates now repointed by WP03/WP04 (grep=0 per name; gate proves dead) | WP18 | |
| T088 | Refactor the 3 production `_rb.<name>` call-sites to import the seam leaf directly; delete their façade delegates | WP18 | |
| T089 | Update the frozen `test_bridge_compat_surface.py` exact-baseline: drop exactly the deleted symbols; surviving sentinels intact | WP18 | |
| T090 | Dead-code gate + `tests/runtime` (incl. `test_bridge_parity.py`) green | WP18 | |
| T091 | ruff/mypy clean; final runtime_bridge parity/compat tracer verdict; NFR-001 recorded | WP18 | |

## Work Packages

### WP01 — Dead-code gate: first-party dynamic-access awareness (FR-001)

**Goal**: Teach `_symbol_key.py` to resolve first-party `module.attr` dynamic access as a live reference,
generally (no `runtime_bridge` special-case). Pure tooling — no allowlist edits (those are WP05's).
**NFR-001 anchor**: this lands before any Cluster-0 deletion. **Independent test**: focused AST fixtures
prove both directions (dynamic-access→live, unreferenced→dead).

- [x] T001 First-party `module.attr` dynamic-access resolution in `_symbol_key.py` (WP01)
- [x] T002 Fixture AST test: dynamic-access → live (into `test_no_dead_symbols.py`, recorded out-of-map) (WP01)
- [x] T003 Fixture AST test: unreferenced → dead (WP01)
- [x] T004 The 4 known façade symbols classify live without a row; gate green (WP01)
- [x] T005 ruff/mypy clean; tracer catalog + friction rows (WP01)

Prompt: [tasks/WP01-dead-code-dynamic-access.md](./tasks/WP01-dead-code-dynamic-access.md) · ~240 lines · deps: none

### WP02 — Classify the runtime_bridge compat-delegate surface (FR-003) — CRITICAL PATH

**Goal (re-sequenced → classification-only):** Grep-classify the ~416 `setattr(runtime_bridge…)`
occurrences (53 test files; WP03 ~241 in `tests/next` + WP04 ~168) into forwarding-vs-real-seam, and record
the 45-candidate pure-forwarding table (deletable-after-repoint vs canonical-`__all__` vs
needs-call-site-refactor). **The src-delegate DELETION moved to WP18** (post-repoint) — WP02 empirically
proved 0-deletable-today (deleting any forwarder reds the frozen `test_bridge_compat_surface.py` baseline
and/or an un-repointed patcher; 3 have live production `_rb.<name>` deps). **Independent test**:
classification recorded + baseline stays green (zero src diff).

- [x] T006 Grep-classify the ~416 forwarding-vs-real-seam occurrences (53 files; WP03 ~241 + WP04 ~168) (WP02)
- [x] T007 Delete pure re-export delegates in `runtime_bridge.py`; keep the 8 `__all__` names (WP02)
- [x] T008 Delete pure re-export delegates in the seam modules (if any) (WP02)
- [x] T009 Dead-code gate green + runtime suite green (WP02)
- [x] T010 ruff/mypy clean; NFR-001 dep recorded; tracer rows (WP02)

Prompt: [tasks/WP02-runtime-bridge-delegate-deletion.md](./tasks/WP02-runtime-bridge-delegate-deletion.md) · ~260 lines · deps: WP01

### WP03 — Repoint monkeypatch sites, batch A: `tests/next/**` (FR-003)

**Goal (repoint-only):** Repoint the forwarding `monkeypatch.setattr(runtime_bridge, …)` sites in
`tests/next/**` (12 files, ~241 occurrences incl. the two heaviest) at their owning seam modules, so the
delegates become deletable by WP18. Do NOT delete any src delegate here (that is WP18's surface, post-WP04).
**Independent test**: `tests/next` suite green with zero remaining `runtime_bridge`-forwarded patches.

- [x] T011 Repoint forwarding sites in `tests/next/**` (WP03)
- [x] T012 Repoint the two heavy files (`test_query_mode_unit`, `test_runtime_bridge_unit`) (WP03)
- [x] T013 `tests/next` suite green (WP03)
- [x] T014 ruff/mypy clean; tracer rows (WP03)

Prompt: [tasks/WP03-repoint-monkeypatch-batch-a.md](./tasks/WP03-repoint-monkeypatch-batch-a.md) · ~220 lines · deps: WP02

### WP04 — Repoint monkeypatch sites, batch B: runtime/specify_cli/integration/misc (FR-003)

**Goal (repoint-only):** Repoint the remaining forwarding sites (runtime, specify_cli, integration, contract,
agent, perf, unit — ~40 files, ~168 occurrences), disjoint from WP03, so the delegates become deletable by
WP18. Do NOT delete any src delegate here, and do NOT edit `tests/runtime/test_bridge_compat_surface.py`
(WP18 owns the frozen-baseline update; WP04's `tests/runtime/**` glob is sequential-exempt from it).
**Independent test**: affected suites green incl. the behavioural-parity `tests/runtime/test_bridge_parity.py`.

- [x] T015 Repoint `tests/runtime/**`, `tests/specify_cli/**` (WP04)
- [x] T016 Repoint `tests/integration/**`, `tests/contract/**`, misc (WP04)
- [x] T017 Affected suites green (incl. `test_bridge_parity.py`) (WP04)
- [x] T018 ruff/mypy clean; tracer rows (parity suite observed) (WP04)

Prompt: [tasks/WP04-repoint-monkeypatch-batch-b.md](./tasks/WP04-repoint-monkeypatch-batch-b.md) · ~230 lines · deps: WP03

### WP05 — Allowlist reconciliation + grandfathered burndown (FR-002, FR-004)

**Goal**: Remove the 4 façade allowlist rows (now live via WP01) and burn down the
`category_b_grandfathered_legacy` subset WP01 reclassifies as genuinely dead — baseline 193 decreases,
NOT to 0; keep live `doctrine.*` re-exports. **Independent test**: dead-code gate green;
`git grep <deleted symbol>` = 0 across `src`+`tests`.

- [x] T019 Remove the 4 `runtime_bridge` façade allowlist rows (WP05)
- [x] T020 Burn down the `category_b_grandfathered_legacy` genuinely-dead subset (WP05)
- [x] T021 Single baseline recount (193 → decreases, not 0); keep live `doctrine.*` (WP05)
- [x] T022 DoD: gate green; `git grep <deleted symbol>` = 0 across `src`+`tests` (WP05)
- [x] T023 ruff/mypy clean; tracer catalog rows (WP05)

Prompt: [tasks/WP05-allowlist-reconciliation-burndown.md](./tasks/WP05-allowlist-reconciliation-burndown.md) · ~240 lines · deps: WP18

### WP06 — Close the seed-tuple laundering hole in the positional-anchor ban (FR-005)

**Goal**: Extend `test_ratchet_positional_anchor_ban.py` to flag a `(rel,int)` seed laundered through a
loop var into `composite_key(source,N)`, and convert `test_trio_seam_only._IO_ALLOWLIST_SITES` (~L463) to
content-addressed keys. `test_no_write_side_rederivation.py` is already clean — do NOT touch it.
**Independent test**: `git grep -E '\.py", *[0-9]{3}\)' tests/architectural/` = 0; ban green on the real tree.

- [x] T024 Extend the ban guard to catch the loop-var laundering (WP06)
- [x] T025 Regression fixture attempting the laundering fails the ban (WP06)
- [x] T026 Convert `test_trio_seam_only._IO_ALLOWLIST_SITES` (~L463) to content-addressed keys (WP06)
- [x] T027 DoD: `git grep` for positional anchors = 0; ban green on the real tree (WP06)
- [x] T028 ruff/mypy clean; tracer rows (WP06)

Prompt: [tasks/WP06-positional-anchor-ban-hole.md](./tasks/WP06-positional-anchor-ban-hole.md) · ~230 lines · deps: none

### WP07 — Lane-enum golden count → exact frozenset (FR-006)

**Goal**: Replace `len(Lane) == N` with an exact `Lane` member-name frozenset and rename the test off
"…nine_values". The exemplar pattern for WP11's sweep. **Independent test**: adding/removing a lane forces
a content edit; `tests/status/test_models.py` green.

- [x] T029 Assert the exact `Lane` member-name frozenset (WP07)
- [x] T030 Rename the test off "…nine_values" (WP07)
- [x] T031 `tests/status/test_models.py` green (WP07)
- [x] T032 ruff/mypy clean; tracer row (exemplar for WP11) (WP07)

Prompt: [tasks/WP07-lane-enum-frozenset.md](./tasks/WP07-lane-enum-frozenset.md) · ~200 lines · deps: none

### WP08 — Source-as-text wiring → observable contract (+ sibling audit) (FR-007)

**Goal**: Re-point the confirmed `read_text()` twin (`:211`) to an observable contract with no `@patch` on
the SUT; audit the 3 siblings and re-point ONLY genuine twins (do not manufacture a false shared helper).
**Independent test**: no `@patch` on the SUT in any re-pointed test; assertion on a persisted artifact.

- [x] T033 Re-point the confirmed twin (`:211` `read_text`) to an observable contract (WP08)
- [x] T034 Audit `test_dashboard/test_api_handler.py`; repoint only if a genuine twin (WP08)
- [x] T035 Audit `glossary/test_event_emission.py` + `sync/tracker/test_service.py`; repoint only genuine twins (WP08)
- [x] T036 DoD: no `@patch` on the SUT; assert a persisted artifact (WP08)
- [x] T037 ruff/mypy clean; tracer parity rows (WP08)

Prompt: [tasks/WP08-source-as-text-observable.md](./tasks/WP08-source-as-text-observable.md) · ~240 lines · deps: none

### WP09 — Production-delegating mission factory (FR-008)

**Goal**: `tests/_factories.make_mission()` delegates to `create_mission_core()`; add a side-effect-free /
no-coordination entrypoint to the core if missing (behaviour-preserving). **Independent test**: output
`meta.json` byte-identical (minus overrides) to a direct core call; `_factories/__init__.py` non-empty with
≥1 real importer.

- [x] T038 Add a side-effect-free / no-coord entrypoint to `create_mission_core()` if missing (WP09)
- [x] T039 `make_mission()` delegating wrapper in `tests/_factories/__init__.py` (WP09)
- [x] T040 Factory-parity test: `meta.json` byte-identical minus overrides (WP09)
- [x] T041 DoD: `_factories/__init__.py` non-empty with ≥1 real importer (WP09)
- [x] T042 ruff/mypy clean; tracer row (WP09)

Prompt: [tasks/WP09-mission-factory-delegation.md](./tasks/WP09-mission-factory-delegation.md) · ~230 lines · deps: none

### WP10 — Verify-and-close hygiene: #2553 + #2295 (FR-009, FR-010)

**Goal**: Verify #2553 is a real fix (not a suppression) → close or minimal-fix; recount #2295 quarantine
(~1 active marker), triage it, cross-ref #2309, do NOT drive to 0. MUST NOT edit `tests/conftest.py`.
**Independent test**: DoD evidence recorded; zero production behaviour change.

- [x] T043 Verify #2553 is a real fix → close or minimal-fix (WP10)
- [x] T044 Recount #2295 quarantine (~1 marker, `test_summary_tolerance.py:704`) (WP10)
- [x] T045 Triage the residual marker; cross-ref #2309; no drive-to-0; no `conftest.py` edit (WP10)
- [x] T046 DoD evidence; confirm zero production change (WP10)
- [x] T047 tracer row (quarantine ratchet observed) (WP10)

Prompt: [tasks/WP10-verify-close-hygiene.md](./tasks/WP10-verify-close-hygiene.md) · ~220 lines · deps: none

### WP11 — Golden-count inventory + recurrence guard (FR-014)

**Goal**: AST inventory of `len(<collection>) == <int>` in `tests/` (classify keep vs convert), write the
recurrence guard `test_golden_count_ban.py` (fails on NEW un-annotated golden-count; escape hatch
`# golden-count: cardinality-is-contract`), and emit the convert-set inventory partitioned BY DIRECTORY for
the batch WPs. New-guard-file DoD applies. **Independent test**: a fresh un-annotated `len==int` fixture
fails the guard; guard green on the real tree.

- [x] T048 AST inventory of `len(...) == int` in `tests/` → classify keep vs convert (WP11)
- [x] T049 Recurrence guard `test_golden_count_ban.py` (fails NEW un-annotated; escape hatch) (WP11)
- [x] T050 Regression: a fresh un-annotated fixture fails the guard (WP11)
- [x] T051 Convert-set baseline + inventory artifact partitioned BY DIRECTORY under feature_dir (WP11)
- [x] T052 New-guard-file DoD: register in `_arch_shard_map.py` (out-of-map append) + refreeze gc3b & gc2b (WP11)
- [x] T053 DoD: guard green on the real tree; anchors WP07's exemplar pattern (WP11)
- [x] T054 ruff/mypy clean; tracer catalog rows (WP11)

Prompt: [tasks/WP11-golden-count-inventory-guard.md](./tasks/WP11-golden-count-inventory-guard.md) · ~290 lines · deps: WP07

### WP12 — Golden-count conversion batch 1: doctrine & charter (FR-014)

**Goal**: Convert the WP11-inventory `convert`-set in `tests/charter/**`, `tests/doctrine/**`,
`tests/doctrine_synthesizer/**`, `tests/glossary/**`. **Independent test**: convert-set baseline strictly
decreases; owned-dir suites + golden-count guard green.

- [x] T055 Pull WP11's inventory convert-set for the owned directories (WP12)
- [x] T056 Convert `len==N` → set/frozenset-equality per file (owned dirs only) (WP12)
- [x] T057 Decrement the convert-set baseline (strictly decreases) (WP12)
- [x] T058 Affected suites + golden-count guard green (WP12)
- [x] T059 ruff/mypy clean; tracer rows (WP12)

Prompt: [tasks/WP12-golden-count-batch-doctrine-charter.md](./tasks/WP12-golden-count-batch-doctrine-charter.md) · ~210 lines · deps: WP11

### WP13 — Golden-count conversion batch 2: lifecycle & upgrade (FR-014)

**Goal**: Convert the `convert`-set in `tests/upgrade/**`, `tests/dossier/**`, `tests/lanes/**`,
`tests/migration/**`, `tests/migrate/**`, `tests/post_merge/**`, `tests/merge/**`, `tests/coordination/**`,
`tests/review/**`. **Independent test**: convert-set baseline strictly decreases; suites + guard green.

- [x] T060 Pull WP11's inventory convert-set for the owned directories (WP13)
- [x] T061 Convert `len==N` → set/frozenset-equality per file (owned dirs only) (WP13)
- [x] T062 Decrement the convert-set baseline (strictly decreases) (WP13)
- [x] T063 Affected suites + golden-count guard green (WP13)
- [x] T064 ruff/mypy clean; tracer rows (WP13)

Prompt: [tasks/WP13-golden-count-batch-lifecycle-upgrade.md](./tasks/WP13-golden-count-batch-lifecycle-upgrade.md) · ~210 lines · deps: WP11

### WP14 — Golden-count conversion batch 3: cli/auth/tasks & long tail (FR-014)

**Goal**: Convert the `convert`-set in the remaining clean directories (audit, auth, tasks, missions,
cross_cutting, docs, cli, doctor, core, characterization, kernel, policy, delivery, research, git_ops,
event_journal, dashboard, context, ci, paths, init, e2e, cross_branch, concurrency, release, readiness,
proof, mission_metadata, calibration). **Independent test**: convert-set baseline strictly decreases;
suites + guard green.

- [x] T065 Pull WP11's inventory convert-set for the owned directories (WP14)
- [x] T066 Convert `len==N` → set/frozenset-equality per file (owned dirs only) (WP14)
- [x] T067 Decrement the convert-set baseline (strictly decreases) (WP14)
- [x] T068 Affected suites + golden-count guard green (WP14)
- [x] T069 ruff/mypy clean; tracer rows (WP14)

Prompt: [tasks/WP14-golden-count-batch-cli-auth-tail.md](./tasks/WP14-golden-count-batch-cli-auth-tail.md) · ~220 lines · deps: WP11

### WP15 — gc2b exact-selection ratchet: scope to orphans (FR-015)

**Goal**: Stop the gc2b exact-selection baseline over-firing on routine test-file add/remove (this mission
does it 4–5×). Scope the ratchet to orphans (or make it advisory) per #2616, preserving orphan detection.
Lands early so the other new-file WPs' baseline burden shrinks. **Independent test**: a routine add/remove
no longer trips red; the orphan-detection true-positive still fires.

- [x] T070 Scope the gc2b exact-selection ratchet to orphans (or advisory) per #2616 (WP15)
- [x] T071 Regression: routine add/remove no longer trips red; orphan detection preserved (WP15)
- [x] T072 Verify the load-bearing orphan-detection signal is retained (WP15)
- [x] T073 DoD; ruff/mypy clean (WP15)
- [x] T074 tracer row (gc2b ratchet) (WP15)

Prompt: [tasks/WP15-gc2b-scope-to-orphan.md](./tasks/WP15-gc2b-scope-to-orphan.md) · ~210 lines · deps: none

### WP16 — Explicit shard-registry seam (FR-011)

**Goal**: Replace the import-side-effect `SHARD_GROUPS` assembly with an idempotent
`register()`/`all_groups()` + expected-group manifest so the completeness guard fails diagnosably (never a
bare `KeyError`) and an unmarked `tests/next` universe fails loud. Owns `tests/conftest.py`. New-guard-file
DoD applies. **Independent test**: dropping the `_next_shard_map` registration emits the diagnosable
message; an unmarked `tests/next` universe fails.

- [x] T075 `_shard_registry.py`: idempotent `register()` / `all_groups()` + expected-group manifest (WP16)
- [x] T076 Refactor `_arch_shard_map.py` + `_next_shard_map.py` to register via the seam (WP16)
- [x] T077 `test_arch_shard_marker_completeness.py`: diagnosable "group not registered" (WP16)
- [x] T078 `conftest.py` shard-marker hook uses the registry; unmarked `tests/next` fails loud (WP16)
- [x] T079 Regression: drop `_next_shard_map` registration → diagnosable message; unmarked universe fails (WP16)
- [x] T080 New-guard-file DoD (self-register + refreeze baselines); ruff/mypy; tracer (WP16)

Prompt: [tasks/WP16-shard-registry-seam.md](./tasks/WP16-shard-registry-seam.md) · ~270 lines · deps: WP15

### WP17 — CI gate + coverage guards (FR-012, FR-013)

**Goal**: Two guards over `ci-quality.yml` (single-file ownership): (a) every `pytest`-invoking job is in
`quality-gate.needs` minus a reasoned `NON_BLOCKING_ALLOWLIST`; (b) the sonarcloud job discovers the
`ui-e2e.yml`-run `coverage-ui-e2e.xml` (cross-workflow, head-SHA-keyed) with a wiring guard. New-guard-file
DoD applies. **Independent test**: a fake pytest job → guard fails; the coverage path is in the discovered set.

- [x] T081 `test_suite_jobs_gate_blocking.py`: `pytest_jobs − allowlist ⊆ quality-gate.needs` (WP17)
- [x] T082 Resolve `slow-tests` / `mutation-testing` to explicit gated OR allowlisted-with-rationale (WP17)
- [x] T083 Regression: a fake pytest job → guard fails (WP17)
- [x] T084 `ci-quality.yml` sonarcloud discovers `coverage-ui-e2e.xml` cross-workflow head-SHA (WP17)
- [x] T085 `test_ui_e2e_coverage_discovered.py` wiring guard asserts the path is discovered (WP17)
- [x] T086 `quality-gate.needs` edits if a job must join; new-guard-file DoD; ruff/mypy; tracer (WP17)

Prompt: [tasks/WP17-ci-gate-coverage-guards.md](./tasks/WP17-ci-gate-coverage-guards.md) · ~280 lines · deps: WP16

### WP18 — Retire runtime_bridge src delegates (repoint-then-delete residue) (FR-003) — LANE-0 DELETION POLE

**Goal**: The deletion pole re-sequenced OUT of WP02, running AFTER the WP03/WP04 repoints. Delete the
WP02-classified pure-forwarding delegates in `runtime_bridge.py` + seam modules (canonical `__all__` kept),
refactor the 3 live production `_rb.<name>` call-sites (`_retrospective_blocks_completion`,
`_composition_dispatch_inputs`, `_has_generated_docs`) to import the seam leaf directly, and update the
FROZEN `tests/runtime/test_bridge_compat_surface.py` exact-baseline. Owns `src/runtime/next/runtime_bridge*.py`
+ that compat test. **Independent test**: dead-code gate green post-delete (each delegate proven dead) +
`tests/runtime` (incl. `test_bridge_parity.py`) green; `git grep <deleted symbol>` = 0 across `src`+`tests`.

- [x] T087 Delete the WP02-classified forwarding delegates now repointed by WP03/WP04 (grep=0 per name) (WP18)
- [x] T088 Refactor the 3 production `_rb.<name>` call-sites to import the seam leaf directly; delete their façade delegates (WP18)
- [x] T089 Update the frozen `test_bridge_compat_surface.py` exact-baseline; surviving sentinels intact (WP18)
- [x] T090 Dead-code gate + `tests/runtime` (incl. `test_bridge_parity.py`) green (WP18)
- [x] T091 ruff/mypy clean; final runtime_bridge parity/compat tracer verdict; NFR-001 recorded (WP18)

Prompt: [tasks/WP18-runtime-bridge-src-delegate-retirement.md](./tasks/WP18-runtime-bridge-src-delegate-retirement.md) · ~150 lines · deps: WP04
