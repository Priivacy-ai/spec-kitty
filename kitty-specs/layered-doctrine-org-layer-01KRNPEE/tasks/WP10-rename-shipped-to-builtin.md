---
work_package_id: WP10
title: Rename shipped doctrine directories to built-in
dependencies:
- WP03
requirement_refs:
- FR-001
- FR-002
planning_base_branch: feat/org-doctrine-layer
merge_target_branch: feat/org-doctrine-layer
branch_strategy: Planning artifacts for this mission were generated on feat/org-doctrine-layer. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/org-doctrine-layer unless the human explicitly redirects the landing branch.
subtasks:
- T051
- T052
- T053
agent: "codex:gpt-4o:reviewer-renata:reviewer"
shell_pid: "694504"
history:
- date: '2026-05-15'
  event: created
agent_profile: python-pedro
authoritative_surface: src/doctrine/directives/built-in/
execution_mode: code_change
owned_files:
- src/doctrine/directives/built-in/**
- src/doctrine/tactics/built-in/**
- src/doctrine/styleguides/built-in/**
- src/doctrine/toolguides/built-in/**
- src/doctrine/paradigms/built-in/**
- src/doctrine/procedures/built-in/**
- src/doctrine/agent_profiles/built-in/**
- src/doctrine/mission_step_contracts/built-in/**
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

---

## Objective

Rename every `shipped/` subdirectory under `src/doctrine/` to `built-in/`, and update
`DoctrineService._shipped_dir()` (and related internal naming) to construct the correct
`built-in/` path. This completes the terminology alignment with the spec (`"builtin"`
provenance tag) and the domain language table ("spec-kitty built-in" pack).

---

## Context

The spec's Domain Language table defines the built-in layer as **"spec-kitty built-in"**
(machine-readable tag: `"builtin"`). WP02 already writes `"builtin"` as the provenance tag.
The remaining gap is that the actual filesystem directories are still named `shipped/` and
`DoctrineService._shipped_dir()` still constructs paths with `/ "shipped"`.

This WP closes that gap. It is a rename-only change — no behavior changes, no new logic.

---

## Branch Strategy

- **Planning/base branch**: `feat/org-doctrine-layer`
- **Merge target**: `feat/org-doctrine-layer`
- **Implement command**: `spec-kitty agent action implement WP10 --agent claude:sonnet-4-6`

---

## Subtask T051 — Rename all `shipped/` subdirectories to `built-in/`

**Directories to rename** (use `git mv` so git tracks the rename):

```bash
for artifact in directives tactics styleguides toolguides paradigms procedures agent_profiles mission_step_contracts; do
  git mv "src/doctrine/${artifact}/shipped" "src/doctrine/${artifact}/built-in"
done
```

Verify the renames are staged:
```bash
git status | grep renamed
```

Expect 8 directory renames.

---

## Subtask T052 — Update `DoctrineService._shipped_dir()` and related internals

**File**: `src/doctrine/service.py`

**T052a — Update `_shipped_dir()` return path:**

Find:
```python
def _shipped_dir(self, artifact: str) -> Path | None:
    if self._shipped_root is None:
        return None
    return self._shipped_root / artifact / "shipped"
```

Replace with:
```python
def _shipped_dir(self, artifact: str) -> Path | None:
    if self._shipped_root is None:
        return None
    return self._shipped_root / artifact / "built-in"
```

**T052b — Optionally rename internal variable and parameter names** to eliminate the
remaining `shipped` terminology. This is optional but recommended for full consistency.
Rename in `service.py` only (not in external call sites — those use keyword args):

- `shipped_root` parameter → `builtin_root`
- `self._shipped_root` → `self._builtin_root`
- `_shipped_dir()` method → `_builtin_dir()`

If renaming, update all usages within `service.py`. Do NOT change the external interface
yet — call sites that pass `shipped_root=...` will need updating in a follow-up if the
parameter is renamed. **If this creates too much churn, skip T052b and only do T052a.**

---

## Subtask T053 — Update docstrings and test fixtures

**Grep for remaining `shipped` references that need updating:**

```bash
grep -rn '"shipped"\|/shipped\b\|shipped/' \
  src/doctrine/ tests/doctrine/ \
  | grep -v ".pyc\|__pycache__\|\.git" \
  | grep -v "# shipped\|#shipped"  # ignore comments that are already updated
```

For each hit:
- If it constructs a `shipped/` path that now should be `built-in/`: update to `built-in/`.
- If it's a docstring referring to the `shipped/` directory: update the wording.
- If it's a test fixture that creates a `shipped/` directory: rename to `built-in/`.

Common test fixture pattern to update:
```python
# Before:
shipped_dir = tmp_path / "directives" / "shipped"
shipped_dir.mkdir(parents=True)

# After:
builtin_dir = tmp_path / "directives" / "built-in"
builtin_dir.mkdir(parents=True)
```

---

## Verification

```bash
# No remaining /shipped path constructions in source (excluding git history):
grep -rn '/ "shipped"\|/"shipped"\|/shipped/' src/doctrine/ | grep -v ".pyc"
# Expected: empty

# All existing tests still pass:
python -m pytest tests/doctrine/ -q 2>&1 | tail -10

# Spot-check that DoctrineService still resolves the shipped graph:
python -c "
from pathlib import Path
from doctrine.service import DoctrineService
from charter.catalog import resolve_doctrine_root
root = resolve_doctrine_root()
svc = DoctrineService(shipped_root=root)
print('directives:', len(svc.directives.list_all()))
print('tactics:', len(svc.tactics.list_all()))
"
```

---

## Commit and handoff

```bash
git add src/doctrine/
git commit -m "feat(WP10): rename shipped/ doctrine directories to built-in/; update DoctrineService path"

cd /home/stijn/Documents/_code/CLIENTS/regnology/forks/spec-kitty
spec-kitty agent tasks mark-status T051 T052 T053 --status done --mission layered-doctrine-org-layer-01KRNPEE
spec-kitty agent tasks move-task WP10 --to for_review --mission layered-doctrine-org-layer-01KRNPEE --note "shipped/ → built-in/ rename complete; DoctrineService path updated; all doctrine tests passing"
```

---

## Definition of Done

- [ ] All 8 `src/doctrine/*/shipped/` directories renamed to `src/doctrine/*/built-in/`
- [ ] `DoctrineService._shipped_dir()` returns `artifact / "built-in"` not `artifact / "shipped"`
- [ ] No `/ "shipped"` path construction remains in `src/doctrine/`
- [ ] All existing doctrine tests pass unchanged
- [ ] `DoctrineService` still resolves the built-in artifact set correctly (spot-check above)

## Risks

- `git mv` on directories with many files: verify all 8 renames land correctly in git status
  before committing.
- Test fixtures that hardcode `"shipped"` as a directory name: the grep in T053 will surface
  these; fix them before running tests.
- If `_shipped_dir` is called from outside `service.py` (check with grep): those call sites
  need updating if the method is renamed. Skip the method rename (T052b) if it creates
  too much churn.

## Reviewer Guidance

1. Confirm `git log --stat HEAD` shows directory renames, not deletes+adds.
2. Run the spot-check to confirm `DoctrineService` resolves artifacts from the renamed dirs.
3. Confirm no `shipped/` directory remains anywhere under `src/doctrine/`.

## Activity Log

- 2026-05-15T14:33:34Z – claude:opus-4-7:python-pedro:implementer – shell_pid=663493 – Started implementation via action command
- 2026-05-15T14:50:41Z – claude:opus-4-7:python-pedro:implementer – shell_pid=663493 – Renamed all 8 src/doctrine/<artifact>/shipped/ dirs to built-in/ via git mv (196 file renames, balanced 289+/289- diff). Updated DoctrineService._shipped_dir() and all 8 repository._default_shipped_dir() paths. Cascaded path-literal updates across YAML data (guide_path, references arrays in toolguides/styleguides), neutrality allowlist, charter catalog/compiler, pack_validator, agent/tasks _get_hic_marker, mission-runtime comments, extractor.py, and ~40 test files. Integration check: DoctrineService loads 17 directives, 92 tactics, 8 styleguides, 10 toolguides, 8 paradigms, 13 procedures, 14 agent profiles, 16 mission step contracts from built-in/. All doctrine/charter/architectural/specify_cli tests pass except pre-existing neutrality lint failure on secure-regex tactic (b134bac5).
- 2026-05-15T14:51:17Z – codex:gpt-4o:reviewer-renata:reviewer – shell_pid=694504 – Started review via action command
- 2026-05-15T14:54:27Z – codex:gpt-4o:reviewer-renata:reviewer – shell_pid=694504 – Review passed: 8/8 dirs renamed shipped→built-in, 196 git renames detected,_shipped_dir() returns built-in path, DoctrineService loads positive artifact counts across all 8 artifact types (17 directives, 92 tactics, 8 styleguides, 10 toolguides, 8 paradigms, 13 procedures, 14 agent profiles, 16 mission step contracts), all tests green (doctrine 1604, charter 746, specify_cli/doctrine 72, architectural/layer-rules 8). Remaining 'shipped' references are user-facing advisory prose (resolver.py error strings) and pre-existing CLI source label in profiles_cmd.py — both fall under the reviewer-brief allowed exclusions and the implementer's explicit out-of-scope list._shipped_root API name and shipped_dir kwarg preserved as documented.
- 2026-05-16T04:29:44Z – codex:gpt-4o:reviewer-renata:reviewer – shell_pid=694504 – Done override: Mission merged via squash commit 9c2c26a0 to feat/org-doctrine-layer
