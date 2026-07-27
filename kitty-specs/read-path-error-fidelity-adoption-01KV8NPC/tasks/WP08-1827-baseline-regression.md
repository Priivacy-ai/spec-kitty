---
work_package_id: WP08
title: '#1827 baseline regression test (test-only)'
dependencies: []
requirement_refs:
- FR-012
tracker_refs: []
planning_base_branch: feat/read-path-error-fidelity
merge_target_branch: feat/read-path-error-fidelity
branch_strategy: Planning artifacts for this mission were generated on feat/read-path-error-fidelity. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/read-path-error-fidelity unless the human explicitly redirects the landing branch.
subtasks:
- T035
- T036
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2293897"
history:
- 2026-06-16 created (/spec-kitty.tasks)
agent_profile: python-pedro
authoritative_surface: tests/specify_cli/merge/
create_intent:
- tests/specify_cli/merge/test_1827_baseline_regression.py
execution_mode: code_change
owned_files:
- tests/specify_cli/merge/test_1827_baseline_regression.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before doing anything else, load the implementer profile so identity, governance scope, and
boundaries are in force for this session:

```
/ad-hoc-profile-load python-pedro
```

Then read, in this order, so the regression test is grounded in the canonical mission record (do NOT
improvise from memory):

- `kitty-specs/read-path-error-fidelity-adoption-01KV8NPC/spec.md` — FR-012, C-002/C-003
  (live-evidence discipline), and the issue-matrix #1827 row (**re-test-first**).
- `kitty-specs/read-path-error-fidelity-adoption-01KV8NPC/plan.md` — WP08 / decision **D-3**
  (#1827 verified-already-fixed; deliver a full-sequence-incl-resume regression test only, NO code
  fix).
- `kitty-specs/read-path-error-fidelity-adoption-01KV8NPC/contracts/behavioral-contracts.md` —
  C-FR012.
- `kitty-specs/read-path-error-fidelity-adoption-01KV8NPC/research/live-repro.md` §"#1827
  (RE-TEST-FIRST)" and the §"Explicit #1827 call-out" — the live trace proving #1827 DOES NOT
  reproduce on HEAD, with the exact helper sequence and the falsification harness shape.

## Objective

Deliver a **regression test ONLY** that locks `spec-kitty merge`'s post-merge baseline ordering as
**verified-already-fixed** (FR-012, C-FR012, decision D-3). Debbie's live repro PASSED on HEAD — the
ordering is structurally fixed — so this WP writes **NO code fix**. The test exercises the full
`merge` record→commit→assert sequence **including a resume/re-run** and includes a **falsification
guard** that reproduces the exact #1827 error string under the BROKEN ordering, so the green is
trustworthy (live-evidence discipline).

**This WP owns ONLY a test file. It MUST NOT modify any merge source module.** Editing
`src/specify_cli/cli/commands/merge.py` (or any `src/` file) is out of scope and a contract
violation. `execution_mode` is `code_change` purely because a new test file is added; there is no
production source change.

## Context

**Why test-only (witnessed on HEAD, `research/live-repro.md` §"#1827").** Issue #1827 (OPEN): `merge`
completes, then errors `baseline_merge_commit is missing from committed meta.json on main` because
the validation ran *before* the tool wrote the field; re-running re-merges and fails identically
(circular). Debbie drove the **exact HEAD merge sequence** with the real helpers on a real
modern-mission repo:

1. `_record_baseline_merge_commit(...)` — `src/specify_cli/cli/commands/merge.py:1633`
2. the bookkeeping commit (carries `meta.json` to the target branch)
3. `_assert_baseline_merge_commit_on_target(...)` — `src/specify_cli/cli/commands/merge.py:1758`
4. the resume/re-run trigger: advance HEAD past the baseline and re-run record+assert.

**Result:** step 3 PASSED; the resume re-record kept the original baseline (idempotent) and the
resume assert PASSED. The ordering is structurally fixed: the assert reads the **recorded** baseline
from working `meta.json` via `_recorded_baseline_from_working_meta`
(`src/specify_cli/cli/commands/merge.py:1711`) rather than a re-derived HEAD, and
`_record_baseline_merge_commit` (`:1633`) is idempotent. The in-code comment documenting the fix and
the existing passing suite `tests/merge/test_merge_done_recording.py` (30 tests) corroborate this.

**Falsification proof (the shape this WP must reproduce).** Debbie ran the helpers in the BROKEN
order (assert BEFORE the bookkeeping commit lands the field on the target) and got the **exact #1827
error string**: `"...baseline_merge_commit is missing from committed kitty-specs/.../meta.json on
main..."`. So the harness genuinely detects the failure mode; HEAD simply does not trigger it. The
regression test must carry this guard so a future reordering regression is caught and the negative
result is not a false-green (C-003 — a bug witnessed in a real run is NOT considered fixed because
the code looks fixed; the falsification guard is the live-evidence anchor for the "already-fixed"
claim).

**Source-module locations (READ-ONLY references — do not edit):**
- `BaselineMergeCommitError` — `src/specify_cli/cli/commands/merge.py:179`
- `_record_baseline_merge_commit` — `:1633` (idempotent)
- `_recorded_baseline_from_working_meta` — `:1711`
- `_assert_baseline_merge_commit_on_target` — `:1758`

Note the test directory `tests/specify_cli/merge/` does not yet exist; create it (with an
`__init__.py` if the sibling `tests/specify_cli/...` packages use one) so the new test module is
collected. The closest existing reference suite is `tests/merge/test_merge_done_recording.py` — read
it for the fixture idiom, but the new file lives at the `owned_files` path.

**Engineering discipline (binding for every subtask):**
- **Live-evidence over static-fixed.** The test asserts behavior end-to-end (full sequence + resume),
  not a unit assertion in isolation; the falsification guard proves the harness is real.
- **Topology-true fixtures — NO fabricated short ids.** Use a **real git repo** with a real modern
  mission whose `meta.json` carries a **full 26-char ULID `mission_id`** (mirror Debbie's
  `01KV8NPCDEBBIE1827REPRO000`-shaped ids, not handcrafted slugs), a real target branch, and real
  commits. The resume leg must really advance HEAD past the baseline. Do not stub the merge helpers.
- **Quality gates.** New test code passes `ruff` + `mypy` with zero issues, complexity ≤ 15, NO
  suppressions (`# noqa`, `# type: ignore`, per-file ignores). Fix the code, not the gate (NFR-004).

## Subtasks

### T035 — #1827 full record→commit→assert + resume regression test (passes on HEAD) [P]
1. Create `tests/specify_cli/merge/test_1827_baseline_regression.py` (and the package `__init__.py`
   if the sibling test packages require it).
2. Build a real git-repo fixture: a modern mission dir under `kitty-specs/<slug>-<ULID8>/` with
   `meta.json` carrying a full 26-char ULID `mission_id`, INITIALLY WITHOUT `baseline_merge_commit`;
   a real target branch (e.g. `main`) and real commits.
3. Drive the exact HEAD sequence with the real helpers (imported READ-ONLY from
   `specify_cli.cli.commands.merge`):
   a. `_record_baseline_merge_commit(feature_dir, target_baseline, mission_id)`;
   b. the bookkeeping commit that carries `meta.json` to the target branch;
   c. `_assert_baseline_merge_commit_on_target(...)` → asserts NO `BaselineMergeCommitError`.
4. Add the **resume/re-run** leg: advance HEAD past the baseline, then re-run record+assert; assert
   the re-record keeps the ORIGINAL recorded baseline (idempotent — does NOT overwrite with the
   advanced HEAD) and the assert still passes (reads the recorded baseline, not a re-derived HEAD).
5. **Validation:** the test passes on HEAD; `pytest
   tests/specify_cli/merge/test_1827_baseline_regression.py -q` green; `ruff` + `mypy` clean.

### T036 — #1827 falsification guard (broken ordering would fail) [P]
1. In the same module, add a guard test that runs the helpers in the BROKEN order — assert BEFORE the
   bookkeeping commit lands the field on the target.
2. Assert that this raises `BaselineMergeCommitError` with the exact #1827 message substring
   (`"baseline_merge_commit is missing from committed"` + `meta.json` + `on main`), proving the
   harness genuinely detects the failure mode (so the green in T035 is trustworthy, not a false
   negative).
3. **Validation:** the guard test passes (i.e. the broken ordering DOES raise the expected error);
   the full module is green; `ruff` + `mypy` clean.

## Branch Strategy

Planning artifacts were generated on `feat/read-path-error-fidelity`. During `/spec-kitty.implement`
this WP may branch from a dependency-specific base, but completed changes merge back into
`feat/read-path-error-fidelity` unless the human explicitly redirects the landing branch. WP08 has
**no dependencies** and is immediately startable in parallel with WP06/WP07.

## Definition of Done

- [ ] `tests/specify_cli/merge/test_1827_baseline_regression.py` exists and is the ONLY file changed
      (plus a package `__init__.py` if required) — **NO `src/` change**, in particular
      `src/specify_cli/cli/commands/merge.py` is untouched (D-3).
- [ ] The full `merge` record→commit→assert sequence INCLUDING a resume/re-run passes on HEAD; the
      assert reads the RECORDED baseline, and `_record_baseline_merge_commit` idempotency is asserted
      (C-FR012).
- [ ] A falsification guard reproduces the exact #1827 error string under the BROKEN ordering and
      asserts `BaselineMergeCommitError` (so the green is trustworthy — live-evidence discipline,
      C-003).
- [ ] The fixture is topology-true: real git repo, real modern mission with a full 26-char ULID
      `mission_id`, real target branch, real HEAD-advance for the resume leg — no stubbed helpers, no
      fabricated short ids (NFR-002).
- [ ] `ruff` + `mypy` clean on the new test; complexity ≤ 15; no suppressions added (NFR-004).
- [ ] `pytest tests/specify_cli/merge/test_1827_baseline_regression.py -q` green.

## Risks / reviewer guidance

- **No "fiction" fix.** Do NOT write a test that pretends the ordering bug is live, and do NOT patch
  `merge.py`. The disposition is verified-already-fixed; the deliverable is a regression LOCK plus a
  falsification guard. Reviewer: confirm `git diff` touches only the test tree.
- **The resume leg is the heart of it.** A pure unit assertion against the recorded baseline is
  insufficient (live-repro is explicit). The test must advance HEAD past the baseline and re-run, so
  a future regression that re-derives HEAD instead of reading the recorded baseline is caught.
- **Falsification guard must actually fail the broken path.** If the guard does not raise
  `BaselineMergeCommitError`, the harness is not exercising the ordering and the T035 green is not
  trustworthy — reviewer should treat a non-raising guard as a blocking defect.
- **Helper imports are read-only.** Importing `_record_baseline_merge_commit` /
  `_assert_baseline_merge_commit_on_target` / `_recorded_baseline_from_working_meta` /
  `BaselineMergeCommitError` from `specify_cli.cli.commands.merge` is fine; modifying them is not.

## Activity Log

- 2026-06-16 — WP prompt authored from plan.md WP08 / decision D-3, contracts C-FR012, and the
  live-repro #1827 evidence (DOES-NOT-REPRODUCE on HEAD; test-only). Awaiting implementation.
- 2026-06-16T20:11:11Z – claude:sonnet:python-pedro:implementer – shell_pid=2262648 – Assigned agent via action command
- 2026-06-16T20:16:32Z – user – shell_pid=2262648 – Moved to claimed
- 2026-06-16T20:16:39Z – user – shell_pid=2262648 – Moved to in_progress
- 2026-06-16T20:17:06Z – claude:sonnet:python-pedro:implementer – shell_pid=2262648 – Ready: #1827 regression test-only; falsification guard confirmed — broken ordering raises BaselineMergeCommitError with exact message substring; all 3 tests green; ruff+mypy clean; no src/ touched
- 2026-06-16T20:19:52Z – claude:opus:reviewer-renata:reviewer – shell_pid=2293897 – Started review via action command
- 2026-06-16T20:28:35Z – user – shell_pid=2293897 – Review passed (renata): falsification guard proven non-vacuous; test-only
