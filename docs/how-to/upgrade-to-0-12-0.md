# Upgrading to Spec Kitty 0.12.0

**Key Change**: Agent management is now **config-driven**. Migrations respect your configuration choices instead of recreating deleted agent directories.

## What Changed

**Old behavior (0.11.x)**:
- You could manually delete agent directories
- Migrations would recreate them on upgrade
- No way to permanently remove an agent

**New behavior (0.12.0+)**:
- `.kittify/config.yaml` is the source of truth for agents
- Migrations only process agents listed in `config.yaml`
- Manually deleted agents stay deleted after upgrade
- Full control over which agents are active

## Why This Change

This change gives you **explicit control** over your agent configuration:
- **Predictable upgrades**: Migrations won't surprise you by recreating agents
- **Cleaner projects**: Remove agents you don't use without them reappearing
- **Multi-agent workflows**: Configure exactly which agents are available

See [ADR #6: Config-Driven Agent Management](../../architecture/adrs/2026-01-23-6-config-driven-agent-management.md) for technical details.

## Migration Steps

### Step 1: Remove Unwanted Agents (Before Upgrading)

**Identify agents you don't use**:
```bash
spec-kitty agent config status
```

**Remove them properly** (using CLI, not manual deletion):
```bash
spec-kitty agent config remove gemini cursor qwen
```

This updates `config.yaml` AND deletes directories consistently.

### Step 2: Upgrade spec-kitty

```bash
pip install --upgrade spec-kitty-cli
```

### Step 3: Verify Configuration

Check that your configured agents are correct:
```bash
spec-kitty agent config list
```

Should show only the agents you want to keep.

### Step 4: Sync Filesystem (Optional)

Clean up any orphaned directories:
```bash
spec-kitty agent config sync --remove-orphaned
```

### Step 5: Add New Agents Later

To add agents after upgrade, use the same command as before:
```bash
spec-kitty agent config add claude codex
```

## Troubleshooting

**Q: I deleted an agent directory manually and it's gone after upgrade**
- A: This is expected behavior in 0.12.0. Use `spec-kitty agent config add` to restore it.

**Q: An agent is in config but its directory is missing**
- A: Run `spec-kitty agent config sync --create-missing` to restore it.

**Q: How do I ensure an agent doesn't come back after upgrade?**
- A: Use `spec-kitty agent config remove <agent>` before upgrading. This removes it from `config.yaml`.

For command details, see [Managing AI Agents](manage-agents.md).
