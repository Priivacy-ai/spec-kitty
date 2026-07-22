# Tasks: Doctrine-Controlled Transition Gates

**Mission**: `doctrine-controlled-transition-gates-01KY51Z7` · **Branch**: `feat/doctrine-controlled-transition-gates`
**Plan**: [plan.md](./plan.md) · **Spec**: [spec.md](./spec.md) · **Design**: [data-model.md](./data-model.md), [contracts/](./contracts/) · **Squads**: [post-spec](./reviews/post-spec-squad.md), [post-plan](./reviews/post-plan-squad.md)

9 work packages from IC-01..06. **Ownership is partitioned by file** (the strangler edits `pre_review_gate.py` / `tasks_move_task.py` in phases; each hot file is owned by exactly one WP, sequenced by dependency — no two WPs share `owned_files`). Every WP is **ATDD red-first**, complexity ≤15, mypy strict + ruff clean, ≥90% new-code coverage.

**Recommended build sequence**: WP01 ∥ WP02 (keystone) → WP03 → WP04 → WP05 → {WP06, WP07, WP08} → WP09 (integrative, last).

**Non-negotiable guards** (see reviews/*): parity-through-hook captured from base `e4ef6e850` (never regenerated); per-handler fail-open (each fault → one warning, no cross-suppression); non-vacuous resolution with a **non-`software-dev` negative control**; portable-verdict **baseline-relative** fidelity (2 fixtures); #2534/#2330 pre-review-facet closure incl. **erroneous-activation**. Tracker: IC-02=#2595, IC-03=#2596, IC-05=#2598; #2741 is **inherited not fixed**.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Author the content-vs-relationship ADR (`2026-07-22-1`) | WP01 | |
| T002 | Reciprocal cross-link from the glossary-first-order ADR | WP01 | [P] |
| T003 | Markdownlint + ADR-index update | WP01 | |
| T004 | Define `ScopeSource` Protocol (test_command/file_to_scope/parse_results) | WP02 | |
| T005 | `GateCoverageScopeSource` (encapsulate pytest/JUnit/`_gate_coverage` import/probe) | WP02 | |
| T006 | `DeclaredCommandScopeSource` (portable, baseline-relative parse_results) | WP02 | |
| T007 | Move `resolve_pytest_command` into `_interpreter`; migrate interpreter test | WP02 | |
| T008 | `test_scope_source.py` (port contract, both impls, no-config→NO_COVERAGE) | WP02 | |
| T009 | Portable-verdict fidelity fixtures (newly-failing / pre-existing) | WP02 | |
| T010 | Behaviour-parity micro-golden for `GateCoverageScopeSource` scope derivation | WP02 | |
| T011 | Refactor `pre_review_gate.py` to consume a `ScopeSource` (baseline+head); drop always-on import | WP03 | |
| T012 | `baseline.py` single test-command authority via the port | WP03 | |
| T013 | Injected-ScopeSource seam (activation-driven selection groundwork) | WP03 | |
| T014 | Migrate `test_pre_review_gate_engine.py` + `..._integration.py` | WP03 | |
| T015 | #2330 pre-review-facet closure test (non-pytest layout) | WP03 | |
| T016 | `gate_registry.py` named-handler registry (mirror `GUARD_REGISTRY`) | WP04 | |
| T017 | Register `evaluate_pre_review_gate` as first handler on `for_review` | WP04 | |
| T018 | `GateHandler` contract (name, edge, callable→verdict) | WP04 | |
| T019 | `test_gate_registry.py` (registration, single-handler dispatch parity) | WP04 | |
| T020 | Add contract-level `gates: list[GateBinding]` to `MissionStepContract` | WP05 | |
| T021 | `GateBinding` model (on_transition/handler/handler_kind/schema_version/fail_open/provenance) | WP05 | |
| T022 | `save()` `exclude_defaults` (no `gates: []` into clean contracts) | WP05 | |
| T023 | Author the `for_review` binding in `review.step-contract.yaml` | WP05 | |
| T024 | `test_gate_binding_schema.py` (validation, inert asset round-trip, save byte-stability) | WP05 | |
| T025 | Back-compat: existing contracts still load; no C-009 allowlist covers review | WP05 | |
| T026 | `load_gate_bindings(repo_root, mission, action)` via repository | WP06 | |
| T027 | Mission-type resolution (`meta.json`) + lane→(mission,action)→contract map | WP06 | |
| T028 | `resolve_active_gate_bindings` pure fn (activated-URN ⋈ bindings) | WP06 | |
| T029 | No-contract path → NO_COVERAGE warn distinguishable from "not activated" | WP06 | |
| T030 | Bounded loads (NFR-005): one graph + one binding load per transition | WP06 | |
| T031 | `test_gate_bindings.py` (non-vacuous + **non-software-dev negative control**) | WP06 | |
| T032 | Register 3 gate terms in the glossary pack (guard 5 real senses) | WP07 | [P] |
| T033 | Author the 3 terms in `docs/context/orchestration.md` | WP07 | [P] |
| T034 | Terminology-guard regression; do NOT touch legacy seed | WP07 | |
| T035 | `verdict_aggregation.py` `aggregate_verdicts()` pure fn (precedence) | WP08 | |
| T036 | `test_verdict_aggregation.py` full outcome×precedence matrix | WP08 | |
| T037 | Capture parity golden from base `e4ef6e850` (script + fixtures, red-first) | WP08 | |
| T038 | `test_transition_gate_parity.py` harness vs base-captured fixtures | WP08 | |
| T039 | Fail-open fault-injection unit (one warning/handler, no cross-suppression) | WP08 | |
| T040 | Invert `_mt_run_pre_review_gate`→`_mt_run_transition_gates`; keep **thin alias** | WP09 | |
| T041 | Per-handler fail-open + two enumerated hard-stops | WP09 | |
| T042 | Delete `is_consumer_repo` machinery (`_PRE_REVIEW_CONSUMER_REPO_REASON` + branch) | WP09 | |
| T043 | Alias `review.pre_review_test_command` + one-time deprecation warning | WP09 | |
| T044 | Update compat surface: `tasks.py` barrel + `test_tasks_compat_surface.py` tuple | WP09 | |
| T045 | Migrate hook-binding tests (escape_hatch/observability/cli_contract_coord) | WP09 | |
| T046 | #2534 closure incl. **erroneous-activation**; parity-through-hook green | WP09 | |
| T047 | Update `docs/development/review-gates.md`; note #2741 inherited | WP09 | |

## Work Packages

### WP01 — Content-vs-relationship ADR (IC-01)

- **Goal**: Record the durable principle (promote a new *content* artefact with its own files/provenance; reuse/attach a *relationship/configuration* on an existing artefact) justifying reuse of `mission_step_contract` over a new `gate` kind — before the schema work depends on it.
- **Priority**: P1 (unblocks the reuse decision; #2468 decision-record obligation). **Deps**: none.
- **Independent test**: markdownlint passes; the ADR reconciles the glossary-*promoted* vs gate-*reused* precedents and is cross-linked both ways.
- **Requirements**: FR-006 (justifies), C-001.
- **Guards**: N/A (docs). Pin slug `2026-07-22-1`; do not use a wildcard.
- [ ] T001 Author the ADR (WP01)
- [ ] T002 Reciprocal cross-link from `2026-07-21-1-glossary-first-order-doctrine-artefact.md` (WP01)
- [ ] T003 Markdownlint + ADR-index/registry update (WP01)

### WP02 — ScopeSource port + both implementations (IC-02, KEYSTONE) *(~450 lines)*

- **Goal**: Extract the repo-shape-varying scope concerns behind a `typing.Protocol` port; land `GateCoverageScopeSource` (encapsulating today's pytest/JUnit/`_gate_coverage`-import/probe, behaviour-preserving) and `DeclaredCommandScopeSource` (portable, baseline-relative verdict).
- **Priority**: P1 keystone/MVP. **Deps**: none (∥ WP01).
- **Independent test**: port + both impls unit-tested; no-config→`NO_COVERAGE`; portable path blocks on a **newly**-failing command and does NOT block a pre-existing baseline failure.
- **Requirements**: FR-001, FR-002, FR-003, NFR-004 (portable fidelity).
- **Guards**: portable-verdict baseline-relative (2 fixtures); micro-parity for internal scope derivation. `changed_files` stays SSOT off the port.
- [ ] T004 Define `ScopeSource` Protocol (WP02)
- [ ] T005 `GateCoverageScopeSource` behaviour-preserving (WP02)
- [ ] T006 `DeclaredCommandScopeSource` portable + baseline-relative (WP02)
- [ ] T007 Move `resolve_pytest_command` into `_interpreter`; migrate interpreter test (WP02)
- [ ] T008 `test_scope_source.py` (WP02)
- [ ] T009 Portable-verdict fidelity fixtures (WP02)
- [ ] T010 Behaviour-parity micro-golden for scope derivation (WP02)

### WP03 — Pre-review engine consumes the port (IC-02) *(~320 lines)*

- **Goal**: Refactor `pre_review_gate.py` into a thin engine consuming an injected `ScopeSource` for baseline AND head; remove the always-on `_gate_coverage` import (now inside the port); make `baseline.py` use the single command authority.
- **Priority**: P1. **Deps**: WP02.
- **Independent test**: engine parity on the spec-kitty tree via `GateCoverageScopeSource`; a non-pytest layout gated via `DeclaredCommandScopeSource`.
- **Requirements**: FR-010, FR-011, FR-012.
- **Guards**: #2330 pre-review-facet closure; migrate (not silence) `test_pre_review_gate_engine.py`/`..._integration.py`.
- [ ] T011 Refactor `pre_review_gate.py` to consume a `ScopeSource` (WP03)
- [ ] T012 `baseline.py` single test-command authority (WP03)
- [ ] T013 Injected-ScopeSource seam (WP03)
- [ ] T014 Migrate engine + integration tests (WP03)
- [ ] T015 #2330 pre-review-facet closure test (WP03)

### WP04 — Named gate-handler registry (IC-03) *(~250 lines)*

- **Goal**: A `GATE_REGISTRY` of named handlers (mirror `mission_v1/guards.py::GUARD_REGISTRY`); register `evaluate_pre_review_gate` as the first handler keyed to `for_review` — **no behaviour change** (one entry, dispatched where the hardcoded call was).
- **Priority**: P2. **Deps**: WP03.
- **Independent test**: registry registration/lookup + single-handler dispatch reproduces the current verdict.
- **Requirements**: FR-004.
- **Guards**: keep aggregation OUT (that's WP08); one handler only.
- [ ] T016 `gate_registry.py` (WP04)
- [ ] T017 Register `evaluate_pre_review_gate` on `for_review` (WP04)
- [ ] T018 `GateHandler` contract (WP04)
- [ ] T019 `test_gate_registry.py` (WP04)

### WP05 — Gate-binding schema on the review contract (IC-04) *(~380 lines)*

- **Goal**: Add contract-level `gates: list[GateBinding]` to `MissionStepContract` (`extra="forbid"`, versioned) with the inert `handler_kind` discriminator; author the `for_review` binding in `review.step-contract.yaml`; ensure `save()` does not reintroduce `gates: []` into clean contracts.
- **Priority**: P2. **Deps**: WP04 (binding references a registry handler name).
- **Independent test**: schema validates + rejects unknown keys; `handler_kind: asset` round-trips inert; re-save is byte-stable; existing contracts still load.
- **Requirements**: FR-005, FR-006.
- **Guards**: back-compat (absent `gates` loads clean); no schema.yaml/doctor update (pydantic self-validates); confirm no C-009 allowlist covers review.
- [ ] T020 Add `gates` field to `MissionStepContract` (WP05)
- [ ] T021 `GateBinding` model (WP05)
- [ ] T022 `save()` `exclude_defaults` (WP05)
- [ ] T023 Author the `for_review` binding (WP05)
- [ ] T024 `test_gate_binding_schema.py` (WP05)
- [ ] T025 Back-compat + allowlist check (WP05)

### WP06 — Binding loader, resolution join, mission-type ownership (IC-04) *(~420 lines)*

- **Goal**: `load_gate_bindings(repo_root, mission, action)` (mission mandatory) + `resolve_active_gate_bindings` pure fn (activated-URN set ⋈ contract bindings) + the lane→(mission,action)→contract mapping; the no-contract path is a visible `NO_COVERAGE` warn **distinguishable** from "handler not activated".
- **Priority**: P2. **Deps**: WP05.
- **Independent test**: non-vacuous resolution (positive + negative control) **including a non-`software-dev` mission** with no review contract; mission-type resolved from `meta.json`; bounded loads.
- **Requirements**: FR-007, FR-008, NFR-003, NFR-005.
- **Guards**: mission-type-blind loader is a blocker — the negative-control test on research/documentation is mandatory; DRG carries no binding payload (load separately).
- [ ] T026 `load_gate_bindings(repo_root, mission, action)` (WP06)
- [ ] T027 Mission-type resolution + lane→(mission,action)→contract map (WP06)
- [ ] T028 `resolve_active_gate_bindings` pure fn (WP06)
- [ ] T029 No-contract → distinguishable NO_COVERAGE warn (WP06)
- [ ] T030 Bounded loads (WP06)
- [ ] T031 `test_gate_bindings.py` incl. non-software-dev negative control (WP06)

### WP07 — Gate terminology registration (IC-06) *(~220 lines)*

- **Goal**: Register `transition gate`, `gate handler`, `gate binding` in BOTH the glossary pack AND `docs/context/orchestration.md`, guarding against the **five real** existing senses; do not add a third divergent copy to the legacy seed.
- **Priority**: P3. **Deps**: WP05 (terms after the schema fixes their meaning).
- **Independent test**: terms resolve in both surfaces; terminology-guard suite green; no `semantic gate` phantom.
- **Requirements**: FR-015.
- **Guards**: 5 senses only (branch strategy / diff compliance / dependency / merge dependency / sonar quality).
- [ ] T032 Register in the glossary pack (WP07)
- [ ] T033 Author in `docs/context/orchestration.md` (WP07)
- [ ] T034 Terminology-guard regression; no legacy-seed edit (WP07)

### WP08 — Verdict aggregation + parity oracle (IC-05) *(~360 lines)*

- **Goal**: `aggregate_verdicts()` as a **pure function** (precedence: terminal > block > warn/pass; block iff `block_enabled AND any NEW_FAILURES AND not force`; ≤1 warning/handler; no cross-suppression) with a full-matrix unit test; and the parity oracle **captured from base commit `e4ef6e850`** against the incumbent hook.
- **Priority**: P2. **Deps**: WP04.
- **Independent test**: aggregation matrix incl. the synthetic multi-handler seam; parity fixtures generated against the OLD `_mt_run_pre_review_gate` (red-first), all 6 outcomes + both hard-stops.
- **Requirements**: FR-014, NFR-001, NFR-002.
- **Guards**: circular-oracle trap — expected values MUST come from base, never regenerated; FR-014 aggregation is a synthetic-exercised seam (one production binding in half A).
- [ ] T035 `verdict_aggregation.py` `aggregate_verdicts()` pure fn (WP08)
- [ ] T036 `test_verdict_aggregation.py` full matrix (WP08)
- [ ] T037 Capture parity golden from base `e4ef6e850` (WP08)
- [ ] T038 `test_transition_gate_parity.py` harness (WP08)
- [ ] T039 Fail-open fault-injection unit (WP08)

### WP09 — Invert the hook (IC-05, integrative, LANDS LAST) *(~520 lines)*

- **Goal**: Invert `_mt_run_pre_review_gate` → `_mt_run_transition_gates` (resolve active bindings via WP06 join + WP04 registry, dispatch, aggregate via WP08), keeping `_mt_run_pre_review_gate` as a **thin alias**; delete the `is_consumer_repo` machinery; alias the third config key with a deprecation warning; update the compat surface + docs.
- **Priority**: P1 (delivers #2534 closure). **Deps**: WP06, WP08.
- **Independent test**: parity-through-hook green vs base fixtures; #2534 closure incl. erroneous-activation; compat-surface guard green after tuple+barrel update.
- **Requirements**: FR-009, FR-013 (+ FR-011 config-key, FR-014 consumption).
- **Guards**: thin alias preserves the frozen compat surface; two hard-stops only; per-handler fail-open; #2534 erroneous-activation closure; #2741 inherited-not-fixed (state in docs).
- [ ] T040 Invert the hook; keep thin alias (WP09)
- [ ] T041 Per-handler fail-open + two hard-stops (WP09)
- [ ] T042 Delete `is_consumer_repo` machinery (WP09)
- [ ] T043 Alias config key + deprecation warning (WP09)
- [ ] T044 Update compat surface (barrel + tuple) (WP09)
- [ ] T045 Migrate hook-binding tests (WP09)
- [ ] T046 #2534 closure incl. erroneous-activation (WP09)
- [ ] T047 Update `docs/development/review-gates.md`; note #2741 inherited (WP09)

## Dependencies

```
WP01 (none)   WP02 (none, keystone)
                 └─ WP03 ─ WP04 ─┬─ WP05 ─┬─ WP06 ─┐
                                 │        └─ WP07   ├─ WP09
                                 └─ WP08 ───────────┘
```
- WP01: [] · WP02: [] · WP03: [WP02] · WP04: [WP03] · WP05: [WP04] · WP06: [WP05] · WP07: [WP05] · WP08: [WP04] · WP09: [WP06, WP08]
- **Parallel lanes**: WP01 ∥ WP02 at start; after WP04, {WP05→WP06, WP05→WP07, WP08} run in parallel; WP09 joins.

## MVP

**WP02 (ScopeSource port)** is the keystone/MVP — behaviour-preserving on its own, front-loads the primary risk, and unblocks the strangler.
