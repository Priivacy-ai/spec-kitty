# Tasks: Doctrine Delivery Activation Fast-Follow

**Mission**: doctrine-delivery-activation-01KYQVQK · **Branch**: `feat/doctrine-delivery-activation`
**Plan**: [plan.md](./plan.md) · **Grounding**: [pre-planning-ledger.md](./pre-planning-ledger.md) (D1–D19)
**Contracts**: [suggests-delivery-walk.md](./contracts/suggests-delivery-walk.md),
[drg-writer-discovery-gate.md](./contracts/drg-writer-discovery-gate.md)

7 WPs / 3 lanes. Critical path **WP01 → WP02 → WP03**. WP04 branches off WP01; WP05/WP06/WP07 fully
parallel (WP07 land-early to de-flake ATDD). All assertions on the **profile channel**
(`profile_channel_reachable`), never `resolve_context` (D10). Baseline deferred set = 60 (D19).

## Subtask Index (reference table — completion is event-sourced via `mark-status`)

| Task | Description | WP | Parallel |
|------|-------------|----|----------|
| T001 | Add `Relation.SUGGESTS` to `PROFILE_CHANNEL_RELATIONS` (reachability.py) | WP01 | |
| T002 | Profile-channel `when`-projection reusing `link_references(roots=seeds, …)` (progressive_disclosure.py) | WP01 | |
| T003 | Widen kind delivery + profile-render consumer beyond procedures (repository.py/context.py) | WP01 | |
| T004 | Consume forward-API seed helpers cross-file (`agent_profile_seed_urns`, …) | WP01 | |
| T005 | ATDD: profile channel delivers DDD/C4/refactoring with `when`; diamond dedup; action-channel isolation | WP01 | |
| T006 | Family-A `when` backfill (architect/paula/randy → DDD) grounded in existing `reason` | WP02 | |
| T007 | Author C4 `template:instantiates` edge from `action:documentation/design` | WP02 | |
| T008 | Author `anti_pattern` nodes for refactoring-* smells (grounded; defer un-attested) | WP02 | |
| T009 | Author `tactic --REJECTS--> anti_pattern` edges; anti-pattern validator green | WP02 | |
| T010 | Update cardinality/histogram goldens + composition-ledger entries | WP02 | |
| T011 | ATDD: template reaches architect via C4 tactic refs (needs WP01); REJECTS validator | WP02 | |
| T012 | Re-measure via canonical helper; reconcile `_PROFILE_UNREACHABLE`/`_PROFILE_RESCUES`/`_ACTION_UNREACHABLE_D2` | WP03 | |
| T013 | Wiring table deferred 60→lower + Family ledgers + reconcile stale 50/39 prose | WP03 | |
| T014 | Final forward-API allowlist sweep (~2–3 wired) + `_baselines.yaml`; unwired stay noted | WP03 | |
| T015 | Lightweight member-vs-ledger cross-check test; NFR-002 review-gate note | WP03 | |
| T016 | Extract reference-pointer helpers (+ module cache) → context_renderers/reference_pointers.py | WP04 | |
| T017 | Extract delivery-table helpers → context_renderers/delivery_table.py + re-export shim (3 test importers) | WP04 | |
| T018 | Define `ArtifactRepository` Protocol; apply at 12 sites; remove `# type: ignore` (net-removal) | WP04 | |
| T019 | ATDD: context.py consumer tests green (behaviour-preserving); mypy --strict green | WP04 | |
| T020 | Route all 3 document-emit sites through `graph_document_to_dict` (incl. pack_assembler) | WP05 | [P] |
| T021 | Register all document writers in `drg_writers/registry.py` | WP05 | [P] |
| T022 | Author writer-discovery gate (dict-literal AND `.model_dump()` shapes; assert membership) | WP05 | [P] |
| T023 | Self-mutation battery: both shapes red independently (NFR-006) | WP05 | [P] |
| T024 | `except DRGGraphSchemaError → ValidationIssue` at both pack_validator sites | WP06 | [P] |
| T025 | Base `_post_validate` success hook (built-in + overlay); move AssetRepository `_source_paths` there | WP06 | [P] |
| T026 | Fix AgentProfileRepository twin; regression: project-layer validation-failure → `source_path` absent | WP06 | [P] |
| T027 | Fixture excludes/resets `context-state.json`; `first_load` always True | WP07 | [P] |
| T028 | Verify hermeticity across the `test_every_load_delivery` matrix | WP07 | [P] |

---

## WP01 — Profile-channel `suggests` walk + `when` delivery (IC-01, IC-02-consume)

- **Goal**: Extend the profile channel to follow `suggests` and surface each edge's `when` as the delivered
  doctrine's applicability condition (links-not-bodies), so architect/implementer profiles receive the A/B/C/E
  linked doctrine. **THE core delivery vector.**
- **Priority**: P1 (critical path — WP02/WP03/WP04 depend on it) · **Requirements**: FR-001, FR-002, FR-003,
  FR-006(consume); NFR-003 · **Deps**: none
- **Independent test**: `profile_channel_reachable(graph, {agent_profile:architect-alphonso})` +
  the profile render path surfaces `paradigm:domain-driven-design` with its `when` — RED today
  (`test_reachability.py:710`), NEVER via `resolve_context` (D10). See contract `suggests-delivery-walk.md`.
- **Subtasks**: T001, T002, T003, T004, T005
- **Risks**: `when` is on the inbound edge + seeds are stripped → reuse `link_references(roots=seeds)`, no
  re-walk (D11); projection lands in progressive_disclosure sibling, minimal context.py delta (R-M7).
- **Est. prompt size**: ~420 lines

## WP02 — DRG topology authoring: Family-A `when` + C4 template + anti-pattern `REJECTS` (IC-03, IC-04)

- **Goal**: Author the DRG-edge/node topology this mission adds AND own every cardinality/histogram golden it
  moves: Family-A `when` backfill, the C4 `template:instantiates` edge, anti-pattern nodes + `REJECTS` edges.
- **Priority**: P1 · **Requirements**: FR-007, FR-008; C-004, C-005; NFR-002(cardinality goldens) · **Deps**: WP01
- **Independent test**: templates reach the architect via IC-01's suggests-walk to the C4 tactic's references
  (needs WP01); each anti_pattern is a `REJECTS`-target with the anti-pattern validator green; all
  cardinality/histogram goldens green with matching ledger entries.
- **Subtasks**: T006, T007, T008, T009, T010, T011
- **Risks**: no invented smells (C-004) — defer un-attested; `instantiates` walked by no channel → the edge
  is topology completion, delivery rides WP01 (D13); anti_patterns validation-tier, never delivered (D14);
  owns the shared goldens so parallel-WP golden collision is avoided (R-M1).
- **Est. prompt size**: ~480 lines

## WP03 — Reachability reconciliation (terminal) (IC-05)

- **Goal**: Re-measure the profile-reachable set via the canonical helper and reconcile the **reachability**
  goldens (pins + wiring table + final allowlist sweep). Owns ONLY reachability goldens, NOT cardinality (WP02).
- **Priority**: P1 (terminal) · **Requirements**: FR-004, FR-005, FR-006(final); NFR-002, NFR-004 · **Deps**: WP01, WP02
- **Independent test**: `_PROFILE_UNREACHABLE`/`_PROFILE_RESCUES`/`_ACTION_UNREACHABLE_D2` reconciled to the
  measured set; wiring-table deferred set drops below 60; `test_no_dead_symbols` green after the ~2–3 sweep;
  every moved golden has a ledger row.
- **Subtasks**: T012, T013, T014, T015
- **Risks**: NFR-002 pins are REVIEW-gated not CI-gated (D18) — per-member ledger-vs-diff is the sole gate;
  measure ONLY via the helper (C-001); "50"/"39" are stale, baseline 60 (D19).
- **Est. prompt size**: ~360 lines

## WP04 — context.py extraction + `ArtifactRepository` Protocol typing (IC-08, IC-06b)

- **Goal**: Extract the reference-pointer + delivery-table helpers to `context_renderers/` siblings
  (behaviour-preserving) and replace `object`-typed repository surfaces with an `ArtifactRepository` Protocol,
  net-removing the 12 `# type: ignore`.
- **Priority**: P2 · **Requirements**: FR-012, FR-010(typing half); NFR-001, NFR-005 · **Deps**: WP01
- **Independent test**: all context.py consumer tests stay green (byte-identical payloads); `mypy --strict`
  green with the 12 ignores removed and none added.
- **Subtasks**: T016, T017, T018, T019
- **Risks**: reference slice couples to `_REFERENCE_SOURCE_INDEX_CACHE` (move together); delivery slice has
  3 external test importers (re-export shim); `Refs #2532` slice, NOT `Closes` (D8); the 2 progressive_
  disclosure.py ignores are a documented out-of-map type-only edit (WP01 owns that file).
- **Est. prompt size**: ~380 lines

## WP05 — DRG writer registry unify + discovery gate (IC-06a, #3075/#2977)

- **Goal**: Route ALL three document-emit sites (incl. `pack_assembler`) through the canonical
  `graph_document_to_dict`, register each, and author a non-vacuous discovery gate.
- **Priority**: P2 (parallel) · **Requirements**: FR-010(writer half); NFR-006 · **Deps**: none
- **Independent test**: a hypothetical new top-level `DRGGraph` field emits at all 3 sites; the discovery-gate
  self-mutation battery reds independently for a dict-literal AND a `.model_dump()`-shaped unregistered writer.
- **Subtasks**: T020, T021, T022, T023
- **Risks**: NFR-006 non-vacuity — BOTH shapes proven (D-M5); bound the "closes the class" claim; registry is
  fail-open by design. #3075 closes only if WP04's typing half also lands (C-007).
- **Est. prompt size**: ~360 lines

## WP06 — `DRGGraphSchemaError` UX + asset source-path (IC-07, #3062)

- **Goal**: Surface `DRGGraphSchemaError` as a structured `ValidationIssue` during `doctrine validate`; fix the
  asset `_source_paths` split-brain via a base `_post_validate` hook and fix the AgentProfileRepository twin.
- **Priority**: P2 (parallel) · **Requirements**: FR-011 · **Deps**: none
- **Independent test**: a pack with a stray top-level graph key → structured issue (not traceback); a
  project-layer asset that fails validation → `source_path(id)` absent.
- **Subtasks**: T024, T025, T026
- **Risks**: `_post_validate` must fire at BOTH load paths (built-in + overlay, D-M8); base-hook must not
  change other repos' success-path behaviour.
- **Est. prompt size**: ~300 lines

## WP07 — Hermetic delivery-test fixture (IC-09)

- **Goal**: Make `test_every_load_delivery::project` exclude/reset `context-state.json` so `first_load` is
  always True unless the test sets it — eliminate the local-only false-red.
- **Priority**: P2 (parallel, **land early** to de-flake WP01/WP04 ATDD) · **Requirements**: FR-009 · **Deps**: none
- **Independent test**: the suite is green even with an ambient `context-state.json` recording `implement`.
- **Subtasks**: T027, T028
- **Risks**: minimal — `ignore_patterns("context-state.json")` or unlink-after-copy.
- **Est. prompt size**: ~160 lines

---

## MVP scope

WP01 alone (with WP07 landed first to de-flake) is the demonstrable MVP: the profile channel delivers the
inert A/B/C/E doctrine with `when`. WP02→WP03 complete the topology + reconciliation; WP04–WP06 are the
hygiene closures.

## Requirement coverage

FR-001/002/003 → WP01 · FR-004/005 → WP03 · FR-006 → WP01(consume)+WP03(sweep) · FR-007/008 → WP02 ·
FR-009 → WP07 · FR-010 → WP05(writer)+WP04(typing) · FR-011 → WP06 · FR-012 → WP04.
NFR-001 → WP04 · NFR-002 → WP02+WP03 · NFR-003 → WP01 · NFR-004 → WP03 · NFR-005 → WP04+WP05 · NFR-006 → WP05.
