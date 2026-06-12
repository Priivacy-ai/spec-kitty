# Mission Review Report: coordination-merge-stabilization-01KTXRVR

**Reviewer**: claude:fable-5 (orchestrator) + two independent verification agents (FR-trace/drift; risk/security)
**Date**: 2026-06-12
**Mission**: `coordination-merge-stabilization-01KTXRVR` — Coordination and Merge Stabilization (mission 131)
**Baseline commit**: `e48bdd531` | **HEAD at review**: `262d44ecf` | **PR**: #1879
**WPs reviewed**: WP01–WP05 (all `done`; event log clean — 0 rejection cycles, 0 self-approvals, 1 benign forced `for_review→for_review` re-assert on WP04)

---

## Gate Results

### Gate 1 — Contract tests
- Command: `SPEC_KITTY_ENABLE_SAAS_SYNC=1 .venv/bin/pytest tests/contract/ -q`
- Result: **FAIL (pre-existing, not mission-caused)** — 1 failed, 257 passed
- Notes: `test_contract_example_round_trip[...doctrine-glossary-architecture-consolidation-01KTNWFC/contracts/charter-extends-and-drg-regen.md::block-MISSING_FRONTMATTER]`. The failing contract file was last modified by PR #1850 (`8544012fa`); the mission diff contains **zero lines** under that mission's directory. This is a baseline defect that predates the mission, not contract drift introduced by it.

### Gate 2 — Architectural tests
- Command: `.venv/bin/pytest tests/architectural/ -q`
- Result: **FAIL — 3 of 4 failures are mission-caused**
- Mission-caused:
  1. `test_no_dead_symbols` — `specify_cli.status.doctor_husks::HuskEntry/HuskFixResult/HuskReport` in `__all__` with no src/ importer. *Characterization*: not dead code — they are the return types of `scan_workspace_husks`/`fix_workspace_husks`, which ARE called from `doctor.py:857`; only the type names lack an explicit importer. Cosmetic; fix = trim `__all__` or import the types in `doctor.py`.
  2. `test_docs_cli_reference_parity` — new `spec-kitty doctor workspaces` missing from reference docs.
  3. `test_pytest_marker_convention` — WP03's new `tests/architectural/test_merge_pipeline_ratchets.py` lacks a `pytestmark`.
- Pre-existing: `test_status_module_boundary` (flags `migration/mission_state.py:43`; that file shows zero diff vs baseline — verified by WP03's implementer via stash and re-verified here).

### Gate 3 — Cross-repo E2E
- Result: **NOT RUN — environmental**. The `spec-kitty-end-to-end-testing` repo is not present on this machine. No `mission-exception.md` artifact exists; per C-010 this requires an operator-granted exception (single-scenario waivers only — here the entire suite is unavailable, which exceeds what the exception schema permits). Operator decision required.

### Gate 4 — Issue Matrix
- File: `kitty-specs/coordination-merge-stabilization-01KTXRVR/issue-matrix.md` — 17 rows
- Result: **FAIL** — 5 rows carry `in-mission` verdicts after the mission reached `done` (#1826, #1861, #1814, #1736, #1833). Per the gate, `in-mission` must resolve to a terminal verdict before merge; the done-transition rejection did not fire (the merge recorded done transitions via override — itself workflow-failure evidence). *Factually*, all five issues are resolved by the merged code (each FR-traced ADEQUATE below); the verdict cells are stale bookkeeping. Remediation is mechanical: update the 5 cells to `fixed` with commit evidence (`61d4cdb`).
- Empty/`unknown` verdicts: 0. `deferred-with-followup` rows missing handles: 0.

---

## Full-Suite Status on Merged Main (correction of record)

The earlier orchestration report stated "full suite exit 0" — **that was wrong** (a pipe masked the exit code; the `-x` run actually stopped at the first failure after 1373 passed). Actual state at HEAD:

- **4 mission-caused test regressions** in `tests/agent/test_review_validation_unit.py`: the suite fabricates lane worktrees via bare `mkdir` (lines 47/81/116); WP04's new invariant (workspace must be a real git worktree) rejects them **by design**. WP04 migrated 3 fixture files in `tests/specify_cli/cli/commands/agent/` but missed this fourth file in `tests/agent/`. Production behavior is correct; the fixtures need the same migration (use real worktrees / `.git` markers, as done in the other three files).
- Plus the 3 mission-caused architectural failures from Gate 2.
- **CI on PR #1879 will be red until these 7 are fixed.**

---

## FR Coverage Matrix

All 13 FRs trace **ADEQUATE** — spec → WP → live test → production code, with non-vacuity verified for every ratchet (full evidence table in the FR-trace agent report; highlights):

| FR | Adequacy | Key evidence |
|---|---|---|
| FR-001 | ADEQUATE | e2e drives production `_run_lane_based_merge`; coord HEAD==tip asserted; dirty refusal preserves planted file byte-for-byte |
| FR-002 | ADEQUATE | byte-identical HEAD/porcelain + finding parity vs commit phase |
| FR-003–005, 007 | ADEQUATE | husk suite incl. zero-git-against-primary assertion; real CLI `doctor workspaces` invoked via runner |
| FR-006 | ADEQUATE | residue-free porcelain, record-analysis unblocked, operator-file survival, C-003 pin |
| FR-008 a–e | ADEQUATE | all five ratchets present, each with an anti-vacuity property (AC10 verified red-under-revert) |
| FR-009, 010 | ADEQUATE | divergence-fixture tests; genuinely unmocked baseline recording |
| FR-011 | ADEQUATE | hygiene logs at HEAD; umbrella #1878; (GitHub live state per WP01 review's 5/5 SHA spot-checks) |
| FR-012, 013 | ADEQUATE | backstop message test reproduces real #1826 divergence; dry-run honesty tests |

**Punted FRs: none.** Dead code: none (all new modules have live src/ callers; C-002's exactly-3-sites confirmed).

## Drift Findings

- **D-1..D-5 (C-001/C-002/C-003, safe-commit semantics, status model): CLEAN** — no architecture rework, exactly 3 ref-advance sites migrated, `COORD_OWNED_STATUS_FILES` byte-identical (plus a dedicated guard test), backstop change is message-only with same type/error_code.
- **D-6 (NFR-004, LOW)**: 2 new narrow `# noqa: PLC0415` deferred-import lines (gate.py:201, status_transition.py:176) without inline prose rationale beyond the lint code; offset by the *removal* of a blanket `# noqa: BLE001`. Net suppression hygiene improved; technically deviates from "zero new suppressions".
- **Path drift (LOW)**: tasks.md/WP02 frontmatter referenced `tests/specify_cli/test_wp06_...`; the real suite is `tests/specify_cli/cli/commands/test_wp06_...` (planning typo, coverage unaffected).

## Risk Findings (from the adversarial pass)

| ID | Severity | Finding |
|---|---|---|
| **R1** | **HIGH** | `ref_advance.py` dirty gate excludes untracked (`??`) entries, but `git reset --hard` **overwrites untracked files that collide with tracked paths in the target commit**. The docstring's safety claim ("untracked files are NOT at risk") is wrong for the collision case — an untracked coord-worktree file colliding with a newly-tracked path is silently destroyed. NFR-002 has a hole. Fix shape: check untracked paths against `git ls-tree <new_sha>` and refuse on collision. |
| **R4** | **MEDIUM-HIGH** | `doctor_husks._registered_worktree_paths` **fails OPEN**: if `git worktree list` errors, the registered set is empty and `--fix` will rmtree every `.git`-less entry — the "registered worktrees are never removed" rail evaporates exactly when git is broken (the most likely time an operator runs `--fix`). Must fail closed. |
| R2 | MEDIUM-HIGH | TOCTOU: the merge lock serializes merges only; a non-merge writer (status emitter/daemon) touching the coord worktree between clean-check and reset is discarded (reflog-recoverable, silent). |
| R5 | MEDIUM | TOCTOU between husk scan and rmtree: an in-flight `git worktree add` can be deleted; cheap fix = re-verify `.git` absent immediately before each rmtree. |
| R7 | MEDIUM | Malformed/empty `worktree list --porcelain` output (e.g. newline in a path; format drift) silently yields zero checkouts → no resync → original #1826 behavior returns with no signal. No reset can bypass the clean check (verified) — the risk is a *missed* resync. |
| R3 | LOW-MEDIUM | Concurrent branch switch between snapshot and reset turns `reset --hard <branch>` into a wrong-branch reset; prefer resetting to the recorded SHA after re-verifying HEAD. |
| R10 | LOW-MEDIUM | Retrospective gate's resolver fallback is silent; fail direction is closed (completion blocked), but a pre-coordination-era stale primary log could falsely authorize; should log the fallback. |
| R11 | LOW | `core/stale_detection.py:335` and `core/worktree_topology.py:156` consume the new `exists` semantics without husk-awareness — husk WPs silently drop out of staleness monitoring (reporting inaccuracy only). |
| R6, R8, R9, R12, R13 | LOW/INFO | Symlink rmtree refusal holds the boundary (but tracebacks mid-run); partial-resync failure is loud with named repair; same-branch-twice handled; residue cleanup triple-gated and benign; `doctor --fix` UX safe-by-default *contingent on* R4/R5 fixes. |

## Silent Failure Candidates

| Location | Pattern | Verdict |
|---|---|---|
| `doctor_husks._registered_worktree_paths` | git error → empty set (fail-open) | **REJECT — R4, must fail closed** |
| `gate.py`/`agent_retrospect.py` resolver fallback | narrow except → legacy dir, no log | CONDITIONAL — add a warning log (R10) |
| `status_transition.py` narrowed except | corruption now propagates as raw traceback at `merge.py:379` | IMPROVEMENT (crash-over-corruption); LOW: wrap in structured merge error later |
| `agent/mission.py` residue cleanup OSError→warn | loud later, data re-derivable | ACCEPT |
| `workspace/context.py` toplevel OSError→False | fail-closed | ACCEPT |

## Security Notes

| Check | Result |
|---|---|
| shell=True / eval / os.system in diff | None — all subprocess calls list-args |
| New HTTP/credential surface | None |
| Path traversal from user input | None — husk paths from `iterdir()` of repo-owned dir; symlink escape blocked by rmtree's symlink refusal (R6) |
| Injection via branch names | Not exploitable (git ref-name validation; list-args). Hardening: use `refs/heads/` prefix or `--` separator in the reset (R7 note) |

## Final Verdict

**FAIL** (blocking findings present; all are small and mechanically fixable on the open PR)

### Verdict rationale

Spec→code fidelity is excellent: 13/13 FRs adequately covered by live-path tests, zero drift against constraints and non-goals, zero dead code, and the security posture of the new code is fail-closed in every direction the contracts named. The verdict is FAIL on four grounds the per-WP reviews structurally could not see: (1) **merged main's test suite is red** — 4 fixture regressions in `tests/agent/test_review_validation_unit.py` caused by WP04's (correct) invariant, plus 3 mission-caused architectural-gate failures (dead-symbol exports, docs parity for the new doctor subcommand, missing pytestmark); (2) **Gate 4 hard-fails** — five stale `in-mission` verdicts survived to `done`; (3) **R1 (HIGH)** — the resync helper's untracked-collision hole contradicts NFR-002's no-silent-discard invariant in the exact worktree it protects; (4) **R4 (MEDIUM-HIGH)** — the husk fixer's deletion rail fails open precisely when git is unhealthy. None of these invalidate the shipped fixes; all seven CI-blocking items plus R1/R4/R5 are addressable in one small follow-up commit on PR #1879.

### Blocking remediation list (one commit on `pr/coordination-merge-stabilization-131`)

1. Migrate the 4 fabricated-worktree fixtures in `tests/agent/test_review_validation_unit.py` (same pattern WP04 used for the other 3 fixture files).
2. Add `pytestmark` to `tests/architectural/test_merge_pipeline_ratchets.py`.
3. Trim `doctor_husks.__all__` to the two functions (or import the types in `doctor.py`).
4. Add `spec-kitty doctor workspaces` to the CLI reference docs.
5. Update the 5 stale `in-mission` issue-matrix rows to `fixed` citing `61d4cdb`.
6. R4: make `_registered_worktree_paths` fail closed (scan error ⇒ refuse `--fix`); R5: re-verify `.git` absent immediately before each rmtree.
7. R1: extend the ref-advance dirty gate to refuse when an untracked path in a checkout collides with a tracked path in `new_sha` (and correct the docstring).

### Open items (non-blocking)

- R2/R3/R7 hardening (coord-writer TOCTOU, SHA-pinned reset, `-z` porcelain parsing) → #1878 umbrella.
- R10 fallback warning log; R11 husk-awareness in stale-detection/topology reporting → #1878.
- D-6 noqa prose rationales; tasks.md path typo; Gate 1's pre-existing contract failure (file upstream issue for the 01KTNWFC contract frontmatter); pre-existing `test_status_module_boundary` failure.
- Gate 3: operator to either run the cross-repo e2e suite where available or record the environmental exception.

## Retrospective Reminder

The canonical post-merge sequence (mission review → retrospective → synthesize) is in progress. The terminus auto-generation **did not run** at merge (workflow-failures-log §H.26); the record was authored manually via `retrospect create` and lives at `.kittify/missions/01KTXRVR2HPMKGMH20K18JZ1SA/retrospective.yaml` — note it is **gitignored** (failure §H.27, #1771 residual, commented upstream). The substantive retrospective input is the committed `workflow-failures-log.md` (28 findings). `spec-kitty agent retrospect synthesize --mission coordination-merge-stabilization-01KTXRVR` will find no proposals (the YAML record is empty of findings); treat the failures log + this report as the retrospective corpus.
