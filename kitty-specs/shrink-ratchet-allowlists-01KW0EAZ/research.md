# Research: Shrink Architectural Ratchet Allowlists

Phase 0 output, re-reconciled after the refresh onto current `origin/main`. No open
`[NEEDS CLARIFICATION]` markers. Records the live re-confirmation of the delivered scope and why
`harden-dead-symbol-gate` overtook half of the original plan.

> **⚠️ Refresh reconciliation (2026-06-29):** PR #2159 was 97 commits behind `main` and was refreshed by
> recreating it on current `origin/main`. Main's `harden-dead-symbol-gate` mission had landed and
> OVERTOOK FR-001 (`category_a` `StagedArtifact`/`promote`), FR-002 (`category_b` `charter_*_app`), and
> FR-006 (the `_extract_all_literal` parser fix — it landed on main here). **Delivered scope is now
> FR-003 + FR-004 + an accuracy sync (FR-005).** Design notes below that described a parser fix or a
> `write_pipeline.__all__` trim are retained only as OVERTAKEN historical context.

## Live re-confirmation (refreshed tree on current `origin/main`, 2026-06-29)

| Key (`_baselines.yaml`) | Recorded (stale) | Live | Delivered | Note |
|--------------------------|------------------|------|-----------|------|
| `legacy_contract_allowlist` | 152 | 152 | **151** | FR-003; lives in `tests/contract/test_example_round_trip.py` (not architectural). Enforced. |
| `pure_shim_files` | 3 | 3 | **0** | FR-004; `_ADAPTER_FILES` glob self-empties on package deletion. Enforced. |
| `category_5_wp_in_flight_adapters` | 3 | 3 | **0** | FR-004; same adapter package, hardcoded list emptied. Enforced. |
| `category_a_slice_f_deferred` | 12 | 10 | **10** | FR-005 accuracy sync only — OVERTAKEN by main (rescued `promote` + one more). Informational, not enforced. |
| `category_b_grandfathered_legacy` | 286 | 273 | **264** | FR-005 accuracy sync (273 − 9 dead adapter symbols). Informational, not enforced. |
| `category_4_backcompat_shims` | 8 | 8 | 8 | OUT OF SCOPE (C-005); #2048 / PR #2152. Do NOT touch. |

## D-01 — `harden-dead-symbol-gate` overtook FR-001 / FR-002 / FR-006

- **Finding**: Refreshing onto current `origin/main` revealed that the `harden-dead-symbol-gate` mission
  had already landed: it fixed the `_extract_all_literal` parser (the work originally split to #2158),
  added new caller-detectors, and re-shaped `category_a`/`category_b`.
- **Consequence**:
  - **FR-001 OVERTAKEN** — main's new detectors rescued `write_pipeline::promote`; `StagedArtifact`
    remains legitimately allowlisted on main. This PR touches no `category_a` entry.
  - **FR-002 OVERTAKEN** — `charter.activate::charter_activate_app` /
    `charter.deactivate::charter_deactivate_app` no longer exist in `src/` on main; nothing to remove.
  - **FR-006 LANDED on main** — the parser fix is present on main; nothing owed here.
- **Decision**: Reduce delivered scope to the still-stale work that main did not clear — FR-003, FR-004 —
  plus an accuracy sync (FR-005) of the two informational baselines that drifted because `harden`
  landed without re-recording them.

## D-02 — Adapter package retirement spans 4 surfaces (FR-004)

Retiring the whole `compat/_adapters/` package (`detector.py`, `gate.py`, `version_checker.py`, and the
now-empty `__init__.py`) — zero functional importers, an abandoned WP05/WP07 migration seam whose real
cutover landed via `migration.gate` delegating directly to `compat.planner` — requires removing entries
from **four** places in lock-step (C-003):
1. `_CATEGORY_5_WP_IN_FLIGHT_ADAPTERS` in `tests/architectural/test_no_dead_modules.py` (hardcoded list — empty it).
2. `_ADAPTER_FILES` in `tests/architectural/test_compat_shims.py` (glob-discovered — self-empties on deletion).
3. the 9 `specify_cli.compat._adapters.*::*` dead-symbol entries in `_CATEGORY_B_GRANDFATHERED_LEGACY`
   (`tests/architectural/test_no_dead_symbols.py`).
4. `_baselines.yaml`: `pure_shim_files: 3 → 0` AND `category_5_wp_in_flight_adapters: 3 → 0` (both pin the
   same package).

Re-confirm zero `from ... import specify_cli.compat._adapters.*` in `src/` before deleting.

## D-03 — `MismatchType` orphan: demote, do not grandfather

- **Finding**: Deleting `compat/_adapters/version_checker.py` orphans
  `specify_cli.core.version_checker::MismatchType` (a `Literal` type alias) — the deleted adapter was its
  only cross-file importer. The original plan grandfathered it into the dead-symbol allowlist (the `+1`).
- **Decision (adversarial-review correction)**: **Demote** `MismatchType` out of `core/version_checker.py`'s
  `__all__` instead of grandfathering it. The dead-symbol gate scans only `__all__` names, so a
  non-exported alias is invisible to it.
- **Why this is better**: demotion closes the orphan at the root with **zero new allowlist debt** and no
  follow-up ticket owed; grandfathering would have left a `+1` entry to burn down later. The alias stays
  defined as an internal annotation on `compare_versions` / `format_version_error`, so there is zero
  functional change. This is why `category_b` lands at 264 (273 − 9), not 265.

## D-04 — Atomicity / shared-file coupling

- **Decision**: FR-004 (adapter package) and FR-005 (the `category_b` accuracy sync) both touch
  `tests/architectural/test_no_dead_symbols.py` and `_baselines.yaml`, so they land in a single lane,
  keeping the suite green at each commit.
- **Rationale**: C-001 (enforced baseline = live size) and the dead-module gate fail mid-way if a
  category's allowlist and the package deletion don't land together (C-003).

## D-05 — FR-005 is accuracy + documentation only

The `category_a`/`category_b` baselines under `test_no_dead_symbols:` are **not** cross-checked by
`test_ratchet_baselines.py` (it enforces only `test_no_dead_modules` / `test_compat_shims` /
`test_example_round_trip` and 3 others), so recording their true live sizes (10 and 264) is an accuracy
fix, not a gate requirement. The path/source corrections (legacy_contract lives in `tests/contract/`; the
parser fix landed on main via `harden-dead-symbol-gate`) are documentation-only.

---

### OVERTAKEN historical context (original pre-refresh plan — retained for traceability)

The original mission also planned an `_extract_all_literal` parser fix (D-01 in the pre-refresh draft)
and a paired `src/charter/synthesizer/write_pipeline.py` `__all__` trim to resolve the slice-F
(`category_a`) entries (`StagedArtifact`, `promote`, `compute_written_artifacts`). All of that is
**OVERTAKEN** — `harden-dead-symbol-gate` landed the parser fix on main and re-shaped `category_a` via
new caller-detectors. This PR does not touch the parser or `write_pipeline.py`.
