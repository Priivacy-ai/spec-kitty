# Data Model: 066 Review Loop Stabilization

**Mission**: 066-review-loop-stabilization
**Date**: 2026-04-06

## Overview

This mission introduces four new data structures and modifies two existing interfaces. All new models follow the existing codebase patterns: frozen dataclasses with `to_dict()` / `from_dict()` class methods, YAML frontmatter for markdown artifacts, and JSON for structured data.

---

## New Models

### 1. ReviewCycleArtifact

**Purpose**: Persisted review feedback for a single rejection cycle.
**Location on disk**: `kitty-specs/<mission>/tasks/<WP-slug>/review-cycle-{N}.md`
**Format**: Markdown with YAML frontmatter.

#### Frontmatter Schema

```yaml
---
cycle_number: 1
wp_id: WP01
mission_slug: "066-review-loop-stabilization"
reviewer_agent: "claude"
verdict: "rejected"               # "rejected" | "approved"
reviewed_at: "2026-04-06T12:00:00Z"
affected_files:
  - path: "src/specify_cli/cli/commands/agent/tasks.py"
    line_range: "245-265"
  - path: "src/specify_cli/cli/commands/agent/workflow.py"
    line_range: "652-662"
reproduction_command: "pytest tests/agent/test_review_feedback_pointer_2x_unit.py -x"
---
```

#### Body

Free-form markdown containing the reviewer's detailed feedback. No structural constraints on the body — it is for human and agent consumption.

#### Derivation Rules

- `cycle_number`: Count of existing `review-cycle-*.md` files in the WP sub-artifact directory, plus one.
- `affected_files`: Extracted from reviewer feedback. Each entry has `path` (relative to repo root) and optional `line_range` (format: `"start-end"`).
- `verdict`: Always `"rejected"` for review-cycle artifacts (an approved review does not create a review-cycle artifact — it transitions the WP to `done`).

#### Dataclass (for programmatic access)

```python
@dataclass(frozen=True)
class ReviewCycleArtifact:
    cycle_number: int
    wp_id: str
    mission_slug: str
    reviewer_agent: str
    verdict: str  # "rejected" | "approved"
    reviewed_at: str  # ISO 8601 UTC
    affected_files: list[AffectedFile]
    reproduction_command: str | None = None
    body: str = ""  # markdown body (not in frontmatter)

    def to_dict(self) -> dict[str, Any]: ...
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ReviewCycleArtifact: ...
    @classmethod
    def from_file(cls, path: Path) -> ReviewCycleArtifact: ...
    def write(self, path: Path) -> None: ...

@dataclass(frozen=True)
class AffectedFile:
    path: str           # relative to repo root
    line_range: str | None = None  # "start-end" or None
```

---

### 2. BaselineTestResult

**Purpose**: Cached baseline test results captured at WP claim time.
**Location on disk**: `kitty-specs/<mission>/tasks/<WP-slug>/baseline-tests.json`
**Format**: JSON (not markdown — this is structured data, not prose).

#### Schema

```json
{
  "wp_id": "WP01",
  "captured_at": "2026-04-06T10:00:00Z",
  "base_branch": "main",
  "base_commit": "abc1234",
  "test_runner": "pytest",
  "total": 487,
  "passed": 484,
  "failed": 3,
  "skipped": 0,
  "failures": [
    {
      "test": "test_legacy_import_path",
      "error": "ImportError: no module named 'old_name'",
      "file": "tests/test_compat.py:45"
    }
  ]
}
```

#### Size Constraint

- Only failure records are stored (test name + one-line error + file path).
- No raw stdout/stderr dumps.
- No passing test details.
- Expected size: < 10 KB for typical projects.

#### Dataclass

```python
@dataclass(frozen=True)
class BaselineTestResult:
    wp_id: str
    captured_at: str        # ISO 8601 UTC
    base_branch: str
    base_commit: str        # 7-40 hex chars
    test_runner: str        # "pytest", "unittest", "jest", etc.
    total: int
    passed: int
    failed: int
    skipped: int
    failures: list[TestFailure]

    def to_dict(self) -> dict[str, Any]: ...
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BaselineTestResult: ...
    @classmethod
    def load(cls, path: Path) -> BaselineTestResult | None: ...
    def save(self, path: Path) -> None: ...

@dataclass(frozen=True)
class TestFailure:
    test: str       # fully qualified test name
    error: str      # one-line error summary
    file: str       # file:line
```

---

### 3. ArbiterDecision

**Purpose**: Structured arbiter override rationale for false-positive review rejections.
**Location on disk**: Stored as a field within the review-cycle artifact's frontmatter (when an arbiter overrides), and persisted in the event log via the existing `review_ref` field.

#### Schema (as frontmatter extension on review-cycle artifact)

```yaml
---
# ... standard review-cycle fields ...
arbiter_override:
  arbiter: "robert"
  category: "pre_existing_failure"  # see categories below
  explanation: "Test test_legacy_import_path has been failing since commit abc123, predates this WP"
  checklist:
    is_pre_existing: true
    is_correct_context: true
    is_in_scope: true
    is_environmental: false
  decided_at: "2026-04-06T14:00:00Z"
---
```

#### Rationale Categories (extensible enum)

```python
class ArbiterCategory(StrEnum):
    PRE_EXISTING_FAILURE = "pre_existing_failure"
    WRONG_CONTEXT = "wrong_context"           # reviewer talking about wrong WP/mission
    CROSS_SCOPE = "cross_scope"               # finding is outside this WP's scope
    INFRA_ENVIRONMENTAL = "infra_environmental"  # test infra, CI, env issue
    CUSTOM = "custom"                         # requires mandatory explanation
```

#### Dataclass

```python
@dataclass(frozen=True)
class ArbiterDecision:
    arbiter: str
    category: ArbiterCategory
    explanation: str
    checklist: ArbiterChecklist
    decided_at: str  # ISO 8601 UTC

    def to_dict(self) -> dict[str, Any]: ...
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ArbiterDecision: ...

@dataclass(frozen=True)
class ArbiterChecklist:
    is_pre_existing: bool
    is_correct_context: bool
    is_in_scope: bool
    is_environmental: bool
```

---

### 4. ReviewLock (concurrent review serialization)

**Purpose**: Tracks active review sessions per worktree to prevent concurrent review collisions.
**Location on disk**: `.spec-kitty/review-lock.json` inside the worktree (git-ignored, ephemeral by design — this is runtime state, not a committed artifact).

#### Schema

```json
{
  "worktree_path": "/path/to/.worktrees/066-lane-a",
  "wp_id": "WP03",
  "agent": "gpt-5.4",
  "started_at": "2026-04-06T12:00:00Z",
  "pid": 12345
}
```

#### Behavior

- Created when `agent action review` starts.
- Deleted when review completes (move-task executed) or on process exit.
- A second `agent action review` in the same worktree checks for this lock:
  - If lock exists and PID is alive: block with actionable message.
  - If lock exists and PID is dead: stale lock, delete and proceed.

#### Dataclass

```python
@dataclass
class ReviewLock:
    worktree_path: str
    wp_id: str
    agent: str
    started_at: str  # ISO 8601 UTC
    pid: int

    def to_dict(self) -> dict[str, Any]: ...
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ReviewLock: ...
    @classmethod
    def load(cls, worktree: Path) -> ReviewLock | None: ...
    def save(self, worktree: Path) -> None: ...
    @staticmethod
    def release(worktree: Path) -> None: ...
    def is_stale(self) -> bool: ...  # check if PID is alive
```

---

## Modified Interfaces

### 5. _persist_review_feedback() — updated signature

**Current** (tasks.py:245-265): Writes to `.git/spec-kitty/feedback/`, returns `(Path, pointer_string)`.

**New**: Writes to `kitty-specs/<mission>/tasks/<WP-slug>/review-cycle-{N}.md`, returns `(Path, pointer_string)`.

```python
def _persist_review_feedback(
    *,
    main_repo_root: Path,
    mission_slug: str,
    task_id: str,
    feedback_source: Path,
    reviewer_agent: str,           # NEW: who reviewed
    affected_files: list[dict],    # NEW: structured affected files
) -> tuple[Path, str]:
    """Persist review feedback as a versioned review-cycle artifact.

    Returns (persisted_path, pointer_string).
    Pointer format changes from feedback:// to review-cycle:// for new artifacts.
    """
```

**Migration note**: The old `feedback://` pointer format is still resolved by `_resolve_review_feedback_pointer()` for backward compatibility (FR-016). New artifacts use a `review-cycle://` pointer format pointing to the kitty-specs location.

### 6. _resolve_review_feedback_pointer() — dual resolution

**Current** (workflow.py:87-100): Resolves only `feedback://` pointers to `.git/` paths.

**New**: Resolves both formats:
- `feedback://mission/task/filename` → `.git/spec-kitty/feedback/mission/task/filename` (legacy)
- `review-cycle://mission/task/review-cycle-N.md` → `kitty-specs/mission/tasks/task-slug/review-cycle-N.md` (new)

---

## Config Extensions

### .kittify/config.yaml — new optional sections

```yaml
# Existing sections unchanged
agents:
  available: [claude, opencode]

# NEW (WP05): opt-in concurrent review isolation
review:
  concurrent_isolation:
    strategy: "env_var"           # "env_var" or "serialized" (default)
    env_var: "DATABASE_URL"       # which env var to scope
    template: "postgresql://localhost:5432/test_{agent}_{wp_id}"  # naming template

  # NEW (WP04): custom test command for baseline capture
  # Default: pytest --junitxml=<tmpfile> (auto, no config needed)
  # Only configure if NOT using pytest:
  test_command: "cargo test -- --format json"
  test_output_format: "junit_xml"  # "junit_xml" (default) — parser used to extract structured results
```

**Concurrent isolation default behavior** (no config): serialization (ReviewLock).
**With config**: env-var scoping per review agent using the declared template.

**Baseline test default behavior** (no config): `pytest --junitxml=<tmpfile>`, parsed via `xml.etree.ElementTree`.
**With config**: custom `test_command` with specified output format. Non-pytest projects must configure explicitly — no auto-detection.

---

## Artifact Directory Layout

After all WPs are implemented, a WP's sub-artifact directory looks like:

```
kitty-specs/066-review-loop-stabilization/tasks/
├── WP01-persisted-review-artifact-model.md    # WP prompt file
├── WP01-persisted-review-artifact-model/      # sub-artifact directory
│   ├── review-cycle-1.md                      # first rejection feedback
│   ├── review-cycle-2.md                      # second rejection feedback
│   └── baseline-tests.json                    # baseline test results
├── WP02-focused-rejection-recovery.md
├── WP02-focused-rejection-recovery/
│   └── review-cycle-1.md
...
```

---

## State Transitions Affected

The review-cycle artifact model does not add new lanes to the status state machine. It adds structured data to existing transitions:

| Transition | Current behavior | New behavior |
|------------|-----------------|-------------|
| `for_review` → `planned` (rejection) | Writes feedback to `.git/`, sets `review_ref` to `feedback://` pointer | Writes review-cycle artifact to `kitty-specs/`, sets `review_ref` to `review-cycle://` pointer |
| `planned` → `claimed` (re-claim after rejection) | Shows feedback path in prompt | Generates fix-mode prompt from latest review-cycle artifact |
| `for_review` → `done` (approval) | Stores evidence in DoneEvidence | Unchanged |
| Arbiter override (forward `--force` from `planned` after rejection) | Sets `review_ref` to `"force-override"` | Sets `review_ref` to the existing `review-cycle://` pointer for the rejection's review-cycle artifact. Persists `ArbiterDecision` as a frontmatter extension on that same artifact. No new pointer scheme — the arbiter decision is metadata on the review-cycle artifact, not a separate resource. |
