# Research — Mission-Type DRG Node + Cross-Grain Integrity Gate

## R1 — DRG generator internals (S0 grounding)

**Decision:** Add `mission_type` as a node kind and emit one node per built-in type via the existing generator.
**Findings:**
- `graph.yaml` node shape is `{urn, kind, label}` (plus edges elsewhere). Present kinds: action, agent_profile, directive, paradigm, procedure, styleguide, tactic, template, toolguide — **no `mission_type`/`step_contract`/`gate`/`asset`** (confirms the ADR S0 gap).
- DRG code: `src/doctrine/drg/{models.py, validator.py, migration/extractor.py, loader.py, query.py}`; generated header `generated_by: drg-migration-v1`.
- Node kinds are enumerated/validated in `drg/models.py` + `drg/validator.py`; generation is in `drg/migration/extractor.py`. Adding a kind = register in models/validator + teach the extractor to emit `mission_type:<type>` nodes from `missions/mission_types/*.yaml`, then regenerate + `--check`.
**Rationale:** matches the ADR's "packs offer via the graph" for the 8 existing kinds; brings mission_type onto the same rails, which also unblocks cascade (`_source_urn` resolves).
**Alternatives considered:** a bespoke mission_type registry outside the DRG (rejected — perpetuates the "runs outside the graph" gap the ADR closes).

## R2 — FR-013 enforcement home (adjudication outcome)

**Decision:** The load-bearing enforcer is a **doctrine-integrity / DRG consistency gate** over the unioned (type ⊕ action) grain on real content, with a non-vacuity twin. The resolver-embedded `CrossGrainDoubleDeclarationError` is a **lazy fast-fail only**, subordinate to the gate.
**Rationale:** ADR 2026-07-14-2 Enduring-verification already decided this (doctrine-module + integration test with a non-vacuity twin through a shared action name). The resolver raise is verifiably swallowed on every runtime path (`CrossGrainDoubleDeclarationError(ValueError)` sibling of `UnknownMissionTypeError`; runtime `except Exception: pass`; nothing reads `.governance`), and making the runtime consume it eagerly would regress NFR-001.
**Alternatives considered:** (a) resolver-embedded eager guard as sole enforcement — rejected (inert + NFR-001 regression + vacuous on shipped disjoint doctrine); (b) abandon the union — rejected (ADR mandates the union + `_EMPTY_GRAIN` retirement).

## R3 — Vacuity is correct-by-design

**Decision:** Frame the gate as **forward-looking regression protection**; author a deliberate-collision temp-tree fixture for the non-vacuity twin.
**Rationale:** shipped doctrine is authored disjoint on purpose (`plan/actions/plan/index.yaml`: "kept disjoint (FR-013) — do not repeat type-grain selections"). Under the ADR's pack-extensibility, future org/project grains can collide. "Catches no existing defect" is by design; the defect was only the spec's self-contradictory wording, now fixed.

## R4 — Eager→lazy + overlay-aware root

**Decision:** Thunk the governance slot (mirror `expected_artifacts`/`step_contracts`); source the action-grain from the overlay-aware `missions_root` (`MissionTypeProfileRepository`/package-asset resolution), not the resolver's `repo_root`.
**Rationale:** ADR NFR-001 driver ("keep resolution lazy like expected_artifacts/step_contracts"); type-grain is overlay-resolved (project>org>builtin), so a single-root action-grain would be asymmetric authority (ADR-incoherent). `load_action_index` returns a per-action `ActionIndex` dataclass → needs an aggregation loop + `ActionIndex→Mapping[str,list[str]]` adapter before `from_grains`.
**Alternatives considered:** single shipped root (rejected — asymmetric); eager (rejected — NFR-001).

## R5 — Second-source reconciliation

**Decision:** Reconcile the two enduring test-side unions (`_resolve_union`, `_resolve_union_from_mission`) in-mission to a single source.
**Rationale:** once production folds the action-grain in, these double-union; they are a live second implementation of the exact reduction this mission canonicalizes (DIRECTIVE_044 single-authority). ADR testing posture expects substantial suite change.
