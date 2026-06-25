# Mission Specification: Shrink Architectural Ratchet Allowlists

**Mission**: `shrink-ratchet-allowlists-01KW0EAZ`
**Type**: software-dev
**Status**: Draft
**Source**: [GitHub issue #2049](https://github.com/Priivacy-ai/spec-kitty/issues/2049) — "Shrink architectural ratchet exception allowlists (burn-down)"
**Requirements basis**: `docs/engineering_notes/2049-ratchet-burndown-audit.md` — a 5-agent research-squad audit (2026-06-25) that live-verified every removal below.

## Purpose

`tests/architectural/_baselines.yaml` is a **SHRINK ratchet**: each category count is meant to trend
toward zero, never up. The exception allowlists across the architectural suite have accumulated entries
whose original rationale no longer holds — symbols deleted, shims dead, contract files removed. This
mission removes the evidence-backed stale entries and corrects drift in the tracking issue. Sister issue
#2048 (the `category_4` `9→8` reversal) is handled separately in PR #2152 and is **out of scope** here.

> **Scope note (FR-006 deferred → #2158):** the dead-symbol-gate parser bug (`_extract_all_literal`) was
> originally in scope, but un-blinding it surfaces **~117 pre-existing dead symbols across ~57 modules**
> — a blast radius that would *grow* the ratchet, not shrink it. It is split out to its own issue
> [#2158](https://github.com/Priivacy-ai/spec-kitty/issues/2158). This mission delivers the clean
> allowlist removals only and does **not** touch the parser or `write_pipeline.py`.

## Domain Language

| Term | Meaning |
|------|---------|
| **SHRINK ratchet** | The `tests/architectural/_baselines.yaml` policy where a category count may only decrease (Slice F C-004). `test_ratchet_baselines.py` enforces declared-vs-live equality and forbids growth. |
| **Allowlist / exception entry** | A frozenset member exempting a specific dead module/symbol/file/contract from a gate. |
| **Stale entry** | An allowlist member whose exempting condition no longer applies (symbol gone, file deleted, contract removed) — inert at best, debt-masking at worst. |
| **Dead-symbol gate** | `test_no_dead_symbols.py` — flags an `__all__` symbol with no cross-module caller; exemptions live in `category_a/b/c` frozensets. |

## User Scenarios & Testing

### Primary scenario
**Actor:** Maintainer running the architectural + contract suites after the burn-down.
**Trigger:** `pytest tests/architectural/ tests/contract/` on the feature branch.
**Success outcome:** Suites pass with the four reduced baselines (`category_a_slice_f_deferred: 9`,
`category_b_grandfathered_legacy: 284`, `legacy_contract_allowlist: 151`, `pure_shim_files: 0`), each
matching its live frozenset size; the dead-symbol gate now inspects `write_pipeline.py`'s public symbols.

### Acceptance scenarios
1. **Given** the stale entries are removed and `_baselines.yaml` decremented, **when** `test_ratchet_baselines.py` runs, **then** every edited category's declared count equals its live frozenset size and no GROW violation fires.
2. **Given** the 3 `compat/_adapters/*` shim files are deleted with their sibling allowlists, **when** `test_compat_shims.py`, `test_no_dead_modules.py`, and `test_no_dead_symbols.py` run, **then** they pass with `pure_shim_files` and `category_5_wp_in_flight_adapters` at 0.
3. **Given** the dangling `legacy_contract_allowlist` entry is removed, **when** `tests/contract/test_example_round_trip.py` runs, **then** it passes with the entry gone.

### Edge cases
- Removing the 2 slice-F entries is safe even though the dead-symbol gate is blind to `write_pipeline.py` (the entries are inert) — the gate's blindness (and its fix) is out of scope (#2158); this mission must NOT touch the parser or `write_pipeline.py`.
- `pure_shim_files` and `category_5_wp_in_flight_adapters` pin the **same** 3 files; both must move to 0 together with the file deletions, or the dead-module gate flags the now-unallowlisted files.
- The `legacy_contract_allowlist` lives in `tests/contract/`, not `tests/architectural/` — the issue text is wrong (corrected by FR-005).

## Requirements

### Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | Remove the 2 stale entries `charter.synthesizer.write_pipeline::StagedArtifact` and `::promote` from `category_a_slice_f_deferred` (`tests/architectural/test_no_dead_symbols.py`) and set `_baselines.yaml` `category_a_slice_f_deferred` to **9** (live frozenset is currently 11 vs a stale declared 12; this both removes the 2 entries and fixes the drift). | Pending |
| FR-002 | Remove the 2 stale entries `specify_cli.cli.commands.charter.activate::charter_activate_app` and `…deactivate::charter_deactivate_app` from `category_b_grandfathered_legacy` (`test_no_dead_symbols.py`) — both symbols were deleted by a prior charter-app refactor (absence asserted by `tests/specify_cli/test_charter_activate_cli.py`) — and set `_baselines.yaml` `category_b_grandfathered_legacy` to **284**. | Pending |
| FR-003 | Remove the dangling entry `kitty-specs/033-github-observability-event-metadata/contracts/event-envelope.md` (mission dir no longer exists) from `legacy_contract_allowlist` in `tests/contract/test_example_round_trip.py` and set `_baselines.yaml` `legacy_contract_allowlist` to **151**. | Pending |
| FR-004 | Retire the 3 dead pure-shim adapter files `src/specify_cli/compat/_adapters/{version_checker,gate,detector}.py` (zero functional importers; real consumers use the canonical modules directly), removing their entries from `_ADAPTER_FILES` (`test_compat_shims.py`), `_CATEGORY_5_*` (`test_no_dead_modules.py`), and the dead-symbol allowlist (`test_no_dead_symbols.py`); set `_baselines.yaml` `pure_shim_files` to **0** and `category_5_wp_in_flight_adapters` to **0**. | Pending |
| FR-005 | Correct the drift in the tracking issue / docs: `legacy_contract_allowlist` lives in `tests/contract/` (not `tests/architectural/`); live counts are `category_7_grandfathered_orphans = 7` (issue said 6) and `category_b_grandfathered_legacy = 286` (issue said 271); note the parser fix moved to #2158. Record corrections in the mission artifacts / a comment on #2049. | Pending |

### Non-Functional Requirements

| ID | Requirement | Threshold / Measure | Status |
|----|-------------|---------------------|--------|
| NFR-001 | The full architectural + contract suites pass after the change. | `pytest tests/architectural/ tests/contract/` exits 0, including `test_ratchet_baselines.py`, `test_no_dead_modules.py`, `test_no_dead_symbols.py`, `test_compat_shims.py`, `test_example_round_trip.py`. | Pending |
| NFR-002 | No production behavior change beyond retiring dead intermediaries. | The only `src/` edits are deleting the 3 dead `compat/_adapters/*` shim files; their canonical targets (`core.version_checker`, `migration.gate`, `upgrade.detector`) are unchanged and real consumers already bypass the shims (grep proves zero functional importers). | Pending |
| NFR-003 | Lint and type gates stay green. | `ruff check .` and `mypy` report zero new issues on the diff. | Pending |
| NFR-004 | Every decremented baseline matches its live frozenset/file-list size. | `test_ratchet_baselines.py` cross-check passes for `category_a_slice_f_deferred`, `category_b_grandfathered_legacy`, `legacy_contract_allowlist`, `pure_shim_files`, `category_5_wp_in_flight_adapters`. | Pending |

### Constraints

| ID | Constraint | Status |
|----|-----------|--------|
| C-001 | Every `_baselines.yaml` decrement MUST exactly match the post-edit live frozenset/file-list size; the ratchet test enforces equality. | Active |
| C-002 | Each `_baselines.yaml` edit MUST carry a `# justification:` comment per the file's edit policy (lines 11–17), naming #2049 and the evidence. | Active |
| C-003 | File deletions (FR-004) and their allowlist removals MUST land together so the dead-module/symbol gates never see an un-allowlisted dead module at any commit. | Active |
| C-004 | This mission removes ONLY the evidence-backed stale entries audited above. The **full** burn-down of the large externally-owned categories (`category_b_grandfathered_legacy` residual via the C-007 grandfathered-legacy follow-on; the 15 active + 136 inert `legacy_contract` backfill entries) stays with their separate follow-on missions and is OUT OF SCOPE. | Active |
| C-005 | `category_4_backcompat_shims` (the `9→8` `mission_read_path` reversal) is OUT OF SCOPE — delivered by sister issue #2048 / PR #2152. This mission must not touch `category_4`. | Active |

## Success Criteria

1. Four baselines reduced and matching live sizes: `category_a_slice_f_deferred: 9`, `category_b_grandfathered_legacy: 284`, `legacy_contract_allowlist: 151`, `pure_shim_files: 0` (+ `category_5_wp_in_flight_adapters: 0`).
2. The 3 `compat/_adapters/*` shim files are gone; `grep -rn "compat._adapters" src/ tests/` returns only intentional references (ideally none).
3. `pytest tests/architectural/ tests/contract/` is green at the reduced baselines, with no net allowlist growth.
4. `ruff check .` and `mypy` are clean on the diff.
5. The PR closes #2049 (and records the FR-005 corrections); ~7 stale allowlist entries retired across 4 categories; the parser fix is tracked separately in #2158.

## Key Entities

- **`_baselines.yaml`** — the ratchet ledger (four keys decremented + one sibling).
- **`test_no_dead_symbols.py`** — holds the `category_a`/`category_b` frozensets (entries removed from each).
- **`test_compat_shims.py` / `test_no_dead_modules.py`** — hold the `pure_shim_files` / `category_5` adapter allowlists.
- **`tests/contract/test_example_round_trip.py`** — holds `legacy_contract_allowlist`.
- **`compat/_adapters/{version_checker,gate,detector}.py`** — the 3 dead shim files retired by FR-004.

## Assumptions

- The audit's evidence (squad-verified 2026-06-25) still holds at implementation time; the implementer re-confirms each removal against the live tree before editing (counts can drift as other missions land).
- The dead-symbol gate remains blind to `write_pipeline.py` (the parser bug is unfixed here, deferred to #2158), so removing the 2 slice-F entries is inert-safe and surfaces no new dead symbols.

## Out of Scope

- `category_4_backcompat_shims` (#2048 / PR #2152).
- The `_extract_all_literal` parser fix and the ~117-symbol cleanup it surfaces — deferred to **#2158** (its blast radius would grow, not shrink, the ratchet).
- `category_7_grandfathered_orphans` burn-down — requires wiring/deleting library modules (design work), not allowlist cleanup; none removable by this audit's evidence.
- The full burn-down of `category_b_grandfathered_legacy` and the `legacy_contract` frontmatter backfill — separate follow-on missions.
