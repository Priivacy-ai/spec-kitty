---
work_package_id: WP01
title: Registry extension and Pydantic resource models
dependencies: []
requirement_refs:
- FR-006
- FR-007
- FR-008
planning_base_branch: feature/650-dashboard-ui-ux-overhaul
merge_target_branch: feature/650-dashboard-ui-ux-overhaul
branch_strategy: Planning artifacts for this feature were generated on feature/650-dashboard-ui-ux-overhaul. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/650-dashboard-ui-ux-overhaul unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
agent: claude
history: []
agent_profile: python-pedro
authoritative_surface: src/dashboard/
execution_mode: code_change
model: claude-sonnet-4-6
owned_files:
- src/dashboard/services/registry.py
- src/dashboard/api/models.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else in this prompt, run:

```
/ad-hoc-profile-load python-pedro
```

This initialises your identity, governance scope, and implementation style for this work package.

---

## Objective

Extend `WorkPackageRecord` with two new fields that `WorkPackageAssignment` requires (`claimed_at`, `blocked_reason`), update the scan logic to populate them, and define all seven new Pydantic v2 response models in `src/dashboard/api/models.py`. After this WP, `tests/architectural/test_resource_models_have_links.py` must transition from vacuous to enforcing (≥5 `ResourceModel` subclasses detected).

## Branch Strategy

- **Planning base branch**: `feature/650-dashboard-ui-ux-overhaul`
- **Merge target**: `feature/650-dashboard-ui-ux-overhaul`
- Execution workspace allocated by `spec-kitty implement WP01 --agent claude`.
- No dependencies — this WP starts from the current HEAD of `feature/650-dashboard-ui-ux-overhaul`.

## Context

**Registry layer** (`src/dashboard/services/registry.py`):
- `WorkPackageRecord` is a frozen dataclass at line ~94. It already has `last_event_id`, `last_event_at`, `lane`, `assignee`, `agent_profile`, `role`.
- `WorkPackageRegistry.list_work_packages()` (line ~441) drives the per-WP scan; it reads `kitty-specs/<slug>/tasks/WP*.md` for metadata and `status.events.jsonl` for lane state.
- The registry reads `status.events.jsonl` to derive `lane` and `last_event_id`. Extend this read to also capture the most recent `→ claimed` event's `at` timestamp and the most recent `→ blocked` event's `reason` field.

**Models layer** (`src/dashboard/api/models.py`):
- `ResourceModel` base class at lines ~411–430 (added by mission 112). It declares `_links: dict[str, Link]` using Pydantic v2 field aliasing. New models inherit from it.
- `_DashboardModel(BaseModel)` is the base for all pre-existing models; do not change existing models.
- `Link` (lines ~399–410): `href: str`.
- `LaneCounts` (pre-existing): lane-keyed int counts.

**Arch test**: `tests/architectural/test_resource_models_have_links.py` — currently vacuous (no `ResourceModel` subclasses). After this WP it must detect ≥5 subclasses and verify each declares `_links`.

## Implementation Guide

### T001 — Extend WorkPackageRecord

**File**: `src/dashboard/services/registry.py`

Add two fields to `WorkPackageRecord` (frozen dataclass):

```python
@dataclass(frozen=True)
class WorkPackageRecord:
    # ... existing fields ...
    claimed_at: datetime | None      # NEW — timestamp of most recent →claimed event
    blocked_reason: str | None       # NEW — reason from most recent →blocked event
```

Add the fields after `last_event_at` to maintain a logical grouping. Use `None` as the default — do NOT give them default values in the dataclass signature (frozen dataclasses require all fields without defaults before fields with defaults; if existing fields have no defaults, this is safe). If existing fields already have defaults, place the new fields accordingly.

**Backward-compat note**: Any test that constructs `WorkPackageRecord(...)` directly using positional arguments will break. Grep for `WorkPackageRecord(` in `tests/` and update each call to pass the new fields as keyword arguments with `claimed_at=None, blocked_reason=None`.

---

### T002 — Update WorkPackageRegistry scan

**File**: `src/dashboard/services/registry.py`

Inside the method that reads `status.events.jsonl` per WP (look for the JSONL read inside `WorkPackageRegistry`), add extraction of:

- `claimed_at`: iterate events in chronological order; track the most recent event where `event["to_lane"] == "claimed"`; capture `event["at"]` as a `datetime`.
- `blocked_reason`: same approach for `event["to_lane"] == "blocked"`; capture `event.get("reason")`.

Both should default to `None` if the JSONL is absent or no matching event exists. Parse the `at` field using `datetime.fromisoformat(event["at"])` — consistent with existing event parsing in the file.

Pass `claimed_at=claimed_at, blocked_reason=blocked_reason` when constructing `WorkPackageRecord`.

**Edge cases**:
- Missing JSONL (legacy mission): both fields stay `None` — same pattern as `last_event_id`.
- Event log with no `claimed` events: `claimed_at = None`.
- Event log with multiple `claimed` events (re-claim after rejection): use the most recent one.

---

### T003 — ReviewEvidence and WorkPackageAssignment

**File**: `src/dashboard/api/models.py`

Add after the existing `ResourceModel` block (around line 430):

```python
class ReviewEvidence(BaseModel):
    """Evidence from a review event (in_review → approved/rejected)."""
    reviewed_by: str
    reviewed_at: datetime
    verdict: Literal["approved", "rejected"]
    notes: str | None = None


class WorkPackageAssignment(BaseModel):
    """Ownership contract for a single WP."""
    wp_id: str
    lane: str
    assignee: str | None = None
    agent_profile: str | None = None
    role: str | None = None
    claimed_at: datetime | None = None
    last_event_id: str | None = None
    blocked_reason: str | None = None
    review_evidence: ReviewEvidence | None = None
```

Import `Literal` from `typing` (or `typing_extensions` if Python 3.11+; use `typing.Literal` directly). Import `datetime` from `datetime` at the top of the file if not already present.

Add both to `__all__`.

---

### T004 — MissionSummary and Mission models

**File**: `src/dashboard/api/models.py`

```python
class MissionSummary(ResourceModel):
    """Lightweight mission representation for list responses."""
    mission_id: str
    mission_slug: str
    mission_number: int | None = None
    mid8: str
    friendly_name: str
    mission_type: str
    target_branch: str
    lane_counts: LaneCounts
    weighted_percentage: float | None = None
    is_legacy: bool = False
    # _links inherited from ResourceModel: keys = self, status, workpackages


class Mission(ResourceModel):
    """Full mission detail representation."""
    mission_id: str
    mission_slug: str
    mission_number: int | None = None
    mid8: str
    friendly_name: str
    mission_type: str
    target_branch: str
    created_at: datetime | None = None
    lane_counts: LaneCounts
    weighted_percentage: float | None = None
    is_legacy: bool = False
    # _links inherited: keys = self, status, workpackages
```

Add both to `__all__`.

---

### T005 — MissionStatus model

**File**: `src/dashboard/api/models.py`

```python
class MissionStatus(ResourceModel):
    """Lane counts and progress for a single mission — polling-friendly."""
    mission_id: str
    lane_counts: LaneCounts
    weighted_percentage: float | None = None
    done_count: int
    total_count: int
    current_phase: int = 2
    # _links inherited: keys = self, mission
```

Add to `__all__`.

---

### T006 — WorkPackageSummary, WorkPackage, and arch test

**File**: `src/dashboard/api/models.py`

```python
class WorkPackageSummary(ResourceModel):
    """Lightweight WP representation for list responses."""
    wp_id: str
    title: str
    assignment: WorkPackageAssignment
    # _links inherited: keys = self, mission


class WorkPackage(ResourceModel):
    """Full WP detail representation."""
    wp_id: str
    title: str
    assignment: WorkPackageAssignment
    subtasks_done: int
    subtasks_total: int
    dependencies: list[str]
    requirement_refs: list[str]
    prompt_ref: str | None = None
    # _links inherited: keys = self, mission, workpackages
```

Add both to `__all__`.

**Arch test verification**:
```bash
.venv/bin/python -m pytest tests/architectural/test_resource_models_have_links.py -v
```
The test must report ≥5 `ResourceModel` subclasses verified and exit 0. If it is still reporting "vacuous" or skipping, read the test file to understand its detection logic and ensure the new models are importable from `dashboard.api.models`.

## Definition of Done

- [ ] `WorkPackageRecord` has `claimed_at` and `blocked_reason` fields.
- [ ] Registry scan populates the new fields from `status.events.jsonl`.
- [ ] All 7 new Pydantic models defined and exported from `models.py`.
- [ ] All 5 `ResourceModel` subclasses declare `_links: dict[str, Link]`.
- [ ] `pytest tests/architectural/test_resource_models_have_links.py -v` passes and is non-vacuous.
- [ ] `pytest tests/test_dashboard/ -q` exits 0 (no regressions).
- [ ] Zero new `# type: ignore` directives added.

## Risks

- **Frozen dataclass field ordering**: If existing `WorkPackageRecord` fields have no defaults, the new `| None` fields must come last (Python requires non-default fields before default fields). Inspect the dataclass carefully before adding.
- **Test breakage from positional construction**: Tests that construct `WorkPackageRecord` with positional arguments will fail. Grep and fix.
- **`_links` field visibility in Pydantic v2**: The `ResourceModel` base uses `Field(alias="_links")`. Verify that subclasses inherit this correctly and that `model.model_dump(by_alias=True)` includes `_links` in output. Run a quick smoke test: `MissionSummary(mission_id="x", ..., **{"_links": {}}).model_dump(by_alias=True)`.
