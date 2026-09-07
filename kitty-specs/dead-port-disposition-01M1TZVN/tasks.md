# Work Packages: Dead-Port Disposition

**Inputs**: Design documents from `kitty-specs/dead-port-disposition-01M1TZVN/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ (dsl-retirement, glossary-bootstrap, residue-and-emitter-shrunk), quickstart.md, decisions/ (9 records)

**Tests**: REQUIRED. WP01 is anchored on a RED-on-main import-hygiene ratchet (permanent); WP02 pins the bootstrap contract; every gate edited ships in the same WP as its deletion (NFR-003).

**Mission-level gate (C-001)**: claim NO work package until Mission A `fsm-write-path-integrity-01M1TZV6` has merged into `missions/coreloop-proto-missions`. `spec-kitty next` does not model cross-mission gates; the orchestrator enforces this.

**Gate re-check performed at tasks time (2026-09-06)**: PR #3888 merged (FR-013 unblocked); PR #3898 **merged 16:00Z with the ADR Accepted** → FR-012 executable → **WP05 minted** (decision `tasks.emitter.adr-execution-home`; OD7 superseded); WP03 keeps its shrunk emitter items, which WP05 supersedes; PR #3899 merged 16:00Z (`truststore` dropped; `pyproject.toml`/`uv.lock` moved — WP01 must `uv lock` on top of it).

**Organization**: `Txxx` subtasks roll up into `WPxx` work packages; each WP is independently deliverable. Subtasks are reference rows: record completion with `spec-kitty agent tasks mark-status <Txxx> --status done --mission dead-port-disposition-01M1TZVN`.

## Path Conventions

Single project: `src/specify_cli/`, `src/kernel/`, `src/charter/`, `src/runtime/`, `src/mission_runtime/`, `packs/`, `tests/`. All paths repo-root-relative.

---

## Work Package WP01: Mission-DSL v1 Retirement (FULL) + `transitions` Drop (Priority: P1) 🎯 MVP

**Goal**: Break the eager import block, delete the DSL runtime (FULL), drop the `transitions` dependency, delete the orphan pack DSL blocks, and move every gate pin in the same change.
**Independent Test**: SC-001 ratchet green (subprocess import of `mission_v1.events` loads neither `transitions` nor `six`); SC-002 (`transitions` gone from `pyproject.toml`/`uv.lock`, `six` retained); SC-003 (zero `import transitions` in `src/`); the two live consumers' tests pass unchanged; `tests/architectural/` green.
**Prompt**: `tasks/WP01-dsl-retirement-and-transitions-drop.md`
**Requirement Refs**: FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007, NFR-001, NFR-002, NFR-003, C-004, C-005

### Included Subtasks

T001 Red-first ratchet `tests/specify_cli/mission_v1/test_import_hygiene.py` (subprocess-isolated; RED on main; permanent)
T002 Rewrite `mission_v1/__init__.py`: drop the eager block `:20-29`, delete `MissionProtocol`/`load_mission`/`load_mission_by_name`, re-export `emit_event`/`read_events` only, new docstring (OD4)
T003 Delete `compat.py`, `runner.py`, `guards.py`, `schema.py`; re-point `review/gate_registry.py:7,132` and `skills/manifest_store.py:27` docstrings at git history
T004 Rework the test blast radius: delete the DSL-only test files; TRIM `test_mission_v1_events_unit.py` (`:228-304`) and the schema-validation halves of `tests/research/test_research_plan_missions_integration.py` / `tests/missions/test_mission_software_dev_integration.py`
T005 Same-WP gate edits: drop dead-symbol pins `test_no_dead_symbols.py:720-727` AND `:3278`; drop fold-gate entry `test_wp_frontmatter_fold.py:60`; verify `_gate_coverage.py:1456` row and the runtime ledger row `test_layer_rules.py:194` stay green
T006 [P] Pack-DSL honesty (OD3): delete `states:`/`transitions:` blocks from the three built-in `mission.yaml`s; update the `MISSION_COMPAT_IGNORED_FIELDS` comment (`mission.py:59-67`), tolerance retained
T007 Dependency drop: delete `pyproject.toml:82`, `uv lock`, verify the lock diff (only `transitions`; `six` stays), CHANGELOG entry under `[Unreleased] - 3.2.7rc1`, clean-install smoke, full `tests/architectural/` run once (cross-cutting rule)

### Implementation Notes

- "Both, together, or neither": T002 and T003 land in one commit. The ratchet proves it.
- One dependency change per PR — do not touch `truststore` (PR #3899).

### Parallel Opportunities

T006 is independent of T002–T005.

### Dependencies

None within the mission (C-001 mission-level gate applies).

### Risks & Mitigations

- R2 gate goes red/vacuous → T005 + the full architectural run in T007.
- R3 `uv.lock` conflict with PR #3899 → whichever lands second rebases.

---

## Work Package WP02: Glossary Runner Design-Story Repair (Priority: P2)

**Goal**: Replace the four-site "registered by `specify_cli`/`glossary` at import/startup" fiction with the canonical lazy self-bootstrap contract; pin it with a behaviour test; record the FR-020 enforcement gap honestly.
**Independent Test**: SC-004 grep yields zero registration-by-`specify_cli`/`glossary` phrasing across the four files; the bootstrap-contract test is green; SC-005 note present in code and drafted for #1868.
**Prompt**: `tasks/WP02-glossary-bootstrap-repair.md`
**Requirement Refs**: FR-008, FR-009, FR-010

### Included Subtasks

T008 Rewrite the four sites per `contracts/glossary-bootstrap.md` §2 (`kernel/glossary_runner.py`, `kernel/__init__.py`, `kernel/README.md`, `charter/offering/missions/glossary_hook.py`); optional code-motion helper `_ensure_runner_registered()` (behaviour identical)
T009 Behaviour pins in `tests/doctrine/missions/test_glossary_hook.py`: self-bootstrap registers the concrete runner; degradation only when `glossary.attachment` is unimportable
T010 FR-020 enforcement-honesty `.. note::` in `glossary_hook.py`; tracker-note text for #1868 drafted in `design-notes/WP02-glossary.md` (operator posts); SC-004 grep + terminology guard

### Implementation Notes

- Docs-shaped WP; no behaviour change. Leave the three-link re-export chain alone (US2-4).

### Parallel Opportunities

Independent of WP01/WP03/WP04 (disjoint files).

### Dependencies

None within the mission.

### Risks & Mitigations

- R7 note reads as a wiring promise → wording in the contract §4 says "separate feature decision".

---

## Work Package WP03: Gate-Adjacent Residue + Emitter Slice (SHRUNK) (Priority: P3)

**Goal**: Delete the stale `constitution` exclusion, the `team_projection/` tombstone, the `ActionContext` alias; demote the 13 test-only `__all__` exports with matching re-pins; correct the `event_emitter.py` docstring; extract the FR-011 verified record; draft the emitter-execution follow-up.
**Independent Test**: SC-006 (pins re-pinned, no vacuous entries; open PRs checked against gate files), SC-007 shrunk variant (zero emitter behaviour/name/signature change; parity oracle untouched), SC-008 (`constitution` exclusion absent; landed after #3888).
**Prompt**: `tasks/WP03-residue-and-emitter-shrunk.md`
**Requirement Refs**: FR-011, FR-012, FR-013, FR-014, C-002, C-003, C-006, C-007

### Included Subtasks

T011 Delete `test_layer_rules.py:65-73` (`constitution` exclusion); layer rules green
T012 [P] Delete `src/specify_cli/team_projection/`; verify wheel packages and the absence bans stay green
T013 [P] Delete the `ActionContext` alias (`mission_runtime/context.py:338,:342`; `mission_runtime/__init__.py:127,:139-142`); zero references remain
T014 Demote the 13 test-only `__all__` exports (never delete); repoint test importers to module paths; re-pin `test_no_dead_symbols.py` (out-of-map, sequenced after WP01, rationale logged)
T015 [P] `event_emitter.py:1-10` docstring correction (points at `status/adapters.py:364-366`; no code change); extract `research/emitter-adr-inputs.md` (FR-011) with re-verified anchors; draft the FR-012 follow-up mint text in `design-notes/WP03-residue.md`; re-check PR #3898/#3899 state and record it

### Implementation Notes

- `_BufferingRuntimeEmitter` (`runtime_bridge_retrospective.py:69`) and `tests/runtime/test_bridge_parity.py` are untouchable in the shrunk variant.

### Parallel Opportunities

T012, T013, T015 are independent of T011/T014.

### Dependencies

Depends on WP01 (single owner of `test_no_dead_symbols.py`; WP03 re-pins after WP01's pin drops).

### Risks & Mitigations

- R6 wheel build → `test_pyproject_shape.py` in the blast radius.
- Ledger discipline (C-007) → run `test_runtime_ledger_has_no_stale_entries` after every deletion.

---

## Work Package WP04: `decision.py` Dead DSL Readers (Priority: P3)

**Goal**: Delete `derive_mission_state` and `evaluate_guards` (`runtime/next/decision.py:187-235`) and their legacy tests; nothing else in the file changes.
**Independent Test**: AST/grep proof of zero callers; `tests/next` green; runtime ledger unchanged and green.
**Prompt**: `tasks/WP04-decision-dead-readers.md`
**Requirement Refs**: FR-015, C-001

### Included Subtasks

T016 AST/grep proof: zero callers of `derive_mission_state`/`decision.evaluate_guards` in `src/` (the `runtime_bridge_cores` `evaluate_guards*` family is unrelated); record in the Activity Log
T017 Delete the two functions and the lazy `mission_v1.events.read_events` import at `:200`; delete `tests/next/test_decision_unit.py:28,189-219`; run `tests/next`, `tests/runtime/next`, `test_layer_rules.py`

### Implementation Notes

- Owns `src/runtime/next/decision.py` alone — one of Mission A's four shared files; claim only after Mission A has merged (OD9, C-001).

### Parallel Opportunities

Independent of WP01–WP03 once the mission-level gate is open.

### Dependencies

None within the mission; C-001 mission-level gate.

### Risks & Mitigations

- A leftover consumer of `read_events` in `decision.py` → grep in T016; `next_invocation_lifecycle.py:332` remains the live `events.py` consumer.

---

## Work Package WP05: RuntimeEventEmitter ADR Execution (Priority: P4, minted on ADR acceptance)

**Goal**: Execute the Accepted disposition ADR (PR #3898, merged 2026-09-06): rewire-ready consolidation — one `RuntimeEventEmitter` (the Protocol), a factory returning `NullEmitter` by default with the E3 registration hook, `for_mission` + `seed_from_snapshot` promoted onto the seam, the duplicate concrete class deleted, the buffer flush-target bug fixed on BOTH paths under red-first tests, conformance/parity tests updated. No live producer.
**Independent Test**: the ADR's Confirmation items (1)–(4): exactly one class named `RuntimeEventEmitter` under `src/runtime/next/`; factory + seed capability intact; strict-policy `decision_required` advance appends `DecisionInputRequested` to the decision git log after the flush (both paths); a refused terminal gate writes nothing; bridge-parity and producer-conformance green.
**Prompt**: `tasks/WP05-emitter-adr-execution.md`
**Requirement Refs**: FR-012, C-003, C-006, C-007

### Included Subtasks

T018 Red-first flush-target tests (strict-gated `decision_required` advance; buffered path + composition dispatch path; terminal-gate discard stays green)
T019 Promote `for_mission` + `seed_from_snapshot` onto the seam; factory with E3 registration hook; delete `event_emitter.py`; retype bridge/engine against the Protocol
T020 Fix the flush target (`runtime_bridge.py:2187` → `ctx.emitter_for_engine`; composition path likewise); flip T018
T021 One-pass `sync_emitter` decision; parity/conformance comment updates
T022 [P] Seam-consolidation tests (one class; factory default/minimal-import; registration; seed no-op; identity parity); runtime ledger
T023 Design note with ADR Confirmation evidence; C-009 cleanup

### Dependencies

Depends on WP03 (the FR-011 record and the shrunk docstring, which this WP supersedes). Mission-level C-001 (Mission A merged) applies.

### Risks & Mitigations

- Behaviour change on the strict-gated path (decision events now durably commit) → called out + pinned.
- Ledger red on deleting `event_emitter.py` → same-commit ledger edit.

---

## Dependency & Execution Summary

- **Mission-level gate**: Mission A merged into the branch first (C-001).
- **Sequence**: wave 0 = WP01 ∥ WP02 ∥ WP04; wave 1 = WP03 (after WP01); wave 2 = WP05 (after WP03).
- **Merge order**: WP01 first (gate pins), then WP02/WP04 as they land, then WP03, then WP05.
- **MVP Scope**: WP01 (removes the dependency from the hot path; the mission's bulk).
- ADR execution is now in-mission (WP05); no follow-up mint needed.

---

## Requirements Coverage Summary

| Requirement ID | Covered By Work Package(s) |
|----------------|----------------------------|
| FR-001 | WP01 |
| FR-002 | WP01 |
| FR-003 | WP01 |
| FR-004 | WP01 |
| FR-005 | WP01 |
| FR-006 | WP01 |
| FR-007 | WP01 |
| FR-008 | WP02 |
| FR-009 | WP02 |
| FR-010 | WP02 |
| FR-011 | WP03 |
| FR-012 | WP05 (execution); WP03 (record + docstring, superseded) |
| FR-013 | WP03 |
| FR-014 | WP03 |
| FR-015 | WP04 |
| NFR-001 | WP01 |
| NFR-002 | WP01 |
| NFR-003 | WP01, WP03 |
| C-001 | WP04 (and mission-level) |
| C-002 | WP03 |
| C-003 | WP03, WP05 |
| C-004 | WP01 |
| C-005 | WP01 |
| C-006 | WP03, WP05 |
| C-007 | WP03, WP05 |

---

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|------------|---------|--------------|----------|-----------|
| T001 | Red-first import-hygiene ratchet | WP01 | P1 | No |
| T002 | Rewrite mission_v1/__init__.py | WP01 | P1 | No |
| T003 | Delete DSL modules; re-point docstrings | WP01 | P1 | No |
| T004 | Rework test blast radius | WP01 | P1 | No |
| T005 | Same-WP gate edits | WP01 | P1 | No |
| T006 | Pack-DSL block deletion | WP01 | P1 | Yes |
| T007 | Dependency drop + CHANGELOG + arch run | WP01 | P1 | No |
| T008 | Rewrite four glossary sites | WP02 | P2 | No |
| T009 | Bootstrap behaviour pins | WP02 | P2 | No |
| T010 | FR-020 honesty note + tracker text | WP02 | P2 | No |
| T011 | Delete constitution exclusion | WP03 | P3 | No |
| T012 | Delete team_projection tombstone | WP03 | P3 | Yes |
| T013 | Delete ActionContext alias | WP03 | P3 | Yes |
| T014 | Demote 13 __all__ exports; re-pin | WP03 | P3 | No |
| T015 | Emitter docstring; FR-011 record; follow-up mint | WP03 | P3 | Yes |
| T016 | Zero-caller proof | WP04 | P3 | No |
| T017 | Delete dead readers + legacy tests | WP04 | P3 | No |
| T018 | Red-first flush-target tests | WP05 | P4 | No |
| T019 | Seam promotion + factory + delete duplicate | WP05 | P4 | No |
| T020 | Fix flush target both paths | WP05 | P4 | No |
| T021 | sync_emitter one-pass decision; comments | WP05 | P4 | No |
| T022 | Seam consolidation tests; ledger | WP05 | P4 | Yes |
| T023 | Design note + ADR confirmation | WP05 | P4 | No |
