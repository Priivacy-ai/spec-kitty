# Data Model: WP Metadata & State Type Hardening

**Mission**: 065-wp-metadata-state-type-hardening  
**Date**: 2026-04-06

---

## New Types — All in `src/specify_cli/status/`

### `WPMetadata` (Pydantic model — `wp_metadata.py`)

```python
class WPMetadata(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="allow",           # Phase 1: allow unknown fields (backward compat)
        populate_by_name=True,   # Accept both alias and field name
    )

    # ── Required: identity ─────────────────────────────────────
    work_package_id: str                # Pattern: r"^WP\d{2,}$"
    title: str                          # min_length=1

    # ── Required: dependency graph ─────────────────────────────
    dependencies: list[str] = Field(default_factory=list)

    # ── Required: branch contract (post-implement, optional at planning) ──
    base_branch: str | None = None      # Git branch workspace created from
    base_commit: str | None = None      # Pattern: r"^[0-9a-f]{7,40}$"
    created_at: str | None = None       # ISO 8601

    # ── Optional: planning metadata ────────────────────────────
    planning_base_branch: str | None = None
    merge_target_branch: str | None = None
    branch_strategy: str | None = None
    requirement_refs: list[str] = Field(default_factory=list)

    # ── Optional: execution context ────────────────────────────
    execution_mode: str | None = None
    owned_files: list[str] = Field(default_factory=list)
    authoritative_surface: str | None = None

    # ── Optional: workflow metadata ────────────────────────────
    subtasks: list[Any] = Field(default_factory=list)
    phase: str | None = None
    assignee: str | None = None
    agent: str | None = None
    shell_pid: int | None = None
    history: list[Any] = Field(default_factory=list)

    # ── Optional: observed-in-practice fields (research.md Finding 5) ──
    mission_id: str | None = None
    wp_code: str | None = None
    branch_strategy_override: str | None = None
```

**Loader function** (`wp_metadata.py`):
```python
def read_wp_frontmatter(path: Path) -> tuple[WPMetadata, str]:
    """Load and validate WP frontmatter. Raises ValidationError on invalid data."""
    frontmatter_dict, body = FrontmatterManager().read(path)
    return WPMetadata.model_validate(frontmatter_dict), body
```

**Phase 2**: After all consumers migrated and all `kitty-specs/` WP files pass CI, change `extra="allow"` → `extra="forbid"`.

---

### `WPState` (ABC — `wp_state.py`)

```python
@dataclass(frozen=True)
class WPState(ABC):
    """Abstract base for lane-specific work package behaviour."""

    @property
    @abstractmethod
    def lane(self) -> Lane: ...

    @property
    def is_terminal(self) -> bool:
        return False

    @property
    def is_blocked(self) -> bool:
        return False

    @abstractmethod
    def allowed_targets(self) -> frozenset[Lane]: ...

    @abstractmethod
    def can_transition_to(self, target: Lane, ctx: TransitionContext) -> bool: ...

    def transition(self, target: Lane, ctx: TransitionContext) -> "WPState":
        """Return the new state after a validated transition."""
        if not self.can_transition_to(target, ctx):
            raise InvalidTransitionError(self.lane, target)
        return wp_state_for(target)

    @abstractmethod
    def progress_bucket(self) -> str:
        """One of: 'not_started', 'in_flight', 'review', 'terminal'."""
        ...

    @abstractmethod
    def display_category(self) -> str:
        """Kanban column label (e.g., 'Planned', 'In Progress', 'Done')."""
        ...
```

**Concrete classes** (one per canonical lane):

| Class | `lane` | `is_terminal` | `is_blocked` | `progress_bucket` | `display_category` |
|-------|--------|---------------|--------------|-------------------|--------------------|
| `PlannedState` | `planned` | False | False | `not_started` | `Planned` |
| `ClaimedState` | `claimed` | False | False | `in_flight` | `In Progress` |
| `InProgressState` | `in_progress` | False | False | `in_flight` | `In Progress` |
| `ForReviewState` | `for_review` | False | False | `review` | `Review` |
| `InReviewState` | `in_review` | False | False | `review` | `In Review` |
| `ApprovedState` | `approved` | False | False | `review` | `Review` |
| `DoneState` | `done` | True | False | `terminal` | `Done` |
| `BlockedState` | `blocked` | False | True | `in_flight` | `Blocked` |
| `CanceledState` | `canceled` | True | False | `terminal` | `Canceled` |

**Factory function**:
```python
def wp_state_for(lane: Lane | str) -> WPState:
    """Instantiate the correct concrete WPState for a given lane value."""
```

**Note on `doing` alias**: `LANE_ALIASES["doing"] = "in_progress"`. The `doing` alias is resolved at input boundaries (emit, CLI) before reaching `WPState`. No `DoingState` class is needed.

**Note on `in_review` promotion**: The former alias `LANE_ALIASES["in_review"] = "for_review"` is **removed**. `in_review` becomes a first-class lane (`Lane.IN_REVIEW`) with its own concrete state class. This resolves a concurrency blind spot: in parallel execution, multiple agents could not distinguish "awaiting review" (`for_review`) from "review actively in progress" (`in_review`). The `for_review` lane is now a pure queue state; `in_review` is the reviewer's active-work state, analogous to how `claimed` -> `in_progress` works for implementers. The `(for_review, in_review)` transition carries an actor-required guard with conflict detection, preventing two reviewers from claiming the same WP.

---

### `ReviewResult` (frozen dataclass — `transition_context.py`)

```python
@dataclass(frozen=True)
class ReviewResult:
    """Structured review outcome required for all outbound in_review transitions.

    Unifies the currently asymmetric approval (DoneEvidence.review: ReviewApproval)
    and rejection (review_ref: str) recording paths into a single typed contract.
    """

    reviewer: str                               # Who performed the review
    verdict: str                                # "approved" | "changes_requested"
    reference: str                              # Approval ref or feedback:// URI
    feedback_path: str | None = None            # Resolved path to feedback file (rejection only)
```

**Guard contract**: Every outbound transition from `in_review` requires a non-None `review_result` in the `TransitionContext`:
- `in_review` -> `approved` / `done`: `verdict` must be `"approved"`, `reviewer` and `reference` non-empty
- `in_review` -> `in_progress` / `planned`: `verdict` must be `"changes_requested"`, `reference` non-empty (typically a `feedback://` URI)

---

### `TransitionContext` (frozen dataclass — `transition_context.py`)

```python
@dataclass(frozen=True)
class TransitionContext:
    """All inputs needed for guard evaluation during a lane transition."""

    actor: str                                  # Who is requesting the transition
    workspace_context: str | None = None        # "worktree" | "direct" | None
    subtasks_complete: bool = False             # All subtasks checked off?
    evidence: DoneEvidence | None = None        # Required for → done
    review_ref: str | None = None               # Required for → for_review (legacy compat)
    review_result: ReviewResult | None = None   # Required for all in_review outbound transitions
    reason: str | None = None                   # Required for → blocked/canceled
    force: bool = False                         # Bypass terminal guard?
    implementation_evidence_present: bool = False  # For → for_review guard
```

**Migration note**: `review_ref` is preserved for backward compatibility with non-migrated consumers and the existing `for_review` -> `in_progress` path (which is removed from `ALLOWED_TRANSITIONS` but may still appear in force-override flows). New code should use `review_result` exclusively.

---

### Dashboard API Response Types (TypedDict — `dashboard/api_types.py`)

> #361 Phase 1: typed response contracts for dashboard JSON endpoints.

```python
class ArtifactInfo(TypedDict):
    exists: bool
    mtime: float | None
    size: int | None

class KanbanStats(TypedDict):
    total: int
    planned: int
    doing: int          # API-facing alias for in_progress (backward compat with dashboard consumers)
    for_review: int
    in_review: int      # New: added by this mission
    approved: int
    done: int
    # Note: blocked/canceled intentionally omitted — current dashboard does not surface these counts

class KanbanTaskData(TypedDict):
    id: str
    title: str
    lane: str
    subtasks: list[Any]
    agent: str
    phase: str
    prompt_path: str

class KanbanResponse(TypedDict):
    lanes: dict[str, list[KanbanTaskData]]
    is_legacy: bool
    upgrade_needed: bool

class HealthResponse(TypedDict):
    status: str
    project_path: str
    sync: dict[str, Any]

class ResearchResponse(TypedDict):
    main_file: str | None
    artifacts: list[dict[str, str]]

class ArtifactDirectoryResponse(TypedDict):
    files: list[dict[str, str]]
```

**Note**: `FeaturesListResponse` is the largest shape (~15 keys with nested objects).
Its definition will be finalized during WP08 implementation based on the post-migration
handler output. The types above cover the shapes most affected by WP04/WP06 migration.

---

## Changed Types

| Type | Location | Change in this mission |
|------|----------|----------------------|
| `Lane(StrEnum)` | `status/models.py:18` | Add `IN_REVIEW = "in_review"` member (9 lanes total) |
| `ALLOWED_TRANSITIONS` | `status/transitions.py:31` | Add 7 `in_review` outbound pairs; remove 4 `for_review` outbound pairs that move to `in_review` source; net +3 pairs. `for_review` retains only: `in_review`, `blocked`, `canceled` |
| `_GUARDED_TRANSITIONS` | `status/transitions.py:61` | Add `(for_review, in_review): "actor_required_with_conflict_check"`; move 4 entries from `for_review` source to `in_review` source |
| `LANE_ALIASES` | `status/transitions.py:24` | Remove `"in_review": "for_review"` (no longer an alias) |
| `CANONICAL_LANES` | `status/transitions.py:13` | Add `"in_review"` after `"for_review"` |

## Unchanged Types

| Type | Location | Change in this mission |
|------|----------|----------------------|
| `StatusEvent` | `status/models.py:137` | None — event log format frozen |
| `validate_transition()` | `status/transitions.py` | None — old API remains for non-migrated consumers |
| `FrontmatterManager` | `frontmatter.py` | Read signature unchanged; `read_wp_frontmatter()` wraps it |

---

## Module Layout After Mission

```
src/specify_cli/status/
├── __init__.py              (export WPMetadata, WPState, TransitionContext)
├── bootstrap.py             (unchanged)
├── emit.py                  (regex fix; WPState optional in transition path)
├── lane_reader.py           (unchanged)
├── models.py                (add Lane.IN_REVIEW member)
├── reducer.py               (unchanged)
├── store.py                 (unchanged)
├── transition_context.py    (NEW: TransitionContext dataclass)
├── transitions.py           (add in_review transitions; remove in_review alias; update CANONICAL_LANES)
├── validate.py              (unchanged)
├── wp_metadata.py           (NEW: WPMetadata model + read_wp_frontmatter())
└── wp_state.py              (NEW: WPState ABC + 9 concrete classes + factory)
```

```
src/specify_cli/dashboard/
├── ...                      (existing files unchanged)
├── api_types.py             (NEW: TypedDict response shapes for all JSON endpoints)
└── ...
```

```
tests/specify_cli/status/
├── (existing test files — unchanged structure)
├── test_wp_metadata.py      (NEW: WPMetadata validation, round-trip, consumers)
├── test_wp_state.py         (NEW: WPState concrete classes + property equivalence harness)
└── test_transition_context.py (NEW: TransitionContext construction)

tests/status/               (moved to new CI stage, no file changes)
```

```
tests/test_dashboard/
├── (existing test files — unchanged structure)
└── test_api_contract.py     (NEW: validates TypedDict keys match JS frontend usage)
```
