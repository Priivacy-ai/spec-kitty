# Tasks — Quality and DevEx Hardening 3.2

**Mission**: `quality-devex-hardening-3-2-01KRJGKH`
**Branch**: `fix/quality-check-updates`
**Spec**: [spec.md](spec.md)
**Plan**: [plan.md](plan.md)

This document enumerates the work packages and their constituent subtasks. Sequence below preserves the dependency graph from `plan.md` § Phase 2. Lane computation is left to `spec-kitty agent mission finalize-tasks`.

## Subtask Index

| ID | Description | WP | Parallel |
|---|---|---|---|
| T001 | Add type stubs (types-PyYAML/types-toml/types-jsonschema/types-psutil/types-requests) to dev deps | WP01 | |
| T002 | Localize `# type: ignore[import-untyped]` on each `re2` import site (research §1) | WP01 | [P] |
| T003 | Regression test for `doctor.py:1092` `RepairReport` vs `RepoAuditReport` mismatch (capture real bug before narrowing types) | WP01 | |
| T004 | Fix typed-code errors in `status/reducer.py`, `sync/__init__.py`, `agent_retrospect.py` | WP01 | [P] |
| T005 | Fix typed-code errors in `auth/recovery`, `next/_internal_runtime/*`, `sync/*` (excluding `__init__.py`) | WP01 | [P] |
| T006 | Verify `uv run mypy --strict src/specify_cli src/charter src/doctrine` exits 0 (acknowledging doctor.py errors are owned by WP06) | WP01 | |
| T007 | Record WP01 evidence (chosen scope option A, decision DM-01KRJHT7QD7XQMY33Y5TDTQ80V) and CHANGELOG entry fragment | WP01 | |
| T008 | Create `tests/upgrade/test_m_0_8_0_symlink_windows.py` with happy `OSError → shutil.copy2` fallback via `monkeypatch.setattr` | WP02 | |
| T009 | Parametrize the dual-failure case (`shutil.copy2` raises `OSError`) and assert `errors` list entry | WP02 | |
| T010 | Verify test runs on POSIX CI (no Windows-only mark); record WP02 glossary fragment for "characterization test" | WP02 | |
| T011 | Author characterization tests for `_canonicalize_status_row` using legacy rows from `.kittify/migrations/mission-state/` (commit BEFORE refactor) | WP03 | |
| T012 | Create `src/specify_cli/migration/canonicalization.py` with `CanonicalRule` Protocol + `CanonicalStepResult` + `CanonicalPipelineResult` + `MigrationContext` + `apply_rules` runner | WP03 | |
| T013 | Lift `_canonicalize_status_row` rules onto Protocol — 10 named pure rules + `_RULES` tuple | WP03 | |
| T014 | Lift analogous rules in `rebuild_state.py` onto the same Protocol (validates two-consumer bar) | WP03 | |
| T015 | Per-rule unit tests in `tests/unit/migration/test_canonicalization_rules.py` (parametrized) | WP03 | [P] |
| T016 | Update `architecture/2.x/04_implementation_mapping/code-patterns.md` to cite `migration/canonicalization.py` as canonical Transformer-flavor implementation | WP03 | |
| T017 | Record WP03 glossary fragment for "pipeline-shape", "rule pipeline" (with three flavors) | WP03 | |
| T018 | Audit `release/changelog.py` regexes for catastrophic-backtracking shapes (per `secure-regex-catastrophic-backtracking` tactic) | WP04 | |
| T019 | Apply rewrite ladder (bound quantifier / refactor nested / possessive / negated char class) per the secure-regex tactic | WP04 | |
| T020 | Add wall-clock regression test in `tests/regressions/test_changelog_regex_redos.py` (≤100 ms for 100 000 chars adversarial input) | WP04 | |
| T021 | Record Sonar rationale annotations (via the Sonar UI) for each regex hotspot remediation | WP04 | |
| T022 | Record WP04 glossary fragment for "catastrophic backtracking" + Sonar evidence | WP04 | |
| T023 | Charter.py orchestration tests — typer-runner integration in `tests/cli/commands/test_charter_orchestration.py` (research §4 Bucket A) | WP05 | |
| T024 | Charter.py IO tests — `tmp_path` real-IO in `tests/cli/commands/test_charter_io.py` (Bucket B) | WP05 | [P] |
| T025 | Charter.py rendering tests — substring-stable assertions in `tests/cli/commands/test_charter_rendering.py` (Bucket C) | WP05 | [P] |
| T026 | Coverage tests for `cli/commands/charter_bundle.py` and `cli/commands/agent/config.py` | WP05 | [P] |
| T027 | Coverage tests for `next/_internal_runtime/engine.py` (hot paths only) and `core/file_lock.py` (uncovered branches) | WP05 | [P] |
| T028 | Record WP05 glossary fragment | WP05 | |
| T029 | Characterization tests for `doctor.py::mission_state` covering `--audit` / `--fix` / `--teamspace-dry-run` modes (commit BEFORE refactor) | WP06 | |
| T030 | Fix typing errors at `doctor.py:631`, `:1092..1125` (regression test for `MissionRepairResult.findings` real-branch bug FIRST) | WP06 | |
| T031 | Extract `_validate_modes`, `_resolve_fail_on`, `_resolve_audit_root` helpers (`refactoring-extract-first-order-concept`) | WP06 | |
| T032 | Extract `_run_repair`, `_run_teamspace_dry_run`, `_run_audit` per-mode runners | WP06 | |
| T033 | Extract shared `_emit` helper for the JSON-vs-pretty pattern (logical duplication across the three modes) | WP06 | |
| T034 | Slim `mission_state` to ~30-line orchestrator; verify all characterization tests pass; record WP06 glossary fragment for "structural debt" and "deliberate linearity" | WP06 | |
| T035 | Triage `127.0.0.1` loopback hotspots in auth/sync callback paths; mark safe-by-design in Sonar with rationale | WP07 | |
| T036 | Triage review-lock signal-safety hotspot (either fix or document rationale in Sonar) | WP07 | |
| T037 | Verify Sonar gate is OK on `main` via `work/snippets/sonarcloud_branch_review.sh Priivacy-ai_spec-kitty main` | WP07 | |
| T038 | Flip `.github/workflows/ci-quality.yml::sonarcloud` trigger from `schedule \|\| workflow_dispatch` to `always()`; remove the temporary deferral comment block | WP07 | |
| T039 | Record WP07 glossary fragment for "Sonar quality gate" | WP07 | |
| T040 | Promote `contracts/stale-lane-auto-rebase-classifier-policy.md` to `architecture/2.x/adr/2026-05-14-1-stale-lane-auto-rebase-classifier-policy.md` with status ACCEPTED (operator approval flag) | WP08 | |
| T041 | Implement `src/specify_cli/merge/conflict_classifier.py` with the five rules (R-PYPROJECT-DEPS-UNION, R-INIT-IMPORTS-UNION, R-URLS-LIST-UNION, R-UVLOCK-REGENERATE, R-DEFAULT-MANUAL) per data-model.md and ADR | WP08 | |
| T042 | Per-rule unit tests in `tests/integration/merge/test_conflict_classifier.py` (parametrized happy + counter-example for each rule) | WP08 | [P] |
| T043 | Implement `src/specify_cli/lanes/auto_rebase.py` orchestrator (attempt `git merge`, classify, apply, regenerate `uv.lock` under `core.file_lock` mutex) | WP08 | |
| T044 | Integration test for two-lane additive merge in `tests/integration/lanes/test_auto_rebase_additive.py` | WP08 | |
| T045 | Negative integration test for semantic conflict (fail-safe halt with current actionable error; no partial auto-resolution leaks) | WP08 | |
| T046 | Update `src/specify_cli/lanes/merge.py` to delegate to `auto_rebase` before halting on stale-detect; record WP08 glossary fragment | WP08 | |
| T047 | Create `src/specify_cli/core/upgrade_probe.py` per data-model.md `UpgradeProbeResult` + `UpgradeChannel` + probe function (httpx-based PyPI fetch, 2 s timeout, four-channel classification) | WP09 | |
| T048 | Create `src/specify_cli/core/upgrade_notifier.py` with `maybe_emit_upgrade_notice` + cache logic (24 h success / 1 h unknown TTL) + `SPEC_KITTY_NO_UPGRADE_CHECK` opt-out | WP09 | |
| T049 | Wire notifier into CLI hot path (gated by `should_check_version()`); modify `core/version_checker.py` to extend the existing gate (do NOT introduce a parallel gate) | WP09 | |
| T050 | Behavior tests in `tests/core/test_upgrade_probe_and_notifier.py` using `requests_mock` + `freezegun`; cover all four channels + cache hit/miss + opt-out + network failure | WP09 | [P] |
| T051 | Wall-clock test asserting ≤100 ms cache-warm budget per NFR-004 | WP09 | [P] |
| T052 | Document opt-out env var in `spec-kitty --help` output; record WP09 glossary fragment | WP09 | |
| T053 | Consolidate all WP01..WP09 glossary-fragment YAML into `.kittify/glossaries/spec_kitty_core.yaml`; verify every Domain Language term in `spec.md` has an entry | WP10 | |
| T054 | Verify `architecture/2.x/04_implementation_mapping/code-patterns.md` cites `migration/canonicalization.py` (introduced by WP03) | WP10 | |
| T055 | Author mission-review report `mission-review.md` citing every doctrine tactic applied per WP + linking the code-patterns catalog | WP10 | |
| T056 | Run NFR-001 release-stability smoke (init → specify → plan → tasks → implement → review → merge → PR on a throwaway feature); record results in mission-review | WP10 | |
| T057 | Update `CHANGELOG.md` with the mission's deliverables: cross-reference all 6 tickets (#971, #825, #595, #629, #771, #740) + mypy scope decision + auto-rebase ADR + push-time Sonar restoration | WP10 | |

## Work Packages

### WP01 — Mypy strict baseline (excluding doctor.py)

**Goal**: Make `uv run mypy --strict src/specify_cli src/charter src/doctrine` exit 0 on every file the WP owns. Doctor.py errors are owned by WP06 and addressed there.

**Priority**: P0 (foundation; everything else prefers a clean baseline).

**Independent test**: `uv run mypy --strict <WP01 owned files>` exits 0; the regression test for `MissionRepairResult.findings` (added in T003) fails before T030 and passes after.

**Doctrine tactics applied**:

- [`function-over-form-testing`](../../../src/doctrine/tactics/shipped/testing/function-over-form-testing.tactic.yaml) — regression test asserts the observable behavior of the broken branch, not the type assertion.
- [`refactoring-guard-clauses-before-polymorphism`](../../../src/doctrine/tactics/shipped/refactoring/refactoring-guard-clauses-before-polymorphism.tactic.yaml) — applied only if conditional flattening is needed to make types narrow.

**Included subtasks**:

- [x] T001 Add type stubs to dev deps (WP01)
- [x] T002 [P] Localize `re2` strict-drop type-ignore comments (WP01)
- [x] T003 Regression test for `doctor.py:1092` (commit BEFORE T030 in WP06) (WP01)
- [x] T004 [P] Fix typed-code errors in `status/reducer.py`, `sync/__init__.py`, `agent_retrospect.py` (WP01)
- [x] T005 [P] Fix typed-code errors in `auth/recovery`, `next/_internal_runtime/*`, `sync/*` (WP01)
- [x] T006 Verify mypy strict exits 0 on WP01-owned files (WP01)
- [x] T007 Record evidence + CHANGELOG fragment (WP01)

**Dependencies**: none (foundation).

**Risks**: T003's regression test may surface the `MissionRepairResult.findings` bug is more substantial than the typing drift indicates — escalate to operator if behavior fix is non-trivial.

**Prompt**: [`tasks/WP01-mypy-strict-baseline.md`](tasks/WP01-mypy-strict-baseline.md)

---

### WP02 — Windows symlink-fallback test (#629)

**Goal**: Add a behavior test for the `m_0_8_0_worktree_agents_symlink` migration's `OSError → shutil.copy2` fallback path. Test runs on every POSIX CI pass via `monkeypatch`.

**Priority**: P1 (small WP; primes Windows-fallback confidence).

**Independent test**: `uv run pytest tests/upgrade/test_m_0_8_0_symlink_windows.py -v` passes both parameterized cases.

**Doctrine tactics applied**:

- [`function-over-form-testing`](../../../src/doctrine/tactics/shipped/testing/function-over-form-testing.tactic.yaml) — behavior assertion on `AGENTS.md` file content and migration `changes` / `errors` lists.

**Included subtasks**:

- [x] T008 Create test file with happy fallback case (WP02)
- [x] T009 Parametrize dual-failure case (WP02)
- [x] T010 Verify POSIX CI execution + glossary fragment (WP02)

**Dependencies**: none (the symlink test is independent of WP01's typing fixes — it lives under `tests/upgrade/` and uses `monkeypatch` to drive the migration directly).

**Risks**: minimal.

**Prompt**: [`tasks/WP02-windows-symlink-test.md`](tasks/WP02-windows-symlink-test.md)

---

### WP03 — Canonicalization rule-pipeline extraction

**Goal**: Lift `_canonicalize_status_row` onto the `CanonicalRule` Protocol (Transformer flavor). Reuse the Protocol in `rebuild_state.py` (two-consumer bar). Update code-patterns catalog.

**Priority**: P1 (motivating structural-debt refactor; concrete demonstration of the rule-pipeline tactic).

**Independent test**: characterization tests captured pre-refactor (T011) remain green after T013/T014; per-rule unit tests pass (T015); pipeline integration tests pass.

**Doctrine tactics applied**:

- [`chain-of-responsibility-rule-pipeline`](../../../src/doctrine/tactics/shipped/code-patterns/chain-of-responsibility-rule-pipeline.tactic.yaml) (Transformer flavor) — the central tactic for this WP.
- [`tdd-red-green-refactor`](../../../src/doctrine/tactics/shipped/testing/tdd-red-green-refactor.tactic.yaml) — characterization tests precede refactor.
- [`refactoring-extract-first-order-concept`](../../../src/doctrine/tactics/shipped/refactoring/refactoring-extract-first-order-concept.tactic.yaml) — each rule is a first-order concept.
- [`function-over-form-testing`](../../../src/doctrine/tactics/shipped/testing/function-over-form-testing.tactic.yaml) — per-rule tests are value-transformer tests.

**Included subtasks**:

- [x] T011 Characterization tests for `_canonicalize_status_row` (BEFORE refactor commit) (WP03)
- [x] T012 Create `canonicalization.py` with Protocol + runner (WP03)
- [x] T013 Lift `_canonicalize_status_row` rules (WP03)
- [x] T014 Lift `rebuild_state.py` rules (WP03)
- [x] T015 [P] Per-rule unit tests (WP03)
- [x] T016 Update code-patterns catalog (WP03)
- [x] T017 Glossary fragment ("pipeline-shape", "rule pipeline") (WP03)

**Dependencies**: WP01 (migration code must be type-clean before refactor).

**Risks**: characterization-test corpus must include a representative fixture for every rule in the pipeline; a missed rule means a green refactor that silently changes behavior. Mitigation: pre-T011 audit of `.kittify/migrations/mission-state/` for fixture coverage breadth.

**Prompt**: [`tasks/WP03-canonicalization-rule-pipeline.md`](tasks/WP03-canonicalization-rule-pipeline.md)

---

### WP04 — Sonar regex hotspots + wall-clock tests

**Goal**: Apply the `secure-regex-catastrophic-backtracking` tactic to every regex hotspot in `release/changelog.py`. Every fix carries a wall-clock regression test.

**Priority**: P1 (Sonar hotspot review required for gate-green).

**Independent test**: `uv run pytest tests/regressions/test_changelog_regex_redos.py -v --durations=10` passes, slowest test < 100 ms.

**Doctrine tactics applied**:

- [`secure-regex-catastrophic-backtracking`](../../../src/doctrine/tactics/shipped/secure-regex-catastrophic-backtracking.tactic.yaml) — every regex change.
- [`function-over-form-testing`](../../../src/doctrine/tactics/shipped/testing/function-over-form-testing.tactic.yaml) — completion-within-budget is the observable outcome.

**Included subtasks**:

- [x] T018 Audit `release/changelog.py` regexes for dangerous shapes (WP04)
- [x] T019 Apply rewrite ladder (WP04)
- [x] T020 Wall-clock regression test (WP04)
- [x] T021 Sonar rationale annotations (WP04)
- [x] T022 Glossary fragment ("catastrophic backtracking") (WP04)

**Dependencies**: none (regex rewrites in `release/changelog.py` are independent of WP01's typing fixes; happy-path correctness tests are local to this WP).

**Risks**: a rewrite that loses match semantics is a silent behavior regression — the wall-clock test does not catch this. Mitigation: every rewrite includes a correctness test on the original happy-path corpus.

**Prompt**: [`tasks/WP04-regex-hotspots.md`](tasks/WP04-regex-hotspots.md)

---

### WP05 — Sonar coverage on hot release/auth/sync paths

**Goal**: Author behavior-driven coverage tests for the highest-uncov files. Tests assert observable outcomes; no mocks beyond true system boundaries; characterization-first if any source-file modification is required (DEFER if it is — Pedro reports, does not fix in WP05).

**Priority**: P1 (drives `new_coverage` toward 80 %; precondition for #825 gate flip).

**Independent test**: `uv run pytest tests/cli/commands/test_charter*.py tests/cli/commands/test_agent_config_coverage.py tests/integration/test_internal_runtime_engine.py tests/core/test_file_lock_behavior.py -v` passes; Sonar reports `new_coverage` ≥ 80 on the touched surfaces.

**Doctrine tactics applied**:

- [`function-over-form-testing`](../../../src/doctrine/tactics/shipped/testing/function-over-form-testing.tactic.yaml) — every test.
- [`tdd-red-green-refactor`](../../../src/doctrine/tactics/shipped/testing/tdd-red-green-refactor.tactic.yaml) — only if a refactor surfaces.

**Included subtasks**:

- [x] T023 Charter orchestration tests (typer-runner integration) (WP05)
- [x] T024 [P] Charter IO tests (tmp_path real I/O) (WP05)
- [x] T025 [P] Charter rendering tests (substring-stable assertions) (WP05)
- [x] T026 [P] Coverage tests for `charter_bundle.py` and `agent/config.py` (WP05)
- [x] T027 [P] Coverage tests for `internal_runtime/engine.py` and `core/file_lock.py` (WP05)
- [x] T028 Glossary fragment (WP05)

**Dependencies**: WP01, WP04 (regex shape locked before authoring tests that may exercise regex paths).

**Risks**: behavior tests on `charter.py` may surface real bugs (e.g. file-encoding edge cases) — Pedro reports as new issues, does not fix in this WP. Test files must use substring-stable assertions, not full-output snapshots (per research §4 Bucket C).

**Prompt**: [`tasks/WP05-coverage-hot-paths.md`](tasks/WP05-coverage-hot-paths.md)

---

### WP06 — `doctor.py::mission_state` typing + multiplexer refactor

**Goal**: Fix doctor.py typing errors (regression test first for the `MissionRepairResult.findings` real-branch bug). Refactor the `mission_state` CLI command into per-mode runners + shared `_emit` helper. Characterization tests precede refactor.

**Priority**: P1 (closes WP01's doctor.py carve-out; demonstrates extract-first-order-concept on a debt-classified offender).

**Independent test**: characterization tests pass before and after refactor; `uv run mypy --strict src/specify_cli/cli/commands/doctor.py` exits 0; each extracted helper has cognitive complexity ≤ 10.

**Doctrine tactics applied**:

- [`tdd-red-green-refactor`](../../../src/doctrine/tactics/shipped/testing/tdd-red-green-refactor.tactic.yaml) — characterization tests precede refactor (NFR-003).
- [`refactoring-extract-first-order-concept`](../../../src/doctrine/tactics/shipped/refactoring/refactoring-extract-first-order-concept.tactic.yaml) — per-mode runner + shared `_emit` extraction.
- [`function-over-form-testing`](../../../src/doctrine/tactics/shipped/testing/function-over-form-testing.tactic.yaml) — tests assert exit codes + emitted artifacts, not internal calls.

**Included subtasks**:

- [x] T029 Characterization tests for the three modes (BEFORE refactor) (WP06)
- [x] T030 Fix typing errors at lines 631, 1092–1125 (with regression test FIRST) (WP06)
- [x] T031 Extract `_validate_modes`, `_resolve_fail_on`, `_resolve_audit_root` (WP06)
- [x] T032 Extract per-mode runners (WP06)
- [x] T033 Extract shared `_emit` helper (WP06)
- [x] T034 Slim `mission_state` to ~30-line orchestrator; glossary fragment (WP06)

**Dependencies**: WP01.

**Risks**: the `MissionRepairResult.findings` bug may have a non-trivial fix that pulls Pedro out of locality — if so, fix in a focused PR before this WP closes; do not let typing-drift work expand into unrelated cleanup.

**Prompt**: [`tasks/WP06-doctor-multiplexer-refactor.md`](tasks/WP06-doctor-multiplexer-refactor.md)

---

### WP07 — Sonar hotspot non-regex triage + push-time Sonar restoration

**Goal**: Resolve the remaining 5 non-regex Sonar hotspots (loopback `127.0.0.1` × 4, review-lock signal safety × 1). Once the gate is OK on `main`, flip the push-time Sonar trigger.

**Priority**: P1 (release-gate flip; final Sonar workstream).

**Independent test**: `bash work/snippets/sonarcloud_branch_review.sh Priivacy-ai_spec-kitty main | head -10` shows `status: OK`; next push to `main` produces a Sonar run with `conclusion: success`.

**Doctrine tactics applied**:

- (CI yaml change — coordinate with infra reviewer.)
- [`secure-design-checklist`](../../../src/doctrine/tactics/shipped/secure-design-checklist.tactic.yaml) — applied if the review-lock signal safety hotspot needs a code fix.

**Included subtasks**:

- [x] T035 Triage `127.0.0.1` loopback hotspots (safe-by-design rationale) (WP07)
- [x] T036 Triage review-lock signal-safety hotspot (WP07)
- [x] T037 Verify Sonar gate OK on `main` (WP07)
- [x] T038 Flip `.github/workflows/ci-quality.yml` sonarcloud trigger (WP07)
- [x] T039 Glossary fragment ("Sonar quality gate") (WP07)

**Dependencies**: WP04 + WP05 + WP06 (Sonar gate must be green first).

**Risks**: race condition where another mission merges between WP07's gate verification and the trigger flip and re-introduces gate-failing code. Mitigation: re-run the verification immediately before the flip.

**Prompt**: [`tasks/WP07-sonar-triage-and-gate-flip.md`](tasks/WP07-sonar-triage-and-gate-flip.md)

---

### WP08 — Stale-lane auto-rebase: ADR + classifier + orchestrator

**Goal**: Promote the classifier-policy ADR draft to canonical status. Implement the classifier and orchestrator. Auto-rebase additive-only conflicts in `spec-kitty merge`; fail-safe on anything unmatched.

**Priority**: P1 (DevEx improvement; addresses ~30 min/mission rote-merge cost called out in #771).

**Independent test**: `uv run pytest tests/integration/lanes/test_auto_rebase_additive.py tests/integration/merge/test_conflict_classifier.py -v` passes; two-lane additive smoke (quickstart §5) completes without operator intervention; semantic-conflict negative smoke halts with the current actionable error.

**Doctrine tactics applied**:

- (ADR-led design — architectural decision recorded before implementation.)
- [`function-over-form-testing`](../../../src/doctrine/tactics/shipped/testing/function-over-form-testing.tactic.yaml) — every test.
- [`secure-design-checklist`](../../../src/doctrine/tactics/shipped/secure-design-checklist.tactic.yaml) — for the `uv lock` regeneration step (operates on the lockfile boundary).

**Included subtasks**:

- [x] T040 Promote ADR draft to canonical (operator approval gate) (WP08)
- [x] T041 Implement `merge/conflict_classifier.py` per ADR (WP08)
- [x] T042 [P] Per-rule unit tests (WP08)
- [x] T043 Implement `lanes/auto_rebase.py` orchestrator (WP08)
- [x] T044 Two-lane additive integration test (WP08)
- [x] T045 Semantic-conflict negative integration test (WP08)
- [x] T046 Update `lanes/merge.py` to delegate; glossary fragment (WP08)

**Dependencies**: WP01.

**Risks**: a wrongly-classified semantic conflict silently combines incompatible code — mitigated by fail-safe default (`R-DEFAULT-MANUAL` always last; AST/TOML validation after auto-resolution; classifier `try/except` defaults to `Manual` on any rule-evaluation exception).

**Prompt**: [`tasks/WP08-auto-rebase-classifier.md`](tasks/WP08-auto-rebase-classifier.md)

---

### WP09 — Upgrade probe + notifier (#740)

**Goal**: Add `core/upgrade_probe.py` + `core/upgrade_notifier.py` for the "no upgrade available" / "already current" UX. Non-blocking, cache-aware, opt-out env var.

**Priority**: P2 (DevEx improvement).

**Independent test**: `uv run pytest tests/core/test_upgrade_probe_and_notifier.py -v` passes; quickstart §6 cold-cache + warm-cache + opt-out + probe-failure smokes all behave as documented; wall-clock test asserts ≤ 100 ms cache-warm budget.

**Doctrine tactics applied**:

- [`secure-design-checklist`](../../../src/doctrine/tactics/shipped/secure-design-checklist.tactic.yaml) — new external surface (PyPI probe).
- [`function-over-form-testing`](../../../src/doctrine/tactics/shipped/testing/function-over-form-testing.tactic.yaml) — every test.

**Included subtasks**:

- [x] T047 Create `core/upgrade_probe.py` per data-model (WP09)
- [x] T048 Create `core/upgrade_notifier.py` with cache + opt-out (WP09)
- [x] T049 Wire into CLI hot path via `should_check_version()` (WP09)
- [x] T050 [P] Behavior tests (4 channels + cache + opt-out + failure) (WP09)
- [x] T051 [P] Wall-clock test (NFR-004 budget) (WP09)
- [x] T052 Document opt-out in `--help`; glossary fragment (WP09)

**Dependencies**: WP01.

**Risks**: PyPI rate limits or DNS issues cause probe failures — mitigated by the 1 h `UNKNOWN`-channel cache TTL (prevents repeated re-probing) and the global swallow-and-return policy on the hot path.

**Prompt**: [`tasks/WP09-upgrade-probe-notifier.md`](tasks/WP09-upgrade-probe-notifier.md)

---

### WP10 — Glossary consolidation + mission-review

**Goal**: Consolidate per-WP glossary fragments into the canonical glossary YAML. Verify code-patterns catalog is up to date. Author the mission-review report. Run the release-stability smoke. Update CHANGELOG.

**Priority**: P0 (closes the release-gate acceptance).

**Independent test**: every term in `spec.md` § Domain Language has a `status: active` entry in `.kittify/glossaries/spec_kitty_core.yaml`; mission-review report enumerates every doctrine tactic applied per WP; NFR-001 smoke completes without manual repair; CHANGELOG documents the mission's six-ticket closeout.

**Doctrine tactics applied**:

- (consolidation + audit role — no new patterns introduced)
- Reviewer-Renata profile applied for the mission-review report.
- Curator-Carla profile applied for the glossary consolidation.

**Included subtasks**:

- [x] T053 Consolidate WP01..WP09 glossary fragments into `spec_kitty_core.yaml` (WP10)
- [x] T054 Verify code-patterns catalog cites `migration/canonicalization.py` (WP10)
- [x] T055 Author `mission-review.md` (WP10)
- [x] T056 Run NFR-001 release-stability smoke (WP10)
- [x] T057 Update `CHANGELOG.md` with the mission's deliverables (WP10)

**Dependencies**: WP01, WP02, WP03, WP04, WP05, WP06, WP07, WP08, WP09.

**Risks**: NFR-001 smoke may surface a real regression in the post-merge `main` — Pedro reports immediately and triages with the operator; the mission cannot be marked release-ready otherwise.

**Prompt**: [`tasks/WP10-glossary-mission-review.md`](tasks/WP10-glossary-mission-review.md)

---

## Lane Computation Hints (for `finalize-tasks`)

- **WP01, WP02, WP04** are independent — no shared `owned_files`.
- **WP03, WP05, WP06, WP08, WP09** depend on WP01.
- **WP05** is independent of WP04 textually (different files) but Pedro sequences WP05 after WP04 to lock the regex contract before authoring regex-adjacent tests.
- **WP07** depends on WP04, WP05, WP06 (Sonar gate must be green before flip).
- **WP10** depends on WP01..WP09.

Suggested lane shape:

| Lane | WPs (in order) |
|---|---|
| Lane A | WP01 → WP03 → WP06 |
| Lane B | WP02 |
| Lane C | WP04 → WP05 → WP07 |
| Lane D | WP08 |
| Lane E | WP09 |
| Lane F | WP10 (after all merge) |

`finalize-tasks` reads `dependencies` from each WP's frontmatter and computes the actual lanes — the table above is an advisory seed.

## Scope policy

The full ten-WP scope is the mission's deliverable. **No WP is deferred.** The mission's binding philosophy (`spec.md` § Mission Philosophy item 3 — "Quality > speed") permits the work to span multiple sessions and to take as long as it takes; it does not permit cutting WPs from scope. Deferrals are reserved for items already named as out-of-scope in `spec.md` § Out of Scope.

If a specific WP becomes blocked (e.g. WP08 awaiting operator ADR approval), the implement-review loop pauses that WP and continues unblocked WPs. The blocked WP resumes when the blocker resolves; the mission does not "ship without" the WP.

WP-level priority for sequencing (per `plan.md` § Phase 2 dependency graph):

1. **WP01** — mypy strict baseline (foundation).
2. **WP02** — independent; small; can run in parallel with WP01.
3. **WP04** — independent; regex hotspots; can run in parallel with WP01.
4. **WP03, WP05, WP06, WP08, WP09** — depend on WP01; run after it lands.
5. **WP07** — depends on WP04 + WP05 + WP06 (Sonar gate green precondition).
6. **WP10** — depends on WP01..WP09; consolidates and runs the post-merge mission-review.
