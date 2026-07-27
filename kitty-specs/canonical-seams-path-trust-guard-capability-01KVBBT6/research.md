# Phase 0 Research — Canonical Path-Trust & Guard-Capability Seams

**Date:** 2026-06-17 · **Branch:** `feat/canonical-seams-path-trust-guard-capability` (HEAD off main `77c869712`)
Re-verifies the pre-spec investigation census (`research/00-investigation-synthesis.md`) against current HEAD,
and resolves the C-003 scope decision.

## Census re-verification (line numbers confirmed on HEAD)

### (a) Three divergent slug/segment validators — CONFIRMED
| Validator | Location | Regex | Raises | Scope |
|-----------|----------|-------|--------|-------|
| `_validate_mission_slug_path_segment` | `merge.py:774` (`_MISSION_SLUG_PATH_SEGMENT_RE` :102) | `^[A-Za-z0-9_-]+$` (ASCII, no dots) | `ValueError` | mission_slug |
| `_validate_safe_segment` | `coordination/transaction.py:168` (`_SAFE_PATH_SEGMENT_RE` :150) | `^[A-Za-z0-9][A-Za-z0-9._-]*$` (dots ok) | `BookkeepingError` | **mission_id (:317), mission_slug (:693), mid8 (:694)** |
| `_validate_mission_slug` | `status/aggregate.py:347` (`_MISSION_SLUG_PATTERN` :54) | `^[A-Za-z0-9_-]+$` (ASCII, no dots) | `InvalidMissionSlug(ValueError)` :124 | mission_slug |

**Decision (FR-001/FR-004):** the canonical validator is a **general safe-path-segment** guard (not slug-only),
because `transaction.py` applies it to `mission_id`/`mid8` too. Home: `core/paths.py`. Raise `ValueError`
(both `merge.py` and `aggregate.py::InvalidMissionSlug` are already `ValueError`-compatible; `transaction.py`
wraps to `BookkeepingError` at its call sites — preserve that wrap). **Rationale:** `KEBAB_CASE_PATTERN`
(`core/mission_creation.py:65`, `^[a-z0-9][a-z0-9]*(-[a-z0-9]+)*$`) is a subset of all three; the `.`-allowing
`transaction.py` form is the most permissive — the reconciled grammar must keep the `.`/`..`/`/`/`\` traversal
guard while still admitting every real-format value (full ULID, `<slug>-<mid8>`, numeric-prefix, bare mid8).
A union-of-real-format-values test (NFR-006) pins this.

### (b) Primitives validate nothing; SAFE-TO-MOVE — CONFIRMED
- `candidate_feature_dir_for_mission` (`_read_path_resolver.py:370`) → routes through `resolve_mission_read_path`,
  no validation.
- `primary_feature_dir_for_mission` (`:397`) → topology-blind `get_main_repo_root(repo_root) / KITTY_SPECS_DIR /
  mission_slug`, zero validation. Its docstring already claims it is a "blessed owner of `KITTY_SPECS_DIR` path
  assembly enforced by `test_no_raw_mission_spec_paths.py`" — that claim is hollow until it validates.
- **Decision:** add the validator call inside `primary_feature_dir_for_mission` and once in
  `resolve_mission_read_path` (so `candidate_*` inherits it too). The dry-run/abort sites in `merge.py`
  (`_resolve_mission_slug` :1429, used at :3100/:3194/:3212) only catch `MissingLanesError`/`CorruptLanesError`;
  raising `ValueError` there for a malformed handle is acceptable (today it silently builds a bad path then
  fails confusingly) — but a WP must add a catch/clean diagnostic at those sites to keep `--abort` UX clean.

### (c) #2019 sibling seams — CONFIRMED (minor drift)
Unguarded `mission_slug`→path composers in `merge.py`: `:597`/`:599` (`Path(KITTY_SPECS_DIR)/mission_slug/...`),
`:828` (`primary_feature_dir_for_mission(repo_resolved, mission_slug)` — raw), `:1853` (`f"kitty-specs/{mission_slug}/meta.json"`),
`:2382` (`primary_feature_dir_for_mission(main_repo, mission_slug)` — raw), `:2746`/`:2747` (`f"kitty-specs/{mission_slug}/..."`).
Once the primitive validates, the `primary_feature_dir_for_mission` sites inherit the guard; the raw f-string
composers (`:597`/`:1853`/`:2746`) do NOT route through the primitive — FR-003's proof test targets a
`primary_feature_dir_for_mission` sibling (`:828`/`:2382`). The raw f-strings are pre-validated upstream by the
same `mission_slug` having passed the primitive earlier in the same flow; a WP confirms this and adds a guard
only if a flow reaches them with an unvalidated slug.

### (d) Containment helpers — CONFIRMED
- `_assert_status_path_within_target_surface` (`merge.py:820`) — single computed root (`primary_feature_dir_for_mission`). → collapses.
- `_assert_status_surface_path_is_trusted` (`:837`) — **conditional XOR** root by `is_under_worktrees_segment` (:846). → STAYS a conditional caller (no union-widening — behavior change).
- `_assert_bookkeeping_snapshot_path_is_trusted` (`:865`) — multi-root **+ exact-file allowlist** (`.kittify/merge-state.json`). → collapses, needs the `files=` arm.
- `ensure_within_directory` (`core/utils.py:29`) — single-root primitive; `write_text_within_directory` (:40) wraps it. No `ensure_within_any` yet.
- **Decision (FR-005/FR-006):** add `ensure_within_any(path, *, roots, files=())` to `core/utils.py` (resolve(strict=False) + is_relative_to over roots, plus exact-file membership). Collapse the two non-XOR helpers; keep the XOR helper as a conditional caller selecting its single root then delegating.

### (e) Architectural CI gate is maskable — CONFIRMED
`ci-quality.yml`: `core_misc` filter (`:174`) carries `tests/architectural/**`; `execution_context` filter (`:220`)
carries `src/specify_cli/status/**` but its only architectural inclusion is the single file
`tests/architectural/test_execution_context_parity.py` (`:225`). The short-circuit (`:1359`/`:1364`) runs ONLY that
parity file for execution-context-only changes and `exit`s. → a `status/**` edit runs `fast-tests-status` but
skips the rest of `tests/architectural/**` (e.g. `test_no_write_side_rederivation`). **Decision (FR-007):**
add `src/specify_cli/status/**`, `src/specify_cli/coordination/**`, `src/specify_cli/core/worktree.py` to the
`core_misc` filter (`:174`) so any guarded-surface edit forces the full architectural shard; add a meta-test
asserting the trigger covers the guarded surfaces (NFR-004, so a future filter edit can't silently re-open it).

### (f) Line-number-keyed ratchet pins — CONFIRMED
- `test_no_worktree_name_guess.py`: `_ALLOWED_SITES` (`:82`), `_NAME_COMPOSE_BASELINE_RAW_MATCHES` (`:126`),
  and the `_SHORTID_*` allow-lists/baselines — the re-key targets (FR-008).
- `test_no_write_side_rederivation.py`: `_ALLOW_LIST` (`:81`) seeds `("…/status_transition.py", 295)` — the
  deliberate #1716-blocked pin. **OUT of scope (C-007).** The AST/token machinery to reuse
  (`_code_tokens_by_line` etc.) lives in this same file.
- **Decision (FR-008):** re-key the `test_no_worktree_name_guess.py` allow-lists to an AST/qualname +
  normalized-token-line composite (reuse the sibling's machinery — no new infra); add a +1-line-drift test;
  leave `:295` untouched.

## C-003 scope decision — FOLD GOAL C IN

**Sizing:** FR-007 = a bounded `ci-quality.yml` filter edit (add 3 path globs) + a meta-test. FR-008 = a focused
`test_no_worktree_name_guess.py` re-key reusing the sibling test's existing AST machinery + a drift test. No new
infrastructure; ~2 WPs. Goals A (~2–3 WPs) + B (~1–2 WPs) + C (~2 WPs) ≈ 5–7 WPs total — Goal C is a bounded
slice, not a scope shift.

**Decision (operator guidance 2026-06-17 "fold if not a big scope shift"):** **FOLD Goal C into this mission**;
keep #2023 as the in-mission tracker home (under #1931). paula's split fallback (#1931/#1914) is NOT triggered
because C is bounded and reuses existing machinery. Recorded rationale: C is guard-*mechanism* (how guards are
keyed/scheduled), behavior-preserving for what they assert, and the CI-mask is a live this-session failure worth
closing in the same mission that hardens the path-trust surfaces those guards protect.

## Decisions of record
- **D-1** Canonical validator is a general safe-segment guard in `core/paths.py`, raising `ValueError`;
  `transaction.py` keeps its `BookkeepingError` wrap at the call site.
- **D-2** Validate inside `primary_feature_dir_for_mission` + `resolve_mission_read_path`; add clean-diagnostic
  catches at the `merge.py` dry-run/abort sites.
- **D-3** `ensure_within_any(path, *, roots, files=())` in `core/utils.py`; XOR helper stays a conditional caller.
- **D-4** CI fix = widen `core_misc` filter + meta-test; FR-008 re-key reuses sibling AST machinery; leave `:295`.
- **D-5** FOLD Goal C in (C-003 resolved).
- **D-6 (ownership)** `merge.py` is touched by Goal A (validator delegate) and Goal B (helper delegate) —
  linearize: the merge.py validator-delegate edit (A) and the merge.py helper-collapse edit (B) land in
  **dependency order within a single owning lane**, OR partition by non-overlapping line regions with one WP
  owning `merge.py` for both edits. Plan picks the latter (one merge.py-owning WP carries both the validator
  delegate and the helper collapse) to keep `owned_files` overlap-free.
