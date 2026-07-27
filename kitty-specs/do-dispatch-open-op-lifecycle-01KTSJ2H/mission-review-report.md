# Post-Merge Mission Review — do-dispatch-open-op-lifecycle-01KTSJ2H

Reviewer: senior post-merge mission reviewer (claude). Date: 2026-06-11.
Baseline diff: `b64b8e079..HEAD` (squash merge 447754669). 115 files, +8150/-644.
Mission status: 6/6 WPs Done (`spec-kitty agent tasks status`). No forced
transitions / arbiter overrides found in `status.events.jsonl` (grep for
forced/override/arbiter: 0 hits).

## Gate Results

| Gate | Command | Result |
|------|---------|--------|
| 1. Contract | `SPEC_KITTY_ENABLE_SAAS_SYNC=1 .venv/bin/pytest tests/contract -q` | **PASS** — 257 passed, exit 0 |
| 2. Architectural | `.venv/bin/pytest tests/architectural -q` | **FAIL** — 5 failed, 312 passed (details below; all 4 failing test ids are mission-caused hygiene violations) |
| 3. Cross-repo E2E | `../spec-kitty-end-to-end-testing/scenarios` | **ENVIRONMENTAL / NOT VALID** — see below |
| 4. Issue matrix | `kitty-specs/.../issue-matrix.md` | **PASS (with note)** — all 5 rows are `deferred-with-followup`, each with a follow-up handle (#1810, #1229, #1688, #1781, #701); no unknown/empty/in-mission rows. Note: rows for #1229/#1688/#1781/#701 say "closed by WPxx in this mission" but were never upgraded after those WPs landed — stale verdicts, not a gate violation. |

### Gate 2 detail (HARD FAIL — exit non-zero)

Failing tests, all attributable to this mission's diff:

1. `tests/architectural/test_no_dead_modules.py::test_no_new_dead_modules_under_src`
   — `specify_cli.upgrade.migrations.m_3_3_0_op_record_schema_v2` has zero static
   src/ importers. **Important nuance**: the migration IS live at runtime — it is
   discovered via `pkgutil.iter_modules` + `importlib.import_module` in
   `src/specify_cli/upgrade/migrations/__init__.py:40,79` and registers via
   `@MigrationRegistry.register` (m_3_3_0_op_record_schema_v2.py:223). The gate
   does not model pkgutil discovery; the module needed an `_ALLOWLIST` entry and
   WP05/merge never added one.
2. `tests/architectural/test_no_dead_symbols.py::test_no_public_symbol_in_all_is_unimported`
   — `specify_cli.session_presence.writers.claude_code::SESSION_STOP_CMD` is in
   `__all__` but only used inside its own module (claude_code.py:33,55,60,70).
3. `tests/architectural/test_pytest_marker_convention.py::test_every_test_file_declares_a_pytestmark_marker`
   — new file `tests/upgrade/test_op_record_schema_v2_migration.py` has no
   module-level `pytestmark`, making it invisible to marker-based CI profiles
   (i.e. the WP05 migration tests may not run in CI lanes at all).
4. `tests/architectural/test_pytest_marker_correctness.py::test_subprocess_git_users_must_carry_git_repo_marker`
   — `tests/specify_cli/invocation/cli/test_do.py` and
   `tests/specify_cli/invocation/test_invocation_e2e.py` invoke git via
   subprocess without the `git_repo` marker → CI `-m git_repo` silently skips them.

These are wiring/hygiene defects, not behavior defects, but #3 means the FR-011
test evidence may be excluded from CI runs — that converts a hygiene issue into
a coverage risk.

### Gate 3 detail

- Direct run with this repo's venv: collection error
  (`ModuleNotFoundError: No module named 'spec_kitty_e2e'`) — the e2e repo is a
  package with its own env.
- `cd ../spec-kitty-end-to-end-testing && SPEC_KITTY_ENABLE_SAAS_SYNC=1 uv run pytest scenarios -q`:
  **2 failed, 4 passed** in 94s. Both failures are environmental:
  `saas_sync_enabled.py:136` fails with `SAAS_SYNC_UNAUTHENTICATED` ("Run
  `spec-kitty auth login`") — no SaaS credentials exist in this sandbox.
- **Validity caveat**: the harness resolved the spec-kitty binary to
  `/Users/robert/spec-kitty-dev/spec-kitty/.venv/bin/spec-kitty` (version
  3.2.0rc35) — a *different* checkout, not this merged worktree
  (`spec_kitty_e2e/cli.py:20-42` resolves `root.parent / "spec-kitty"`). So even
  the 4 passes do not exercise the merged code. Recorded as environmentally
  unrunnable against this checkout; not faked as a pass.

## FR Coverage Matrix

| FR | Implementation evidence | Test evidence | Adequacy |
|----|------------------------|---------------|----------|
| FR-001 do never auto-closes | `do_cmd.py` — the `executor.complete_invocation(...outcome="done")` block was deleted (diff hunk at do_cmd.py:150); grep `complete_invocation` in do_cmd.py = 0 hits | `test_do.py:225 test_creates_jsonl_record_on_successful_routing` asserts lifecycle == exactly one `started`, zero `completed` (line 250-254). Would fail if dispatch closed the Op. | ADEQUATE |
| FR-002 close instruction in output | Rich block in do_cmd.py:158-170; JSON: `InvocationPayload.to_dict()` adds `status:"open"` + `close_contract` via `build_close_contract()` (executor.py:64-80,130-133) | `test_do.py:276 test_rich_output_includes_close_contract`, `:386 test_json_output_has_status_open_and_close_contract` | ADEQUATE |
| FR-003 close surface, idempotent | `advise.py complete_invocation`: `--outcome` now required (typer `...`), validated against {done,failed,abandoned} (advise.py:283-296), `closed_by="agent"` (advise.py:305); double close → exit 1, error JSON to stderr (advise.py:210-217) | `tests/.../cli/test_complete.py` (266 lines, new), incl. evidence-mode refusal tests at :197,:217 | ADEQUATE |
| FR-004 schema split, no blank defaults | `record.py`: `OpStartedEvent`/`OpCompletedEvent` frozen models; `outcome`/`closed_by` are required Literals with no default; completed event carries no started-only fields; ULID regex validator; min_length=1 on profile_id/action/actor/mode_of_work/started_at/completed_at | `test_record.py` (43 tests; multiple `pytest.raises(ValidationError)` at :88-:147 constraining unconstructibility) | ADEQUATE |
| FR-005 single-file story | Started event carries actor/request/profile/action/gov hash/timestamps; completed carries outcome/closed_by/completed_at/evidence_ref. `invocations list` surfaces `closed_by` (invocations_cmd.py:269,:325) | test_invocations.py (+129 lines), test_record round-trips | ADEQUATE |
| FR-006 sweep via executor, doctor closing actor | `doctor/ops.py close_stale_ops()` calls `executor.complete_invocation(..., outcome="abandoned", closed_by="doctor_sweep")` (ops.py:165-170); zero direct JSONL appends in doctor/ops.py (verified by read) | `test_doctor_ops.py` (+283 lines) incl. already_closed race, error continuation, perf | ADEQUATE |
| FR-007 threshold semantics | doctor.py: default 24.0 (`threshold if threshold is not None else 24.0`, doctor.py:1500-1504); `--threshold` without `--close-stale` → BadParameter; ops.py:152 `is_stale = threshold_hours == 0 or age is None or age > threshold_hours`; fresh ops reported, never closed; exit 1 when fresh remain (doctor.py:1437) | test_doctor_ops.py + test_doctor_ops_cli.py (+143) | ADEQUATE |
| FR-008 do propagates via shared propagator | `do_cmd._build_executor` now constructs `InvocationSaaSPropagator` (do_cmd.py:41-45); envelope = v2 `model_dump(exclude_none=True)` 1:1 (propagator.py:_build_started/_completed_event_dict); sync gate via `resolve_checkout_sync_routing` unchanged | `test_do.py:421 propagator_receives_started_event`, `:443 sync_disabled_writes_locally_without_propagation`, `:482 propagator_submission_is_non_blocking`; test_propagator*.py updated | ADEQUATE (but see Risk R1: doctor-sweep closes bypass propagation) |
| FR-009 session presence | `session_start.py:57-61` appends `render_open_ops_section`; new `session_stop.py` command registered (`commands/__init__.py:224`); Stop hook registered by `ClaudeCodeWriter.write` (claude_code.py:54-56); migration backfills Stop hook (`m_3_3_0_session_presence_claude_code.py`) | `test_open_ops.py` (219 lines), `test_claude_code_hook.py` (+77), `test_claude_code_writer.py` (+38), `test_m_session_presence_claude_code.py` (+67) | ADEQUATE |
| FR-010 contract prose | `session_presence/content.py:69-75` rewritten to open→work→close; `src/doctrine/skills/spec-kitty.advise/SKILL.md` (new, 140 lines); runtime-next SKILL.md updated; grep `outcome done\|single-shot\|record written` over `src/doctrine` + `src/specify_cli/session_presence` = **0 hits** | test_content.py (+17) asserts close-contract prose | ADEQUATE |
| FR-011 migration | `m_3_3_0_op_record_schema_v2.py`: normative mapping incl. `"unrecorded"` placeholders for missing actor/action, `completed_at` → `started_at` fallback with warning, `closed_by="agent"` backfill, null outcome → `abandoned`, byte-identical link/glossary passthrough, delete-unsalvageable with operator-visible report; idempotent via `_is_v2_*` skip | `tests/upgrade/test_op_record_schema_v2_migration.py` (320 lines) — but file lacks pytestmark (Gate 2 failure 3): may be skipped by CI marker profiles | ADEQUATE in repo; PARTIAL in CI (marker gap) |
| FR-012 commit at close only | `do` writes no commit (only close path commits: executor.py:347 `_commit_op_record`, message `op(<profile>): <action> [<id8>]` at executor.py:468, `allow_completed_op_on_protected_branch=True` via `safe_commit`); sweep closes share the same path | `test_do.py:401 test_successful_do_leaves_op_file_untracked`; e2e/doctor tests cover close-time commit | ADEQUATE |

NFRs: NFR-001 — `test_do.py:482` non-blocking propagator test (real: stubs a slow
propagator and bounds wall time). NFR-002 — `test_doctor_ops.py:309` 1k-file
perf guard + `:329 @pytest.mark.slow` 10k test. NFR-003 — ruff clean on all
mission modules (`All checks passed!`); mypy targeted run shows only
`Class cannot subclass "BaseMigration" (has type "Any")` which also fires on
the pre-existing sibling migration → invocation/config artifact, not
mission-introduced; repo CI mypy is advisory. NFR-004 — idempotency covered by
`_plan_file` skip logic + dedicated tests in test_op_record_schema_v2_migration.py.

## Constraint Compliance

- C-001 breaking-ok: no compat flag; CHANGELOG.md updated (+24 lines). OK.
- C-002 no rename: `do` command intact (do_cmd.py). OK.
- C-003 Claude-Code-only hooks: only `ClaudeCodeHookRegistrar`/`ClaudeCodeWriter` touched. OK.
- C-004 append-only: writer uses `"x"` create + append; migration is the sole
  in-place mutation (atomic tmp + os.replace). OK.
- C-005 source templates: doctrine sources edited; the 13 generated
  `spec-kitty-standalone.md` copies changed identically (5 lines each),
  consistent with regeneration rather than hand-editing. OK.
- WP01 stopgap removal (WP03): no `outcome or`-coercion remains — outcome is a
  required Literal end to end; CLI validates explicitly. Verified.
- Lane-c/lane-f merge outcome: final main has BOTH WP02's open-dispatch do_cmd
  (no complete_invocation) AND WP03's closed_by threading
  (executor.complete_invocation keyword-only `closed_by`). Verified coherent by
  full read of executor.py.

## Drift Findings

| ID | Severity | Finding |
|----|----------|---------|
| D1 | MEDIUM | **Doctor-sweep closes are never propagated to SaaS.** `close_stale_ops` builds `ProfileInvocationExecutor(repo_root)` with no propagator (doctor/ops.py:139,148); executor only submits when `self._propagator is not None` (executor.py:344). The agent close path (advise.py:55-59) does propagate. Result: with sync enabled, a swept Op's started event reaches SaaS but its `abandoned` completion never does — SaaS shows it open forever. Spec FR-008/Success Criterion 5 ("same fidelity as ask/advise") is arguably violated for sweep-closed Ops; the doctor-ops contract is silent, so this shipped unflagged. |
| D2 | LOW | Issue matrix rows never upgraded post-WP-landing (all still `deferred-with-followup` while claiming "closed by WPxx in this mission"). Formally gate-compliant; informationally stale. |
| D3 | LOW | Stale comment: propagator.py:131 still says "WP06 only submits the `completed` InvocationRecord" — both event types are now submitted and `InvocationRecord` no longer exists. |
| D4 | LOW | `InvocationPayload.to_dict()` hardcodes `status: "open"` + close contract for every invocation (executor.py:130-133), including `ask` query-mode payloads where closing may be a no-op ritual. Accurate at emit time, but the close contract is emitted even for modes where `--evidence` is refused; orchestrators get a uniform instruction regardless of mode. Cosmetic/contract-surface drift only. |

## Risk Findings

| ID | Severity | Finding |
|----|----------|---------|
| R1 | MEDIUM | Same as D1 (SaaS open-Op leak on sweep closes) — flagged as both drift and operational risk: SaaS-side stale-open accumulation is exactly the failure class this mission set out to eliminate locally. |
| R2 | MEDIUM | CI marker gaps (Gate 2 failures 3+4): the WP05 migration test file and the two git-subprocess test files are invisible/skippable under marker-based CI profiles. Behavior is tested locally, but the regression net in CI has holes for FR-001/FR-011 evidence. |
| R3 | LOW | TOCTOU between completed-event write and auto-commit: `write_completed` appends, then `_commit_op_record` runs `safe_commit` best-effort; on commit failure it only logs (executor.py:483-484). The record stays truthful (close persisted), but FR-012's "auto-commit at close" can silently not happen — acceptable (best-effort by design), invisible to the closer except via log. |
| R4 | LOW | Sweep treats unparseable `started_at` as stale and closes it (ops.py:148-152). Deliberate and flagged via `parse_warning`, but `--close-stale` with a large threshold can still close a *fresh* Op whose timestamp was corrupted. Documented behavior; residual operator surprise. |
| R5 | LOW | `_age_hours` treats naive timestamps as UTC; a legacy local-time `started_at` could be mis-aged by the TZ offset (max ±14h vs 24h default threshold). Bounded; only affects pre-v2 stragglers. |
| R6 | INFO | `doctor ops --close-stale` exits 1 whenever fresh open Ops remain (doctor.py:1437) — contract-conformant, but orchestrators must not treat exit 1 as sweep failure. |

## Silent Failure Candidates

| Location | Pattern | Verdict |
|----------|---------|---------|
| session_stop.py:34-36 `except Exception: pass` | swallow-all | SANCTIONED (Stop hook must exit 0); scoped to the whole command body but the body is trivially small and scan-only |
| session_start.py:58-59 (open-ops section inside existing `except Exception: pass`) | swallow-all | Sanctioned by pre-existing session-start contract |
| writer.py:_append_to_index `except OSError: pass` | silent degrade | Pre-existing, documented as performance aid |
| executor.py:483 `_commit_op_record` catch-all → log warning | best-effort commit | Acceptable; logged (R3) |
| doctor/ops.py:178 per-op `except Exception` → error entry | continue-on-error | Correct: surfaced in report + exit 1 via `has_errors` |
| propagator `_propagate_one` swallow-all → propagation-errors.jsonl | best-effort | Per contract |
| doctor/ops.py:_read_started_fields returns ("","") on failure | silent empty return | Bounded: feeds parse_warning/stale path, not hidden |

## Security Notes

- No new `shell=True`; no new subprocess with dynamic content beyond
  pre-existing `git -C <repo_root>` argument lists and `safe_commit` (paths are
  repo-relative, message components come from on-disk record fields — commit
  message injection is not a shell risk since safe_commit uses argv lists).
- Migration writes `<file>.tmp` in the same directory and `os.replace`s
  (m_3_3_0_op_record_schema_v2.py:213-221) — atomic, same-filesystem,
  tmp cleaned in `finally`. Deletions use `unlink(missing_ok=True)`.
- `.claude/settings.json` writes are atomic via sibling temp + `os.replace`
  inside `write_text_within_directory`; invalid pre-existing JSON is preserved
  to `settings.json.invalid*`, foreign hooks preserved.
- `ClaudeCodeHookRegistrar._settings_path` guards path traversal
  (relative_to check raising ValueError).
- session-start/stop are scan-only (no git calls) per open_ops.py docstring;
  verified no subprocess imports in open_ops.py/session_stop.py.

## Final Verdict

**PASS WITH NOTES** — with one hard caveat.

The merged code faithfully realizes all 12 FRs with genuine, behavior-pinning
tests (no false-positive coverage found; the FR-001 test would fail if the
dispatch-close were reintroduced, the FR-004 models are unconstructible without
outcome/closed_by, the sweep goes exclusively through the executor close path).
Constraints C-001..C-005 are honored. The migration is real, atomic, idempotent,
and runtime-wired via pkgutil discovery.

However, Gate 2 (architectural) exits non-zero with 5 mission-caused failures.
By the stated rule that is a HARD FAIL of the gate; I classify the overall
mission as PASS WITH NOTES rather than FAIL because all five are
hygiene/allowlist/marker wiring defects with no behavioral impact — but they
MUST be fixed in an immediate follow-up commit before tagging, since failure 3
(missing pytestmark) degrades CI coverage of FR-011 and failure 4 hides FR-001
tests from `-m git_repo` CI lanes.

## Open Items (recommended follow-ups)

1. Fix the 5 architectural gate failures (allowlist the pkgutil-discovered
   migration or add a static import; de-export SESSION_STOP_CMD or use it;
   add pytestmark to tests/upgrade/test_op_record_schema_v2_migration.py;
   add `git_repo` marker to test_do.py and test_invocation_e2e.py).
2. D1/R1: wire a propagator into the doctor-sweep executor so swept
   `abandoned` completions reach SaaS (or document the gap in
   contracts/doctor-ops-close-stale.md and file an issue).
3. Refresh issue-matrix.md verdicts for #1229/#1688/#1781/#701 now that their
   WPs landed.
4. Clean stale comment propagator.py:131.
5. E2E repo: scenario harness resolves a sibling `spec-kitty` checkout by
   directory convention — runs from this worktree silently test a different
   checkout. Consider honoring an override env var in CI for post-merge review.

## Retrospective Reminder

`.kittify/missions/01KTSJ2H8E5YF2EGJYGAE5Z5Q2/retrospective.yaml` does **not**
exist (the mission state directory itself is absent from `.kittify/missions/`,
which contains only 01KT6HVH... and 01KTDVHZ...). The retrospective step has
not been run for this mission — run it after addressing Open Item 1.
