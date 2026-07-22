# Implementation Plan: Charter-layer dead-code burndown + no-op-stability campsite

**Branch**: `feat/charter-deadcode-noop-campsite` | **Date**: 2026-07-19 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/charter-deadcode-noop-campsite-01KXW0NY/spec.md`

## Summary

Retire two confirmed-dead charter modules (`charter.generator`, `charter.extractor`) and their
deferred arch-gate allowlist entries — shrinking the dead-code baselines downward — and make the
governed charter render/preflight/synthesize surface no-op-stable so a governed read on a clean
tree never dirties git (#2373/#1914). The render-path bug is already fixed by #2773; the residual
churn is a `synthesized_drg` freshness-misfire in `charter_runtime` that triggers a needless
`charter synthesize`. Behavior-preserving except the intentional no-op-stability fix and the
dead-code removals. Grounded by a pre-spec research squad (see [research.md](./research.md)).

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: charter layer (`src/charter/`), `src/specify_cli/charter_runtime/`
(preflight + freshness), the arch dead-code gate harness (`tests/architectural/`)
**Storage**: filesystem — `.kittify/charter/charter.yaml` (authoritative), `.kittify/doctrine/**`
(git-tracked doctrine artifacts), `.kittify/charter/context-state.json` (untracked runtime state)
**Testing**: pytest (`tests/charter/`, `tests/architectural/`, `tests/specify_cli/charter_runtime/`,
`tests/charter/synthesizer/`); ATDD red-first through the pre-existing entry points
(`charter context`, `charter synthesize`, the preflight runner, the arch gates)
**Target Platform**: Linux/macOS/Windows dev + CI
**Project Type**: single (CLI library)
**Performance Goals**: no new subprocess on a pure render/read path (NFR-003); a no-op must be
cheaper, not costlier
**Constraints**: `src/charter/` must not import `specify_cli` (C-002 layer boundary); do not reopen
#2773 invariants (C-001); baselines move only downward (C-003); ruff + mypy --strict clean, zero new
suppressions, complexity ≤ 15
**Scale/Scope**: ~2 module deletions + ~7 test-file retirements + 3 allowlist edits + a focused
freshness-misfire fix with regression guards; net tracked-source LOC delta negative

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **ATDD-First (C-011)** — every behavioral change (the freshness fix) and every guard lands via a
  red-first test through the pre-existing entry point. Dead-code removals are proven by the arch
  gates going/staying green with shrunk baselines. **PASS (by construction).**
- **Burn-down Policy (C-004) / dead-code baselines** — removals shrink baselines DOWNWARD with
  justification; no green-wash upward. **PASS.**
- **`__all__` Convention (C-007)** — deleting `charter.generator` requires removing its `__init__.py`
  import + `__all__` entries in the same change. **PASS (owned by IC-01).**
- **Layer boundary (C-002, `test_shared_package_boundary`)** — the preflight/freshness fix lives in
  `specify_cli.charter_runtime`, NOT `src/charter/`; no new `src/charter/ → specify_cli` import.
  **PASS.**
- **Terminology Canon (`test_no_legacy_terminology`)** — no user-facing prose change expected;
  run the guard before push if any doctrine/prose is touched. **PASS.**
- **No #2773 regression (C-001)** — charter.yaml authority, FLAT activation, `charter:` pointer,
  manifest v2, fail-loud all untouched. **PASS.**

No violations → Complexity Tracking table intentionally empty.

## Project Structure

### Documentation (this mission)

```
kitty-specs/charter-deadcode-noop-campsite-01KXW0NY/
├── plan.md              # This file
├── research.md          # Phase 0 — pre-spec research-squad grounding
├── data-model.md        # Phase 1 — the two removals + the freshness-misfire + landmines
├── contracts/           # Phase 1 — no-op-stability contract + freshness-signal contract
├── traces/              # tracer files (tooling-friction / approach / design-decisions)
└── tasks.md             # Phase 2 (/spec-kitty.tasks — not created here)
```

### Source Code (repository root)

```
src/charter/
├── generator.py                     # IC-01: DELETE (dead WP03 wrapper)
├── extractor.py                     # IC-02: DELETE (dead prose→triad scraper husk)
└── __init__.py                      # IC-01: remove generator import + __all__ entries

src/specify_cli/charter_runtime/
├── freshness/computer.py            # IC-04: fix synthesized_drg no-op misfire
└── preflight/runner.py              # IC-04: ensure auto-refresh does not churn on a no-op

tests/charter/
├── test_generator.py                # IC-01: drop generator import + 4 generator tests; KEEP 4 compiler tests
├── test_extractor*.py               # IC-02: retire (Extractor-dedicated)
├── test_sync_authority_paths.py     # IC-02: retire / de-Extractor
├── test_sync_references.py          # IC-02: retire / de-Extractor (line 156 already broken)
├── test_context*.py                 # IC-03: render-cleanliness guard
└── synthesizer/test_*.py            # IC-04: synthesize-twice no-op ratchet

tests/architectural/
├── _baselines.yaml                  # IC-02: category_5_wp_in_flight_adapters 1 → 0
├── test_no_dead_modules.py          # IC-02: remove "charter.extractor" allowlist entry
└── test_no_dead_symbols.py          # IC-02: remove Extractor SymbolKey frozenset + union term
```

**Structure Decision**: single-project layout. Two removal concerns (charter layer + arch gates),
one render-guard concern, one runtime freshness-fix concern. `owned_files` are partitioned so no two
concerns write the same file (see ICM).

## Complexity Tracking

*No Charter Check violations — table intentionally empty.*

## Implementation Concern Map

> Concerns are NOT work packages. `/spec-kitty.tasks` maps these to executable WPs.

### IC-01 — Retire `charter.generator`

- **Purpose**: Delete the dead WP03 wrapper (`CharterDraft`/`build_charter_draft`/`write_charter`)
  and its package reexport, leaving no functional gap.
- **Relevant requirements**: FR-001, FR-002; NFR-002; C-003, C-007.
- **Affected surfaces**: `src/charter/generator.py` (delete); `src/charter/__init__.py` (line 31
  import + `__all__` lines 108-110); `tests/charter/test_generator.py` (drop line-10 import + the 4
  `build_charter_draft`/`write_charter` tests; KEEP the 4 `write_compiled_charter` symlink-guard tests).
- **Sequencing/depends-on**: none.
- **Risks**: `test_generator.py` cannot be deleted wholesale (hosts surviving compiler tests) — surgical
  edit only. Landmine cleared: nothing bootstraps an initial `charter.md` from generator (research §1).

### IC-02 — Retire `charter.extractor` + its deferred allowlist entries

- **Purpose**: Delete the dead `Extractor` scraper husk and remove the three arch-gate allowlist
  entries in the same change so the gates stay green and the baseline shrinks downward.
- **Relevant requirements**: FR-003, FR-004; NFR-002; C-003, C-004.
- **Affected surfaces**: `src/charter/extractor.py` (delete); `tests/architectural/_baselines.yaml:58`
  (`category_5_wp_in_flight_adapters` 1→0); `tests/architectural/test_no_dead_modules.py:339-344`
  (remove entry); `tests/architectural/test_no_dead_symbols.py:907-913` (remove SymbolKey frozenset +
  its `|` term in `_SYMBOL_ALLOWLIST`); the Extractor-importing test files
  (`test_extractor*.py`, `test_sync_authority_paths.py`, `test_sync_references.py`, and the Extractor
  usage in `test_activate_resolves_no_answers_edit.py` / `test_charter_context_spdd_reasons.py`).
- **Sequencing/depends-on**: none (independent of IC-01; disjoint `owned_files`).
- **Risks**: deleting the module/class WITHOUT removing all three allowlist entries turns
  `test_no_dead_modules` stale-red and `test_no_dead_symbols` dangling-red — they MUST ship together.
  Task decomposition must check whether `test_activate_resolves_no_answers_edit.py` /
  `test_charter_context_spdd_reasons.py` are Extractor-dedicated (retire) or merely import it
  (de-Extractor only) — do not drop unrelated coverage (C-003).

### IC-03 — Render-path no-op-stability guard (#2373 render surface)

- **Purpose**: Lock in the already-shipped #2773 fix — a red-first test asserting `build_charter_context`
  writes no git-tracked artifact (only untracked runtime state).
- **Relevant requirements**: FR-005, FR-008; NFR-001.
- **Affected surfaces**: a new/extended guard in `tests/charter/test_context*.py`. No production change
  expected in `src/charter/context.py`; if the guard fails there, that is a real regression to fix.
- **Sequencing/depends-on**: none.
- **Risks**: must assert cleanliness in a doctrine-tracked context, not this masked checkout (FR-007).

### IC-04 — Preflight/synthesize freshness no-op-stability fix (#2373 residual, #1914)

- **Purpose**: Fix the `synthesized_drg` freshness-misfire so a genuine no-op is judged fresh and the
  preflight auto-refresh does not shell out to `charter synthesize` and churn tracked doctrine.
- **Relevant requirements**: FR-006, FR-007, FR-008; NFR-001, NFR-003; C-002, C-005.
- **Affected surfaces**: `src/specify_cli/charter_runtime/freshness/computer.py` (the staleness signal);
  `src/specify_cli/charter_runtime/preflight/runner.py` (only if the no-op guard belongs there);
  synthesizer no-op ratchet tests under `tests/charter/synthesizer/` +
  `tests/specify_cli/charter_runtime/`.
- **Sequencing/depends-on**: none (distinct subsystem from IC-01/IC-02); independent of the removals.
- **Risks**: **red-first reproduction requires a doctrine-tracked checkout** — this working tree's local
  `.git/info/exclude` masks the churn (research §3). The fix must suppress *no-op* churn ONLY, never
  genuine `charter.yaml`/pack staleness (spec US2 scenario 4). Keep doctrine artifacts materialized
  (C-005) — do not make them on-demand-only.

### Mission hygiene (not an IC — coord-partition artifacts)

- `issue-matrix.md` with #2373 (+ epic refs #1797/#1914); assign operator; comment on #2373 naming the
  mission. Tracer files (`traces/`) seeded at planning, appended during implement, assessed at close.
