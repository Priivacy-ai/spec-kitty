# Post-Spec Adversarial Squad — Findings & Resolutions

**Date**: 2026-07-22 · **Phase**: post-spec, pre-plan · **Squad**: 3 Opus specialists (read-only)
**Lenses**: architect-alphonso (architecture) · paula-patterns (coupling/boundary) · curator-carla (roadmap/doctrine)
**Verdict pre-amendment**: NOT ready for plan (2 architectural blockers + overclaim). **Post-amendment**: resolved into FR/NFR/C; ready for plan.

All load-bearing code claims were verified against source before amending (verify-before-you-fix).

## Highest-stakes question — RESOLVED

**"Reuse `mission_step_contract`, no new `gate` kind — does it foreclose Mission D/#2599?"** → **No** (curator-carla, decisive). #2599's acceptance is entirely about making the **ASSET** kind executable+activatable — orthogonal to whether "gate" is its own kind. Kept C-001 (reuse). BUT the binding *schema* needed future-proofing (carla-F1) so half B doesn't force a breaking `schema_version` bump on a frozen model.

## Findings → resolutions

| # | Lens | Finding (verified) | Resolution in spec |
|---|------|--------------------|--------------------|
| A1 | alphonso | **BLOCKER.** `DRGNode` carries only `urn/kind/label/provenance/tags` — no binding payload (verified `drg/models.py:292-311`). "Resolve bindings via activation" had an unnamed URN→binding join + loader. | **FR-007** names the 3-step join (activated URN set → load mission-type bindings via named loader → retain handler-resolved) + **NFR-005** bounds both loads. |
| A2 | alphonso | **BLOCKER.** `MissionStep` is `(mission_type_id, step_id)` in the mission-action FSM; the pre-review gate fires on a WP-lane edge with no step context. Which step owns `→for_review` was undefined. | **FR-008** requires deterministic lane→owning-step mapping (`for_review`→review step) + precedence rule. Decision #1 (attach to step-contract surface) **stands**, now fully specified per carla's content-vs-relationship principle. |
| A3 | alphonso | **CONTRADICTION.** `GateOutcome` has **6** members; `TIMED_OUT`/`CANCELLED` also `Exit(1)` (verified `pre_review_gate.py:742-751`, `tasks_move_task.py:1144,1271-1296`). C-003/FR-011 "sole hard stop" false. | **C-003 + FR-013** enumerate **two** hard-stops; **NFR-001/SC-002** parity set covers all 6 outcomes + both hard-stops. |
| A4 | alphonso | Aggregation of N handlers undefined; NFR-002 "exactly one warning" wrong for N handlers. | **FR-014** (deterministic order, block condition, ≤1 warning/handler, no cross-suppression); **NFR-002** reworded per-handler. |
| A5 | alphonso | Golden parity proved engine, not the inverted hook (the riskiest change). | **NFR-001/SC-002/US2** now require parity **through** `_mt_run_transition_gates` incl. metadata/block/exit/console. |
| F1 (paula) + A7 | paula+alphonso | **#2330 relocated, not closed** — port dropped `parse_results()`; shared runner injects `--junitxml`/`-q` + JUnit-only parse → non-pytest gate is decorative (verified `pre_review_gate.py:656-716`). Also `changed_files()` is the SSOT, shouldn't be per-impl. | **FR-001** narrows port to `test_command/file_to_scope/parse_results`, keeps `changed_files` as shared SSOT; **FR-003** parses to real verdict; **FR-002** moves pytest injection inside internal impl; **NFR-004** proves portable path blocks. |
| F2 (paula) + A8 | paula+alphonso | Dual selector: `_is_spec_kitty_source_repo` probe (verified `:153,183`) competes with activation; consumer that activates spec-kitty handler could still reach the import. | **FR-009** makes activation the sole selector; internal impl+import reachable only when spec-kitty handler activated; probe retired/demoted; **US1 AS4/SC-001** add the erroneous-activation closure test. |
| F3 (paula) + A6 | paula+alphonso | Test-command ownership split across 3 surfaces incl. third key `review.pre_review_test_command` (verified `tasks_move_task.py:785`); portable baseline↔head symmetry undefined. | **FR-011** makes ScopeSource the single authority (baseline+head), reconciles/deprecates the third key; **FR-003/NFR-004** define whole-suite verdict. |
| F4 (paula) + carla-F2/F5 | paula+carla | "Closes #2534/#2330 by construction" overclaimed — #2534 precise for the import, but #2330 is multi-part (accept path gate, mission-review Python gates) and sibling gates retain the coupling class. | **Overview scope-honesty para + C-006** name the out-of-scope siblings; claims narrowed to the "pre-review facet." |
| carla-F1 | carla | **Schema migration debt.** Binding pins `handler` to `mission_step_contract` URN space; a half-B asset handler is a different kind (`_ARTIFACT_TO_NODE_KIND` per-kind, verified `executor.py:31-42`) → #2599 forced to bump `schema_version` on a frozen model. Sibling glossary-pack mission deliberately shipped inert fields to avoid exactly this. | **FR-005** adds inert-in-half-A `handler_kind` (default `mission_step_contract`) + optional `provenance`; **NFR-004/SC-003** prove round-trip. |
| carla-F3 | carla | Two opposite kind precedents (glossary promoted vs this reuses) with no reconciling principle; C-001 justified only by cost (#2468 demands a decision record). | **C-001** rationale expanded to the content-vs-relationship principle; short ADR to be authored at plan. |
| carla-F4 | carla | 3 new "gate"-family terms atop an already-overloaded, now-enforced glossary. | **FR-015** registers `transition gate`/`gate handler`/`gate binding` with "Do NOT confuse with" guards. |
| carla-F5 / A-context | carla+alphonso | Other ~34 gates never named out-of-scope. | Folded into **C-006**. |

## Positive confirmations
- #2843 framing correct (Assumptions absorb the lens-2↔4 reconciliation: mirror, don't ride).
- C-002 half-A/half-B boundary drawn exactly where the epic's strangler splits (steps 1-4 vs step 5).
- No Mission/Feature terminology-canon violation (`feat/` is a conventional-commit tag).

## Carried into plan
- Author the ADR for C-001's content-vs-relationship principle (parallels `docs/adr/3.x/2026-07-21-1-glossary-first-order-doctrine-artefact.md`).
- Data-model must name: the binding home (review step-contract), the loader surface reading bindings, the lane→step mapping table, and the aggregation precedence order.
- WP-level tests must include the erroneous-activation #2534 closure case and the failing-non-pytest-command NEW_FAILURES fidelity case.
