# Implementation Plan: Doctrine-Controlled Transition Gates

**Branch**: `feat/doctrine-controlled-transition-gates` | **Date**: 2026-07-22 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/doctrine-controlled-transition-gates-01KY51Z7/spec.md`

## Summary

Half A of epic #2535: invert the `→ for_review` pre-review transition gate from "hardcoded to Spec Kitty's own repo shape" to "declared by the repo's active doctrine." A strangler refactor in four independently-landable steps — (1) extract scope behind a `ScopeSource` port, (2) register the existing pre-review engine as the first named handler in a `GATE_REGISTRY`, (3) add a versioned gate-binding schema, (4) invert the hook to resolve active bindings via charter activation — closing the pre-review facet of #2534 (consumer-repo `_gate_coverage` import leak) and #2330 (pytest-layout papercut) by construction. The gate binding lives on the **`MissionStepContract` review contract** (`review.step-contract.yaml`) — the runtime-wired, activation-filtered `mission_step_contract` surface — resolved through a named loader joined against the activated-URN set (the DRG carries no binding payload). Executable third-party gate assets (#2599 / Mission D, half B) are OUT, with an inert `handler_kind` discriminator as the forward-compatible seam.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: existing Spec Kitty runtime surfaces — `specify_cli.review` (pre-review engine, baseline), `specify_cli.cli.commands.agent.tasks_move_task` (the transition hook), `doctrine.missions.step_contracts` (`MissionStepContract`/`MissionStepContractRepository`), `charter` (`PackContext.from_config`, `filter_graph_by_activation`), `specify_cli.mission_step_contracts.executor` (activation-filter pattern to mirror). No new third-party dependencies.
**Storage**: files — `.kittify/config.yaml` (activation state), `*.step-contract.yaml` (gate bindings), `.kittify/glossaries` / `src/doctrine/glossary_packs` (term registration). No database.
**Testing**: pytest, ATDD red-first; `PYTHONPATH=$(pwd)/src`. Golden parity-through-hook, fault-injection, non-vacuous resolution with negative control, portable-verdict fidelity, and #2534/#2330 pre-review-facet closure fixtures (incl. erroneous-activation).
**Target Platform**: cross-platform CLI (Linux/macOS/Windows), Python runtime.
**Project Type**: single project (CLI library) — changes are internal to `src/specify_cli/` + `src/doctrine/` + `docs/`.
**Performance Goals**: NFR-005 — the inverted hook performs at most one doctrine-graph load and one contract-bindings load per transition (no per-candidate re-resolution).
**Constraints**: NFR-006 — `mypy --strict` + `ruff` zero issues, cyclomatic complexity ≤ 15/function, ≥ 90% new-code coverage. C-003 — exactly two hard-stops (opt-in `NEW_FAILURES` block; terminal `TIMED_OUT`/`CANCELLED`); every other handler-execution error fails open to a visible warning. C-004 — PR-bound; no direct pushes to `origin/main`.
**Scale/Scope**: one transition edge (`in_progress→for_review`); ~6 implementation concerns; the other ~34 hardcoded gates are explicitly out of scope (C-006).

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Charter loaded (compact mode). This mission is bound by the charter's Quality & Tech-Debt Standing Orders and Governing Principles:

- **ATDD-first (C-011), red-first discipline** — every concern is authored test-first; the five non-negotiable regression guards (parity-through-hook, per-handler fail-open, non-vacuous resolution, portable-verdict fidelity, #2534/#2330 closure) are locked by C-005. ✅ satisfied by design.
- **Architectural gate discipline / canonical sources** — the mission reuses canonical surfaces (`mission_step_contract`, `filter_graph_by_activation`, the `OrgDoctrineSource` port pattern) rather than improvising; the activation-filter pattern is mirrored from `executor.py:183`, not reimplemented. ✅
- **Single canonical authority** — the `ScopeSource` becomes the single authority for "what command proves the change" (reconciling three drifting surfaces, FR-011); the content-vs-relationship kind principle is recorded in an ADR (IC-01, C-001). ✅
- **Terminology adherence** — three new gate-family terms are registered against the (now first-order, enforced) glossary with disambiguation guards (FR-015, IC-06). Terminology-guard test must run pre-push. ✅
- **Git/workflow discipline** — PR-bound to upstream; `spec-kitty merge` to local main only (C-004). ✅
- **No new charter violations.** No complexity-tracking justifications required (see below).

*Post-design re-check*: no new gates triggered; the binding-home ruling (MissionStepContract vs unified MissionStep) keeps the design on the runtime-wired canonical surface and avoids scope creep into the unified-model wiring.

## Project Structure

### Documentation (this mission)

```
kitty-specs/doctrine-controlled-transition-gates-01KY51Z7/
├── plan.md              # This file
├── research.md          # Phase 0 — 11 resolved design decisions + build map
├── data-model.md        # Phase 1 — ScopeSource port, GateBinding, join, mapping, aggregation
├── quickstart.md        # Phase 1 — five validation walkthroughs
├── contracts/
│   ├── scope-source-port.md
│   ├── gate-binding-schema.md
│   └── transition-gate-hook.md
├── reviews/post-spec-squad.md   # post-spec adversarial squad record
└── tasks.md             # Phase 2 (created by /spec-kitty.tasks — NOT here)
```

### Source Code (repository root)

```
src/specify_cli/review/
├── scope_source.py          # NEW — ScopeSource Protocol + GateCoverageScopeSource + DeclaredCommandScopeSource
├── gate_registry.py         # NEW — GATE_REGISTRY (named handlers); pre-review engine registered first
├── pre_review_gate.py       # EDIT — consume ScopeSource (baseline+head); move pytest/JUnit inside GateCoverageScopeSource;
│                            #        remove always-on `import tests.architectural._gate_coverage`; demote _is_spec_kitty_source_repo
└── baseline.py              # EDIT — read the test command via the single ScopeSource authority

src/specify_cli/cli/commands/agent/
└── tasks_move_task.py       # EDIT — _mt_run_pre_review_gate → _mt_run_transition_gates (activation-driven resolution + aggregation);
                             #        reconcile/deprecate the third `review.pre_review_test_command` key

src/doctrine/missions/
├── step_contracts.py        # EDIT — add versioned `gates: list[GateBinding]` to MissionStepContract (extra=forbid)
└── built_in_step_contracts/
    └── review.step-contract.yaml   # EDIT — author the for_review gate binding

src/doctrine/glossary_packs/built-in/
└── spec-kitty-core.glossary-pack.yaml   # EDIT — register transition gate / gate handler / gate binding + guards

docs/adr/3.x/
└── 2026-07-22-*-gate-binding-content-vs-relationship.md   # NEW — C-001 principle ADR

tests/   # NEW/EDIT — ATDD fixtures: parity-through-hook golden, fault-injection, non-vacuous resolution,
         #            portable-verdict fidelity, #2534/#2330 pre-review-facet closure (incl. erroneous-activation)
```

**Structure Decision**: Single-project CLI. All production changes are confined to `src/specify_cli/review/`, `src/specify_cli/cli/commands/agent/tasks_move_task.py`, `src/doctrine/missions/`, `src/doctrine/glossary_packs/`, and `docs/adr/`. The binding home is the runtime-wired `MissionStepContract` review contract (not the unwired unified `MissionStep`), which keeps the change on the canonical activation-filtered surface and avoids wiring the unified model (out of scope).

## Complexity Tracking

*No Charter Check violations.* The refactor introduces one new abstraction (`ScopeSource` port) and one registry (`GATE_REGISTRY`), both justified by explicit FRs (FR-001, FR-004) and mirrored from existing canonical patterns (`OrgDoctrineSource`, `mission_v1/guards.py::GUARD_REGISTRY`). No new project, no speculative generality — the port surfaces only the three concerns that genuinely vary by repo shape.

## Implementation Concern Map

> **Note**: Implementation concerns are NOT work packages and are NOT executable units.
> `/spec-kitty.tasks` translates these into executable WPs — one concern may become
> multiple WPs; several small concerns may merge into one. IDs below are concern IDs,
> not sequencing labels.

**Recommended build sequence**: IC-01 (ADR) → **IC-02 (ScopeSource port — keystone)** → IC-03 (registry) → IC-04 (binding schema + join + ownership; spike the join early, in parallel with IC-03) → IC-06 (glossary, alongside IC-04) → **IC-05 (invert the hook — integrative, lands last)**.

### IC-01 — Content-vs-relationship ADR (C-001 decision record)

- **Purpose**: Record the durable principle — *promote* a first-class ArtifactKind only for a new distributable content artefact with its own files/provenance; *reuse/attach* when declaring a relationship/configuration on an existing artefact — so reusing `mission_step_contract` (not a new `gate` kind) is justified by principle before the schema work depends on it.
- **Relevant requirements**: C-001 (primary); frames C-002, FR-006.
- **Affected surfaces**: new `docs/adr/3.x/2026-07-22-1-gate-binding-content-vs-relationship.md` (**pin the sequence number `-1-`; do NOT use a wildcard** — `2026-07-21-1` already has colliding slugs). Add a reciprocal **"Related ADRs"** cross-link from `docs/adr/3.x/2026-07-21-1-glossary-first-order-doctrine-artefact.md` (the *promote* precedent) back to this one, so a reader landing on either discovers the governing principle. Consider cross-linking `docs/adr/3.x/2026-05-16-1-doctrine-layer-merge-semantics.md`. No code.
- **Sequencing/depends-on**: none — lands first, independent of code.
- **Risks**: If deferred until after the schema work, the reuse decision becomes retro-justification; the ADR must reconcile the two opposite precedents (glossary *promoted* vs gate *reused*) that the squad flagged, or the #2468 decision-record obligation is unmet.

### IC-02 — ScopeSource port + dual behaviour-split implementations *(keystone / MVP)*

- **Purpose**: Extract the repo-shape-varying concerns behind an injectable `ScopeSource` port (`test_command()`, `file_to_scope()`, `parse_results()`), with `changed_files` kept as the shared canonical merge-base+diff SSOT off the port, and land two implementations — a behaviour-preserving internal one and a portable declared-command one that parses real verdicts.
- **Relevant requirements**: FR-001, FR-002, FR-003, FR-010, FR-011, FR-012; NFR-004 (portable-path verdict fidelity, in part); C-006 (scope guard).
- **Affected surfaces**: new `src/specify_cli/review/scope_source.py`; `src/specify_cli/review/pre_review_gate.py` (move `--junitxml`/`-q` injection + JUnit parse *inside* the internal impl; consume the port for baseline **and** head); `src/specify_cli/cli/commands/agent/tasks_move_task.py` (`_PRE_REVIEW_CONFIG_KEY_TEST_COMMAND` `:785`). **Config-key disposition (firm, per post-plan squad):** `review.pre_review_test_command` (`:785`) actually feeds `_mt_pre_review_scope_override` *scope targets* (`:879-889`), NOT a command — the name lies about its axis. Alias it into the ScopeSource's single authority with a **one-time deprecation warning** (not a silent break); a consumer with the key set keeps working. Update `docs/development/review-gates.md:140-165` (the precedence chain + `review.pre_review_test_command` doc) in lockstep. Related issue: **#2803** (`review.test_command` resolution) — adjacent, out of scope, do not re-open.
- **This IC = tracker issue #2595** ("Extract ScopeSource port … closes #2330 by construction").
- **Sequencing/depends-on**: none (may start immediately; ADR IC-01 in parallel).
- **Risks**: **Behaviour-parity** — the internal impl must reproduce today's exact scope derivation and pytest/JUnit path or the whole strangler is a regression at the base. **Test-command SSOT** — reconciling three resolution sites (baseline capture, head run, third override key) is where drift hides; baseline↔head symmetry must be explicit. **Verdict fidelity** — the portable parser must turn a failing non-JUnit suite into blocking-capable `NEW_FAILURES`, never collapse to `NO_COVERAGE` (the #2330 relocation trap).

### IC-03 — Named gate-handler registry (`GATE_REGISTRY`)

- **Purpose**: Introduce a registry of named, dispatchable gate handlers and register today's pre-review engine as the first handler keyed to the `for_review` edge — with **no behaviour change** (one entry, invoked exactly where the hardcoded call was).
- **Relevant requirements**: FR-004.
- **Affected surfaces**: new `src/specify_cli/review/gate_registry.py`; the pre-review engine in `pre_review_gate.py` registered as first handler; call-site in `tasks_move_task.py` still dispatches the single handler.
- **This IC = tracker issue #2596** ("Register pre-review engine as the first named gate handler").
- **Sequencing/depends-on**: IC-02 (the registered handler consumes the port).
- **Risks**: **Lane→step ownership** must not leak into this IC prematurely — the registry keys on handler name/edge; the binding-driven resolution deciding *which* handler fires is IC-04/IC-05. Any aggregation logic added here is scope creep into IC-05.

### IC-04 — Versioned gate-binding schema, resolution join + loader, and lane→contract ownership

- **Purpose**: Define the versioned, `extra`-forbidding gate-binding model with the inert-in-half-A `handler_kind` discriminator, and mechanically close the resolution mechanism — the activated-URN ⋈ contract-binding-set join, a named binding loader (the DRG carries no binding payload), and a deterministic lane→action→contract mapping with a precedence rule.
- **Relevant requirements**: FR-005, FR-006, FR-007, FR-008; NFR-004 (inert-field byte-stable round-trip), NFR-005 (bounded loads); C-002 (the `handler_kind` seam).
- **Affected surfaces**: `src/doctrine/missions/step_contracts.py` (contract-level `gates: list[GateBinding]` on `MissionStepContract`, mirroring its `extra="forbid"` + `schema_version` pattern; the `.save()` `model_dump(exclude_none=True)` path `:206` must NOT reintroduce `gates: []` into previously-clean contracts — use `exclude_defaults` or equivalent + a round-trip byte-stability test); `src/doctrine/missions/built_in_step_contracts/review.step-contract.yaml` (author the binding); the named loader **`load_gate_bindings(repo_root, mission, action)`** (mission param is mandatory — `MissionStepContractRepository.get_by_action(mission, action)` requires it) reading the review contract's `gates`; resolution mirroring `filter_graph_by_activation` + `PackContext` per `executor.py:183` (mirror the pattern — the graph is not a seam to ride); a **lane-edge→(mission type, action)→contract mapping** (`in_progress→for_review` → the active mission's review contract), mission type resolved from `st.mission_slug`→`meta.json`.
- **No schema-doc/doctor update needed**: step-contracts are pydantic `extra="forbid"` self-validating (there is no `src/doctrine/schemas/mission-step-contract.schema.yaml`); the new field self-validates. Confirm no C-009 top-level-key allowlist covers the review contract (`test_documentation_composition.py:44` is documentation-only).
- **Sequencing/depends-on**: IC-01 (ADR justifies the reuse this schema encodes); IC-03 (bindings resolve to registry handler names).
- **Risks**: **DRG-no-payload join** — `DRGNode` carries only `urn/kind/label/provenance/tags`; the join must load bindings separately from the contract model and retain only handler-resolved-to-activated-URN, or the mechanism is vacuous. **Lane→contract ownership** — the pre-review gate fires on a WP-lane edge with no action context; the mapping across the two FSMs (mission-action vs WP-lane) plus a precedence rule for multiple bindings on one edge must be explicit. **Mission-type-blind loader (blocker)** — only `software-dev` has a `review` action contract; `research`/`documentation`/consumer-custom missions share the `for_review` edge but have no review contract, so a loader that drops the `mission` param silently resolves to no gate = mission-type-axis coupling, and every software-dev fixture passes green while it's broken. The "no contract found" path MUST be a visible `NO_COVERAGE` warn distinguishable from "handler not activated," with a **negative-control test on a non-`software-dev` mission** (FR-008, NFR-003). **Schema-freeze migration debt** — `handler_kind`/`provenance` must be inert *and* byte-stable round-trip now, or half B (#2599) is forced into a breaking `schema_version` bump. This is the **second load-bearing risk** (after the port) — spike the join early.

### IC-05 — Invert the hook: activation as sole selector, fail-open aggregation, parity-through-hook

- **Purpose**: Invert `_mt_run_transition_gates` so the repo's active doctrine (not a repo-shape probe) decides which handlers run — deleting the always-on internal import, retiring `_is_spec_kitty_source_repo` as an impl-selector, and installing deterministic multi-handler aggregation with per-handler fail-open — while proving Spec Kitty's own verdicts are identical through the hook.
- **Relevant requirements**: FR-009, FR-013, FR-014; NFR-001 (parity through hook), NFR-002 (per-handler fail-open), NFR-003 (non-vacuous resolution, proven here); C-003 (two hard-stops), C-006 (scope guard).
- **Affected surfaces**:
  - `tasks_move_task.py` — the inverted hook consuming IC-04's join + IC-03 registry. **Keep `_mt_run_pre_review_gate` as a thin alias** that delegates to the new `_mt_run_transition_gates` (preserves the compat surface and shrinks blast radius) rather than a bare rename. Retire the `_is_spec_kitty_source_repo` call-site.
  - **Extract pure helpers** (hook stays a thin orchestrator so each is independently testable and ≤15 complexity, NFR-006): `resolve_active_gate_bindings(...)` (the §5 join), `aggregate_verdicts(verdicts) -> Verdict` (the §7 precedence — a **pure function with its own full-matrix unit tests**, since FR-014 multi-handler aggregation ships with only ONE production binding in half A = a synthetic-exercised seam), and the lane→(mission,action) mapping.
  - `pre_review_gate.py` — remove the always-on `import tests.architectural._gate_coverage`; demote `_is_spec_kitty_source_repo` to a private internal of `GateCoverageScopeSource` (must NOT gate impl selection).
  - **Campsite deletion (in-scope, prevents vestigial debt — per boyscout lens):** with `_is_spec_kitty_source_repo` demoted and the import gone, the whole `is_consumer_repo` machinery is dead — delete `GateAuthoritiesUnavailable.is_consumer_repo` (`pre_review_gate.py:143-145,183-196`), `_PRE_REVIEW_CONSUMER_REPO_REASON` (`tasks_move_task.py:797-800`), and the consumer-repo message branch (`:1056-1069`); the generic per-handler fail-open warn supersedes them.
  - **Compat surface (guaranteed-red without update):** `src/specify_cli/cli/commands/agent/tasks.py:432-455` re-export barrel and `tests/specify_cli/cli/commands/agent/test_tasks_compat_surface.py:217` `_TASKS_MOVE_TASK` tuple — any new/relocated `_mt_*` symbol migrates its barrel line + tuple entry together.
  - `docs/development/review-gates.md` — behavior/precedence prose. *(Agent-copy propagation N/A: grep of `src/doctrine/missions/*/command-templates/` finds no gate prose, so the CLAUDE.md "update all agents" rule is satisfied by the doc alone.)*
- **This IC = tracker issue #2598** ("Invert move-task gate hook … closes #2534 by construction").
- **Sequencing/depends-on**: IC-02, IC-03, IC-04 (integrative — consumes all three).
- **Risks**: **Fail-open** — every handler *execution error* degrades to exactly one visible "unverified" warning; only two hard-stops survive; introducing a third, or converting a hard-stop to a warn, is a regression. **Aggregation** — a faulting handler must never suppress another's verdict or block; dispatch order fixed. **Dual-selector retirement** — the internal import must be unreachable even under *erroneous* spec-kitty-handler activation, or the #2534 closure is configuration-dependent rather than structural. **Parity-through-hook** — the golden must route through `_mt_run_transition_gates` (metadata + block/exit + console), not just the engine; a resolution test that would pass against an empty graph is rejected (NFR-003 negative control). **Circular-oracle trap (blocker):** the golden's expected values MUST be captured from the base commit against the incumbent `_mt_run_pre_review_gate` BEFORE the refactor (committed fixture, red-first against the OLD function), never regenerated from the new code — otherwise parity is decorative (the repo's documented "passing test / failing system" mode). Highest coordination risk — lands last.

### IC-06 — Gate terminology registered against the overloaded glossary

- **Purpose**: Register `transition gate`, `gate handler`, and `gate binding` as canonical terms with "Do NOT confuse with" guards against the existing gate senses, so three new gate-family terms don't fragment the now-first-order, enforced glossary.
- **Relevant requirements**: FR-015.
- **Affected surfaces**: `src/doctrine/glossary_packs/built-in/spec-kitty-core.glossary-pack.yaml` AND `docs/context/orchestration.md` (the canonical *human* term home per CLAUDE.md's Terminology Canon — e.g. the `### branch strategy gate` entry at `:369`; author the three terms in BOTH). Guard against the **five real** existing senses: `branch strategy gate`, `diff compliance gate`, `dependency gate`, `merge dependency gate`, `sonar quality gate`. (Do NOT guard against `semantic gate` — grep-verified: no such surface exists.) Do NOT add a third divergent copy to `.kittify/glossaries/spec_kitty_core.yaml` — seed-vs-pack reconciliation is the glossary-first-order program's job (#1418), out of scope here.
- **Sequencing/depends-on**: rides alongside IC-04 (the terms it names — binding/handler — are the artefacts IC-04 introduces); no code dependency.
- **Risks**: Low. The only trap is defining the terms before IC-04 fixes their precise meaning; keep authorship co-timed with IC-04.

### Existing tests to migrate (incumbent corpus — red-then-migrate, not delete-to-green)

These assert the CURRENT hardcoded behaviour and will go red under the refactor; they must be migrated (not silenced), and the migration-red must be distinguishable from a regression-red. Reviewers should expect these to change:

| Test file | Asserts (current) | Migrates with |
|---|---|---|
| `tests/review/test_pre_review_gate_engine.py:100-127` | `_is_spec_kitty_source_repo` public probe + `is_consumer_repo=True` contract | IC-05 (retire/rewrite alongside the erroneous-activation closure test) |
| `tests/review/test_pre_review_gate_interpreter.py:36-73` | `resolve_pytest_command` branch behaviour | IC-02 (port supersedes it; move inside `GateCoverageScopeSource`) |
| `tests/review/test_pre_review_gate_integration.py:171,228,391,955` | real-git `run_scoped_tests_at_head`; writes `pre_review_test_command:`; binds `_mt_run_pre_review_gate` | IC-02 (runner/key) + IC-05 (hook alias) |
| `tests/specify_cli/cli/commands/agent/test_tasks_move_task_pre_review_gate_escape_hatch.py` (11 sites) | monkeypatch `_mt_run_pre_review_gate` by name | IC-05 (thin alias preserves these) |
| `..._observability.py:552`, `test_tasks_cli_contract_coord.py:798` | bind `_mt_run_pre_review_gate` | IC-05 (alias) |
| `tests/specify_cli/cli/commands/agent/test_tasks_compat_surface.py:217` | frozen `_TASKS_MOVE_TASK` symbol tuple | IC-05 (update tuple + `tasks.py` barrel together) |

### Related issues & tracker mapping

- **IC-02 = #2595**, **IC-03 = #2596**, **IC-05 = #2598** (epic #2535 sub-issues — the plan's ICs already have tracker items; reference them at tasks time).
- **#2741 (P1) — inherited, NOT fixed.** The gate diffs the working tree, not the WP commit range (`_mt_pre_review_changed_files`→`merge_base_changed_files`, `tasks_move_task.py:927`). Behaviour-preserving parity *preserves* this bug by design; state this explicitly so it is not mistaken for a fix or flagged as a regression. Out of scope.
- **Adjacent, out of scope — do not re-open as regressions:** #2801/#2573 (skip-flag / disable-env seam, `tasks_move_task.py:854-876`), #2803 (`review.test_command` resolution).

### FR → IC coverage

Every FR-001..015 has a home: FR-001/002/003/010/011/012 → IC-02; FR-004 → IC-03; FR-005/006/007/008 → IC-04; FR-009/013/014 → IC-05; FR-015 → IC-06. NFR-001/002 → IC-05; NFR-003 → IC-04 (defines) + IC-05 (proves); NFR-004 → IC-02 + IC-04; NFR-005 → IC-04; NFR-006 → all (global). C-001 → IC-01; C-002 → IC-04; C-003 → IC-05; C-004/C-005 → all (global guards); C-006 → IC-02 + IC-05. No orphan requirements.
