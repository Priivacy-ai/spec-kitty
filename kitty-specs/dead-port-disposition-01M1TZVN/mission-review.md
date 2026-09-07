# Mission Review Report: dead-port-disposition-01M1TZVN

**VERDICT: PASS WITH NOTES — CRITICAL 0 · HIGH 0 · MEDIUM 2 · LOW 11**

**Reviewer**: Claude (Fable 5.1), post-merge mission review per `spec-kitty-mission-review` skill
**Date**: 2026-09-07
**Mission**: `dead-port-disposition-01M1TZVN` — Dead-Port Disposition (Mission B, `software-dev`, `mission_id 01M1TZVNQZKCQFX3NVJ8DKXN78`)
**Baseline commit**: `1ceba9f22` (tree before Mission B's lanes were cut; Mission A merged; `base_commit` of every WP prompt). Note: `meta.json.baseline_merge_commit` = `ebde0e1cb` is the acceptance-artifact commit, not the code baseline — the diff anchor used here is `1ceba9f22` as instructed.
**Squash merge**: `9938351ac` · **Post-merge repair**: `e9794ddea` (`tests/_next_shard_map.py` +2 lines) · **HEAD at review**: `e9794ddea198cb9cc32f5f4ad03edb1922b34a74` (`missions/coreloop-proto-missions`)
**WPs reviewed**: WP01–WP05 (all `done` via `merge` actor at 22:40Z; `spec-kitty agent tasks status` → 5/5 completed, 0 rejection cycles, 0 forced transitions, 0 `ReviewerSelfApproval`; every `approved` transition by `role: reviewer, tool: user`)
**Diff shape**: `1ceba9f22..HEAD` = 112 files, +2977 / −5647; `1ceba9f22..9938351ac` = 110 files, +2847 / −5647; the five commits after the squash change only `kitty-specs/…` ledgers, `retrospective.yaml`, and the shard map.

> **Review-environment caveat.** During this review another session was concurrently modifying the main checkout (uncommitted edits to `docs/changelog/CHANGELOG.md`, `src/specify_cli/mission_v1/{__init__,events}.py`, `tests/missions/test_mission_v1_events_unit.py`, `tests/specify_cli/next/test_next_invocation_lifecycle_seam.py` — a `read_events` → `_read_events` rename in flight; not mine). Every `git diff` / `git show` fact below is anchored at committed HEAD `e9794ddea` and is unaffected. The live-tree test runs recorded under Gate Results may have overlapped that edit window; the working tree was clean (`git status`) when the review started.

---

## Gate Results

### Gate 1 — Contract tests
- Command: `SPEC_KITTY_ENABLE_SAAS_SYNC=1 PWHEADLESS=1 timeout 600 .venv/bin/pytest tests/contract/ -q -p no:cacheprovider -n 3 --dist loadfile`
- Exit code: 0
- Result: **PASS** — 245 passed, 10 skipped, 24.75 s.
- Notes: the one warning is the pre-existing `doctrine` → `charter.offering` shim `DeprecationWarning` (Non-goal 5 says the shim stays until 3.3.0).

### Gate 2 — Architectural tests
- Command (this review, targeted): `PWHEADLESS=1 timeout 600 .venv/bin/pytest tests/architectural/{test_no_dead_symbols,test_layer_rules,test_no_inert_schema_slots,test_ratchet_baselines,test_mission_runtime_surface,test_no_retired_subsystems,test_pyproject_shape,test_no_legacy_terminology,test_arch_shard_marker_completeness,test_gate_remedy_presence,test_shared_package_boundary,test_ruff_format_enforcement,test_runtime_charter_doctrine_boundary}.py -q -p no:cacheprovider -n 3 --dist loadfile` → **213 passed**, exit 0 (includes the shard-marker gate that `e9794ddea` repaired).
- Full-directory run (orchestrator, post-merge, relied on here rather than re-swept): 1825 passed / 2 failed — (a) `test_golden_count_ban::test_convert_sites_do_not_exceed_frozen_baseline` = pre-existing baseline red attributed at `135f1430b` (CLAUDE.md baseline-red category 1; not this mission's, not green-washed); (b) the `tests/_next_shard_map.py` miss for WP05's two new `tests/runtime/` files, fixed in `e9794ddea` and re-verified green above.
- Result: **PASS** (one attributed pre-existing red, zero mission-caused reds).
- Notes: Gate non-vacuity checked separately — see FR-004 falsification under NFR-003 below and `RISK` section; no `# noqa` / `# type: ignore` added anywhere in `src/` by this mission (`git diff 1ceba9f22..HEAD -- src | grep -n "noqa\|type: ignore"` on `+` lines → none).

### Gate 3 — Cross-repo E2E
- Command: not executable — no `spec-kitty-end-to-end-testing` checkout exists under `/Users/robert/spec-kitty-dev/` or as a sibling of this repo (`ls | grep -i "end-to-end\|e2e"` → nothing).
- Exit code: n/a
- Result: **NOT RUN** — no `kitty-specs/dead-port-disposition-01M1TZVN/mission-exception.md` exists either.
- Notes: the mission claims no cross-repo behaviour (deletions, an internal runtime seam consolidation, doc repairs; `status/`, `coordination/`, tracker and sync surfaces untouched — see Non-goal 2 check). Strictly per the skill this gate is unresolved; recorded as an open operator item (FU-01) rather than a FAIL because there is no failing scenario and no e2e surface was touched. Run the four floor scenarios before tagging.

### Gate 4 — Issue Matrix
- File: `kitty-specs/dead-port-disposition-01M1TZVN/issue-matrix.json` (schema_version 1)
- Rows: 7 (`#1868`, `#3285`, `#3888`, `#3898`, `#3899`, `#3904`, `#3913`)
- Empty / `unknown` verdicts: 0 — verdicts are `deferred-with-followup` ×5, `verified-already-fixed` ×2; no `in-mission` survivor.
- `deferred-with-followup` rows missing a follow-up handle: 0 — `#1868` names the WP02 design-note text the operator posts; `#3285` names "file an upstream gap issue (restore or delete the orphaned inert-slots owner gate)"; `#3898` names the follow-up mint; `#3899` names the rebase rule; `#3913` names itself.
- Result: **PASS**, with staleness notes: the `#3898` `evidence_ref` still describes the pre-WP05 world ("emitter execution minted as a follow-up once the ADR is merged and Accepted") although WP05 executed it in-mission; `#3899` still says "draft" (merged 15:59:58Z); four rows carry the scaffold placeholder `title: "<fill at WP-implementation time>"` (RISK-7).

---

## FR Coverage Matrix

Every FR was traced spec → WP → test → diff. "ADEQUATE" means the test constrains the production path (would fail if the implementation were reverted); evidence is the concrete file at HEAD.

| FR ID | Description (brief) | WP | Test file(s) at HEAD | Adequacy | Finding |
|---|---|---|---|---|---|
| FR-001 | Break the eager import block | WP01 | `tests/specify_cli/mission_v1/test_import_hygiene.py::test_events_import_loads_only_the_package_and_events` | ADEQUATE — falsified: re-eagering a sibling submodule in a scratch worktree → `1 failed` | — |
| FR-002 | Retire DSL v1 runtime (FULL, OD1/OD2) | WP01 | `test_import_hygiene.py` (both); `test_no_dead_symbols.py` (pins dropped, no residual `mission_v1` pin); `grep -rn "transitions" src --include='*.py' \| grep import` → only `specify_cli.status.transitions` (unrelated module) | ADEQUATE | — |
| FR-003 | Preserve live `events.py` surface | WP01 | `tests/specify_cli/next/test_next_invocation_lifecycle_seam.py`; `tests/missions/test_mission_v1_events_unit.py` (trimmed); `events.py` byte-identical at HEAD (not in diff stat) | ADEQUATE for `emit_event`; `read_events` now has **zero** production callers (WP04 deleted the last one) | RISK-1 |
| FR-004 | Red-first import-hygiene ratchet | WP01 | `test_import_hygiene.py` (subprocess-isolated, hermetic `PYTHONPATH=src`, 120 s timeout) | ADEQUATE — falsified twice (see NFR-003) | — |
| FR-005 | Drop `transitions` dependency | WP01 | `tests/architectural/test_pyproject_shape.py`; `git diff uv.lock` names → `-name = "transitions"` / `-version = "0.9.3"` only; `pyproject.toml:81` line removed | ADEQUATE | — |
| FR-006 | Rework DSL test blast radius | WP01 | 8 files deleted (`tests/missions/test_{e2e_mission_v1_integration,mission_guards_integration,mission_loading_integration,mission_v1_compat_unit,mission_v1_guards_unit,mission_v1_runner_unit,mission_v1_schema_unit}.py`, `tests/specify_cli/mission_v1/test_guards_bulk_edit.py`); 3 trimmed; `[tool.ruff.format].exclude` entries pruned | ADEQUATE | — |
| FR-007 | Pack-DSL honesty (OD3 delete) | WP01 | `packs/built-in/missions/{software-dev,plan,research}/mission.yaml` block-only deletions; `MISSION_COMPAT_IGNORED_FIELDS` retained (`mission.py:62`, applied at `:265`); live-loader probe (this review) loads all copies | PARTIAL — the built-ins are honest; two other copy sets still carry the blocks | DRIFT-1 |
| FR-008 | Repair four glossary fiction sites | WP02 | `tests/doctrine/missions/test_glossary_hook.py::TestDesignStory` (SC-004 regex over the 4 sites, RED on base 10/23) | ADEQUATE | DRIFT-2 (doc claim vs code) |
| FR-009 | Pin the bootstrap contract | WP02 | `::TestSelfBootstrapContract::test_execute_with_glossary_self_bootstraps_registry` (real `execute_with_glossary`, `clear_registry()` autouse) | ADEQUATE | — |
| FR-010 | FR-020 enforcement-honesty record | WP02 | `::test_hook_carries_the_fr020_enforcement_honesty_note`; `.. note::` at `glossary_hook.py:27-37`; #1868 text in `design-notes/WP02-glossary.md §6` | ADEQUATE (code side); tracker post is an operator action, unverified here | FU-05 |
| FR-011 | Verified emitter record as ADR input | WP03 | `research/emitter-adr-inputs.md` (16-row re-verification table) | ADEQUATE as a record; header still reads "recorded, not executed"; T023's "executed by WP05" marker not applied | DRIFT-3 |
| FR-012 | Execute the landed emitter ADR (conditional → executed) | WP05 (+WP03 shrunk items superseded) | `tests/runtime/test_decision_flush_target.py` (3 pins, real `DecisionGitLog`, asserts on `decisions.events.jsonl`); `tests/runtime/test_emitter_seam_consolidation.py` (16 pins); `tests/runtime/test_bridge_parity.py` untouched | ADEQUATE — reviewer proved discrimination by reverting both fix sites (2/3 fail) | RISK-3, RISK-6, DRIFT-4 |
| FR-013 | Delete stale `constitution` exclusion | WP03 | `tests/architectural/test_layer_rules.py::TestLayerCoverage::test_layer_exclusions_name_existing_packages` (new, RED on base); set now `frozenset()` | ADEQUATE | — |
| FR-014 | Residue routing, single gate ownership | WP03 | `tests/mission_runtime/test_facade_demotions.py` (3 classes); `test_mission_runtime_surface.py::test_public_surface_is_exactly_all` (list now asserted, 42→31); `test_no_retired_subsystems.py` package-level `team_projection` ban; `tests/doctrine/missions/test_models.py::TestMissionOrchestrationFamilyRetired`; `tests/doctrine/test_schema_validation.py::test_mission_schema_has_no_orchestration_state_machine` (rider T014b) | ADEQUATE | RISK-4, RISK-5 |
| FR-015 | Dispose `decision.py` dead DSL readers | WP04 | `tests/next/test_decision_unit.py` legacy section deleted; `tests/next/test_query_mode_unit.py:39-45` undocumented consumer deleted; AST zero-caller proof in Activity Log; grandfathered rows pruned in WP05 step 0 (`test_no_dead_symbols.py` diff `-runtime.next.decision::…` ×2) | ADEQUATE | — |
| NFR-001 | Hot-path import hygiene | WP01 | `test_import_hygiene.py::test_events_import_does_not_load_transitions` | ADEQUATE — falsified: `import six` appended to `mission_v1/__init__.py` in a scratch worktree → `AssertionError: hot path loaded: six` | — |
| NFR-002 | Clean-install integrity | WP01 | `test_pyproject_shape.py` green (Gate 2); WP01 Activity Log records a throwaway-venv `uv sync --frozen --all-extras` smoke (`transitions installed False`, `six True`) | ADEQUATE (CI job not re-run here) | — |
| NFR-003 | No vacuous/orphaned gates | WP01, WP03 | dead-symbol gate: 0 residual pins for `mission_v1`/`team_projection`/`ActionContext`/`MissionOrchestration*`/`decision::derive_mission_state`/`decision::evaluate_guards`/`event_emitter`; duplicate `SymbolKey`s (6) are the pre-existing Category-B/C overlap, not mission-introduced; fold gate re-pointed at two live consumers (D-8) instead of an empty parametrize; `_PUBLIC_SURFACE` now asserted | ADEQUATE | RISK-4 (one kept-but-unverified row) |

Constraints: **C-001** honoured (all WPs claimed 18:33Z+, after Mission A merged at `1ceba9f22`); **C-002** honoured (#3888 present as `c0054153b`); **C-003** honoured (ADR merged+Accepted 15:59:54Z before WP05 was minted 16:33Z); **C-004** honoured (one dependency change, `uv lock` regenerated, CHANGELOG entry, no version bump — rc cycle open); **C-005** honoured (all four pins + fold-gate entry moved in WP01); **C-006** honoured (`runtime_bridge_retrospective.py` not in the diff stat; `_BufferingRuntimeEmitter:69` intact, only its flush *target* changed at the call site); **C-007** honoured (no ledger edit needed; `test_runtime_ledger_has_no_stale_entries` green in Gate 2).

---

## Answers to the seven targeted probes

1. **FR-003/FR-004 — is the ratchet load-bearing?** Yes. Two falsifications in a throwaway `git worktree` at HEAD (removed afterwards): (a) appending `import six` to `src/specify_cli/mission_v1/__init__.py` → `test_events_import_does_not_load_transitions` FAILS (`hot path loaded: six`); (b) adding `_zombie.py` and re-eagering it from `__init__` → `test_events_import_loads_only_the_package_and_events` FAILS. A re-introduced `transitions` import via `mission_v1/__init__.py` would additionally hard-fail the subprocess (`check=True`) because `transitions` is no longer installed. **Limit**: the ratchet is scoped to `import specify_cli.mission_v1.events` (exactly NFR-001's wording); a `transitions` import re-introduced elsewhere on the `spec-kitty next` hot path (e.g. `next_invocation_lifecycle.py` itself) would be caught only by the dependency being absent from `pyproject.toml`/clean-install, not by this test.
2. **FR-007 — do the packs still load; do the overrides diverge?** All three built-ins load through `specify_cli.mission.Mission` and `MissionTemplateRepository.get_mission_config` (probe in this review); the `_internal_runtime.schema.load_mission_template_file` loader rejects every copy identically (`mission.key` missing) regardless of DSL keys — it is not that file's loader, so no regression. The divergence is real: `.kittify/overrides/missions/{plan,research,software-dev}/mission.yaml` (this repo's own overrides, which `runtime/resolver.py:778-801` prefers over the pack) **and** the packaged copies `src/specify_cli/missions/{plan,research,software-dev}/mission.yaml` (seeded into consumer projects by `m_0_6_7_ensure_missions.py:175-190`) still carry `states:`/`transitions:`. No code path notices because `MISSION_COMPAT_IGNORED_FIELDS` strips them at `mission.py:265`. → DRIFT-1.
3. **FR-012 — any third call site flushing to the old target?** No. `grep -rn "\.flush(" src/runtime src/specify_cli/{events,status}` → exactly one buffer flush, `runtime_bridge.py:2202: buffer.flush(ctx.emitter_for_engine)`; the composition path passes `sync_emitter=ctx.emitter_for_engine` at `:1985`; the engine's third seed site (`runtime_bridge_engine.py:344`) now receives the wrap, which is why `DecisionGitLog.seed_from_snapshot` (`events/decision_log.py:166`) was added. `answer_decision_via_runtime` (`:2754-2775`) seeds the inner emitter then wraps — pre-existing and correct.
4. **Rider T014b — did the schema regeneration drop anything besides `orchestration`?** No. `git diff 1ceba9f22..HEAD -- src/charter/offering/schemas/` touches only `mission.schema.yaml`: −62/+0 = `required: - orchestration`, `properties.orchestration`, and the three definitions `mission_orchestration` / `mission_state_object` / `mission_transition`. `PYTHONPATH=src .venv/bin/python scripts/generate_schemas.py --check` → OK for every schema. The rider was **justified** (WP01's four owned baseline rows promised `delete-the-declaration`; the family had no constructor in `src/`/`tests/`/`scripts/`; `mission.schema.yaml` has no runtime validator consumer — only agent-profile/directives/styleguides/tactics/toolguides/paradigms load their schemas) and **correctly bounded** (diff limited to `models.py`, `generate_schemas.py`, the schema, both pin categories, 14 baseline rows, the `_baselines.yaml` counts, `_inert_slots.py::MAX_UNASSIGNED_ENTRIES`, and five in-family fixtures). Two things it did not do: record the decision-record inaccuracy correction anywhere but the design note, and note in the CHANGELOG that a published schema lost a REQUIRED key (breaking for any external consumer of `mission.schema.yaml`) → DRIFT-4.
5. **`sync_emitter` name kept after the sync transport was retired (#115).** 30 occurrences in 2 files (`runtime_bridge.py`, `runtime_bridge_engine.py`) plus the frozen `DecideNextContext.sync_emitter` field and the engine kwarg. Not a `feature*` alias (Terminology Canon is not violated) and `test_no_retired_subsystems.py` bans import prefixes, not identifiers, so no gate fires. It is retired-vocabulary residue on a live seam, deferred with a recorded rationale (WP05 design note §4.5, prompt item 6 allowed it); the follow-up issue the WP05 reviewer said consolidation owes is not in the issue matrix → RISK-3.
6. **`test_no_dead_symbols.py` coherence across WP01/WP03/WP05.** Final file is coherent: the diff is exactly −3 `mission_v1` pins, −1 `strip_v1_keys` row, −3 orchestration-family pins in each of Categories B and C, the `Mission` hash refreshed in both (`15e9ee0f…` → `36ecefcd…`), −2 `runtime.next.decision::` grandfathered rows. Zero residual pins name a retired symbol; 299 `SymbolKey` pins / 292 unique, the 6 duplicates being the by-design B/C overlap that already existed at baseline. The gate is non-vacuous: `test_no_public_symbol_in_all_is_unimported` was shown RED by WP03/WP05 when rows were pruned prematurely (design notes WP03 §6, WP05 §5).
7. **Analysis-report "fold at next spec touch" (I2, I4, I5).** `spec.md` was **not** touched after the analysis (`git log 1ceba9f22..HEAD -- …/spec.md` → empty) and is now stale relative to what shipped in more ways than the report listed: header "Status: Draft … no plan.md or tasks yet"; sequencing pin 2 / C-002 "PR #3888 … currently open"; C-003/FR-012/US4/OD7 describe the ADR as `Proposed` and the emitter slice as "shrunk residue-only" although WP05 executed it; C-005/SC-006 list three pins (four moved); Open Decisions 1–9 presented as open (all resolved in `decisions/`); FR-003's "two live consumers" (one after WP04); no mention of rider T014b or WP05. → DRIFT-3.

---

## Drift Findings

### DRIFT-1: FR-007 realized only on the built-in packs — two other copy sets still carry the dead DSL blocks, one of them preferred by the resolver

**Type**: PUNTED-FR (partial) / spec-intent gap
**Severity**: MEDIUM
**Spec reference**: FR-007 ("so the packs stop implying a live interpreter"), US1 edge case "Option FULL chosen but the pack-DSL blocks are kept", OD3
**Evidence**:
- `.kittify/overrides/missions/{plan,research,software-dev}/mission.yaml` — top-level `states:` (`:9/:9/:12`) and `transitions:` (`:29/:29/:32`) present at HEAD; untouched by the diff.
- `src/specify_cli/missions/{plan,research,software-dev}/mission.yaml` — same keys present; untouched.
- `src/specify_cli/runtime/resolver.py:778-806` — resolution order `.kittify/overrides/missions/{name}/mission.yaml` → `.kittify/missions/{name}` (legacy) → org/global → built-in: the override copy **wins** in this repo.
- `src/specify_cli/mission.py:73-85, :509, :831` — `_packaged_missions_dir()` (the `src/specify_cli/missions` copies) is a live fallback and the "built-in" origin label; `src/specify_cli/upgrade/migrations/m_0_6_7_ensure_missions.py:175-190` seeds consumer `.kittify/missions/` from those packaged copies.
- `tests/next/test_plan_mission_runtime.py:301-304` asserts the packaged research copy **has** `states` — a test pinning the residue.
- WP01 design note D-10 flagged both copy sets as "outside WP01's owned files … flagged as residue for a follow-up"; no owner was assigned in tasks.md, the issue matrix, or the retrospective.

**Analysis**: The spec scoped FR-007 to "the three built-in `mission.yaml`s", so this is not a violation of the letter; it is a gap against the stated intent. After this mission the tree ships three copies of the same three missions in two shapes: the pack copy (honest) and two DSL-bearing copies, one of which this repository's own runtime actually reads. `MISSION_COMPAT_IGNORED_FIELDS` makes the divergence invisible to every loader, which is exactly the "green over an undocumented mechanism" shape the mission set out to remove. The residue also keeps `mission:`/`initial:`/`guards:`/`inputs:`/`outputs:` and the `# v1 State Machine Definition` header in the built-ins (D-10, block-only rule honoured).

### DRIFT-2: The glossary degradation rule is documented narrower than the code enforces

**Type**: LOCKED-DECISION VIOLATION (soft — the mission's own contract text) 
**Severity**: MEDIUM
**Spec reference**: FR-008, SC-004, `contracts/glossary-bootstrap.md` §1 ("Degradation rule: … only when `import_module("glossary.attachment")` raises `ImportError`"), data-model §4 "Degradation rule"
**Evidence**:
- `src/charter/offering/missions/glossary_hook.py:98-120` `_ensure_runner_registered()` — `except Exception: runner_cls = None` (pure code motion of the pre-existing block; WP02 design note §3 says so).
- The four repaired sites now state the narrower rule: `glossary_hook.py:22-25`, `kernel/glossary_runner.py:17-21` and its usage snippet `:41-54` (which even shows `except Exception` while the prose above it says `ImportError`), `kernel/__init__.py:41-47`, `kernel/README.md:18`.
- `tests/doctrine/missions/test_glossary_hook.py::test_execute_with_glossary_degrades_only_when_attachment_unimportable` pins the `ImportError` path only; no test asserts that a non-`ImportError` failure (e.g. `register()`'s `RuntimeError` on double registration with a different class, `glossary_runner.py:92-97`; an `AttributeError` if `GlossaryAwarePrimitiveRunner` were renamed) propagates. It does not — it degrades to "run the primitive without glossary checks" with a `logger.debug` only (`glossary_hook.py:174-178`).
- The WP02 reviewer recorded this as non-blocking ("docs say degrade on ImportError while code keeps pre-existing except Exception (scope: code motion)"); it was not folded or filed.

**Analysis**: FR-008's whole purpose was to make the four sites tell the truth about the mechanism. The registration story is now true; the degradation story is not — the code has a wider silent-failure envelope than every site and the test name claim. Either narrow the `except` to `ImportError` (a behaviour change needing its own red-first pin) or widen the prose at all four sites plus the test name. Not release-blocking (behaviour unchanged from baseline).

### DRIFT-3: Spec and FR-011 record left stale relative to what shipped

**Type**: NFR-MISS (documentation currency) / analysis-report follow-through
**Severity**: LOW
**Spec reference**: analysis-report I2/I4/I5 ("folded at the next spec touch"); C-1 of this review's probe 7
**Evidence**: `spec.md` absent from `git log 1ceba9f22..HEAD`; stale text at `spec.md:115` (status line), `:122` (pin 2), `:123` / `:242` / `:223` (ADR "Proposed", FR-012 "shrunk"), `:244` (C-005 three pins), `:256-266` (Open Decisions as open); `research/emitter-adr-inputs.md:1` header "recorded, not executed (C-003)" — WP05 T023 required the record be marked "executed by WP05"; the body says only "Execution of the ADR is WP05" (`:12-13`, `:97`).
**Analysis**: Documentation drift only (the plan/tasks/decisions/design notes are current). It matters because the spec is the artifact a future reader is told is "the author's promise", and it now promises the shrunk variant that was superseded.

### DRIFT-4: CHANGELOG carries only the WP01 entry; four user-visible changes are unrecorded

**Type**: NFR-MISS (house rule: CHANGELOG entry for surface changes; owed per the WP05 reviewer)
**Severity**: LOW
**Spec reference**: C-004 (WP01 only — satisfied); WP05 Activity Log 22:38:50Z "Consolidation owes: CHANGELOG line"
**Evidence**: `git diff 1ceba9f22..HEAD -- docs/changelog/CHANGELOG.md` = one `### Removed` bullet (WP01). Missing at HEAD: (a) WP05 — `runtime/next/event_emitter.py` deleted, `RuntimeEventEmitter.for_feature` → `runtime_event_emitter_for_mission(mission_dir=…)` (a renamed constructor and keyword on a public `runtime.next` surface; 15 test doubles had to be repointed), `RuntimeEventEmitterRegistry` E3 hook, and the **behaviour change** that strict-gated `decision_required` advances now durably append `DecisionInputRequested` to `decisions.events.jsonl` (RISK-6); (b) WP03 — `mission_runtime` root `__all__` 42→31, `ActionContext` alias removed, `specify_cli.team_projection` package deleted, `get_packs_root_default`/`content_present_at_primary_tip` demoted; (c) T014b — `mission.schema.yaml` lost the REQUIRED `orchestration` key and three definitions (breaking for any external consumer of the published schema). (The working tree shows an in-flight, uncommitted CHANGELOG edit by another session — not evaluated.)
**Analysis**: `src/kernel/__init__.py` was edited (docstring only) without a version bump — CLAUDE.md says "Any changes to `__init__.py` require a version bump … and a CHANGELOG entry"; the plan (C-004 note) records that the rc cycle is already open so no bump is taken. Accepted as a documented deviation; the missing entries are the actionable part.

### DRIFT-5: WP01 folded RED and GREEN into one commit (charter C-011)

**Type**: process deviation (charter red-first discipline)
**Severity**: LOW
**Evidence**: WP01 Activity Log 19:56:22Z reviewer note "ATDD test landed in the same commit as the implementation (charter asks for a separate preceding commit)"; the RED proof is nevertheless recorded (design note "RED proof (T001, base tree 1ceba9f22)") and was reproduced by the reviewer and by this review's falsification. WP02/WP03/WP05 kept separate RED commits.
**Analysis**: Evidence of red-first exists; the commit topology does not. Accepted by the reviewer; noted for the retrospective (the retrospective did not capture it — RISK-8).

---

## Risk Findings

### RISK-1: `mission_v1.read_events` is exported with zero production callers; the package docstring still names a deleted consumer

**Type**: DEAD-CODE / CROSS-WP-INTEGRATION (WP01 ↔ WP04)
**Severity**: LOW
**Location**: `src/specify_cli/mission_v1/__init__.py:8-9` ("`runtime/next/decision.py` reads the log through `read_events`") and `:26-28` (`__all__ = ["emit_event", "read_events"]`); `src/specify_cli/mission_v1/events.py` (byte-identical to base)
**Trigger condition**: `grep -rn "read_events" src --include='*.py'` → every hit outside the package is `specify_cli.status.store.read_events` or `glossary.events.read_events`; the only `mission_v1.events` importer is `runtime/next/next_invocation_lifecycle.py:332` (`emit_event`).
**Analysis**: FR-003 anticipated this ("after FR-015 deletes `derive_mission_state`, the sole live consumer is `emit_event`… FR-003's preservation duty then narrows"), but WP01 ran in parallel with WP04 and neither narrowed the export or the docstring; the widened dead-symbol walk does not flag it because the package `__init__` re-export counts as an importer (the same blind spot WP03 §4.1 documented for `mission_runtime`). Another session appears to be fixing exactly this in the working tree at review time.

### RISK-2: Stale docstring references to the deleted `mission_v1/guards.py`

**Type**: CROSS-WP-INTEGRATION (grep pattern miss)
**Severity**: LOW
**Location**: `src/runtime/next/runtime_bridge_composition.py:404` ("Mirrors the v1 `event_count` guard primitive (see `src/specify_cli/mission_v1/guards.py`)"); 5 files under `docs/` still cite `mission_v1.{guards,schema,runner,compat}` without a retirement note (WP01 reviewer's non-blocking item).
**Analysis**: WP01's T003 grep was `mission_v1\.\(compat\|runner\|guards\|schema\)` (dotted form) and missed the path form. Harmless at runtime; misleading to a reader.

### RISK-3: `sync_emitter` vocabulary survives on a live seam after the sync transport was retired

**Type**: retired-vocabulary residue (Terminology hygiene, not Canon)
**Severity**: LOW
**Location**: `src/runtime/next/runtime_bridge.py` (13 sites incl. `DecideNextContext.sync_emitter`), `src/runtime/next/runtime_bridge_engine.py` (17 sites incl. the `advance_run_state_after_composition(sync_emitter=…)` kwarg); 30 occurrences total.
**Trigger condition**: a future reader assumes the name denotes the (retired, #115) sync transport; the FR-012 compat delegate keyword (`contracts/compat-surface.md`) freezes it.
**Analysis**: Deferred with a sound rationale (WP05 design note §4.5: a ~40-file vocabulary sweep dwarfing the ADR execution; the ADR does not mandate it). The owed follow-up issue is not in `issue-matrix.json` and the retrospective did not capture it.

### RISK-4: `_gate_coverage.py:1456` `mission_v1` shard row kept on a directory that fell below the worklist floor; census stale on base

**Type**: CROSS-WP-INTEGRATION (gate bookkeeping)
**Severity**: LOW
**Location**: `tests/architectural/_gate_coverage.py:1456`; `docs/reports/…/ci_topology_census.json` (D-9)
**Analysis**: WP01 kept the row "as instructed" and reported that `ci_topology_census.json` was already stale on the base in `worklist` and `mapped_dirs`, that no test consumes it, and that `mission_v1` (120 LOC) now sits below the 500-LOC worklist floor. Not regenerated to avoid unrelated churn; no owner assigned.

### RISK-5: The inert-slot "owner completion" mechanism is orphaned upstream — the promise T014b kept has no enforcer

**Type**: BOUNDARY-CONDITION (vacuous-gate class)
**Severity**: LOW
**Location**: `tests/architectural/_inert_slots.py:574-629` (`owner_is_complete` / `unresolved_by_completed_owners`, zero callers since `177e06269`, #3285)
**Analysis**: This mission honoured its `delete-the-declaration` rows by hand (rider T014b) precisely because nothing fires automatically. The upstream gap ("restore or delete the orphaned owner gate") is named in the issue matrix as "file … from the retrospective" — but `retrospective.yaml` has `gaps: []`, so it was not filed anywhere durable.

### RISK-6: Behaviour change on the strict-gated path — decision events now durably logged

**Type**: BOUNDARY-CONDITION (intended, pinned, unadvertised)
**Severity**: LOW
**Location**: `src/runtime/next/runtime_bridge.py:2202` and `:1985`
**Trigger condition**: a mission under a strict retrospective gate (`timing=before_completion`, `failure_policy=block`) whose advance is `decision_required`; and every composition-dispatch `decision_required` regardless of policy.
**Analysis**: Before, the buffered `DecisionInputRequested` was flushed into the inner no-op and silently lost from `decisions.events.jsonl`; now it is appended (no commit — the answer commits). Correct per ADR (c), no double-emit (engine wrote only into the buffer), rollback preserved (refusal pin `test_refused_terminal_gate_discards_buffer_without_a_decision_git_log_write` green before and after). Operators reading `decisions.events.jsonl` will see rows they never saw before; belongs in the CHANGELOG (DRIFT-4).

### RISK-7: Acceptance and issue matrices carry scaffold placeholders

**Type**: artifact hygiene
**Severity**: LOW
**Location**: `acceptance-matrix.json` — all 15 rows `notes: "TODO: replace with a real acceptance criterion"`, `description: "Verify FR-NNN is satisfied"`, `mission_number: ''`, `negative_invariants: []`; `issue-matrix.json` — `title: "<fill at WP-implementation time>"` on `#1868`/`#3888`/`#3898`/`#3899`; `#3898` evidence describes the pre-WP05 plan; `#3899` "draft".
**Analysis**: The `evidence` fields are substantive (commit hashes, RED/GREEN counts, file paths) and the 15/15 `pass` verdict is backed by this review's trace; the placeholders are cosmetic but survived `accept` and `merge`.

### RISK-8: The retrospective record is generator boilerplate and captured none of the mission's recorded learnings

**Type**: process (retrospective quality)
**Severity**: LOW
**Location**: `kitty-specs/dead-port-disposition-01M1TZVN/retrospective.yaml` — `helped` = five "WPnn completed without rejection cycles", `not_helpful` = "analysis-report.md present", `gaps: []`, `proposals: []`.
**Analysis**: Five design notes recorded 20+ deviations, three tool frictions (`ACTIVE_WP_SCOPE_VIOLATION` ×23 paths, `ACTIVE_WP_CONTEXT_STALE`, `ruff --force-exclude` skip-count confusion), the orphaned owner gate (RISK-5), the ADR's failed "net LOC still drops" prediction (+66 `src/` LOC measured), and the lane-planner decision to collapse WP05 into WP03's lane. None reached the record. Note the skill's stated location `.kittify/missions/<mission_id>/retrospective.yaml` does not exist; the canonical location per `coordination/teardown.py:75` is `kitty-specs/<slug>/retrospective.yaml`, where the record is.

---

## Non-goal, locked-decision and terminology checks

| Check | Result |
|---|---|
| Non-goal 1 (no emitter changes before the ADR) | Honoured — WP03 shipped docstring-only (AST-identical proof); WP05 executed only after the ADR was merged+Accepted (15:59:54Z) and minted (16:33Z); claimed 21:12Z. |
| Non-goal 2 (no touches to Mission A's surfaces) | Honoured — `git diff 1ceba9f22..HEAD --stat -- src/specify_cli/status/{emit,aggregate,adapters}.py src/specify_cli/coordination/ src/runtime/next/{runtime_bridge_io.py,_internal_runtime/engine.py,runtime_bridge_retrospective.py,_internal_runtime/{emitter,lifecycle,models}.py} src/specify_cli/core/dependency_graph.py src/specify_cli/doctrine.py` → **empty**. `decision.py` and `runtime_bridge_engine.py` were edited only after A merged (C-001). |
| Non-goal 3 (no wiring of `execute_with_glossary`) | Honoured — still zero production call sites; OD6 accepted by the operator. |
| Non-goal 4 (frozen `_internal_runtime/{emitter,lifecycle,models}.py`) | Honoured — not in the diff. |
| Non-goal 5 (`doctrine.py` shim) | Honoured. |
| Non-goal 6 (`truststore`) | Honoured — dropped by #3899 before WP01; WP01's lock diff names only `transitions`. |
| OD2 = retire (FULL) / OD6 = documented-but-unwired | Both operator-resolved before WP01 claim (plan.md:27; WP01 Activity Log 19:22:56Z). |
| Terminology Canon (`feature*`) | No new `feature*` public name in the src diff (`+` lines with `def`/`class` containing "feature" → none); the promoted constructor is `for_mission`, keyword `mission_dir`, no `for_feature` alias (`test_bridge_and_engine_bind_the_protocol_and_the_factory_only` asserts absence). Pre-existing `get_mission_for_feature`/`feature_dir` untouched. `tests/architectural/test_no_legacy_terminology.py` green. |
| Suppressions | None added in `src/`. |
| Version bump | None (rc cycle open); `src/kernel/__init__.py` docstring edit recorded as the accepted deviation. |

---

## Silent Failure Candidates

| Location | Condition | Silent result | Spec impact |
|---|---|---|---|
| `src/charter/offering/missions/glossary_hook.py:114-118` `_ensure_runner_registered` | any exception during bootstrap (not only `ImportError`) | `None` → primitive runs without glossary checks, `logger.debug` only | DRIFT-2: contract text says `ImportError` only |
| `src/runtime/next/_internal_runtime/events.py:129-140` `_resolve_mission_id` | `resolve_mission_identity` raises (missing/unreadable/identity-less `meta.json`) | `mission_id=None` on the emitter | Documented fail-open instrumentation (ported from the retired `for_feature`); pinned by `test_for_mission_resolves_identity_like_the_retired_for_feature` (missing dir, corrupt meta) — accepted |
| `src/runtime/next/runtime_bridge.py:2760-2766` `answer_decision_via_runtime` seed | snapshot read fails | `logger.warning`, continues | Pre-existing, unchanged |

## Security Notes

| Finding | Location | Risk class | Recommendation |
|---|---|---|---|
| Subprocess in the ratchet test | `tests/specify_cli/mission_v1/test_import_hygiene.py:56-66` | — (list argv, no `shell=True`, hermetic env, `timeout=120`) | none |
| Env-gated factory | `src/runtime/next/_internal_runtime/events.py:257` `is_truthy(os.environ.get("SPEC_KITTY_SYNC_MINIMAL_IMPORT"))` | — (read-only gate mirroring `status/adapters.py`) | none |
| No new file I/O, HTTP, credential, or lock code in `src/` | `git diff 1ceba9f22..HEAD -- src` grep for `subprocess|shell=True|open(|httpx|requests.` → only the env read above | — | none |

---

## Review-history signal

No WP had a rejection cycle, a forced transition, an arbiter override, or a `ReviewerSelfApproval`; every approval was recorded by `role: reviewer, tool: user` after an independent reproduction (RED/GREEN counts in each `review-cycle-1.md`). Cross-WP hand-offs were all closed: WP04's orphaned grandfathered rows (not executable on lane-c, WP03 §6) were pruned in WP05 step 0 after lane-d was merged into lane-c (`6584186a5`), with RED proof that pruning before the merge fails the gate; WP01's D-12 open item became decision `DM-01M1W4WZEZZM8DM21JN1ZQY9E6` and rider T014b, executed in WP03 with its stop condition checked and the decision record's inaccuracy ("only checks the schema file") corrected in-commit. WP03's move to `approved` was initially blocked by the issue-matrix gate (missing `#3285` row) and resolved by the operator (`79832156a`).

---

## Final Verdict

**PASS WITH NOTES**

### Verdict rationale

All 15 FRs and 3 NFRs trace to shipped code and to tests that constrain the production path (the import-hygiene ratchet and the flush-target pins were both falsified in this review); no locked decision, non-goal, or constraint was violated; Mission A's surfaces and the rollback machinery are byte-untouched; the ADR was executed only after it was Accepted and its four Confirmation items hold at HEAD; Gates 1, 2 (targeted 213 + orchestrator's full run with one attributed pre-existing red) and 4 pass; no security finding. Nothing is release-blocking. The two MEDIUM findings are truth-of-documentation gaps in the mission's own territory — FR-007's honesty stops at the built-in packs while the resolver-preferred overrides and the packaged copies still advertise the dead DSL (DRIFT-1), and the repaired glossary sites now state a degradation rule narrower than the code enforces (DRIFT-2). Gate 3 (cross-repo e2e) could not be run on this machine and no exception artifact exists; the mission touched no cross-repo surface, so this is recorded as an operator item rather than a FAIL.

### Open items (non-blocking)

See the companion `mission-review-B-followups.md` (FU-01 … FU-14): run Gate 3; assign an owner to the DSL-bearing override/packaged copies and the residue test; reconcile the glossary degradation rule; refresh `spec.md` and the FR-011 record; add the three missing CHANGELOG entries; narrow the `mission_v1` export/docstring; fix the stale `guards.py` citations; file the `sync_emitter` rename, the orphaned inert-slot owner gate, and the `_gate_coverage` row/census follow-ups; post the #1868 note; replace the matrix placeholders; enrich the retrospective.

## Retrospective Reminder

The canonical post-merge sequence is: **mission review → author or verify retrospective → surface findings**. The record for this mission was authored automatically at the terminus and lives at `kitty-specs/dead-port-disposition-01M1TZVN/retrospective.yaml` (commit `09aecbc4b`, `created_by: spec-kitty-generator`, `findings_status: has_findings`); the skill's stated path `.kittify/missions/01M1TZVNQZKCQFX3NVJ8DKXN78/retrospective.yaml` does not exist because the canonical location is under `kitty-specs/` (`src/specify_cli/coordination/teardown.py:75`). It exists but is generator boilerplate (RISK-8) — run `spec-kitty retrospect summary` for the cross-mission view and `spec-kitty agent retrospect synthesize --mission dead-port-disposition-01M1TZVN` (dry-run by default) to inspect proposals; consider re-authoring the `helped`/`not_helpful`/`gaps` sections from the five design notes while the work is fresh. No `RetrospectiveCaptureFailed` event is present in `status.events.jsonl`.

---

## Appendix — commands run in this review (all foreground, `timeout` bounded, `-p no:cacheprovider`, max `-n 3 --dist loadfile`)

| Command | Result |
|---|---|
| `.venv/bin/spec-kitty agent tasks status --mission dead-port-disposition-01M1TZVN` | 5/5 done |
| `SPEC_KITTY_ENABLE_SAAS_SYNC=1 PWHEADLESS=1 timeout 600 .venv/bin/pytest tests/contract/ -q -n 3 --dist loadfile` | 245 passed, 10 skipped |
| targeted `tests/architectural/` set (13 files, listed under Gate 2) | 213 passed |
| `tests/specify_cli/mission_v1 tests/runtime/test_decision_flush_target.py tests/runtime/test_emitter_seam_consolidation.py tests/runtime/test_bridge_parity.py tests/doctrine/missions/test_glossary_hook.py tests/mission_runtime/test_facade_demotions.py tests/doctrine/missions/test_models.py tests/doctrine/test_schema_validation.py tests/status/test_producer_conformance.py tests/specify_cli/test_wp_frontmatter_fold.py tests/next/test_plan_mission_runtime.py tests/specify_cli/next/test_next_invocation_lifecycle_seam.py` | 198 passed |
| `PYTHONPATH=src .venv/bin/python scripts/generate_schemas.py --check` | OK (all schemas) |
| live-loader probe: `specify_cli.mission.Mission`, `MissionTemplateRepository.default().get_mission_config`, `_internal_runtime.schema.load_mission_template_file` over packs / overrides / packaged copies | see probe 2 |
| ratchet falsification in a throwaway `git worktree` at HEAD (`import six` appended; sibling submodule re-eagered) | 1 failed / 1 passed in each case; worktree removed, `git worktree list` clean |
| `pgrep -fl pytest` at finish | only other sessions' processes (PIDs 9936, 10006, 10451 …) — none started by this review remain |
