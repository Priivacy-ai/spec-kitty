# Issue Matrix: review-merge-gate-hardening-3-2-x-01KRC57C

**Mission**: `review-merge-gate-hardening-3-2-x-01KRC57C` (mid8 `01KRC57C`, mission_number 116)
**Baseline merge commit**: `9ec050a7201ba5cc9fd8dd789a114280749779dd`
**Generated**: 2026-05-12 (eat-our-own-dogfood per NFR-003; backfilled after post-merge mission review surfaced D2)

This matrix records every GitHub issue this mission was scoped to address, the work package that delivered the change, the closure verdict, and the evidence reference. Verdict allow-list (enforced by the validator this mission introduced): `fixed` · `verified-already-fixed` · `deferred-with-followup`.

| issue | scope | wp | verdict | evidence_ref |
|-------|-------|----|---------|--------------|
| [#985](https://github.com/Priivacy-ai/spec-kitty/issues/985) | mission-review report contract enforcement; closed-set `issue-matrix.md` validator + remediation of 6 existing matrices | WP03 | `fixed` | `src/specify_cli/cli/commands/review/_mode.py`, `_issue_matrix.py`, `_diagnostics.py`, `ERROR_CODES.md`; `tests/specify_cli/cli/commands/review/` (80 tests). FR-005..FR-009, FR-023, FR-028..FR-034. |
| [#987](https://github.com/Priivacy-ai/spec-kitty/issues/987) | hermetic gate invocation; preflight `assert_pytest_available()` prevents PATH fallthrough | WP01 | `fixed` | `src/specify_cli/cli/commands/_test_env_check.py` (wired into `review/__init__.py` via `assert_pytest_available()` — see D1 remediation 2026-05-12 PM); `tests/specify_cli/cli/commands/test_test_env_check.py`. FR-001, FR-002. |
| [#986](https://github.com/Priivacy-ai/spec-kitty/issues/986) | concurrency-safe pytest-venv fixture via `FileLock` with 60s timeout | WP02 | `fixed` | `tests/conftest.py` (`_ensure_test_venv()` lock zone); `tests/integration/test_pytest_venv_concurrency.py`; `tests/README.md`. FR-003, FR-004. |
| [#983](https://github.com/Priivacy-ai/spec-kitty/issues/983) | idempotent mission-number assignment; `mission_number_baked` flag + resume short-circuit | WP04 | `fixed` | `src/specify_cli/merge/state.py` (flag field); `src/specify_cli/cli/commands/merge.py` (`_bake_mission_number_into_mission_branch` idempotency check inside merge-state lock); `tests/merge/test_mission_number_idempotency.py`. FR-010, FR-011, FR-012. |
| [#984](https://github.com/Priivacy-ai/spec-kitty/issues/984) | worktree-aware status read resolution via `get_status_read_root()` | WP05 | `fixed` | `src/specify_cli/core/paths.py` (`get_status_read_root`, `assert_worktree_supported`); `src/specify_cli/cli/commands/agent/tasks.py`, `src/specify_cli/agent_utils/status.py` (read-only routing); `tests/status/test_status_read_worktree_resolution.py` (11 tests). FR-013, FR-014, FR-015. |
| [#644](https://github.com/Priivacy-ai/spec-kitty/issues/644) | narrowed encoding chokepoint at charter ingestion boundary; broader audit deferred per #822 anti-scope | WP06 | `deferred-with-followup` | `src/charter/_io.py` (chokepoint + provenance); 3 retrofit sites (compiler, sync, interview); `tests/charter/` (13 tests); `src/charter/ERROR_CODES.md`. FR-016..FR-022. Follow-up: broader UTF-8 audit beyond charter-content ingestion to be filed as a successor ticket once 3.2.0 ships; the 5 deferred re-read sites (`context.py`, `hasher.py`, `language_scope.py`, `compact.py`, `neutrality/lint.py`) remain UTF-8-only by design (NFR-004 5-module budget). |
| [#391](https://github.com/Priivacy-ai/spec-kitty/issues/391) | still-open structural-extraction children #612 / #613 / #614 deferred from 3.2.x stabilization scope | — | `deferred-with-followup` | Decision recorded in [ADR 2026-05-11-1](../../architecture/adrs/2026-05-11-1-defer-391-structural-extraction-from-3-2-x.md). Re-scoping happens post-3.2 on top of the shared-package-boundary cutover's enforcement tests. Follow-up: child issues #612, #613, #614 remain open on the GH backlog. |
| [#822](https://github.com/Priivacy-ai/spec-kitty/issues/822) | residual P1 tranche of the 3.2.0 stabilization epic | — | `fixed` | Mission `01KRC57C` consolidates the 5 P1 bugs above + narrowed #644. Epic body updated 2026-05-11 to reflect the residual tranche assignment to this mission. The companion in-flight PR set (#806, #1027, #1028) covers the remaining items (#662, #988, #889) under #822's scope; this mission does not duplicate that work. |

## Aggregate verdict summary

- `fixed`: **6** — #985, #987, #986, #983, #984, #822
- `verified-already-fixed`: **0** (this mission's tranche items were genuinely re-opened P1 bugs from rc-line review, not previously-fixed items)
- `deferred-with-followup`: **2** — #644 (broader audit deferred), #391 (structural extraction deferred)

## Post-merge audit follow-ups (resolved in-band 2026-05-12 PM after `/spec-kitty-mission-review`)

A post-merge adversarial mission review surfaced 5 follow-on findings. All have been addressed on this same branch (commits after the merge SHA):

- **D1 (MEDIUM)** — dead `assert_pytest_available()` helper not called from production. **Resolved**: wired into `review/__init__.py` preflight; tests of the helper now exercise the live path.
- **D2 (HIGH)** — mission missing its own `issue-matrix.md` + `baseline_merge_commit` (this file). **Resolved**: this file authored; `meta.json` backfilled with `baseline_merge_commit`. NFR-003 self-dogfood now satisfied.
- **D3 (MEDIUM)** — `--unsafe` not propagated through `compiler.py:_load_yaml_asset`. **Resolved**: `unsafe` parameter threaded through the helper.
- **S1 (MEDIUM)** — `interview.py:read_interview_answers` swallowed `CharterEncodingError`. **Resolved**: narrowed `except Exception` to permit propagation; `KittyInternalConsistencyError` (the canonical base for all such errors, introduced in `src/kernel/errors.py`) now reaches callers.
- **S2 (MEDIUM)** — `compiler.py:_load_yaml_asset` swallowed `CharterEncodingError`. **Resolved**: same fix pattern; encoding errors propagate; pre-existing YAML-parse resilience preserved.

Coverage gaps observed by the audit (FR-007 gate records, FR-008 mission-exception schema, FR-020 ambiguous body content, FR-024/FR-025 WP07 mechanical-only, FR-034 glossary entries) remain `deferred-with-followup` — production code paths exist and were per-WP reviewed, but lack regression scaffolding. Suggested for a successor mission under epic #992.

## Follow-up issues to file

- Broader UTF-8 audit (extension of #644 to the 5 deferred re-read sites under `src/charter/`)
- Regression tests for FR-007 (`GateRecord` end-to-end), FR-008 (`mission-exception.md` schema), FR-020 (ambiguous-body content assertions), FR-034 (glossary-presence test)
- Cross-surface fixture harness (epic #992 Phase 0) that exercises the JSON-stable diagnostic codes against fixture missions
