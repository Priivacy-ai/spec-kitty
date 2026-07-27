# Research — Code-state falsification + campsite (pre-planning squad)

**Source**: paula-patterns adversarial code-state lens, read-only on `feat/doctrine-activation-freshness` @ `50263573` (code identical to `main`), 2026-07-17. Ran to FALSIFY the grounding brief's structural claims.

## Headline

Grounding was structurally right on **5 of 6** claims. Its load-bearing claim #1 — the "single write chokepoint" that C-005/C-006 rested on — is **REFUTED as an absolute invariant**: `CharterPackManager.merge_defaults` (`pack_manager.py:703-755`, direct write at `:747` → `_save_config` `:753`) writes `activated_*` state **bypassing `commit_plan`**. It is test-covered (`tests/charter/test_pack_manager.py:300-335`) and ADR-scheduled to go live on `init` (ADR 2026-07-15-1: default activation is "triple-sourced (constants, default.yaml, merge_defaults)"; remediation S1 = "`init` provisions the default charter via `merge_defaults`").

**Consequence (folded into spec C-005/C-006/Q2):** the reconciler must be **writer-agnostic**. This *strengthens* the grounding's Q2(a) read-path parity recommendation (`run_consistency_check` reads `config.yaml` directly at `_load_raw_activation_lists:197`, so it sees any writer) and **rejects** Q2(c) write-side marker (blind to the `merge_defaults`/`init` bypass).

## Falsification verdicts

| # | Claim | Verdict | Evidence |
|---|-------|---------|----------|
| 1 | Single write chokepoint (C-005/C-006) | **REFUTED as invariant** | `merge_defaults` (`pack_manager.py:747/753`) is a second `activated_*` writer, test-alive + ADR-slated for `init`. Spec corrected. |
| 2 | Content-hash blindness (#2759) | **CONFIRMED** | `BUNDLE_CONTENT_HASH_FILES` (`bundle.py:47-52`) = 4 files under `.kittify/charter/`; `config.yaml` at `.kittify/config.yaml` not hashed. `_compute_synthesized_drg` (`computer.py:349`) compares at `:426-428`. |
| 3 | references.yaml gap (#2758) | **CONFIRMED** | `_SYNC_OUTPUT_FILES` (`sync.py:46-50`) omits references.yaml; `compute_bundle_content_hash` → `None` on any missing file (`bundle.py:170-171`); `computer.py:428` maps None→stale. Permanent, un-healable by synthesize (documented `computer.py:16-23`). |
| 4 | consistency_check built-but-unwired | **CONFIRMED** | `run_consistency_check` (`consistency_check.py:645`) + `_check_reference_id_parity` (`:455`) + `_check_graph_kind_parity` (`:562`). Sole production caller = `charter/pack.py:30` (CLI). No call from `computer.py`/`runner.py`. |
| 5 | #2157 two-subsystem split (C-004) | **CONFIRMED** | Implement gate `_require_current_analysis_report` (`workflow.py:835`) → `analysis_report.check_analysis_report_current` (hashes spec/plan/tasks/charter). Charter preflight `_attempt_auto_refresh` (`runner.py:327`) reached only via `run_charter_preflight`. Disjoint. 2157b OUT is valid. |
| 6 | ~6 activation call-sites | **CONFIRMED (7 live + 1 bypass)** | Live→commit_plan: pack_manager.activate (direct+cascade), deactivate (direct+cascade), promote_activations ← interview `:111` / org_charter `:425` / migration `m_unify_charter_activation:313`. Bypass: `merge_defaults`. NFR-003 eager-always hazard real (migration + org_charter drive promote_activations). |

**Bonus internal inconsistency (note in #2758 WP):** `bundle.py:110-119 CANONICAL_MANIFEST.derived_files` lists **3** files (references.yaml excluded) while the hash set is **4**. Reconcile deliberately, don't blind-match.

## Campsite scan (touch-surface; ruff default passes clean on all 5)

| Item | Location | Class |
|------|----------|-------|
| `_check_reference_id_parity` complexity **12** (FR-002/C-007 wiring target; pre-extract sub-checks before wiring) | `consistency_check.py:455` | **SAFE-to-fold** |
| `_compute_synthesized_drg` 7 returns (#2759 read-side; extract built_in_only branch + hash-compare tail when wiring parity, stay ≤15) | `computer.py:349` | **SAFE-to-fold** |
| Repeated command-prefix list `["spec-kitty","charter",…]` ×3 in the #2157a edit target | `runner.py` (`_attempt_auto_refresh`) | **SAFE-to-fold** |
| Remediation literals `"spec-kitty charter sync"` ×6, `"…synthesize"` ×3, `state="stale"` ×5, `state="missing"` ×5 (S1192) | `computer.py` | **ADJACENT** |
| `BUNDLE_CONTENT_HASH_FILES` (bundle.py:47) ↔ `_BUNDLE_FILES` (computer.py:137) intentional dup (data-model Decision 5) — if Q1 narrows to triad, BOTH change together | contract | **ADJACENT** |
| mypy `no-any-return`/`unused-ignore` surfaced only in isolation (`charter.*` follow_imports=skip artifacts) — re-verify under project mypy | computer.py/runner.py | **OUT** (likely config noise) |

## Bottom line for /plan

- **Spec correction applied**: C-005/C-006 reframed writer-agnostic; Q2(a) now strongly favoured with the `merge_defaults` reason; Q2(c) rejected. Q5 added (dual-edit contract + manifest derived-set mismatch).
- Claims 2–6 stand; the sequence #2758 → #2759 → #2157a → #2770 is grounded.
- Campsite light: three SAFE-to-fold cleanups sit exactly in the mission's edit targets — fold in-WP, don't spawn a separate campsite WP.
