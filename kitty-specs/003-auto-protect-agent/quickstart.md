# Quickstart: Auto-protect Agent Directories

## Overview

The Auto-protect Agent Directories feature ensures that all AI agent-specific directories are automatically added to `.gitignore` during `spec-kitty init`, preventing accidental commits of sensitive files and credentials.

## Quick Usage

### Basic Usage - Protect All Agents

```python
from specify_cli.gitignore_manager import GitignoreManager
from pathlib import Path

# Initialize manager with project root
manager = GitignoreManager(Path.cwd())

# Protect all known agent directories
result = manager.protect_all_agents()

if result.success:
    print(f"Added {len(result.entries_added)} directories to .gitignore")
    print(f"Skipped {len(result.entries_skipped)} already protected directories")
```

### Protect Selected Agents Only

```python
# Protect only specific agents
result = manager.protect_selected_agents(["claude", "codex", "opencode"])
```

### During spec-kitty init

The protection happens automatically:

```bash
$ spec-kitty init

# ... agent selection ...

✓ Updated .gitignore to exclude AI agent directories:
  - .claude/
  - .codex/
  - .opencode/
  - ... (and 9 more)
```

## Implementation Details

The GitignoreManager replaces the previous fragmented approach where only `.codex/` was protected by `handle_codex_security()`. Now all agent directories are protected uniformly through a centralized system.

## Protected Directories

The following directories are automatically protected:

| Agent | Directory | Notes |
|-------|-----------|-------|
| Claude Code | `.claude/` | Command files and history |
| Codex | `.codex/` | Contains auth.json credentials |
| opencode | `.opencode/` | Command files |
| Windsurf | `.windsurf/` | Workflows |
| Gemini | `.gemini/` | Google Gemini files |
| Cursor | `.cursor/` | Cursor configuration |
| Qwen | `.qwen/` | Qwen files |
| Kilocode | `.kilocode/` | Kilocode files |
| Auggie | `.augment/` | Augment files |
| GitHub Copilot | `.github/` | ⚠️ Shared with GitHub Actions |
| Roo Coder | `.roo/` | Roo configuration |
| Amazon Q | `.amazonq/` | Amazon Q files |

## Special Considerations

### .github/ Directory

The `.github/` directory is used by both GitHub Actions and GitHub Copilot. The tool adds it to `.gitignore` with a warning comment:

```gitignore
# Added by Spec Kitty CLI (auto-managed)
.github/  # Note: Also used by GitHub Actions - review before committing
```

### Multiple Runs

Running `spec-kitty init` multiple times is safe:
- Duplicate entries are automatically detected and skipped
- Existing `.gitignore` content is preserved
- Only missing directories are added

### Error Handling

If `.gitignore` cannot be modified:
```
⚠️ Cannot update .gitignore: Permission denied
   Run: chmod u+w .gitignore
   Then re-run spec-kitty init
```

## Testing Your Setup

After running `spec-kitty init`, verify protection:

```bash
# Check .gitignore contents
cat .gitignore | grep "Added by Spec Kitty"

# Verify agent directories are ignored
git status --ignored | grep -E "\.claude/|\.codex/"
```

## API Reference

### GitignoreManager Class

```python
class GitignoreManager:
    def __init__(self, project_path: Path)
    def protect_all_agents() -> ProtectionResult
    def protect_selected_agents(agents: List[str]) -> ProtectionResult
    def ensure_entries(entries: List[str]) -> bool
    @classmethod
    def get_agent_directories() -> List[AgentDirectory]
```

### ProtectionResult Structure

```python
@dataclass
class ProtectionResult:
    success: bool              # Operation succeeded
    modified: bool             # .gitignore was modified
    entries_added: List[str]   # New entries added
    entries_skipped: List[str] # Already protected
    errors: List[str]          # Error messages
    warnings: List[str]        # Warning messages
```

## Troubleshooting

### Q: Directories not being added to .gitignore?
**A:** Check file permissions and ensure you're in a git repository root.

### Q: Can I exclude certain directories from protection?
**A:** Currently, all directories are protected. Future versions will support exclusion.

### Q: What about custom agent directories?
**A:** Currently supports known agents only. Custom directories can be added manually.

## Next Steps

- Run `/spec-kitty.tasks` to see implementation tasks
- Review the full specification in [spec.md](spec.md)
- Check the technical design in [plan.md](plan.md)