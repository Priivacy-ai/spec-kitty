# Research: Shrink Architectural Ratchet Allowlists

Phase 0 output. No open `[NEEDS CLARIFICATION]` markers. Records the live re-confirmation of the
2026-06-25 squad audit (counts/line-numbers drift as other missions land) and the design resolution
of the FR-001 ↔ FR-006 interaction.

## Live re-confirmation (counts as of 2026-06-26, on `feat/shrink-ratchet-allowlists`)

| Key (`_baselines.yaml`) | Audit value | Live value | Note |
|--------------------------|-------------|-----------|------|
| `category_a_slice_f_deferred` | 12 (live 11) | 12 | declared 12; audit found live frozenset = 11 (latent drift). Confirm at implement time. |
| `category_b_grandfathered_legacy` | 286 | 286 | ✓ |
| `legacy_contract_allowlist` | 152 | 152 | lives in `tests/contract/test_example_round_trip.py` (not architectural) |
| `pure_shim_files` | 3 | 3 | ✓ |
| `category_5_wp_in_flight_adapters` | 3 | 3 | same 3 adapter files as `pure_shim_files` |
| `category_4_backcompat_shims` | 8→9 | 9 | still 9 — #2048/PR #2152 NOT merged yet; OUT OF SCOPE (C-005) |

**Line-number drift:** the audit's `test_no_dead_symbols.py:823-832` / `:666` references are stale (the
#2058 merge decomposition added entries). Current: `_extract_all_literal` at line **910**, its buggy
`return frozenset()` at line **938**. Implementer must locate by symbol name, not line number.

## D-01 — The `_extract_all_literal` bug and its exact fix (FR-006)

- **Decision**: In the `elif isinstance(node, ast.AnnAssign)` branch, when the target is NOT `__all__`,
  `continue` to the next node instead of falling through to `if value is None: return frozenset()`.
  Only return the empty frozenset for an `__all__` AnnAssign that genuinely has no value
  (`__all__: list[str]`).
- **Rationale**: Today a top-level annotated assignment whose target isn't `__all__` (e.g.
  `_VOLATILE_PROVENANCE_FIELDS: ... = ...` in `write_pipeline.py`, declared before `__all__`) matches the
  `AnnAssign` branch, leaves `value = None`, and trips the early return — so the gate sees an empty
  `__all__` for the entire module and inspects none of its public symbols.
- **Alternatives**: skip the fix (FR-001 removals stay inert-safe but unprovable) — rejected by the
  user's scope decision (include the fix).

## D-02 — FR-001 ↔ FR-006 interaction: trim `write_pipeline.__all__`, don't just delete allowlist entries

- **Finding**: `src/charter/synthesizer/write_pipeline.py` declares
  `__all__ = ["promote", "stage_and_validate", "compute_written_artifacts", "StagedArtifact"]`.
  Cross-module `from`-import callers in `src/`:
  - `stage_and_validate` — **LIVE** (`from charter.synthesizer.write_pipeline import stage_and_validate` at `src/specify_cli/cli/commands/charter/_synthesis.py:272`).
  - `promote` — only module-style `write_pipeline.promote()` (lazy-import seam in `orchestrator.py`); **no `from`-import** → gate flags dead.
  - `compute_written_artifacts` — **no** `from`-import caller → gate flags dead (NOT in the current allowlist; a NEW surface once the gate can see it).
  - `StagedArtifact` — **no** `from`-import caller → gate flags dead.
- **Decision**: After fixing the parser (D-01), resolve the 3 newly-visible dead symbols by **removing
  them from `write_pipeline.__all__`** (leaving `__all__ = ["stage_and_validate"]`), i.e. demote
  `promote`, `compute_written_artifacts`, `StagedArtifact` to unexported internals. This is the
  established burn-down pattern (see the `specify_cli.merge.*` allowlist comment block: "drop them from
  the seam `__all__` … once the focused tests reference them without the public-contract expectation, or
  wire a runtime cross-seam caller"). The dead-symbol gate then sees only live symbols → no allowlist
  entry needed → FR-001's removal of the 2 `category_a` entries (`StagedArtifact`, `promote`) becomes
  correct, and `compute_written_artifacts` needs no new entry.
- **Why this is safe**: `from X import Y` works regardless of `__all__`; trimming `__all__` only affects
  `from X import *`. So intra-package module-style calls (`write_pipeline.promote()`) and any explicit
  `from ... import StagedArtifact` in tests keep working.
- **VERIFY at implement time** (before trimming): (a) no `from charter...write_pipeline import *` star-import
  exists; (b) each demoted symbol has no `from`-import caller in `src/` (re-grep); (c) `write_pipeline`
  still passes `test_all_declarations_required` (it retains a non-empty `__all__`). If any demoted symbol
  turns out to have a genuine cross-module `from`-import caller, keep it in `__all__` (it's live) and drop
  only the truly-uncalled ones.
- **Alternatives**: keep the symbols allowlisted (contradicts FR-001, no burn-down) — rejected; wire
  artificial `from`-import callers — rejected (manufacturing proof-of-life is the anti-pattern the gate warns against).

## D-03 — Atomicity / shared-file coupling

- **Decision**: The dead-symbol work (FR-001, FR-002, FR-006 + the `__all__` trim) and the pure-shim work
  (FR-004) both edit `tests/architectural/test_no_dead_symbols.py` and `tests/architectural/_baselines.yaml`,
  so they cannot run as independent parallel lanes — they converge on the same files. Sequence them within
  a single lane (one or two dependent WPs), keeping the suite green at each commit.
- **Rationale**: C-001 (baseline = live size) and the dead-module gate fail mid-way if a category's
  allowlist and file deletion don't land together (C-003).

## D-04 — pure_shim retirement spans 4 surfaces (FR-004)

Retiring `compat/_adapters/{version_checker,gate,detector}.py` (zero functional importers — real
consumers import `core.version_checker` / `migration.gate` / `upgrade.detector` directly) requires
removing entries from **four** places in lock-step (C-003):
1. `_ADAPTER_FILES` in `tests/architectural/test_compat_shims.py`
2. the `category_5` adapter entries in `tests/architectural/test_no_dead_modules.py`
3. the adapter dead-symbol entries in `tests/architectural/test_no_dead_symbols.py`
4. `_baselines.yaml`: `pure_shim_files: 3 → 0` AND `category_5_wp_in_flight_adapters: 3 → 0`
   (both pin the same 3 files).

Re-confirm zero `from ... import` of `specify_cli.compat._adapters.*` in `src/` before deleting.

## D-05 — FR-005 corrections are documentation-only

The path/count corrections (legacy_contract lives in `tests/contract/`; `category_7`=7, `category_b`=286)
are recorded in the mission artifacts and posted as a comment on issue #2049. No code change.
