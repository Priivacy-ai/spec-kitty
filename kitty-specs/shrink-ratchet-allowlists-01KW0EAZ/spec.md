# Mission Specification: Shrink Architectural Ratchet Allowlists

**Mission**: `shrink-ratchet-allowlists-01KW0EAZ`
**Type**: software-dev
**Status**: Delivered (refreshed onto current `origin/main`)
**Source**: [GitHub issue #2049](https://github.com/Priivacy-ai/spec-kitty/issues/2049) — "Shrink architectural ratchet exception allowlists (burn-down)"
**PR**: #2159
**Requirements basis**: `docs/engineering_notes/2049-ratchet-burndown-audit.md` — a 5-agent research-squad audit (2026-06-25) that live-verified the original removal set. Re-reconciled against current `origin/main` (see the Refresh reconciliation note below).

> ## Refresh reconciliation (2026-06-29)
>
> PR #2159 was 97 commits behind `main` and was refreshed by recreating it on current `origin/main`.
> During the refresh we discovered that main's **`harden-dead-symbol-gate` mission has since LANDED**,
> which OVERTOOK roughly half of the original plan:
>
> - **FR-001** (remove `charter.synthesizer.write_pipeline::StagedArtifact` / `::promote` from
>   `category_a`) — **OVERTAKEN**. Main's new caller-detectors rescued `promote`; `StagedArtifact`
>   remains legitimately allowlisted on main. This PR does **not** touch `category_a` entries.
> - **FR-002** (remove `charter.activate::charter_activate_app` / `charter.deactivate::charter_deactivate_app`
>   from `category_b`) — **OVERTAKEN**. Those symbols no longer exist in `src/` on main. This PR does
>   **not** touch them.
> - **FR-006** (the `_extract_all_literal` parser fix, already deferred to #2158 in the original plan) —
>   **LANDED on main** as part of `harden-dead-symbol-gate`.
>
> **Delivered scope is now: FR-003 + FR-004 + an accuracy sync (FR-005) of two unenforced
> informational baselines.** The orphan left by the adapter deletion
> (`core.version_checker::MismatchType`) was **demoted** from `version_checker.py`'s `__all__`, **not**
> grandfathered into any allowlist — so it closes at the root with zero new allowlist debt and no
> follow-up ticket owed.

## Purpose

`tests/architectural/_baselines.yaml` is a **SHRINK ratchet**: each category count is meant to trend
toward zero, never up. The exception allowlists across the architectural suite had accumulated entries
whose original rationale no longer held — shims dead, contract files removed. After the refresh onto
current `origin/main`, this mission removes the still-stale entries that main did not already clear, and
records the true live size of two informational baselines that drifted when `harden-dead-symbol-gate`
landed without re-recording them. Sister issue #2048 (the `category_4` reversal) is handled separately in
PR #2152 and is **out of scope** here.

## Domain Language

| Term | Meaning |
|------|---------|
| **SHRINK ratchet** | The `tests/architectural/_baselines.yaml` policy where a category count may only decrease (Slice F C-004). `test_ratchet_baselines.py` enforces declared-vs-live equality and forbids growth — but only for the keys it inspects (see "enforced vs unenforced"). |
| **Allowlist / exception entry** | A frozenset member exempting a specific dead module/symbol/file/contract from a gate. |
| **Stale entry** | An allowlist member whose exempting condition no longer applies (symbol gone, file deleted, contract removed) — inert at best, debt-masking at worst. |
| **Dead-symbol gate** | `test_no_dead_symbols.py` — flags an `__all__` symbol with no cross-module caller; exemptions live in `category_a/b/c` frozensets. The gate scans **only `__all__` names**, so demoting a symbol out of `__all__` closes its orphan with no allowlist entry. |
| **Enforced vs unenforced baseline** | `test_ratchet_baselines.py` enforces declared-vs-live equality for `test_no_dead_modules` / `test_compat_shims` / `test_example_round_trip` (and 3 others). The `test_no_dead_symbols:` section (`category_a_*`, `category_b_*`) is **informational only** — not cross-checked — so its recorded values can silently drift. |

## User Scenarios & Testing

### Primary scenario
**Actor:** Maintainer running the architectural + contract suites after the refreshed burn-down.
**Trigger:** `pytest tests/architectural/ tests/contract/` on the refreshed PR branch.
**Success outcome:** Suites pass with `pure_shim_files: 0`, `category_5_wp_in_flight_adapters: 0`, and
`legacy_contract_allowlist: 151` (the enforced baselines), each matching its live frozenset/file-list
size; the two informational baselines record their true live sizes
(`category_a_slice_f_deferred: 10`, `category_b_grandfathered_legacy: 264`).

### Acceptance scenarios
1. **Given** the dangling `legacy_contract_allowlist` entry is removed, **when** `tests/contract/test_example_round_trip.py` runs, **then** it passes with the entry gone and `_baselines.yaml` `legacy_contract_allowlist: 151`.
2. **Given** the entire `compat/_adapters/` package is deleted with its sibling allowlists, **when** `test_compat_shims.py`, `test_no_dead_modules.py`, and `test_no_dead_symbols.py` run, **then** they pass with `pure_shim_files` and `category_5_wp_in_flight_adapters` at 0 and the 9 dead adapter symbols removed from `category_b`.
3. **Given** the adapter deletion orphans `core.version_checker::MismatchType`, **when** the dead-symbol gate runs, **then** no orphan is flagged because `MismatchType` was demoted out of `version_checker.py`'s `__all__` (not grandfathered).
4. **Given** `harden-dead-symbol-gate` landed on main without re-recording the informational baselines, **when** their live frozenset sizes are read, **then** `_baselines.yaml` records `category_a_slice_f_deferred: 10` and `category_b_grandfathered_legacy: 264`.

### Edge cases
- `pure_shim_files` and `category_5_wp_in_flight_adapters` pin the **same** adapter package; both must move to 0 together with the package deletion, or the dead-module gate flags the now-unallowlisted files.
- `_ADAPTER_FILES` (`test_compat_shims.py`) is glob-discovered from the adapters dir, so deleting the package self-empties it; `_CATEGORY_5_WP_IN_FLIGHT_ADAPTERS` is a hardcoded list and must be emptied explicitly.
- The `legacy_contract_allowlist` lives in `tests/contract/`, not `tests/architectural/` — the issue text is wrong (corrected by FR-005).
- The `category_a`/`category_b` baselines are unenforced; recording their true live size is an accuracy fix, not a gate requirement.

## Requirements

### Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | ~~Remove `charter.synthesizer.write_pipeline::StagedArtifact` and `::promote` from `category_a_slice_f_deferred`.~~ | **OVERTAKEN** — main's `harden-dead-symbol-gate` rescued `promote` via new caller-detectors; `StagedArtifact` remains legitimately allowlisted on main. This PR does NOT touch `category_a` entries. |
| FR-002 | ~~Remove `charter.activate::charter_activate_app` and `charter.deactivate::charter_deactivate_app` from `category_b_grandfathered_legacy`.~~ | **OVERTAKEN** — those symbols no longer exist in `src/` on main. This PR does NOT touch them. |
| FR-003 | Remove the dangling entry `kitty-specs/033-github-observability-event-metadata/contracts/event-envelope.md` (mission dir no longer exists on main) from `_LEGACY_CONTRACT_ALLOWLIST` in `tests/contract/test_example_round_trip.py` and set `_baselines.yaml` `legacy_contract_allowlist: 152 → 151`. | **Delivered** |
| FR-004 | Delete all three pure-shim adapter files `src/specify_cli/compat/_adapters/{detector,gate,version_checker}.py` AND the now-empty package `src/specify_cli/compat/_adapters/__init__.py` — the whole package is removed (an abandoned WP05/WP07 migration seam; the real cutover landed via `migration.gate` delegating directly to `compat.planner`). Consequences: empty `_CATEGORY_5_WP_IN_FLIGHT_ADAPTERS` (`test_no_dead_modules.py`) → `category_5_wp_in_flight_adapters: 3 → 0`; `_ADAPTER_FILES` (`test_compat_shims.py`) is glob-discovered so self-empties → `pure_shim_files: 3 → 0`; remove the 9 dead `specify_cli.compat._adapters.*::*` symbol entries from `_CATEGORY_B_GRANDFATHERED_LEGACY` (`test_no_dead_symbols.py`). The deletion orphans `specify_cli.core.version_checker::MismatchType` (a `Literal` type alias whose only cross-file importer was the deleted adapter): it is **DEMOTED from `core/version_checker.py`'s `__all__` — NOT grandfathered**. The gate scans only `__all__` names, so demotion closes the orphan at the root with zero new allowlist debt and no follow-up ticket owed. | **Delivered** |
| FR-005 | Accuracy-sync the two **UNENFORCED** informational baselines under `test_no_dead_symbols:` in `_baselines.yaml` (this section is NOT cross-checked by `test_ratchet_baselines.py`), whose values went stale when `harden-dead-symbol-gate` landed without re-recording them: `category_a_slice_f_deferred: 12 → 10` (main's new caller-detectors rescued `write_pipeline::promote` and one more; live frozenset == 10 — this PR removes no `category_a` entry itself) and `category_b_grandfathered_legacy: 286 → 264` (live drifted to 273 on main; this PR removes the 9 dead adapter symbols → 273 − 9 = 264; no `+1` because `MismatchType` was demoted, not added). Also correct the tracking-issue/doc drift: `legacy_contract_allowlist` lives in `tests/contract/` (not `tests/architectural/`); the parser fix landed on main via `harden-dead-symbol-gate` (originally split to #2158). | **Delivered** |

### Non-Functional Requirements

| ID | Requirement | Threshold / Measure | Status |
|----|-------------|---------------------|--------|
| NFR-001 | The full architectural + contract suites pass after the change. | `pytest tests/architectural/ tests/contract/` exits 0, including `test_ratchet_baselines.py`, `test_no_dead_modules.py`, `test_no_dead_symbols.py`, `test_compat_shims.py`, `test_example_round_trip.py`. | Pass |
| NFR-002 | No production behavior change beyond retiring dead intermediaries. | The only `src/` edits are deleting the `compat/_adapters/` package (3 shims + the empty `__init__.py`) and demoting `MismatchType` out of `core/version_checker.py`'s `__all__` (the `Literal` alias stays defined; canonical modules unchanged; real consumers already bypass the shims). | Pass |
| NFR-003 | Lint and type gates stay green. | `ruff check .` and `mypy` report zero new issues on the diff. | Pass |
| NFR-004 | Every **enforced** decremented baseline matches its live frozenset/file-list size. | `test_ratchet_baselines.py` cross-check passes for `legacy_contract_allowlist`, `pure_shim_files`, `category_5_wp_in_flight_adapters`. (The `category_a`/`category_b` informational baselines are not cross-checked; their recorded values are synced to the true live size for accuracy.) | Pass |

### Constraints

| ID | Constraint | Status |
|----|-----------|--------|
| C-001 | Every **enforced** `_baselines.yaml` decrement MUST exactly match the post-edit live frozenset/file-list size; the ratchet test enforces equality for those keys. | Active |
| C-002 | Each `_baselines.yaml` edit MUST carry a `# justification:` comment per the file's edit policy (lines 11–17), naming #2049 and the evidence. | Active |
| C-003 | The `compat/_adapters/` package deletion (FR-004) and its allowlist removals MUST land together so the dead-module/symbol gates never see an un-allowlisted dead module at any commit. | Active |
| C-004 | This mission removes ONLY the still-stale entries that main's `harden-dead-symbol-gate` did not already clear. The full burn-down of the large externally-owned categories stays with their separate follow-on missions and is OUT OF SCOPE. | Active |
| C-005 | `category_4_backcompat_shims` stays at main's value **8** — OUT OF SCOPE, owned by sister issue #2048 / PR #2152. This mission must not touch `category_4`. | Active |

## Success Criteria

1. Enforced baselines reduced and matching live sizes: `legacy_contract_allowlist: 151`, `pure_shim_files: 0`, `category_5_wp_in_flight_adapters: 0`. Informational baselines synced to live: `category_a_slice_f_deferred: 10`, `category_b_grandfathered_legacy: 264`.
2. The `compat/_adapters/` package is gone (3 shims + empty `__init__.py`); `grep -rn "compat._adapters" src/ tests/` returns only intentional references (ideally none); `MismatchType` demoted out of `version_checker.__all__`.
3. `pytest tests/architectural/ tests/contract/` is green at the reduced baselines, with no net allowlist growth.
4. `ruff check .` and `mypy` are clean on the diff.
5. The PR (#2159) advances #2049 with the delivered scope (FR-003 + FR-004 + accuracy sync) and records that `harden-dead-symbol-gate` overtook FR-001/FR-002/FR-006.

## Key Entities

- **`_baselines.yaml`** — the ratchet ledger (3 enforced keys decremented + 2 informational keys synced; `category_4` left at 8).
- **`test_no_dead_symbols.py`** — holds the `category_a`/`category_b` frozensets (9 adapter symbols removed from `category_b`).
- **`test_compat_shims.py` / `test_no_dead_modules.py`** — hold the `pure_shim_files` (glob-discovered) / `category_5` adapter allowlists.
- **`tests/contract/test_example_round_trip.py`** — holds `_LEGACY_CONTRACT_ALLOWLIST`.
- **`compat/_adapters/` package** — the dead shim package retired by FR-004 (`detector.py`, `gate.py`, `version_checker.py`, `__init__.py`).
- **`core/version_checker.py`** — `MismatchType` demoted out of `__all__` (the only `src/` non-deletion edit).

## Assumptions

- The refreshed tree on current `origin/main` is the ground truth; the implementer re-confirms each removal/baseline against the live tree before editing.
- `harden-dead-symbol-gate` has fully landed on main (its parser fix and new caller-detectors are present), so FR-001/FR-002/FR-006 are genuinely overtaken and need no action here.

## Out of Scope

- `category_4_backcompat_shims` — stays at main's value **8** (#2048 / PR #2152, C-005).
- The `_extract_all_literal` parser fix — landed on main via `harden-dead-symbol-gate` (originally split to #2158); nothing owed here.
- `category_a`/`category_b` entry removals — OVERTAKEN by main (FR-001/FR-002); this PR only records their true live size.
- The full burn-down of `category_b_grandfathered_legacy` and the `legacy_contract` frontmatter backfill — separate follow-on missions.
