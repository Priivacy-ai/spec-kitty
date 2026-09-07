# Mission Specification: Dead-Port Disposition

**Mission Branch**: `dead-port-disposition-01M1TZVN`
**Created**: 2026-09-06
**Status**: Draft (proto-mission — sliced at spec level; no plan.md or tasks yet; open decisions carried explicitly below)
**Input**: User description: "Retire the dormant mission-DSL and its hot-path `transitions` dependency, repair the glossary-runner design story, and stage the ADR-gated RuntimeEventEmitter cleanup — adjudicating and cleaning the core loop's dead and dormant hook seams."

**Ground truth**: `research/29-missionB-research-dossier.md` (Researcher Robbie, verified at HEAD `e721763759`). Where this spec and the dossier disagree, the dossier wins; flag the drift.

**Sequencing pins (binding)**:
1. This mission runs **AFTER Mission A** `fsm-write-path-integrity-01M1TZV6` — the four shared runtime files (`runtime_bridge_io.py`, `_internal_runtime/engine.py`, `decision.py`, `runtime_bridge_engine.py`) are NOT parallel-safe; no edits to them until Mission A's WPs on them are merged.
2. The `test_layer_rules.py` residue item lands only **after PR #3888** (which modifies `test_layer_rules.py` and `test_runtime_charter_doctrine_boundary.py`) has merged; this mission lands second and rebases trivially.
3. The **RuntimeEventEmitter disposition ADR is an INPUT DEPENDENCY**: it exists as **PR #3898** — `docs/adr/3.x/2026-09-06-2-runtime-event-emitter-disposition.md`, currently `status: Proposed` (PR open). Nothing in this mission decides it; the emitter-execution slice is conditional on that ADR being **merged AND Accepted** by tasks-time (the WP03 gate check).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - `spec-kitty next` stops paying an import tax for a DSL nothing uses (Priority: P1)

As a maintainer, when any agent or operator runs `spec-kitty next`, the runtime should load only what the live loop needs. Today `specify_cli/mission_v1/__init__.py:20-28` (compat at `:20`) eagerly imports **all five** submodules (compat, events, guards, runner, schema), so the live observability import — `runtime/next/next_invocation_lifecycle.py:332` (`emit_event`) — plus the dormant `read_events` site (`runtime/next/decision.py:200`, inside the zero-caller `derive_mission_state` this mission's FR-015 slates for deletion) drags the `transitions` library (plus `six`) into `sys.modules` on every invocation, in service of a state-machine DSL with zero production callers (~1,190 test-only LOC). This story retires the mission-DSL v1 runtime AND breaks the eager import chain — the dossier's proven constraint is "both, together, or neither": deleting files without trimming `__init__` frees nothing; trimming `__init__` without deleting the files leaves the dead code in place.

**Why this priority**: It is the mission's bulk and the only slice that removes a third-party dependency from the hot path of every `spec-kitty next` invocation. It is unconditional (no ADR gate) and independently shippable.

**Independent Test**: In a subprocess-isolated test, `import specify_cli.mission_v1.events` completes with `transitions` and `six` absent from `sys.modules`, while `emit_event`/`read_events` still function for their two live consumers; `transitions` is absent from `pyproject.toml` and `uv.lock`; clean-install CI is green.

**Acceptance Scenarios**:

1. **Given** the current tree (eager block intact), **When** the red-first import-hygiene test runs `import specify_cli.mission_v1.events` in an isolated subprocess and inspects `sys.modules`, **Then** it FAILS (red) — proving the test observes the defect before any change lands.
2. **Given** the retirement has landed, **When** the same test runs, **Then** `transitions` and `six` are absent from `sys.modules` and the test is green — and it remains in the suite as a permanent ratchet against re-eager-ing (an enduring negative invariant, not a disposable parity test).
3. **Given** the retirement has landed, **When** `spec-kitty next` is invoked on a live mission, **Then** the `MissionNextInvoked` observability write (`emit_event`) and the deprecated `derive_mission_state` reader (`read_events`) behave exactly as before — `events.py` survives as live code.
4. **Given** the `transitions>=0.9.2` entry in `[project].dependencies` (`pyproject.toml`) is deleted and `uv lock` regenerated (never hand-edited), **When** the `clean-install-verification` job and `tests/architectural/test_pyproject_shape.py` run, **Then** both pass; `six` remains in the lock via its `python-dateutil` edge.
5. **Given** the settled retirement extent (MIN or FULL — see Open Decisions), **When** the deletion PR lands, **Then** the same PR removes the three dead-symbol pins at `tests/architectural/test_no_dead_symbols.py:719-727`, updates the `_gate_coverage.py:1456` `mission_v1` shard row if `tests/specify_cli/mission_v1/` empties, and (Option FULL only) removes the `("specify_cli.mission_v1.guards", "read_wp_frontmatter")` entry from the fold gate at `tests/specify_cli/test_wp_frontmatter_fold.py:60` — no gate goes red or vacuous.
6. **Given** `tests/missions/test_mission_v1_events_unit.py` imports `runner` at `:228-304`, **When** the blast-radius tests are reworked, **Then** that file is trimmed, not deleted — its events half covers live code.

---

### User Story 2 - A reader of `kernel/glossary_runner.py` is told the truth about who registers (Priority: P2)

As a maintainer reading the kernel glossary-runner seam, I should find documentation that matches the mechanism that actually runs. The registry is **LIVE** (this is a repair, NOT a deletion): the only production `register()`/`get_runner()` path is the lazy self-bootstrap inside `charter/offering/missions/glossary_hook.py:127-137` (`get_runner()` → on `None`, `import_module("glossary.attachment")` → `register(GlossaryAwarePrimitiveRunner)` → retry). Yet four verified sites tell three variants of a fiction — that `specify_cli` (or `glossary`) registers the runner at import/startup time: `kernel/glossary_runner.py:14-16` (+ the stale provider block `:33-38` and pre-relocation dependency diagram), `charter/offering/missions/glossary_hook.py:16-17` (contradicted 111 lines above its own bootstrap at `:127`), `kernel/README.md:18`, and `kernel/__init__.py:38-42`. Separately, the hook's FR-020 claim ("`glossary_check` defaults to enabled") is enforced nowhere in the live mission loop: `execute_with_glossary` has zero production call sites and zero `glossary_check` references exist in `packs/` — the honesty note must say so.

**Why this priority**: The doctrine-layer hook self-bootstrap keeps working either way, but the documented fiction is exactly the rot shape (green tests over an undocumented-in-truth mechanism) that produced the dead-port confusion this mission cleans up. Cheap (docs-shaped, ~0.5 day), independent of every gate.

**Independent Test**: Read the four sites — each describes the self-bootstrap (or the settled alternative, see Open Decisions); run the new behavior test — after `execute_with_glossary` executes with no prior registration, `get_runner()` returns the concrete runner.

**Acceptance Scenarios**:

1. **Given** the four fiction sites at their verified locations, **When** the repair lands, **Then** each documents the real contract per the settled Open Decision — recommendation carried from report 27 (B-WP02): option (a), canonicalize the self-bootstrap — and the "graceful degradation when no runner is registered" story is restated as "degradation only when `glossary.attachment` itself is unimportable".
2. **Given** a fresh process with no prior registration, **When** `execute_with_glossary` runs, **Then** `get_runner()` returns the concrete `GlossaryAwarePrimitiveRunner` — pinned as a behavior test extending `tests/doctrine/missions/test_glossary_hook.py`, turning today's incidental mechanism into a pinned invariant.
3. **Given** the FR-020 enforcement gap (zero production call sites for `execute_with_glossary`; zero `glossary_check` in `packs/`), **When** the repair lands, **Then** an honest record exists in both a code-adjacent note (e.g. a `.. note::` in the hook) and a tracker note on the glossary workstream (#1868) — silently keeping green tests over a dead production path is explicitly rejected.
4. **Given** the optional three-link re-export chain tidy (`charter/offering/missions/__init__.py:10` → `charter/primitives.py:14` → `specify_cli/missions/__init__.py:28`), **When** it would require touching the escalated live-collision pins in `test_no_dead_symbols.py`, **Then** it is skipped — it is optional, never load-bearing.

---

### User Story 3 - Gate-adjacent residue is routed and retired without pin-hash races (Priority: P3)

As a maintainer, the small confirmed-dead residue that couples to this mission's gate files gets cleaned here (once its external gates open), and residue with zero coupling goes to the quick-wins PR — one owner per gate file, no two PRs racing on `test_no_dead_symbols.py` hash pins. The quick-wins PR is **PR #3899** (draft): it covers the scripts/dep/symlink/prose set (CODEOWNERS, CONTRIBUTING symlink, the orphan scripts + their test, `truststore` in pyproject+uv.lock, Makefile/pytest.ini/testing-parallel prose) — the `src/mission_runtime` residue is owned HERE. In scope here: the stale `constitution` exclusion at `test_layer_rules.py:66-74` (the `_EXCLUDED_FROM_LAYER_ENFORCEMENT` frozenset; a package that no longer exists — mission 063 done), sequenced strictly after PR #3888; the 13 un-demoted test-only `__all__` exports (demotion from package `__all__`, never deletion — `content_present_at_primary_tip` and `get_packs_root_default` have in-package src callers); the `team_projection/` tombstone; and the `ActionContext` alias (two files: `mission_runtime/context.py:~338` AND the `__getattr__` block in `mission_runtime/__init__.py:127,139-142`) — all re-routed into this mission's residue slice, since #3899's verified file list does not carry them. Routed to #3899 (not here): `truststore` and the rest of its scripts/dep/symlink/prose scope.

**Why this priority**: Low-risk hygiene that prevents vacuous gates, but valueless if it races another PR on the same gate file; sequencing discipline is the whole story.

**Independent Test**: After #3888 merges and this slice lands, `test_layer_rules.py` carries no exclusion for a nonexistent package; every residue item is traceably placed (this mission, the quick-wins PR, or explicitly deferred) with its gate re-pinned in the same PR.

**Acceptance Scenarios**:

1. **Given** PR #3888 has merged, **When** the `constitution` exclusion at `test_layer_rules.py:66-74` is deleted, **Then** the layer-rules gate stays green and the rebase over #3888's `_RUNTIME_ALLOWED_SPECIFY_CLI` ledger changes is trivial.
2. **Given** the residue-placement decision routes the 13 `__all__` demotions into this mission, **When** they land, **Then** they ride the same PR as this mission's other `test_no_dead_symbols.py` edits, with matching re-pins — never a second concurrent PR on that gate file.
3. **Given** PR #3888 has NOT merged by the time this slice is ready, **When** the mission otherwise completes, **Then** the `test_layer_rules.py` hunk is held back (or minted as a follow-up), not landed first.

---

### User Story 4 - The emitter seam is cleaned exactly as far as the ADR permits — and no further (Priority: P4, CONDITIONAL on the RuntimeEventEmitter disposition ADR)

As a maintainer, the RuntimeEventEmitter confusion — two classes with the same name (`runtime/next/event_emitter.py:23`, a concrete 88-LOC no-op, vs `runtime/next/_internal_runtime/events.py:67`, the live Protocol with `NullEmitter`) — is resolved per the disposition ADR — PR #3898, `docs/adr/3.x/2026-09-06-2-runtime-event-emitter-disposition.md`, currently `status: Proposed`. This mission's unconditional contribution is the **verified record** (safe under ANY disposition): the name-collision map; the 29-occurrence `sync_emitter` map (`runtime_bridge_engine.py` ×16, all annotations under a `TYPE_CHECKING`-only import at `:80`; `runtime_bridge.py` ×13, the sole runtime coupling — import `:195`, `for_feature` `:1552`/`:2739`, `seed_from_snapshot` `:1614`/`:2745`); and the live buffer flush-target defect (buffer swap `runtime_bridge.py:2149-2150`, flush into the inner no-op `ctx.sync_emitter` at `:2187` instead of the `DecisionGitLog`-wrapped `emitter_for_engine` built at `:1560-1565` — recorded, NOT touched). Execution — retire/rewire/merge, any rename, `sync_emitter` signature changes, the flush-target adjudication, the parity-oracle update at `tests/runtime/test_bridge_parity.py:1131-1152` — happens ONLY if the ADR is merged AND Accepted by tasks-time (the WP03 gate); otherwise this slice ships as the shrunk residue-only variant with a docstring correction pointing `event_emitter.py:1-10` at the real E3 seam (`status/adapters.py:364-366`) instead of the false promise.

**Why this priority**: The disposition is owned elsewhere (input dependency); this mission must neither pre-empt it nor lose the verified facts that anchor it. Also gated behind Mission A (both emitter files are Mission-A-adjacent) — triple-gated, hence last.

**Independent Test**: If the ADR landed: its decision is executed with the parity oracle updated in the same PR and no name collision remains. If not: the shrunk variant landed (docstring correction only on the emitter surface) and no emitter behavior, name, or signature changed.

**Acceptance Scenarios**:

1. **Given** the ADR (PR #3898) is merged AND Accepted by tasks-time, **When** its decision is executed, **Then** the name collision is resolved per the ADR, the `sync_emitter` vocabulary/signature pass happens as ONE pass over the 29 sites (not two), the flush-target defect is adjudicated per the ADR (never silently frozen or silently fixed), and `test_side_effect_sinks_are_actually_reached` is updated in the same PR if the capture is removed.
2. **Given** the ADR is NOT merged-and-Accepted by tasks-time, **When** this slice ships, **Then** it contains only the residue items plus the `event_emitter.py:1-10` docstring correction — zero emitter rewiring, deletion, renaming, or signature changes — and the emitter execution is minted as a follow-up mission/WP.
3. **Given** any disposition, **When** work touches `runtime_bridge_retrospective.py`, **Then** `_BufferingRuntimeEmitter` (`:69`) is untouched — it is rollback machinery, the only thing preventing an unretractable `MissionRunCompleted` on a rolled-back terminal advance, and is not deletable under any disposition.
4. **Given** a removal that erases a subpackage's last live `specify_cli` edge, **When** the PR is assembled, **Then** the same PR carries the `test_runtime_ledger_has_no_stale_entries` ledger edit (and respects the widened doctrine-scan baseline pinning `runtime_bridge_io.py`/`runtime_bridge_composition.py` lazy reaches).

---

### Edge Cases

- **ADR outcome is "explicit deferral"**: the P4 slice shrinks to residue + the docstring correction; the emitter execution is minted separately (dossier §6 WP03 gate note; Open Decision 7).
- **The operator answers "yes, mission-DSL v1 is on a roadmap"** (Open Decision 2): P1 converts from retirement to re-justification and the `transitions` pin stays — the mission's bulk re-scopes.
- **`events.py` relocation chosen** (Open Decision 4): the move touches the two runtime lazy imports and the seam test `tests/specify_cli/next/test_next_invocation_lifecycle_seam.py:49` — cheap now, costlier later; if kept in place, the package docstring must stop advertising the deleted DSL.
- **Option FULL chosen but the pack-DSL blocks are kept**: the three `mission.yaml` `states:`/`transitions:` blocks lose their only interpreter (the schema-validation test halves are deleted); keeping them requires the in-file "uninterpreted" comment, and `MISSION_COMPAT_IGNORED_FIELDS` (`mission.py:59-67,260-261`) stays either way for third-party hybrid YAMLs.
- **Mission A's WP05 lane still open at tasks-time**: the two dead DSL readers in `decision.py` (`derive_mission_state:~187`, `evaluate_guards:~218` — zero callers; `runtime_bridge_cores`' `evaluate_guards*` family is an unrelated same-name function) are handed to that lane; otherwise a small follow-up owns `decision.py` alone after A merges (Open Decision 9).
- **Quick-wins PR and this mission both want the 13 `__all__` demotions**: whoever edits `test_no_dead_symbols.py` first takes them — the failure mode being prevented is two PRs racing on the same gate file's hash pins.
- **`test_mission_v1_events_unit.py` deleted wholesale by mistake**: its `:228-304` runner half dies with the DSL, but its events half covers live production code — trim, don't delete.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Break the full eager import block | As a maintainer, I want `specify_cli/mission_v1/__init__.py:20-28` (compat at `:20`) reworked so that importing `mission_v1.events` loads neither `transitions` nor `six` nor the other four submodules — the whole eager block (all five submodules), not two lines. | High | Open |
| FR-002 | Retire the mission-DSL v1 runtime | As a maintainer, I want `runner.py`, `compat.py`, and the `load_mission`/`load_mission_by_name` dispatch deleted (plus `guards.py`/`schema.py` under Option FULL — Open Decision 1) so no dead DSL code remains under the settled extent. | High | Open |
| FR-003 | Preserve the live `events.py` surface | As a runtime consumer, I want `emit_event` and `read_events` to keep working unchanged for `next_invocation_lifecycle.py:332` and `decision.py:200` so the retirement is invisible to the live loop. Note: after FR-015 deletes `derive_mission_state`, the sole live `events.py` consumer is `emit_event` at `next_invocation_lifecycle.py:332`; FR-003's preservation duty then narrows accordingly. | High | Open |
| FR-004 | Red-first import-hygiene ratchet | As a maintainer, I want a subprocess-isolated test — red today — asserting `import specify_cli.mission_v1.events` leaves `transitions` out of `sys.modules`, kept permanently as a ratchet against re-eager-ing. | High | Open |
| FR-005 | Drop the `transitions` dependency | As a maintainer, I want the `transitions>=0.9.2` entry in `[project].dependencies` (`pyproject.toml`) removed and `uv.lock` regenerated via `uv lock` so the dependency leaves the product (`six` stays via `python-dateutil`). | High | Open |
| FR-006 | Rework the DSL test blast radius | As a maintainer, I want the extent-appropriate test files deleted or trimmed (per the dossier §1.3 table; `test_mission_v1_events_unit.py` trimmed, never deleted) so no test imports retired code. | High | Open |
| FR-007 | Pack-DSL honesty | As a pack author, I want the orphan `states:`/`transitions:` blocks in the three built-in `mission.yaml`s either deleted or explicitly commented as uninterpreted (Open Decision 3), with `MISSION_COMPAT_IGNORED_FIELDS` retained, so the packs stop implying a live interpreter. | Medium | Open |
| FR-008 | Repair the four glossary fiction sites | As a reader of the kernel glossary seam, I want `glossary_runner.py:14-16,33-38`, `glossary_hook.py:16-17`, `kernel/README.md:18`, and `kernel/__init__.py:38-42` rewritten to document the real registration mechanism (per Open Decision 5; recommendation: canonicalize the self-bootstrap). | High | Open |
| FR-009 | Pin the bootstrap contract | As a maintainer, I want a behavior test (extending `test_glossary_hook.py`) asserting that after `execute_with_glossary` runs with no prior registration, `get_runner()` returns the concrete runner — the documented contract becomes a pinned invariant. | Medium | Open |
| FR-010 | FR-020 enforcement-honesty record | As an operator, I want an honest record — in-code note plus a tracker note on #1868's glossary workstream — that `glossary_check` "enabled by default" is enforced nowhere in the live mission loop (zero production call sites; zero `glossary_check` in `packs/`). | Medium | Open |
| FR-011 | Verified emitter record as ADR input | As the ADR author, I want the name-collision map, the 29-occurrence `sync_emitter` map, the flush-target defect, and the `spec_kitty_events` 9.1.6 `VOLATILE_EVENT_TYPES` context preserved as verified inputs in a named home — the dossier §3, extracted as `research/emitter-adr-inputs.md` handed to the ADR author (PR #3898) — recorded, never executed ahead of the ADR. | High | Open |
| FR-012 | Execute the landed emitter ADR (CONDITIONAL) | As a maintainer, I want the ADR's disposition executed exactly (collision resolution, `sync_emitter` vocabulary as one pass, flush-target adjudication, parity-oracle update in the same PR) — only if the ADR (PR #3898) is merged AND Accepted by tasks-time; else the shrunk residue-only variant ships (per US4). | Medium | Open |
| FR-013 | Delete the stale `constitution` exclusion | As a maintainer, I want `test_layer_rules.py:66-74` (the `_EXCLUDED_FROM_LAYER_ENFORCEMENT` frozenset entry, excluding a package that no longer exists) removed — strictly after PR #3888 lands. | Low | Open |
| FR-014 | Residue routing with single gate ownership | As a maintainer, I want each residue item placed with single gate ownership: the quick-wins PR #3899 (draft) keeps its verified scripts/dep/symlink/prose scope, while the `src/mission_runtime` residue — the `team_projection/` tombstone, the `ActionContext` alias (2 files), and the 13 `__all__` demotions, none of which are in #3899's file list — rides this mission's gate-editing WP, so no two PRs race on `test_no_dead_symbols.py` hash pins (Open Decision 8). | Low | Open |
| FR-015 | Dispose the `decision.py` dead DSL readers | As a maintainer, I want the two `.. deprecated:: 2.0.0` functions (`derive_mission_state`, `evaluate_guards`) deleted by whichever lane owns the shared file post-Mission-A (Open Decision 9) — never edited in parallel with Mission A. | Low | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Hot-path import hygiene | A subprocess running `import specify_cli.mission_v1.events` finishes with `transitions` and `six` absent from `sys.modules` — asserted by the permanent ratchet test on every CI run. | Performance | High | Open |
| NFR-002 | Clean-install integrity | After the dependency drop, the `clean-install-verification` CI job and `tests/architectural/test_pyproject_shape.py` pass with zero failures. | Reliability | High | Open |
| NFR-003 | No vacuous or orphaned gates | Every architectural gate edited by this mission (`test_no_dead_symbols.py`, `_gate_coverage.py`, `test_wp_frontmatter_fold.py`, `test_layer_rules.py`, the runtime ledger, the parity oracle) is updated in the same PR as the deletion it covers — zero red pins, zero pins asserting on deleted-and-forgotten surfaces. | Maintainability | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Mission-A sequencing | No edits to `runtime_bridge_io.py`, `_internal_runtime/engine.py`, `decision.py`, or `runtime_bridge_engine.py` until Mission A `fsm-write-path-integrity-01M1TZV6`'s WPs on them are merged; the whole mission sequences after Mission A's shared-file lanes. | Technical | High | Open |
| C-002 | PR #3888 sequencing | The `test_layer_rules.py` residue hunk (FR-013) lands only after PR #3888 merges; this mission rebases over it. | Technical | High | Open |
| C-003 | Emitter ADR gate | No emitter rewiring, deletion, renaming, or `sync_emitter` signature change before the RuntimeEventEmitter disposition ADR (PR #3898, `docs/adr/3.x/2026-09-06-2-runtime-event-emitter-disposition.md`, currently `status: Proposed`) is merged AND Accepted; the flush-target defect is record-don't-touch until then. | Technical | High | Open |
| C-004 | Dependency-removal mechanics | the `transitions>=0.9.2` entry in `[project].dependencies` (`pyproject.toml`) deleted; `uv.lock` regenerated with `uv lock`, never hand-edited; version bump in `pyproject.toml` + `CHANGELOG.md` entry (house rule); one dependency change per PR — `truststore` removal belongs to the quick-wins PR #3899 and must not be bundled. | Technical | High | Open |
| C-005 | Same-PR gate edits | The DSL-retirement PR itself removes the three dead-symbol pins at `test_no_dead_symbols.py:719-727`, updates the `_gate_coverage.py:1456` shard row if `tests/specify_cli/mission_v1/` empties, and (Option FULL) the fold-gate entry at `test_wp_frontmatter_fold.py:60`. | Technical | High | Open |
| C-006 | Rollback machinery is untouchable | `_BufferingRuntimeEmitter` (`runtime_bridge_retrospective.py:69`) is not deletable under any disposition. | Technical | High | Open |
| C-007 | Runtime-ledger discipline | Any removal erasing a subpackage's last live `specify_cli` edge carries the `test_runtime_ledger_has_no_stale_entries` ledger edit in the same PR; the widened doctrine-scan baseline's pins on `runtime_bridge_io.py`/`runtime_bridge_composition.py` lazy reaches are respected. | Technical | Medium | Open |

### Key Entities

- **mission-DSL v1** (`src/specify_cli/mission_v1/`): five submodules; only `events.py` (93 LOC) is production-live; `runner.py`/`compat.py` hold the only `import transitions` lines in the tree; ~1,190 test-only LOC total.
- **`transitions` dependency**: the `transitions>=0.9.2` entry in `[project].dependencies` (`pyproject.toml`), lock `0.9.3` with a `six` edge; loaded on every `spec-kitty next` via the eager chain.
- **Kernel glossary registry** (`kernel/glossary_runner.py` + `glossary_hook.py`): LIVE via lazy self-bootstrap; its documented registration story is fiction at four sites; FR-020 enforcement is a documented-but-unwired claim.
- **RuntimeEventEmitter (×2)**: concrete no-op (`event_emitter.py:23`) vs live Protocol (`_internal_runtime/events.py:67`); disposition owned by the pending ADR.
- **Gate-adjacent residue**: stale `constitution` exclusion; 13 test-only `__all__` exports (demotion-only); `team_projection/` tombstone and `ActionContext` alias (owned HERE — not in quick-wins PR #3899, whose scope is the scripts/dep/symlink/prose set incl. `truststore`).

## Open Decisions *(decision log — dossier §7; the specify interview is past — each decision carries its routing)*

1. [NEEDS DECISION: **DSL retirement extent — MIN vs FULL** (§1.3) — **BLOCKS-PLANNING**; recorded working default: **FULL** (planning proceeds on it). Delete `guards.py`/`schema.py` too? Randy says FULL; Alphonso (report 24) keeps `guards.py` as shape-precedent — but the precedent is docstring prose that could cite git history instead. FULL forces the fold-gate edit (`test_wp_frontmatter_fold.py:60`) and kills the pack-DSL validator tests. Recommendation on the table: FULL, with `gate_registry.py` docstrings re-pointed at history.]
2. [NEEDS DECISION: **Is mission-DSL v1 on any roadmap?** — **OPERATOR-ONLY, no default recorded.** A "yes" converts the P1 slice from retirement to re-justification and keeps the `transitions` pin.]
3. [NEEDS DECISION: **Pack DSL blocks** (§1.4) — delete the orphan `states:`/`transitions:` blocks from the three `mission.yaml`s, or keep-with-comment naming them uninterpreted? Does `MISSION_COMPAT_IGNORED_FIELDS` stay as third-party tolerance either way (recommended: yes)?]
4. [NEEDS DECISION: **`events.py` future home** — stays as `specify_cli.mission_v1.events` (a one-module package whose name outlives its DSL), or relocates (e.g. under `status`/`mission_metadata`)? Relocation touches the two runtime lazy imports and the seam test at `test_next_invocation_lifecycle_seam.py:49` — cheap now, costlier later. If kept, does the package docstring get rewritten to stop advertising the deleted DSL?]
5. [NEEDS DECISION: **Glossary contract choice** (§2) — (a) canonicalize the self-bootstrap (docs-only; recommended by report 27) or (b) mint a real registration seam in `specify_cli` with the bootstrap as fallback (design change, no current driver)? And who owns the FR-020 honesty follow-through — a tracker note only, or does Mission C's design-codification arc absorb it?]
6. [NEEDS DECISION: **Wire-or-retire for `execute_with_glossary` itself** — **OPERATOR-ONLY, no default recorded.** Explicitly out of this mission (Non-goal 3), but the operator must confirm they accept "documented-but-unwired" as the steady state, else mint the feature issue now.]
7. [NEEDS DECISION: **ADR timing** — the ADR is PR #3898 (`docs/adr/3.x/2026-09-06-2-runtime-event-emitter-disposition.md`, currently `status: Proposed`); the WP03 gate check at tasks-time is "ADR merged AND Accepted" — self-resolving then. If not merged-and-Accepted, does the P4 slice ship as the shrunk residue-only variant with the emitter execution minted as a follow-up mission/WP?]
8. [NEEDS DECISION: **Residue placement** — the quick-wins PR is #3899 (draft), covering the scripts/dep/symlink/prose set; its verified file list carries NONE of the `src/mission_runtime` residue. Recorded default (planning proceeds on it): `team_projection`, `ActionContext`, AND the 13 `__all__` demotions ride this mission's gate-editing WP — which also dissolves the `test_no_dead_symbols.py` hash-pin race, since #3899 edits no gate file. Operator may still re-route them onto an extended #3899.]
9. [NEEDS DECISION: **`decision.py` dead-reader ownership** — Mission A WP05 lane (if still open at tasks-time), or a small Mission B follow-up that owns the file alone after A merges?]

## Non-Goals *(verbatim from dossier §5)*

1. **No emitter rewiring, deletion, renaming, or `sync_emitter` signature changes before the disposition ADR lands.** Mission B may carry the ADR's *execution* as a late WP only if the ADR has landed by tasks-time; otherwise that WP is minted separately.
2. **No touches to Mission A's surfaces**: `status/emit.py`, `coordination/status_transition.py` / `transaction.py`, `status/aggregate.py`, the writer census, dependency gating, lock work — and no parallel edits to the four shared files (`runtime_bridge_io.py`, `_internal_runtime/engine.py`, `decision.py`, `runtime_bridge_engine.py`) until Mission A's WPs on them are merged.
3. **No wiring of `execute_with_glossary` into the live step executor** (feature work, unowned).
4. **No adjudication of `_internal_runtime/{emitter,lifecycle,models}.py` frozen re-exports** (Category-6 contract renegotiation, shared-package-boundary owner).
5. **No `doctrine.py` shim deletion** (on schedule for 3.3.0 per shim-registry).
6. **No `truststore` removal here** (quick-wins PR #3899 owns it).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Importing `specify_cli.mission_v1.events` in an isolated subprocess leaves `transitions` (and `six`) out of `sys.modules` — the ratchet test is green and permanent in the suite.
- **SC-002**: `transitions` is absent from `pyproject.toml` and `uv.lock`; `six` remains via `python-dateutil`; the `clean-install-verification` CI job and `test_pyproject_shape.py` are green.
- **SC-003**: Zero `import transitions` (or `from transitions import`) lines remain anywhere in `src/`; the retired LOC matches the settled extent (~530 LOC MIN, ~1,190+ LOC FULL, per the §1.3 table); the two live consumers (`next_invocation_lifecycle.py:332`, `decision.py:200`) pass their existing tests unchanged.
- **SC-004**: All four glossary fiction sites describe the settled registration contract; the bootstrap-contract behavior test is green; a grep across the four named files yields zero matches for register-at-import/startup phrasing (the primary, greppable check), with human review of the four sites as secondary.
- **SC-005**: The FR-020 honesty record exists in both the code-adjacent note and the #1868 tracker note.
- **SC-006**: The three dead-symbol pins (`test_no_dead_symbols.py:719-727`) are gone; every gate this mission touched is green with no vacuous entries; the operable race rule held — whoever edits `test_no_dead_symbols.py` first takes the demotions, and this mission checked open PRs against its gate files at PR-assembly time.
- **SC-007**: The emitter slice matches its gate state exactly — ADR (PR #3898) merged AND Accepted: decision executed, collision gone, parity oracle updated in the same PR; ADR not merged-and-Accepted: only the residue + the `event_emitter.py:1-10` docstring correction shipped, with zero emitter behavior/name/signature changes.
- **SC-008**: The `constitution` exclusion is absent from `test_layer_rules.py` and landed after PR #3888 — never before.

## Cross-References

- **#1868** — parent candidate epic for this mission (glossary-workstream tracker notes land there).
- **#2173** — infra-logic separation epic (context for the port/seam discipline this mission enforces).
- **PR #3888** — open PR touching `test_layer_rules.py` / `test_runtime_charter_doctrine_boundary.py`; hard sequencing gate for FR-013.
- **RuntimeEventEmitter disposition ADR** — **PR #3898**, `docs/adr/3.x/2026-09-06-2-runtime-event-emitter-disposition.md`, currently `status: Proposed` (PR open); input dependency of the P4 slice (C-003, FR-011/FR-012); tasks-time gate: merged AND Accepted.
- **PR #3899** — the quick-wins PR (draft), covering the scripts/dep/symlink/prose set (incl. `truststore`); the `src/mission_runtime` residue is owned by this mission (US3/FR-014/Open Decision 8).
- **Mission A** — `fsm-write-path-integrity-01M1TZV6`; sequencing gate C-001.
- **Missions C and D** — planned-but-unminted (no kitty-specs entry, no tracker issue); the obligations recorded here are self-contained regardless.
- **Evidence chain** — `work/post-convergence/19`–`29` (reports 20, 21, 24, 25, 27 are the dossier's sources; 27 is the after-action debrief; 29 is copied into this mission at `research/29-missionB-research-dossier.md`). The in-mission dossier fully subsumes those session reports: the `work/post-convergence/` files are session-local provenance only (gitignored, machine-local, untracked) and are NOT required to plan or implement — refinement needs only the dossier.
