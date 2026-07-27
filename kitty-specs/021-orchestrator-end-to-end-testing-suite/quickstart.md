# Quickstart: Orchestrator End-to-End Testing

## Prerequisites

### Required

- Python 3.11+
- Git
- At least 2 core agents installed and authenticated

### Core Agents (at least 2 required)

| Agent | Install | Auth Check |
|-------|---------|------------|
| Claude Code | `npm install -g @anthropic-ai/claude-code` | `claude --version` |
| GitHub Codex | `npm install -g @openai/codex` | `codex auth status` |
| GitHub Copilot | Via GitHub CLI or VS Code | `gh copilot --version` |
| Google Gemini | `pip install google-generativeai` | `gemini auth status` |
| OpenCode | `npm install -g opencode` | `opencode --version` |

### Extended Agents (optional)

Cursor, Qwen, Augment, Kilocode, Roo, Windsurf, Amazon Q

## Running Tests

### Check Agent Availability

```bash
# See which agents are available
pytest tests/specify_cli/orchestrator/ -m orchestrator_availability -v
```

### Run All E2E Tests

```bash
# Full suite (may take up to 30 minutes)
pytest tests/specify_cli/orchestrator/ -m "orchestrator" -v
```

### Run Specific Categories

```bash
# Happy path only
pytest tests/specify_cli/orchestrator/ -m orchestrator_happy_path -v

# Review cycles
pytest tests/specify_cli/orchestrator/ -m orchestrator_review_cycles -v

# Parallel execution
pytest tests/specify_cli/orchestrator/ -m orchestrator_parallel -v

# Extended agent smoke tests
pytest tests/specify_cli/orchestrator/ -m orchestrator_smoke -v
```

### Run with Specific Test Path

```bash
# Force 1-agent path (even if more available)
pytest tests/specify_cli/orchestrator/ --test-path=1-agent -v

# Force 2-agent path
pytest tests/specify_cli/orchestrator/ --test-path=2-agent -v
```

## Test Path Behavior

The test suite automatically selects a path based on available agents:

| Available Agents | Path | What's Tested |
|------------------|------|---------------|
| 1 | 1-agent | Same agent does impl + review |
| 2 | 2-agent | Different agents for impl vs review |
| 3+ | 3+-agent | Full suite including implicit fallback coverage |

## Fixture Management

### List Available Checkpoints

```bash
ls tests/fixtures/orchestrator/
```

### Create a New Checkpoint

```python
from specify_cli.orchestrator.testing import create_checkpoint

# After reaching desired state in a test
create_checkpoint(
    name="my_checkpoint",
    state=orchestration_state,
    feature_dir=feature_dir,
    worktrees=worktree_list,
)
```

### Detect Stale Checkpoints

```bash
# Check if fixtures match current orchestrator version
pytest tests/specify_cli/orchestrator/ -m orchestrator_fixtures --check-stale
```

## Troubleshooting

### "No core agents available"

At least 2 core agents must be installed and authenticated. Check:

```bash
# Verify installations
which claude codex opencode gemini

# Verify auth (varies by agent)
claude --version
codex auth status
```

### "Test skipped: extended agent not available"

This is expected behavior. Extended agents skip gracefully when not installed.

### "Fixture stale: orchestrator version mismatch"

Regenerate fixtures after updating orchestrator code:

```bash
pytest tests/specify_cli/orchestrator/ -m orchestrator_fixtures --regenerate
```

### Tests timing out

E2E tests with real agents can take several minutes. Increase timeout:

```bash
pytest tests/specify_cli/orchestrator/ -v --timeout=600
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ORCHESTRATOR_TEST_TIMEOUT` | 300 | Max seconds per test |
| `ORCHESTRATOR_PROBE_TIMEOUT` | 10 | Max seconds for auth probe |
| `ORCHESTRATOR_SKIP_SLOW` | false | Skip tests >60s if true |

## CI Considerations

These tests are designed for local execution with real agents. For CI:

1. Ensure agents are installed in CI environment
2. Configure agent authentication via secrets
3. Consider running only `orchestrator_availability` in CI
4. Full suite best run manually before releases
