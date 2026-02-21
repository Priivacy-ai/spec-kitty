# Agent: Windsurf (Codeium)

## Basic Info

- **Directory**: `.windsurf/workflows/`
- **Primary Interface**: IDE (VS Code fork) with AI-first design
- **Vendor**: Codeium (formerly Exafunction)
- **Documentation**: <https://docs.windsurf.com>

## CLI Availability

### Installation

```bash
# Windsurf IDE (macOS)
brew install --cask windsurf
# or download from https://windsurf.com

# Shell integration
windsurf --locate-shell-integration-path zsh
```

### Verification

```bash
which windsurf && windsurf --version
```

### Local Test Results

```bash
$ windsurf --version
Windsurf 1.106.0

$ which windsurf
/opt/homebrew/bin/windsurf

$ windsurf chat --help
Usage: windsurf chat [options] [prompt]
Options:
  -m --mode <mode>        The mode to use: 'ask', 'edit', 'agent'
  -a --add-file <path>    Add files as context
  --maximize              Maximize the chat session view
  -r --reuse-window       Force to use the last active window
  -n --new-window         Force to open an empty window
```

**Status**: CLI exists but requires GUI. The `windsurf chat` command opens the IDE with a chat session - it is NOT a headless CLI.

## Task Specification

### How to Pass Instructions

- [x] Command line argument - `windsurf chat "Your prompt"` (opens GUI)
- [x] File context - `windsurf chat -a file.js "Review this"`
- [ ] Stdin - Not supported
- [ ] Non-interactive/headless - **NOT AVAILABLE**

### Example Invocation

```bash
# Opens IDE with chat session (NOT headless)
windsurf chat "Write a hello world function"

# With specific mode
windsurf chat -m agent "Build this feature"
windsurf chat -m ask "Explain this code"
windsurf chat -m edit "Refactor main.js"

# With file context
windsurf chat -a src/main.js "Review this file"
```

### Context Handling

- Opens in workspace directory (cwd or specified path)
- File context via `-a, --add-file` flag
- Requires GUI environment - cannot run headlessly

## Completion Detection

**Not applicable for automation** - Windsurf `chat` command opens GUI and does not return until the user closes the session.

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | IDE launched successfully |
| Non-zero | Launch error |

**Note**: Exit code indicates launch success, not task completion.

### Output Format

- No stdout output (GUI-based interaction)
- Results visible only in IDE interface

## Parallel Execution

### Concurrent Sessions

- Multiple Windsurf windows can run simultaneously
- Each window is independent
- No programmatic session management

### Resource Requirements

- Memory: High (full Electron IDE)
- CPU: Moderate (GUI rendering)
- Display: Required (X11/Wayland or macOS GUI)
- Network: Required for AI features

## Authentication

### Methods

1. **Codeium Account**: Sign in via GUI
2. **API Token**: Can be obtained from Codeium dashboard

```bash
# No CLI authentication method
# Must authenticate through IDE GUI
```

## Headless Workarounds

### 1. windsurfinabox (Docker + Xvfb)

A community project provides Windsurf in a Docker container with virtual display:

```bash
# https://github.com/pfcoperez/windsurfinabox
docker run -e CODEIUM_TOKEN=<token> \
  -v ./instructions:/workspace/windsurf-instructions.txt \
  ghcr.io/pfcoperez/windsurfinabox
```

**How it works**:

- Uses Xvfb to create virtual X11 display
- Uses xdotool to simulate keyboard/mouse input
- Reads task from `windsurf-instructions.txt` file
- Executes preconfigured workflow automatically

**Limitations**:

- Requires Docker
- Fragile (depends on GUI automation)
- Limited control over execution
- No structured output

### 2. Termium (Terminal Autocomplete Only)

Codeium offers **Termium** for terminal autocomplete:

```bash
curl -L https://github.com/Exafunction/codeium/releases/download/termium-v0.2.0/install.sh | bash
```

**Note**: Termium is autocomplete only (like GitHub Copilot's old `suggest` command). It does NOT provide agentic task execution.

### 3. Codeium API (Limited)

Direct API access may be possible but undocumented:

- Register at <https://api.codeium.com/register_user/>
- Uses Firebase authentication
- Primarily for autocomplete, not agentic tasks

## Orchestration Assessment

### Can participate in autonomous workflow?

[ ] No - GUI-only, no native headless mode

### Capabilities for Orchestration

- **Non-interactive mode**: Not available
- **Task input**: GUI only (chat subcommand opens window)
- **Completion detection**: Not possible programmatically
- **File modification**: Only through GUI
- **Structured output**: Not available

### Unique Features (IDE, not CLI)

- **Cascade AI**: Sophisticated multi-step agentic capabilities
- **Memory**: Persistent context across sessions
- **Flows**: Automated multi-step workflows
- **Turbo Mode**: Auto-execution of terminal commands (in IDE)
- **Wave 13**: Multi-agent parallel sessions, git worktrees support

### Limitations

- **No native headless CLI** - Primary limitation for orchestration
- Requires GUI environment
- Docker workaround is fragile
- No structured output format
- No completion detection mechanism

### Integration Complexity

**High** - No native headless support. Docker workaround (windsurfinabox) is the only option and is fragile.

## Recommended Orchestration Pattern

**Not recommended for autonomous orchestration** due to lack of headless support.

If headless operation is required, consider alternatives:

1. Use Claude Code, Codex, or Copilot CLI instead
2. Use windsurfinabox Docker image (fragile workaround)
3. Wait for potential future CLI from Codeium

```bash
# Workaround only (NOT RECOMMENDED for production)
# Using windsurfinabox Docker image
docker run \
  -e CODEIUM_TOKEN=$CODEIUM_TOKEN \
  -v $(pwd)/tasks/WP01-prompt.md:/workspace/windsurf-instructions.txt \
  ghcr.io/pfcoperez/windsurfinabox
```

## Comparison to Other Agents

| Feature | Windsurf | Claude Code | Copilot CLI |
|---------|----------|-------------|-------------|
| Headless flag | ❌ None | `-p, --print` | `-p, --prompt` |
| File edits | GUI only | `--allowedTools` | `--allow-all` |
| JSON output | ❌ No | Yes | `-s` for clean output |
| Stdin support | ❌ No | Yes | Via shell |
| Session resume | GUI only | Yes | Yes |
| Orchestration ready | ❌ No | ✅ Yes | ✅ Yes |

## Termium vs Windsurf

| Feature | Termium | Windsurf chat |
|---------|---------|---------------|
| Type | Terminal autocomplete | Full IDE + AI |
| Headless | Partial (autocomplete) | No |
| Agentic | No | Yes (but GUI only) |
| Installation | Shell script | Application bundle |

## Sources

- [Windsurf Documentation](https://docs.windsurf.com)
- [Windsurf Terminal Docs](https://docs.windsurf.com/windsurf/terminal)
- [windsurfinabox GitHub](https://github.com/pfcoperez/windsurfinabox)
- [Termium Launch Blog](https://windsurf.com/blog/termium-codeium-in-terminal-launch)
- Local CLI testing: `windsurf --help`, `windsurf chat --help` (v1.106.0)
