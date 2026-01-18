# Agent: Qwen Code

## Basic Info
- **Directory**: `.qwen/`
- **Primary Interface**: CLI
- **Vendor**: Alibaba (Qwen Team)
- **Documentation**: https://qwenlm.github.io/qwen-code-docs/
- **GitHub**: https://github.com/QwenLM/qwen-code

## CLI Availability

### Installation
```bash
# NPM global install (recommended)
npm install -g @qwen-code/qwen-code@latest

# Homebrew (macOS/Linux)
brew install qwen-code
```

**Prerequisites**: Node.js 20 or higher

### Verification
```bash
which qwen
qwen --version
qwen --help
```

### Local Test Results
```bash
$ which qwen
/opt/homebrew/bin/qwen

$ qwen --version
0.7.1

$ echo 'print("Hello")' | qwen -p "What does this code do?" --output-format json
[
  {"type":"system","subtype":"init","session_id":"uuid","cwd":"/path","tools":[...],"model":"qwen3-coder-plus"},
  {"type":"assistant","message":{"content":[{"type":"text","text":"..."}]}},
  {"type":"result","subtype":"success","duration_ms":2017,"usage":{...}}
]
```

## Task Specification

### How to Pass Instructions
- [x] Command line argument (`qwen "your prompt"` or `qwen -p "prompt"`)
- [x] Stdin (`echo "code" | qwen`)
- [x] Stdin + prompt combined (`cat file.md | qwen -p "analyze"`)
- [x] Prompt file in working directory (uses AGENTS.md context)
- [ ] Environment variable

### Example Invocation
```bash
# One-shot headless execution
qwen "Write a function to reverse a string in Python" --output-format json

# Stdin piping with prompt
cat src/main.py | qwen -p "Review this code for bugs" --output-format json

# YOLO mode (auto-approve all actions)
qwen "Fix all linting errors" --yolo --output-format json

# With specific model
qwen -m qwen3-coder-480b "Explain this codebase" --output-format json

# Stream JSON for real-time monitoring
qwen "Implement a REST API" --output-format stream-json --include-partial-messages

# Resume previous session
qwen --continue
qwen --resume <session-id>
```

### Context Handling
- Automatically indexes the current working directory
- Respects `.gitignore` patterns
- Uses `AGENTS.md` or `.qwen/AGENTS.md` for project-specific instructions
- Supports `@filename` syntax to reference specific files
- `--include-directories` flag for additional folders
- `--all-files` flag to include everything

## Completion Detection

### Exit Codes
| Code | Meaning |
|------|---------|
| 0 | Success |
| Non-zero | Error (API errors, authentication failures, etc.) |

*Note: Qwen Code uses non-zero exit codes for errors. Specific codes follow similar patterns to Gemini CLI (fork origin).*

### Output Format
- [x] Stdout (plain text) - default
- [x] Stdout (JSON) - `--output-format json`
- [x] Streaming JSONL - `--output-format stream-json`
- [x] Structured logs (stats, tool calls, token usage in JSON)

**JSON Output Structure** (array format):
```json
[
  {
    "type": "system",
    "subtype": "init",
    "session_id": "uuid",
    "cwd": "/path/to/project",
    "tools": ["task", "read_file", "grep_search", "glob", ...],
    "model": "qwen3-coder-plus",
    "qwen_code_version": "0.7.1"
  },
  {
    "type": "assistant",
    "message": {
      "role": "assistant",
      "content": [{"type": "text", "text": "response here"}]
    }
  },
  {
    "type": "result",
    "subtype": "success",
    "duration_ms": 2017,
    "num_turns": 1,
    "usage": {
      "input_tokens": 500,
      "output_tokens": 200,
      "cache_read_input_tokens": 0
    }
  }
]
```

## Parallel Execution

### Rate Limits
| Auth Method | Rate Limit |
|-------------|------------|
| Qwen OAuth (free tier) | 2,000 requests/day |
| OpenAI-compatible API | Depends on provider |
| DashScope API | Alibaba Cloud limits |

### Concurrent Sessions
- Multiple CLI instances can run in parallel in separate directories
- Each session gets a unique `session_id`
- Session data stored in `~/.qwen/projects/<sanitized-cwd>/chats/`
- Workspace isolation via `--include-directories`

### Resource Requirements
- 256K token context window (native), up to 1M with extrapolation
- Model: Qwen3-Coder-480B-A35B (480B params, 35B active via MoE)
- Tools: file operations, shell commands, web fetch, grep, glob

## Authentication

### Option 1: Qwen OAuth (Recommended - Free)
```bash
# Interactive login
qwen
# Run /auth command
# Select "Qwen OAuth" and complete browser login
# Credentials cached in ~/.qwen/settings.json
```

**Free Tier**: 2,000 requests/day

### Option 2: OpenAI-Compatible API
```bash
export OPENAI_API_KEY="your-api-key-here"
export OPENAI_BASE_URL="https://api.openai.com/v1"  # optional
export OPENAI_MODEL="gpt-4o"  # optional
```

### Option 3: DashScope API (Alibaba Cloud)
```bash
# Via settings.json or environment variables
# Requires Alibaba Cloud account
```

### Option 4: Settings File
```json
// ~/.qwen/settings.json or .qwen/settings.json
{
  "apiKey": "your-api-key",
  "baseUrl": "https://api.example.com/v1",
  "model": "model-name"
}
```

**Environment Variables**:
- `OPENAI_API_KEY` - API key for OpenAI-compatible endpoints
- `OPENAI_BASE_URL` - Custom API endpoint
- `OPENAI_MODEL` - Model to use
- `TAVILY_API_KEY` - Tavily web search
- `GOOGLE_API_KEY` - Google Custom Search
- `GOOGLE_SEARCH_ENGINE_ID` - Google CSE ID

## Orchestration Assessment

### Can participate in autonomous workflow?
[x] Yes

### Capabilities
- **Headless execution**: Full support with `-p` flag
- **JSON output**: Structured parsing with `--output-format json`
- **Streaming**: Real-time progress with `--output-format stream-json`
- **Auto-approval**: `--yolo` flag for non-interactive operation
- **Session continuity**: `--continue` and `--resume` flags
- **Multi-auth**: Supports OAuth, OpenAI-compatible, and custom endpoints

### Limitations
- Requires authentication setup (OAuth or API key)
- Rate limits on free tier (2,000/day)
- Fork of Gemini CLI (may lag on features)

### Integration Complexity
**Low** - Full CLI with headless mode, JSON output, session management, and familiar Gemini CLI interface

## Advanced Features

### MCP Server Support
```bash
# Manage MCP servers
qwen mcp list
qwen mcp add <server-name> <command>

# Use specific MCP servers
qwen --allowed-mcp-server-names server1,server2 "your prompt"
```

### Extensions
```bash
# List extensions
qwen --list-extensions

# Use specific extensions
qwen -e extension1,extension2 "your prompt"
```

### Approval Modes
- `plan` - Plan only, no execution
- `default` - Prompt for each action
- `auto-edit` - Auto-approve file edits only
- `yolo` - Auto-approve everything

### Skills & SubAgents
```bash
# Enable experimental skills
qwen --experimental-skills "your prompt"

# Agents: general-purpose
```

### Input/Output Formats
```bash
# Input format
qwen --input-format text "prompt"     # Default text
qwen --input-format stream-json       # Stream JSON from stdin

# Output format
qwen --output-format text             # Human-readable
qwen --output-format json             # Buffered JSON array
qwen --output-format stream-json      # Line-delimited JSONL
```

## CI/CD Integration Example

```bash
#!/bin/bash
# ci-code-review.sh

# Run code review with JSON output
result=$(qwen -p "Review the changes in this PR for security issues" \
  --output-format json)

# Parse the result (last element contains summary)
response=$(echo "$result" | jq -r '.[-1].result // empty')
is_error=$(echo "$result" | jq -r '.[-1].is_error // false')

if [ "$is_error" = "true" ]; then
  echo "Error occurred"
  exit 1
fi

echo "$response"
```

## Comparison with Gemini CLI

Qwen Code is a fork of Gemini CLI, optimized for Qwen3-Coder:

| Feature | Gemini CLI | Qwen Code |
|---------|------------|-----------|
| Model | Gemini 2.5 Pro | Qwen3-Coder-480B |
| Free tier | 60 req/min, 1000/day | 2,000 req/day |
| Context | 1M tokens | 256K-1M tokens |
| Auth | Google OAuth, API key | Qwen OAuth, OpenAI-compat |
| CLI flags | Nearly identical | Adds --experimental-skills |
| JSON format | Single object | Array of events |

## Sources
- [Qwen Code Documentation](https://qwenlm.github.io/qwen-code-docs/)
- [GitHub Repository](https://github.com/QwenLM/qwen-code)
- [Qwen3-Coder Blog Post](https://qwenlm.github.io/blog/qwen3-coder/)
- [Headless Mode Guide](https://qwenlm.github.io/qwen-code-docs/en/users/features/headless/)
- [Troubleshooting Guide](https://qwenlm.github.io/qwen-code-docs/en/users/support/troubleshooting/)
- [NPM Package](https://www.npmjs.com/package/@qwen-code/qwen-code)
