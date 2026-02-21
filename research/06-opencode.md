# Agent: OpenCode

## Basic Info

- **Directory**: `.opencode/`
- **Primary Interface**: CLI (TUI default, headless available)
- **Vendor**: OpenCode AI (anomalyco)
- **Documentation**: <https://opencode.ai/docs/cli/>

## CLI Availability

### Installation

```bash
# Via official installer
curl -fsSL https://opencode.ai/install | sh

# Or via npm
npm install -g opencode
```

### Verification

```bash
which opencode && opencode --version
```

### Local Test Results

```bash
$ opencode --version
1.1.14

$ which opencode
/Users/robert/.opencode/bin/opencode
```

**Status**: CLI is installed and functional.

## Task Specification

### How to Pass Instructions

- [x] Command line argument - `opencode run "Your prompt here"`
- [x] Stdin - Can pipe prompts via stdin
- [x] File path (--file, -f) - `-f, --file` to attach files to message
- [x] Prompt file in working directory - `cat prompt.md | opencode run`
- [ ] Environment variable - Not supported

### Example Invocation

```bash
# Basic non-interactive prompt
opencode run "What is 2+2?"

# With specific model
opencode run --model anthropic/claude-sonnet-4-20250514 "Review this code"

# With JSON output
opencode run --format json "Analyze this project"

# Continue previous session
opencode run --continue "Follow up question"

# Resume specific session
opencode run --session <session_id> "Continue"

# Attach files
opencode run -f file1.py -f file2.py "Review these files"

# With custom title
opencode run --title "Code Review" "Check for bugs"

# Share session
opencode run --share "Generate a report"

# With model variant (reasoning effort)
opencode run --variant high "Complex analysis"
```

### Context Handling

- Automatically operates in current directory
- Can specify project path: `opencode [project]`
- Multi-provider support: 75+ LLM providers
- Files can be attached with `-f` flag

## Completion Detection

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| Non-zero | Error |

Note: Specific exit codes not documented. Use `--format json` for structured output.

### Output Format

- [x] Stdout (plain text) - Default formatted output
- [x] Stdout (JSON) - `--format json` for raw JSON events
- [ ] File output - Results go to stdout
- [ ] Structured logs - JSON events provide structure

### Parsing Output

```bash
# JSON output
opencode run --format json "prompt"

# Export session as JSON
opencode export <sessionID>

# Import session
opencode import session.json
```

## Parallel Execution

### Rate Limits

- Depends on underlying provider (Anthropic, OpenAI, Google, etc.)
- Multi-provider means flexible rate limit management
- Can switch providers if one is rate-limited

### Concurrent Sessions

- Yes, multiple instances can run
- Each session has unique ID
- Sessions can be exported/imported

### Resource Requirements

- Memory: Moderate (Node.js runtime)
- CPU: Light (API calls are remote)
- Network: Required for cloud providers
- Can use local models via `--oss` providers (Ollama, LM Studio)

## Orchestration Assessment

### Can participate in autonomous workflow?

[x] Yes

### Capabilities for Orchestration

- **Non-interactive mode**: `run` subcommand
- **Task input**: Accepts prompts via argument, stdin, or with `-f` files
- **Completion detection**: JSON format output
- **Multi-provider**: Can use different models/providers
- **Session management**: Continue, resume, export/import
- **Server mode**: `opencode serve` for headless HTTP server

### Unique Features

- **Multi-provider**: 75+ LLM providers supported
- **Server mode**: `opencode serve` exposes HTTP API
- **Web UI**: `opencode web` for browser interface
- **Attachable**: `opencode attach <url>` to connect to running server
- **GitHub integration**: `opencode github` and `opencode pr <number>`

### Limitations

- No explicit dangerous/bypass mode documented
- Exit codes not well documented
- Newer project, documentation still evolving

### Integration Complexity

**Low** - Clean `run` subcommand with JSON output and multi-provider flexibility.

## Recommended Orchestration Pattern

```bash
# For spec-kitty orchestration
cat tasks/WP01-prompt.md | opencode run \
  --model anthropic/claude-sonnet-4-20250514 \
  --format json

# Or with file attachment
opencode run \
  -f tasks/WP01-prompt.md \
  --format json \
  "Complete this work package"

# Using server mode for multiple requests
opencode serve --port 4096 &
# Then attach from multiple clients
opencode run --attach http://localhost:4096 "Task 1"
```

## Sources

- [OpenCode CLI Documentation](https://opencode.ai/docs/cli/)
- [OpenCode Commands](https://opencode.ai/docs/commands/)
- [GitHub Repository](https://github.com/opencode-ai/opencode)
- Local CLI testing: `opencode --help` (v1.1.14)
