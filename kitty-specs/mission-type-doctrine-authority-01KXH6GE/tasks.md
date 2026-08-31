# Tasks: Mission-Type Doctrine Authority

**Mission**: mission-type-doctrine-authority-01KXH6GE | **Branch**: `mission/883-mission-type-governance-profiles`
**Plan**: [plan.md](./plan.md) (9-IC / 4-lane map, post-plan-squad reconciled) | **Spec**: [spec.md](./spec.md)
**Design authority**: [ADR 2026-07-14-2](../../docs/adr/3.x/2026-07-14-2-doctrine-to-core-mission-type-resolution-unification.md) · [data-model.md](./data-model.md) · [contracts/resolution-and-enforcement.md](./contracts/resolution-and-enforcement.md)

> The architecture is **fixed by the ADR** (Accepted). These WPs decompose it; they do not
> re-decide it. Every WP maps ~1:1 to a plan IC. The ADR / plan / contracts are the authority —
> WP bodies cite them and add per-subtask execution guidance, they do not restate the design.

**12 work packages across 4 lanes.** Slice 1 of the `specify_cli/missions` retirement (#883, partial
close — **no PR auto-close keyword**). Two swaps (gates, steps) carry **transitional parity scaffolds**
added at the swap's start and **deleted before merge** (C-002, NFR-005). The enduring guards are
behavioural (non-leakage + non-vacuity twin + determinism), authored as doctrine-module + integration
tests in the join (WP12).

## Lane shape (binding — see plan.md "Cross-cutting notes")

- **Lane A — tidy (independent root):** WP01 (retire `governance_refs`). Behaviour-preserving, first,
  no dependency. Shares the terminal `graph.yaml` regenerate with WP06/07/08 — that regenerate is
  **owned once by WP12** so no lane clobbers DRG freshness.
- **Lane B — critical path (SERIAL SPINE):** WP02 (canonicalizer) → WP03 (resolver seam) →
  {WP04 (leak closure), WP05 (override channel), WP11 (steps swap)}. WP03 is the seam every downstream
  WP converges on; it MUST subsume-and-migrate (never add-beside) and stay ≤ 15 complexity.
- **Lane C — content authoring (PARALLEL, uneven):** WP06 (documentation, heaviest — 5 net-new
  styleguides), WP07 (research), WP08 (plan, lightest). Each deps WP03 (schema stable) **and** WP05
  (the `id == mission_type` overlay invariant). Sized off the ADR artifact inventory, not equal thirds.
- **Lane D — gates/dossier swap (DETACHABLE, NON-BLOCKING):** WP09 (reconcile upward) → WP10
  (adapter + reader flip + delete copies). Internal hard edge reconcile→migrate. **This lane must NOT
  gate the join** — WP12 does not depend on it (FR-007 / NFR-004). On deep drift the final flip in WP10
  may defer to slice 2 (reconciliation still lands; deferral recorded, never silent).
- **Join — enforcement (TERMINAL):** WP12. Deps WP03, WP04, WP06, WP07, WP08, WP11. **Explicitly NOT
  WP09/WP10** — making the enduring governance guards depend on a deliberately non-blocking lane would
  gate the mission on it (violating FR-007/NFR-004). WP12 owns the single terminal
  `regenerate-graph --check`, run once after WP01 + WP06/07/08 land.

**Single-file ownership invariants (no-overlap by construction):**
`src/charter/mission_type_profiles.py` → WP03 (WP05 adds `id` to `MissionTypeProfile`, WP10 populates
the `expected_artifacts` slot — both **sequential, recorded out-of-map** edits **serialized** behind
WP03: WP05←WP03 and WP10←WP03+WP05, so the two out-of-map edits never run in parallel);
`src/charter/context.py` → WP04; `src/doctrine/base.py` → WP05;
`src/doctrine/missions/step_contracts.py` → WP11; `src/doctrine/graph.yaml` → WP12.
**Coordination resolved (post-squad):** `src/specify_cli/cli/commands/mission_type.py` is owned by **WP01**
(governance_refs display removal). WP03 now **migrates** the `resolve_action_sequence` caller at `:1477`
(+ its import) as a **justified out-of-map, sequential** edit — enabled by the new **WP01 → WP03**
dependency edge (WP01 lands first, leaving the file quiet). No caller is operator-deferred. See
"WP01/WP03 mission_type.py coordination" below.

## Dependency graph (edges)

```
WP01 ─┐  (root, Lane A)
WP02 ─┴→ WP03 → WP04                      (Lane B spine; WP03 deps WP01, WP02)
                → WP05 → {WP06, WP07, WP08}   (Lane C, each deps WP03+WP05)
                → WP11
WP09 → WP10                              (Lane D, detachable — NOT a WP12 dep; WP10 deps WP09, WP03, WP05)
{WP03, WP04, WP06, WP07, WP08, WP11} → WP12   (join)
```

Roots: **WP01, WP02, WP09.**

## WP → IC → requirement map

| WP | IC | Title | Deps | Profile | Functional refs |
|----|----|-------|------|---------|-----------------|
| WP01 | IC-01 | Retire `governance_refs` | — | python-pedro | FR-010 |
| WP02 | IC-02 | Mission-type canonicalizer | — | python-pedro | FR-012, FR-001, FR-003, C-001 (FR-003a in body) |
| WP03 | IC-03 | Unified resolver seam | WP01, WP02 | python-pedro | FR-006, FR-013, FR-004, FR-003, FR-009, NFR-007, NFR-001 |
| WP04 | IC-04 | Action-path leak closure | WP03 | python-pedro | FR-002, FR-001, C-004 (FR-003a in body) |
| WP05 | IC-05 | Per-type override channel | WP03 | python-pedro | FR-011, C-005 |
| WP06 | IC-06a | Documentation governance content | WP03, WP05 | doctrine-daphne | FR-005, FR-002, NFR-006 (SC-004 in body) |
| WP07 | IC-06b | Research governance content | WP03, WP05 | doctrine-daphne | FR-005 (SC-004 in body) |
| WP08 | IC-06c | Plan governance content | WP03, WP05 | doctrine-daphne | FR-005 (SC-004 in body) |
| WP09 | IC-07a | Gates reconcile upward | — | python-pedro | FR-007 |
| WP10 | IC-07b | Gates migrate/flip | WP09, WP03, WP05 | python-pedro | FR-007, NFR-004, NFR-001 (SC-005 in body) |
| WP11 | IC-08 | Steps swap | WP03 | python-pedro | FR-008, NFR-001 (SC-007 in body) |
| WP12 | IC-09 | Enforcement + test posture | WP03, WP04, WP06, WP07, WP08, WP11 | python-pedro | NFR-005, NFR-006, NFR-007, C-002 (SC-001/002/003/006 in body) |

> `NFR-002` (ruff/mypy clean) and `NFR-003` (complexity ≤ 15) bind **every** code WP and are carried in
> each WP's `requirement_refs`. `FR-003a` (typeless/mission-less degrade), `SC-*` (success criteria), and
> the remaining `C-*` constraints are validated at the behaviour level inside the WP bodies — they are
> not `FR|NFR|C-\d+`-shaped mappable refs, so they live in Context/DoD, not `requirement_refs`.

## Subtask Index

| ID | Description | WP |
|----|-------------|----|
| T001 | Remove `governance_refs` from `MissionType` model (`extra="forbid"`) | WP01 |
| T002 | Strip `governance_refs:` + dangling `DIR-010/011` from all four `mission_types/*.yaml` | WP01 |
| T003 | Update `mission_type.py` CLI display (drop the governance_refs rows) | WP01 |
| T004 | Fix the `drg.py:169` comment; re-point any DRG parity guard | WP01 |
| T005 | Update the ~3–4 tests that asserted the field; ruff/mypy clean | WP01 |
| T006 | New boundary-safe `charter/mission_type_key.py` canonicalizer | WP02 |
| T007 | Remove sw-dev governance default at `mission.py get_mission_type:575` | WP02 |
| T008 | Route `get_deliverables_path:605` through the canonicalizer | WP02 |
| T009 | Retire the dead `get_mission_key:548` | WP02 |
| T010 | Classify the ~13 `get_mission_type` callers (has-meta → unaffected; typeless → neutral degrade) | WP02 |
| T011 | RED-first: typeless caller degrades (never sw-dev); ruff/mypy clean | WP02 |
| T012 | `ResolvedMissionType` / `ResolvedGovernance` ordered bundle types | WP03 |
| T013 | `resolve_mission_type_context` resolver + `_resolve_*` helpers (≤ 15) | WP03 |
| T014 | Subsume `resolve_action_sequence`/`resolve_mission_type_governance`/`load_profile` | WP03 |
| T015 | Migrate all 7 call-sites (incl. `mission_type.py:1477`) + `__all__` + stale doc ref `resolver.py:299` | WP03 |
| T016 | URN-normalized cross-grain disjointness guard (FR-013) | WP03 |
| T017 | Preserve the two hard-fail policies as explicit branches; FR-004 empty-grain | WP03 |
| T018 | Transitional sw-dev byte-parity scaffold (deleted at WP end); determinism test | WP03 |
| T019 | RED-first behavioural test through a shared action name (leak repro) | WP04 |
| T020 | Rewire `_load_action_doctrine_bundle:865` off `template_set` onto `meta.json` | WP04 |
| T021 | Thread `mission_type` through `build_charter_context:252` + `_json:3254` + `scope_router:66` | WP04 |
| T022 | Split `template_set` (kept for template-file selection only, C-004) | WP04 |
| T023 | Delete the dead `_render_action_scoped:1500`/`_append_action_doctrine_lines:1451` pair + its orphan test `test_context.py:716` | WP04 |
| T024 | Per-entry degrade for mission-less callers (`executor.py:270`, `workflow.py:675`); ruff/mypy | WP04 |
| T025 | Add `id` to `MissionTypeProfile` (out-of-map into WP03's file, sequential) | WP05 |
| T026 | `BaseDoctrineRepository[MissionTypeProfile]` subclass in `charter/` | WP05 |
| T027 | Wire the overlay (`doctrine/base.py`) builtin → org → project for the profile | WP05 |
| T028 | Precedence + collision test (project override wins, warning reported) | WP05 |
| T029 | `id == mission_type` invariant asserted; ruff/mypy clean | WP05 |
| T030 | Reference-wire existing docs doctrine (042-common-docs, 037-living-docs, curation tactics, mermaid/plantuml) | WP06 |
| T031 | Author `divio-type-discipline` styleguide | WP06 |
| T032 | Author `plain-language` styleguide | WP06 |
| T033 | Author `docs-accessibility` styleguide | WP06 |
| T034 | Author `publication-authority` styleguide | WP06 |
| T035 | Author `docs-freshness-sla` styleguide | WP06 |
| T036 | `documentation/governance-profile.yaml` (`id: documentation`) + `actions/*/index.yaml` | WP06 |
| T037 | Reference-wire existing research doctrine (003-decision-doc, dialectic/premortem/reverse-speccing, situational-assessment) | WP07 |
| T038 | Author `spike-timebox-policy` procedure (closes `researcher-robbie.agent.yaml:60` dangler) | WP07 |
| T039 | Author `research-citation-discipline` styleguide | WP07 |
| T040 | `research/governance-profile.yaml` (`id: research`) | WP07 |
| T041 | `research/actions/*/index.yaml` | WP07 |
| T042 | DRG resolvability check for the 2 net-new artifacts; terminology guard | WP07 |
| T043 | Reference-wire existing plan doctrine (problem-decomposition, moscow, eisenhower, adr-drafting, 031-context-aware-design, DDD/deep-module/c4 paradigms, planning-and-tracking) | WP08 |
| T044 | `plan/governance-profile.yaml` (`id: plan`) | WP08 |
| T045 | Create `plan/actions/` indices (create_intent — plan has no actions dir today) | WP08 |
| T046 | FR-004 verification: plan's empty grain resolves empty without error | WP08 |
| T047 | DRG resolvability + terminology guard | WP08 |
| T048 | Port `runtime.charter-lint.decay` → `lint-report.json` delta upward (doctrine tree) | WP09 |
| T049 | Port `blocking: false` flag upward | WP09 |
| T050 | Port the `occurrence_map.yaml` bulk-edit NOTE comment block upward | WP09 |
| T051 | Confirm doctrine ≡ specify_cli content post-reconcile (pre-flip parity baseline) | WP09 |
| T052 | `ConfigResult → ExpectedArtifactManifest` adapter (`model_validate(parsed)`) + cache preserve | WP10 |
| T053 | Transitional dossier-parity scaffold (sw-dev required-artifact set unchanged) | WP10 |
| T054 | Flip `load_manifest:178` onto the doctrine tree | WP10 |
| T055 | Update the 5 consumer sites (`indexer.py:77,130,307,359`, `namespace.py:98`) | WP10 |
| T056 | Delete `specify_cli/missions/*/expected-artifacts.yaml` copies (reconcile-before-flip) | WP10 |
| T057 | Populate `ResolvedMissionType.expected_artifacts` slot (out-of-map into WP03's file) | WP10 |
| T058 | Delete the transitional dossier-parity scaffold; ruff/mypy clean | WP10 |
| T059 | Route step-contract resolution through the artefact bundle | WP11 |
| T060 | Pin exact anchors + migrate the `specify_cli` step-contract readers | WP11 |
| T061 | Transitional step-parity scaffold (sw-dev step behaviour unchanged) | WP11 |
| T062 | Delete the step-parity scaffold; SC-007 (0 remaining specify_cli readers) | WP11 |
| T063 | ruff/mypy clean; NFR-001 recorded | WP11 |
| T064 | Enduring non-leakage test (URN-normalized denylist, doctrine-module) | WP12 |
| T065 | Non-vacuity twin (shared action name — sw-dev DOES resolve the denylist) | WP12 |
| T066 | Determinism test (byte-identical on identical inputs, NFR-007) | WP12 |
| T067 | Integration test: real documentation/research/plan mission resolves domain governance, zero sw-dev | WP12 |
| T068 | Unknown-typed hard-fail + typeless-degrade on every path (SC-002) | WP12 |
| T069 | Delete ALL transitional parity scaffolds; assert 0 remain at merge (NFR-005) | WP12 |
| T070 | Terminal `regenerate-graph --check` (single owner); terminology guard | WP12 |

## Work Packages

### WP01 — Retire the inert `governance_refs` field (FR-010)

**Goal**: Remove the dead, dangling per-type `governance_refs` field (model + all four `mission_types/*.yaml`
+ CLI display + `drg.py:169` comment) so governance resolves only through the live path — no danglers.
Behaviour-preserving tidy; independent Lane-A root.

- [x] T001 Remove `governance_refs` from `MissionType` model (`extra="forbid"`) (WP01)
- [x] T002 Strip `governance_refs:` + dangling `DIR-010/011` from all four `mission_types/*.yaml` (WP01)
- [x] T003 Update `mission_type.py` CLI display (drop the governance_refs rows) (WP01)
- [x] T004 Fix the `drg.py:169` comment; re-point any DRG parity guard (WP01)
- [x] T005 Update the ~3–4 tests that asserted the field; ruff/mypy clean (WP01)

Prompt: [tasks/WP01-retire-governance-refs.md](./tasks/WP01-retire-governance-refs.md) · deps: none

### WP02 — Single boundary-safe mission-type canonicalizer (FR-012, FR-001, FR-003, C-001)

**Goal**: One canonicalizer both layers import (charter ↛ specify_cli); remove the sw-dev governance default
at `mission.py get_mission_type:575`; retire dead `get_mission_key:548`; classify the ~13 callers.
Lane-B root.

- [x] T006 New boundary-safe `charter/mission_type_key.py` canonicalizer (WP02)
- [x] T007 Remove sw-dev governance default at `mission.py get_mission_type:575` (WP02)
- [x] T008 Route `get_deliverables_path:605` through the canonicalizer (WP02)
- [x] T009 Retire the dead `get_mission_key:548` (WP02)
- [x] T010 Classify the ~13 `get_mission_type` callers (has-meta → unaffected; typeless → neutral degrade) (WP02)
- [x] T011 RED-first: typeless caller degrades (never sw-dev); ruff/mypy clean (WP02)

Prompt: [tasks/WP02-mission-type-canonicalizer.md](./tasks/WP02-mission-type-canonicalizer.md) · deps: none

### WP03 — Unified resolver seam (ResolvedMissionType bundle) (FR-006, FR-013, FR-004, FR-003, FR-009, NFR-007, NFR-001)

**Goal**: One charter-mediated `resolve_mission_type_context` both consumers converge on; ordered
`ResolvedGovernance`; URN-normalized cross-grain disjointness; subsume-and-migrate 3 functions + 7 live
call-sites (`load_profile` = export-removal, 0 callers); ≤ 15 complexity; preserve the existing
`UnknownMissionTypeError`; transitional sw-dev parity scaffold deleted at WP end.

- [x] T012 `ResolvedMissionType` / `ResolvedGovernance` ordered bundle types (WP03)
- [x] T013 `resolve_mission_type_context` resolver + `_resolve_*` helpers (≤ 15) (WP03)
- [x] T014 Subsume `resolve_action_sequence`/`resolve_mission_type_governance`/`load_profile` (WP03)
- [x] T015 Migrate all 7 call-sites (incl. `mission_type.py:1477`) + `__all__` + stale doc ref `resolver.py:299` (WP03)
- [x] T016 URN-normalized cross-grain disjointness guard (FR-013) (WP03)
- [x] T017 Preserve the two hard-fail policies + existing `UnknownMissionTypeError`; FR-004 empty-grain (WP03)
- [x] T018 Transitional sw-dev byte-parity scaffold (deleted at WP end); determinism test (WP03)

Prompt: [tasks/WP03-unified-resolver-seam.md](./tasks/WP03-unified-resolver-seam.md) · deps: WP01, WP02

### WP04 — Action-path leak closure (FR-002, FR-001, C-004)

**Goal**: Rewire the live `_load_action_doctrine_bundle:865` off `template_set` onto `meta.json`; delete
the dead `_render_action_scoped`/`_append_action_doctrine_lines` pair + orphan test; split `template_set`;
per-entry degrade; RED-first. Do NOT grow into #2532.

- [x] T019 RED-first behavioural test through a shared action name (leak repro) (WP04)
- [x] T020 Rewire `_load_action_doctrine_bundle:865` off `template_set` onto `meta.json` (WP04)
- [x] T021 Thread `mission_type` through `build_charter_context:252` + `_json:3254` + `scope_router:66` (WP04)
- [x] T022 Split `template_set` (kept for template-file selection only, C-004) (WP04)
- [x] T023 Delete the dead pair + its orphan test `test_context.py:716` (WP04)
- [x] T024 Per-entry degrade for mission-less callers (`executor.py:270`, `workflow.py:675`); ruff/mypy (WP04)

Prompt: [tasks/WP04-action-path-leak-closure.md](./tasks/WP04-action-path-leak-closure.md) · deps: WP03

### WP05 — Per-type project override channel (FR-011, C-005)

**Goal**: Ride the `doctrine/base.py` overlay (builtin → org → project); add `id` to `MissionTypeProfile`;
`BaseDoctrineRepository[MissionTypeProfile]` subclass in `charter/`; set the `id == mission_type` invariant;
precedence + collision test.

- [x] T025 Add `id` to `MissionTypeProfile` (out-of-map into WP03's file, sequential) (WP05)
- [x] T026 `BaseDoctrineRepository[MissionTypeProfile]` subclass in `charter/` (WP05)
- [x] T027 Wire the overlay (`doctrine/base.py`) builtin → org → project for the profile (WP05)
- [x] T028 Precedence + collision test (project override wins, warning reported) (WP05)
- [x] T029 `id == mission_type` invariant asserted; ruff/mypy clean (WP05)

Prompt: [tasks/WP05-per-type-override-channel.md](./tasks/WP05-per-type-override-channel.md) · deps: WP03

### WP06 — Author documentation governance content (FR-005, FR-002, NFR-006)

**Goal**: Reference-wire existing docs doctrine + author 5 net-new styleguides; populate
`documentation/governance-profile.yaml` (`id: documentation`) + action indices. Heaviest content WP.

- [x] T030 Reference-wire existing docs doctrine (042-common-docs, 037-living-docs, curation tactics, toolguides) (WP06)
- [x] T031 Author `divio-type-discipline` styleguide (WP06)
- [x] T032 Author `plain-language` styleguide (WP06)
- [x] T033 Author `docs-accessibility` styleguide (WP06)
- [x] T034 Author `publication-authority` styleguide (WP06)
- [x] T035 Author `docs-freshness-sla` styleguide (WP06)
- [x] T036 `documentation/governance-profile.yaml` (`id: documentation`) + `actions/*/index.yaml` (WP06)

Prompt: [tasks/WP06-documentation-governance-content.md](./tasks/WP06-documentation-governance-content.md) · deps: WP03, WP05

### WP07 — Author research governance content (FR-005)

**Goal**: Reference-wire existing research doctrine + author `spike-timebox-policy` procedure (closes the
`researcher-robbie.agent.yaml:60` dangler) and `research-citation-discipline` styleguide; populate
`research/governance-profile.yaml` (`id: research`) + action indices.

- [x] T037 Reference-wire existing research doctrine (003-decision-doc, dialectic/premortem/reverse-speccing, situational-assessment) (WP07)
- [x] T038 Author `spike-timebox-policy` procedure (closes `researcher-robbie.agent.yaml:60` dangler) (WP07)
- [x] T039 Author `research-citation-discipline` styleguide (WP07)
- [x] T040 `research/governance-profile.yaml` (`id: research`) (WP07)
- [x] T041 `research/actions/*/index.yaml` (WP07)
- [x] T042 DRG resolvability check for the 2 net-new artifacts; terminology guard (WP07)

Prompt: [tasks/WP07-research-governance-content.md](./tasks/WP07-research-governance-content.md) · deps: WP03, WP05

### WP08 — Author plan governance content (FR-005)

**Goal**: Mostly reference-only planning doctrine; populate `plan/governance-profile.yaml` (`id: plan`);
create `plan/actions/` indices (plan has no actions dir today); FR-004 empty-grain verified. Lightest content WP.

- [x] T043 Reference-wire existing plan doctrine (problem-decomposition, moscow, eisenhower, adr-drafting, 031-context-aware-design, DDD/deep-module/c4, planning-and-tracking) (WP08)
- [x] T044 `plan/governance-profile.yaml` (`id: plan`) (WP08)
- [x] T045 Create `plan/actions/` indices (create_intent — plan has no actions dir today) (WP08)
- [x] T046 FR-004 verification: plan's empty grain resolves empty without error (WP08)
- [x] T047 DRG resolvability + terminology guard (WP08)

Prompt: [tasks/WP08-plan-governance-content.md](./tasks/WP08-plan-governance-content.md) · deps: WP03, WP05

### WP09 — Reconcile expected-artifacts upward into the doctrine tree (FR-007)

**Goal**: Port the specify_cli-ahead deltas (charter-lint.decay→lint-report.json, blocking:false,
occurrence_map NOTE block; #2628) UPWARD into the doctrine copies. Detachable Lane-D root; hard predecessor
of WP10.

- [x] T048 Port `runtime.charter-lint.decay` → `lint-report.json` delta upward (doctrine tree) (WP09)
- [x] T049 Port `blocking: false` flag upward (WP09)
- [x] T050 Port the `occurrence_map.yaml` bulk-edit NOTE comment block upward (WP09)
- [x] T051 Confirm doctrine ≡ specify_cli content post-reconcile (pre-flip parity baseline) (WP09)

Prompt: [tasks/WP09-gates-reconcile-upward.md](./tasks/WP09-gates-reconcile-upward.md) · deps: none

### WP10 — Adapt + flip the dossier gate reader onto the doctrine tree (FR-007, NFR-004, NFR-001)

**Goal**: `ConfigResult → ExpectedArtifactManifest` adapter + cache; flip `load_manifest:178` to the
doctrine tree; delete the specify_cli copies; populate the bundle's `expected_artifacts` slot; transitional
parity scaffold deleted at WP end. Detachable — NOT a WP12 dep.

- [x] T052 `ConfigResult → ExpectedArtifactManifest` adapter (`model_validate(parsed)`) + cache preserve (WP10)
- [x] T053 Transitional dossier-parity scaffold (sw-dev required-artifact set unchanged) (WP10)
- [x] T054 Flip `load_manifest:178` onto the doctrine tree (WP10)
- [x] T055 Update the 5 consumer sites (`indexer.py:77,130,307,359`, `namespace.py:98`) (WP10)
- [x] T056 Delete `specify_cli/missions/*/expected-artifacts.yaml` copies (reconcile-before-flip) (WP10)
- [x] T057 Populate `ResolvedMissionType.expected_artifacts` slot (out-of-map into WP03's file) (WP10)
- [x] T058 Delete the transitional dossier-parity scaffold; ruff/mypy clean (WP10)

Prompt: [tasks/WP10-gates-migrate-flip.md](./tasks/WP10-gates-migrate-flip.md) · deps: WP09, WP03, WP05

### WP11 — Route step-contract resolution through the artefact bundle (FR-008)

**Goal**: Route step-contract resolution through the artefact bundle; pin + migrate the specify_cli
step-contract readers (SC-007 → 0); transitional step-parity scaffold deleted at WP end.

- [x] T059 Route step-contract resolution through the artefact bundle (WP11)
- [x] T060 Pin exact anchors + migrate the `specify_cli` step-contract readers (WP11)
- [x] T061 Transitional step-parity scaffold (sw-dev step behaviour unchanged) (WP11)
- [x] T062 Delete the step-parity scaffold; SC-007 (0 remaining specify_cli readers) (WP11)
- [x] T063 ruff/mypy clean; NFR-001 recorded (WP11)

Prompt: [tasks/WP11-steps-swap.md](./tasks/WP11-steps-swap.md) · deps: WP03

### WP12 — Enforcement gates + test posture (the join) (NFR-005, NFR-006, NFR-007, C-002)

**Goal**: Enduring non-leakage (URN denylist) + non-vacuity twin (shared action name) + determinism +
integration + hard-fail/degrade tests; delete ALL transitional scaffolds; single terminal
`regenerate-graph --check`. Deps WP03, WP04, WP06, WP07, WP08, WP11 — NOT WP09/WP10.

- [x] T064 Enduring non-leakage test (URN-normalized denylist, doctrine-module) (WP12)
- [x] T065 Non-vacuity twin (shared action name — sw-dev DOES resolve the denylist) (WP12)
- [x] T066 Determinism test (byte-identical on identical inputs, NFR-007) (WP12)
- [x] T067 Integration test: real documentation/research/plan mission resolves domain governance, zero sw-dev (WP12)
- [x] T068 Unknown-typed hard-fail + typeless-degrade on every path (SC-002) (WP12)
- [x] T069 Delete ALL transitional parity scaffolds; assert 0 remain at merge (NFR-005) (WP12)
- [x] T070 Terminal `regenerate-graph --check` (single owner); terminology guard (WP12)

Prompt: [tasks/WP12-enforcement-test-posture.md](./tasks/WP12-enforcement-test-posture.md) · deps: WP03, WP04, WP06, WP07, WP08, WP11

## WP01/WP03 `mission_type.py` coordination (RESOLVED — post-squad)

`src/specify_cli/cli/commands/mission_type.py` is in **WP01's** owned_files (it removes the
`governance_refs` display rows at `:1486,1505`). **WP03** also migrates the `resolve_action_sequence`
call-site at `:1477` (+ its import) when it subsumes that function. Two edits, one file, two WPs.

**Resolution (squad-directed):** a **WP01 → WP03 dependency edge** was added. WP01 lands first and leaves
the file quiet; WP03 then makes the `:1477` migration as a **justified out-of-map, sequential** edit (the
file stays out of WP03's owned_files, so `finalize --validate-only` reports no false overlap, while the
dependency edge serializes the two edits). This honours the subsume-and-migrate discipline (C-002 / ADR) —
**no** thin `resolve_action_sequence` wrapper is kept to dodge the edit; **no** caller is operator-deferred.

## Transitional-scaffold ledger (must be empty at merge — NFR-005 / C-002)

| Scaffold | Added in | Deleted in |
|----------|----------|------------|
| sw-dev governance byte-parity | WP03 (T018) | WP03 (same WP, final commit) |
| dossier required-artifact parity | WP10 (T053) | WP10 (T058) |
| step-contract parity | WP11 (T061) | WP11 (T062) |

WP12 (T069) asserts **zero** parity/snapshot scaffolds referencing the removed path survive merge.
