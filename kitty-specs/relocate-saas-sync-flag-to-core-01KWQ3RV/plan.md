# Implementation Plan: Relocate SaaS-Sync Flag to Core

**Mission**: relocate-saas-sync-flag-to-core-01KWQ3RV
**Branch contract**: current = base = merge-target = `feat/relocate-saas-sync-flag-to-core` (PR'd upstream to `Priivacy-ai:main`)
**Spec**: [spec.md](./spec.md)
**Status**: Plan (Phase 1 complete)

## Summary

Close the last CORE↛INTEGRATION allowlist exemption (#2252). Move the pure
`SPEC_KITTY_ENABLE_SAAS_SYNC` reader from INTEGRATION `saas/rollout.py` into a new
CORE module `core/saas_sync_config.py`, repoint the sole CORE importer
(`readiness/coordinator.py:237`), retain `saas/rollout.py` + the `saas/__init__`
and `sync`/`tracker` `feature_flags` surfaces as thin re-export shims, empty the
`ALLOWLIST` and tighten the count-ratchet to `== 0`, and record the resolution in
the ADR + stability contract. Behavior-preserving; single canonical definition.

## Technical Context

- **Language/Version**: Python 3.11+
- **Primary Dependencies**: standard library only for the moved code (`os`); `pytest`, `ruff`, `mypy --strict` for gates. No new runtime dependencies.
- **Storage / State**: none. The flag is a stateless env read.
- **Testing**: `pytest`, scoped to the change's bounding packages (charter Testing Requirements — no full-suite run for a scoped change): `tests/architectural/test_integration_boundary.py`, `tests/saas/`, `tests/**/*feature_flag*`, `tests/contract/test_example_round_trip.py`.
- **Target platform**: cross-platform CLI (`spec-kitty-cli`).
- **Project type**: single Python package (`src/specify_cli/`).
- **Performance goals**: n/a (import-graph refactor; no hot-path change).
- **Constraints**: CORE↛INTEGRATION boundary (the mission's subject); single canonical authority (DIRECTIVE_044); ATDD red-first (C-011); terminology canon; the byte-frozen `saas_rollout.md` contract.

## Charter Check

- **Single canonical authority (DIRECTIVE_044)**: exactly one `def is_saas_sync_enabled` / `def saas_sync_disabled_message` post-mission, in `core/saas_sync_config.py`; every other surface re-exports. New module is the sole owner of this concern — not a second authority. ✔
- **Architectural alignment (DIRECTIVE_001)**: the move *restores* the declared boundary (removes the last CORE→INTEGRATION edge). ✔
- **ATDD-first (C-011)**: the allowlist removal is the red-first pin — `test_no_core_imports_integration` reds until the relocation lands (verified). ✔
- **Campsite cleaning (DIRECTIVE_025)**: fold only the domain-matched, now-stale docstrings that name the relocated module — `sync/feature_flags.py:1` + `tracker/feature_flags.py:1` ("canonical home is `saas.rollout`" → `core.saas_sync_config`), and `readiness/upgrade_ux.py:77` ("Stable truthy parser shared with `saas.rollout`", which is *already* false — it is a divergent copy, not shared). Reword `upgrade_ux.py`'s docstring to drop the false "shared" claim (do NOT re-point it to a module it still doesn't consume); the 3-way truthy-grammar unification is tracked as a follow-up, not folded (out of scope). No unrelated debt. ✔
- **Architectural gate discipline (DIRECTIVE_043)**: tighten the ratchet `<=1 → ==0` (close the defect class by construction); keep the negative-control injection proof so the gate stays non-vacuous. Post-merge: run the boundary + arch-gate sweep with a cross-base pre-existing check. ✔
- **Terminology canon**: no new `feature*` identifiers introduced. ✔
- No charter conflicts.

## Phase 0 — Research (resolved)

Full rationale in [research.md](./research.md). Resolutions:

- **Target module → `core/saas_sync_config.py` (new)**, not a join into `core/config.py`. `core/config.py` is a static-choices constants module; a focused module keeps the runtime env-reader cohesive, is the single authority, and imports only `os` (no cycle). (D-01)
- **`saas/rollout.py` → retained as a thin re-export shim, NOT deleted** (forced by NFR-001: `tests/saas/test_rollout.py:16` hard-imports it and asserts shim object-identity; deletion would edit that test). (D-02)
- **Ratchet → tightened `<=1` to `==0`** to close the exemption class permanently, plus remove the now-stale positive-control assertion in `test_allowlist_cannot_be_bypassed` (it hard-codes the removed crossing and would stay red); keep the negative control. (D-03)
- **Stability contract**: it lives in `kitty-specs/082-stealth-gated-saas-sync-hardening/contracts/saas_rollout.md` and pins the module location. Decision: **edit in place** with a version bump + a "relocated by #2252" note. Correction from the post-plan gate: the file is listed in `_LEGACY_CONTRACT_ALLOWLIST` (`test_example_round_trip.py:140`) AND has **zero code blocks**, so the round-trip test **warns-not-fails and does not content-validate it** — an in-place prose/location edit is safe and cannot red that test (do not add a `yaml` codeblock, which would opt it into validation). Editing it is still correct so the contract stops naming the wrong location. (D-04)

## Phase 1 — Design

### The move (FR-001)
New `src/specify_cli/core/saas_sync_config.py` holds `SAAS_SYNC_ENV_VAR`, `is_saas_sync_enabled`, `saas_sync_disabled_message`, and the privates `_TRUTHY_VALUES` / `_DISABLED_MESSAGE` — byte-for-byte the current `saas/rollout.py` bodies. It declares `__all__` (the module is under `core/`; per C-007 the `__all__` convention applies to `charter/`+`kernel/`, but declaring it here keeps the dead-symbol gate happy and documents the public surface).

### Repoint the sole CORE importer (FR-002)
`readiness/coordinator.py:237` changes its lazy `from specify_cli.saas.rollout import is_saas_sync_enabled` to `from specify_cli.core.saas_sync_config import is_saas_sync_enabled`. This is the only CORE-set importer (verified). A plan-time re-grep in WP01 confirms none other exists.

### Re-export surfaces (FR-003, single canonical authority)
`saas/rollout.py` becomes: `from specify_cli.core.saas_sync_config import (…)` + `__all__` (thin shim, preserves object identity for `test_rollout.py`). `saas/__init__.py` continues to re-export the names (now transitively via the shim, or directly from core — either keeps resolution + identity; prefer importing from the shim to minimize churn and keep `saas.__init__`'s stated public API). `sync/feature_flags.py`, `tracker/feature_flags.py`, and the `sync/__init__` / `tracker/__init__` facades are unchanged (they import from `saas.rollout`, which still resolves). No consumer import path breaks.

### Boundary test changes (FR-004)
In `tests/architectural/test_integration_boundary.py`: (a) delete the single `ALLOWLIST` tuple → `ALLOWLIST = frozenset()`; (b) change `test_allowlist_count_ratchet`'s assertion `len(ALLOWLIST) <= 1` → `== 0`, and sweep **all** the now-stale `<= 1` / "at most one" / "exactly one exemption" prose in this file (verified locations: lines 32, 34, 45, 98, 276, 282, 284, 285 — not just 32-35/45); (c) delete the positive-control block (~`:264-272`) in `test_allowlist_cannot_be_bypassed` that injects the now-removed coordinator→`saas.rollout` allowlisted crossing and asserts suppression — retain the negative-control (the separate block at ~`:246-262` where a non-allowlisted CORE→INTEGRATION import IS reported), which keeps the scanner honest.

### Docs (FR-005 / FR-006) + campsite (C-005)
- ADR `docs/adr/3.x/2026-06-26-1-core-integration-boundary.md`: sweep **all** the now-stale "single/one exemption" + `<= 1` references (verified: the Allowlist Exemptions table ~:183 → resolved/empty; point 7 `len(ALLOWLIST) <= 1` ~:151 → `== 0`; the negative bullet ~:238-240 "single remaining allowlist entry … one structural coupling in CORE" → moved to resolved/struck; Confirmation item 2 ~:253 "passes with exactly one allowlist entry" → "zero"; Confirmation item 3 ~:254 → checked, referencing #2252). Add a one-line note acknowledging the retained-shim depth trade-off (`tracker`/`sync` feature_flags → `rollout.py` shim → core) so a later reader doesn't read it as an oversight.
- Contract `kitty-specs/082-…/contracts/saas_rollout.md`: `**Module**:` line (~:3) → new core home; "made once in `saas/rollout.py`" (~:49) → "made once in `core/saas_sync_config.py`, re-exported by `saas/rollout.py`"; bump the contract version; keep it round-trip parse-valid.
- Campsite: `readiness/upgrade_ux.py:77` docstring "shared with `saas.rollout`" → the new home.

### ATDD red-first order (C-004) — clean single-red
Emptying the `ALLOWLIST` reds **two** tests, not one: `test_no_core_imports_integration` (the real behavioral pin) AND the positive-control in `test_allowlist_cannot_be_bypassed` (which hard-codes the removed crossing). So the **red commit must be atomic** = {empty `ALLOWLIST` + delete the positive-control block `:264-272`} while `readiness/coordinator.py:237` still imports `saas.rollout` → exactly one meaningful red (`test_no_core_imports_integration`), with the ratchet (`== 0`) and the negative-control both green. The **green commit** = {create `core/saas_sync_config.py` + repoint coordinator + shim `rollout.py` + tighten ratchet to `== 0` + sweep the `<= 1` prose + fix the stale docstrings}. Do NOT split emptying-allowlist from positive-control-removal across commits.

## Risks

| Risk | Mitigation |
|------|------------|
| Deleting `rollout.py` (tempting "clean" move) breaks `test_rollout.py` identity tests | Design mandates retain-as-shim (D-02); reviewer checks `rollout.py` still exists and re-exports the same objects. |
| Positive-control left in place → boundary suite red after relocation | FR-004(c) explicitly removes it; WP01 validation runs the full `test_integration_boundary.py`. |
| A missed CORE importer beyond coordinator | WP01 re-greps `specify_cli.saas.rollout` across `core|status|readiness|invocation` before finishing; the boundary scan itself is the backstop. |
| Contract edit breaks the round-trip test | Keep frontmatter/codeblocks parse-valid; run `test_example_round_trip.py` in WP02. |

## Work-package shape (guidance for /spec-kitty.tasks)
Strictly-linear, 2 WPs:
1. **WP01 — code + boundary** (FR-001/002/003/004, C-004/C-005): (red commit) empty `ALLOWLIST` + delete the positive-control `:264-272` while coordinator still imports INTEGRATION → clean single red. (green commit) create `core/saas_sync_config.py`, repoint `coordinator.py:237`, rewrite `rollout.py` to a re-export shim (the `saas/__init__` + `sync`/`tracker` feature_flags surfaces need **verification only**, not edits — they resolve transitively), tighten the ratchet to `== 0` + sweep all `<= 1` prose in the boundary test, and fix the 3 stale docstrings (`sync`/`tracker` feature_flags "canonical home", `upgrade_ux.py:77` drop the false "shared" claim). ATDD red-first. Scoped tests: `tests/architectural/test_integration_boundary.py` + `tests/saas/` + `tests/**/*feature_flag*` green; ruff + mypy-strict on changed files.
2. **WP02 — docs** (FR-005/FR-006): sweep ALL stale `<=1`/"single/exactly one" refs in the ADR (:151, :183, :238-240, :253, :254) + the shim-depth note; update the stability contract (`:3` module, `:49` semantics, shims section, version bump). Depends on WP01. Scoped tests: `tests/contract/test_example_round_trip.py` + `tests/architectural/test_no_legacy_terminology.py` (prose edits — charter terminology guard).

(Exact slicing is the tasks author's call.)

## Out-of-scope follow-up (tracked)
The truthy-grammar `{"1","true","yes","on"}` is triplicated across `saas/rollout.py` (moved), `readiness/upgrade_ux.py:75`, and `compat/config.py:48` — three independent parsers for *different* flags. Unifying them is a distinct refactor beyond this mission's single-flag relocation; **filed as a follow-up issue at PR time** (do not silently propagate a "shared" docstring — WP01 drops the false claim). Also noted: this mission intentionally increases shim depth (`tracker`/`sync` feature_flags → `rollout.py` shim → core) to avoid NFR-001 test churn — a deliberate scope-discipline trade-off, recorded in the ADR.
