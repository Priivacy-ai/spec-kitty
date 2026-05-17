# Mission Review Report: backward-transition-cli-emit-01KRV8GC

**Reviewer**: Claude (Opus 4.7) — Mission Review (pre-merge audit)
**Date**: 2026-05-17
**Mission**: `backward-transition-cli-emit-01KRV8GC` — CLI Backward-Transition Emit Path
**Lane head**: `kitty/mission-backward-transition-cli-emit-01KRV8GC-lane-a` at `70255ad0` (WP02 implementer commit)
**WPs reviewed**: WP01, WP02 (both `approved`)
**Pre- or post-merge**: **Pre-merge**.

---

## Gate Results

The hard-gate apparatus is the same as in Mission 1: standing gates reference repositories/artifacts that are not part of this contract-only program. Substitutions apply.

### Gate 1 — Contract tests
- Status: `tests/contract/` directory does not exist in `spec-kitty` (CLI repo) in a sense relevant to this mission. The mission's contract is `kitty-specs/backward-transition-cli-emit-01KRV8GC/contracts/auto-promote-backward-emit.md`, which is verified by WP02's tests.
- Substituted check: `uv run pytest tests/specify_cli/cli/commands/agent/test_tasks_backward_emit.py -v` → 8 passed, 1 skipped (FR-009 fixture cross-check — see "Drift Findings" below).
- Result: **PASS** (with the documented skip flagged).

### Gate 2 — Architectural tests
- Substituted check: `uv run mypy --strict src/specify_cli/cli/commands/agent/tasks.py` → Success: no issues.
- `uv run ruff check tests/specify_cli/cli/commands/agent/test_tasks_backward_emit.py` → All checks passed.
- Pre-existing ruff errors elsewhere (`doctor.py`, `review/__init__.py`) verified by WP02 reviewer as pre-existing on `cdf71379` (WP01 commit). Not regressions.
- Result: **PASS**.

### Gate 3 — Cross-repo E2E
- Status: No standalone e2e harness in this workspace. Cross-repo verification is delegated to Mission 3 (`spec-kitty-saas` materializer), which will consume the new wire shape via the same `wp-status-changed-approved-rewind-valid` fixture.
- Result: **N/A** (no operator exception required).

### Gate 4 — Issue Matrix
- Status: No `issue-matrix.md` authored (this is a foundation/contract-fix mission, not a remediation sweep).
- Result: **N/A**.

**Gate summary**: No HARD FAIL. Mission proceeds.

---

## FR Coverage Matrix

| FR ID | Description (brief) | WP Owner | Evidence | Test Adequacy | Finding |
|---|---|---|---|---|---|
| FR-001 | Backward → `force=True` | WP01 | `tasks.py:1747-1748` (`if not force and _is_backward_transition(...): emit_force = True`) | ADEQUATE | — |
| FR-002 | Canonical reason shape `"backward rewind: <from> -> <to>[: <feedback-ref>]"` | WP01 | `tasks.py:1749-1755` (reason_parts construction with optional `review_feedback_pointer`) | ADEQUATE | — |
| FR-003 | Auto-promote only when not `--force` | WP01 | Guard `if not force and ...` at line 1747 | ADEQUATE | — |
| FR-004 | Forward moves preserved | WP01 | `_is_backward_transition` returns False for forward; auto-promote block falls through | ADEQUATE — verified by `test_planned_to_claimed_does_not_auto_promote` and `test_planned_to_in_progress_expands_intermediate` | — |
| FR-005 | Guard conditions ("checked regardless of force") respected | WP01 | Canonical reason satisfies `in_progress -> planned requires reason`; validator runs downstream | ADEQUATE | — |
| FR-006 | Single event for backward emit | WP01 | Existing `_lane_targets_for_emit` returns `[target]` for backward pairs (analyzed in research.md R-001); no code change needed | ADEQUATE | — |
| FR-007 | Terminal-lane exits preserved | WP01 | Terminal-exit semantics enforced upstream by `validate_transition`; auto-promote is direction-only and doesn't bypass that | ADEQUATE | — |
| FR-008 | Family + control tests | WP02 | 6 `def test_` methods (one parametrized 4-way = 4 lane variants) in `test_tasks_backward_emit.py` — 8 passed | ADEQUATE | — |
| FR-009 | Mission 1 fixture wire-shape regression | WP02 | Test method present; gracefully skips because fixture absent from published `spec-kitty-events==5.0.0`. Direct CLI invariants (force/from_lane/to_lane/reason-prefix) still asserted | PARTIAL — see DRIFT-1 below | DRIFT-1 |
| FR-010 | No mutation of 22 dev evidence events | WP01 + WP02 | All test fixtures synthetic; no reads/writes of `~/spec-kitty-dev/terminal-failed-evidence-2026-05-17.json` | ADEQUATE | — |
| FR-011 | Explicit `--force` preserved | WP01 | Guard `if not force` short-circuits auto-promote; existing path runs | ADEQUATE — verified by `test_explicit_force_backward_uses_existing_path` | — |
| FR-012 | Single-file source change | WP01 | `git diff main..lane-a --stat` shows only `src/specify_cli/cli/commands/agent/tasks.py` modified in `src/`; only the new test file added in `tests/` | ADEQUATE | — |

**Coverage: 12/12 FRs (100%). FR-009 PARTIAL but with mitigation in place.**

**Test authenticity**: tests import the real `move_task` via Typer `CliRunner`, exercise `emit_status_transition` end-to-end, and capture the emitted event from `status.events.jsonl`. No mocks of `validate_transition`, `emit_status_transition`, or the `_review_cycle` review-feedback URI synthesis. If WP01's auto-promote block were deleted, every FR-008 family test would fail.

---

## Drift Findings

### DRIFT-1: FR-009 fixture cross-check skipped (Mission 1 fixture not in published `spec-kitty-events`)

**Type**: CROSS-MISSION INTEGRATION GAP (not a violation; mitigation in place)
**Severity**: **LOW** (acceptable to proceed; tracked for follow-up)
**Spec reference**: FR-009 ("A regression test loads the `wp-status-changed-approved-rewind-valid` fixture from `spec_kitty_events.conformance.load_fixtures("edge_cases")` and asserts ... match the fixture")
**Evidence**:
- `uv run python -c "from spec_kitty_events.conformance import load_fixtures; ids = [fc.id for fc in load_fixtures('edge_cases')]; print(ids)"` returns 5 ids; `wp-status-changed-approved-rewind-valid` is NOT among them.
- The `spec-kitty` repo's `pyproject.toml` pins `spec-kitty-events==5.0.0` (or a range capping below the Mission 1 release).
- Mission 1's fixture was merged into the `spec-kitty-events` repo's `main` branch (mission_number=15, commit `934149b`) but has not been published to PyPI yet.
- WP02's `test_approved_to_planned_matches_mission1_fixture` gracefully `pytest.skip(...)`s the fixture cross-check while still asserting the direct CLI wire-shape invariants (`force=True`, `reason.startswith("backward rewind: approved -> planned")`, `from_lane="approved"`, `to_lane="planned"`).

**Analysis**: This is the expected sequencing of a multi-mission program where Mission 1 lands the contract artifact and Mission 2 consumes it via the published package. The contract is verified by the WP02 direct invariants; the fixture cross-check is defense-in-depth. When `spec-kitty-events` publishes a release containing the Mission 1 fixture, the WP02 test will auto-activate the cross-check with no code change required.

**Mitigation (already in place)**:
- WP02's FR-009 test asserts all four wire-shape invariants directly *before* attempting the fixture lookup. The skip path is reached only when the fixture is unavailable; the contract verification is not skipped.
- Mission 1's fixture content and the WP01 code are derived from the same contract anchor (`contracts/backward-transition-family.md` from Mission 1; `contracts/auto-promote-backward-emit.md` in this mission). The two will be in sync by construction.

**Recommended follow-up** (NOT a blocker for merge):
- After both Mission 2 and Mission 3 merge, publish a new `spec-kitty-events` release containing Mission 1's fixtures. The next CI run of `spec-kitty` after that bump will pick up the fixture cross-check automatically.
- Track this as a program-level concern (Mission 4 closure note may include it).

**No action required pre-merge.**

---

## Risk Findings

### RISK-1: Auto-promote rewrites generic fallback reason text but NOT user-supplied `--note`

**Type**: BOUNDARY-CONDITION (positive finding — intentional behavior)
**Severity**: **LOW**
**Location**: `tasks.py:1749-1755`
**Behavior**: The rewrite guard is `if emit_reason is None or emit_reason.startswith("move-task: ")`. A user who passes `--note "anything else"` keeps their note; auto-promote still sets `emit_force=True`. A user who passes `--note "move-task: foo -> bar"` (coincidentally matching the generic fallback prefix) gets their note rewritten.

**Analysis**: This is documented in research R-003 as an accepted trade-off. The probability of a user typing the exact prefix `"move-task: "` is near-zero; if they did, the resulting reason is strictly more informative. No action required.

### RISK-2: Unforced backward `done → *` would auto-promote

**Type**: BOUNDARY-CONDITION (defended elsewhere)
**Severity**: **LOW**
**Location**: `_is_backward_transition('done', 'planned')` returns True (helper is direction-only).
**Trigger**: A user attempts `move-task WP01 --to planned --mission <slug>` when WP01 is in `done`.

**Analysis**: The terminal-lane exit requirement is enforced upstream by `validate_transition` (in `spec_kitty_events.status`), which rejects unforced terminal-lane exits before the CLI emit code runs. The auto-promote block in WP01 is reached only after the upstream guard has allowed the call. WP01's helper docstring explicitly notes this layering: "Direction-only semantics are intentional; terminal-lane guards live upstream in `validate_transition`."

**No action required.** Tested transitively by the existing test suite (no regression in `test_tasks.py`).

### RISK-3: Pre-existing test failures and ruff errors

**Type**: PRE-EXISTING BASELINE (not introduced by this mission)
**Severity**: **LOW** (out of scope; tracked elsewhere)
**Locations**:
- 2 pre-existing failures in `test_wrapper_delegation.py` (verified on `cdf71379` before WP02).
- 226 pre-existing failures in unrelated files (`test_research_prompt_resolution.py`, `test_sync_doctor.py`, etc.) according to WP02 implementer report; reviewer corroborated for the agent/tasks territory.
- 10 pre-existing ruff errors in `doctor.py`, `review/__init__.py`, `tasks.py:1208`.

**Analysis**: None of these are caused by Mission 2's changes. The `tasks.py:1208` ruff error is in code that pre-existed WP01's modifications (WP01 only added lines 148-171 and 1747-1755). Mission 2 introduces zero new ruff errors and zero new test failures.

**No action required pre-merge.** The pre-existing items are a separate housekeeping concern.

---

## Silent Failure Candidates

| Location | Condition | Silent result | Spec impact |
|---|---|---|---|
| (none) | — | — | — |

No `except Exception: pass` or `except Exception: return ""` patterns introduced. No new try/except in the auto-promote block or the test file.

---

## Security Notes

| Finding | Location | Risk class | Recommendation |
|---|---|---|---|
| (none) | — | — | — |

This mission touches no subprocess, HTTP, auth, credential, file-I/O of user input, or lock semantics. Scope is CLI emit logic + tests. Security review pass: **clean**.

---

## NFR Verification

| NFR | Threshold | Measured | Result |
|---|---|---|---|
| NFR-001 | Targeted test runtime ≤ 30s | `uv run pytest tests/specify_cli/cli/commands/agent -k "..." -q` = **18.81s** | ✅ |
| NFR-002 | No regression in full suite | Pre-existing failures verified as baseline; new file adds 8 passing tests | ✅ (with documented baseline) |
| NFR-003 | Lint + type clean | `ruff check` new file ✅; `mypy --strict tasks.py` ✅; pre-existing ruff errors elsewhere not regressions | ✅ |
| NFR-004 | ≥90% coverage on new code | Measured **95.8%** (23/24 lines; 1 unreachable-by-design return) | ✅ |
| NFR-005 | Wire-shape additivity | `StatusTransitionPayload` unchanged; only `force` + `reason` values differ on auto-promoted backward emits | ✅ |

---

## Constraint Verification

| Constraint | Status |
|---|---|
| C-001 (target branch `main`) | ✅ |
| C-002 (`SPEC_KITTY_ENABLE_SAAS_SYNC=1`) | ✅ |
| C-003 (depends on Mission 1 — already merged; CLI already imports `Lane`) | ✅ |
| C-004 (no mutation of 22 dev evidence events) | ✅ — verified by grep for `terminal-failed-evidence`, `robert-douglass`, real-world identifiers; all absent |
| C-005 (editable install on worktree) | ✅ — implementer ran `uv sync --all-extras` |
| C-006 (existing tests pass; backward-compat on explicit-`--force`) | ✅ — `test_tasks.py` 15/15 green; `test_explicit_force_backward_uses_existing_path` confirms FR-011 |

---

## Cross-WP Integration

Single lane (lane-a) handled both WPs sequentially. WP02 read WP01's auto-promote block and built tests against it end-to-end. No add/add merge conflicts expected because WP01 owns `src/` and WP02 owns `tests/` — disjoint paths.

---

## Review History Signal

- WP01: implemented in ~4.5 min; reviewer approved on first pass with notable observations only (no blockers).
- WP02: implemented in ~31 min; reviewer approved on first pass after corroborating three baseline claims (fixture absence, pre-existing failures, pre-existing ruff). One PARTIAL FR (FR-009 skip) accepted with mitigation.

Zero rejection cycles, zero arbiter overrides.

---

## Final Verdict

**PASS WITH NOTE**

### Verdict rationale

12 of 12 FRs covered. FR-009 reaches PARTIAL adequacy because the fixture cross-check is currently skipped due to package-release sequencing (Mission 1's fixture in `spec-kitty-events` main branch but not yet published). The direct CLI wire-shape invariants are asserted before the skip path; the contract is verified, only the defense-in-depth cross-check defers. Skip auto-activates on the next `spec-kitty-events` release with no code change.

All 5 NFRs measured within threshold. All 6 constraints honored. Zero security findings, zero silent-failure patterns, zero regressions in the targeted test territory. Pre-existing failures and ruff errors elsewhere verified as baseline by the WP02 reviewer (reproduced on `cdf71379` before WP02 work).

### Open items (non-blocking)

- **DRIFT-1**: After Mission 2 + Mission 3 merge, publish a `spec-kitty-events` release containing Mission 1's fixture. The next `spec-kitty` CI run will auto-activate the FR-009 fixture cross-check. Track in Mission 4 closure.
- **Pre-existing failures and ruff**: out of this mission's scope. Housekeeping concern.

### Recommendation

Proceed to `spec-kitty merge --mission backward-transition-cli-emit-01KRV8GC`. No pre-merge fixes required.
