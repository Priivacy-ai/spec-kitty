# Tasks: Harden the Dead-Symbol Gate

**Mission**: `harden-dead-symbol-gate-01KW0RJR`
**Planning base branch**: `feat/harden-dead-symbol-gate`
**Final merge target**: `main` (via PR from the feature branch)
**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Research**: [research.md](./research.md) · **Data model**: [data-model.md](./data-model.md)

## Overview

A single atomic work package. The parser fix un-blinds 57 modules → ~119 symbols surface in ONE gate
run; the 4 detectors must absorb the live ones, the residue must be disposed, and the `BANNED_FLAGS`
security fix must land too (un-blinding `envelope.py` surfaces `BANNED_FLAGS` — wiring it is what makes
it live). The gate (`tests/architectural/test_no_dead_symbols.py`) is green only when ALL of this is
coherent, so it cannot be split into independent lanes. Decisions baked in: register-arg symbols are
DEMOTEd (no 5th detector); making the symbol-gate baselines a real ratchet is OUT OF SCOPE (follow-up).

**The load-bearing invariant (C-001 / NFR-001):** every detector binds proof-of-life to a RESOLVED
declaring module, never a bare name — and a no-false-negative regression test proves a synthetic dead
symbol is still flagged.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | FR-001: fix `_extract_all_literal` (continue on non-`__all__` AnnAssign) + unit test | WP01 | |
| T002 | FR-002: per-tree alias map + module-style detector (a) [subsumes (c) Typer] + unit test | WP01 | |
| T003 | FR-002: getattr-string detector (d-getattr) + `__getattr__` facade detector (b) + unit tests | WP01 | |
| T004 | NFR-001: no-false-negative regression test (synthetic dead symbol still flagged) | WP01 | |
| T005 | FR-003/004/006/007: delete `_daemon_root`, DEMOTE the residue, allowlist-defer auth trio, update `_baselines.yaml` | WP01 | |
| T006 | FR-005: wire the `BANNED_FLAGS` security check in `envelope.py` + `--yolo`-rejected test | WP01 | |
| T007 | Verify: gate green (57 modules now inspected), full architectural+contract suite, no net growth, ruff/mypy | WP01 | |

## Work Packages

### WP01 — Harden the dead-symbol gate

- **Goal**: Fix the parser bug, add 4 structurally-anchored caller detectors so the ~119 surfaced symbols are recognized live with no allowlist growth, dispose of the genuinely-dead residue, wire the `BANNED_FLAGS` security check, and leave `tests/architectural/` + `tests/contract/` green — without weakening the gate (no false negatives).
- **Priority**: P1 (the whole mission)
- **Dependencies**: none
- **Prompt**: [tasks/WP01-harden-dead-symbol-gate.md](./tasks/WP01-harden-dead-symbol-gate.md)
- **Estimated prompt size**: ~520 lines (7 subtasks)
- **Independent test**: `PWHEADLESS=1 uv run pytest tests/architectural/test_no_dead_symbols.py tests/architectural/ tests/contract/ -q` green; the un-blinded gate inspects the previously-hidden 57 modules; `category_a`/`category_b` frozenset counts ≤ base; `--yolo` rejected by `parse_and_validate_policy`.

**Included subtasks**:

- [x] T001 FR-001: in `tests/architectural/test_no_dead_symbols.py`, fix `_extract_all_literal` (~L938) so a non-`__all__` top-level `AnnAssign` `continue`s instead of early-returning `frozenset()`; add a focused unit test (module whose first top-level node is a non-`__all__` AnnAssign followed by a real `__all__`) (WP01)
- [x] T002 FR-002: build a per-tree import-alias map (`local name → resolved dotted module` from `ast.Import` + `ast.ImportFrom asname`); add detector (a) — walk `ast.Attribute(value=Name(id in alias_map))`, resolve to module, record the edge; this subsumes (c) Typer registration; fold into `_imports_by_target` so `_symbol_has_caller`'s re-export rules apply; add a unit test (WP01)
- [x] T003 FR-002: add detector (d-getattr) — `Call(getattr, [Name in alias_map, Constant str])` → edge; and detector (b) — module with `def __getattr__` + static dict-literal `(submodule, "name")` tuples → mark the submodule's canonical symbol live; add unit tests for each (WP01)
- [x] T004 NFR-001: add the no-false-negative regression test — a synthetic module with an `__all__` symbol that has NO caller of any recognized kind MUST still be flagged dead (proves the detectors didn't blind the gate) (WP01)
- [x] T005 FR-003/004/006/007: DELETE `specify_cli.sync.owner::_daemon_root` (re-export); DEMOTE from `__all__` (keep defs, verify no external `from`-import/star-import first): `auth.transport::reset_user_facing_dedup`, `sync.owner::check_daemon_owner_match`, `compat.safety_modes::{_ORCHESTRATOR_API_UNSAFE_SUBCOMMANDS, SafetyPredicate, _orchestrator_api_predicate, _mission_state_predicate}`, `legacy_detector::LEGACY_LANE_DIRS`, `readiness.upgrade_ux::{PromptCallback, UpgradeUxOutcome}`, `doctrine.versioning::migrate_v1_to_v2`, plus any residual annotation-only/test-only symbol the detectors don't rescue; ALLOWLIST-as-deferred the `auth.transport` trio (`get_client`/`get_async_client`/`reset_clients`) with ONE justified entry; update `tests/architectural/_baselines.yaml` so `category_a`/`category_b` show no net growth, each edit with a `# justification:` comment (WP01)
- [x] T006 FR-005: in `src/specify_cli/orchestrator_api/envelope.py`, make `parse_and_validate_policy` reject any `dangerous_flags` entry that is a member of `BANNED_FLAGS` (currently defined but never enforced), returning the typed validation error the contract expects; add a test (e.g. `--yolo` rejected) in `tests/agent/test_envelope_unit.py` (WP01)
- [x] T007 Verify: `PWHEADLESS=1 uv run pytest tests/architectural/test_no_dead_symbols.py -q`, then `tests/architectural/ tests/contract/ -q`; confirm the ~119 surfaced symbols are recognized live with ZERO new allowlist entries (only the deferred auth trio adds one); `category_a`/`category_b` counts ≤ base; `uv run ruff check` (diff-scoped) + `uv run mypy src/specify_cli/orchestrator_api/envelope.py` clean (WP01)

**Implementation sketch** (research D-05 order):
1. T001 parser fix (un-blinds — gate will be RED with ~119 until detectors+dispositions land).
2. T002 alias map + module-style detector (a/c).
3. T003 getattr + facade detectors (d/b).
4. T004 no-false-negative guard.
5. T005 dispose the residue (delete/demote/allowlist) + baselines.
6. T006 wire BANNED_FLAGS (also makes that surfaced symbol live).
7. T007 verify green + no growth.

**Parallel opportunities**: none — single atomic gate-green unit.

**Risks**:
- **Masking real dead code** (C-001): a too-loose matcher. Mitigation — every rule resolves the alias to the EXACT declaring module before counting; the T004 no-false-negative test is the guard; reuse the stale-allowlist reverse check (L1093–1099).
- **Demoting an externally-imported symbol**: verify no `from mod import sym` / `import *` before each demote (C-004).
- **Baseline drift** (C-003): re-confirm `category_a`/`category_b` live sizes vs the base (depends on #2159/#2152 merge state) before setting counts.
- **BANNED_FLAGS coupling**: un-blinding surfaces it; T006 must land in the same WP or the gate flags it dead.

## Requirement coverage

FR-001 … FR-007 all map to WP01. NFR-001…004 and C-001…004 are verified by T004/T007 and the WP constraints.
