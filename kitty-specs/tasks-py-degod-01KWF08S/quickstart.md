# Quickstart — Degod tasks.py (Wave 1) validation

Phase 1 output. How to prove the refactor is behavior-preserving. Two artifact families: the
**golden CLI-characterization harness** (the parity guard, green throughout) and the **per-core
unit tests** (the C-011 red-first artifact per extraction WP). All run in CI via the Wave-0 marker
binding (#2294).

## Scenario 1 — Golden parity guard (IC-01, runs on every WP)

```bash
export PATH="$PWD/.venv/bin:$PATH"          # workspace: spec-kitty-doctrine-fidelity
PWHEADLESS=1 pytest tests/specify_cli/cli/commands/agent/test_tasks_cli_contract.py -q
```
Freezes, for all 9 subcommands: flag/option surface (help introspection), exit codes {0,1,2}, and `--json` top-level keys. **PASS invariant: identical before and after each WP** (NFR-001). The new coord-topology fixture additionally drives the mutating commands:

- **move_task on a coord + protected target** → asserts the **skip-exit-0** arm: exit 0, the coord-event path written (NOT the primary), and the conditional `--json` keys (`wp_file_update`, `status_events_path`) present.
- **mark_status / map_requirements on a coord + protected target** → asserts the **refuse-exit-1** arm (current behavior; the inconsistency is deferred #2300).

## Scenario 2 — Per-core unit test (C-011 red-first, per extraction WP)

Author the unit test FIRST; it goes RED against the not-yet-extracted core, then GREEN once the core lands:

```bash
# WP that extracts the transition core:
PWHEADLESS=1 pytest tests/specify_cli/cli/commands/agent/test_tasks_transition_core.py -q
# analogous: test_tasks_mapping_core.py, test_tasks_status_view.py
```
Each enumerates its branch set **from the golden harness** (NFR-002): every `TransitionOutcome` / `MappingPlan` / `StatusView` branch is reachable from a golden-frozen input. Cores are exercised with **Fake** ports (INV-4 — pure, no I/O).

## Scenario 3 — Port stratification & injection (IC-02)

```bash
# ports resolve without a live repo when Fakes are injected:
PWHEADLESS=1 pytest tests/specify_cli/cli/commands/agent/ -k "ports or fake" -q
```
Assert: (a) `TasksPorts(fs, coord, git, render)` — exactly four; StatusEmit is NOT a top-level port (composed in `CoordCommitRouter`). (b) `_do_<cmd>(*, ports=None)` accepts an injected bundle; the Typer command exposes **no** `--ports` flag (registration introspection test). (c) `FsReader` and `CoordCommitRouter` are distinct objects (INV-1).

## Scenario 4 — Read-authority fold parity (IC-05 / FR-010)

```bash
PWHEADLESS=1 pytest tests/specify_cli/cli/commands/agent/ -k "read_dir or planning_read" -q
```
Assert the migrated `resolve_planning_read_dir` reads resolve the **same dir** the kind-blind `resolve_feature_dir_for_mission` did, for `move_task` / `finalize_tasks` / `list_dependents` — so Scenario 1 stays byte-identical (D8).

## Scenario 5 — Census honesty & shim finalization (IC-06 / FR-011)

```bash
# #2072 composite-key re-key MUST already be merged (D3 predecessor).
PWHEADLESS=1 pytest tests/architectural/ -q          # full arch sweep (cross-base at WP09 + merge)
ruff check src/specify_cli/cli/commands/agent/ && mypy src/specify_cli/cli/commands/agent/
```
Assert: `tasks.py` holds **0** inline `json.dumps` (AST-checked, alias-proof — 13 sites migrated); total ≤1400 LOC + each fat body ≤150 LOC + each helper ≤150 LOC / CC ≤15 (NFR-004 LOC gate); drained census sites removed with a 1:1 enumerated cross-base artifact + reviewer(not-author) sign-off + margin gate, floors lowered **shrink-only** (net-zero new entries, NFR-005), baseline 13→12; C-002 canonicalizer-gate stays non-vacuous. Run the `post-merge-arch-gate-adjudication` cross-base sweep at WP09 and mission merge.

## Definition-of-done gate (whole mission)

- Scenario 1 byte-identical pre/post every WP (pure parity, NFR-001). ✔
- Every core branch covered by a per-core unit test (NFR-002). ✔
- 4 stratified ports (coord WRITE = `commit_status` + `commit_artifact`); injection at orchestrator boundary; CoordRead≠CoordWrite (FR-003/FR-009). ✔
- Bodies + helpers within size/complexity ceilings; ruff+mypy clean, 0 new suppressions (NFR-003/004). ✔
- Arch census shrink-only, non-vacuous; full cross-base sweep clean (FR-011/NFR-005). ✔
