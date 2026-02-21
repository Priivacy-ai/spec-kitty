# Agent: Cursor

## Basic Info

- **Directory**: `.cursor/`
- **Primary Interface**: IDE (VS Code fork) + CLI Agent
- **Vendor**: Cursor (Anysphere)
- **Documentation**: <https://cursor.com/docs/cli/headless>

## CLI Availability

### Installation

```bash
# Cursor CLI is bundled with Cursor IDE
# After installing Cursor.app, the CLI is available

# macOS: Install shell integration
cursor agent install-shell-integration

# Or download Cursor from https://cursor.com
```

### Verification

```bash
which cursor && cursor --version
```

### Local Test Results

```bash
$ cursor --version
Cursor 2.0.64
25412918da7e74b2686b25d62da1f01cfcd27680
arm64

$ which cursor
/usr/local/bin/cursor

$ cursor agent about
CLI Version         2026.01.17-d239e66
Model               Auto
OS                  darwin (arm64)
```

**Status**: CLI is installed and functional. Agent subcommand is available.

## Task Specification

### How to Pass Instructions

- [x] Command line argument - `cursor agent -p "Your prompt here"`
- [ ] Stdin - Not well supported (known issue: may read subsequent commands)
- [ ] File path (--file, -f) - Not directly, use `$(cat prompt.txt)` workaround
- [x] Prompt file in working directory - `cursor agent -p "$(cat prompt.md)"`
- [x] Environment variable - `CURSOR_API_KEY` for authentication

### Example Invocation

```bash
# Basic non-interactive prompt (headless mode)
cursor agent -p "What is 2+2?"

# With JSON output
cursor agent -p --output-format json "Analyze this code"

# With streaming JSON output
cursor agent -p --output-format stream-json --stream-partial-output "Review code"

# Allow file modifications
cursor agent -p --force "Add JSDoc comments to src/main.js"

# With specific model
cursor agent -p --model gpt-5 "Fix performance issues"

# Plan mode (read-only)
cursor agent -p --mode plan "Design an architecture"

# Ask mode (Q&A)
cursor agent -p --mode ask "What does this function do?"

# Resume a chat
cursor agent resume

# Cloud handoff (push to cloud agent)
cursor agent -c "Continue this task"
```

### Context Handling

- Operates in workspace directory (cwd or `--workspace <path>`)
- Can read files via tool calling by referencing paths in prompt
- Supports image analysis by referencing image paths
- MCP server support with `--approve-mcps` for headless auto-approval

## Completion Detection

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| Non-zero | Error |

**Known Issue**: CLI can hang indefinitely after responding, even in `--print` mode. May need timeout wrapper.

### Output Format

- [x] Stdout (plain text) - `--output-format text` (default)
- [x] Stdout (JSON) - `--output-format json`
- [x] Stdout (stream-json) - `--output-format stream-json` for NDJSON events
- [ ] File output - Results go to stdout
- [ ] Structured logs - JSON format provides structure

**JSON output includes**:

- System init events
- Delta events (incremental output)
- Tool call events
- Final result object

**Stream-JSON events**:

- Real-time progress tracking
- Works with jq pipelines
- Enable `--stream-partial-output` for incremental deltas

## Parallel Execution

### Rate Limits

- Depends on Cursor subscription tier
- Business/Pro: Higher limits
- Free tier: Limited usage

### Concurrent Sessions

- Yes, multiple instances can run
- Each session has unique chat ID
- Can resume sessions with `cursor agent resume`

### Resource Requirements

- Memory: Moderate
- CPU: Light (API calls are remote)
- Network: Required for all operations
- No offline mode

## Authentication

### Methods

1. **API Key**: `--api-key <key>` or `CURSOR_API_KEY` env var
2. **Browser Login**: `cursor agent login`
3. **Headless Login**: Set `NO_OPEN_BROWSER=1` for non-interactive auth

```bash
# API key method (recommended for automation)
export CURSOR_API_KEY=your_api_key
cursor agent -p "Task here"

# Browser login
cursor agent login
```

## Orchestration Assessment

### Can participate in autonomous workflow?

[x] Yes

### Capabilities for Orchestration

- **Non-interactive mode**: `-p, --print` flag
- **Task input**: Command line argument (stdin has issues)
- **Completion detection**: JSON output format, exit codes (with caveats)
- **File modification**: `--force` flag for actual edits
- **Modes**: plan (read-only), ask (Q&A), default (full agent)
- **Cloud handoff**: Push to cloud agent for background execution

### Unique Features

- **Cloud handoff**: Push local conversation to cloud for background processing
- **Plan mode**: Design-first approach before coding
- **Ask mode**: Q&A without modifications
- **MCP support**: `--approve-mcps` for headless MCP server auto-approval
- **Browser automation**: `--browser` flag for web tasks
- **Shell integration**: Works within terminal environment

### Limitations

- **Hang issue**: CLI can hang after completion - may need timeout wrapper
- **Stdin issues**: Can't reliably pipe prompts, use `$(cat file)` workaround
- **Auth required**: Needs Cursor subscription
- **Exit codes**: Not well documented, rely on output parsing

### Integration Complexity

**Medium** - Full headless support exists but has quirks (hanging, stdin issues) that require workarounds.

## Recommended Orchestration Pattern

```bash
# For spec-kitty orchestration (with timeout workaround)
timeout 300 cursor agent -p --force --output-format json \
  "$(cat tasks/WP02-prompt.md)"

# Or with explicit workspace
timeout 300 cursor agent -p --force --output-format json \
  --workspace /path/to/project \
  "Complete this work package: $(cat tasks/WP02-prompt.md)"

# For read-only analysis
timeout 60 cursor agent -p --mode ask --output-format json \
  "Review this code for issues"
```

## Comparison to Other Agents

| Feature | Cursor | Claude Code | Codex |
|---------|--------|-------------|-------|
| Headless flag | `-p, --print` | `-p, --print` | `exec` |
| File edits | `--force` | `--allowedTools` | `--full-auto` |
| JSON output | Yes | Yes | Yes |
| Stdin support | Problematic | Yes | Yes |
| Cloud handoff | Yes | No | No |
| Hanging issue | Yes | No | No |

## Sources

- [Cursor CLI Overview](https://cursor.com/docs/cli/overview)
- [Cursor Headless CLI Documentation](https://cursor.com/docs/cli/headless)
- [Cursor CLI Blog Announcement](https://cursor.com/blog/cli)
- [Cursor Forum: CLI Agent Modes (Jan 2026)](https://forum.cursor.com/t/cursor-cli-jan-16-2026-cli-agent-modes-and-cloud-handoff/149171)
- Local CLI testing: `cursor agent --help` (v2026.01.17-d239e66)
