# Implementation Plan: Loop-reliability + CI-red burndown remediation

**Branch**: `fix/loop-reliability-ci-red-burndown` | **Date**: 2026-07-19 | **Spec**: [spec.md](./spec.md)
**Input**: Land the ready product fixes for two implement-review-loop P0s (#2534, #2573b) and burn down
the tracked 3.2.x CI reds (#2807, #2809, #2812), grounded by a pre-plan squad ([research.md](./research.md)).

## Summary

Two lanes of small, fully-rooted remediation. **Lane A (product):** land the ready consumer-repo
calm-degrade fix (#2534, a rebase) and teach the sync daemon to honor `SPEC_KITTY_SYNC_DISABLE`
(#2573b, ~4 lines). **Lane B (CI hygiene):** isolate a leaked-toggle test (#2809), fix a schema-drift
crash that reds three charter tests at once (#2807), seed a stale fixture + skip an auth-env test
(#2807), and root-fix a warnings flake + a CI filter-guard mismatch (#2812). All items are S except
#2534 (M — the rebase over churned files is the only real risk). Behavior-preserving except the
intended env-honoring and consumer-repo calm-degrade.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: `src/specify_cli/review/` (pre-review gate), `src/specify_cli/sync/` (daemon),
`src/charter/evidence/` (dry-run evidence), `src/specify_cli/runtime/resolver.py`, `.github/workflows/ci-quality.yml`
**Testing**: pytest; ATDD red-first through the pre-existing repros (`test_daemon_sync_disable_env`, the
`fix/2534` red-first tests, the charter reds); the reliable lane invocation is `uv run --extra test pytest`
**Constraints**: exclude deferred-by-design work (C-001); #2534 is land-not-redesign (C-002); every xfail is
`strict` + carries a tracking-issue ref (NFR-002); ruff + mypy --strict clean
**Scale/Scope**: ~6 WPs / 2 lanes; ~5 S fixes + one M rebase; net small

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **ATDD-First (C-011)** — every fix flips a pre-existing red-first repro red→green (daemon repro, the fix/2534
  tests, the charter/urn reds); no new entry points where one exists. **PASS.**
- **No unjustified suppression (NFR-002 / Sonar)** — prefer real fixes; the only xfail-candidate
  (`test_upgrade_updates_templates`) uses a skip-when-logged-out env-guard, not a blanket xfail. **PASS.**
- **Behavior-preserving except intent** — #2534 (consumer-repo calm-degrade) + #2573b (daemon honors disable
  env) change only the intended surfaces; spec-kitty-repo gate behavior + daemon-on-unset are unchanged. **PASS.**
- **Land-not-redesign (C-002)** — #2534 ships by rebasing the ready branch; #2598 (epic-blocked) supersedes
  later. **PASS.**
- **Scope fences (C-001/C-005)** — exclude #2795/#2367-A, #2573a-deep, #2598; defer the `url_list`→charter.yaml
  re-wire to its own issue; do not split the (well-rooted) loader anomaly. **PASS.**

No violations → Complexity Tracking intentionally empty.

## Project Structure

### Documentation (this mission)
```
kitty-specs/loop-reliability-ci-red-burndown-01KXWWD6/
├── plan.md, research.md, data-model.md, contracts/, traces/, issue-matrix.md, tasks.md (later)
```

### Source Code (repository root)
```
src/specify_cli/review/pre_review_gate.py                 # WP01 (#2534) — is_consumer_repo seam
src/specify_cli/cli/commands/agent/tasks_move_task.py     # WP01 (#2534) — calm reason (3way)
src/specify_cli/sync/daemon.py                            # WP02 (#2573b) — _daemon_start_skip_reason honors disable env
src/charter/evidence/orchestrator.py                      # WP04 (#2807) — isinstance guard (clears 3 reds)
.github/workflows/ci-quality.yml                          # WP06 (#2812) — add `platform` to the loader-coverage if-guard

tests/review/test_pre_review_gate_engine.py               # WP01 — red-first unit (from fix branch)
tests/review/test_pre_review_gate_integration.py          # WP01 — red-first integration (from fix branch)
tests/sync/test_daemon_sync_disable_env.py                # WP02 — repro (flip green)
tests/sync/conftest.py                                    # WP03 (#2809) — hoist the #2794 env-reset fixture
tests/charter/test_bundle_contract.py                     # WP05 (#2807) — seed charter.yaml in _init_fixture
tests/adversarial/test_distribution.py                    # WP05 (#2807) — skip-when-logged-out
tests/runtime/test_resolve_by_urn.py                      # WP06 (#2812) — clear resolver.__warningregistry__
```

**Structure Decision**: single-project. Two lanes (product vs CI-hygiene), disjoint `owned_files` per WP.

## Complexity Tracking

*No Charter Check violations — table intentionally empty.*

## Implementation Concern Map

> Concerns are NOT work packages. `/spec-kitty.tasks` maps these to executable WPs.

### IC-01 — Land the consumer-repo pre-review-gate calm-degrade (#2534)
- **Purpose**: A consumer repo's `move-task --to for_review` no longer surfaces the alarming
  "gate authorities unavailable" internal-module message — calm-degrade to a non-blocking `no_coverage` warn.
- **Relevant requirements**: FR-002; NFR-003; C-002, C-003.
- **Affected surfaces**: rebase commit `0153934f9` onto main — `pre_review_gate.py` (`is_consumer_repo` seam +
  `_is_spec_kitty_source_repo`), `tasks_move_task.py` (`_PRE_REVIEW_CONSUMER_REPO_REASON`; **needs `git apply
  --3way`** — positional drift only), `tests/review/test_pre_review_gate_{engine,integration}.py` (red-first).
- **Sequencing/depends-on**: none.
- **Risks**: the rebase (LM-1) — verify the repro still fires on main + the two hunks land by 3-way; if it
  fights, port-the-intent (research §1). Do NOT re-derive (C-002).

### IC-02 — Sync daemon honors the disable env (#2573b)
- **Purpose**: `SPEC_KITTY_SYNC_DISABLE`/`MINIMAL_IMPORT` actually prevents daemon spawn.
- **Relevant requirements**: FR-003; NFR-003; C-003.
- **Affected surfaces**: `src/specify_cli/sync/daemon.py` `_daemon_start_skip_reason` (`:1038`) — add an early
  `is_truthy`-guarded disable-env check mirroring the pre-review-gate grammar; flip
  `tests/sync/test_daemon_sync_disable_env.py` green.
- **Sequencing/depends-on**: none (independent of the fixture; the repro sets the env itself).
- **Risks**: precedence placement (any position returns non-None → skip); zero blast radius on the unset path.

### IC-03 — Isolate the strict-JSON test from the leaked sync toggle (#2809)
- **Purpose**: `test_strict_json_stdout` is deterministic in CI regardless of a leaked `SPEC_KITTY_SYNC_*` toggle.
- **Relevant requirements**: FR-005; NFR-001.
- **Affected surfaces**: copy the existing autouse `_isolate_pre_review_gate_sync_toggles` fixture (#2794,
  `agent/conftest.py:51`) into `tests/sync/conftest.py`.
- **Sequencing/depends-on**: none.
- **Risks**: scope the fixture to `tests/sync/` (minimal blast radius); don't hoist repo-wide unless needed.

### IC-04 — Fix the schema-drift crash in dry-run evidence (#2807, clears 3 reds)
- **Purpose**: one `isinstance` guard clears `test_phase3_dry_run_evidence_smoke`, the orchestrator dry-run test,
  AND `test_charter_epic_golden_path`.
- **Relevant requirements**: FR-004; NFR-001.
- **Affected surfaces**: `src/charter/evidence/orchestrator.py:95-96` — guard `config["charter"]` being a path
  string post-#2773 (`if not isinstance(charter_cfg, dict): charter_cfg = {}`) + fix the stale docstring (`:82`).
- **Sequencing/depends-on**: none.
- **Risks**: **defer** the `url_list`→charter.yaml re-wire to a separate issue (C-005) — NOT required to clear
  the red; the feature has no live config home post-#2773.

### IC-05 — Charter CI-fixture hygiene (#2807)
- **Purpose**: green `test_bundle_contract` (stale fixture) + de-noise `test_upgrade_updates_templates` (auth-env).
- **Relevant requirements**: FR-004; NFR-001, NFR-002.
- **Affected surfaces**: `tests/charter/test_bundle_contract.py` `_init_fixture` (seed + commit a minimal
  `charter.yaml` alongside `charter.md`); `tests/adversarial/test_distribution.py:237`
  (skip-when-logged-out env-guard, mirroring the charter-mission auth-skip — real fix over blanket xfail).
- **Sequencing/depends-on**: none.
- **Risks**: bundle_contract may need schema-plausible `charter.yaml` content if `is_stale` hashing runs
  (existence + git-tracked is the load-bearing assertion).

### IC-06 — CI flake + workflow filter-guard (#2812)
- **Purpose**: root-fix the urn-lane warnings flake and the mission-loader-coverage skip anomaly.
- **Relevant requirements**: FR-006; NFR-001, NFR-002.
- **Affected surfaces**: `tests/runtime/test_resolve_by_urn.py` (clear `resolver.__warningregistry__` in the
  block); `.github/workflows/ci-quality.yml` (add `|| needs.changes.outputs.platform == 'true'` to the
  mission-loader-coverage job `if:`, `:1290-1293`).
- **Sequencing/depends-on**: none.
- **Risks**: `platform` output feeds other jobs — the 1-line guard change is low blast radius; don't split.

### Mission hygiene (not an IC)
- `issue-matrix.md` (already authored) references #2534/#2573/#2807/#2809/#2812. Tracer files seeded at planning.

## Lanes
Lane A (product): IC-01, IC-02. Lane B (CI hygiene): IC-03, IC-04, IC-05, IC-06. All ICs independent
(disjoint owned_files) → ~6 WPs, highly parallel. `finalize-tasks` computes lanes.
