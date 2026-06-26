---
work_package_id: WP01
title: Retire the mission_read_path shim and restore the ratchet
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-006
- FR-007
tracker_refs:
- '2048'
planning_base_branch: feat/retire-mission-read-path-shim
merge_target_branch: feat/retire-mission-read-path-shim
branch_strategy: Planning artifacts for this mission were generated on feat/retire-mission-read-path-shim. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/retire-mission-read-path-shim unless the human explicitly redirects the landing branch.
created_at: '2026-06-25T15:33:23+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "328733"
history:
- date: '2026-06-25'
  action: created
  actor: claude
agent_profile: randy-reducer
authoritative_surface: src/specify_cli/mission_read_path.py
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/mission_read_path.py
- tests/specify_cli/cli/commands/test_coord_reader_fixes.py
- tests/architectural/test_no_dead_modules.py
- tests/architectural/test_no_dead_symbols.py
- tests/architectural/_baselines.yaml
- tests/architectural/test_single_mission_surface_resolver.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned agent profile via the `/ad-hoc-profile-load` skill (profile: **randy-reducer**, role: implementer). Adopt its boundaries, governance scope, and initialization declaration for this work package. Then return here. This is a behavior-preserving *reduction* (dead-code retirement) — exactly randy-reducer's domain: remove the redundant surface, keep behavior identical, prove it with the gate.

## ⚠️ Before you start: assign the tracker ticket (DIR-003)

Per project directive **DIR-003**, before beginning implementation you MUST assign GitHub issue
**#2048** to the Human-in-Charge (HiC). Do this first:

```bash
unset GITHUB_TOKEN && gh issue edit 2048 --repo Priivacy-ai/spec-kitty --add-assignee <HiC-handle>
```

If you do not know the HiC handle, ask before proceeding.

## Objective

Retire the dead `specify_cli.mission_read_path` backcompat shim and reverse the SHRINK-ratchet bump
it caused. Mission 01KVJPEQ re-pointed the last production importer onto the canonical seam, leaving
the module with **zero `src/` callers** but bumping `category_4_backcompat_shims` from 8 to 9 to keep
the orphaned module passing the dead-module gate. This WP repoints the one remaining test importer,
deletes the module, drops its two architectural allowlist entries, and decrements the baseline
9 → 8 — all in one atomic change so the architectural suite stays green at HEAD.

**No supported production runtime behavior changes.** The only `src/` edit is deleting the shim file; the old unsupported import path intentionally stops importing.

## Context

- **The shim** (`src/specify_cli/mission_read_path.py`) re-exports the canonical worker
  `_resolve_mission_read_path` under its historical public name `resolve_mission_read_path`, plus two
  error-contract names (`STATUS_READ_PATH_NOT_FOUND_CODE`, `StatusReadPathNotFound`) via `__getattr__`.
- **The canonical seam** is `specify_cli.missions._read_path_resolver`. CRITICAL: WP01 of mission
  01KVJPEQ **privatized** the worker to `_resolve_mission_read_path` and dropped it from `__all__`.
  **There is NO public `resolve_mission_read_path` symbol on the canonical module.** The repoint must
  therefore import the private worker and alias it. `StatusReadPathNotFound` IS public (in `__all__`).
- **Importer census** (already verified during planning — see `research.md` D-02):
  - `tests/specify_cli/cli/commands/test_coord_reader_fixes.py` — the ONLY real importer of the shim
    (7 import sites). REPOINT these.
  - `tests/integration/test_cli_status_mediation.py` — imports from the canonical resolver already.
    **DO NOT TOUCH.**
  - `tests/specify_cli/regression/test_issue_1615_1616_1617_1618.py` — only asserts the *string*
    `resolve_mission_read_path` appears in production source. **DO NOT TOUCH.**
  - `tests/architectural/test_single_mission_surface_resolver.py` — line ~828 is a *string fixture*
    (injected fake source), not a real import → unaffected; line ~100 is a stale docstring naming the
    shim as a debt source → tidy it (T006).
- **The gates** (all in `tests/architectural/`): `test_no_dead_modules.py` holds
  `_CATEGORY_4_BACKCOMPAT_SHIMS`; `test_no_dead_symbols.py` holds `_CATEGORY_C_BACKCOMPAT_SHIM_REEXPORT`;
  `_baselines.yaml` holds the `category_4_backcompat_shims` count; `test_ratchet_baselines.py`
  cross-checks the declared count against the live frozenset size.

## Constraints (from spec.md / plan.md)

- **C-001**: After removal, the declared baseline MUST equal the live frozenset size (8). Recount before setting.
- **C-002**: Preserve the local test name by aliasing the private worker — `_resolve_mission_read_path as resolve_mission_read_path`. Do NOT re-promote the worker to public or add it to `__all__`.
- **C-003**: Do NOT modify files that import from the canonical resolver or only assert the symbol-name string.
- **C-004**: The `_baselines.yaml` edit MUST carry a `# justification:` comment (per that file's edit policy, lines 11–17).

## Subtasks

### T001 — Repoint the 7 shim imports in `test_coord_reader_fixes.py`

**Purpose**: Make the canonical seam the single entry point for the resolver under test, without
changing any test body.

**Steps**:
1. In `tests/specify_cli/cli/commands/test_coord_reader_fixes.py`, replace every
   `from specify_cli.mission_read_path import …` (7 sites, at lines ~26, ~42, ~58, ~76, ~97, ~108, ~118)
   with imports from `specify_cli.missions._read_path_resolver`, aliasing the private worker:
   - Single-symbol sites (`import resolve_mission_read_path`) become:
     ```python
     from specify_cli.missions._read_path_resolver import (
         _resolve_mission_read_path as resolve_mission_read_path,
     )
     ```
   - Multi-symbol sites that also import `StatusReadPathNotFound` become:
     ```python
     from specify_cli.missions._read_path_resolver import (
         StatusReadPathNotFound,
         _resolve_mission_read_path as resolve_mission_read_path,
     )
     ```
2. Leave the test bodies untouched — the alias preserves the call name `resolve_mission_read_path` and
   the 3-arg signature `(repo_root, mission_slug, mid8, *, require_exists=…)` matches exactly.

**Validation**:
- [ ] `grep -n "specify_cli.mission_read_path" tests/specify_cli/cli/commands/test_coord_reader_fixes.py` returns zero matches.
- [ ] The file's test count is unchanged.

### T002 — Delete the shim module

**Purpose**: Remove the dead module.

**Steps**:
1. `git rm src/specify_cli/mission_read_path.py` (or delete and stage).

**Validation**:
- [ ] `test ! -f src/specify_cli/mission_read_path.py`.
- [ ] `grep -rn "specify_cli.mission_read_path" src/` returns zero matches.

### T003 — Drop the dead-module allowlist entry

**Steps**:
1. In `tests/architectural/test_no_dead_modules.py`, remove the `"specify_cli.mission_read_path"`
   member from the `_CATEGORY_4_BACKCOMPAT_SHIMS` frozenset (around line ~282). Remove any
   now-orphaned trailing comment specific to that entry.

**Validation**:
- [ ] The entry is gone; the remaining 8 members are intact.

### T004 — Drop the dead-symbol allowlist entry

**Steps**:
1. In `tests/architectural/test_no_dead_symbols.py`, remove
   `"specify_cli.mission_read_path::resolve_mission_read_path"` from
   `_CATEGORY_C_BACKCOMPAT_SHIM_REEXPORT` (around line ~666). If that leaves the frozenset empty, keep
   it as an empty frozenset (do not delete the definition) unless the surrounding test logic clearly
   expects removal — verify the test still imports/uses it.

**Validation**:
- [ ] The entry is gone; `test_no_dead_symbols.py` still parses and runs.

### T005 — Decrement the baseline with justification

**Steps**:
1. In `tests/architectural/_baselines.yaml`, change `category_4_backcompat_shims: 9` to `8`.
2. Add a `# justification:` comment adjacent to the edit, e.g.:
   ```yaml
   # justification: #2048 retired dead shim specify_cli.mission_read_path (zero src callers,
   # last production importer re-pointed by 01KVJPEQ). Reverses the 01KVJPEQ 8->9 bump; restores
   # the SHRINK trend. Live _CATEGORY_4_BACKCOMPAT_SHIMS size is now 8.
   category_4_backcompat_shims: 8
   ```
3. Recount the live `_CATEGORY_4_BACKCOMPAT_SHIMS` frozenset to confirm it equals 8 (C-001).

**Validation**:
- [ ] Declared count (8) equals live frozenset size.
- [ ] `# justification:` comment present.

### T006 — Tidy the stale docstring

**Steps**:
1. In `tests/architectural/test_single_mission_surface_resolver.py` (~line 100), update the prose that
   names `specify_cli.mission_read_path` as a live `__all__`-symbol-debt source so it reflects the
   shim's removal (or drop the now-inaccurate clause). Do NOT touch the `snippet = "…"` string fixture
   lower in the file (it imports from the canonical resolver and is intentionally synthetic).

**Validation**:
- [ ] Docstring no longer asserts the shim is a current debt source.
- [ ] `test_single_mission_surface_resolver.py` still passes.

### T007 — Verify everything is green

**Steps**:
1. Run the gates and repointed tests:
   ```bash
   PWHEADLESS=1 pytest tests/architectural/test_no_dead_modules.py \
                       tests/architectural/test_no_dead_symbols.py \
                       tests/architectural/test_ratchet_baselines.py \
                       tests/specify_cli/cli/commands/test_coord_reader_fixes.py \
                       tests/architectural/test_single_mission_surface_resolver.py -q
   ```
2. Run the full architectural suite: `PWHEADLESS=1 pytest tests/architectural/ -q`.
3. Run lint/type gates: `ruff check .` and `mypy src/specify_cli`.
4. Confirm `grep -rn "specify_cli.mission_read_path" src/` is empty.
5. If `ruff`/`mypy` flags importing the private `_resolve_mission_read_path` in the test, see the
   risk note below before adding any suppression.

**Validation**:
- [ ] All listed test files pass; `category_4_backcompat_shims` resolves to 8.
- [ ] Full `tests/architectural/` suite green.
- [ ] `ruff` and `mypy` clean on the diff.
- [ ] `src/` grep returns zero matches.

## Branch Strategy

- **Planning base branch**: `feat/retire-mission-read-path-shim` (where planning artifacts were committed).
- **Final merge target**: `feat/retire-mission-read-path-shim`, which itself merges to `main` via a PR. Do not push to `origin/main` directly.
- Execution worktrees are allocated per computed lane from `lanes.json` (written by `finalize-tasks`). Enter the lane workspace that `spec-kitty agent action implement WP01` resolves — do not reconstruct the path by hand.

## Definition of Done

- `src/specify_cli/mission_read_path.py` deleted; zero `src/` references remain.
- The 7 importer sites in `test_coord_reader_fixes.py` resolve `resolve_mission_read_path` (aliased) and `StatusReadPathNotFound` from the canonical resolver; test bodies unchanged.
- Both allowlist entries removed; `category_4_backcompat_shims` baseline = 8 with a `# justification:` comment; live frozenset size = 8.
- Stale docstring tidied.
- `pytest tests/architectural/`, the repointed test file, `ruff`, and `mypy` are all green.

## Risks & Reviewer Guidance

- **Wrong import name (C-002)**: Reviewer — confirm the test imports `_resolve_mission_read_path as resolve_mission_read_path`, NOT a bare `resolve_mission_read_path` (which does not exist on the canonical module) and NOT a re-promotion of the worker into `__all__`.
- **Baseline off-by-one (C-001)**: Reviewer — confirm the declared 8 equals the live `_CATEGORY_4_BACKCOMPAT_SHIMS` size and that `test_ratchet_baselines.py` passes.
- **Scope creep (C-003)**: Reviewer — confirm `test_cli_status_mediation.py` and `test_issue_1615_1616_1617_1618.py` are NOT in the diff.
- **Private-member lint**: Importing `_resolve_mission_read_path` may trip a "private member accessed" rule. Only add a suppression if a real rule actually fires; keep it narrow with an inline rationale (the worker is intended for in-repo use — the shim was its only public face). Per charter, do not pre-emptively suppress.

## Activity Log

- 2026-06-25T16:00:16Z – claude:opus:randy-reducer:implementer – shell_pid=304688 – Assigned agent via action command
- 2026-06-25T16:17:10Z – claude:opus:randy-reducer:implementer – shell_pid=304688 – Shim retired; 7 imports repointed to canonical _read_path_resolver (aliased private worker _resolve_mission_read_path); both allowlist entries dropped; category_4_backcompat_shims 9->8 with justification; docstring tidied. Verification: src grep clean (zero matches); targeted gates 42 passed; full tests/architectural/ 494 passed with 1 pre-existing unrelated failure (test_pytest_marker_convention::test_support_helper_tree_is_exempt, fails identically on clean base); ruff exit 0.
- 2026-06-25T16:18:43Z – claude:opus:reviewer-renata:reviewer – shell_pid=328733 – Started review via action command
- 2026-06-25T16:23:11Z – user – shell_pid=328733 – Review passed: shim src/specify_cli/mission_read_path.py deleted (src grep empty); 7 import sites in test_coord_reader_fixes.py repointed to specify_cli.missions._read_path_resolver aliasing private worker _resolve_mission_read_path as resolve_mission_read_path (C-002 ok — no bare public symbol on canonical module, worker NOT in __all__, StatusReadPathNotFound imported directly as public, no re-promotion, test bodies unchanged); both architectural allowlist entries dropped; _baselines.yaml category_4_backcompat_shims 9->8 with # justification comment, declared 8 == live frozenset size 8 (C-001 ok); stale docstring tidied, snippet fixture untouched; no scope creep (test_cli_status_mediation.py and test_issue_1615_1616_1617_1618.py NOT in diff, only the 6 owned files changed); gates green: 42 passed, ruff exit 0; issue-matrix verdicts recorded (#2048 fixed by this WP, #2049 deferred-with-followup per spec Out of Scope).
