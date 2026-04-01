---
work_package_id: WP01
title: Data Models and Metadata Helper
dependencies: []
requirement_refs:
- FR-003
- FR-004
- FR-005
- FR-013
- FR-015
- FR-016
- FR-017
planning_base_branch: main
merge_target_branch: main
branch_strategy: Feature branch from main. No WP dependencies — can implement immediately.
subtasks: [T001, T002, T003, T004, T005, T006, T007]
history:
- date: '2026-04-01'
  action: created
  by: spec-kitty.tasks
authoritative_surface: src/specify_cli/tracker/
execution_mode: code_change
owned_files:
- src/specify_cli/tracker/origin.py
- tests/sync/tracker/test_origin_models.py
- tests/specify_cli/test_feature_metadata_origin.py
---

# WP01: Data Models and Metadata Helper

## Objective

Create the three origin dataclasses (`OriginCandidate`, `SearchOriginResult`, `MissionFromTicketResult`) in `src/specify_cli/tracker/origin.py` and add the `set_origin_ticket()` mutation helper to `src/specify_cli/feature_metadata.py`. Write tests for all of them.

This WP establishes the data foundation that all downstream WPs depend on.

## Branch Strategy

- **Planning base branch**: `main`
- **Merge target**: `main`
- **Implementation command**: `spec-kitty implement WP01`
- No dependencies — this WP can start immediately.

## Context

- **Spec**: `kitty-specs/061-ticket-first-mission-origin-binding/spec.md` — see "Candidate shape", "Result shape", "Local Metadata Shape"
- **Data model**: `kitty-specs/061-ticket-first-mission-origin-binding/data-model.md` — canonical field definitions
- **Plan**: `kitty-specs/061-ticket-first-mission-origin-binding/plan.md` — D1 (dataclass decision), constitution check

## Subtasks

### T001: Create `OriginCandidate` frozen dataclass

**Purpose**: Immutable value object representing one candidate external issue from search.

**File**: `src/specify_cli/tracker/origin.py` (new file)

**Implementation**:
```python
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any

@dataclass(frozen=True, slots=True)
class OriginCandidate:
    """A candidate external issue returned by ticket search."""
    external_issue_id: str
    external_issue_key: str
    title: str
    status: str
    url: str
    match_type: str  # "exact" or "text"
```

**Validation rules**:
- All fields are non-empty strings
- `match_type` must be `"exact"` or `"text"` (aligned with upstream contract)
- Frozen — instances are immutable after creation

### T002: Create `SearchOriginResult` frozen dataclass

**Purpose**: Structured result from `search_origin_candidates()` including candidates and routing context.

**File**: `src/specify_cli/tracker/origin.py`

```python
@dataclass(frozen=True, slots=True)
class SearchOriginResult:
    """Result of an origin candidate search."""
    candidates: list[OriginCandidate]
    provider: str       # "jira" or "linear"
    resource_type: str   # e.g., "linear_team", "jira_project"
    resource_id: str
    query_used: str
```

### T003: Create `MissionFromTicketResult` dataclass

**Purpose**: Result of `start_mission_from_ticket()` with created feature info + origin metadata.

**File**: `src/specify_cli/tracker/origin.py`

```python
@dataclass(slots=True)
class MissionFromTicketResult:
    """Result of creating a mission from an external ticket."""
    feature_dir: Path
    feature_slug: str
    origin_ticket: dict[str, str]
    event_emitted: bool
```

Not frozen because `Path` objects and the mutable nature of the result dict.

### T004: Add `set_origin_ticket()` mutation helper

**Purpose**: Persist the `origin_ticket` block in `meta.json` following the canonical mutation pattern.

**File**: `src/specify_cli/feature_metadata.py`

**Pattern to follow**: `set_documentation_state()` (line 279 in current code).

```python
def set_origin_ticket(
    feature_dir: Path,
    origin_ticket: dict[str, Any],
) -> dict[str, Any]:
    """Set or replace ``origin_ticket`` subtree in meta.json.

    The origin_ticket dict must contain all required keys:
    provider, resource_type, resource_id, external_issue_id,
    external_issue_key, external_issue_url, title.
    """
    meta = load_meta(feature_dir)
    if meta is None:
        raise FileNotFoundError(f"No meta.json in {feature_dir}")

    # Validate required keys
    required_keys = {
        "provider", "resource_type", "resource_id",
        "external_issue_id", "external_issue_key",
        "external_issue_url", "title",
    }
    missing = required_keys - set(origin_ticket.keys())
    if missing:
        raise ValueError(f"origin_ticket missing required keys: {sorted(missing)}")

    meta["origin_ticket"] = origin_ticket
    write_meta(feature_dir, meta)
    return meta
```

### T005: Add `origin_ticket` to `FeatureMetaOptional` TypedDict

**File**: `src/specify_cli/feature_metadata.py`

Add to the existing `FeatureMetaOptional` class:
```python
origin_ticket: dict[str, Any]
```

This is for static type checking documentation only — `write_meta` works with plain dicts.

### T006: Write tests for dataclass construction and validation

**File**: `tests/sync/tracker/test_origin_models.py` (new file)

**Test cases**:
- Construct `OriginCandidate` with all valid fields → succeeds
- `OriginCandidate` is frozen (assigning attribute raises `FrozenInstanceError`)
- Construct `SearchOriginResult` with empty candidates list → succeeds
- Construct `SearchOriginResult` with multiple candidates → order preserved
- Construct `MissionFromTicketResult` with Path and dict → succeeds
- `MissionFromTicketResult` is mutable (not frozen)

### T007: Write tests for `set_origin_ticket()`

**File**: `tests/specify_cli/test_feature_metadata_origin.py` (new file)

**Test cases**:
- Happy path: writes origin_ticket block, returns updated meta
- Preserves existing fields (feature_number, slug, etc. untouched)
- Missing meta.json raises `FileNotFoundError`
- Missing required keys raises `ValueError` with key names
- Overwrites existing origin_ticket (idempotent re-write)
- Written via `write_meta()` — file is valid JSON with sorted keys

**Fixture**: Use `tmp_path` with pre-seeded `meta.json` containing standard required fields.

## Definition of Done

- [ ] `OriginCandidate`, `SearchOriginResult`, `MissionFromTicketResult` defined in `tracker/origin.py`
- [ ] `set_origin_ticket()` implemented in `feature_metadata.py`
- [ ] `origin_ticket` added to `FeatureMetaOptional`
- [ ] All dataclass tests pass
- [ ] All metadata helper tests pass
- [ ] `mypy --strict` passes on new code
- [ ] `ruff check` passes

## Risks

- **Low**: Pure data structures with no external dependencies. Minimal risk.

## Reviewer Guidance

- Verify `OriginCandidate` is frozen (immutability contract)
- Verify `set_origin_ticket()` validates all 7 required keys
- Verify no SaaS database primary keys in the origin_ticket field set
- Check that `write_meta()` is called (not ad-hoc JSON writes)
