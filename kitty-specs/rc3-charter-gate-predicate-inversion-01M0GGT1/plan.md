# Implementation Plan: M3 — Gate on the declared entity, not a coarse set

**Spec**: `spec.md` (finalized 2026-08-21, POST-SPEC squad folded) · **Target**: `main` · **Topology**: single_branch
**Author**: architect-alphonso (plan-phase design) · **Date**: 2026-08-21 · **POST-PLAN squad folded** (planner-priti / architect-alphonso / reviewer-renata)

> Reads `spec.md` + `research.md` + `tracer-squad-findings.md`. The five surfaces (A–D + the ADR E) each replace a coarse-set membership test with a predicate on the declared entity. This plan fixes the WP cut lines, per-symbol ownership (vs M4/M5), the single-graph-load proof for NFR-001, the issue→WP map, and the red-first strategy the WP01 ADR names.

---

## 1. Architecture overview

| Surface | File (code) | Coarse test today | Declared-entity predicate | Data authority |
|---------|-------------|-------------------|---------------------------|----------------|
| A #3596 | `src/charter/context.py:255,484` (+ display `src/specify_cli/cli/commands/charter/context.py:199`) | `action in BOOTSTRAP_ACTIONS` | `bundle.merged is not None and f"action:{type}/{action}" in bundle.merged.node_urns()` | `packs/built-in/action.graph.yaml` (node `scope` edges) |
| A-fold | `src/charter/interview.py:34` | `action in _KNOWN_ACTIONS` | one fast-path constant **+** declared-node source | (as A) |
| B #3598 | `src/charter/mission_type_profiles.py:766,1235` | `_project_has_doctrine_overrides` (project-wide) | per-type `governance-profile.yaml` id-match at any layer | `MissionTypeProfileRepository` (`_GOVERNANCE_PROFILE_GLOB`) |
| C #3599/#3597 | `analysis_report.py:33`, `runtime_bridge_io.py:841`, `worktree.py:609`, resolver seam | hardcoded filename literals / dead guard registry | per-type filename set + live per-type presence gate | **`expected-artifacts.yaml` `path_pattern`** (read-only via `src/doctrine/missions/repository.py:362 get_expected_artifacts`) |
| D #3407 | `src/runtime/next/runtime_bridge.py:797` | `mission_family="software-dev"` (unconditional) | resolved mission family → `_GUARD_TABLES[family]` | `get_mission_type(feature_dir)` (`mission.py:559`, already imported at `runtime_bridge.py:177`) |
| E | `docs/adr/3.x/2026-08-21-1-*.md` | — | one policy-reversal ADR naming every red-by-design test | — |

**Data-flow (delivery path, post-fix):** `context.py` threads the caller's `mission_type` → resolves the bundle **once** (`_resolve_action_bundle` → `_load_action_doctrine_bundle` → `load_validated_graph`, `action_doctrine_bundle.py:194`) → tests `bundle.merged.node_urns()` membership → `bootstrap` (deliver the node's `scope`-edge grain) or `compact`. Typeless → `resolve_mission_type_key` returns `None` → `bundle.merged is None` → `compact` (the `None` guard is load-bearing).

## 2. Single-graph-load proof (NFR-001) — VALID via the `.merged` carrier, no memoization

Today the non-bootstrap path is **graph-free** — both gates short-circuit to `_non_bootstrap_context_result` (`context.py:256`) before `_resolve_action_bundle` (`:272`/`:503`). FR-001 moves the bundle resolve *before* the mode decision. This stays single-load **without memoization** (architect-alphonso, verified):

1. Within one `build_charter_context_json` call, `_load_action_doctrine_bundle` calls `load_validated_graph` **exactly once** (`action_doctrine_bundle.py:194`); `resolve_context` reuses that in-memory graph, carried on `_ActionDoctrineBundle.merged` (`action_doctrine_bundle.py:71`, `DRGGraph | None`).
2. The FR-001 predicate consumes that **same** carrier: `bundle.merged is not None and f"action:{type}/{action}" in bundle.merged.node_urns()` (`src/doctrine/drg/models.py:413`) — pure in-memory, **zero** additional loads.
3. **Do NOT memoize `load_validated_graph`** — it is not memoized today and must not be: process-wide path-keyed memoization would serve **stale** graphs when project/org overlays change mid-process (test suites, daemon). The per-call carrier is the correct and sufficient guarantee.
4. The 4-token **fast path** (FR-002) still returns `bootstrap` for `specify/plan/implement/review` without resolving the bundle — only genuinely non-bootstrap actions pay the one load (accepted cost, recorded in the ADR).
5. **New red-first test** (NFR-001): patch `charter._drg_helpers.load_validated_graph` with a call counter; assert `build_charter_context_json(action="tasks", mission_type="software-dev")` triggers exactly **one** load. The pre-existing `test_charter_import_time_io.py` (import-time `MissionTypeRepository.default` spy) stays but is NOT the budget witness.

## 3. Work-package breakdown

Cut lines from the squads (A/B/C/D independent; C splits along the red-first fault line; E foundational). Single_branch → WPs land sequentially; WP01 is the shared ADR foundation.

| WP | Title | Surface | FRs / ACs | Depends | Size |
|----|-------|---------|-----------|---------|------|
| **WP01** | Policy-reversal ADR + design-decision resolution | E | FR-016; C-002 | — | S |
| **WP02** | Action gate: node-URN membership + vocab fold | A | FR-001/002/003/004/007/008/015; NFR-001; AC-1/2/3/7/8 | WP01 | M |
| **WP03** | Governance-slot: layered per-type probe | B | FR-005/006; NFR-002; AC-4/5/6 | WP01 | M |
| **WP04a** | Artifact filename seam (green refactor) | C | FR-009/010; C-001; NFR-003; AC-9/12 | WP01 | M |
| **WP04b** | Live per-type gate + stray-touch delete (behavioral) | C | FR-011/012/013; AC-10/11 | WP04a | M |
| **WP05** | CLI guard family: resolve actual family | D | FR-014; NFR-003; AC-13/14 | WP01 (sequencing-only†) | S |

† WP05 reverses no red-by-design test (#3407 is a pure route-around); its WP01 edge is sequencing-only, not an ADR gate.

**WP04a (green characterization — NFR-003 witness, no behavior change):**
1. Relocate `ExpectedArtifactManifest`/`ExpectedArtifactSpec`/`ArtifactClassEnum` `src/specify_cli/dossier/manifest.py:168` → `src/doctrine/missions/expected_artifact_manifest.py` (new module gets its own `__all__`, C-007; enroll the 3 names in `src/doctrine/missions/__init__.py` `__all__`). **Blast radius = consumers (POST-TASKS-corrected):** (a) `dossier/indexer.py`; (b) `dossier/__init__.py:12-15,50-52` re-export from the new home; (c) `ManifestRegistry` uses the class at **RUNTIME** (`load_manifest`→`model_validate`) — a `TYPE_CHECKING`-only import would `NameError` at runtime while mypy stays green, so preserve `manifest.py`'s import-time isolation via a **lazy function-local import** (`_doctrine_repository()` `# noqa: PLC0415` pattern) or a PEP 562 `__getattr__` re-export; (d) three test importers (`tests/dossier/test_manifest.py:458`, `tests/dossier/test_manifest_guard_parity.py:39`, `tests/sync/test_dossier_pipeline.py:234`) — the relocation test asserts the legacy import path still resolves at runtime. Direction `specify_cli→doctrine` stays legal.
2. Add `resolve_configured_artifact_name` + `required_artifacts_for(step)` sourcing `expected-artifacts.yaml` `path_pattern` by **consuming** `repository.py:362 get_expected_artifacts` read-only; `project_artifact_name_set` beside `project_template_set` (`step_projection.py:100`); two charter bundle slots (`Mapping[str, Any]`).
3. Convert the named call sites to the resolved set (byte-compat, NFR-003): `_HASH_INPUTS` (`analysis_report.py:33`), the accept triple, the retrospective precondition, `validate_feature_structure` (`worktree.py:704`), `_PRESENCE_FILE_TAGS` contents (`runtime_bridge_io.py:841`, all 10). AC-9 load-bearing: patching `path_pattern` changes the call-site output.

**WP04b (behavioral reds — depends WP04a):**
4. Live per-type presence gate: `gather_artifact_presence` consults the per-type `path_pattern` set (data-driven), so a custom family gates on its own filenames — AC-10 present→passes / absent→blocks. (`evaluate_guards_strict`'s `UnregisteredMissionFamilyError` strict-raise is retained for guard-table *dispatch* of a genuinely unregistered family — a distinct concern, per the ADR.)
5. Third-kind pins (AC-12, specific raises) + delete the `else: spec_file.touch()` branch (`worktree.py:609`, AC-11 reversal).

## 4. Per-symbol ownership (cross-mission)

- **vs M4 (`rc3-operator-signal-fail-loud`, not landed) — ZERO-EDIT.** M4 owns `src/doctrine/missions/repository.py:295 get_action_index` / `except :316` (#3412). **WP04 CONSUMES `get_expected_artifacts` (`:362`) read-only and does NOT modify `repository.py`** (planner-priti). No same-file collision; no rebase-reconcile risk.
- **vs M5 (`rc3-canonical-mission-type-reader`, partial-landed).** M3 consumes the landed `canonical_mission_type_key`/`resolve_mission_type_key`; adds no parallel reader (NFR-002). When M5 lands `read_mission_type(meta)`, `resolve_mission_type_key` becomes its delegate — no M3 change.

## 5. Issue → owning-WP map (tracker hygiene)

| Issue | WP | Note |
|-------|----|----|
| #3596 | WP02 | action gate predicate |
| **file #NNNN (`_KNOWN_ACTIONS` fold) BEFORE WP02 implement** | WP02 | not yet filed — file + assign to HiC (DIR-012) |
| #3598 | WP03 | layered per-type probe |
| #3599 | WP04a/WP04b | artifact-name seam + live gate |
| #3597 | WP04b | live per-type presence gate |
| #3407 | WP05 | family routing |
| — | WP01 | **WP01/ADR owns NO issue** — issue-verdict must not flag it as an orphan |

## 6. Red-first test strategy (ATDD, charter C-011)

Each implementation WP lands its ATDD test(s) as the **first commit**, RED on `planning_base_branch`, GREEN on the WP's final commit. Reviewer verifies red→green.

| WP | Red-first tests (real entry point) | Kind |
|----|-----------------------------------|------|
| WP02 | reverse `test_every_load_delivery.py:197` + `test_context_schema_version_ledger.py:104` (AC-3); NEW load-count test (NFR-001); AC-2 node-membership companion; **FR-015 acceptance note: retrospect nodes recorded as on-demand sequence-orphans per ADR**; sweep `tests/charter/` for siblings | behavioral red + reversal |
| WP03 | AC-4 `resolve_mission_type_context(repo,"softwaer-dev")` raises; reverse `test_mission_type_profiles.py:260` seeding real per-type `governance-profile.yaml` (AC-6); AC-5 layered project/org/built-in fixtures | behavioral red + reversal |
| WP04a | AC-9 load-bearing "patch `path_pattern` → output changes"; AC-12 specific-raise pins | green characterization |
| WP04b | AC-10 `gather_artifact_presence(mission_family="<custom>")` fail-closed both directions; reverse `test_worktree.py:263` (AC-11) | behavioral red + reversal |
| WP05 | AC-13 hand-built `_check_cli_guards("review", <plan dir + unapproved WP>)` latent-defect pin; AC-14 software-dev unchanged; **verify `get_mission_type` string == `_GUARD_TABLES` family key for every built-in** | latent pin + green characterization |

## 7. Resolved design decisions (were deferred; POST-PLAN squad)

- **Memoization** — resolved: **none needed**; the `.merged` per-call carrier guarantees single-load (§2). WP02 verifies with the load-count test.
- **Custom-family gate** — resolved: **data-driven presence via `path_pattern`** (AC-10) + retained strict-raise for guard-table dispatch (ADR).
- **`path_pattern` coverage** — WP04a audits all 10 tags resolve to today's built-in filenames (NFR-003).
- **Interview validation mechanism** (static label-union vs loaded nodes) — WP02 decides; state validation is type-agnostic (any label on some action node passes).
- **Retrospect sequence-orphans** — recorded as on-demand orphans per ADR; WP02 acceptance note.

## 8. Risks & mitigations

- **C-001 relocation blast radius (WP04a)** — 4 consumers; `TYPE_CHECKING` isolation preserves `manifest.py`'s import-time boundary; layer tests stay green.
- **Red-by-design "fixed backwards"** — the ADR names all four tests; reviewer checks the assertion was *reversed*, not restored.
- **NFR-003 silent drift** — §3 conversion keeps built-in outputs byte-identical; AC-9 load-bearing assertion proves the seam is real; WP04a audits all 10 tags.
- **WP05 family-key divergence** — verify `get_mission_type` == guard-table key per built-in before shipping (else a non-software-dev mission fail-closes wrongly).
