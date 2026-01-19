# Data Model: Orchestrator End-to-End Testing Suite

## Overview

This document defines the entities used in the orchestrator end-to-end testing infrastructure. These entities support fixture management, agent availability detection, and test path selection.

## Entities

### AgentAvailability

Detection result for a single agent, including installation and authentication status.

```python
from dataclasses import dataclass
from typing import Literal

@dataclass
class AgentAvailability:
    """Result of detecting an agent's availability for testing."""

    agent_id: str
    """Canonical agent identifier (e.g., 'claude', 'codex', 'gemini')."""

    is_installed: bool
    """True if the agent CLI binary exists and is executable."""

    is_authenticated: bool
    """True if the agent responded to a probe API call."""

    tier: Literal["core", "extended"]
    """Agent tier: 'core' (fail if unavailable) or 'extended' (skip if unavailable)."""

    failure_reason: str | None
    """Human-readable reason if is_installed or is_authenticated is False."""

    probe_duration_ms: int | None
    """Time taken for auth probe in milliseconds (None if not probed)."""
```

**Core tier agents**: `claude`, `codex`, `copilot`, `gemini`, `opencode`

**Extended tier agents**: `cursor`, `qwen`, `augment`, `kilocode`, `roo`, `windsurf`, `amazonq`

### FixtureCheckpoint

A snapshot of orchestration state at a known point in the workflow.

```python
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

@dataclass
class FixtureCheckpoint:
    """A restorable snapshot of orchestration state."""

    name: str
    """Checkpoint identifier (e.g., 'wp_created', 'review_pending')."""

    path: Path
    """Absolute path to the checkpoint directory."""

    orchestrator_version: str
    """Version of spec-kitty that created this checkpoint."""

    created_at: datetime
    """When this checkpoint was created."""

    state_file: Path
    """Path to state.json within checkpoint."""

    feature_dir: Path
    """Path to feature/ directory within checkpoint."""

    worktrees_file: Path
    """Path to worktrees.json within checkpoint."""
```

**Standard checkpoints**:

| Checkpoint Name | State Description |
|-----------------|-------------------|
| `wp_created` | WPs exist in planned lane, no worktrees created |
| `wp_implemented` | WP01 implemented, awaiting review |
| `review_pending` | WP01 submitted for review |
| `review_rejected` | WP01 review rejected, needs re-implementation |
| `review_approved` | WP01 review approved, ready for merge |
| `wp_merged` | WP01 merged to main |

### WorktreeMetadata

Metadata for recreating git worktrees from a fixture.

```python
from dataclasses import dataclass

@dataclass
class WorktreeMetadata:
    """Information needed to recreate a git worktree."""

    wp_id: str
    """Work package identifier (e.g., 'WP01')."""

    branch_name: str
    """Git branch name for this worktree."""

    relative_path: str
    """Path relative to repo root (e.g., '.worktrees/test-feature-WP01')."""

    commit_hash: str | None
    """Optional commit hash to checkout (None = branch HEAD)."""
```

**worktrees.json format**:
```json
{
  "worktrees": [
    {
      "wp_id": "WP01",
      "branch_name": "test-feature-WP01",
      "relative_path": ".worktrees/test-feature-WP01",
      "commit_hash": null
    }
  ]
}
```

### TestPath

The test execution path based on available agent count.

```python
from dataclasses import dataclass
from typing import Literal

@dataclass
class TestPath:
    """Selected test path based on runtime agent availability."""

    path_type: Literal["1-agent", "2-agent", "3+-agent"]
    """The test path variant to execute."""

    available_agents: list[str]
    """List of authenticated agent IDs available for this run."""

    implementation_agent: str
    """Agent to use for implementation phase."""

    review_agent: str
    """Agent to use for review phase."""

    fallback_agent: str | None
    """Third agent for fallback scenarios (None for 1/2-agent paths)."""
```

**Path selection logic**:

| Agent Count | Path Type | Behavior |
|-------------|-----------|----------|
| 1 | 1-agent | Same agent for impl and review |
| 2 | 2-agent | Different agents for impl vs review |
| 3+ | 3+-agent | Third agent available for fallback |

### TestContext

Runtime context for an e2e test, combining fixtures and agent availability.

```python
from dataclasses import dataclass
from pathlib import Path

@dataclass
class TestContext:
    """Complete context for running an e2e orchestrator test."""

    temp_dir: Path
    """Temporary directory containing the test environment."""

    repo_root: Path
    """Root of the test git repository."""

    feature_dir: Path
    """Path to the test feature directory."""

    test_path: TestPath
    """Selected test path with agent assignments."""

    checkpoint: FixtureCheckpoint | None
    """Loaded checkpoint if test started from snapshot."""

    orchestration_state: "OrchestrationRun | None"
    """Loaded state from checkpoint (None if fresh start)."""
```

## Fixture Directory Structure

```
tests/fixtures/orchestrator/
├── checkpoint_wp_created/
│   ├── state.json              # Serialized OrchestrationRun
│   ├── feature/
│   │   ├── spec.md
│   │   ├── plan.md
│   │   ├── meta.json
│   │   └── tasks/
│   │       ├── WP01.md         # lane: planned
│   │       └── WP02.md         # lane: planned
│   └── worktrees.json          # Empty list (no worktrees yet)
│
├── checkpoint_wp_implemented/
│   ├── state.json              # WP01 status: IMPLEMENTATION complete
│   ├── feature/
│   │   └── tasks/
│   │       ├── WP01.md         # lane: doing
│   │       └── WP02.md         # lane: planned
│   └── worktrees.json          # WP01 worktree exists
│
└── ... (other checkpoints follow same pattern)
```

## State Validation

After each test, validate:

1. **State file integrity**: `state.json` can be deserialized to `OrchestrationRun`
2. **Lane consistency**: WP frontmatter lanes match state file status
3. **Git state**: Worktrees exist where `worktrees.json` says they should
4. **Commit history**: Expected commits present in worktree branches

```python
def validate_test_result(ctx: TestContext) -> list[str]:
    """Validate orchestration state after test. Returns list of errors."""
    errors = []

    # Check state file
    state_path = ctx.feature_dir / ".orchestration-state.json"
    if not state_path.exists():
        errors.append("Missing orchestration state file")

    # Check lane consistency
    for wp_id, wp in ctx.orchestration_state.work_packages.items():
        expected_lane = wp.status.to_lane()
        actual_lane = read_wp_frontmatter(ctx.feature_dir / "tasks" / f"{wp_id}.md")
        if expected_lane != actual_lane:
            errors.append(f"{wp_id}: lane mismatch (expected {expected_lane}, got {actual_lane})")

    return errors
```
