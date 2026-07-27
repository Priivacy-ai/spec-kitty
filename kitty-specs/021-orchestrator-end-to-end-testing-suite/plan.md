# Implementation Plan: Orchestrator End-to-End Testing Suite

**Branch**: `021-orchestrator-end-to-end-testing-suite` | **Date**: 2026-01-19 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/kitty-specs/021-orchestrator-end-to-end-testing-suite/spec.md`

## Summary

Build comprehensive end-to-end testing infrastructure for the orchestrator (feature 020) with:
- Tiered agent coverage (5 core agents with full integration tests, 7 extended agents with smoke tests)
- Modular test paths based on agent count (1-agent, 2-agent, 3+-agent)
- Checkpoint-based fixtures for fast test execution
- Real agent CLI invocation (no mocks)

## Technical Context

**Language/Version**: Python 3.11+ (matches existing spec-kitty codebase)
**Primary Dependencies**: pytest, pytest-asyncio (for async orchestrator tests), existing orchestrator module
**Storage**: Git-tracked fixtures in `tests/fixtures/orchestrator/`
**Testing**: pytest with custom markers for test categories
**Target Platform**: Local developer machines with agents installed
**Project Type**: Single project (test infrastructure added to existing codebase)
**Performance Goals**: Full integration suite <30 min, smoke suite <10 min
**Constraints**: Requires real agent CLIs installed and authenticated
**Scale/Scope**: 5 core agents, 7 extended agents, 6 test categories

## Constitution Check

*No constitution file found. Section skipped.*

## Project Structure

### Documentation (this feature)

```
kitty-specs/021-orchestrator-end-to-end-testing-suite/
├── plan.md              # This file
├── data-model.md        # Test entities and fixture schema
├── quickstart.md        # How to run the test suite
└── tasks.md             # Phase 2 output (created by /spec-kitty.tasks)
```

### Source Code (repository root)

```
tests/
├── fixtures/
│   └── orchestrator/                    # NEW: Fixture snapshots
│       ├── checkpoint_wp_created/
│       │   ├── state.json               # OrchestrationRun state
│       │   ├── feature/                 # Minimal feature structure
│       │   │   ├── spec.md
│       │   │   └── tasks/
│       │   │       ├── WP01.md
│       │   │       └── WP02.md
│       │   └── worktrees.json           # Worktree metadata
│       ├── checkpoint_wp_implemented/
│       ├── checkpoint_review_pending/
│       ├── checkpoint_review_rejected/
│       ├── checkpoint_review_approved/
│       └── checkpoint_wp_merged/
│
├── specify_cli/
│   └── orchestrator/
│       ├── test_integration.py          # EXISTING: Basic integration tests
│       ├── test_e2e_happy_path.py       # NEW: Happy path tests
│       ├── test_e2e_review_cycles.py    # NEW: Review cycle tests
│       ├── test_e2e_parallel.py         # NEW: Parallel execution tests
│       ├── test_e2e_smoke.py            # NEW: Extended agent smoke tests
│       └── conftest.py                  # NEW: Fixtures and markers
│
└── conftest.py                          # Update: Add orchestrator markers

src/specify_cli/
└── orchestrator/
    └── testing/                         # NEW: Test utilities module
        ├── __init__.py
        ├── availability.py              # Agent detection with auth probe
        ├── fixtures.py                  # Fixture loader/creator
        └── paths.py                     # Test path selection (1/2/3+ agents)
```

**Structure Decision**: Extend existing `tests/specify_cli/orchestrator/` with new e2e test files. Add `tests/fixtures/orchestrator/` for checkpoint snapshots. Add `src/specify_cli/orchestrator/testing/` for reusable test utilities.

## Key Engineering Decisions

### 1. Fixture Storage (from planning Q1)

**Decision**: Git-tracked directory snapshots in `tests/fixtures/orchestrator/`

**Structure per checkpoint**:
```
checkpoint_<name>/
├── state.json           # Serialized OrchestrationRun
├── feature/             # Minimal kitty-specs structure
│   ├── spec.md
│   ├── plan.md
│   ├── meta.json
│   └── tasks/
│       ├── WP01.md      # With lane frontmatter
│       └── WP02.md
└── worktrees.json       # Metadata: [{wp_id, branch, path}]
```

**Loader behavior**:
1. Copy fixture to temp directory
2. Initialize git repo in temp dir
3. Create worktrees from `worktrees.json` metadata
4. Load `state.json` into OrchestrationRun object
5. Return ready-to-use test context

### 2. Auth Verification (from planning Q2)

**Decision**: Lightweight API probe per agent

**Implementation**:
```python
class AgentAvailability:
    agent_id: str
    is_installed: bool      # CLI binary exists
    is_authenticated: bool  # Probe call succeeded
    tier: Literal["core", "extended"]
    failure_reason: str | None
```

**Probe behavior**:
- Each agent invoker gets a `probe()` method
- Makes minimal API call (e.g., list models, whoami)
- Timeout: 10 seconds
- Caches result for session duration

### 3. Test Path Model (from planning Q3)

**Decision**: Parameterized by agent count, not identity

**Paths**:
| Path | Agents | Tests |
|------|--------|-------|
| 1-agent | Single agent | Same-agent implementation and review |
| 2-agent | Two agents | Cross-agent review (different impl vs review agent) |
| 3+-agent | Three+ agents | Fallback scenarios (third agent used on failure) |

**Runtime selection**:
```python
@pytest.fixture
def available_agents() -> list[str]:
    """Detect available agents at test start."""
    return [a.agent_id for a in detect_all_agents() if a.is_authenticated]

@pytest.fixture
def test_path(available_agents) -> Literal["1-agent", "2-agent", "3+-agent"]:
    """Select test path based on agent count."""
    count = len(available_agents)
    if count >= 3:
        return "3+-agent"
    elif count == 2:
        return "2-agent"
    return "1-agent"
```

### 4. Smoke Test Task (from planning Q4)

**Decision**: File touch - agent creates empty file at specified path

**Implementation**:
```python
SMOKE_TASK = """
Create an empty file at: {target_path}
Do not add any content. Just create the file.
"""

def verify_smoke_result(target_path: Path) -> bool:
    return target_path.exists()
```

## Test Categories & Markers

```python
# In conftest.py
pytest.mark.orchestrator_availability  # Agent detection tests
pytest.mark.orchestrator_fixtures      # Fixture management tests
pytest.mark.orchestrator_happy_path    # Basic orchestration flow
pytest.mark.orchestrator_review_cycles # Review rejection/re-impl
pytest.mark.orchestrator_parallel      # Parallel execution & deps
pytest.mark.orchestrator_smoke         # Extended agent smoke tests

# Tier markers for skip behavior
pytest.mark.core_agent                 # Fail if agent unavailable
pytest.mark.extended_agent             # Skip if agent unavailable
```

## Agent Tiers

**Core Tier** (must be available - tests fail if missing):
- Claude Code (`claude`)
- GitHub Codex (`codex`)
- GitHub Copilot (`copilot`)
- Google Gemini (`gemini`)
- OpenCode (`opencode`)

**Extended Tier** (skip gracefully if missing):
- Cursor (`cursor`)
- Qwen Code (`qwen`)
- Augment Code (`augment`)
- Kilocode (`kilocode`)
- Roo Cline (`roo`)
- Windsurf (`windsurf`)
- Amazon Q (`amazonq`)

## Complexity Tracking

No constitution violations to track.
