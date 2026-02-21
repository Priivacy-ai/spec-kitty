# Agent: Claude Code

## Basic Info

- **Directory**: `.claude/`
- **Primary Interface**: CLI
- **Vendor**: Anthropic
- **Documentation**: <https://code.claude.com/docs/en/headless>

## CLI Availability

### Installation

```bash
# Via npm (official package)
npm install -g @anthropic-ai/claude-code

# Or via Anthropic installer
curl -fsSL https://claude.ai/install | sh
```

### Verification

```bash
which claude && claude --version
```

### Local Test Results

```bash
$ claude --version
2.1.12 (Claude Code)

$ which claude
/Users/robert/.local/bin/claude
```

**Status**: CLI is installed and functional.

## Task Specification

### How to Pass Instructions

- [x] Command line argument - `claude -p "Your prompt here"`
- [x] Stdin - `echo "prompt" | claude -p`
- [ ] File path (--file, -f) - `--file` is for downloading file resources, not prompt files
- [x] Prompt file in working directory - Read via stdin: `cat prompt.md | claude -p`
- [ ] Environment variable - Not supported

### Example Invocation

```bash
# Basic non-interactive prompt
claude -p "What is 2+2?"

# With JSON output
claude -p "Summarize this project" --output-format json

# With specific tools allowed
claude -p "Run tests and fix failures" --allowedTools "Bash,Read,Edit"

# With structured output
claude -p "Extract function names" --output-format json --json-schema '{"type":"object","properties":{"functions":{"type":"array"}}}'

# Continue a conversation
claude -p "Follow up question" --continue

# Resume specific session
claude -p "Continue" --resume <session_id>
```

### Context Handling

- Automatically indexes the working directory
- Respects `.gitignore` and similar patterns
- Can add additional directories with `--add-dir`
- Uses tools (Read, Glob, Grep) to explore codebase on demand

## Completion Detection

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success - task completed |
| 1 | Error - various failures |

Note: Exit codes are not extensively documented. Recommend checking output for success indicators.

### Output Format

- [x] Stdout (plain text) - Default with `-p`
- [x] Stdout (JSON) - `--output-format json`
- [x] Stdout (stream-json) - `--output-format stream-json` for real-time streaming
- [ ] File output - Results go to stdout only
- [ ] Structured logs - Use `--debug` for verbose logging

**JSON output includes**:

- `result`: Text response
- `session_id`: For conversation continuity
- `structured_output`: When using `--json-schema`

### Parsing Output

```bash
# Extract text result
claude -p "prompt" --output-format json | jq -r '.result'

# Get session ID for resumption
session_id=$(claude -p "Start" --output-format json | jq -r '.session_id')
```

## Parallel Execution

### Rate Limits

- Depends on Anthropic API tier
- Pro subscribers: Higher limits
- API key users: Per-key quotas
- Not explicitly documented in CLI

### Concurrent Sessions

- Yes, multiple instances can run simultaneously
- Each session has unique `session_id`
- No explicit locking mechanism

### Resource Requirements

- Memory: Moderate (Node.js runtime)
- CPU: Light (API calls are remote)
- Network: Required for all operations
- Tokens: Depends on prompt and response size

## Orchestration Assessment

### Can participate in autonomous workflow?

[x] Yes

### Capabilities for Orchestration

- **Non-interactive mode**: `-p` flag enables headless operation
- **Task input**: Accepts prompts via argument or stdin (can read prompt files)
- **Completion detection**: JSON output with session tracking
- **Tool permissions**: `--allowedTools` for pre-approval
- **Dangerous mode**: `--dangerously-skip-permissions` for fully automated (sandboxed only)

### Limitations

- No native prompt file flag (must use stdin piping)
- Exit codes not extensively documented
- Requires internet connection (no offline mode)

### Integration Complexity

**Low** - Well-documented headless mode with JSON output and session management.

## Recommended Orchestration Pattern

```bash
# For spec-kitty orchestration
cat tasks/WP01-prompt.md | claude -p \
  --output-format json \
  --allowedTools "Read,Write,Edit,Bash" \
  --append-system-prompt "Complete this work package. Report completion status."
```

## Sources

- [Claude Code Headless Documentation](https://code.claude.com/docs/en/headless)
- [Anthropic Engineering Best Practices](https://www.anthropic.com/engineering/claude-code-best-practices)
- Local CLI testing: `claude --help` (v2.1.12)
