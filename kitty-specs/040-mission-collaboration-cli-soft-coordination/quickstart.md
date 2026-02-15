# Quickstart Guide: Mission Collaboration CLI Development

**Feature**: 040-mission-collaboration-cli-soft-coordination
**Version**: S1/M1 Step 1
**Date**: 2026-02-15

## Overview

This guide helps developers get started with implementing and testing the mission collaboration CLI feature. It covers environment setup, development workflows, testing strategies, and common tasks.

**Prerequisites:**
- Python 3.11+
- Git
- Poetry (for dependency management)
- Access to spec-kitty-events private repository (GitHub deploy key)

---

## Quick Setup (5 minutes)

```bash
# 1. Clone spec-kitty repository
git clone https://github.com/Priivacy-ai/spec-kitty.git
cd spec-kitty

# 2. Checkout 2.x branch
git checkout 2.x

# 3. Install dependencies (includes pinned spec-kitty-events via Git)
poetry install

# 4. Verify setup
poetry run pytest tests/ -x -q --co  # Collect tests (should not error)
poetry run mypy src/specify_cli/ --version  # Verify mypy installed

# 5. Run existing tests to verify baseline
poetry run pytest tests/specify_cli/ -x -q
```

**Expected outcome:** All existing tests pass, no import errors.

---

## Development Environment

### Directory Structure

```
spec-kitty/
├── src/specify_cli/
│   ├── cli/commands/mission/      # NEW: Command handlers
│   ├── collaboration/             # NEW: Domain logic
│   ├── adapters/                  # NEW: Adapter interface
│   └── events/                    # ENHANCED: Queue + replay
│
├── tests/specify_cli/
│   ├── cli/commands/mission/      # NEW: Command tests
│   ├── collaboration/             # NEW: Domain tests
│   ├── adapters/                  # NEW: Adapter tests
│   └── integration/               # NEW: Integration tests
│
├── kitty-specs/040-mission-collaboration-cli-soft-coordination/
│   ├── spec.md                    # Feature specification
│   ├── plan.md                    # Implementation plan
│   ├── data-model.md              # Entity definitions
│   └── quickstart.md              # This file
│
└── pyproject.toml                 # Dependencies (pins spec-kitty-events)
```

### Key Dependencies

**Existing:**
- `typer` - CLI framework
- `rich` - Console output
- `ruamel.yaml` - YAML parsing
- `pytest` - Testing
- `mypy` - Type checking

**New (feature 040):**
- `spec-kitty-events` - Event schemas (Git dependency, pinned to 006 prerelease)
- `httpx` - SaaS API client
- `ulid-py` - ULID generation

**Check pinned commit:**
```bash
grep "spec-kitty-events" pyproject.toml
# Should show: spec-kitty-events = { git = "...", rev = "abc1234" }
```

---

## Integration with Feature 006 (spec-kitty-events)

### Understanding the Dependency

**Contract Ownership:**
- **Feature 006 owns**: Event schemas, payload models, reducer semantics
- **Feature 040 owns**: Event emission, ULID generation, local queue, replay transport

**Development Workflow:**
1. Feature 006 team develops collaboration event schemas in `spec-kitty-events` feature branch
2. Feature 040 pins to 006 feature branch commit
3. Iterate: 006 updates schemas → 040 updates pin → test integration
4. Merge 006 → main
5. Update 040 to pin to 006 main commit hash
6. Merge 040 → 2.x

### Updating spec-kitty-events Pin

```bash
# Check current pinned commit
grep "spec-kitty-events" pyproject.toml

# Update to new 006 commit (during parallel development)
poetry remove spec-kitty-events
poetry add "spec-kitty-events @ git+https://github.com/Priivacy-ai/spec-kitty-events.git@<new-commit-hash>"
poetry lock --no-update
poetry install

# Verify integration
poetry run pytest tests/specify_cli/integration/test_006_event_schemas.py -v
```

**Get latest 006 commit hash:**
```bash
# If you have spec-kitty-events cloned locally
cd ../spec-kitty-events
git log -1 --format="%H"

# Or check GitHub
# https://github.com/Priivacy-ai/spec-kitty-events/commits/feature/006-collaboration-events
```

### Testing Event Schema Compatibility

```bash
# Run integration tests against pinned 006 version
poetry run pytest tests/specify_cli/integration/test_006_event_schemas.py -v

# Expected: All event types conform to canonical envelope
# - event_id: ULID (26 chars)
# - causation_id: ULID (26 chars) if present
# - aggregate_id: mission_id
# - payload: Contains participant_id (ULID)
```

---

## Running Tests

### Unit Tests (Fast, No Network)

```bash
# All unit tests
poetry run pytest tests/specify_cli/ -v

# Specific module
poetry run pytest tests/specify_cli/cli/commands/mission/ -v
poetry run pytest tests/specify_cli/collaboration/ -v
poetry run pytest tests/specify_cli/adapters/ -v

# Single test file
poetry run pytest tests/specify_cli/cli/commands/mission/test_join.py -v

# Single test function
poetry run pytest tests/specify_cli/cli/commands/mission/test_join.py::test_join_mission_success -v
```

**Expected behavior:**
- No network calls (mock SaaS APIs)
- Fast execution (< 5 seconds for full suite)
- 90%+ coverage for new code

### Integration Tests (Mock SaaS, Pin 006)

```bash
# All integration tests
poetry run pytest tests/specify_cli/integration/ -v

# Event schema compatibility (006 prerelease)
poetry run pytest tests/specify_cli/integration/test_006_event_schemas.py -v

# SaaS join API (mocked)
poetry run pytest tests/specify_cli/integration/test_saas_join_mock.py -v

# SaaS replay API (mocked)
poetry run pytest tests/specify_cli/integration/test_saas_replay_mock.py -v

# End-to-end offline → online flow
poetry run pytest tests/specify_cli/integration/test_offline_queue_replay.py -v
```

**Expected behavior:**
- Mock httpx responses for SaaS APIs
- Validate canonical envelope format
- Test event ordering (Lamport clock, causation chain)

### E2E Test (Real SaaS Dev Environment)

**Prerequisites:**
- SaaS dev environment must be running
- API key for authentication
- Test mission created in SaaS dev

```bash
# Set environment variables
export SAAS_DEV_URL=https://dev.spec-kitty-saas.com
export SAAS_DEV_API_KEY=<api-key>

# Run E2E test
poetry run pytest tests/e2e/test_collaboration_scenario.py -v

# Scenario: 3 participants, concurrent drive, warning+ack, offline replay
```

**Expected behavior:**
- Real SaaS API calls (join, replay endpoints)
- 3 CLI instances simulate 3 participants
- Collision warnings triggered and acknowledged
- Offline events replayed successfully

**Note:** E2E test is S1/M1 exit gate (required for milestone completion).

### Type Checking

```bash
# Check new modules only
poetry run mypy src/specify_cli/cli/commands/mission/ --strict
poetry run mypy src/specify_cli/collaboration/ --strict
poetry run mypy src/specify_cli/adapters/ --strict
poetry run mypy src/specify_cli/events/ --strict

# Check all (may have pre-existing errors in other modules)
poetry run mypy src/specify_cli/ --strict
```

**Expected:**
- No type errors in new modules
- All functions have type annotations
- No `Any` types without justification

### Code Coverage

```bash
# Generate coverage report
poetry run pytest --cov=src/specify_cli --cov-report=html tests/

# Open report in browser
open htmlcov/index.html

# Expected: 90%+ coverage for new code (constitution requirement)
```

---

## Common Development Tasks

### 1. Add New Command Handler

**Example:** Add `mission pause` command

```bash
# 1. Create command handler
touch src/specify_cli/cli/commands/mission/pause.py

# 2. Implement command (see template below)
# 3. Register in mission/__init__.py
# 4. Add use-case in collaboration/service.py
# 5. Add tests
touch tests/specify_cli/cli/commands/mission/test_pause.py

# 6. Run tests
poetry run pytest tests/specify_cli/cli/commands/mission/test_pause.py -v
```

**Command Handler Template:**
```python
# src/specify_cli/cli/commands/mission/pause.py
import typer
from rich.console import Console
from specify_cli.collaboration import service

console = Console()
app = typer.Typer()

@app.command()
def pause(
    mission_id: str = typer.Option(None, help="Mission ID (uses active if omitted)"),
):
    """Pause active participation in mission."""
    try:
        result = service.pause_mission(mission_id)
        console.print(f"✓ Paused participation in {result['mission_id']}")
    except Exception as e:
        console.print(f"✗ Error: {e}", style="red")
        raise typer.Exit(1)
```

**Test Template:**
```python
# tests/specify_cli/cli/commands/mission/test_pause.py
import pytest
from unittest.mock import patch, MagicMock
from specify_cli.cli.commands.mission import pause

def test_pause_mission_success(tmp_path):
    """Test pause command succeeds when mission is active."""
    with patch("specify_cli.collaboration.service.pause_mission") as mock_pause:
        mock_pause.return_value = {"mission_id": "mission-abc-123"}

        result = pause.pause(mission_id="mission-abc-123")

        assert result is None  # Command exits cleanly
        mock_pause.assert_called_once_with("mission-abc-123")
```

### 2. Add New Adapter Implementation

**Example:** Add Claude adapter

```bash
# 1. Create adapter file
touch src/specify_cli/adapters/claude.py

# 2. Implement ObserveDecideAdapter protocol (see template below)
# 3. Add contract tests with recorded fixtures
touch tests/specify_cli/adapters/test_claude.py

# 4. Record sample outputs from Claude
mkdir -p tests/fixtures/claude/
# Save Claude outputs to fixtures/claude/*.json

# 5. Run tests
poetry run pytest tests/specify_cli/adapters/test_claude.py -v
```

**Adapter Template:**
```python
# src/specify_cli/adapters/claude.py
from typing import Protocol
from specify_cli.adapters.observe_decide import (
    ObserveDecideAdapter,
    ActorIdentity,
    ObservationSignal,
    DecisionRequestDraft,
    AdapterHealth
)

class ClaudeObserveDecideAdapter(ObserveDecideAdapter):
    """Claude adapter for observe+decide pattern."""

    def normalize_actor_identity(self, runtime_ctx: dict) -> ActorIdentity:
        """Extract Claude agent identity."""
        return ActorIdentity(
            agent_type="claude",
            auth_principal=runtime_ctx.get("user_email", "unknown"),
            session_id=runtime_ctx.get("session_id", "unknown")
        )

    def parse_observation(self, output: str | dict) -> list[ObservationSignal]:
        """Parse Claude output into structured signals."""
        # Implementation: parse Claude's JSON or markdown output
        signals = []
        # ... parsing logic ...
        return signals

    # ... other methods ...
```

**Contract Test Template:**
```python
# tests/specify_cli/adapters/test_claude.py
import pytest
from specify_cli.adapters.claude import ClaudeObserveDecideAdapter

def test_claude_adapter_contract():
    """Verify Claude adapter produces identical events to other adapters."""
    adapter = ClaudeObserveDecideAdapter()

    # Load recorded fixture
    with open("tests/fixtures/claude/step_started.json") as f:
        claude_output = f.read()

    # Parse observation
    signals = adapter.parse_observation(claude_output)

    # Verify: signal_type, entity_id, metadata structure
    assert len(signals) == 1
    assert signals[0].signal_type == "step_started"
    assert signals[0].entity_id.startswith("step:")
```

### 3. Update Event Schemas (Feature 006 Dependency)

**When feature 006 updates collaboration event schemas:**

```bash
# 1. Coordinate with 006 team on schema changes
# (GitHub issue, Slack, or planning meeting)

# 2. Wait for 006 to merge schema update to main
# 3. Get new commit hash
cd ../spec-kitty-events
git pull origin main
git log -1 --format="%H"

# 4. Update spec-kitty pin
cd ../spec-kitty
poetry remove spec-kitty-events
poetry add "spec-kitty-events @ git+https://github.com/Priivacy-ai/spec-kitty-events.git@<new-commit-hash>"
poetry lock --no-update
poetry install

# 5. Run integration tests to verify compatibility
poetry run pytest tests/specify_cli/integration/test_006_event_schemas.py -v

# 6. Fix any breaking changes in CLI code
# 7. Commit pyproject.toml and poetry.lock
git add pyproject.toml poetry.lock
git commit -m "chore: update spec-kitty-events to <commit-hash>"
```

### 4. Debug Collaboration Commands Locally

**Test mission join without SaaS:**

```bash
# 1. Mock SaaS join API response
export MOCK_SAAS=true

# 2. Run command
poetry run spec-kitty mission join mission-test-123 --role developer

# 3. Verify session file created
cat ~/.spec-kitty/missions/mission-test-123/session.json

# Expected:
# {
#   "mission_id": "mission-test-123",
#   "participant_id": "01HQRS8ZMBE6XYZ0000000001",
#   "role": "developer",
#   ...
# }
```

**Test offline event queue:**

```bash
# 1. Join mission (mocked)
poetry run spec-kitty mission join mission-test-123 --role developer

# 2. Disconnect network (simulate offline)
# (disable Wi-Fi or use firewall rule)

# 3. Run commands offline
poetry run spec-kitty mission focus set wp:WP01
poetry run spec-kitty mission drive set --state active

# 4. Verify events queued locally
cat ~/.spec-kitty/events/mission-test-123.jsonl

# Expected: 2 events with _replay_status="pending"

# 5. Reconnect network
# 6. Run any online command (triggers replay)
poetry run spec-kitty mission status

# 7. Verify events replayed
cat ~/.spec-kitty/events/mission-test-123.jsonl
# Expected: _replay_status="delivered"
```

---

## Troubleshooting

### Issue: spec-kitty-events import errors

**Symptom:**
```
ModuleNotFoundError: No module named 'spec_kitty_events'
```

**Solution:**
```bash
# 1. Verify spec-kitty-events is in pyproject.toml
grep "spec-kitty-events" pyproject.toml

# 2. Reinstall dependencies
poetry install

# 3. Verify installation
poetry run python -c "import spec_kitty_events; print(spec_kitty_events.__file__)"
```

### Issue: GitHub authentication errors (CI/CD)

**Symptom:**
```
fatal: could not read Username for 'https://github.com': terminal prompts disabled
```

**Solution (Local Development):**
```bash
# Use SSH URL instead of HTTPS
poetry remove spec-kitty-events
poetry add "spec-kitty-events @ git+ssh://git@github.com/Priivacy-ai/spec-kitty-events.git@<commit-hash>"
```

**Solution (CI/CD):**
- Verify `SPEC_KITTY_EVENTS_DEPLOY_KEY` secret is configured
- Check SSH key permissions (should be 600)
- See `.github/workflows/` for SSH setup steps

### Issue: Type checking errors in new code

**Symptom:**
```
error: Function is missing a return type annotation
```

**Solution:**
```python
# Add explicit return type
def join_mission(mission_id: str) -> dict:  # Add return type
    return {"mission_id": mission_id}
```

### Issue: Test failures due to missing fixtures

**Symptom:**
```
FileNotFoundError: [Errno 2] No such file or directory: 'tests/fixtures/gemini/step_started.json'
```

**Solution:**
```bash
# Create fixtures directory
mkdir -p tests/fixtures/gemini/

# Record sample outputs (run Gemini agent manually, save output)
# Or use placeholder fixture for initial development
echo '{"type": "step_started", "step_id": "step:42"}' > tests/fixtures/gemini/step_started.json
```

### Issue: E2E test fails (SaaS dev unavailable)

**Symptom:**
```
ConnectionError: Cannot connect to https://dev.spec-kitty-saas.com
```

**Solution:**
- Verify SaaS dev environment is running (contact ops team)
- Check API key is valid (regenerate if expired)
- Skip E2E test during local development (use `pytest -m "not e2e"`)
- Note: E2E test is required for S1/M1 exit gate (cannot skip for milestone)

---

## Code Review Checklist

Before submitting PR:

**Code Quality:**
- [ ] All tests pass (`pytest tests/ -v`)
- [ ] Type checking passes (`mypy src/specify_cli/ --strict`)
- [ ] Coverage >= 90% for new code (`pytest --cov`)
- [ ] Docstrings added for public APIs
- [ ] No security issues (credentials, secrets handling)

**Integration:**
- [ ] spec-kitty-events pinned to specific commit (not "main")
- [ ] Integration tests pass (`pytest tests/specify_cli/integration/ -v`)
- [ ] Event schemas conform to canonical envelope (ULID, aggregate_id)

**Documentation:**
- [ ] CLI help text clear and includes examples
- [ ] CHANGELOG.md updated (new commands, breaking changes)
- [ ] This quickstart.md updated (if new development tasks)

**Constitution Compliance:**
- [ ] Python 3.11+ compatible (no legacy Python 2)
- [ ] Cross-platform (Linux, macOS, Windows 10+)
- [ ] CLI operations < 2 seconds (typical operations)
- [ ] Target 2.x branch (not 1.x)

---

## Next Steps

After completing development:

1. **Run full test suite:**
   ```bash
   poetry run pytest tests/ -v --cov=src/specify_cli --cov-report=html
   ```

2. **Submit PR:**
   - Target branch: `2.x`
   - Include test coverage report
   - Reference spec: `kitty-specs/040-mission-collaboration-cli-soft-coordination/spec.md`

3. **Coordinate E2E test:**
   - Schedule SaaS dev environment availability
   - Run E2E test with 3 participants
   - Verify acceptance criteria #5

4. **Update documentation:**
   - README.md (new commands)
   - CHANGELOG.md (version bump)
   - CLI help text (`--help` flag)

**S1/M1 Exit Criteria:**
- ✅ All unit tests pass (90%+ coverage)
- ✅ All integration tests pass (pinned to 006 prerelease)
- ✅ E2E test passes (real SaaS dev, 3 participants)
- ✅ Type checking passes (mypy --strict)
- ✅ Constitution compliance verified
- ✅ PR approved and merged to 2.x

---

## Resources

- **Feature Spec**: [spec.md](spec.md)
- **Implementation Plan**: [plan.md](plan.md)
- **Data Model**: [data-model.md](data-model.md)
- **Constitution**: `.kittify/memory/constitution.md`
- **spec-kitty-events Repo**: https://github.com/Priivacy-ai/spec-kitty-events
- **SaaS Dev Environment**: https://dev.spec-kitty-saas.com

---

**Questions?** Contact the feature 040 team lead or open a GitHub issue.
