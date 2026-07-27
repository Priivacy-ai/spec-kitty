# Tasks: Charter-layer dead-code burndown + no-op-stability campsite

**Mission**: charter-deadcode-noop-campsite-01KXW0NY
**Branch**: `feat/charter-deadcode-noop-campsite`
**Plan**: [plan.md](./plan.md) · **Spec**: [spec.md](./spec.md) · **Data model / landmines**: [data-model.md](./data-model.md)

Four independent work packages (disjoint `owned_files`, no cross-WP dependency). Two pure
dead-code removals (WP01, WP02) and two no-op-stability concerns (WP03 render guard, WP04 the
deep preflight/freshness fix).

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Delete `src/charter/generator.py` | WP01 | [P] |
| T002 | Remove generator import + `__all__` entries from `src/charter/__init__.py` | WP01 | |
| T003 | Drop generator import + 4 generator-API tests in `test_generator.py`, keep the 4 compiler tests | WP01 | |
| T004 | Verify: zero live refs, gates green, ruff/mypy | WP01 | |
| T005 | Delete `src/charter/extractor.py` | WP02 | [P] |
| T006 | Retire dedicated Extractor tests; RECONSTRUCT the 2 incidental fixtures without Extractor | WP02 | |
| T007 | Remove ALL FOUR gate entries (baseline 1→0, modules, symbols, chokepoint carve-out) | WP02 | |
| T008 | Verify: dead-code + chokepoint gates green (no stale/dangling/missing), ruff/mypy | WP02 | |
| T009 | Red-first render-cleanliness guard on a doctrine-tracked repo | WP03 | [P] |
| T010 | Assert contract G1/G3; confirm green (no prod change expected) | WP03 | |
| T011 | Verify: pytest guard, ruff/mypy | WP03 | |
| T012 | Preflight no-op-stability guard (G2/G3) on a real-synthesized doctrine-tracked fixture | WP04 | [P] |
| T013 | INV-2 anti-over-suppression guard (G4/F3) — or cite existing coverage | WP04 | |
| T014 | Verify: guard green at HEAD, NO src change, ruff/mypy | WP04 | |

---

## WP01 — Retire `charter.generator` (dead WP03 wrapper)

**Priority**: P1 · **Prompt**: [tasks/WP01-retire-charter-generator.md](./tasks/WP01-retire-charter-generator.md)
**Requirements**: FR-001, FR-002; NFR-002; C-003, C-007 · **Tracker**: #1797
**Independent test**: `pytest tests/charter/test_generator.py tests/architectural/test_no_dead_modules.py`
green; `git grep` finds zero live refs; the 4 `write_compiled_charter` symlink-guard tests pass.

- [ ] T001 Delete `src/charter/generator.py` (WP01)
- [ ] T002 Remove `from .generator import ...` (line 31) + `__all__` entries (108-110) in `src/charter/__init__.py` (WP01)
- [ ] T003 In `tests/charter/test_generator.py`: drop the generator import + the 4 `build_charter_draft`/`write_charter` tests; KEEP the 4 `write_compiled_charter` symlink-guard tests (WP01)
- [ ] T004 Verify: zero live refs, gates green, ruff + mypy clean (WP01)

## WP02 — Retire `charter.extractor` + its deferred allowlist entries

**Priority**: P1 · **Prompt**: [tasks/WP02-retire-charter-extractor.md](./tasks/WP02-retire-charter-extractor.md)
**Requirements**: FR-003, FR-004; NFR-002; C-003, C-004 · **Tracker**: #1797
**Independent test**: `pytest tests/architectural/{test_no_dead_modules,test_no_dead_symbols,test_ratchet_baselines}.py`
green with `category_5_wp_in_flight_adapters = 0` and no stale/dangling entries.

- [ ] T005 Delete `src/charter/extractor.py` (WP02)
- [ ] T006 Retire the 5 dedicated Extractor test files; RECONSTRUCT the 2 incidental fixtures (`test_activate_resolves_no_answers_edit.py`, `test_charter_context_spdd_reasons.py`) inline without Extractor so their live SPDD-activation assertions survive (WP02)
- [ ] T007 Remove ALL FOUR gate entries: `_baselines.yaml` category_5 1→0; `test_no_dead_modules.py` entry; `test_no_dead_symbols.py` SymbolKey frozenset + union term; `test_chokepoint_coverage.py:61` carve-out (WP02)
- [ ] T008 Verify: dead-code + chokepoint gates green (no stale/dangling/missing carve-out), baseline shrunk downward, ruff + mypy clean (WP02)

## WP03 — Render-path no-op-stability guard (#2373 render surface)

**Priority**: P1 · **Prompt**: [tasks/WP03-render-cleanliness-guard.md](./tasks/WP03-render-cleanliness-guard.md)
**Requirements**: FR-005, FR-008; NFR-001 · **Tracker**: #2373, #1914
**Independent test**: `pytest tests/charter/test_context_noop_stability.py` — `build_charter_context`
on a doctrine-tracked repo leaves `git status --porcelain` empty (only untracked runtime state).

- [ ] T009 Add red-first guard: `build_charter_context` on a **doctrine-tracked** temp repo (exclude removed) → tree clean (WP03)
- [ ] T010 Assert contract G1/G3; confirm GREEN — no prod change expected (if red, that is a real regression → escalate) (WP03)
- [ ] T011 Verify: pytest guard, ruff + mypy clean (WP03)

## WP04 — Preflight no-op-stability regression guard (#2373 already-remediated) — GUARD ONLY

**Priority**: P1 · **Prompt**: [tasks/WP04-freshness-noop-stability-fix.md](./tasks/WP04-freshness-noop-stability-fix.md)
**Requirements**: FR-006, FR-007, FR-008; NFR-001 · **Tracker**: #2373, #1914
**⚠ Scope reversed by the post-tasks squad:** #2373's residual churn is already fixed at HEAD
(#2773 + #2732 content-hash freshness + #1912 promote guards). **No behavioral change** — this WP
only adds a preflight-level regression guard pinning the already-correct behavior and closes #2373.
**Independent test**: on a real-synthesized doctrine-tracked committed-clean fixture, run
`run_charter_preflight(auto_refresh=True)` twice → `git status` clean, synthesize uninvoked; a
genuine `charter.yaml` edit still reports stale.

- [ ] T012 Preflight no-op-stability guard (G2/G3) on a real-synthesized doctrine-tracked fixture — green at HEAD (WP04)
- [ ] T013 INV-2 anti-over-suppression guard (G4/F3): a substantive `charter.yaml` change still synthesizes — or cite existing `test_computer.py` coverage (WP04)
- [ ] T014 Verify: guard green, NO change to `charter_runtime`/synthesizer src, ruff + mypy --strict (WP04)

---

## Dependencies & Lanes

All four WPs are independent (disjoint `owned_files`, no code dependency). `finalize-tasks`
computes lanes; expect ~2-4 lanes. WP01 and WP02 are pure removals; WP03 is test-only; WP04 is
the sole behavioral change.

## Landmines (see data-model.md)

- **LM-1** — the working checkout's local `.git/info/exclude` masks doctrine churn; WP03/WP04
  reproduce in a doctrine-tracked checkout or the "fix" is static-fixed.
- **LM-2** — WP02 must delete the module AND all three allowlist entries together (else gate red).
- **LM-3** — WP01 must not delete `test_generator.py` wholesale (surviving compiler tests).
- **LM-5** — WP04 must not over-suppress genuine staleness (INV-2).
