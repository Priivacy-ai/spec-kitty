---
work_package_id: WP02
title: tasks_support risk-isolated re-anchor + final category_4 drain
dependencies:
- WP01
requirement_refs:
- FR-001
- FR-002
- FR-003
tracker_refs:
- '#2289'
planning_base_branch: tidy/unshim-wave1
merge_target_branch: tidy/unshim-wave1
branch_strategy: Planning artifacts for this mission were generated on tidy/unshim-wave1. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into tidy/unshim-wave1 unless the human explicitly redirects the landing branch.
subtasks:
- T005
- T006
- T007
phase: Phase 1 - Sequential deletion lane
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2339339"
history:
- at: '2026-07-03T12:00:28Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/tasks_support.py
- tests/specify_cli/cli/commands/agent/test_tasks.py
- tests/specify_cli/cli/commands/test_charter_lint.py
- tests/specify_cli/test_runtime_hard_fail.py
- tests/git_ops/test_atomic_status_commits_unit.py
- tests/tasks/test_tasks_support.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP02 – tasks_support risk-isolated re-anchor

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

---

## ⚠️ IMPORTANT: Review Feedback

Check the `review_ref` field in the event log before starting; address all feedback.

---

## Objectives & Success Criteria

Spec FR-001/FR-002/FR-003 remainder (IC-02): delete `src/specify_cli/tasks_support.py`
(30 LOC, canonical home `specify_cli.task_utils` / `.support`) after re-anchoring its
**~35 sites across ~14 test files — including 10 `patch("specify_cli.tasks_support...")`
string targets**, each with a provable interception check. This WP is deliberately
risk-isolated: the ENTIRE silent-no-op mock class lives here, and the reviewer's whole
surface is "did every re-pointed mock still intercept". Success = module gone,
`_CATEGORY_4_BACKCOMPAT_SHIMS == frozenset()`, `_baselines.yaml category_4: 0`, the
tasks_support pyproject override gone, per-site interception evidence in the Activity
Log, full suite green.

## Context & Constraints

- **Ownership note**: the frontmatter lists the 4 dominant test files; the full
  re-anchor set is ~14 files (enumerate live with the T005 grep). Editing the
  remaining ~10 files + the 3 shared gate/config files
  (`test_no_dead_modules.py`, `_baselines.yaml`, `pyproject.toml`) is
  rationale-backed out-of-map leeway: they are WP01-owned, WP01 is your dependency
  (already merged into your base), and this lane is sequential — record a one-line
  rationale in the Activity Log per the ownership-leeway convention.
- **The patch-target trap (spec AC 1.2, research.md D6)**: `unittest.mock.patch`
  patches the LOOKUP namespace. After you re-anchor a consumer from
  `from specify_cli.tasks_support import find_repo_root` to
  `from specify_cli.task_utils import find_repo_root`, a patch that targeted
  `specify_cli.tasks_support.find_repo_root` must now target where the CONSUMER looks
  it up — e.g. `patch("specify_cli.cli.commands.charter.find_repo_root")`: the
  charter PACKAGE re-exports `find_repo_root` in its `__init__.py` and `lint.py`
  resolves it via `_charter_pkg.find_repo_root()` at call time, so the patch target
  is the package `__init__` re-export — NOT the fictitious `charter_lint` submodule
  and NOT necessarily `specify_cli.task_utils.support`. The lookup namespace may be
  a package `__init__` re-export; derive per site by reading how the consumer
  actually resolves the symbol.
- **Interception proof obligation (per rewritten patch site, no exceptions)**: EITHER
  (a) the site has / gains an `assert_called*` or call-count assertion, OR (b) record
  a red-first flip: point the rewritten patch at a bogus target → test MUST fail →
  restore correct target → green. Most of the 10 sites are bare return-value
  redirects with NO call assertion today — the proof is the deliverable, not
  paperwork. Log each site's proof form in the Activity Log.
- C-002 deletion-only; C-005 canonical home from the spec table only.

## Branch Strategy

- **Strategy**: {{branch_strategy}}
- **Planning base branch**: tidy/unshim-wave1
- **Merge target branch**: tidy/unshim-wave1

## Subtasks & Detailed Guidance

### Subtask T005 – Re-anchor the plain import sites

- **Steps**:
  1. Enumerate live: `grep -rn "tasks_support" tests/ | grep -v Binary` — expect ~35
     sites / ~14 files (≈25 plain imports + 10 patch strings).
  2. Re-anchor every plain `from specify_cli.tasks_support import …` /
     `import specify_cli.tasks_support` to `specify_cli.task_utils` (check the
     canonical module's actual export surface first — symbols may live in
     `task_utils.support`; match the real layout).
  3. Run each touched file's tests.
- **Files**: the ~14 test files (leeway rule above).

### Subtask T006 – Rewrite the 10 patch() strings + interception proofs

- **Steps**:
  1. For each `patch("specify_cli.tasks_support.<symbol>")` site: read the CONSUMER
     (the production module the test exercises), determine its post-WP01/WP02 import
     form, and rewrite the patch target to the consumer's lookup namespace.
  2. Apply the proof obligation per site — (a) call assertion or (b) red-first flip —
     and log: `site file:line → new target → proof form → outcome`.
  3. Run each touched file's tests after each rewrite batch.
- **Files**: the patch-bearing test files (`test_charter_lint.py` alone has 10
  `patch(...find_repo_root)` strings — verify each one's consumer independently;
  do not bulk-replace).

### Subtask T007 – Delete the module + final drain + gates

- **Steps**:
  1. `git rm src/specify_cli/tasks_support.py`.
  2. Remove the last `_CATEGORY_4` row → the frozenset is empty; `_baselines.yaml`
     `category_4_backcompat_shims: 1` → `0`; remove the `specify_cli.tasks_support`
     pyproject mypy-override entry (~line 343).
  3. Gates: both architectural gate files green; `PWHEADLESS=1 pytest
     tests/architectural/ -q` green; whole-tree mypy 0; ruff clean; the NFR-002 grep
     for `tasks_support` returns empty in `src/`; full
     `PWHEADLESS=1 pytest tests/ -n auto --dist loadfile -p no:cacheprovider` green.
  4. Commit; paste the interception-proof table into the handoff note.

## Test Strategy

```bash
export PATH="$PWD/.venv/bin:$PATH"
grep -rn "tasks_support" tests/ src/   # after T007: zero hits outside kitty-specs archives
PWHEADLESS=1 pytest tests/specify_cli/cli/commands/test_charter_lint.py tests/specify_cli/test_tasks.py -q
PWHEADLESS=1 pytest tests/architectural/ -q -p no:cacheprovider
PWHEADLESS=1 pytest tests/ -n auto --dist loadfile -p no:cacheprovider
python -m mypy src/ 2>&1 | tail -2; ruff check .
```

## Risks & Mitigations

- **Silent no-op mock** — a rewritten patch that targets the wrong namespace leaves
  the test green while validating nothing. The per-site proof obligation is the
  mitigation; a bulk sed across the 10 strings is a REVIEW REJECT.
- **Canonical export-surface mismatch** — `task_utils` vs `task_utils.support`
  layouts differ per symbol; read the canonical module before re-anchoring.

## Review Guidance

- The interception-proof table (10 rows, one per patch site, each with proof form +
  outcome) is the headline artifact — reject if any row is missing or "assumed".
- Spot re-derive 3 patch targets by reading the consumer modules yourself.
- `_CATEGORY_4` empty + baseline 0 + pyproject entry gone, all in this WP's diff.

## Activity Log

> Append at the END, chronological. Format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`

- 2026-07-03T12:00:28Z – system – Prompt created.
- 2026-07-03T12:55:31Z – claude:opus:python-pedro:implementer – shell_pid=2225885 – Assigned agent via action command
- 2026-07-03T13:21:34Z – claude:opus:python-pedro:implementer – shell_pid=2225885 – MISATTRIBUTION NOTE: validator flagged T008-T012 as unchecked WP02 subtasks, but tasks.md assigns those to WP03 (WP02 owns only T005-T007, all done). Used --force per prompt guidance; did NOT mark WP03's subtasks. --- Deleted src/specify_cli/tasks_support.py after re-anchoring 35 sites/14 files onto specify_cli.task_utils. The 10 patch('specify_cli.tasks_support.find_repo_root') sites (all test_charter_lint.py) re-targeted to consumer lookup namespace specify_cli.cli.commands.charter.find_repo_root (charter pkg __init__ re-export; lint.py resolves via _charter_pkg.find_repo_root() at call time), each with per-site mock_frr.assert_called_once() proof. PROBE: old target silent no-op called=False; new called=True count=1; two wrong task_utils targets both called=False. 10-row interception-proof table in WP02 Activity Log. Atomic C-006 drain: _CATEGORY_4=frozenset() + _baselines category_4:1->0 + pyproject mypy-override removed in the delete commit. GATES: ruff diff exit0; mypy 0 (1062 files); tests/architectural 641 passed; NFR-002 grep src/ empty; full suite 28467 passed, 5 fail+1 err ALL non-mine (sphinx env; 3 reproduce on clean base; 2 e2e parallel flakes pass in isolation). Commit 37cd33f38.
- 2026-07-03T13:22:26Z – claude:opus:reviewer-renata:reviewer – shell_pid=2339339 – Started review via action command
- 2026-07-03T13:27:19Z – user – shell_pid=2339339 – Review passed (--force: T008-T012 are WP03 subtasks per tasks.md, misattributed by validator; WP02's own T005-T007 all done). Independently verified all 10 charter_lint patch sites re-anchored to specify_cli.cli.commands.charter.find_repo_root (consumer lookup namespace: lint.py:96 _charter_pkg.find_repo_root(); charter/__init__.py:23 re-exports from task_utils); each has assert_called_once. Discrimination probe (site:88 -> task_utils.find_repo_root) went RED 'Called 0 times' then restored, proving assertions load-bearing. Gates: charter_lint 10 passed; test_no_dead_modules+test_ratchet_baselines 5 passed with _CATEGORY_4=frozenset()/baseline 0; mypy clean 1062 files; grep tasks_support src/ empty. Atomic drain in delete commit 37cd33f38; only src change is tasks_support.py deletion.
