# Agent: Google Gemini (Gemini CLI)

## Basic Info
- **Directory**: `.gemini/`
- **Primary Interface**: CLI
- **Vendor**: Google
- **Documentation**: https://developers.google.com/gemini-code-assist/docs/gemini-cli
- **GitHub**: https://github.com/google-gemini/gemini-cli

## CLI Availability

### Installation
```bash
# NPX (no installation required)
npx @google/gemini-cli

# NPM global install
npm install -g @google/gemini-cli

# Homebrew (macOS/Linux)
brew install gemini-cli
```

**Prerequisites**: Node.js 20 or higher

### Verification
```bash
which gemini
gemini --version
gemini --help
```

### Local Test Results
```bash
$ which gemini
/opt/homebrew/bin/gemini

$ gemini --version
0.24.0

$ echo 'print("Hello")' | gemini -p "What does this code do?" --output-format json
{
  "session_id": "b2b90938-611f-4bd0-adf6-829e14549653",
  "error": {
    "type": "Error",
    "message": "Please set an Auth method in your /Users/robert/.gemini/settings.json...",
    "code": 41
  }
}
```

## Task Specification

### How to Pass Instructions
- [x] Command line argument (`gemini "your prompt"` or `gemini -p "prompt"`)
- [x] Stdin (`echo "code" | gemini`)
- [x] Stdin + prompt combined (`cat file.md | gemini -p "analyze"`)
- [x] Prompt file in working directory (uses AGENTS.md context)
- [ ] Environment variable

### Example Invocation
```bash
# One-shot headless execution
gemini "Write a function to reverse a string in Python" --output-format json

# Stdin piping with prompt
cat src/main.py | gemini -p "Review this code for bugs" --output-format json

# YOLO mode (auto-approve all actions)
gemini "Fix all linting errors" --yolo --output-format json

# With specific model
gemini -m gemini-2.5-pro "Explain this codebase" --output-format json

# Stream JSON for real-time monitoring
gemini "Implement a REST API" --output-format stream-json
```

### Context Handling
- Automatically indexes the current working directory
- Respects `.gitignore` patterns
- Uses `AGENTS.md` or `.gemini/AGENTS.md` for project-specific instructions
- Supports `@filename` syntax to reference specific files
- `--include-directories` flag for additional folders
- `--all-files` flag to include everything

## Completion Detection

### Exit Codes
| Code | Meaning |
|------|---------|
| 0 | Success |
| 41 | FatalAuthenticationError - Authentication failed |
| 42 | FatalInputError - Invalid input (e.g., piped input with --prompt-interactive) |
| 52 | FatalConfigError - Configuration/settings error |
| 130 | FatalCancellationError - User cancelled (e.g., trust dialog) |

### Output Format
- [x] Stdout (plain text) - default
- [x] Stdout (JSON) - `--output-format json`
- [x] Streaming JSONL - `--output-format stream-json`
- [x] Structured logs (stats, tool calls, token usage in JSON)

**JSON Output Structure**:
```json
{
  "session_id": "uuid",
  "response": "AI response text",
  "stats": {
    "models": {
      "gemini-2.5-pro": {
        "api": {"totalRequests": 1, "totalLatencyMs": 1200},
        "tokens": {"prompt": 500, "candidates": 200, "cached": 0}
      }
    },
    "tools": {"totalCalls": 3, "totalSuccess": 3},
    "files": {"totalLinesAdded": 50, "totalLinesRemoved": 10}
  },
  "error": null
}
```

## Parallel Execution

### Rate Limits
| Auth Method | Rate Limit |
|-------------|------------|
| Google Account (OAuth) | 60 requests/min, 1,000 requests/day |
| API Key | 100 requests/day (Gemini 2.5 Pro) |
| Vertex AI | Usage-based billing |
| Gemini Code Assist Enterprise | Enterprise-grade limits |

### Concurrent Sessions
- Multiple CLI instances can run in parallel in separate directories
- Each session gets a unique `session_id`
- No shared state between instances
- Workspace isolation via `--include-directories`

### Resource Requirements
- 1M token context window (Gemini 2.5 Pro)
- Tools: file operations, shell commands, web fetch, Google Search grounding
- MCP server support for custom integrations

## Authentication

### Option 1: Google Account (OAuth) - Recommended
```bash
# Interactive login
gemini
# Select "Login with Google" when prompted
# Credentials cached in ~/.gemini/settings.json
```

### Option 2: API Key
```bash
# Generate key at https://aistudio.google.com/apikey
export GEMINI_API_KEY="your-api-key-here"
```

### Option 3: Vertex AI (Enterprise)
```bash
export GOOGLE_API_KEY="your-api-key"
export GOOGLE_GENAI_USE_VERTEXAI=true
export GOOGLE_CLOUD_PROJECT="your-project-id"  # Optional
```

### Option 4: Gemini Code Assist License
```bash
export GOOGLE_GENAI_USE_GCA=true
export GOOGLE_CLOUD_PROJECT="your-project-id"
```

**Environment Variables**:
- `GEMINI_API_KEY` - Direct API key
- `GOOGLE_API_KEY` - Google Cloud API key
- `GOOGLE_GENAI_USE_VERTEXAI` - Enable Vertex AI backend
- `GOOGLE_GENAI_USE_GCA` - Enable Code Assist license
- `GOOGLE_CLOUD_PROJECT` - Google Cloud project ID

## Orchestration Assessment

### Can participate in autonomous workflow?
[x] Yes

### Capabilities
- **Headless execution**: Full support with `-p` flag
- **JSON output**: Structured parsing with `--output-format json`
- **Streaming**: Real-time progress with `--output-format stream-json`
- **Auto-approval**: `--yolo` flag for non-interactive operation
- **Error handling**: Consistent exit codes for scripting
- **Session management**: `--resume` flag for session continuity

### Limitations
- Requires authentication setup (OAuth or API key)
- Rate limits on free tier (60/min, 1000/day)
- 1M token context limit

### Integration Complexity
**Low** - Full CLI with headless mode, JSON output, and well-documented exit codes

## Advanced Features

### MCP Server Support
```bash
# List configured MCP servers
gemini mcp list

# Add MCP server
gemini mcp add <server-name> <command>

# Use specific MCP servers
gemini --allowed-mcp-server-names server1,server2 "your prompt"
```

### Extensions
```bash
# List extensions
gemini --list-extensions

# Use specific extensions
gemini -e extension1,extension2 "your prompt"
```

### Approval Modes
- `default` - Prompt for each action
- `auto_edit` - Auto-approve file edits only
- `yolo` - Auto-approve everything

## CI/CD Integration Example

```bash
#!/bin/bash
# ci-code-review.sh

# Run code review with JSON output
result=$(gemini -p "Review the changes in this PR for security issues" \
  --output-format json \
  --approval-mode default)

# Parse response
response=$(echo "$result" | jq -r '.response')
exit_code=$(echo "$result" | jq -r '.error.code // 0')

if [ "$exit_code" != "0" ]; then
  echo "Error: $exit_code"
  exit 1
fi

echo "$response"
```

## Sources
- [Gemini CLI Documentation](https://developers.google.com/gemini-code-assist/docs/gemini-cli)
- [Headless Mode Guide](https://google-gemini.github.io/gemini-cli/docs/cli/headless.html)
- [GitHub Repository](https://github.com/google-gemini/gemini-cli)
- [Troubleshooting Guide](https://google-gemini.github.io/gemini-cli/docs/troubleshooting.html)
- [Exit Codes PR](https://github.com/google-gemini/gemini-cli/pull/13728)
