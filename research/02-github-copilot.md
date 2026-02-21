# Agent: GitHub Copilot

## Basic Info

- **Directory**: `.github/prompts/`
- **Primary Interface**: CLI (new Copilot CLI) + VS Code extension
- **Vendor**: GitHub (Microsoft)
- **Documentation**: <https://github.com/github/copilot-cli>

## CLI Availability

### Installation

```bash
# New Copilot CLI (standalone) - RECOMMENDED
brew install github/gh-copilot/copilot-cli
# or via npm
npm install -g @github/copilot-cli

# Legacy gh extension (DEPRECATED)
gh extension install github/gh-copilot
```

### Verification

```bash
which copilot && copilot --version
```

### Local Test Results

```bash
$ copilot --version
0.0.384
Commit: 0b21260

$ which copilot
/opt/homebrew/bin/copilot

$ copilot --help
Usage: copilot [options] [command]
GitHub Copilot CLI - An AI-powered coding assistant
# ... (full help output available)
```

**Status**: Full CLI is installed and functional. This is a complete agentic coding assistant.

## Task Specification

### How to Pass Instructions

- [x] Command line argument - `copilot -p "Your prompt here"`
- [x] Stdin - Not directly, but can use shell substitution
- [x] Interactive mode - `copilot -i "Start with this prompt"`
- [x] File context - `copilot --add-dir <path>` for directory access

### Example Invocation

```bash
# Non-interactive mode (exits after completion)
copilot -p "Fix the bug in main.js" --allow-all-tools

# With full auto-approval (headless automation)
copilot -p "Implement feature X" --yolo
# or equivalently
copilot -p "Implement feature X" --allow-all

# Silent mode for scripting (JSON-like output)
copilot -p "What files handle authentication?" --silent

# With specific model
copilot --model gpt-5 -p "Refactor this code"

# Resume previous session
copilot --continue
copilot --resume [sessionId]

# Share session to file after completion
copilot -p "Complete this task" --share ./session.md
```

### Context Handling

- Operates in current working directory by default
- Add directories with `--add-dir <path>`
- `--allow-all-paths` disables path restrictions
- MCP server support with `--additional-mcp-config`
- GitHub MCP integration built-in with `--enable-all-github-mcp-tools`

## Completion Detection

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| Non-zero | Error |

### Output Format

- [x] Stdout (default with markdown rendering)
- [x] Silent mode (`-s, --silent`) - agent response only, no stats
- [x] Session sharing (`--share <path>`) - exports to markdown
- [x] Gist sharing (`--share-gist`) - exports to secret GitHub gist

**Silent mode output**: Clean agent response text suitable for scripting/parsing.

## Parallel Execution

### Rate Limits

- Depends on GitHub Copilot subscription tier
- Individual: Standard limits
- Business/Enterprise: Higher limits

### Concurrent Sessions

- Yes, multiple instances can run in parallel
- Each session independent
- Session resume capability with `--resume [sessionId]`

### Resource Requirements

- Memory: Moderate
- CPU: Light (API calls are remote)
- Network: Required for all operations
- No offline mode

## Authentication

### Methods

1. **GitHub Token**: Environment variable `GITHUB_TOKEN`
2. **GitHub CLI Auth**: Uses `gh auth` credentials
3. **Copilot Subscription**: Required (Individual, Business, or Enterprise)

```bash
# Verify authentication
gh auth status

# Copilot CLI uses same auth as gh CLI
copilot -p "test" --allow-all
```

## Orchestration Assessment

### Can participate in autonomous workflow?

[x] Yes - Full headless support

### Capabilities for Orchestration

- **Non-interactive mode**: `-p, --prompt` flag
- **Full auto-approval**: `--yolo` or `--allow-all` flag
- **Task input**: Command line argument
- **Completion detection**: Exit codes, silent mode output
- **File modification**: Enabled with `--allow-all-tools`
- **Session export**: `--share` flag for audit trail
- **Granular permissions**: `--allow-tool`, `--deny-tool` for fine control

### Unique Features

- **Multi-model support**: GPT-5.x, Claude models, Gemini available
- **MCP Integration**: Built-in GitHub MCP server, custom MCP support
- **Session management**: `--continue`, `--resume` for session persistence
- **URL permissions**: `--allow-url`, `--deny-url` for network access control
- **Path permissions**: `--allow-all-paths` or `--add-dir` for filesystem access

### Available Models

```
claude-sonnet-4.5, claude-haiku-4.5, claude-opus-4.5, claude-sonnet-4,
gpt-5.2-codex, gpt-5.1-codex-max, gpt-5.1-codex, gpt-5.2, gpt-5.1,
gpt-5, gpt-5.1-codex-mini, gpt-5-mini, gpt-4.1, gemini-3-pro-preview
```

### Limitations

- Requires GitHub Copilot subscription
- Network connectivity required
- No local/offline mode

### Integration Complexity

**Low** - Full headless support with comprehensive automation flags. Very similar to Claude Code CLI.

## Recommended Orchestration Pattern

```bash
# For spec-kitty orchestration
copilot -p "$(cat tasks/WP01-prompt.md)" \
  --yolo \
  --silent \
  --share ./session-WP01.md

# Or with explicit permissions
copilot -p "$(cat tasks/WP01-prompt.md)" \
  --allow-all-tools \
  --allow-all-paths \
  --silent

# With specific model
copilot --model gpt-5.2-codex -p "$(cat tasks/WP01-prompt.md)" --yolo
```

## Comparison to Other Agents

| Feature | Copilot CLI | Claude Code | Codex CLI |
|---------|-------------|-------------|-----------|
| Headless flag | `-p, --prompt` | `-p, --print` | `exec` |
| Full auto | `--yolo`, `--allow-all` | `--dangerously-skip-permissions` | `--full-auto` |
| Silent output | `-s, --silent` | N/A | `--json` |
| Session resume | `--resume` | `--resume` | N/A |
| Multi-model | Yes (14+ models) | No (Claude only) | No (OpenAI only) |
| MCP support | Yes (built-in) | Yes | Yes |

## Legacy: gh copilot Extension

**DEPRECATED** - The `gh copilot` extension has been deprecated in favor of the standalone Copilot CLI.

```bash
# Legacy (DO NOT USE)
$ gh copilot suggest "list files"
The gh-copilot extension has been deprecated in favor of the newer GitHub Copilot CLI.
```

The old extension only supported `suggest` and `explain` commands for shell/git/gh command generation. The new standalone CLI is a full agentic coding assistant.

## Sources

- [GitHub Copilot CLI Repository](https://github.com/github/copilot-cli)
- [Deprecation Announcement (Sep 2025)](https://github.blog/changelog/2025-09-25-upcoming-deprecation-of-gh-copilot-cli-extension)
- Local CLI testing: `copilot --help` (v0.0.384)
- `copilot help config`, `copilot help permissions`, `copilot help environment`
