# Agent: Kilocode

## Basic Info
- **Directory**: `.kilocode/`
- **Primary Interface**: CLI / IDE (VS Code extension with full-featured CLI)
- **Vendor**: Kilo Code (kilo.ai)
- **Documentation**: https://kilo.ai/docs/

## CLI Availability

### Installation

```bash
# npm (global installation)
npm install -g @kilocode/cli

# Verify installation
kilocode --version
# or
kilo --version
```

**Package**: `@kilocode/cli` on npm
**Latest Version**: 0.23.1 (as of 2026-01-17)
**License**: Apache-2.0

### Verification
```bash
# Command to verify installation
which kilocode
kilocode --version
```

### Local Test Results
```bash
$ which kilocode
/opt/homebrew/bin/kilocode

$ kilocode --version
0.23.1

$ kilocode --help
Usage: kilocode [options] [command] [prompt]

Kilo Code Terminal User Interface - AI-powered coding assistant

Arguments:
  prompt                           The prompt or command to execute

Options:
  -V, --version                    output the version number
  -m, --mode <mode>                Set the mode of operation (architect, code,
                                   ask, debug, orchestrator)
  -w, --workspace <path>           Path to the workspace directory
  -a, --auto                       Run in autonomous mode (non-interactive)
  --yolo                           Auto-approve all tool permissions
  -j, --json                       Output messages as JSON (requires --auto)
  -i, --json-io                    Bidirectional JSON mode (no TUI, stdin/stdout enabled)
  -c, --continue                   Resume the last conversation from this workspace
  -t, --timeout <seconds>          Timeout in seconds for autonomous mode (requires --auto)
  -p, --parallel                   Run in parallel mode - creates separate git branch
  -eb, --existing-branch <branch>  (Parallel mode only) Work on an existing branch
  -pv, --provider <id>             Select provider by ID (e.g., 'kilocode-1')
  -mo, --model <model>             Override model for the selected provider
  -s, --session <sessionId>        Restore a session by ID
  -f, --fork <shareId>             Fork a session by ID
  --nosplash                       Disable welcome message and update notifications
  --append-system-prompt <text>    Append custom instructions to the system prompt
  --on-task-completed <prompt>     Send a custom prompt when task completes
  --attach <path>                  Attach a file to the prompt (supports images)
  -h, --help                       display help for command

Commands:
  auth                             Manage authentication for the Kilo Code CLI
  config                           Open the configuration file in your default editor
  debug [mode]                     Run a system compatibility check
```

## Task Specification

### How to Pass Instructions
- [x] Command line argument (positional prompt argument)
- [x] Stdin (with `--json-io` mode)
- [ ] File path (--file, -f)
- [ ] Prompt file in working directory
- [x] Environment variable (for configuration)

### Example Invocation
```bash
# Interactive mode
kilocode "Refactor the authentication module"

# Autonomous mode (non-interactive)
kilocode -a -t 300 "Fix all TypeScript errors in src/"

# Autonomous with JSON output
kilocode -a -j "Generate unit tests for utils.ts"

# Fully autonomous with auto-approve (YOLO mode)
kilocode -a --yolo "Implement feature X according to spec.md"

# Bidirectional JSON mode for programmatic integration
kilocode -i "Your task here"

# Parallel mode (creates separate branch)
kilocode -p "Implement WP01"

# Specific provider and model
kilocode -pv openai-1 -mo gpt-4o "Your task"
```

### Context Handling
- Automatically reads codebase from workspace directory (`-w` flag or current directory)
- Supports MCP (Model Context Protocol) for custom tools and APIs
- Configuration stored at `~/.kilocode/config.json`
- Environment variable overrides for ephemeral operation (useful in containers)

## Completion Detection

### Exit Codes
| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error / Task failed |

### Output Format
- [x] Stdout (plain text) - default TUI mode
- [x] Stdout (JSON) - with `--json` flag
- [x] Structured logs - via `--json-io` mode
- [ ] File output

## Parallel Execution

### Rate Limits
Depends on the underlying LLM provider (OpenAI, Anthropic, etc.). No Kilocode-specific rate limits documented.

### Concurrent Sessions
- Yes, multiple instances can run simultaneously
- Built-in `--parallel` flag creates separate git branches automatically
- Can use `--existing-branch` to target specific branches
- Each session can have a unique `--session` ID

### Resource Requirements
- Node.js 22+ required
- Memory depends on context size and provider
- Token limits depend on configured model

## Orchestration Assessment

### Can participate in autonomous workflow?
[x] Yes

### Limitations
- Requires authentication via `kilocode auth`
- YOLO mode (`--yolo`) needed for fully unattended operation
- Timeout must be set for autonomous mode

### Integration Complexity
**Low** - Kilocode has excellent CLI support with:
- Full autonomous mode (`-a`)
- JSON I/O for programmatic integration (`-i`, `-j`)
- Parallel branch support (`-p`)
- Timeout control (`-t`)
- Custom system prompts (`--append-system-prompt`)

## VS Code Extension Patterns

Kilocode demonstrates the gold standard for VS Code extension CLI support:
- The CLI bundles the entire extension codebase at build time using esbuild
- `ExtensionHost` class provides a VS Code API facade that maps VS Code-specific APIs to CLI equivalents
- Extension code runs unmodified in both VS Code and CLI environments
- Full feature parity between VS Code extension and CLI

### Headless Workarounds
- No workarounds needed - native CLI support
- Works in CI/CD pipelines
- Runs anywhere Node.js runs (serverless, cron jobs, containers)

## Sources
- [Kilo Code VS Code Marketplace](https://marketplace.visualstudio.com/items?itemName=kilocode.Kilo-Code)
- [Kilo Code Documentation](https://kilo.ai/docs/)
- [npm: @kilocode/cli](https://www.npmjs.com/package/@kilocode/cli)
- [GitHub: Kilo-Org/kilocode](https://github.com/Kilo-Org/kilocode)
- [DeepWiki: CLI Interface](https://deepwiki.com/Kilo-Org/kilocode/7-cli-interface)
- [TechNow: Kilo Code Overview](https://tech-now.io/en/blogs/kilo-code-the-new-open-source-ai-coding-agent-for-vs-code)
- Local CLI testing (2026-01-18)
