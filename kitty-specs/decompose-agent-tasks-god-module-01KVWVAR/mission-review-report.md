# Post-Merge Mission Review — decompose-agent-tasks-god-module-01KVWVAR

**Mission ID**: 01KVWVARJKSH9T2QNHJVE4ZC7Y · **Issue**: #2058 (parent #1797) · **Reviewed**: 2026-06-24
**Branch reviewed**: `kitty/mission-decompose-agent-tasks-god-module-01KVWVAR` (merged, all 7 WPs `done`)
**Baseline**: `origin/main` (`c3814ec5a`) · diff scope `git diff origin/main..HEAD`
**Reviewer**: senior post-merge auditor (adversarial spec→code fidelity)

**FINAL VERDICT: PASS WITH NOTES** — the decomposition is sound, behavior-preserving, and FR-complete. The commit-routing centralization is correct and the FR-007 deferral is the right engineering call. Two genuine, mission-introduced architectural-gate regressions (test marker / orphan-surface; dead-symbol `__all__`; stale untrusted-path inventory; an identifier-name false-positive in the raw-path gate) are **non-blocking but must be cleaned up as fast-follow** — they are bookkeeping/hygiene misses, not correctness or security defects. None alter runtime behavior.

---

## 1. Gate Results

| Gate | Result | Notes |
|------|--------|-------|
| **Gate 1 — Contract** (`tests/contract/`) | NOT RUN (time-boxed) | Requires `SPEC_KITTY_ENABLE_SAAS_SYNC=1` / network; FR-001 is already proven by the dedicated golden CLI contract test (48 passed, below). Recorded as deferred, not FAIL. |
| **Gate 2 — Architectural** (`tests/architectural/`) | **10 failed / 471 passed** | 4 failures **environmental** (`test_tid251_enforcement.py` — `No module named ruff` in the test venv; also fail on origin/main baseline → NOT mission-caused). **6 failures mission-introduced** but reducible to 3 root causes — see Drift Findings D-1/D-2/D-3. None are correctness/security regressions. |
| **Gate 3 — Cross-repo e2e** (`spec-kitty-end-to-end-testing`) | **N/A (environmental)** | Repo not present in this checkout. Recorded N/A, not FAIL. |
| **Gate 4 — Issue matrix** | **PASS** | All 5 rows terminal: #2058 `fixed`, #2060 `fixed`, #1797 `deferred-with-followup` (parent epic, sibling decompositions), #2056/#1623 `verified-already-fixed` (convention precedents). No `in-mission`/`unknown`. |
| ruff (`C901` + full) on the 6 files | **PASS** | `All checks passed!` — NFR-001 (maxCC ≤ 15) and NFR-003 (ruff clean) hold. |
| mypy `--strict` on the 6 files | **PASS** | `Success: no issues found in 6 source files` — NFR-003 holds. |
| FR pinning / per-seam / contract suites | **PASS** | move_task guard + #1615-1618 regression: 36 passed; FR-008 + golden CLI contract: 48 passed; 5 per-seam suites: 167 passed. |

---

## 2. FR Coverage Matrix

The decisive question per FR: *if the implementation were deleted, would the test fail?* All mapped tests answered **yes** (real-logic, not synthetic-fixture). No false-positive tests found.

| FR | Requirement | Spec→Test→Code | If-deleted? | Verdict |
|----|-------------|----------------|-------------|---------|
| **FR-001** | Public CLI surface byte-identical | `test_tasks_cli_contract.py` (27 tests) pins all 9 commands, flag subsets, exit codes 0/1/2, `--json` envelope shapes; captured pre-refactor (WP01), green post-refactor. | Yes — asserts concrete fixtures in `fixtures/tasks_cli/help/*` + `json/envelopes.json`. | **ADEQUATE** |
| **FR-002** | `#2058` pointer comment at head of `tasks.py` | Present (`tasks.py` lines 3-7): GOD-MODULE banner + `issues/2058`, matching the `#2056`/`#1623` convention. | Code-review proof; convention match confirmed. | **ADEQUATE** |
| **FR-003** | Decompose into cohesive seams; 6 mega-fns internally split | 5 seams created (outline 229, materialization 287, finalize_validation 324, dependency_graph 200, parsing_validation 997 LOC). One-way imports **verified empty** (no seam imports `tasks.py`). All 5 imported by `tasks.py` (grep count = 5). `_validate_ready_for_review` (348 LOC) sub-split into ≤15-CC helpers. | Yes — per-seam direct unit tests (167 passed) exercise moved logic. | **ADEQUATE** |
| **FR-004** | Each seam carries focused direct tests, ≥90% on new code | 5 per-seam test files driving real parser/validator/gating logic (167 tests). Acceptance-matrix records 90-100% coverage per seam. | Yes — tests import seam functions directly, not via CLI. | **ADEQUATE** (see D-1: 3 of these files are CI-invisible) |
| **FR-005** | `tasks.py` reduced toward a thin shim | 4633 → 3346 LOC; ~1290 LOC relocated; every function maxCC ≤ 15 (ruff C901 clean). | Code-review + ruff. | **ADEQUATE** (documented NFR-004 LOC deviation — adjudicated §5) |
| **FR-006** | 3 commit tails route through `commit_for_mission` | `tasks.py` lines 1555/1906/2649 call `commit_for_mission`; tail 3 threads `target_branch=`. AST guard in `test_wp03_bypass_writers_fr008.py` asserts ZERO `safe_commit` call sites. `grep safe_commit` in `tasks.py` returns only comments. | Yes — AST test fails if a bypass writer reappears. | **ADEQUATE** |
| **FR-007** | Delete now-dead `is_protected` pre-checks | **DEVIATION (deferred, validated).** Pre-checks `_skip_target_branch_commit` (tasks.py:530) and `_protected_branch_status_commit_error` (tasks.py:497) are **NOT dead** — independently re-verified (§4). | Pinning tests (36 passed) would break on deletion. | **ADEQUATE (correct deferral)** |
| **FR-008** | Regression test: router-only + byte-identical message/exit | `test_wp03_bypass_writers_fr008.py` — AST router-only proof + per-tail protected-primary byte-identity + exit 1; 21 passed (within the 48-pass run). | Yes — asserts verbatim error string + exit code. | **ADEQUATE** |

**FR coverage matrix verdict: ALL ADEQUATE.** No synthetic-fixture / false-positive tests detected; every mapped test fails on implementation deletion.

---

## 3. Drift Findings

### D-1 (HIGH, mission-introduced) — 3 new test files are invisible to CI marker profiles
`test_tasks_materialization.py`, `test_tasks_finalize_validation.py`, `test_tasks_dependency_readiness.py` lack a module-level `pytestmark`. This trips **two** Gate-2 tests with the same root cause:
- `test_pytest_marker_convention.py::test_every_test_file_declares_a_pytestmark_marker`
- `test_gate_coverage.py::test_no_new_orphan_surfaces` ("3 test file(s) selected by ZERO CI gates … will never run in CI")

Impact: the files pass when invoked by path (confirmed: 167 per-seam tests green), **but they are not selected by `-m fast` / `-m unit` / `-m architectural` profiles**, so FR-004's coverage guarantee is undermined *in CI* for 3 of the 5 seams. The other 3 new test files (`test_tasks_cli_contract`, `test_tasks_outline`, `test_tasks_parsing_validation`) and `test_wp03_*` correctly carry `pytestmark`. **Fix is one line each** (`pytestmark = [pytest.mark.unit, pytest.mark.fast]`). `test_tasks_dependency_readiness.py` also lacks `import pytest`. Pre-existing baseline on origin/main: this gate **passed** (the files are new) → mission-attributable.

### D-2 (MEDIUM, mission-introduced) — dead `__all__` re-exports flagged by symbol-level gate
`tasks.py` introduces a new `__all__` (origin/main had none) re-exporting 6 symbols (`_behind_commits_touch_only_planning_artifacts`, `_check_dependent_warnings`, `_lane_targets_for_emit`, `_wp_lane_from_status_events`, `app`, `compute_incomplete_dependents`). `test_no_dead_symbols.py::test_no_public_symbol_in_all_is_unimported` flags them as declared-but-unimported-by-other-`src/`. The header comment claims they are listed "so the re-export is explicit (C-007)", but the dead-symbol ratchet requires either an actual importer or an entry in `_SYMBOL_ALLOWLIST` with a rationale + tracker ticket. Neither was added. **Not a runtime defect** (the symbols are live, used by seams/tests), but the gate is red. Fix: allowlist the re-exports with rationale, or drop the unneeded `__all__` entries.

### D-3 (LOW/MEDIUM, mission-introduced) — stale untrusted-path inventory + raw-path identifier false-positive
Two distinct Gate-2 failures, both bookkeeping-class:
- `test_untrusted_path_containment.py` (2 tests): the audited sink `worktree_kitty / mission_slug / "tasks"` `.exists()` probe **moved from `tasks.py:1972` to `tasks.py:1046`** during the refactor, but `untrusted_path_audit/inventory.md` still records line 1972. The sink is **unchanged** (same raw-`--mission`-slug `.exists()` probe, already dispositioned `routed-through-seam (TODO)`). This is a line-drift the mission failed to refresh; **no new untrusted-path join was introduced**. Fix: re-run `audit.py` and update the line number in inventory.md.
- `test_no_raw_mission_spec_paths.py`: flags `tasks_parsing_validation.py:720/873/980` — but the matches are the **function identifier `_check_kitty_specs_contamination`**, snagged by the gate's unquoted `kitty_specs` regex alternative. This is a **false-positive class** (the gate targets raw `"kitty-specs"` path-construction *string literals*; the function constructs no raw path — it uses `kitty-specs/` only in a docstring/message). The function was internally split out of `_validate_ready_for_review` during this mission, so the identifier (and thus the false match) is new. Fix: rename the helper (e.g. `_check_specs_contamination`), tighten the gate regex, or add a justified exemption.

### D-4 (PASS, no drift) — Constraint compliance
- **C-001** (no command/flag changes): golden contract green; FR-001 ADEQUATE.
- **C-002** (canonical `commit_for_mission`; no bespoke guards reintroduced): AST guard proves router-only; the surviving pre-checks (FR-007) are a *skip* decision, not a re-introduced routing guard (§4).
- **C-003** (byte-identical incl. commit routing): FR-008 byte-identity proven.
- **C-004** (no new suppressions): the 4 `# noqa: BLE001` in `tasks_parsing_validation.py` **pre-existed verbatim in `origin/main:tasks.py`** (lines 261/339/548/1689) — moved with the code, not new. Each is a narrowly-justified fail-closed/fail-open guard with inline rationale. **Zero net-new suppressions.**
- **C-006** (`mission.py` untouched): `git diff origin/main..HEAD -- agent/mission.py` = **0 lines**. Clean.

---

## 4. Independent Adjudication — FR-007 Deviation (deferred deletion)

**Verdict: the deferral is CORRECT.** Same discovery class as the "3 tails not 4" re-grounding in `research.md §3` — the requirement's literal premise was factually wrong.

Evidence (independently traced, not taken from the acceptance matrix):
- `_skip_target_branch_commit` (`tasks.py:530`) is explicitly **not a routing authority** — it returns `True` only when *coord topology is active AND the primary `target_branch` is protected*, and its docstring states it "selects no ref; it suppresses a commit that the protection policy would refuse anyway."
- In `move_task` (`tasks.py:995-1032`), `skip_target_branch_commit=True` takes a distinct arm: it **suppresses the direct WP-file commit and proceeds → exit 0**, with the status transition committed to the coordination branch treated as authoritative. (It only escalates to exit 1 if unsupported metadata flags — tracker_refs/assignee/shell_pid/activity_log — are passed alongside the skip.)
- `commit_for_mission` cannot reproduce this: on a protected primary it returns `no_op_wrong_surface` → the call site maps that to a refusal → **exit 1**. So routing the skip arm through the router would convert a silent-skip-with-coord-authority (exit 0) into a hard refusal (exit 1) — an observable behavior change, violating C-003.
- Pinning tests confirm the arm is live: `test_move_task_guard.py` + `test_issue_1615_1616_1617_1618.py` → **36 passed**. Deleting the pre-checks would break them.

FR-006's *intent* (centralize the routing path through the canonical router) is **fully achieved** for the genuine commit tails; the surviving pre-checks govern a separate coord-topology silent-skip behavior the router was never designed to own. Revisit deletion only if that silent-skip behavior is itself redesigned. This is the right call.

---

## 5. NFR-004 LOC Deviation Adjudication

`tasks.py` is 3346 LOC vs the ~1200 research target. Spec NFR-004 explicitly names **maxCC ≤ 15 (NFR-001) as the binding constraint** and the LOC figure as "the realistic floor." maxCC ≤ 15 holds everywhere (ruff C901 clean). The residual is large because the 9 command *bodies* (`move_task`, `status`, `map_requirements` orchestration) carry genuine sequential logic at low branching — not extractable without inventing artificial seams. **Deviation is acceptable and correctly documented.** Further body-thinning is a legitimate fast-follow, not a mission failure.

---

## 6. Risk / Anti-Pattern Findings

- **Dead code**: no orphaned seam — all 5 seams imported by `tasks.py` (grep = 5). The `__all__` re-exports (D-2) are the only "dead-by-gate" symbols and are live in practice.
- **Silent empty returns**: the seams add several `return None` / `return []` guards. All inspected ones are in moved validation/parser helpers with explicit fail-open/fail-closed rationale (the 4 BLE001 guards) or structured outcome returns — no newly-introduced *silent swallowing of real errors*. The `tasks.py:213` BLE001 ("legacy fixtures keep target-branch fallback") pre-existed.
- **Cross-WP integration on the shared file**: the merge was a manual multi-lane integration converged onto lane-g, evidenced by 15 `force=true` status events. **Reviewed**: every force has a detailed rationale citing "net kitty-specs tree == mission (benign integration-merge history), merge-safe." The code-bearing WP07 force (FR-007 deferral) and WP03 cycle-2 approval were `user`-adjudicated (human), and WP03 was reviewed by `reviewer-renata` (distinct actor from the `randy-reducer` implementer) — **no self-approval anti-pattern**. WP03 had a legitimate cycle-1 reject (stray `-` file) → fixed → re-approved.

## 7. Silent-Failure Candidates

None blocking. The fail-open guards (`# noqa: BLE001`) in `tasks_parsing_validation.py` are intentional and pre-existing (moved verbatim from origin/main). The `_map_requirements_feature_dir` `ActionContextError`→candidate-dir translation (`tasks.py:242`) is a deliberate message-preservation shim, documented. No new exception handler swallows a real error without recovery/logging.

## 8. Security Notes

**No security regressions.** This mission touches git-commit routing + subprocess git calls (in `tasks_dependency_graph.py`, `tasks_parsing_validation.py`):
- **Shell injection**: every `subprocess.run` uses **list-arg form** (`["git", "merge-base", "HEAD", check_branch]`, `["git", "diff", "--name-only", f"{merge_base}..{check_branch}"]`, `["git", "status", "--porcelain", str(feature_dir)]`). **No `shell=True`, no `os.system`, no string-into-shell concatenation.** The `f"{merge_base}..{check_branch}"` refspec is a single list element passed to git, not shell-interpolated. The `console.print(f"...git rebase...")` lines are user-facing *guidance strings*, never executed.
- **Path handling**: the one untrusted-path sink (`mission_slug` join, D-3) is a `.exists()` probe that moved but did not change behavior; already dispositioned in the audit inventory.
- **Protected-branch enforcement**: the commit-routing change **strengthens** centralization (single `commit_for_mission` authority) and FR-008 proves the protected-primary refusal message/exit code are byte-identical. The surviving `is_protected` skip arm (FR-007) preserves — does not weaken — the existing refusal-vs-skip semantics.

---

## 9. Final Verdict — PASS WITH NOTES

**Rationale**: The mission delivers its core intent fully and correctly. The god-module is decomposed into 5 cohesive, one-way-imported, independently-tested seams; the CLI surface is byte-identical (golden contract green); commit routing is centralized through `commit_for_mission` with byte-identical protected-primary behavior; maxCC ≤ 15 everywhere; mypy --strict and ruff clean; the FR-007 and NFR-004 deviations are both the correct engineering calls, independently re-verified. The issue matrix is fully terminal.

The notes are **non-blocking hygiene/bookkeeping regressions** introduced by the mission, all in the architectural-gate layer, none affecting runtime behavior, correctness, or security:
1. **D-1 (HIGH)** — 3 new test files missing `pytestmark` → CI-invisible (fix: 3 one-liners). This is the most important to fix, because it silently weakens the very FR-004 coverage guarantee the mission claims.
2. **D-2 (MEDIUM)** — dead-`__all__` re-exports not allowlisted.
3. **D-3 (LOW/MEDIUM)** — stale untrusted-path inventory line number + a raw-path-gate identifier false-positive.

These should be addressed in a fast-follow PR (single small commit refreshing markers, the symbol allowlist, the inventory line, and either renaming `_check_kitty_specs_contamination` or tightening the gate regex). They do **not** justify FAIL: no defect changes behavior, breaks the contract, or weakens security.

**Recommended follow-up handle**: fast-follow under #2058 (or a child of #1797) — "tasks.py decomposition: refresh architectural-gate bookkeeping (test markers, __all__ allowlist, untrusted-path inventory, raw-path identifier)."

---

## 10. Retrospective Reminder

- The Gate-2 architectural suite is the layer that catches what unit/contract tests cannot — **run it before declaring a decomposition mission done.** Three of its findings (D-1/D-2/D-3) are exactly the class a per-WP review misses: they only surface when the whole tree is re-scanned post-integration.
- When a refactor *moves* a function, re-check every gate that records **line numbers or symbol-name patterns** (untrusted-path inventory, raw-path regex, symbol allowlists) — these are the silent casualties of relocation.
- New test files need a `pytestmark` to count in CI. "167 tests passed when I ran them by path" is not the same as "they run in CI." Wire the marker the moment the file is created.
- The two documented deviations (FR-007 deferral, NFR-004 LOC) were handled exemplarily: premise re-grounded in research, validated with pinning tests, recorded in the acceptance matrix with terminal verdicts. This is the model for non-blocking deviation handling.
