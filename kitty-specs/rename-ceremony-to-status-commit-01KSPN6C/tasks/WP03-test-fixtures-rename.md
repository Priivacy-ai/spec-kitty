---
work_package_id: WP03
title: Test Fixtures + Identifier Renames
dependencies: []
requirement_refs:
- FR-001
- FR-005
- FR-011
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
created_at: '2026-05-28T07:11:05Z'
subtasks:
- T008
- T009
- T010
- T011
- T012
- T013
- T014
phase: Phase 1 - Foundation
agent: claude
history:
- at: '2026-05-28T07:11:05Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/
execution_mode: code_change
owned_files:
- tests/e2e/conftest.py
- tests/doctrine/procedures/conftest.py
- tests/doctrine/procedures/test_models.py
- tests/architectural/_baselines.yaml
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP03 — Test Fixtures + Identifier Renames

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

Scope governance context to Python implementation before reading anything else. This WP renames Python identifiers across multiple test modules — load the Python-implementer profile so type-strict + lint + ruff conventions apply.

---

## Objective

Rename test identifiers, fixture IDs, branch literals, and a comment across 4 test files. Two sense-classifications apply:

- **Commit-class** (use `status commit` / `status_commit` / `STATUS_COMMIT` / `status-commit` depending on case): the e2e conftest constant + function + branch literal. These represent the protected-branch commit guard fixture.
- **Workflow-sense** (use `workflow`): the `mission-merge-ceremony` fixture ID — it represents the merge **workflow** procedure, not a commit class. The `_baselines.yaml` comment is also workflow-sense ("no ceremony" → "no extra workflow steps").

All Python identifier renames must propagate to all callers — mypy/import errors will surface stragglers.

## Context

- **Spec anchors**: [FR-001](../spec.md#functional-requirements), [FR-005](../spec.md#functional-requirements), [FR-011](../spec.md#functional-requirements).
- **Occurrence-map entries**: `cs-001` through `cs-004`, `sk-001` through `sk-003`, `tf-001` through `tf-003`. Each entry has file + line + replacement text — apply exactly.
- **Live state check**: `tests/git_ops/test_safe_commit_helper_integration.py` is already clean — do not modify. The issue body is stale for that file.

## Subtask Detail

### T008 — Rename `E2E_CEREMONY_BRANCH` constant + literal value

**File**: `tests/e2e/conftest.py` line 25

**Current**:

```python
E2E_CEREMONY_BRANCH = "e2e-ceremony"
```

**Replacement**:

```python
E2E_STATUS_COMMIT_BRANCH = "e2e-status-commit"
```

After this edit, grep across `tests/` for any importer using the old name:

```bash
grep -rn 'E2E_CEREMONY_BRANCH\|"e2e-ceremony"' tests/
```

Update every importer in the same commit. Any code that referenced the string `"e2e-ceremony"` (likely for branch creation or assertion) must use `"e2e-status-commit"`.

### T009 — Rename `_checkout_e2e_ceremony_branch` function + callers + docstrings

**File**: `tests/e2e/conftest.py`

**Line 214 — function definition**:

```python
def _checkout_e2e_ceremony_branch(project: Path) -> None:
```

→

```python
def _checkout_e2e_status_commit_branch(project: Path) -> None:
```

**Line 215 — function docstring**:

```python
    """Run ceremony-writing E2E workflows away from protected main/master."""
```

→

```python
    """Run status-commit-writing E2E workflows away from protected main/master."""
```

**Line 232 — docstring or comment** (verify exact phrasing at edit time; it currently reads "Checks out an E2E ceremony branch for workflow write operations"):

→

```
- Checks out an E2E status commit branch for workflow write operations
```

If the surrounding prose reads awkwardly after substitution, tighten to "Checks out an E2E status commit branch for status commit write operations" — match the surrounding voice.

**Line 324 — function call** + **Line 399 — function call**:

```python
    _checkout_e2e_ceremony_branch(project)
```

→

```python
    _checkout_e2e_status_commit_branch(project)
```

Grep `tests/` again after these edits for any remaining `ceremony` occurrence in callers outside `conftest.py`:

```bash
grep -rn '_checkout_e2e_ceremony_branch\|e2e_ceremony' tests/
```

### T010 — Rename `mission-merge-ceremony` fixture ID

**File**: `tests/doctrine/procedures/conftest.py` line 48

**Current**:

```python
        "id": "mission-merge-ceremony",
```

**Replacement** (workflow-sense per occurrence_map `sk-001`):

```python
        "id": "mission-merge-workflow",
```

### T011 — Update assertion paired with T010

**File**: `tests/doctrine/procedures/test_models.py` line 31

**Current**:

```python
        assert p.id == "mission-merge-ceremony"
```

**Replacement**:

```python
        assert p.id == "mission-merge-workflow"
```

T010 and T011 **must land together** — they reference the same fixture ID. If T010 lands without T011, the test fails.

### T012 — Rewrite `_baselines.yaml` comment

**File**: `tests/architectural/_baselines.yaml` line 17

**Current**:

```yaml
# - Shrinkage requires no ceremony (just edit the number).
```

**Replacement** (workflow-sense per occurrence_map `tf-003`):

```yaml
# - Shrinkage requires no extra workflow steps (just edit the number).
```

### T013 — Run targeted tests

From the lane workspace:

```bash
PWHEADLESS=1 pytest tests/e2e/ -v
PWHEADLESS=1 pytest tests/doctrine/procedures/ -v
PWHEADLESS=1 pytest tests/architectural/ -v
```

All must pass green. If any fail because of a missed caller, update the caller and re-run.

### T014 — Confirm zero stragglers in `tests/`

```bash
grep -rn 'ceremony' tests/ --include='*.py' --include='*.yaml'
```

Expected: **zero hits**. If any hit appears, classify per occurrence_map and update.

Note: this grep covers all of `tests/`, not only this WP's owned files. Other WPs do not touch `tests/`, so any stragglers here belong to this WP.

## Branch Strategy

- Planning base branch: `main`
- Final merge target: `main`
- Execution workspace: allocated per lane in `lanes.json` after `finalize-tasks`.
- Resolve via `spec-kitty agent context resolve --action implement --wp WP03 --mission rename-ceremony-to-status-commit-01KSPN6C --json`.

## Test Strategy

- Targeted pytest runs from T013 must pass.
- `mypy --strict tests/` passes (rename surfaces caller mismatches as type errors).
- `ruff check tests/` passes.
- WP06 regression guard will assert no `ceremony` substring remains in `tests/`.

## Definition of Done

- [ ] `tests/e2e/conftest.py` line 25 declares `E2E_STATUS_COMMIT_BRANCH = "e2e-status-commit"`.
- [ ] `tests/e2e/conftest.py` line 214 declares `def _checkout_e2e_status_commit_branch(project: Path) -> None:`.
- [ ] Lines 324 and 399 call the renamed function.
- [ ] Docstrings on lines 215 and 232 contain no "ceremony" substring.
- [ ] `tests/doctrine/procedures/conftest.py:48` fixture ID is `"mission-merge-workflow"`.
- [ ] `tests/doctrine/procedures/test_models.py:31` assertion matches `"mission-merge-workflow"`.
- [ ] `tests/architectural/_baselines.yaml:17` comment uses "no extra workflow steps".
- [ ] `grep -rn 'ceremony' tests/ --include='*.py' --include='*.yaml'` returns zero hits.
- [ ] `PWHEADLESS=1 pytest tests/e2e/ tests/doctrine/procedures/ tests/architectural/` passes.
- [ ] `mypy --strict tests/` and `ruff check tests/` pass.

## Risks & Reviewer Guidance

- **Risk 1**: A test module outside this WP's owned_files imports `E2E_CEREMONY_BRANCH`. Mitigation: grep + update in same commit. If the importer is owned by a different WP per the lane plan, surface as a conflict during review (likely shouldn't happen — grep at plan time showed no cross-tree importers).
- **Risk 2**: Docstring at line 232 reads awkwardly post-substitution. Mitigation: tighten the surrounding phrase as needed; the goal is canonical-term-consistent prose, not minimum-edit literalism.
- **Risk 3**: `mission-merge-ceremony` is referenced in a fixture data file (not Python source). Mitigation: T010+T011 cover both currently-known references; the T014 grep catches any others.
- **Reviewer check 1**: Diff touches only the 4 files in owned_files. Any other touched file is a scope violation.
- **Reviewer check 2**: Both halves of T010+T011 are in the same commit.
- **Reviewer check 3**: T014 grep returns zero hits.

## References

- Spec: [../spec.md](../spec.md) — FR-001, FR-005, FR-011
- Occurrence map: [../occurrence_map.yaml](../occurrence_map.yaml) — `cs-001..004`, `sk-001..003`, `tf-001..003`
- Term-rename contract: [../contracts/term-rename-contract.md](../contracts/term-rename-contract.md) — Rules R3, R4
