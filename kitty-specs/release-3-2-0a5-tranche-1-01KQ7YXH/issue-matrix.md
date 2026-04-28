# Issue Matrix: 3.2.0a5 Tranche 1

**Mission**: `release-3-2-0a5-tranche-1-01KQ7YXH` (mid8 `01KQ7YXH`, mission_number 104)
**Branch**: `release/3.2.0a5-tranche-1`
**Merge commit**: `86c2f967`
**Generated post-merge**: 2026-04-27 (addresses mission-review DRIFT-1)

This file is the FR-037 closing-evidence matrix for the 10 GitHub issues in scope. Each row documents the verdict and the evidence that closes it. Allowed verdicts: `fixed` · `verified-already-fixed` · `deferred-with-followup`.

| Issue | FR | WP | Verdict | evidence_ref |
|-------|----|----|---------|--------------|
| [#705](https://github.com/Priivacy-ai/spec-kitty/issues/705) | FR-002 | WP01 | `fixed` | `src/specify_cli/upgrade/runner.py:125-126` and `:173-174` (call-order swap + `# Why:` comments at `:119-124` and `:169-172`); regression: `tests/cross_cutting/versioning/test_upgrade_version_update.py::test_upgrade_persists_schema_version`; e2e: `tests/e2e/test_upgrade_post_state.py::test_upgrade_then_branch_context_does_not_gate` |
| [#735](https://github.com/Priivacy-ai/spec-kitty/issues/735) | FR-008 | WP06 | `fixed` | `src/specify_cli/cli/commands/agent/mission.py:727` (`mark_invocation_succeeded()` after final JSON write); atexit consumers: `src/specify_cli/sync/background.py:172`, `src/specify_cli/sync/runtime.py:322-336`; e2e: `tests/e2e/test_mission_create_clean_output.py` |
| [#717](https://github.com/Priivacy-ai/spec-kitty/issues/717) | FR-009 | WP06 | `fixed` | `src/specify_cli/sync/background.py:289` and `:345` (`report_once("sync.unauthenticated")`); `src/specify_cli/auth/transport.py:122` (`report_once("auth.token_refresh_failed")`); regression: `tests/sync/test_diagnostic_dedup.py` |
| [#636](https://github.com/Priivacy-ai/spec-kitty/issues/636) | FR-005 | WP05 | `fixed` | `src/specify_cli/cli/commands/init.py:234-257` (`_is_inside_git_work_tree`), `:391-396` (yellow info line), `:703-706` (next-steps bullet); honors Decision Moment `01KQ84P1AJ8H3FPJN9J5C12CBY` (canonical invariant: non-git init is allowed; silent non-git init is not); regression: `tests/specify_cli/cli/commands/test_init_non_git_message.py` |
| [#830](https://github.com/Priivacy-ai/spec-kitty/issues/830) | FR-010 | WP08 | `fixed` | `src/specify_cli/status/store.py:222` (`if "event_type" in obj: continue`) with `# Why:` comment at `:207-221`; 5-test regression: `tests/status/test_read_events_tolerates_decision_events.py` (incl. the malformed-lane fail-loud preservation test, restored after WP08 cycle-1 review rejection) |
| [#805](https://github.com/Priivacy-ai/spec-kitty/issues/805) | FR-001 | WP03 | `fixed` | `.python-version` set to `3.11` (matches `pyproject.toml::requires-python = ">=3.11"`); `mypy --strict src/specify_cli/mission_step_contracts/executor.py` clean; CI lock: `tests/cross_cutting/test_mypy_strict_mission_step_contracts.py` (invokes mypy in-process and asserts exit 0); Decision Moment `01KQ7ZSQKT9DVH7B4GGXWS8DTW` (resolved: floor at 3.11) |
| [#815](https://github.com/Priivacy-ai/spec-kitty/issues/815) | FR-003 | WP04 | `fixed` | Bulk removal per `kitty-specs/release-3-2-0a5-tranche-1-01KQ7YXH/occurrence_map.yaml` (29 REMOVE / 7 KEEP across 6 of 8 standard categories); deleted: source template, override copy, manifest entry, legacy hash catalog entry, all 13 per-agent regression baselines, codex-legacy upgrade fixtures; aggregate scanner: `tests/specify_cli/test_no_checklist_surface.py`; artifact preservation: `tests/missions/test_specify_creates_requirements_checklist.py` |
| [#635](https://github.com/Priivacy-ai/spec-kitty/issues/635) | FR-004 | WP04 | `fixed` (superseded by #815) | Same evidence as #815. CHANGELOG note: "Retire the deprecated /spec-kitty.checklist command surface ... (#815, supersedes #635, WP04)"; close #635 with a comment linking to #815. |
| [#790](https://github.com/Priivacy-ai/spec-kitty/issues/790) | FR-006 | WP07 | `verified-already-fixed` | All 22 `--feature` declarations across `src/specify_cli/cli/commands/` already carry `hidden=True` on `release/3.2.0a5-tranche-1` baseline. WP07 added regression tests to lock the invariant: `tests/specify_cli/cli/test_no_visible_feature_alias.py` (typer-walk + `--help` grep + `hidden=True` per-param assertion) and `tests/e2e/test_feature_alias_smoke.py` (alias still routes to mission semantics). C-004 forbids deprecation warning unless explicitly approved during plan; not approved → no warning emitted. |
| [#774](https://github.com/Priivacy-ai/spec-kitty/issues/774) | FR-007 | WP07 | `verified-already-fixed` | The actual subgroup is `spec-kitty agent decision { open \| resolve \| defer \| cancel \| verify }` — already canonical on baseline. WP07 added regression test `tests/specify_cli/cli/test_decision_command_shape_consistency.py` (typer walk + `--help` listing + multi-source grep for non-canonical shapes). The `widen` subcommand exists but carries `hidden=True` (decision.py:403). |

## Aggregate

| Verdict                  | Count |
|--------------------------|-------|
| `fixed`                  | 7     |
| `verified-already-fixed` | 2     |
| `deferred-with-followup` | 0     |

All 10 issues have a closeable verdict and concrete evidence. No `unknown` rows; no empty `evidence_ref` cells; no bare deferrals. FR-037 Gate 4 is satisfied.

## Follow-up issues to file at PR time

These are NOT in the current tranche's verdict; they are forward-looking captures from the mission-review (see `follow-ups.md`):

- File new GitHub issue: extend `mark_invocation_succeeded()` to every JSON-emitting `agent` command (RISK-2 from mission-review).
- File new GitHub issue: architectural cleanup of `status.events.jsonl` writer/reader cooperation (RISK-3 from mission-review).
- File new GitHub issue: `_stamp_schema_version` should `logger.warning` on its silent-return paths (silent-failure rows 1-2 from mission-review). Note: this tranche's follow-up commit `<this-commit-sha>` adds the warnings inline; the GitHub issue can therefore close as `verified-already-fixed`.
- File new GitHub issue (or close as known design): `--feature` alias has no deprecation warning (RISK-1; C-004 forbids the warning today; revisit in a future hardening tranche).
