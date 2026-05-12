# Tasks: Review/Merge Gate Hardening (3.2.x)

**Mission**: `review-merge-gate-hardening-3-2-x-01KRC57C` | **Date**: 2026-05-12
**Branch**: `fix/3.2.x-review-merge-gate-hardening`
**Spec**: [`spec.md`](./spec.md) | **Plan**: [`plan.md`](./plan.md)

8 work packages, 43 subtasks. Target prompt size 200–500 lines per WP; sized to 4–7 subtasks each.

## Subtask Index (reference table; not a tracking surface)

| ID | Description | WP | Parallel |
|----|-------------|-----|----------|
| T001 | Audit and classify every `uv run pytest` reference (docs, templates, skill renderer) as release-gate or developer-convenience | WP01 | [P] |
| T002 | Replace release-gate references with `uv run python -m pytest`; leave dev convenience as-is | WP01 |  |
| T003 | Add preflight helper module asserting `pytest` is importable in project venv | WP01 | [P] |
| T004 | Wire preflight into gate invocation paths; emit `MISSION_REVIEW_TEST_EXTRA_MISSING` | WP01 |  |
| T005 | Regression test: subprocess fixture with venv lacking `test` extra; assert diagnostic fires | WP01 |  |
| T006 | Add or confirm `filelock` dependency in `pyproject.toml` | WP02 | [D] |
| T007 | Wrap `.pytest_cache/spec-kitty-test-venv` creation in conftest with file lock + 60s timeout | WP02 |  | [D] |
| T008 | On lock-acquire timeout, emit diagnostic naming the lock file path so operator can clean | WP02 | [D] |
| T009 | Regression test: parallel contract + architectural suites complete deterministically | WP02 |  | [D] |
| T010 | Document the fixture's concurrency contract in `tests/README.md` or similar | WP02 | [D] |
| T011 | Create `src/specify_cli/cli/commands/review/__init__.py` package; re-export `review_mission` public symbol | WP07 |  |
| T012 | Extract Step 1 (WP lane check) into `review/_lane_gate.py` | WP07 |  |
| T013 | Extract Step 2 (dead-code scan) into `review/_dead_code.py` | WP07 | [P] |
| T014 | Extract Step 3 (BLE001 audit) into `review/_ble001_audit.py` | WP07 | [P] |
| T015 | Extract Step 4 (report writer) into `review/_report.py` | WP07 | [P] |
| T016 | Delete the original `review.py`; verify existing review tests pass unchanged (NFR-005) | WP07 |  |
| T017 | Add `review/_diagnostics.py` with `MissionReviewDiagnostic` StrEnum; class docstring references `ERROR_CODES.md` | WP03 | [P] |
| T018 | Implement mode resolution + `--mode` flag in `review/_mode.py`; mode-mismatch diagnostic body with 3 remediation options (FR-005, FR-006, FR-023) | WP03 |  |
| T019 | Implement `review/_issue_matrix.py` validator: mandatory + named-optional columns, alias normalization, verdict allow-list, single-table rule, body-cell rules (FR-006, FR-028–FR-031) | WP03 |  |
| T020 | Extend `review/_report.py` for new frontmatter (mode, gates_recorded, issue_matrix_present, mission_exception_present); record `GateRecord` per gate (FR-007) | WP03 |  |
| T021 | Remediate the 6 existing `issue-matrix.md` files on `main`: auto-normalize trivial drift with provenance note; surface structural drift via diagnostic (FR-032) | WP03 |  |
| T022 | Author `src/specify_cli/cli/commands/review/ERROR_CODES.md` with one section per `MissionReviewDiagnostic` member (FR-033, NFR-008) | WP03 | [P] |
| T023 | Add glossary entries for: lightweight mode, post-merge mode, mode mismatch, issue-matrix schema drift (FR-034) | WP03 | [P] |
| T024 | Add `mission_number_baked: bool = False` to `MergeState`; ensure JSON serializer carries it | WP04 |  | [D] |
| T025 | Implement idempotency check in `_run_lane_based_merge`: read `meta.json.mission_number` before assignment; skip + set flag when equal (FR-010, FR-011) | WP04 |  | [D] |
| T026 | Update `merge --resume` flow to short-circuit when `mission_number_baked == True` | WP04 |  | [D] |
| T027 | Regression test simulating partial-merge resume scenario: assert no empty mission-number commit; flag flips to True (FR-012) | WP04 |  | [D] |
| T028 | Add `get_status_read_root()` helper preferring current worktree (FR-013) | WP05 | [P] |
| T029 | Audit every `get_main_repo_root()` call site in status-read code paths; tag read-only vs read-write; route read-only ones through the new helper | WP05 |  |
| T030 | Implement fail-loud path: if a status command cannot serve from a detached worktree, emit diagnostic naming the constraint (FR-014) | WP05 |  |
| T031 | Regression fixture with two worktrees + divergent `status.events.jsonl`; from each worktree, `agent tasks status --json` reflects its own events (FR-015) | WP05 |  |
| T032 | Promote `charset-normalizer` to direct dep in `pyproject.toml` pinned `>=3.4,<4`; verify `uv.lock` resolves cleanly | WP06 | [P] |
| T033 | Create `src/charter/_diagnostics.py` with `CharterEncodingDiagnostic` StrEnum; class docstring references `ERROR_CODES.md` | WP06 | [P] |
| T034 | Create `src/charter/_io.py` exposing `load_charter_file()` and `load_charter_bytes()`; detection order per contract; provenance write to dual-storage routing (FR-016, FR-017, FR-022) | WP06 |  |
| T035 | Retrofit 3 ingest sites: `compiler.py:594`, `sync.py:151`, `interview.py:283,398` (NFR-004 budget) | WP06 |  |
| T036 | Implement `--unsafe` bypass on the loader; record `bypass_used: true` in provenance (FR-021) | WP06 |  |
| T037 | Author `src/charter/ERROR_CODES.md` (FR-033, NFR-008); add glossary entries for encoding chokepoint, encoding provenance, unsafe bypass (FR-034) | WP06 | [P] |
| T038 | Regression tests covering cp1252 ingest, mixed-content AMBIGUOUS, `--unsafe` bypass, per-mission vs centralized routing | WP06 |  |
| T039 | Create `spec-kitty migrate charter-encoding` subcommand at `src/specify_cli/cli/commands/migrate/charter_encoding.py` | WP08 |  | [D] |
| T040 | Implement corpus scan: inventory `kitty-specs/*/charter/*` + `.kittify/charter/*` (extensions `.yaml`, `.md`, `.txt`); detect encoding via WP06 chokepoint per file | WP08 |  | [D] |
| T041 | Implement interactive mode (prompt before each non-UTF-8 file) + `--dry-run` and `--yes` flags | WP08 | [D] |
| T042 | Implement idempotency check: re-running on already-normalized corpus is a no-op (NFR-006) | WP08 |  | [D] |
| T043 | JSON-stable summary report (FR-027); regression test for legacy mission migration + idempotency check | WP08 |  | [D] |

---

## Work Packages

### WP01 — Hermetic mission-review gate invocation

**Goal**: Mission-review gate commands cannot fall through to a globally installed `pytest`. Replace bare `uv run pytest …` with hermetic invocation in release-gate contexts; add a preflight assertion that fails fast if the project `.venv` lacks the `test` extra.

**Priority**: P1 — blocks the cross-surface fixture harness (#992 Phase 0) and the fresh-clone smoke from epic #822's stable-release-gate.

**Independent test**: Fresh shallow clone with `uv sync` (no `--extra test`); run documented mission-review gate command; verify exit non-zero with `MISSION_REVIEW_TEST_EXTRA_MISSING` and never invokes `/opt/homebrew/bin/pytest` or any system pytest.

**Source bug**: #987

**Dependencies**: WP07 (preflight helper lives in the post-refactor review/ package neighborhood, but at a sibling path not owned by WP07 to avoid overlap)

**Estimated prompt size**: ~300 lines

#### Subtasks

- [x] T001 [P] Audit and classify every `uv run pytest` reference (docs, templates, skill renderer) as release-gate or developer-convenience (WP01)
- [x] T002 Replace release-gate references with `uv run python -m pytest`; leave dev convenience as-is (WP01)
- [x] T003 [P] Add preflight helper module asserting `pytest` is importable in project venv (WP01)
- [x] T004 Wire preflight into gate invocation paths; emit `MISSION_REVIEW_TEST_EXTRA_MISSING` (WP01)
- [x] T005 Regression test: subprocess fixture with venv lacking `test` extra; assert diagnostic fires (WP01)

#### Risks

- A doc/template change is missed → another agent reproduces the bug post-fix. Mitigated by T001's classification pass producing an audit table that becomes part of the PR.

#### Parallel opportunities

T001 and T003 in parallel (different files); T002 follows T001; T004 follows T003; T005 follows T002 and T004.

**Prompt**: [`tasks/WP01-hermetic-gate-invocation.md`](./tasks/WP01-hermetic-gate-invocation.md)

---

### WP02 — Concurrency-safe pytest-venv fixture

**Goal**: The shared `.pytest_cache/spec-kitty-test-venv` fixture creation is safe to run from parallel pytest invocations (contract + architectural gates). Add a file lock around creation; emit operator-actionable diagnostics on timeout.

**Priority**: P1 — release-gate parallelization is documented behavior; false hard-gate failures undermine release confidence.

**Independent test**: Concurrent execution of `tests/contract/` and `tests/architectural/` in two parallel pytest processes; both complete deterministically without `ensurepip` errors or partial-venv observations.

**Source bug**: #986

**Dependencies**: none

**Estimated prompt size**: ~280 lines

#### Subtasks

- [x] T006 [P] Add or confirm `filelock` dependency in `pyproject.toml` (WP02)
- [x] T007 Wrap `.pytest_cache/spec-kitty-test-venv` creation in conftest with file lock + 60s timeout (WP02)
- [x] T008 [P] On lock-acquire timeout, emit diagnostic naming the lock file path so operator can clean (WP02)
- [x] T009 Regression test: parallel contract + architectural suites complete deterministically (WP02)
- [x] T010 [P] Document the fixture's concurrency contract in `tests/README.md` or similar (WP02)

#### Risks

- Lock timeout too aggressive → flaky CI under load. Mitigated by 60s window and stale-lock detection. If 60s is insufficient on slow CI runners, tune up; do not remove the lock.

#### Parallel opportunities

T006, T008, T010 are parallelizable (different files / no shared state). T007 sequenced after T006. T009 sequenced after T007.

**Prompt**: [`tasks/WP02-pytest-venv-concurrency.md`](./tasks/WP02-pytest-venv-concurrency.md)

---

### WP07 — `review.py` hygiene refactor

**Goal**: Split `src/specify_cli/cli/commands/review.py` into a package of sibling files (`commands/review/` + `_lane_gate.py`, `_dead_code.py`, `_ble001_audit.py`, `_report.py`). **Mechanical extraction only** — no new abstractions, no domain modeling, no behavior change (NFR-005). Prerequisite to WP03 so the contract enforcement code lands into a clean structure.

**Priority**: P1 — sequencing prerequisite. Doing this after WP03 means rebuilding WP03 against a refactor.

**Independent test**: Run the existing review test suite against the post-WP07 codebase with no test modifications; every test passes (same inputs → same outputs → same exit codes → same artifacts).

**Source**: HiC directive 2026-05-12 (WP03 Q3 resolution)

**Dependencies**: none

**Estimated prompt size**: ~350 lines

#### Subtasks

- [x] T011 Create `src/specify_cli/cli/commands/review/__init__.py` package; re-export `review_mission` public symbol (WP07)
- [x] T012 Extract Step 1 (WP lane check) into `review/_lane_gate.py` (WP07)
- [x] T013 [P] Extract Step 2 (dead-code scan) into `review/_dead_code.py` (WP07)
- [x] T014 [P] Extract Step 3 (BLE001 audit) into `review/_ble001_audit.py` (WP07)
- [x] T015 [P] Extract Step 4 (report writer) into `review/_report.py` (WP07)
- [x] T016 Delete the original `review.py`; verify existing review tests pass unchanged (NFR-005) (WP07)

#### Risks

- Scope creep: an implementer is tempted to "improve while moving" — fix a small bug or rename a function. **NFR-005 forbids any behavior change.** Implementer agent must resist; any improvement opportunity is a follow-up ticket, not WP07 scope.

#### Parallel opportunities

T013, T014, T015 in parallel. T012 sequenced after T011 (Step 1 uses helpers exported from `__init__.py`). T016 last.

**Prompt**: [`tasks/WP07-review-py-refactor.md`](./tasks/WP07-review-py-refactor.md)

---

### WP03 — Mission-review mode contract, validator, and existing-matrix remediation

**Goal**: Add `--mode {lightweight|post-merge}` with auto-detect default; enforce the audit-derived `issue-matrix.md` schema; record Gate 1–4 with `command`/`exit_code`/`result`; remediate the 6 existing matrices on `main`. Ship JSON-stable diagnostics with remediation guidance.

**Priority**: P0 — primary release-blocker fix.

**Independent test**: (1) Post-merge mission lacking `issue-matrix.md` fails with `MISSION_REVIEW_ISSUE_MATRIX_MISSING`. (2) Lightweight invocation writes a report whose body explicitly says "Lightweight consistency check; not a release gate". (3) Mode-mismatch invocation fails with `MISSION_REVIEW_MODE_MISMATCH` and body lists three remediation options.

**Source bug**: #985 + HiC audit directive 2026-05-12

**Dependencies**: WP01 (hermetic gates), WP02 (parallel-safe fixtures), WP07 (refactored review/ package)

**Estimated prompt size**: ~480 lines

#### Subtasks

- [x] T017 [P] Add `review/_diagnostics.py` with `MissionReviewDiagnostic` StrEnum; class docstring references `ERROR_CODES.md` (WP03)
- [x] T018 Implement mode resolution + `--mode` flag in `review/_mode.py`; mode-mismatch diagnostic body with 3 remediation options (FR-005, FR-006, FR-023) (WP03)
- [x] T019 Implement `review/_issue_matrix.py` validator: mandatory + named-optional columns, alias normalization, verdict allow-list, single-table rule, body-cell rules (FR-006, FR-028–FR-031) (WP03)
- [x] T020 Extend `review/_report.py` for new frontmatter (mode, gates_recorded, issue_matrix_present, mission_exception_present); record `GateRecord` per gate (FR-007) (WP03)
- [x] T021 Remediate the 6 existing `issue-matrix.md` files on `main`: auto-normalize trivial drift with provenance note; surface structural drift via diagnostic (FR-032) (WP03)
- [x] T022 [P] Author `src/specify_cli/cli/commands/review/ERROR_CODES.md` with one section per `MissionReviewDiagnostic` member (FR-033, NFR-008) (WP03)
- [x] T023 [P] Add glossary entries for: lightweight mode, post-merge mode, mode mismatch, issue-matrix schema drift (FR-034) (WP03)

#### Risks

- The existing 6 matrices have varied shapes (see spec §Existing-mission audit findings). Auto-normalization MUST write a one-line provenance note inside the file before modifying any content; never silent rewrite. Implementer must inspect each file and decide per the contract.
- Diagnostic-code namespace drift: if the StrEnum and `ERROR_CODES.md` get out of sync, NFR-008 fires. T022 produces the doc and T024 (in tests) asserts the cross-reference holds.

#### Parallel opportunities

T017, T022, T023 in parallel (different files/concerns). T018 + T019 sequential within mode-then-validator chain. T020 after T017 (uses Diagnostic enum) and T019 (writes validator result). T021 last.

**Prompt**: [`tasks/WP03-mission-review-contract.md`](./tasks/WP03-mission-review-contract.md)

---

### WP04 — Idempotent mission-number assignment

**Goal**: Resume of a partial-merge after `mission_number` was committed must succeed without empty mission-number commits. Add `mission_number_baked` flag to merge-state; short-circuit assignment when already-equal.

**Priority**: P1 — recovery story for release-blocking missions.

**Independent test**: Simulate partial-merge (`mission_number=N` written, then merge fails); rerun `merge --resume`; verify no empty commit; assignment step skipped; flag is True.

**Source bug**: #983

**Dependencies**: none

**Estimated prompt size**: ~260 lines

#### Subtasks

- [x] T024 Add `mission_number_baked: bool = False` to `MergeState`; ensure JSON serializer carries it (WP04)
- [x] T025 Implement idempotency check in `_run_lane_based_merge`: read `meta.json.mission_number` before assignment; skip + set flag when equal (FR-010, FR-011) (WP04)
- [x] T026 Update `merge --resume` flow to short-circuit when `mission_number_baked == True` (WP04)
- [x] T027 Regression test simulating partial-merge resume scenario: assert no empty mission-number commit; flag flips to True (FR-012) (WP04)

#### Risks

- Subtle concurrency: the mission-number lock must still serialize concurrent merges. The idempotency check happens INSIDE the lock; do not move it outside.

#### Parallel opportunities

T024 first; T025 + T026 sequential; T027 last.

**Prompt**: [`tasks/WP04-mission-number-idempotency.md`](./tasks/WP04-mission-number-idempotency.md)

---

### WP05 — Worktree-aware status read resolution

**Goal**: `spec-kitty agent tasks status` from a detached worktree reads that worktree's `status.events.jsonl`, not the primary checkout's. Add `get_status_read_root()` helper; route read-only paths through it.

**Priority**: P1 — post-merge SHA verification is core to release-gate trust.

**Independent test**: Two-worktree fixture with divergent event logs; from each worktree, `agent tasks status --json` reflects its own events.

**Source bug**: #984

**Dependencies**: none

**Estimated prompt size**: ~270 lines

#### Subtasks

- [x] T028 [P] Add `get_status_read_root()` helper preferring current worktree (FR-013) (WP05)
- [x] T029 Audit every `get_main_repo_root()` call site in status-read code paths; tag read-only vs read-write; route read-only ones through the new helper (WP05)
- [x] T030 Implement fail-loud path: if a status command cannot serve from a detached worktree, emit diagnostic naming the constraint (FR-014) (WP05)
- [x] T031 Regression fixture with two worktrees + divergent `status.events.jsonl`; from each worktree, `agent tasks status --json` reflects its own events (FR-015) (WP05)

#### Risks

- Audit miss: a write path is mistakenly routed through the new helper. Mitigated by explicit tagging in T029 and code review for "any function that writes to status MUST keep main-repo-root resolution".

#### Parallel opportunities

T028 in parallel with audit prep; T029 sequenced after T028 (uses the helper); T030 + T031 sequential.

**Prompt**: [`tasks/WP05-status-read-worktree-resolution.md`](./tasks/WP05-status-read-worktree-resolution.md)

---

### WP06 — Charter encoding chokepoint

**Goal**: Single ingestion chokepoint at three boundaries (`compiler.py`, `sync.py`, `interview.py`) with `charset-normalizer`-backed detection, provenance recording in dual storage, `--unsafe` bypass with audit, and fail-loud on ambiguity. NFR-004 caps the module budget at 5.

**Priority**: P2 — addresses #644 within #822's narrowed-slice constraint.

**Independent test**: Ingest a cp1252-encoded charter; assert provenance recorded with `normalization_applied=True`; ingest a mixed-content file and assert `CHARTER_ENCODING_AMBIGUOUS`; same with `--unsafe` succeeds and records `bypass_used=true`.

**Source bug**: #644 (narrowed)

**Dependencies**: none

**Estimated prompt size**: ~450 lines

#### Subtasks

- [x] T032 [P] Promote `charset-normalizer` to direct dep in `pyproject.toml` pinned `>=3.4,<4`; verify `uv.lock` resolves cleanly (WP06)
- [x] T033 [P] Create `src/charter/_diagnostics.py` with `CharterEncodingDiagnostic` StrEnum; class docstring references `ERROR_CODES.md` (WP06)
- [x] T034 Create `src/charter/_io.py` exposing `load_charter_file()` and `load_charter_bytes()`; detection order per contract; provenance write to dual-storage routing (FR-016, FR-017, FR-022) (WP06)
- [x] T035 Retrofit 3 ingest sites: `compiler.py:594`, `sync.py:151`, `interview.py:283,398` (NFR-004 budget) (WP06)
- [x] T036 Implement `--unsafe` bypass on the loader; record `bypass_used: true` in provenance (FR-021) (WP06)
- [x] T037 [P] Author `src/charter/ERROR_CODES.md` (FR-033, NFR-008); add glossary entries for encoding chokepoint, encoding provenance, unsafe bypass (FR-034) (WP06)
- [x] T038 Regression tests covering cp1252 ingest, mixed-content AMBIGUOUS, `--unsafe` bypass, per-mission vs centralized routing (WP06)

#### Risks

- Scope creep: implementer notices the 5 deferred re-read sites also use `read_text(encoding="utf-8")` and "fixes" them as a courtesy. **NFR-004's >5-module guardrail explicitly forbids this.** Implementer must STOP and escalate if more than 5 modules would be touched.
- charset-normalizer detection on small files (< 100 bytes) may misclassify. Detection order checks BOM and strict UTF-8 first; only ambiguous content falls to charset-normalizer.

#### Parallel opportunities

T032, T033, T037 in parallel. T034 follows T032/T033 (uses both). T035 follows T034. T036 modifies T034's loader. T038 last.

**Prompt**: [`tasks/WP06-charter-encoding-chokepoint.md`](./tasks/WP06-charter-encoding-chokepoint.md)

---

### WP08 — Charter-content encoding migration flow

**Goal**: Scan every existing mission's charter content for non-UTF-8 encodings; normalize-or-fail-loud preemptively so WP06's chokepoint doesn't surface false regressions on legacy files. Idempotent (NFR-006); JSON-stable summary report.

**Priority**: P2 — operational hygiene; runs in CI to keep the chokepoint trustworthy.

**Independent test**: Synthesize a legacy mission directory with a cp1252 charter file; run `spec-kitty migrate charter-encoding`; verify the file is normalized with provenance and a second invocation is a no-op.

**Source**: HiC directive 2026-05-12 (WP06 Q2 resolution)

**Dependencies**: WP06 (uses the chokepoint's detection + provenance)

**Estimated prompt size**: ~320 lines

#### Subtasks

- [x] T039 Create `spec-kitty migrate charter-encoding` subcommand at `src/specify_cli/cli/commands/migrate/charter_encoding.py` (WP08)
- [x] T040 Implement corpus scan: inventory `kitty-specs/*/charter/*` + `.kittify/charter/*` (extensions `.yaml`, `.md`, `.txt`); detect encoding via WP06 chokepoint per file (WP08)
- [x] T041 [P] Implement interactive mode (prompt before each non-UTF-8 file) + `--dry-run` and `--yes` flags (WP08)
- [x] T042 Implement idempotency check: re-running on already-normalized corpus is a no-op (NFR-006) (WP08)
- [x] T043 JSON-stable summary report (FR-027); regression test for legacy mission migration + idempotency check (WP08)

#### Risks

- Operator runs `--yes` mode in CI on a corpus that contains a genuinely ambiguous file → CI fails. Acceptable: CI should fail loudly when ambiguity exists, surfacing the file for human repair. Do not auto-bypass ambiguous content in `--yes` mode.

#### Parallel opportunities

T041 in parallel with T040 (different flag/CLI surface vs scan logic). T042 follows T040. T043 last.

**Prompt**: [`tasks/WP08-charter-encoding-migration.md`](./tasks/WP08-charter-encoding-migration.md)

---

## Dependency Graph

```
WP07 (review.py refactor) ──┐
                            ├─► WP03 (mode contract + validator + remediation)
WP01 (hermetic gates) ──────┤
WP02 (pytest-venv lock) ────┘

WP04 (mission-number idempotency)   independent
WP05 (status read worktree)         independent

WP06 (encoding chokepoint) ──► WP08 (charter-content migration)
```

## MVP Scope

WP01 + WP02 + WP07 + WP03 = the release-gate apparatus (the primary release-blocker pattern).
WP04 + WP05 = recovery and verification correctness.
WP06 + WP08 = the narrowed encoding hygiene slice.

Recommended sprint sequencing:

1. Sprint A (parallel): WP07, WP02, WP04, WP05, WP06.
2. Sprint B (after WP07/WP01/WP02 finish): WP03.
3. Sprint C (after WP06 finishes): WP08.
4. WP01 starts when WP07's package layout exists; can run in parallel with WP02 since it owns different files.

## Acceptance for the Mission

- All 43 subtasks marked complete.
- All 34 FRs (FR-001 through FR-034) have at least one passing regression test.
- All 8 NFRs hold.
- The eat-our-own-dogfood smoke (NFR-003): this mission's own `mission-review-report.md` is generated by the new WP03 post-merge mode and passes its own contract.
- Decision verifier reports clean.
- Mission-review hard gates 1–4 pass on `main` after the mission is merged.

## Next

Run `/spec-kitty.implement` (or the `spec-kitty-implement-review` skill) when ready to dispatch lane agents.
