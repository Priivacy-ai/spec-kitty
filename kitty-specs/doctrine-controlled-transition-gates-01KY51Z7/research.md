# Research: Doctrine-Controlled Transition Gates (half A, epic #2535)

**Phase**: 0 (research / build map) · **Base commit**: `e4ef6e850`
**Traces**: `spec.md` (FR-001..015, NFR-001..006, C-001..006), `reviews/post-spec-squad.md`
**Folds**: the 4-lens pre-spec brief (`scratchpad/half-a-research/00..04`) into the plan-time build map.

This document records the resolved design questions in **Decision / Rationale /
Alternatives-considered** form, each anchored to verified `file:line` evidence. It is the
build map: every entry names the concrete surface a later WP touches. No production code is
written here.

---

## D-01 — Binding home: the legacy `MissionStepContract` review contract, not unified `MissionStep`

**Decision.** A gate binding lives as a new **contract-level** `gates: list[GateBinding]` field on
`MissionStepContract` (`src/doctrine/missions/step_contracts.py:86`, frozen + `extra="forbid"` +
`schema_version` — an explicit versioned addition), authored in the review action's
`src/doctrine/missions/built_in_step_contracts/review.step-contract.yaml`. The binding is
**contract/action-level**, NOT per-`MissionStepContractStep` — a gate binds an *action's*
transition (`in_progress → for_review`), not an individual step. This **reconciles decision #1**
(attach gates to the review step-contract surface) **and decision #2** (reuse `mission_step_contract`,
which IS the legacy contract surface). (FR-005, FR-008, C-001, FR-006)

**Rationale (plan-time ruling, code-grounded).** The runtime-wired, activation-filtered surface is
the **legacy** `MissionStepContract`, not the unified `MissionStep`:
- The executor + activation consume `MissionStepContract`/`MissionStepContractStep` via
  `MissionStepContractRepository` (`executor.py:22-24,160,188`), resolved from `*.step-contract.yaml`.
  `review.step-contract.yaml` (`schema_version: "1.0"`, `action: review`, `mission: software-dev`)
  IS the activation-filtered `mission_step_contract` node for the review action.
- The unified `MissionStep` (`models.py:109`) is **NOT wired to any gate-time reader** —
  `MissionType.steps` has no runtime consumer (verified: no `.steps` reader in
  `missions/repository.py` or `charter/mission_type_profiles.py`). Placing `gates` there would
  require wiring the unified model into the runtime load path = out-of-scope scope creep, and would
  contradict decision #2 (reuse `mission_step_contract`, the legacy surface). This is the seam the
  post-spec catch surfaced; the ruling resolves it to the runtime-wired contract.
- Per carla's content-vs-relationship principle (C-001), a gate binding is a
  **relationship/configuration on an existing artefact** — a field, not a standalone distributable
  content artefact.

**Alternatives considered.**
- *Unified `MissionStep.gates`* (`models.py:109`). Rejected: `MissionType.steps` has no gate-time
  reader; adopting it forces wiring the unified model into the runtime = scope creep beyond half A.
- *`MissionOrchestration.guards: list[str]`* (`models.py:86`). Rejected: bare FSM check-expression
  *names* whose bodies live in `mission.yaml` (e.g. `has_spec: check: artifact_exists("spec.md")`)
  with **no DRG/activation flow** — binding here needs a second handler-resolution mechanism.
- *Per-`MissionStepContractStep.gates`* (`step_contracts.py:66`). Rejected: a gate binds an
  action's transition, not an individual step; contract/action-level is the correct grain.

---

## D-02 — Reuse `mission_step_contract` kind; no new `gate` ArtifactKind

**Decision.** Half-A gate handlers bind and resolve through the existing activatable
`mission_step_contract` kind. No new `gate` `ArtifactKind`/`NodeKind` is introduced. (FR-006,
C-001)

**Rationale.** A new activatable kind is the **#2468 promotion tax** — ~12 hardcoded
enumeration sites, all already wired for `mission_step_contract`:
`artifact_kinds.py` enum + `_PLURALS` + `_PATTERNS` + `CHARTER_KIND_TOKENS`;
`drg/models.py` `NodeKind`; `drg/query.py` `resolve_transitive_refs` buckets;
`executor.py:31` `_ARTIFACT_TO_NODE_KIND`; `charter/kind_vocabulary.py`;
`charter/pack_context.py` `_BUILTIN_ARTIFACT_KINDS`; `charter/activations.py`;
`charter/activation_engine.py`; `doctrine/service.py`; a new `src/doctrine/gates/` package;
a new `gate.schema.yaml`; DRG loader globs. Routing through `mission_step_contract` touches
**zero** new enumeration sites (`executor.py:31-42` already maps it to `NodeKind`).
Content-vs-relationship (C-001) is the durable rationale, not merely the cost.

**Does it foreclose Mission D / #2599?** No (curator-carla, decisive). #2599's axis is making
the **ASSET** kind executable+activatable — orthogonal to whether "gate" is its own kind.
FR-005's inert `handler_kind` discriminator (see D-10) is the forward-compatible seam so half B
adds an executable-asset handler *without* a breaking `schema_version` bump.

**Alternatives considered.** *Promote a first-class `gate` kind* (the glossary-pack precedent).
Rejected here because a glossary pack is distributable *content* with its own files/repo/
provenance; a gate binding is a *field* on a step. The two precedents are reconciled by the
content-vs-relationship principle, to be recorded in a short ADR at plan time (paralleling
`docs/adr/3.x/2026-07-21-1-glossary-first-order-doctrine-artefact.md`).

---

## D-03 — ScopeSource port narrowed to `test_command / file_to_scope / parse_results`

**Decision.** The port is a `typing.Protocol` (mirror `doctrine/sources/protocol.py`) exposing
exactly the three repo-shape-varying concerns: `test_command()`, `file_to_scope(path)`,
`parse_results(output)`. "Which files changed" is **not** a port method — it is the shared
canonical merge-base+diff input, passed in. (FR-001)

**Rationale.** The post-spec squad (F1/A7) found #2330 was *relocated, not closed* by the
first port sketch: the port dropped `parse_results()`, so a shared runner injecting
`--junitxml`/`-q` and JUnit-only parsing (`pre_review_gate.py:656`; `_parse_junit_xml` home
`baseline.py:151`, call-site `pre_review_gate.py:716`) left a non-pytest gate **decorative** — a
failing Go/npm suite would collapse to
`NO_COVERAGE` instead of a blocking `NEW_FAILURES`. Restoring `parse_results()` on the port
lets the portable impl turn declared-command output into a real verdict. Keeping
`changed_files` off the port prevents the two impls diverging on the changed-file SSOT
(mission `merge-base-diff-ssot-01KX44SD`, sourced by
`tasks_move_task.py:_mt_pre_review_changed_files` L927 → `core.vcs.git.merge_base_changed_files`).

**Alternatives considered.** *Four-method port incl. `changed_files()`.* Rejected: it duplicates
the diff SSOT per impl. *No `parse_results` (runner owns parsing).* Rejected — the F1 finding:
that is exactly what makes the portable path decorative.

---

## D-04 — DRG carries no binding payload → a named URN→binding loader + join is mandatory

**Decision.** The hook resolves active bindings in three named steps (FR-007): (1) compute the
activated URN set via `filter_graph_by_activation` (`charter/drg.py:433`); (2) load the review
contract's `gates` from a **named loader** — `load_gate_bindings(repo_root, mission, action)`
delegating to `MissionStepContractRepository.get_by_action(mission, action)` (`step_contracts.py:160`)
→ the review contract's `gates` field (the DRG does not carry them). The `mission` param is required
(`get_by_action` keys on `(mission, action)`; only `software-dev` ships a `review` contract),
resolved from `st.mission_slug` → `meta.json`. A resolved `(mission, review)` with no contract or no
`for_review` binding → a **distinguishable `NO_COVERAGE` warn** (worded apart from "handler not
activated"), never a silent vanish; (3) retain only bindings whose `handler` resolves to an
activated `mission_step_contract` URN.

**Rationale.** `DRGNode` carries only `urn/kind/label/provenance/tags`
(`drg/models.py:292-311`) — **no binding payload** (squad A1, BLOCKER, verified). "Resolve
bindings via activation" without a loader would assume the graph carries data it structurally
does not. The loader reads the binding *content* from the `MissionStepContract` model (via the
repository already used by the executor); the DRG supplies only the *activation verdict* on the
review contract's own URN and the handler URN. NFR-005 bounds this to one graph load + one
contract-bindings load per transition — bindings are then set-membership-checked, no per-node
re-resolution.

**Alternatives considered.** *Store bindings as DRG node fields.* Rejected: would require
extending `DRGNode` and the extractor's serializer (which explicitly writes field-by-field,
`drg/models.py:298-304`). *Skip activation, run every declared binding.* Rejected: breaks the
doctrine-toggle contract (US3) — activation must be the sole selector.

---

## D-05 — Lane-FSM vs action-FSM mismatch → explicit lane→owning-step mapping

**Decision.** The WP-lane hook deterministically maps the target **lane edge** to its owning
mission **action → step-contract**: `in_progress → for_review` → the **review** action's
`review.step-contract.yaml` `gates`. A defined precedence/conflict rule (all activated matching
bindings fire, stable dispatch order) governs multiple bindings on one `on_transition` edge.
(FR-008)

**Rationale.** Two FSMs (squad A2, BLOCKER): a step-contract is identified by
`(mission, action)` in the mission-**action** FSM, but the pre-review gate fires on a
WP-**lane** edge (`in_progress → for_review`) with no action context. The binding lives on the
review contract (D-01) but is triggered by a lane transition, so the two must be joined by an
explicit table.
The lane FSM is already centralized (`status/wp_state.py`, State-Pattern DM-01KTH03G) and
`coordination/status_transition.py::_prepare_event` (L436-530) already special-cases the
`in_progress → for_review` edge — the mapping generalizes an existing shape, not a net-new
interception.

**Alternatives considered.** *Bind directly on the lane transition (a `Lane`→handler map in
code).* Rejected: reintroduces the hardcoding this mission removes. *Infer the step from the
lane heuristically.* Rejected: FR-008 demands a *deterministic* table, not inference.

---

## D-06 — Six outcomes, two hard-stops (the corrected reality)

**Decision.** `GateOutcome` has **six** members (`pre_review_gate.py:742-750`): `NO_COVERAGE`,
`NO_NEW_FAILURES`, `NEW_FAILURES`, `UNVERIFIED_BASELINE`, `TIMED_OUT`, `CANCELLED`. There are
**two** legitimate non-completions: (1) the opt-in `NEW_FAILURES` block; (2) the incumbent
terminal interruption `TIMED_OUT`/`CANCELLED`. All parity work covers all six + both hard-stops.
(FR-013, NFR-001, C-003)

**Rationale.** The squad (A3, CONTRADICTION, verified) found the spec's earlier "sole hard-stop"
framing false: `TIMED_OUT`/`CANCELLED` also `Exit(1)` and set `transition_applied=False`
(`tasks_move_task.py:1270-1296`), distinct from the block at `:1298-1300`. The terminal
interruption is checked **before** the block (`:1285` before `:1298`) — a precedence that
parity must preserve.

**Alternatives considered.** *Treat interruption as a warn (fold into fail-open).* Rejected:
that changes incumbent behaviour (US2 regression) and C-003 forbids collapsing the second
hard-stop.

---

## D-07 — Retire the dual selector `_is_spec_kitty_source_repo`

**Decision.** Activation becomes the **sole** selector of the internal handler. The hardcoded
`import_module("tests.architectural._gate_coverage")` (`pre_review_gate.py:185`) is removed from
the always-on path; the internal `GateCoverageScopeSource` and that import are reachable **only**
when the Spec-Kitty handler is the activated handler. `_is_spec_kitty_source_repo`
(`pre_review_gate.py:153`) is retired from impl selection — demoted to a private internal of
`GateCoverageScopeSource`, forbidden from gating which impl runs. (FR-009)

**Rationale.** Squad F2/A8 (verified `:153,183`): the probe competes with activation — a
consumer that *erroneously activates* the spec-kitty handler could still reach the import. Making
activation the only selector closes the pre-review facet of #2534 **by construction even under
misconfiguration** (US1 AS4, SC-001): when the spec-kitty handler is not activated, the import is
structurally unreachable; when it *is* (erroneously) activated but the module is absent, the
handler's own `GateAuthoritiesUnavailable` (`pre_review_gate.py:120-145`) degrades to a
`NO_COVERAGE` warn without the internal-module import ever succeeding.

**Alternatives considered.** *Keep the probe as a secondary guard.* Rejected: two selectors =
the exact dual-authority bug F2 flagged.

---

## D-08 — Single test-command authority (three surfaces reconciled today)

**Decision.** `ScopeSource` becomes the sole authority for "what command proves the change,"
consumed by **both** baseline capture and the head run. The third override key
`review.pre_review_test_command` is re-pointed at the port or deprecated. (FR-011)

**Rationale.** The command is resolved in three uncoordinated places today (squad F3/A6,
verified):
1. `review/baseline.py::_get_test_command` (L124) — reads `review.test_command` +
   `review.test_output_format`; used **only** by baseline capture.
2. `review/_interpreter.py::resolve_pytest_command` (L32) — **hardcoded pytest**; used by the
   head run, ignoring `review.test_command`.
3. `tasks_move_task.py` `review.pre_review_test_command` (`_PRE_REVIEW_CONFIG_KEY_TEST_COMMAND`
   L785) — override-scope precedence (frontmatter > this key > auto-scope, L883).

The sharpest latent bug (lens 3, item 6): baseline honours `review.test_command`; the head run
silently overrides it with pytest. A single `ScopeSource.test_command()` authority unifies
baseline↔head so a consumer's declared command is honoured on both sides.

**Alternatives considered.** *Leave three surfaces, document precedence.* Rejected: FR-011
requires reconciliation, and the baseline↔head split is a correctness bug, not just ergonomics.

---

## D-09 — #2843 is a pattern to MIRROR, not a seam to RIDE

**Decision.** The inverted hook **copies** the executor's resolve→filter→execute shape
(`executor.py:179-185`, `_resolve_pack_context` L259-282) but builds its own lane-edge dispatch;
it does not call `StepContractExecutor.execute()`. (Assumptions §; FR-007)

**Rationale.** Squad + lens 4 (decisive over lens 2): #2843 (mission
`drg-relation-parity-activation-gate-01KY48PD`) was a **correctness** fix to
`filter_graph_by_activation`'s per-ID stem→URN gate (`_resolve_activated_urns_by_kind`,
`drg.py:339`) — it inverted no gate and touched neither `tasks_move_task.py` nor
`pre_review_gate.py`. The executor resolves *mission-action step delegations*
(`_resolve_step_delegations` L284), not *lane-transition gates* — a different call path. #2843
**de-risks** the primitive (per-ID activation now works, so an activation-driven gate won't
silently drop its own handler node) and leaves a copyable `_resolve_pack_context` pattern
(fail-**closed** on `OrgPackEnvVarUnsetError`/`OrgPackSubdirEscapeError`, else `None`,
L275-282); it does **not** shrink the inversion.

**Alternatives considered.** *Ride `StepContractExecutor.execute()` directly.* Rejected: wrong
call path (action-step delegation, not lane-edge gate) and it dispatches invocations, not gate
verdicts.

---

## D-10 — `handler_kind` future-proofing (mirror the glossary-pack inert-field play)

**Decision.** `GateBinding` carries an inert-in-half-A `handler_kind` discriminator (default
`mission_step_contract`; accepts `asset` and round-trips it byte-stable without executing it)
plus an optional `provenance`. (FR-005, NFR-004, C-002)

**Rationale.** Schema-migration debt (curator-F1, verified `executor.py:31-42`): binding a
`handler` to the `mission_step_contract` URN space would force #2599 (a half-B asset handler, a
different kind) to bump `schema_version` on a frozen `extra="forbid"` model. The sibling
glossary-pack mission deliberately shipped inert fields to avoid exactly this. `handler_kind`
lets half B name an executable-asset handler with **no breaking schema change**; in half A the
field is validated, round-tripped, and never dispatched (no attempt to execute an asset).

**Alternatives considered.** *Add `handler_kind` only in half B.* Rejected: that is the breaking
`schema_version` bump on a frozen model the finding warns against.

---

## D-11 — Fail-open per handler; no-config is a visible `NO_COVERAGE`

**Decision.** Every handler **execution** error degrades to exactly one visible "unverified"
`NO_COVERAGE` warn; a repo declaring no test command yields a visible `NO_COVERAGE` warn (never
silent green, never crash). Aggregation is deterministic: block iff `block_enabled AND any
NEW_FAILURES AND not force`; ≤1 warning per handler; no cross-suppression. (FR-012, FR-013,
FR-014, NFR-002)

**Rationale.** The incumbent already wraps three catches
(`GateAuthoritiesUnavailable` `tasks_move_task.py:1241`-area, `KeyboardInterrupt` `:1241`,
`Exception` `:1248`) all degrading to `_mt_empty_scope_verdict` (`NO_COVERAGE`). Extending to a
registry of N handlers must preserve this per handler (squad A4): "exactly one warning" is a
per-handler property, and one faulting handler must never suppress another's verdict. The engine
invariant "empty is never clean" (`evaluate_with_scope` L797-798; `ScopeResult.is_empty` →
`NO_COVERAGE`) already forbids a silent green on empty scope.

**Alternatives considered.** *Fail-closed on handler error.* Rejected: introduces a new
transition-blocking bug class (C-003 caps hard-stops at two). *Silent no-op when no command.*
Rejected: "empty is never clean" — the warn must be visible.

---

## Build-map file index (all under repo root)

| Surface | Anchor | Role in half A |
|---|---|---|
| Pre-review engine | `pre_review_gate.py`: `GateOutcome` L742, `evaluate_pre_review_gate` L853, `evaluate_with_scope` L765, `run_scoped_tests_at_head` L623, `GateAuthoritiesUnavailable` L120 | Becomes first named handler; scope moves behind port |
| Internal import (delete from always-on path) | `pre_review_gate.py:167,185` `_load_gate_coverage_module` / `import_module` | Reachable only inside `GateCoverageScopeSource` |
| Dual selector (retire) | `pre_review_gate.py:153` `_is_spec_kitty_source_repo` | Demoted to internal of `GateCoverageScopeSource` |
| Baseline command | `review/baseline.py:124` `_get_test_command` | Re-pointed at `ScopeSource.test_command()` |
| Head-run command | `review/_interpreter.py:32` `resolve_pytest_command` | Internal-impl detail only |
| Third override key | `tasks_move_task.py:785` `_PRE_REVIEW_CONFIG_KEY_TEST_COMMAND` | Reconciled/deprecated |
| Hook to invert | `tasks_move_task.py:1160` `_mt_run_pre_review_gate` → `_mt_run_transition_gates`; hard-stops L1270-1300 | Activation-driven dispatch + aggregation |
| Changed-files SSOT | `tasks_move_task.py:927` `_mt_pre_review_changed_files` → `core.vcs.git.merge_base_changed_files` | Shared input, off the port |
| Binding home | `doctrine/missions/step_contracts.py:86` `MissionStepContract` (`.gates` new field); authored in `built_in_step_contracts/review.step-contract.yaml` | Versioned schema add (contract-level) |
| Binding loader | `step_contracts.py:160` `MissionStepContractRepository.get_by_action(mission, action)` → new `load_gate_bindings(repo_root, mission, action)` | Reads review contract `.gates`; mission from `meta.json` |
| Kind map | `mission_step_contracts/executor.py:31` `_ARTIFACT_TO_NODE_KIND` | Reused; no new entry |
| Executor consumes legacy contract | `executor.py:22-24,160,188` (`MissionStepContract`/`MissionStepContractStep`/repository) | Confirms runtime-wired surface |
| Resolve→filter pattern | `executor.py:179-185`, `_resolve_pack_context` L259-282, `_candidate_urn` L315 | Pattern to mirror |
| DRG node (no payload) | `drg/models.py:292-311` `DRGNode` | Proves the loader is mandatory |
| Activation filter | `charter/drg.py:433` `filter_graph_by_activation`, `_resolve_activated_urns_by_kind` L339 | Activated-URN-set source |
| Pack context | `charter/pack_context.py:184` `PackContext.from_config` | Fail-closed on env/escape |
| Port pattern | `doctrine/sources/protocol.py:53` `OrgDoctrineSource` | `typing.Protocol` shape to mirror |
| Registry pattern | `mission_v1/guards.py:270` `GUARD_REGISTRY` | `GATE_REGISTRY` template |

---

## Non-negotiable regression guards (carry into every WP; C-005)

- **Non-vacuous resolution** (NFR-003): positive arm (binding resolves to an activated node) +
  negative-control arm (a non-activated binding does **not** resolve); a test that would pass
  against an empty graph is rejected.
- **Per-handler fail-open** (NFR-002): fault-inject one handler → 0 crashes, 0 blocks by the
  faulting handler, exactly one visible warn, co-firing verdicts unaffected.
- **#2534 pre-review-facet closure** (SC-001): simulated consumer (no
  `tests/architectural/_gate_coverage.py`) transitions to `for_review` without ever importing
  `_gate_coverage` — **including** the erroneous-activation case.
- **#2330 pre-review-facet closure** (SC-001, NFR-004): non-`src/specify_cli`, non-pytest layout
  gated by its declared command; a failing suite yields blocking-capable `NEW_FAILURES`, not
  `NO_COVERAGE`.
- **Parity through the hook** (NFR-001, SC-002): golden `(outcome, scope, transition metadata,
  block/exit, console)` through `_mt_run_transition_gates` across all six outcomes + both
  hard-stops.
- **Round-trip fidelity** (NFR-004): `handler_kind: asset` / `provenance` load→serialize
  byte-stable and inert in half A.
- **Quality** (NFR-006): `mypy --strict` + `ruff` clean, cyclomatic complexity ≤ 15/function,
  ≥ 90% new-code line coverage. Tests: `PYTHONPATH=$(pwd)/src`.
