# Agent: GitHub Codex (OpenAI Codex CLI)

## Basic Info

- **Directory**: `.codex/`
- **Primary Interface**: CLI
- **Vendor**: OpenAI
- **Documentation**: <https://developers.openai.com/codex/cli/>

## CLI Availability

### Installation

```bash
# Via Homebrew
brew install codex

# Or via npm
npm install -g @openai/codex
```

### Verification

```bash
which codex && codex --version
```

### Local Test Results

```bash
$ codex --version
codex-cli 0.87.0

$ which codex
/opt/homebrew/bin/codex
```

**Status**: CLI is installed and functional.

## Task Specification

### How to Pass Instructions

- [x] Command line argument - `codex exec "Your prompt here"`
- [x] Stdin - `echo "prompt" | codex exec -` or without argument reads from stdin
- [ ] File path (--file, -f) - Not directly, but can read via stdin
- [x] Prompt file in working directory - Read via stdin: `cat prompt.md | codex exec -`
- [ ] Environment variable - Not supported

### Example Invocation

```bash
# Basic non-interactive prompt
codex exec "What is 2+2?"

# With JSON output
codex exec "Summarize this project" --json

# With automatic approval (sandboxed)
codex exec "Run tests" --full-auto

# With specific sandbox mode
codex exec "Fix the bug" --sandbox workspace-write

# Dangerous mode (fully automated, no sandbox)
codex exec "Deploy" --dangerously-bypass-approvals-and-sandbox

# Output last message to file
codex exec "Generate report" -o output.txt

# With specific model
codex exec "Review code" --model o3

# Resume previous session
codex exec resume --last "Continue from here"

# Code review mode
codex review
```

### Context Handling

- Automatically operates in current Git repository
- `--cd <DIR>` to specify working directory
- `--add-dir <DIR>` to add additional writable directories
- `--skip-git-repo-check` to run outside Git repos

## Completion Detection

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success - task completed |
| Non-zero | Error or failure |

Note: Specific exit codes not extensively documented. Use `--json` for structured output.

### Output Format

- [x] Stdout (plain text) - Default formatted output
- [x] Stdout (JSON) - `--json` for newline-delimited JSON events
- [x] File output - `-o, --output-last-message <FILE>`
- [ ] Structured logs - JSON events include state changes

**JSON output includes**:

- Event stream with state changes
- Final message can be captured with `-o` flag

### Parsing Output

```bash
# JSON events to stdout
codex exec "prompt" --json

# Capture last message to file
codex exec "prompt" -o result.txt

# With output schema validation
codex exec "Extract data" --output-schema schema.json
```

## Parallel Execution

### Rate Limits

- Depends on OpenAI API tier
- Free tier: Limited requests
- API key users: Per-key quotas
- Rate limits not explicitly in CLI docs

### Concurrent Sessions

- Yes, multiple instances can run simultaneously
- Sessions have unique IDs
- Can resume sessions by ID

### Resource Requirements

- Memory: Moderate (Rust binary)
- CPU: Light (API calls are remote)
- Network: Required for all operations
- Tokens: Depends on model and prompt size

## Orchestration Assessment

### Can participate in autonomous workflow?

[x] Yes

### Capabilities for Orchestration

- **Non-interactive mode**: `exec` subcommand (alias: `e`)
- **Task input**: Accepts prompts via argument or stdin
- **Completion detection**: JSON output with `-o` for final message
- **Sandbox modes**: `read-only`, `workspace-write`, `danger-full-access`
- **Full automation**: `--full-auto` or `--dangerously-bypass-approvals-and-sandbox`

### Limitations

- No native prompt file flag (must use stdin)
- Requires Git repository by default (override with flag)
- Exit codes not well documented

### Integration Complexity

**Low** - Well-designed `exec` subcommand specifically for automation with JSON output and sandbox controls.

## Recommended Orchestration Pattern

```bash
# For spec-kitty orchestration
cat tasks/WP01-prompt.md | codex exec - \
  --json \
  --full-auto \
  -o /tmp/codex-result.txt

# Or with bypass for fully trusted environments
cat tasks/WP01-prompt.md | codex exec - \
  --dangerously-bypass-approvals-and-sandbox \
  --json
```

## GitHub Actions Integration

OpenAI provides official GitHub Action:

```yaml
- uses: openai/codex-action@v1
  with:
    prompt: "Review this PR"
```

## Sources

- [Codex CLI Documentation](https://developers.openai.com/codex/cli/)
- [Codex CLI Features](https://developers.openai.com/codex/cli/features/)
- [Codex CLI Reference](https://developers.openai.com/codex/cli/reference/)
- [GitHub Repository](https://github.com/openai/codex)
- Local CLI testing: `codex --help` (v0.87.0)
