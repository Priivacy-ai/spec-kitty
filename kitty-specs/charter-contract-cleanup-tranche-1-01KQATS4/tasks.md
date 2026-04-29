# Tasks: Charter Contract Cleanup Tranche 1

**Mission:** `charter-contract-cleanup-tranche-1-01KQATS4` (mid8 `01KQATS4`)
**Spec:** [spec.md](./spec.md) · **Plan:** [plan.md](./plan.md) · **Research:** [research.md](./research.md) · **Data model:** [data-model.md](./data-model.md) · **Contracts:** [contracts/](./contracts/) · **Quickstart:** [quickstart.md](./quickstart.md)
**Branch contract:** planning/base = `main` · merge target = `main`
**Date:** 2026-04-28

---

## Subtask Index (reference table — not a tracking surface)

| Task | Description | Work Package | Parallel |
|------|-------------|--------------|----------|
| T001 | Run regression-guard test suite against feature branch and capture per-test evidence | WP01 | | [D] |
| T002 | Inspect `runtime_bridge.py` and `retrospective/schema.py` invariants by reading current code | WP01 | [D] |
| T003 | Inspect golden-path helpers (`_parse_first_json_object`, `_run_next_and_assert_lifecycle`) and the synthesizer-call path in the E2E | WP01 | [D] |
| T004 | Author `verification-evidence.md` with results, FR-009/FR-010 disposition, and any escalation flags | WP01 | | [D] |
| T005 | Refactor `charter synthesize --json` branch in `src/specify_cli/cli/commands/charter.py` to keep stdout strict-JSON, emit contracted envelope fields, source `written_artifacts` from staged entries, drive dry-run from same source, and eliminate user-visible `PROJECT_000` | WP02 | |
| T006 | Extend `src/charter/synthesizer/write_pipeline.py` staged-artifact return shape **only if** WP01/T005 inspection shows the existing return is insufficient | WP02 | |
| T007 | Add/harden regression test in `tests/integration/test_json_envelope_strict.py` proving `json.loads(stdout)` succeeds when evidence warnings exist | WP02 | [P] |
| T008 | Add/harden assertions in `tests/agent/cli/commands/test_charter_synthesize_cli.py` covering the four contracted envelope fields | WP02 | [P] |
| T009 | Add/harden assertions in `tests/integration/test_charter_synthesize_fresh.py` covering envelope shape on fresh-project seed | WP02 | [P] |
| T010 | Add new `tests/charter/synthesizer/test_synthesize_path_parity.py` proving dry-run/non-dry-run path parity for non-`PROJECT_000` provenance | WP02 | [P] |
| T011 | Run `PROJECT_000` user-visibility sweep (grep + assertion) and `mypy --strict` on every modified runtime file | WP02 | |
| T012 | Update issued-action assertion in `tests/e2e/test_charter_epic_golden_path.py` to require resolvable `prompt_file` (or documented public equivalent) | WP03 | |
| T013 | Update blocked-decision assertion in the same file to require non-empty `reason` and not require a prompt file | WP03 | |
| T014 | Run the golden-path E2E end-to-end against the real synthesizer and confirm both new assertions pass and existing ones do not regress | WP03 | |
| T015 | Confirm verify-only invariants on `_parse_first_json_object` and `_run_next_and_assert_lifecycle` still hold after the assertion changes | WP03 | |
| T016 | Modify the `e2e-cross-cutting` job in `.github/workflows/ci-quality.yml`: install `pip install -e .[test,lint]` instead of `pip install -e .[test]` | WP04 | |
| T017 | Verify locally that the modified install line produces a functioning `python -m mypy` and that `tests/cross_cutting/test_mypy_strict_mission_step_contracts.py` passes | WP04 | |
| T018 | Confirm no other CI job in the workflow regresses (read job graph, identify any indirect dependency on the `[test]`-only install) | WP04 | |
| T019 | Run the five-command local test gate (NFR-001) on the feature branch and capture terminal evidence | WP05 | |
| T020 | Diagnose the `Protect Main Branch` failure observed on release PR #864 — fix here if reproducible from product code, otherwise file/update a GitHub issue | WP05 | |
| T021 | Open the PR `fix/charter-827-contract-cleanup` → `Priivacy-ai/spec-kitty:main` with the test-gate evidence in the description | WP05 | |
| T022 | After merge, apply post-merge GH issue hygiene: comment/close `#844`, comment on `#827`, update `#848` | WP05 | |
| T023 | Update `release-evidence.md` with the final CI-green snapshot, list of issues touched, and pointer to the merge commit | WP05 | |

---

## Work Package Roll-up

### WP01 — Regression-guard verification (verify-only baseline)

- **Goal:** Establish that the FR-009/FR-010 verify-only items are intact on the feature branch *before* any related code is changed elsewhere in this mission. If a regression is observed, escalate it as new in-scope work per C-003.
- **Priority:** Foundation (must run before WP02/WP03/WP04 for full confidence; technically independent in terms of file ownership, so soft-sequential).
- **Estimated prompt size:** ~280 lines.
- **Success criteria:**
  - All five regression-guard test files pass on the feature branch with their existing assertions.
  - Source-level invariants documented in spec FR-009/FR-010 are visible in current code (no silent regression).
  - `verification-evidence.md` exists at `kitty-specs/charter-contract-cleanup-tranche-1-01KQATS4/research/verification-evidence.md` and lists per-test results plus a Go/No-Go statement.
- **Independent test:** `uv run pytest tests/next/test_retrospective_terminus_wiring.py tests/retrospective/test_gate_decision.py tests/doctrine_synthesizer/test_path_traversal_rejection.py -q` exits 0.
- **Included subtasks:**
  - [x] T001 Run regression-guard test suite against feature branch and capture per-test evidence (WP01)
  - [x] T002 Inspect `runtime_bridge.py` and `retrospective/schema.py` invariants by reading current code (WP01)
  - [x] T003 Inspect golden-path helpers and the synthesizer-call path in the E2E (WP01)
  - [x] T004 Author `verification-evidence.md` with results, FR-009/FR-010 disposition, and any escalation flags (WP01)
- **Implementation sketch:** read code → run tests → write evidence file. No production-code edits unless evidence shows a regression.
- **Parallel opportunities:** T002 and T003 can run in parallel after T001.
- **Dependencies:** none.
- **Risks:** A real regression in the verify-only set would expand mission scope. Mitigation: spec C-003 already authorises absorbing it.

### WP02 — Charter synthesize CLI contract overhaul (FR-001..FR-005)

- **Goal:** Make `spec-kitty charter synthesize ... --json` emit a strict, contracted JSON envelope with real staged-artifact provenance, byte-equal dry-run/non-dry-run paths, and zero user-visible `PROJECT_000`.
- **Priority:** P0 — the largest user-visible contract gap.
- **Estimated prompt size:** ~560 lines.
- **Success criteria:**
  - `json.loads(stdout)` over `charter synthesize --adapter fixture --json` stdout succeeds with warnings present.
  - Envelope contains `result`, `adapter` (with `id` and `version`), `written_artifacts`, `warnings`.
  - `written_artifacts` entries are sourced from typed staged-artifact data; `path` is byte-equal between dry-run and real run.
  - No user-visible output contains `PROJECT_000`.
  - `mypy --strict` passes on every modified runtime file.
- **Independent test:** `uv run pytest tests/agent/cli/commands/test_charter_synthesize_cli.py tests/integration/test_json_envelope_strict.py tests/integration/test_charter_synthesize_fresh.py tests/charter/synthesizer/test_synthesize_path_parity.py -q` exits 0.
- **Included subtasks:**
  - [ ] T005 Refactor `charter synthesize --json` branch (WP02)
  - [ ] T006 Extend `write_pipeline.py` staged-artifact return shape only if needed (WP02)
  - [ ] T007 Add/harden `test_json_envelope_strict.py` regression (WP02)
  - [ ] T008 Add/harden `test_charter_synthesize_cli.py` envelope assertions (WP02)
  - [ ] T009 Add/harden `test_charter_synthesize_fresh.py` envelope assertions (WP02)
  - [ ] T010 Add new `test_synthesize_path_parity.py` for FR-004 (WP02)
  - [ ] T011 `PROJECT_000` sweep + `mypy --strict` on touched files (WP02)
- **Implementation sketch:** inspect the synthesize JSON branch and the write pipeline's staged-artifact return → introduce a single envelope-builder function that consumes typed staged entries → switch dry-run to consume the same source → route warnings into the envelope (not stdout) → add tests pinned to the contract → mypy + grep sweep last.
- **Parallel opportunities:** T007/T008/T009/T010 can be drafted in parallel after T005.
- **Dependencies:** WP01 (baseline established).
- **Risks:** T006 expands scope if `write_pipeline.py`'s return shape is too thin. Mitigation: T005's inspection determines whether T006 is needed; if it is, the change is additive (new field on existing dataclass / typed entry), single-file blast radius.

### WP03 — Golden-path E2E prompt-file assertion (FR-006, FR-007 — closes #844)

- **Goal:** Make `tests/e2e/test_charter_epic_golden_path.py` fail loudly when an issued action lacks a resolvable prompt file, and pass blocked decisions that carry a non-empty `reason` instead.
- **Priority:** P0 for #844 closure.
- **Estimated prompt size:** ~330 lines.
- **Success criteria:**
  - Issued-action envelopes (`kind == "step"`) without a non-null/non-empty/resolvable prompt path cause the test to fail with a clear message.
  - Blocked decisions without a non-empty `reason` cause the test to fail.
  - Existing assertions about other envelope kinds and the lifecycle trail continue to pass.
- **Independent test:** `uv run pytest tests/e2e/test_charter_epic_golden_path.py -q` exits 0 on the feature branch.
- **Included subtasks:**
  - [ ] T012 Update issued-action assertion to require resolvable `prompt_file` (WP03)
  - [ ] T013 Update blocked-decision assertion to require non-empty `reason` (WP03)
  - [ ] T014 Run the golden-path E2E and confirm both new assertions pass and existing ones do not regress (WP03)
  - [ ] T015 Confirm verify-only invariants on `_parse_first_json_object` and `_run_next_and_assert_lifecycle` still hold (WP03)
- **Implementation sketch:** locate the per-envelope loop → branch on envelope kind → add the two new assertions → run the test with verbose output to confirm legitimate envelopes are not falsely rejected → re-read helper functions for verify-only confirmation.
- **Parallel opportunities:** runs in parallel with WP02 and WP04.
- **Dependencies:** WP01.
- **Risks:** the assertion fires false-negative on a legitimate runtime envelope shape. Mitigation: `contracts/golden-path-envelope-assertions.md` permits multiplexing across the documented public field names, and T014 verifies against the real synthesizer.

### WP04 — CI `e2e-cross-cutting` mypy availability (FR-008)

- **Goal:** Make the `e2e-cross-cutting` CI job actually exercise `tests/cross_cutting/test_mypy_strict_mission_step_contracts.py` instead of failing on `python -m mypy: not found`.
- **Priority:** P0 for CI hygiene.
- **Estimated prompt size:** ~210 lines.
- **Success criteria:**
  - `e2e-cross-cutting` job installs the `lint` extra alongside `test`.
  - The strict-typing executor test runs and passes in that job.
  - No other CI job regresses.
- **Independent test:** push to a feature branch and observe `gh pr checks` — `e2e-cross-cutting` exits green; lint-feedback job (if present) is unaffected.
- **Included subtasks:**
  - [ ] T016 Modify the `e2e-cross-cutting` install step to add the `lint` extra (WP04)
  - [ ] T017 Verify locally that the modified install line produces a functioning `python -m mypy` and the test passes (WP04)
  - [ ] T018 Confirm no other CI job in the workflow regresses (WP04)
- **Implementation sketch:** edit one line in `.github/workflows/ci-quality.yml` → reproduce the install locally to confirm `mypy` is on PATH and the test passes → grep the workflow for any other job that might inadvertently rely on the `[test]`-only state.
- **Parallel opportunities:** runs in parallel with WP02 and WP03.
- **Dependencies:** WP01.
- **Risks:** the change brings `bandit`, `pip-audit`, `cyclonedx-bom` into the job environment. They are not invoked by tests in `e2e-cross-cutting`, so they are dormant. Documented in T018's confirmation.

### WP05 — Local test gate + PR + GH issue hygiene (FR-011, FR-012, FR-013)

- **Goal:** Land the PR. Run the NFR-001 test gate, dispose of the Protect-Main-Branch finding, open the PR, and after merge apply issue hygiene to `#844`, `#827`, `#848`.
- **Priority:** Final phase — gates the merge.
- **Estimated prompt size:** ~410 lines.
- **Success criteria:**
  - All five NFR-001 commands exit 0 on the feature branch.
  - `Protect Main Branch` is fixed in this PR or filed/updated as a separate issue with rationale.
  - PR `fix/charter-827-contract-cleanup` → `Priivacy-ai/spec-kitty:main` is open with evidence in the description.
  - After merge, GH issues `#844`, `#827`, `#848` carry post-merge comments per spec FR-011 / C-006.
  - `release-evidence.md` exists at `kitty-specs/charter-contract-cleanup-tranche-1-01KQATS4/research/release-evidence.md` and captures the final state.
- **Independent test:** `gh pr checks --watch` shows all required CI green; the merge commit hash matches `release-evidence.md`.
- **Included subtasks:**
  - [ ] T019 Run the five-command local test gate (WP05)
  - [ ] T020 Diagnose the `Protect Main Branch` failure (fix or file issue) (WP05)
  - [ ] T021 Open the PR with the test-gate evidence in the description (WP05)
  - [ ] T022 Apply post-merge GH issue hygiene: `#844`, `#827`, `#848` (WP05)
  - [ ] T023 Update `release-evidence.md` with the final CI-green snapshot (WP05)
- **Implementation sketch:** run the five-command gate locally → diagnose Protect-Main-Branch with `gh run view` and source inspection → push branch and open PR → monitor checks → merge once green → run issue-hygiene `gh` commands (with `unset GITHUB_TOKEN` per CLAUDE.md) → write evidence file.
- **Parallel opportunities:** T019 can start as soon as WP02/WP03/WP04 are complete; T022 only after merge.
- **Dependencies:** WP01, WP02, WP03, WP04.
- **Risks:** PR fails an unexpected CI check. Mitigation: T019 catches local-gate failures pre-push; CI failures get treated case-by-case (real regression → fix in this PR; release-process artefact → issue per FR-013/R-008).

---

## Dependency DAG

```
WP01 ─┬─→ WP02 ─┐
      ├─→ WP03 ─┼─→ WP05
      └─→ WP04 ─┘
```

WP02, WP03, WP04 are file-disjoint and can run in parallel after WP01 establishes baseline. WP05 gates the final landing and post-merge hygiene.

## Parallelisation Highlights

- WP02, WP03, WP04 share no `owned_files` and can be implemented concurrently.
- Within WP02, the new/hardened tests (T007/T008/T009/T010) can be drafted in parallel after the refactor in T005 settles the contract.
- WP01's source inspections (T002, T003) can run in parallel after the test gate in T001 establishes the baseline.

## Out of Scope (mission-level constraint, repeated for clarity)

- External end-to-end canaries in `spec-kitty-end-to-end-testing` (`#827` Tranche 3).
- Plain-English acceptance scenarios in `spec-kitty-plain-english-tests` (`#827` Tranche 3).
- End-user documentation parity for the Charter epic (`#828`).
- Phase 7 schema versioning + provenance hardening (`#469`).

## MVP Scope Recommendation

**WP01 → WP02 → WP05** is the smallest path to value if the mission ever needs to be split. WP03 and WP04 are non-negotiable for closing #844 and the CI hygiene gap respectively, so the realistic MVP is the full 5-WP set.
