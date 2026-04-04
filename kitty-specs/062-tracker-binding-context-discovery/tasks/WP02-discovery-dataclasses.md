---
work_package_id: WP02
title: Discovery Dataclasses
dependencies: []
requirement_refs:
- C-006
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: main
base_commit: 96092bf02f4651a8040ec14db7f743ef1f92912b
created_at: '2026-04-04T09:34:48.330445+00:00'
subtasks: [T006, T007, T008, T009, T010]
shell_pid: "44612"
agent: "codex"
history:
- date: '2026-04-04T09:10:15Z'
  action: created
  by: spec-kitty.tasks
authoritative_surface: src/specify_cli/tracker/
execution_mode: code_change
owned_files: [src/specify_cli/tracker/discovery.py, tests/sync/tracker/test_discovery.py]
---

# WP02: Discovery Dataclasses

## Objective

Create `src/specify_cli/tracker/discovery.py` — a new module containing pure data helpers for tracker binding discovery. This module owns dataclasses for API response parsing and a candidate lookup function. It does NOT import `rich`, `typer`, or any terminal I/O.

## Context

- **Spec**: Key Entities section (BindableResource, BindCandidate, BindResult, ValidationResult, candidate_token, binding_ref)
- **Plan**: Discovery Module layer in plan.md architecture; module boundary rule
- **Data Model**: All 5 new dataclasses defined in data-model.md
- **Contracts**: Response shapes in contracts/resources.md, bind-resolve.md, bind-confirm.md, bind-validate.md

## Implementation Command

```bash
spec-kitty implement WP02
```

No dependencies — this WP can start immediately.

## Subtasks

### T006: Create BindableResource + BindCandidate

**Purpose**: Dataclasses representing discovered tracker resources and bind candidates.

**Steps**:
1. Create `src/specify_cli/tracker/discovery.py`
2. Add imports: `from __future__ import annotations`, `from dataclasses import dataclass`, `from typing import Any`
3. Create `BindableResource`:
   ```python
   @dataclass(frozen=True, slots=True)
   class BindableResource:
       candidate_token: str
       display_label: str
       provider: str
       provider_context: dict[str, str]
       binding_ref: str | None = None
       bound_project_slug: str | None = None
       bound_at: str | None = None

       @property
       def is_bound(self) -> bool:
           return self.binding_ref is not None

       @classmethod
       def from_api(cls, data: dict[str, Any]) -> BindableResource:
           return cls(
               candidate_token=data["candidate_token"],
               display_label=data["display_label"],
               provider=data["provider"],
               provider_context=data.get("provider_context", {}),
               binding_ref=data.get("binding_ref"),
               bound_project_slug=data.get("bound_project_slug"),
               bound_at=data.get("bound_at"),
           )
   ```
4. Create `BindCandidate`:
   ```python
   @dataclass(frozen=True, slots=True)
   class BindCandidate:
       candidate_token: str
       display_label: str
       confidence: str  # "high", "medium", "low"
       match_reason: str
       sort_position: int

       @classmethod
       def from_api(cls, data: dict[str, Any]) -> BindCandidate:
           return cls(
               candidate_token=data["candidate_token"],
               display_label=data["display_label"],
               confidence=data["confidence"],
               match_reason=data["match_reason"],
               sort_position=data["sort_position"],
           )
   ```

**Files**: `src/specify_cli/tracker/discovery.py` (new)

### T007: Create BindResult + ValidationResult + ResolutionResult

**Purpose**: Dataclasses for bind-confirm, bind-validate, and bind-resolve responses.

**Steps**:
1. Add `BindResult`:
   ```python
   @dataclass(frozen=True, slots=True)
   class BindResult:
       binding_ref: str
       display_label: str
       provider: str
       provider_context: dict[str, str]
       bound_at: str

       @classmethod
       def from_api(cls, data: dict[str, Any]) -> BindResult:
           return cls(
               binding_ref=data["binding_ref"],
               display_label=data["display_label"],
               provider=data["provider"],
               provider_context=data.get("provider_context", {}),
               bound_at=data["bound_at"],
           )
   ```
2. Add `ValidationResult`:
   ```python
   @dataclass(frozen=True, slots=True)
   class ValidationResult:
       valid: bool
       binding_ref: str
       reason: str | None = None
       guidance: str | None = None
       display_label: str | None = None
       provider: str | None = None
       provider_context: dict[str, str] | None = None

       @classmethod
       def from_api(cls, data: dict[str, Any]) -> ValidationResult:
           return cls(
               valid=data["valid"],
               binding_ref=data["binding_ref"],
               reason=data.get("reason"),
               guidance=data.get("guidance"),
               display_label=data.get("display_label"),
               provider=data.get("provider"),
               provider_context=data.get("provider_context"),
           )
   ```
3. Add `ResolutionResult`:
   ```python
   @dataclass(frozen=True, slots=True)
   class ResolutionResult:
       match_type: str  # "exact", "candidates", "none"
       candidate_token: str | None = None
       binding_ref: str | None = None
       display_label: str | None = None
       candidates: list[BindCandidate] = field(default_factory=list)

       @classmethod
       def from_api(cls, data: dict[str, Any]) -> ResolutionResult:
           candidates = [BindCandidate.from_api(c) for c in data.get("candidates", [])]
           return cls(
               match_type=data["match_type"],
               candidate_token=data.get("candidate_token"),
               binding_ref=data.get("binding_ref"),
               display_label=data.get("display_label"),
               candidates=candidates,
           )
   ```

**Files**: `src/specify_cli/tracker/discovery.py`

### T008: Add find_candidate_by_position() Helper

**Purpose**: Pure function to look up a candidate by `--select N` (1-based user input maps to sort_position = N-1).

**Steps**:
1. Add function:
   ```python
   def find_candidate_by_position(
       candidates: list[BindCandidate], select_n: int
   ) -> BindCandidate | None:
       """Find candidate by 1-based selection number (maps to sort_position = N-1).
       Returns None if out of range or candidates is empty."""
       position = select_n - 1
       for candidate in candidates:
           if candidate.sort_position == position:
               return candidate
       return None
   ```

**Files**: `src/specify_cli/tracker/discovery.py`

### T009: Write from_api() Tests

**Purpose**: Verify all dataclass factories parse valid, partial, and malformed API data.

**Steps**:
1. Create `tests/sync/tracker/test_discovery.py`
2. For each dataclass, test:
   - Valid full response → all fields populated
   - Minimal response (optional fields missing) → defaults applied
   - Missing required field → KeyError raised
3. For `ResolutionResult.from_api`, test nested candidate parsing

**Files**: `tests/sync/tracker/test_discovery.py` (new)

### T010: Write find_candidate Tests

**Purpose**: Verify candidate lookup for valid, out-of-range, and empty inputs.

**Steps**:
1. Add to `tests/sync/tracker/test_discovery.py`:
   - `test_find_candidate_valid`: select_n=1 returns sort_position=0
   - `test_find_candidate_second`: select_n=2 returns sort_position=1
   - `test_find_candidate_out_of_range`: select_n=99 returns None
   - `test_find_candidate_zero`: select_n=0 returns None (no sort_position=-1)
   - `test_find_candidate_empty_list`: empty candidates returns None

**Files**: `tests/sync/tracker/test_discovery.py`

## Definition of Done

- [ ] `src/specify_cli/tracker/discovery.py` exists with 5 dataclasses + 1 helper function
- [ ] No imports of `rich`, `typer`, or any I/O libraries
- [ ] All dataclasses are `frozen=True, slots=True`
- [ ] All `from_api()` methods parse contract response shapes correctly
- [ ] All tests pass: `python -m pytest tests/sync/tracker/test_discovery.py -x -q`
- [ ] `ruff check src/specify_cli/tracker/discovery.py`
- [ ] `mypy src/specify_cli/tracker/discovery.py`

## Risks

- **`frozen=True` with `field(default_factory=list)`**: Works in Python 3.11+. ResolutionResult uses it for `candidates`. No risk.

## Reviewer Guidance

- Verify no I/O imports in discovery.py (grep for `rich`, `typer`, `print`, `input`)
- Check that `from_api()` factories match the contract shapes in `contracts/` directory
- Verify `find_candidate_by_position` is 1-based (user types 1, maps to sort_position=0)

## Activity Log

- 2026-04-04T09:34:48Z – coordinator – shell_pid=32788 – Started implementation via workflow command
- 2026-04-04T09:37:48Z – coordinator – shell_pid=32788 – Ready for review: 5 dataclasses + find_candidate_by_position helper, 22 tests all passing, ruff clean
- 2026-04-04T09:38:28Z – codex – shell_pid=44612 – Started review via workflow command
- 2026-04-04T09:44:22Z – codex – shell_pid=44612 – Review passed: discovery dataclasses/helper match contracts; 22 tests passed; ruff clean
