# Implementation Plan: Harden the Dead-Symbol Gate

**Branch**: `feat/harden-dead-symbol-gate` | **Date**: 2026-06-26 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/harden-dead-symbol-gate-01KW0RJR/spec.md`

## Summary

Fix the `_extract_all_literal` parser bug and add four **structurally-anchored** caller detectors to the
dead-symbol gate so the ~119 symbols it surfaces are correctly recognized as live (no allowlist growth),
then clean up the genuinely-dead residue (1 delete, ~7+ demotes) and wire a latent security check. The
parser fix and detectors **must land together** (research D-01: fix-only turns the gate red with 119
false positives). The load-bearing invariant (research D-02): every detector binds proof-of-life to a
**resolved declaring module**, never a bare name — that is what lets the gate see more without going
blind to real dead code. Two design forks resolved: register-arg symbols are **DEMOTEd** (not a 5th
detector); making the symbol-gate baselines a real ratchet is **out of scope** (follow-up).

## Technical Context

**Language/Version**: Python 3.11+ (stdlib `ast` only — the gate is pure-AST)
**Primary Dependencies**: pytest (the gate is `tests/architectural/test_no_dead_symbols.py`); ruff, mypy. No new runtime deps.
**Storage**: N/A
**Testing**: pytest; the gate IS a test. Each new detector gets a focused unit test (synthetic module exercising the pattern) PLUS the NFR-001 no-false-negative test (a synthetic genuinely-dead `__all__` symbol must STILL be flagged).
**Target Platform**: Linux/macOS dev + CI
**Project Type**: single (Python package `specify_cli` + sibling `charter`/`doctrine`/etc.)
**Performance Goals**: Detectors reuse the cached whole-src AST corpus (`path_to_tree`) — extra `ast.walk` passes, zero new file I/O (research: gate parses each src file once).
**Constraints**: Detectors MUST be structurally anchored (AST + resolved-module binding), never bare substring (C-001); `_baselines.yaml` edits carry `# justification:` + match live size (C-002); no net frozenset growth (NFR-003); re-confirm live counts at implement time vs #2159/#2152 merge state (C-003).
**Scale/Scope**: ~1 gate file (parser fix + 4 detectors + their tests), ~10-15 src modules touched by demotes/the delete, 1 security fix (`orchestrator_api/envelope.py`), `_baselines.yaml`.

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Charter present. Relevant gates:
- **Burn-down Policy (C-004) / SHRINK ratchet** — this mission *strengthens* the gate and avoids the +107 growth #2049 deferred FR-006 to prevent; fully aligned. ✅
- **`__all__` Declaration Convention (C-007)** — DEMOTE (drop a symbol from `__all__`, keep def) is the convention's intended move for non-public/internal symbols; each demoted module retains a valid (possibly smaller) `__all__`. ✅
- **ATDD-First (C-011)** — the gate's own suite is the acceptance oracle; every detector is test-driven, and the no-false-negative regression test (NFR-001) is the binding guard. ✅
- **Identifier Safety (DIR-001/002)** — N/A.
- **DIR-003** — assign #2158 to the HiC at implement start (best-effort; MOES-Media can't be assigned upstream).
- **Security** — FR-005 wires an unenforced unsafe-flag blocklist; this is a security *improvement*, reviewed as a behavior change.

No violations. No Complexity Tracking entries.

## Project Structure

### Documentation (this mission)
```
kitty-specs/harden-dead-symbol-gate-01KW0RJR/
├── plan.md · research.md · data-model.md · quickstart.md · spec.md
└── research/ (evidence-log.csv, source-register.csv)
```

### Source Code (repository root)
```
tests/architectural/
├── test_no_dead_symbols.py          # FR-001 parser fix (_extract_all_literal ~L938);
│                                     # FR-002 four detectors in _imports_by_target/_symbol_has_caller;
│                                     # new unit tests + the NFR-001 no-false-negative test
└── _baselines.yaml                  # justification + (documentary) symbol-gate counts; no net growth

src/specify_cli/
├── sync/owner.py                    # FR-003 DELETE _daemon_root re-export
├── auth/transport.py                # FR-004 demote reset_user_facing_dedup; FR-006 allowlist trio
├── sync/owner.py, compat/safety_modes.py, legacy_detector.py, readiness/upgrade_ux.py  # FR-004 demotes
├── doctrine/versioning.py, compat/safety_modes.py  # register-arg DEMOTEs (migrate_v1_to_v2, predicates)
└── orchestrator_api/envelope.py     # FR-005 wire BANNED_FLAGS check (+ test)
```

**Structure Decision**: The gate file (`test_no_dead_symbols.py`) is the hub — the parser fix, the 4
detectors, and their tests live there and must be coherent in one commit. The disposition edits (delete +
demotes) span ~10-15 src modules but each is a one-line `__all__` edit; they must all land with the gate
change so the gate is green at HEAD (a demoted/deleted symbol that's still in `__all__` elsewhere would
flag). The `BANNED_FLAGS` security fix is the one independent piece (different file, own test).

## Complexity Tracking

*No Charter Check violations — section intentionally empty.*

## Implementation Concern Map

> Concerns are NOT work packages. `/spec-kitty.tasks` translates these into WPs. IC-01 and IC-02 both
> end at the same gate run (`test_no_dead_symbols.py` must be green once detectors + dispositions land),
> so they share a lane; IC-03 is independent.

### IC-01 — Parser fix + the four in-gate detectors (the hard core)
- **Purpose**: Un-blind the 57 modules AND absorb the resulting 119-symbol wave by recognizing live-but-blind callers — without weakening the gate.
- **Relevant requirements**: FR-001, FR-002, NFR-001, C-001
- **Affected surfaces**: `tests/architectural/test_no_dead_symbols.py` — fix `_extract_all_literal` (`continue` on non-`__all__` AnnAssign); add detectors, anchored to a resolved declaring module via a per-tree import-alias map, folded into `_imports_by_target` (widen the import-edge index so `_symbol_has_caller`'s parent/submodule rules apply automatically) or a sibling `_nonimport_callers` pass:
  - **(a) module-style `alias.symbol`**: build alias map from `ast.Import`/`ImportFrom asname`; walk `ast.Attribute` whose `.value` is a known alias → `(resolved_module, attr)`.
  - **(c) Typer registration**: free — the `app.command()(mod.fn)` arg is an `ast.Attribute` (a)'s walk already visits.
  - **(d-getattr)**: `Call` to `getattr`, `args[1]` str Constant, `args[0]` resolved via the alias map.
  - **(b) `__getattr__` facade**: module with `def __getattr__` + static dict-literal `(submodule, "name")` tuples → mark the submodule's canonical symbol live.
- **Sequencing/depends-on**: Parser fix + all 4 detectors land in the SAME commit/WP (D-01) — otherwise the gate is red. Each detector ships with a focused unit test; the NFR-001 no-false-negative test is mandatory.
- **Risks**: A too-loose matcher masks real dead code (C-001). Mitigation: every rule resolves the alias to the exact declaring module before counting; reuse the stale-allowlist reverse check (L1093–1099) to self-surface over-broad rules; the no-false-negative regression test is the gate.

### IC-02 — Disposition of the genuinely-dead / non-public residue
- **Purpose**: Clean up what the detectors correctly DON'T rescue.
- **Relevant requirements**: FR-003, FR-004, FR-006, FR-007, NFR-003, C-002
- **Affected surfaces**: DELETE `sync.owner::_daemon_root`; DEMOTE from `__all__` (keep defs): the FR-004 set (`reset_user_facing_dedup`, `check_daemon_owner_match`, `_ORCHESTRATOR_API_UNSAFE_SUBCOMMANDS`, `SafetyPredicate` redundant re-export, `LEGACY_LANE_DIRS`, `PromptCallback`, `UpgradeUxOutcome`) PLUS the **register-arg** symbols (`doctrine.versioning::migrate_v1_to_v2`, `compat.safety_modes::_orchestrator_api_predicate`/`_mission_state_predicate`) PLUS any residual return-type/annotation-only or test-only symbols the detectors don't cover; ALLOWLIST-as-deferred the `auth.transport` trio with one justified entry; `_baselines.yaml` reflects the net (no growth).
- **Sequencing/depends-on**: Lands with IC-01 (same gate run). Re-verify each symbol against the live tree before demoting (C-004) — a demote is only safe if nothing does `from mod import *` and no external `from`-import exists.
- **Risks**: Demoting a symbol that IS externally imported would break that import — verify first. `category_a/b` net entry count must not grow (NFR-003).

### IC-03 — BANNED_FLAGS security fix (independent)
- **Purpose**: Close the latent gap — `BANNED_FLAGS` is defined but never enforced.
- **Relevant requirements**: FR-005, NFR-004
- **Affected surfaces**: `src/specify_cli/orchestrator_api/envelope.py` — `parse_and_validate_policy` rejects any `dangerous_flags` entry in `BANNED_FLAGS`; add a test (`--yolo` rejected). (This also makes `BANNED_FLAGS` a genuinely-live symbol, so it needs no disposition.)
- **Sequencing/depends-on**: Independent of IC-01/IC-02 (different file); could be its own WP/lane. Runtime behavior change — reviewed accordingly.
- **Risks**: Low. Ensure the rejection path returns the typed validation error the envelope contract expects.

## Out of Scope (design decisions)

- **Making the symbol-gate baselines a real ratchet** (research D-06): the `test_no_dead_symbols` section of `_baselines.yaml` is documentary-only and partial/stale vs the ~16 live frozensets. Wiring it into `test_ratchet_baselines.py` is its own task — **deferred to a follow-up**, not this mission. "No net growth" (NFR-003) is verified here by frozenset entry-count in review.
- A generic register-arg in-gate detector (decided: DEMOTE the few affected symbols instead).
- Wiring the `auth.transport` trio into the SaaS path (future migration wave; FR-006 only defers).
- The broader `category_b`/`legacy_contract` burn-down and `category_4` (#2152) — per #2049.
