# Developer Quickstart: Agent Profile Projection and Plugin Production Pipeline

**Mission**: agent-profile-projection-plugin-production-01KV3NGS

## Prerequisites

- spec-kitty CLI installed (`uv tool install spec-kitty-cli` or equivalent)
- A test project with `.kittify/config.yaml` configured for at least `claude` and `codex`
- For plugin validation: Claude CLI (`npm install -g @anthropic-ai/claude-code`)
- For Codex agent testing: Codex CLI installed

## Testing Profile Projection (Core Flow)

### 1. Fresh init with profile projection

```bash
# In a new test project directory
spec-kitty init --ai claude codex copilot auggie

# Verify profiles are generated
ls .claude/agents/          # *.md files
ls .codex/agents/           # *.toml files
ls .github/agents/          # *.agent.md files
ls .augment/agents/         # *.md files

# Verify doctor reports all present
spec-kitty doctor tool-surfaces --kind agent-profile --json
# Expect: all configured harnesses show "present", others show "not_applicable"
```

### 2. Upgrade from rc44-era state (migration fixture)

```bash
# Simulate rc44 state:
# - Remove generated profiles
rm -rf .claude/agents/ .codex/agents/ .github/agents/

# - Truncate command-skill manifest to 11 entries (edit .kittify/command-skills-manifest.json)
# - Do NOT create .roo/ (should not be needed)

spec-kitty upgrade

# Verify:
# - Summary shows profiles created, manifest repaired
# - doctor reports zero errors except not_applicable
spec-kitty doctor tool-surfaces --json | python3 -m json.tool
```

### 3. Drift protection

```bash
# Edit a generated profile
echo "# user edit" >> .claude/agents/analyst.md

# Interactive mode — should prompt
spec-kitty upgrade
# Expected: "analyst.md has been locally modified. Overwrite? [y/N]"
# Choose N → file preserved

# Non-interactive mode — should report and exit non-zero
spec-kitty upgrade --yes
# Expected: exits non-zero, reports drift on analyst.md, no overwrite

# Force overwrite
spec-kitty upgrade --repair-drift=overwrite
# Expected: analyst.md overwritten, exits 0
```

### 4. Idempotency check

```bash
spec-kitty upgrade   # first run — creates/repairs
spec-kitty upgrade   # second run — should show no changes, exit 0
spec-kitty doctor tool-surfaces --json | python3 -c "
import sys, json
d = json.load(sys.stdin)
errors = [s for s in d['surfaces'] if s['status'] not in ('present', 'not_applicable')]
print('Errors:', errors)
assert not errors, 'Non-zero error surfaces on second run!'
print('Idempotency check passed.')
"
```

## Testing Claude Code Plugin Build

```bash
# Build the plugin
spec-kitty plugin build --target claude-code

# Inspect the bundle
ls dist/spec-kitty-plugins/claude-code/
# Expected: .claude-plugin/plugin.json, skills/, agents/, bin/, marketplace.json

cat dist/spec-kitty-plugins/claude-code/.claude-plugin/plugin.json
# Verify: "version" matches current spec-kitty-cli version, no "0.0.0"

# Validate with Claude CLI
claude plugin validate --strict dist/spec-kitty-plugins/claude-code/
# Expected: zero errors, zero strict warnings

# Local dev install
claude --plugin-dir dist/spec-kitty-plugins/claude-code/
# In the Claude session, run /agents and verify Spec Kitty agents appear

# Test the bin/ wrapper
dist/spec-kitty-plugins/claude-code/bin/spec-kitty-wrapper --version
# With spec-kitty installed: should use installed version
# Without spec-kitty: should fall back to uvx
```

## Testing Codex Plugin Build

```bash
# Build the Codex plugin
spec-kitty plugin build --target codex

# Inspect
ls dist/spec-kitty-plugins/codex/
cat dist/spec-kitty-plugins/codex/.codex-plugin/plugin.json
# Verify: "hooks" key NOT present, "agents" key NOT present

# Verify hooks/ directory exists (discovered by presence)
ls dist/spec-kitty-plugins/codex/hooks/  # if applicable

# Install locally for testing
codex plugin marketplace add dist/spec-kitty-plugins/codex/
codex plugin add spec-kitty@spec-kitty-plugins
codex plugin list  # should show spec-kitty
```

## Testing Codex Agent Profiles

```bash
# After spec-kitty init with codex configured:
ls .codex/agents/
cat .codex/agents/analyst.toml
# Expected: name, description, developer_instructions fields present, valid TOML

# Test with Codex CLI:
# codex --agent analyst  # or however Codex loads custom agents
```

## Testing Roo Code Deprecation

```bash
# Create a project with .roo/ and roo in config
mkdir -p .roo/commands
echo "- roo" >> .kittify/config.yaml  # (if it was there)

spec-kitty upgrade
# Expected: deprecation notice about Roo Code shutdown on 2026-05-15
# .roo/ directory preserved (not deleted)
# roo removed from config.yaml
```

## Running the Full Test Suite

```bash
# Unit tests only
pytest tests/specify_cli/tool_surface/ -v

# Integration tests (requires project fixture)
pytest tests/specify_cli/integration/ -v

# Migration acceptance fixture specifically
pytest tests/specify_cli/integration/test_rc44_migration_fixture.py -v

# Full suite with coverage
pytest tests/ --cov=src/specify_cli --cov-report=term-missing

# Type checking
mypy src/specify_cli/tool_surface/ src/specify_cli/cli/commands/plugin.py

# Linting
ruff check src/specify_cli/
```

## CI Plugin Validation Setup

```yaml
# In .github/workflows/ci.yml, add to the integration job:
- name: Install Claude CLI for plugin validation
  run: npm install -g @anthropic-ai/claude-code

- name: Build and validate Claude Code plugin
  run: |
    spec-kitty plugin build --target claude-code
    claude plugin validate --strict dist/spec-kitty-plugins/claude-code/
```
