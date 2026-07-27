# Implementation Plan: Unshim Wave 2 — registered-shim removals + charter deprecation-cycle closure

**Branch**: `tidy/unshim-wave2` | **Date**: 2026-07-03 | **Spec**: [spec.md](spec.md) (rev 2, squad-hardened)
**Input**: Feature specification from `/kitty-specs/unshim-wave2-01KWMCAX/spec.md`

## Summary

Live-caller re-point → prove → delete migration across three shim families, plus two fold-ins. Stream A: re-point `specify_cli.next`'s 3 src callers (one is a monkeypatch injection seam moving WITH its 2 injector tests) and its 78-file test surface (417 plain imports + the occurrence-map's patch-string ledger, every row carrying an `interception_proof`), then delete the shim and drain the registry atomically. Stream B: delete the zero-caller glossary husk. Stream C: charter deprecation-cycle closure as FULL DELETE — 4 src callers (incl. the `runner.py:36` canonical→legacy defect), 23 test files, 3 shim packages, the 6-test lock-gate retired with a per-test disposition table; `charter_activate.py` settled canonical (document-and-exclude). Stream D: #2326 dead-wrapper prune (baseline 216→215). Stream E: WS1 `mission_runtime` LayerRule bind with a committed CI-selected negative test and the upward-edges allowed-exception decision recorded (#2327). Topology: sequential DAG (paula) — C-005 atomicity spreads spine edits (`shim-registry.yaml`, `test_shim_registry_schema.py`, `_baselines.yaml`) across the delete WPs, so parallel lanes would race on co-tenant files.

## Technical Context

**Language/Version**: Python 3.11 (repo standard; `.python-version` 3.11.15)
**Primary Dependencies**: pytest (+xdist), ruff, mypy, PyYAML — no new dependencies; import-path migration + deletions + one new architectural LayerRule test
**Storage**: N/A (governance state = `shim-registry.yaml`, allowlist frozensets, `_baselines.yaml`)
**Testing**: per-WP targeted suites + `tests/architectural/` sweep; per-site interception proofs recorded in the occurrence-map ledger (FR-002); the 5 CI-only charter shards run locally per the post-merge arch-gate discipline; full parallel suite `PWHEADLESS=1 pytest tests/ -n auto --dist loadfile` on the merged branch
**Target Platform**: Linux dev/CI; clean-install-verification lane must stay green (post-repoint `spec-kitty next` in a fresh venv)
**Project Type**: single — existing layout; deletions + import-line edits + one new arch test
**Performance Goals**: N/A (no runtime paths change semantically)
**Constraints**: C-001 re-point-before-delete per stream; C-002 behavior-neutral (import-path-only edits); C-004 occurrence-map governs the bulk rename (`occurrence_map.yaml`, plan artifact); C-005 atomic delete+drain per WP; C-006 refactor-stable retirements with per-test disposition tables
**Scale/Scope**: ~530 re-point sites (417 plain + patch-string ledger + 23 charter files + 4 src callers), 5 shim-surface deletions, 1 new LayerRule + negative test, 2 live governance docs scrubbed, CHANGELOG entry; 10-WP prior (paula)

## Charter Check

*GATE: evaluated against `.kittify/charter/charter.md` (compact context).*

- **Single canonical authority / unification**: ✅ the mission's essence — one import path per domain (`runtime.next`, `glossary`, `charter_runtime`); the runner.py:36 canonical→legacy cycle is fixed; registration-instead-of-deletion rejected per the anti-deferral ruling (Adjudicated Decision 1).
- **Quality & Tech-Debt Standing Orders**: ✅ squad cadence honored (pre-spec 3-lens + post-spec 2-lens, folds = rev 2); campsite items ride (#2326, doc scrub FR-011); test-remediation discipline (retired tests get per-test disposition tables; interception proofs prevent vacuous passes); canonical sources (census verified twice, occurrence-map is the binding ledger).
- **ATDD-first / red-first**: adapted — the interception-proof protocol IS the red-first surface (bogus-target flip = literal red proof); the WS1 negative test is committed and CI-selected (durable non-vacuity), not a throwaway run.
- **Architectural gate discipline**: ✅ every gate firing is mapped (registry schema test, scanner, lock-gate, baselines); all ratchet changes shrink-only; honest-live counts (NFR-004, Wave 1 precedent).
- **Terminology canon**: ✅.
- **Git/workflow discipline**: ✅ planning on `tidy/unshim-wave2`; lands on upstream main via PR only; operator merges.

No violations → Complexity Tracking empty.

## Project Structure

### Documentation (this mission)

```
kitty-specs/unshim-wave2-01KWMCAX/
├── spec.md               # rev 2 (binding census + adjudicated decisions)
├── issue-matrix.md       # tracker verdicts
├── plan.md               # this file
├── research.md           # Phase 0: squad-synthesis decisions D1–D9
├── occurrence_map.yaml   # C-004 binding ledger for the bulk rename (incl. patch-string proof ledger)
├── quickstart.md         # per-WP and merge-time validation commands
└── tasks.md + tasks/     # Phase 2 (/spec-kitty.tasks)
```

`data-model.md`/`contracts/`: N/A by design — no data entities or API surfaces; the executable contracts are the shim-registry schema test, the stale-allowlist guards, the interception-proof ledger, and the new LayerRule negative test. Recorded so downstream gates don't read absence as omission.

### Source Code (repository root)

```
DELETE (5 shim surfaces + 1 wrapper):
src/specify_cli/next/                      (75-LOC re-export __init__)
src/specify_cli/glossary/                  (55-LOC husk __init__)
src/specify_cli/charter_lint/  charter_freshness/  charter_preflight/
src/specify_cli/frontmatter.py             (update_field wrapper :318-320 + __all__ :373 + orphaned method :142 — edits, not file deletion)

RE-POINT (src, 7 callers):
src/specify_cli/cli/commands/implement.py:1285          → runtime.next.runtime_bridge
src/specify_cli/cli/commands/agent/workflow.py:1518     → runtime.next.runtime_bridge
src/specify_cli/cli/commands/next_cmd.py:52-58          → seam re-keyed to runtime.next.runtime_bridge (+ 2 injector tests)
src/specify_cli/cli/commands/charter/lint.py:45,93      → charter_runtime.lint
src/specify_cli/cli/commands/charter/status.py:55       → charter_runtime.freshness
src/specify_cli/charter_runtime/preflight/runner.py:36  → charter_runtime.freshness (defect fix)

RE-POINT (tests): 78 next files (417 plain + patch-string ledger) + 23 charter files + 2 glossary files
DELETE (tests): tests/glossary/test_legacy_import_shim.py; tests/architectural/test_charter_runtime_shim_paths.py (6 tests, per-test disposition table; test_canonical_paths_import re-homes)

EDIT (spine, atomic per C-005):
docs/migrations/shim-registry.yaml          (next + glossary rows out)
tests/architectural/test_shim_registry_schema.py:44-45  (presence-asserts edited same commit)
tests/architectural/_baselines.yaml         (category_b 216→215; honest-live re-derive at close)
tests/architectural/test_no_dead_symbols.py (:235 update_field row out; :517-518 charter_activate rows STAY)

ADD:
tests/architectural/test_layer_rules.py     (mission_runtime outbound LayerRule + committed negative test, CI-selected markers)

EDIT (docs): docs/architecture/05_ownership_manifest.yaml + 05_ownership_map.md (FR-011);
CHANGELOG.md (breaking-removal entry); docs/plans/degod-unshim-roadmap.md (closeout strike)
```

**Structure Decision**: single-project layout unchanged; no package becomes empty (canonical trees survive everywhere).

## Implementation Concern Map

> Concerns are not WPs; `/spec-kitty.tasks` translates them. Squad-adjudicated shape: **sequential DAG** (paula) — spine co-tenancy + C-005 forbid parallel lanes; A-repoint splits by directory cluster (risk-class is a per-WP checklist, not a WP boundary).

### IC-01 — A-seam: next src callers + injection seam (FR-001)

- **Purpose**: Re-point the 2 plain src imports and re-key the `next_cmd.py` monkeypatch seam together with its 2 injector tests, with consumption proven via the `captured`-dict side-effect.
- **Affected surfaces**: implement.py, agent/workflow.py, next_cmd.py, test_selector_resolution.py.
- **Sequencing/depends-on**: none (first; everything A depends on it).
- **Risks**: seam re-pointed without the injectors (or vice versa) = vacuous injection post-deletion.

### IC-02 — A-repoint bulk (FR-002; 2–3 WPs by directory cluster per the occurrence-map)

- **Purpose**: Re-point the 78-file test surface: 417 plain imports (mechanical) + every patch-string site with its `interception_proof` ledger row populated.
- **Affected surfaces**: the occurrence-map's tests_fixtures file list, clustered by directory (~38/~39 files per WP; a third WP if the map's live-doc classification adds volume).
- **Sequencing/depends-on**: IC-01.
- **Risks**: silent no-op patch targets (ledger is the mitigation); wrong plain re-point fails loud at collection.

### IC-03 — A+B delete + spine drain (FR-003, FR-004)

- **Purpose**: Delete `specify_cli/next/` and `specify_cli/glossary/` (+ `test_legacy_import_shim.py`), drain both registry rows with the schema-test presence-asserts edited in the same commit.
- **Sequencing/depends-on**: IC-02 (all references gone first, C-001).
- **Risks**: registry row removed without the same-commit schema-test edit reds; deletion before ledger complete = ModuleNotFoundError storm.

### IC-04 — C-repoint: charter callers + tests (FR-005, FR-006 part 1)

- **Purpose**: Re-point the 4 src callers (incl. the runner.py:36 defect fix) and the 23 legacy-import test files to `charter_runtime.*`, with interception proofs on the 10 charter patch-strings; run the 5 CI-only shards locally.
- **Sequencing/depends-on**: none in principle (spine-free); serialized in the single DAG.
- **Risks**: CI-only shards skipped locally → missed surface; patch-at-canonical-key changes module-identity assumptions.

### IC-05 — C-delete: shim packages + lock-gate retirement (FR-006 part 2, FR-007)

- **Purpose**: Delete the 3 charter shim packages; retire `test_charter_runtime_shim_paths.py` with the per-test disposition table (6 rows; `test_canonical_paths_import` re-homes); record the charter_activate documented-canonical adjudication.
- **Sequencing/depends-on**: IC-04.
- **Risks**: hand-waved disposition table (review reject); accidentally draining the :517-518 rows (they STAY).

### IC-06 — D: #2326 wrapper prune (FR-008)

- **Purpose**: Delete the update_field wrapper + `__all__` entry + orphaned instance method; drain the :235 row; baseline 216→215.
- **Sequencing/depends-on**: after IC-05 (baseline co-tenancy serialization).
- **Risks**: none material; honest-live re-derive of category_b at close in case earlier deletions dead more rows.

### IC-07 — E: WS1 LayerRule bind (FR-009; #2327)

- **Purpose**: Bind the `mission_runtime` outbound LayerRule with the named allowed-exception set (the 10+ upward `specify_cli` edges documented, NOT redded), a committed CI-selected negative test, and the recorded decision.
- **Sequencing/depends-on**: none (spine-free, zero next/glossary edges — schedulable anywhere).
- **Risks**: vacuous rule (allowed-set too broad) — the negative test must reject a synthetic out-of-set import; marker visibility per NFR-005/#2034.

### IC-08 — Closeout: docs + tracker (FR-010, FR-011)

- **Purpose**: FR-011 governance-doc scrub; CHANGELOG breaking-removal entry (no version bump — `specify_cli/__init__.py` untouched, verified); roadmap strike; verdict comments; #1797 progress; #2293 prerequisite note; #2327 progress; issue-matrix terminal; NFR-002 pinned grep; closing sweep.
- **Sequencing/depends-on**: all.
- **Risks**: premature issue closure (PR closes #2291/#2290/#2326).

## Complexity Tracking

*(empty — no charter violations)*
