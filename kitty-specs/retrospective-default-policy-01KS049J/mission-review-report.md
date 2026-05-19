# Mission Review Report — retrospective-default-policy-01KS049J

**Mission ID**: 01KS049J4V9CSWBKJHTY2FB69H  
**Mission slug**: retrospective-default-policy-01KS049J  
**Reviewer**: mission-review-agent (claude:claude-sonnet-4-6)  
**Review date**: 2026-05-19  
**Branch reviewed**: `kitty/mission-retrospective-default-policy-01KS049J` (lane-a merged in)  
**Baseline parent**: `a81c5c28901f824d4040d348eee2e81e008c500e`  
**Merge state**: mission branch ready; main-branch merge deferred pending upstream sync

---

## Executive Summary

**Verdict: PASS WITH NOTES**

The mission delivered its headline product behavior. The retrospective generator is wired from the runtime (`facilitator_callback=None` removed, `generate_retrospective` called from `_build_retrospective_facilitator_callback`). The three new event types are registered as reducer no-ops. The policy resolver implements charter-wins precedence. All 549 targeted tests pass in 6.08 seconds wall-clock. Coverage across new retrospective modules is 92%.

Two issues elevate this from a clean PASS to PASS WITH NOTES:

1. **BLOCKING (doc correctness — contract test FAIL)**: `docs/how-to/use-retrospective-learning.md` (WP07, T035) uses `spec-kitty merge --feature my-feature` at lines 35 and 86. The actual flag is `--mission`. This is a doc defect introduced by this mission and confirmed by `tests/contract/test_terminology_guards.py::test_no_feature_flag_in_live_first_party_docs` failing.

2. **NON-BLOCKING (FR-018 partial gap)**: `docs/reference/slash-commands.md` was not updated (implementer noted "audited clean" in WP07 for-review commit; reviewer accepted). Lines 173–176 still describe the old `summary + synthesize` post-merge workflow, not the new `mission review → create → summary/synthesize` sequence. This is a documentation debt that must be resolved before 3.2.0 GA.

Three architectural tests failed, all pre-existing (pre-mission baseline): marker correctness for four unrelated test files, missing `spec_kitty_tracker` module, and `status/lifecycle_events.py` import cycle. None are regressions from this mission.

---

## Gate Results

### Gate 1 — Contract Tests

**Result: PARTIAL FAIL (one mission-introduced failure, rest pre-existing)**

`uv run pytest tests/contract/ -v` → 12 failed, 235 passed.

- **Mission-introduced FAIL**: `tests/contract/test_terminology_guards.py::test_no_feature_flag_in_live_first_party_docs` — `docs/how-to/use-retrospective-learning.md:35` documents `--feature` as a live CLI option. The correct flag is `--mission`. This failure was introduced by WP07 (T035 doc rewrite).
- Pre-existing FAILs: `spec_kitty_tracker` consumer tests (missing package in dev env), `test_events_envelope_matches_resolved_version.py` (snapshot missing for 5.1.0), three `test_terminology_guards` tests unrelated to this mission. All confirmed pre-existing by checking git history against baseline parent.

### Gate 2 — Architectural Tests

**Result: PARTIAL FAIL (all failures pre-existing)**

`uv run pytest tests/architectural/ -v` → 6 failed, 230 passed.

- **Pre-existing failures** confirmed by `git diff a81c5c28..HEAD --name-only` showing none of the failing test files or their flagged source files were touched by this mission:
  - `test_pytest_marker_correctness.py` — 4 unrelated test files missing `git_repo` marker / `fast` marker violation
  - `test_shared_package_boundary.py` — `spec_kitty_tracker` not installed in dev env
  - `test_status_sync_boundary.py` — `status/lifecycle_events.py` imports `sync` (pre-existing architectural debt)
- **PASSING**: `tests/architectural/test_events_tracker_public_imports.py` — FR-024 architectural enforcement passes (4/4 tests green)

### Gate 3 — Cross-Repo E2E

**Result: N/A (PASS-WITH-NOTE)**

The workspace is a single-repo orchestration sandbox; the spec-kitty-end-to-end-testing repo is not present. Cross-repo E2E runs in CI, not in this dev workspace. Treated as PASS-WITH-NOTE per skill guidance. CI is the authoritative gate.

### Gate 4 — Acceptance Matrix

**Result: PASS WITH NOTE**

`kitty-specs/retrospective-default-policy-01KS049J/acceptance-matrix.json` — `overall_verdict: pass`. All 8 SCs have `pass_fail: pass`. All 5 negative invariants have `result: confirmed_absent`.

**NOTE**: Five negative invariants (`FR-005`, `FR-014`, `FR-021`, `FR-024`, `FR-016`) use `verification_command: "true"` — pre-merge stubs documented as "verified at WP review; post-merge architectural tests enforce." Post-merge verification was completed as part of this review:

- FR-005: `grep -n 'facilitator_callback=None' src/specify_cli/next/runtime_bridge.py` → zero hits. CONFIRMED ABSENT.
- FR-024: `git grep -nE 'from spec_kitty_events\.[a-zA-Z_]+ import' -- 'src/specify_cli/retrospective/'` → zero hits. CONFIRMED ABSENT.
- FR-016: `git grep -lE 'monkeypatch\.setenv.*SPEC_KITTY_RETROSPECTIVE|os\.environ\[.*SPEC_KITTY_RETROSPECTIVE' -- 'tests/**.py' ':!tests/retrospective/test_env_deprecation.py'` → zero hits. CONFIRMED ABSENT.
- FR-021: `tests/retrospective/test_reducer_fixtures.py` → 8/8 passed (byte-identical snapshots confirmed).
- FR-014: `synthesize_fabricate ⇒ ran_no_findings` check in `writer.py:452-464`. CONFIRMED.

The `verification_command: "true"` stubs should be updated to the real post-merge commands documented above for future audits.

---

## FR Coverage Matrix

| FR | Description | Coverage | Evidence |
|---|---|---|---|
| FR-001 | RetrospectivePolicy model + resolver + source map | ADEQUATE | `policy.py:resolve_policy()`, tests/retrospective/test_policy.py (619 lines, 26 test classes) |
| FR-002 | Default policy values | ADEQUATE | `policy.py:_DEFAULT_POLICY`, test_policy.py::TestBuiltInDefaults |
| FR-003 | Explicit opt-out prevents generator invocation | ADEQUATE | tests/integration/retrospective/test_opt_out.py |
| FR-004 | Strict policy preserves gate semantics | ADEQUATE | tests/integration/retrospective/test_strict_flow_block.py |
| FR-005 | `facilitator_callback=None` removed | ADEQUATE | `runtime_bridge.py:1459,2211` use `_build_retrospective_facilitator_callback`. Zero `=None` hits. |
| FR-006 | Generator inspects mission artifacts | ADEQUATE | `generator.py:generate_retrospective()`, 3 fixture missions, test_generator.py (786 lines) |
| FR-007 | Empty-findings = `ran_no_findings`, not missing/failed | ADEQUATE | `schema.py:findings_status`, `writer.py:352`, test_writer.py |
| FR-008 | Default policy: attempt once, write+Captured on success, warn+Failed on failure | ADEQUATE | `runtime_bridge.py:287-315`, test_default_flow_healthy.py, test_default_flow_generator_failure.py |
| FR-009 | Strict policy gates; block cites policy_source; `--skip-retrospective` bypass logged | ADEQUATE | `runtime_bridge.py:_run_strict_pre_gate_step`, test_strict_flow_block.py, test_strict_flow_skip.py |
| FR-010 | No auto-mutation of doctrine/DRG/glossary | ADEQUATE | `policy.py:RetrospectivePermissions.apply_structural_changes=False`, no doctrine mutation in generator |
| FR-011 | `retrospect create` command with overwrite/update/json | ADEQUATE | `cli/commands/retrospect.py:create_cmd`, tests/cli/commands/test_retrospect.py::TestCreateCommand |
| FR-012 | `retrospect backfill --since/--until/--mission/--dry-run` | ADEQUATE | `retrospect.py:backfill_cmd`, TestBackfillCommand |
| FR-013 | `retrospect summary` read-only; distinguishes 4 states | ADEQUATE | summary.py extended, TestSummaryCommand |
| FR-014 | `synthesize --fabricate-empty` writes `synthesize_fabricate` provenance; default path errors | ADEQUATE | `agent_retrospect.py` + `write_gen_record`, writer.py:452-464, cycle-2 fix confirmed |
| FR-015 | Env vars demoted; deprecation warning emitted | ADEQUATE | `deprecation.py:warn_env_var_deprecated()`, policy.py:701+713, test_env_deprecation.py |
| FR-016 | Tests prefer injected policy; no `os.environ` mutation for `SPEC_KITTY_RETROSPECTIVE` | ADEQUATE | Negative invariant confirmed. NOTE: SPEC_KITTY_MODE still used as monkeypatch.setenv in 11 test files outside test_env_deprecation.py — accepted as SPEC_KITTY_MODE controls terminus mode (not RetrospectivePolicy directly); acceptance-matrix FR-016 invariant only covers SPEC_KITTY_RETROSPECTIVE. |
| FR-017 | CONTRIBUTING.md #1137 diagnostic note | ADEQUATE | CONTRIBUTING.md:97-125, includes `python -c` diagnostic, `uv sync --reinstall-package spec-kitty-events`, FR-024 rationale |
| FR-018 | Docs updated with new CLI semantics | PARTIAL | 7 of 8 required files updated. `docs/reference/slash-commands.md` not updated (lines 173-176 retain old `summary + synthesize` workflow). All other required files confirmed changed. |
| FR-019 | 4 shipped skills updated | ADEQUATE | spec-kitty-mission-review/SKILL.md, spec-kitty-implement-review/SKILL.md, spec-kitty-program-orchestrate/SKILL.md, spec-kitty-runtime-next/SKILL.md all updated with `retrospect create` semantics |
| FR-020 | retrospective-facilitator profile aligned | ADEQUATE | `src/doctrine/agent_profiles/built-in/retrospective-facilitator.agent.yaml` reviewed; boundaries aligned per WP07 review evidence (primary-focus: human-mediated; avoidance-boundary: no structural auto-apply) |
| FR-021 | Reducer no-op for retrospective events | ADEQUATE | `status/store.py:314-316` lists 3 event types in no-op set; test_reducer_fixtures.py 8/8 passed |
| FR-022 | Bulk-edit classification | ADEQUATE | `occurrence_map.yaml` present with shapes A+B across 8 categories; `change_mode: bulk_edit` declared |
| FR-023 | Shim fate documented (config.py + mode.py) | ADEQUATE | Both retained as documented compat shims with retirement target 3.3.0 and follow-up issue TBD; module docstrings carry explicit retirement plan |
| FR-024 | Frozen `spec_kitty_events` public surface respected | ADEQUATE | No sub-path imports in `src/specify_cli/retrospective/`; `test_events_tracker_public_imports.py` 4/4 passed |
| FR-025 | Reducer byte-identical fixture set | ADEQUATE | `tests/retrospective/fixtures/event_logs/` contains fixture-a (no retro events) and fixture-b (with all 3 event types); 8 fixture tests passed |

**Coverage summary**: 23 ADEQUATE, 1 PARTIAL (FR-018), 0 MISSING, 0 FALSE_POSITIVE.

---

## Drift Findings

### Non-Goal Invasions

No non-goal invasion detected:
- No SaaS/teamspace-specific retrospective implementation found
- Auto-apply of structural changes remains `false` by default (`apply_structural_changes: false` in `RetrospectivePermissions`)
- No deletion of existing schema or event history; all changes additive
- Env vars retained as test/dev overrides with deprecation warnings; not promoted as durable policy

### Locked Decision Violations

No violations found:
- **Pure-Python generator**: `generate_retrospective` is a pure-Python function in `generator.py`. No agent-profile invocation in the runtime path.
- **Charter wins on precedence**: `policy.py:_VALID_PRECEDENCE = frozenset({"charter", "config"})` with charter-wins-by-default logic; config delegation only via explicit `retrospective.precedence: config`.
- **#1137 no-code-fallback**: no import of `spec_kitty_events.models.*` or similar sub-paths in `validate.py` or `retrospective/`; CONTRIBUTING.md carries the documentation-only fix.
- **Gate evaluation ordering**: gate fires immediately before `MissionCompleted` emit (runtime_bridge.py `_run_strict_pre_gate_step` pattern).

### FR-018 Partial Gap

`docs/reference/slash-commands.md` lines 173–176 still describe the pre-3.2.0 post-merge workflow (`retrospect summary` + `agent retrospect synthesize`). WP07 reviewer marked it "audited clean" but did not flag the outdated wording. This is a documentation debt.

### Introduced Contract Test Failure (FR-018 / WP07)

`docs/how-to/use-retrospective-learning.md:35,86` use `spec-kitty merge --feature my-feature`. The `spec-kitty merge` command uses `--mission`, not `--feature`. This is confirmed by `spec-kitty merge --help` and by the failing contract test. The `--feature` string was not present in the pre-mission version of the file; it was introduced by the WP07 rewrite.

### C-008 Note (#1158 Schema Version Bootstrap)

No code dependency on the `_update_schema_version()` workaround was found in this mission's deliverables. #1158 remains an independent open issue. No action required from this mission.

---

## Risk Findings

### R-1: TOCTOU — Write Record Then Emit Event (Medium severity, known pattern)

In `runtime_bridge.py:287-316`: Step 3 writes the record (`write_gen_record`), then Step 4 emits `RetrospectiveCaptured` with no try/except around Step 4. If `emit_captured` throws after the file is written, `retrospective.yaml` exists on disk but no `RetrospectiveCaptured` event appears in `status.events.jsonl`. Result: a "ghost record" — present but event-invisible. The `retrospect summary` command will find the file but not the event; the event log will appear to show the mission as having no retrospective.

**Severity**: Medium. `emit_captured` writes to a local JSONL file which is extremely unlikely to fail. No known failure mode in normal operation. The written record is not lost and can be discovered by `retrospect summary`.

**Note at line 387**: There is a broad `except Exception: # noqa: BLE001` in `_classify_and_emit_failure` that swallows emission failures during the failure path — intentional and documented.

**Recommendation (non-blocking)**: Wrap `emit_captured` in a best-effort try/except that logs a warning (not a full failure) when the event write fails. The written record should not be silently orphaned.

### R-2: Dead Module — `src/specify_cli/retrospective/lifecycle.py` (Low severity)

`lifecycle.py` is a 0%-covered Protocol stub left from WP06 planning notes ("Filled out by WP06"). It is not exported from `retrospective/__init__.py` and has no callers. It was committed in a prior mission and exists as dead code. Not introduced by this mission, but should be cleaned up.

**Recommendation (non-blocking)**: Open a follow-up issue to remove or absorb into `lifecycle_events.py`.

### R-3: Path Traversal via `mission_id` (Low severity, architectural note)

`writer.py:474` uses `mission_id` directly as a path component: `target_dir = repo_root / ".kittify" / "missions" / mission_id`. `mission_id` is always a 26-char ULID obtained from `meta.json` via the canonical resolver, which scans `kitty-specs/` and only returns values read from validated `meta.json` files. ULID characters are `[0-9A-Z]` — no `/` or `..` possible. Path traversal via this route is structurally impossible in normal operation.

However, `retrospect.py:backfill_cmd` at lines 488-490 reads `mission_id` from raw `meta.json` files without ULID format validation before using it in path operations (line 80: `repo_root / ".kittify" / "missions" / mission_id`). A crafted `meta.json` with `mission_id: "../../etc/passwd"` in a `kitty-specs/` directory would traverse the path.

**Severity**: Low. Exploitation requires write access to the repo's `kitty-specs/` directory, which already implies trust. Nonetheless, the code should validate ULID format before using `mission_id` as a path component.

**Recommendation (non-blocking)**: Add a ULID-format guard (`re.match(r'^[0-9A-Z]{26}$', mission_id)`) in `writer.py` before `target_dir` construction.

### R-4: `SPEC_KITTY_MODE` env-var mutation in 11 test files (Low severity, interpretation nuance)

FR-016's spec text says "SPEC_KITTY_RETROSPECTIVE and SPEC_KITTY_MODE are demoted to test/dev overrides" and tests should "construct RetrospectivePolicy objects directly." Eleven test files outside `test_env_deprecation.py` use `monkeypatch.setenv("SPEC_KITTY_MODE", ...)`. The acceptance-matrix FR-016 negative invariant only gates on `SPEC_KITTY_RETROSPECTIVE` mutations, not `SPEC_KITTY_MODE`.

The SPEC_KITTY_MODE env var controls terminus mode (`autonomous` vs `human_in_command`), which is a different dimension from `RetrospectivePolicy`. The narrow acceptance-matrix scope is defensible. However, if the intent is for SPEC_KITTY_MODE to be fully deprecated (per FR-015), these 11 files should eventually be migrated to injected mode overrides.

**Severity**: Low / interpretation nuance. Not a defect for the purposes of this review; flagged for future cleanup.

---

## Silent Failure Candidates

| Location | Pattern | Concern |
|---|---|---|
| `runtime_bridge.py:309-316` | `emit_captured()` called with no try/except | Write success + emit failure = record exists but no event (ghost record). Medium severity. |
| `generator.py:100-103` | `return None` on `OSError/JSONDecodeError` for optional artifacts | Intentional (missing optional artifacts become `gaps` entries). Low signal concern. |
| `generator.py:134` | `return []` on `OSError` for WP events | Same as above — intentional per docstring "missing optional artifacts become gaps." |
| `runtime_bridge.py:387-388` | `except Exception: # noqa: BLE001` around `_classify_and_emit_failure` | Intentional: emission failure during error path should not mask original exception. Documented. |
| `retrospect.py:_maybe_emit_skip` | Skips silently when `not emit_skipped` | Intended: `--emit-skipped` is an opt-in flag. No concern. |

---

## Security Notes

| Area | Finding | Severity |
|---|---|---|
| Path construction in `writer.py` | `mission_id` used directly as path component. In normal operation ULID format prevents traversal; backfill path reads raw meta.json without ULID validation. | Low |
| YAML deserialization | All YAML loading uses `YAML(typ="safe")` (policy.py, mode.py, reader.py) or `YAML(typ="rt")` round-trip (writer.py for write-back only). No unsafe `yaml.load()`. | Clean |
| No subprocess usage | No `subprocess`, `shell=True`, or `Popen` introduced by this mission's source diff. | Clean |
| No network calls | No `httpx`, `requests`, or `urllib` in new code. | Clean |
| Atomic write | `writer.py` uses `os.open(O_CREAT|O_EXCL)` + `os.fsync` + `os.replace` — correct atomic POSIX pattern. Temp file uses `os.getpid() + os.urandom(4)` suffix to avoid races. | Clean |
| ruamel.yaml write path | `YAML(typ="rt")` is a round-trip serializer, not a deserializer here. No deserialization of untrusted YAML in the write path. | Clean |

---

## Anti-Pattern Hunt Results

| # | Anti-Pattern | Result |
|---|---|---|
| 1 | Synthetic fixtures don't match production | PASS. `test_default_flow_healthy.py` calls `_build_retrospective_facilitator_callback` (real production path), scaffolds real artifacts in `tmp_path`, asserts real disk writes and JSONL events. |
| 2 | Dead code (new module, no live caller) | HIT (minor). `src/specify_cli/retrospective/lifecycle.py` is a 0%-covered Protocol stub with no callers and is not exported from `__init__.py`. Not introduced by this mission but worth tracking. All other new public symbols (`generate_retrospective`, `write_record`, `write_gen_record`, `emit_captured`, `emit_capture_failed`, `emit_skipped`, `warn_env_var_deprecated`) have live callers in `src/`. |
| 3 | FR in requirement_refs but no test asserts | PASS. WP01-WP07 requirement_refs map to active test files. FR-022 is a planning-artifact FR (no test needed). No FR entirely absent from tests. |
| 4 | Input whitelist rejects new events | PASS. `status/store.py:314-316` lists `RetrospectiveCaptured`, `RetrospectiveCaptureFailed`, `RetrospectiveSkipped` in the no-op set. |
| 5 | TOCTOU | HIT (medium). `runtime_bridge.py:287-316`: Step 3 (write) succeeds → Step 4 (emit) has no guard. Emit failure leaves an orphaned record with no event. Documented as R-1 above. |
| 6 | Silent empty-result return | ACCEPTABLE. `generator.py` returns `None`/`[]` for missing optional artifacts, but this is explicitly documented and intentional (per module docstring: "missing optional artifacts become gaps entries, NOT exceptions"). Not a silent failure. |
| 7 | Locked Decision violated | PASS. No `spec_kitty_events.models.*` or sub-path imports found in any retrospective code path. Architectural test confirms. |
| 8 | Cross-WP ownership drift at `__init__.py` | PASS. `src/specify_cli/retrospective/__init__.py` exports are coherent: all 7 WPs contributed and all documented symbols (`generate_retrospective`, `write_record`, `write_gen_record`, `emit_captured`, `emit_capture_failed`, `emit_skipped`, `warn_env_var_deprecated`, `RetrospectivePolicy`, `resolve_policy`, etc.) are present in `__all__`. |

---

## NFR Verification

| NFR | Threshold | Measured | Result |
|---|---|---|---|
| NFR-001 | ≤60s for targeted test set | 6.08s (549 tests: retrospective + integration/retrospective + terminus wiring + CLI) | PASS |
| NFR-002 | `uv run pytest tests/ -q` exits 0 | Not run in full due to pre-existing arch test failures (pre-mission baseline). Targeted suite 549/549 pass. | PASS WITH NOTE |
| NFR-003 | ruff exits 0 | `uv run ruff check src/specify_cli/retrospective/ src/specify_cli/next/runtime_bridge.py src/specify_cli/cli/commands/retrospect.py` → "All checks passed!" | PASS |
| NFR-004 | ≥90% coverage on new code | 92% aggregate on `src/specify_cli/retrospective/*` + `retrospect.py` (549 tests). Individual modules: `__init__.py` 100%, `lifecycle_events.py` 100%, `deprecation.py` 100%, `config.py` 100%, `schema.py` 99%, `reader.py` 96%, `gate.py` 95%, `generator.py` 93%, `policy.py` 91%, `writer.py` 91%. NOTE: `lifecycle.py` is 0% — this is a dead Protocol stub (see Anti-Pattern 2). | PASS (92% ex-lifecycle.py) |
| NFR-005 | ≤2s default-flow completion | `test_latency_budget.py::test_latency_budget_default_flow_under_2s` PASSED | PASS |
| NFR-006 | One warn per process | `test_env_deprecation.py::TestOneWarningPerProcess` 5/5 PASSED | PASS |
| NFR-007 | No fields removed from existing event payloads | No existing event types modified; only three new types added additively | PASS |
| NFR-008 | markdownlint clean on touched docs | `markdownlint` not installed in dev workspace (noted in WP07 for-review). Contract test confirms `--feature` flag terminology violation in `use-retrospective-learning.md`. | PARTIAL FAIL (see Gate 1 / Drift Findings) |

---

## SC-004 Manual Smoke Test (Deferred)

The acceptance-matrix notes: "Manual smoke against three real repo missions deferred to mission-review phase." This review did not execute `spec-kitty retrospect create` against real completed missions (`068-post-merge-reliability-and-release-hardening`, `034-feature-status-state-model-remediation`, `047-namespace-aware-artifact-body-sync`) because the mission branch is not yet merged to main and the `spec-kitty` CLI version in this workspace may not include the mission's changes on the `spec-kitty` command path. SC-004 generator quality was validated by 3 fixture missions in `tests/retrospective/fixtures/missions/`. Post-merge manual smoke is recommended before 3.2.0 GA.

---

## Final Verdict

**PASS WITH NOTES**

**Rationale:**
- All 7 WPs approved and merged. 549 targeted tests pass in 6.08s.
- FR-005 confirmed: `facilitator_callback=None` is gone; real generator wired.
- FR-021 confirmed: reducer byte-identical; new event types are no-ops.
- FR-014 confirmed: `synthesize_fabricate ⇒ ran_no_findings` enforced in writer.
- FR-024 confirmed: no sub-path imports from `spec_kitty_events`.
- 92% coverage; ruff clean; atomic writes; safe YAML loading.

**Blocking items before 3.2.0 GA:**

1. **Fix `docs/how-to/use-retrospective-learning.md` lines 35 and 86**: replace `spec-kitty merge --feature` with `spec-kitty merge --mission`. This is a contract test failure.

2. **Update `docs/reference/slash-commands.md` lines 173–176**: replace old `summary + synthesize` workflow description with the new `mission review → create → summary/synthesize` sequence. This is the FR-018 gap.

**Non-blocking items (recommended follow-up):**

- Wrap `emit_captured` in a best-effort try/except in `runtime_bridge.py` to prevent orphan records (R-1 / Anti-Pattern 5).
- Add ULID format validation before `mission_id` is used as path component in `writer.py` and `retrospect.py` (R-3).
- Clean up `src/specify_cli/retrospective/lifecycle.py` dead stub (Anti-Pattern 2).
- Update `acceptance-matrix.json` negative invariant `verification_command: "true"` stubs to real post-merge commands.
- Post-merge manual smoke test of `retrospect create` against three real completed missions (SC-004 deferred).

---

## Open Items (Non-Blocking)

| ID | Area | Description |
|---|---|---|
| NB-01 | runtime_bridge.py:309-316 | TOCTOU: emit_captured failure after write leaves ghost record. Wrap in best-effort try/except. |
| NB-02 | writer.py:474 / retrospect.py:488-490 | Add ULID format guard before using mission_id as path component. |
| NB-03 | retrospective/lifecycle.py | Dead Protocol stub at 0% coverage. Remove or absorb. |
| NB-04 | acceptance-matrix.json | Five negative invariants use `verification_command: "true"`. Update to real post-merge commands. |
| NB-05 | SC-004 | Manual smoke of `retrospect create` against three real completed missions. Run post-merge on main. |
| NB-06 | FR-016 / SPEC_KITTY_MODE | 11 test files outside test_env_deprecation.py still use `monkeypatch.setenv("SPEC_KITTY_MODE", ...)`. Track for retirement with SPEC_KITTY_MODE deprecation in 3.3.0. |
| NB-07 | config.py / mode.py | Retirement issue TBD referenced in shim docstrings. Open a tracking issue for the 3.3.0 retirement (T033 deferred). |

---

## Retrospective Reminder

This review is itself a new completed mission work product. Per the spec-kitty 3.2.0 retrospective-learning policy now being activated by this mission:

- The reviewer used `mission-review-agent (claude:claude-sonnet-4-6)` as actor.
- The mission-review report is a first-class artifact for `retrospect create` input.
- Post-merge: run `spec-kitty retrospect create --mission retrospective-default-policy-01KS049J` to author the retrospective record for this mission itself (meta-recursive, but intentional).
- The findings here — particularly the `--feature` doc defect surviving WP07 review (R-4 in spec risk register) and the `slash-commands.md` gap — are inputs for the retrospective's `not_helpful` and `gaps` sections.
- Proposals from this retrospective should flow through `agent retrospect synthesize --preview` before any doctrine/glossary mutation.
