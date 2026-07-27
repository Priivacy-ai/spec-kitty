# Tasks — Charter Golden-Path E2E (Tranche 1)

| Field | Value |
|---|---|
| Mission slug | `charter-golden-path-e2e-tranche-1-01KQ806X` |
| Mission ID | `01KQ806XN4TTJRAQGZWVPQP7V7` |
| Mission type | `software-dev` |
| Branch (planning, base, target) | `test/charter-e2e-827-tranche-1` |
| Date | 2026-04-27 |
| Spec | [spec.md](./spec.md) |
| Plan | [plan.md](./plan.md) |
| Research | [research.md](./research.md) |
| Contract | [contracts/cli-flow-contract.md](./contracts/cli-flow-contract.md) |

## Overview

This mission's deliverable is a single product-repo, public-CLI E2E test (`tests/e2e/test_charter_epic_golden_path.py`) plus a small additive set of helpers in `tests/e2e/conftest.py`. The work splits cleanly along file boundaries:

- **WP01** owns `tests/e2e/conftest.py` and adds three additive helpers (a fresh-project fixture, a source-checkout pollution-guard pair, and a subprocess-failure diagnostic). It modifies nothing existing in conftest beyond its own additions.
- **WP02** owns `tests/e2e/test_charter_epic_golden_path.py` and implements the full golden-path test using WP01's helpers.

WP02 depends on WP01.

## Subtask Index

| ID | Description | WP | Parallel |
|---|---|---|---|
| T001 | Add `fresh_e2e_project` fixture to `tests/e2e/conftest.py` | WP01 | — | [D] |
| T002 | Add source-checkout pollution-guard helpers (`capture_source_pollution_baseline`, `assert_no_source_pollution`) to `tests/e2e/conftest.py` | WP01 | [D] |
| T003 | Add subprocess-failure diagnostic helper (`format_subprocess_failure`) to `tests/e2e/conftest.py` | WP01 | [D] |
| T004 | Scaffold `tests/e2e/test_charter_epic_golden_path.py` (module docstring, markers, baseline capture, fixture wiring) | WP02 | — | [D] |
| T005 | Implement Step 1 + Step 2 — project bootstrap (`git init` → `spec-kitty init`) and Charter governance flow (interview → generate → bundle validate → synthesize `--adapter fixture --dry-run` → synthesize `--adapter fixture` → status → lint) with all FR-009..FR-013 assertions | WP02 | — | [D] |
| T006 | Implement Step 3 — mission scaffolding (`agent mission create` → `setup-plan` → seed minimal `software-dev` mission → `finalize-tasks`) with FR-005 assertions | WP02 | — | [D] |
| T007 | Implement Step 4 — `spec-kitty next` issue + advance with paired-lifecycle-record assertions (FR-006, FR-014, FR-015, FR-016) | WP02 | — | [D] |
| T008 | Implement Step 5 + Step 6 — `retrospect summary --project <temp-project> --json` and final source-pollution-guard assertion (FR-017, FR-018), then run quickstart verification (ruff, mypy --strict, pytest) | WP02 | — | [D] |

`[P]` denotes a subtask that is internally parallel-safe with sibling subtasks in the same WP (different functions/concerns in the same file). Cross-WP parallelism is governed by `dependencies` and the lane allocator.

---

## Work Package WP01: E2E conftest helpers

**Dependencies**: None
**Requirement Refs**: FR-003, FR-017, FR-018, FR-019, FR-020, NFR-004
**Estimated prompt size**: ~280 lines
**Owned files**: `tests/e2e/conftest.py`
**Authoritative surface**: `tests/e2e/conftest.py`
**Execution mode**: `code_change`

### Goal

Add a fresh-project pytest fixture and two reusable diagnostic helpers to `tests/e2e/conftest.py`, with no changes to the existing `e2e_project` fixture or any other existing behaviour.

### Independent test (definition of done for WP01 in isolation)

After WP01:
- `python -c "from tests.e2e.conftest import fresh_e2e_project, capture_source_pollution_baseline, assert_no_source_pollution, format_subprocess_failure"` succeeds (or equivalent import-resolution test via pytest collection).
- `pytest --collect-only tests/e2e/` exits 0 and lists every previously-collected test plus collects `fresh_e2e_project` as a fixture.
- `ruff check tests/e2e/conftest.py` exits 0.
- `mypy --strict tests/e2e/conftest.py` exits 0.
- The existing `e2e_project` fixture and `tests/e2e/test_cli_smoke.py` continue to pass unchanged.

### Included subtasks

- [x] T001 Add `fresh_e2e_project` fixture (WP01)
- [x] T002 Add source-checkout pollution-guard helpers (WP01)
- [x] T003 Add subprocess-failure diagnostic helper (WP01)

### Implementation sketch

1. Append helpers to existing `tests/e2e/conftest.py`; do not delete or rewrite existing imports, fixtures, or constants.
2. `fresh_e2e_project` performs only public-CLI bootstrap: `git init -b main`, git config, `spec-kitty init . --ai codex --non-interactive`, initial commit. It does **not** copy `.kittify` from `REPO_ROOT`.
3. `capture_source_pollution_baseline(repo_root: Path)` returns a typed dataclass with both a `git status --short` snapshot AND a recursive path inventory of `kitty-specs/`, `.kittify/`, `.worktrees/`, `docs/`, plus `**/profile-invocations/` paths.
4. `assert_no_source_pollution(baseline, repo_root)` re-captures and compares both layers; on mismatch it raises `AssertionError` with a diff in the message.
5. `format_subprocess_failure(*, command, cwd, completed)` returns a multi-line string with `command`, `cwd`, `rc`, `stdout`, `stderr` for use in assertion messages.

### Risks / pitfalls

- Do not import any private helper from `specify_cli` (C-001/C-002).
- Keep helpers narrow; resist the urge to refactor the existing `e2e_project` fixture (C-003).
- Pollution-guard layer 2 must read paths **even when `.gitignore` masks them** — use `Path.rglob` rather than relying on `git status`.

### Reviewer guidance

- Confirm no existing fixture/test was modified.
- Confirm the fixture does not copy from `REPO_ROOT`.
- Confirm `mypy --strict` passes on the touched file.

---

## Work Package WP02: Charter golden-path E2E test

**Dependencies**: WP01
**Requirement Refs**: FR-001, FR-002, FR-004, FR-005, FR-006, FR-007, FR-008, FR-009, FR-010, FR-011, FR-012, FR-013, FR-014, FR-015, FR-016, FR-021, NFR-001, NFR-002, NFR-003, NFR-005, NFR-006
**Estimated prompt size**: ~520 lines
**Owned files**: `tests/e2e/test_charter_epic_golden_path.py`
**Authoritative surface**: `tests/e2e/test_charter_epic_golden_path.py`
**Execution mode**: `code_change`

### Goal

Implement the single end-to-end pytest test that drives the operator path through public CLI from a fresh project, asserts the JSON envelopes and lifecycle records per spec, and asserts the source checkout is byte-identical before and after.

### Independent test (definition of done for WP02)

After WP02:
- `uv run pytest tests/e2e/test_charter_epic_golden_path.py -q -s` exits 0.
- `git status --short` in `REPO_ROOT` is empty after the test run.
- `uv run ruff check tests/e2e/test_charter_epic_golden_path.py tests/e2e/conftest.py` exits 0.
- `uv run mypy --strict tests/e2e/test_charter_epic_golden_path.py` exits 0.
- `uv run pytest tests/e2e/ tests/next/ tests/integration/test_documentation_runtime_walk.py tests/integration/test_research_runtime_walk.py -q` shows no previously-green test newly failing.

### Included subtasks

- [x] T004 Scaffold the test module (WP02)
- [x] T005 Project bootstrap + Charter governance flow (WP02)
- [x] T006 Mission scaffolding (WP02)
- [x] T007 `next` issue + advance + lifecycle-record assertions (WP02)
- [x] T008 `retrospect summary` + final pollution-guard assertion + verification commands (WP02)

### Implementation sketch

1. **Scaffold** — module docstring (mirroring `test_cli_smoke.py:1-13` style), `from __future__ import annotations`, stdlib imports, pytest markers (`@pytest.mark.e2e` + `@pytest.mark.slow`), one test function or one-test test class, accept `fresh_e2e_project` and `run_cli` fixtures, capture pollution baseline as the first action, register a `try/finally` (or pytest finalizer) that asserts no pollution.
2. **Step 1+2** — public CLI bootstrap and Charter flow; use `--adapter fixture` for synthesize (R-002 deviation; inline comment cites spec FR-021); assert `.kittify/charter/charter.md` exists (FR-009), `bundle validate --json` reports success (FR-010), dry-run does NOT create `.kittify/doctrine/` (FR-011), real synthesize does (FR-012), `status` non-error and `lint` success-or-warning-only (FR-013).
3. **Step 3** — `agent mission create` (`--mission-type software-dev`) + `setup-plan` + inline-write minimal `spec.md/tasks.md/tasks/WP01-*.md/meta.json` patches (mirror `test_cli_smoke.py:132-214`) + git commit + `finalize-tasks`; assert `result == "success"` and finalized WP01 frontmatter contains `dependencies` field.
4. **Step 4** — `next --json` (query) returns parseable JSON with a `step_id` (or equivalent); inline-document the actual envelope shape on first observation. `next --result success --json` advances OR returns documented blocked envelope; both are acceptable per FR-015. Read JSONL files under `<temp>/.kittify/events/profile-invocations/` and assert paired `started`+`completed` records whose `action` equals the issued step id (FR-016). Capture and report the prompt-file path (FR-014) when present.
5. **Step 5+6** — `retrospect summary --project <temp> --json` returns parseable JSON; assert top-level dict (widen later if shape allows). Final pollution guard via `assert_no_source_pollution(baseline, REPO_ROOT)`.
6. After the function passes locally, run the three quickstart commands (ruff, mypy --strict, regression slice) and address any findings.

### Parallel opportunities

WP02's subtasks T005–T008 are sequential within the single test function (each step builds the temp project's state for the next). Internal parallelism within the WP is not meaningful.

### Risks / pitfalls

- `run_cli` has a 60 s per-call timeout; if a single step ever exceeds that, surface as a product finding (FR-021), do not silently extend the budget.
- The `synthesize --adapter fixture` deviation MUST be captured both in the test's inline comment AND in the PR description.
- The lifecycle-record action-name comparison (FR-016) is the single most regression-sensitive assertion; do not weaken it.
- The pollution guard runs in a `finally` (or finalizer) so it fires even when an earlier assertion fails — this is intentional; an earlier failure is no excuse for leaving the source checkout dirty.
- Do not import or reference any forbidden private helper (C-001, C-002). Resist any urge to monkeypatch (`pytest.MonkeyPatch`) — if the test seems to need a patch, that's a product finding.

### Reviewer guidance

- Confirm zero references to any forbidden symbol (grep the test file).
- Confirm `synthesize` calls use `--adapter fixture`.
- Confirm pollution guard runs in teardown/`finally`.
- Confirm assertion messages on failure carry command + cwd + rc + stdout + stderr per FR-019.
- Confirm the chosen mission is `software-dev` and is documented in a comment.

---

## Phase order

1. **Phase 1 (foundation)**: WP01 — additive helpers in conftest.
2. **Phase 2 (delivery)**: WP02 — the golden-path test.

WP02 depends on WP01.

## Parallelization summary

Two WPs, sequential dependency chain (WP01 → WP02). No cross-WP parallelism is possible for this tranche; this is by design — the test author needs the fixture to write the test, and trying to develop them in lockstep across two parallel sessions would create avoidable rework.

## MVP scope recommendation

WP01 + WP02 together constitute the MVP. Neither is independently shippable; the deliverable is the operator-path proof, which requires both pieces together.
