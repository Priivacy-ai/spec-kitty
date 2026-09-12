# Post-Plan Adversarial Checkup Squad — Findings & Resolutions

**Date**: 2026-07-22 · **Phase**: post-plan, pre-tasks · **Squad**: 3 Opus specialists (read-only)
**Facets**: reviewer-renata (anti-laziness) · paula-patterns (related-surfaces/blast-radius) · curator-carla (extreme boyscouting/hygiene)
**Verdict pre-amendment**: NOT ready for /spec-kitty.tasks (2 anti-laziness blockers + surface gaps + vestigial-debt gaps). **Post-amendment**: resolved into spec + plan + data-model. Ready for tasks.

All load-bearing claims verified against source before amending.

## Blockers (must-fix) → resolutions

| # | Lens | Finding (verified) | Resolution |
|---|------|--------------------|------------|
| R-F1 | renata | **Mission-type-blind loader.** `load_gate_bindings(repo_root, action)` dropped the `mission` param `get_by_action(mission, action)` requires; only `software-dev` has a `review` action contract (verified: research→gathering/methodology/output/scoping/synthesis; documentation→accept/audit/design/discover/generate/publish/validate). All missions hit `for_review` → research/documentation/consumer WPs resolve to no gate = **mission-type-axis coupling**, invisible because every fixture is software-dev. | **spec FR-008** now requires mission-type resolution (`meta.json`) + a visible `NO_COVERAGE` warn distinguishable from "not activated"; **plan IC-04** loader = `load_gate_bindings(repo_root, mission, action)` + lane→(mission,action)→contract map + non-`software-dev` negative-control test; **data-model** (via alphonso). |
| R-F2 | renata | **Circular parity oracle.** The refactor renames the incumbent hook, so "pre-refactor path" ceases to exist; nothing pins the golden to base commit → an impl could snapshot the NEW code ("passing test / failing system"). | **spec NFR-001** + **plan IC-05 risk** require the golden captured from base `e4ef6e850` against the OLD `_mt_run_pre_review_gate`, red-first, never regenerated; **data-model** parity contract (via alphonso). |

## Major/medium → resolutions

| # | Lens | Finding | Resolution |
|---|------|---------|------------|
| R-F3 | renata | FR-014 aggregation has no production caller in half A (1 binding) → synthetic-only; must be an extracted pure fn, not coverage-by-integration. | **plan IC-05** extracts `aggregate_verdicts()` (pure, full-matrix unit tests) + marks FR-014 a synthetic-exercised seam; **data-model** (via alphonso). |
| R-F4 | renata | IC-05 "EDIT tasks_move_task.py" understates a hook rewrite → ≤15 breach. | **plan IC-05** enumerates `resolve_active_gate_bindings()` / `aggregate_verdicts()` / lane→(mission,action) map as first-class helpers; hook = thin orchestrator. |
| R-F5 | renata | Portable verdict semantics undefined → really `ANY_FAILURES` (no baseline) = false-positive block for pre-existing-red consumer. | **spec FR-003/NFR-004** = baseline-relative + pre-existing-failure fixture; **data-model** parse_results contract (via alphonso). |
| P-F1 | paula | Rename double-breaks the compat surface: `test_tasks_compat_surface.py:217` frozen tuple + `tasks.py:455` re-export barrel (verified). | **plan IC-05**: keep `_mt_run_pre_review_gate` as a **thin alias**; name barrel + tuple in affected-surfaces. |
| P-F2 | paula | Existing incumbent test corpus un-enumerated (6 files) → migration-red indistinguishable from regression-red. | **plan** new "Existing tests to migrate" table mapping each file→IC. |
| P-F3 | paula | Under-linked: **#2595/#2596/#2598** ARE IC-02/03/05 (verified OPEN); **#2741** P1 working-tree-diff bug inherited. | **spec Assumptions** + **plan** "Related issues & tracker mapping" (IC=issue; #2741 preserve-ruling; #2801/#2573/#2803 adjacent-OOS). |
| P-F4 | paula | Schema back-compat: loading absent `gates` is SAFE (verified) — but `save()` `exclude_none` would emit `gates: []` into clean contracts; schema docs unnamed. | **plan IC-04** save round-trip (`exclude_defaults` + byte-stable test); **spec NFR-004**; carla confirms pydantic self-validates → **no schema.yaml/doctor update needed**. |
| P-F5/F6 | paula | `review.pre_review_test_command` deprecation has no alias path; `docs/development/review-gates.md` in no IC. | **plan IC-02** alias + one-time deprecation warning + `review-gates.md` in surface list. |
| C-C1 | carla | Vestigial-debt: retire the whole `is_consumer_repo` machinery, not just the probe (`GateAuthoritiesUnavailable.is_consumer_repo`, `_PRE_REVIEW_CONSUMER_REPO_REASON`, consumer-repo branch). | **plan IC-05** campsite-deletion list (in-scope). |
| C-C2 | carla | 3 stale consumer-repo tests (`test_pre_review_gate_engine.py:100-127`) assert the retired contract. | **plan** "Existing tests to migrate" + IC-05. |
| C-C3 | carla | Third-key misnomer: `pre_review_test_command` feeds *scope override*, not a command; firm the cut. | **plan IC-02** names the disposition + the command-vs-scope misnomer. |
| C-C4 | carla | ADR: wildcard slug + no reciprocal cross-link. | **plan IC-01** pin `-1-` slug + reciprocal link from the glossary-first-order ADR. |
| C-C5 | carla | IC-06 named only the pack YAML; canonical human home `docs/context/orchestration.md` omitted. | **plan IC-06** adds orchestration.md. |
| C-C6 | carla | IC-06 guard list names a phantom `semantic gate`; 5 real senses. | **spec FR-015 + plan IC-06** drop `semantic gate`; keep the 5. |

## Punt-check (honest deferrals confirmed)
- **C-006** sibling gates + non-`for_review` edges: renata confirms nothing the FRs need hides behind it.
- **Legacy glossary seed** (`.kittify/glossaries/`) reconciliation: the glossary-first-order program's job (#1418) — do NOT add a third divergent copy.
- **Missing `mission-step-contract.schema.yaml`**: pre-existing doctrine-schema gap, out of blast radius; the new `gates` field needs no schema doc (pydantic `extra="forbid"` self-validates).

## Net
Two anti-laziness blockers (mission-type coupling, circular oracle) + the demolition-half gaps were the real risk; the design mechanisms are otherwise code-grounded and sound. All folded into spec (15 FR / 6 NFR / 6 C — FR-003/008/015, NFR-001/004 amended) + plan (IC-01/02/04/05/06 + two new subsections) + data-model/contracts (alphonso). Ready for `/spec-kitty.tasks`.
