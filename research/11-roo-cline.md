# Agent: Roo Code (formerly Roo Cline)

## Basic Info

- **Directory**: `.roo/`
- **Primary Interface**: IDE (VS Code extension) - CLI support in development
- **Vendor**: Roo Code, Inc. (roocode.com)
- **Documentation**: <https://docs.roocode.com/>

## CLI Availability

### Current Status

**CLI is in active development but not yet officially released.**

As of May 2025, GitHub Issue #3835 requested CLI/headless execution support. The issue was closed as "COMPLETED" with the following solutions:

1. The `@roo-code/evals` package supports headless Docker execution
2. An IPC server can be enabled for CLI integration via the `roo-cli` tool

### Official npm Packages (No CLI Yet)

```bash
# Type definitions (for CLI support infrastructure)
npm info @roo-code/types
# Latest: 1.106.0 (2026-01-15)

# Cloud SDK
npm info @roo-code/cloud
# Latest: 0.29.0 (2025-08-28)
```

### Third-Party CLI Options

**1. roo-ipc (IPC-based CLI)**
Repository: <https://github.com/cte/roo-cli>

```bash
# Clone and install
git clone https://github.com/cte/roo-cli.git
cd roo-cli
pnpm install

# Launch VS Code with IPC socket
ROO_CODE_IPC_SOCKET_PATH=/tmp/roo-code.sock code

# Run task via CLI
pnpm dev "Tell me a pirate joke."
```

**2. Roo-Code-CLI (Terminal Fork)**
Repository: <https://github.com/rightson/Roo-Code-CLI>

A complete fork of Roo-Code reimagined for terminal use:

```bash
# Clone and install
git clone https://github.com/rightson/Roo-Code-CLI.git
cd Roo-Code-CLI
pnpm install

# Build and install as VSIX
pnpm install:vsix
```

### Verification

```bash
# No official CLI installed
$ which roo roo-cline roo-code
# Not found
```

### Local Test Results

```bash
$ npm search roo-code --json | head -20
# Found @roo-code/types, @roo-code/cloud - no CLI package yet

$ which cline
# Not found (Cline CLI may be separate - see below)
```

## Parent Project: Cline

Roo Code is a fork of Cline (previously "Claude Dev"). Cline has its own CLI:

### Cline CLI

- **Documentation**: <https://docs.cline.bot/cline-cli/overview>
- **Supports**: macOS, Linux (Windows coming soon)
- **Authentication**: `cline auth` command

```bash
# Cline CLI installation (from official docs)
# Check cline.bot for latest installation instructions

# Run with hooks enabled
cline -s hooks_enabled=true "Your task"

# Headless automation
cline --headless "Automated task"

# Piping git diff for review
git diff | cline "Review these changes"
```

**Cline CLI Features**:

- Interactive mode for real-time interaction
- Headless automation for scripted task execution
- Multi-instance parallelization
- JSON, plain text, or rich terminal output formats
- CI/CD integration with hooks

## Task Specification

### How to Pass Instructions (via IPC or fork)

- [x] Command line argument (with third-party tools)
- [x] Stdin (with Cline CLI)
- [ ] File path (--file, -f)
- [ ] Prompt file in working directory
- [ ] Environment variable

### Example Invocation

```bash
# Using roo-ipc (requires VS Code running)
ROO_CODE_IPC_SOCKET_PATH=/tmp/roo-code.sock code
pnpm dev "Implement the authentication feature"

# Using Cline CLI (parent project)
cline "Fix the TypeScript errors"

# Headless browser automation (within VS Code)
# Roo can launch headless browsers, click, type, scroll, and capture screenshots
```

### Context Handling

- Model-agnostic: Supports OpenAI, Anthropic, Gemini, Ollama (BYOK)
- MCP (Model Context Protocol) integration
- Multiple modes: Code, Architect, Ask, Debug, Custom
- Reads/writes across multiple files
- Executes terminal commands
- Controls browser sessions

## Completion Detection

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error |
(Exact codes depend on CLI implementation used)

### Output Format

- [ ] Stdout (plain text) - limited official support
- [ ] Stdout (JSON) - via third-party tools
- [x] Structured logs - via IPC messages
- [ ] File output

## Parallel Execution

### Rate Limits

Depends on underlying LLM provider (user provides API keys - BYOK model).

### Concurrent Sessions

- Official: Limited - VS Code extension is single-session
- With roo-ipc: Multiple IPC connections possible
- With Cline CLI: Multi-instance parallelization supported

### Resource Requirements

- VS Code required for official extension
- Node.js for third-party CLI tools
- Docker for `@roo-code/evals` headless execution

## Orchestration Assessment

### Can participate in autonomous workflow?

[ ] Yes / [ ] No / [x] Partial

**Partial** because:

- Official CLI not yet released
- Third-party solutions exist but require setup
- IPC approach requires VS Code running
- Cline CLI (parent) offers better headless support

### Limitations

- No official standalone CLI package
- Requires VS Code or fork/third-party tool
- IPC solution requires VS Code process running
- Documentation for headless use is limited

### Integration Complexity

**High** - Currently requires:

1. Running VS Code with IPC socket, OR
2. Using third-party fork (Roo-Code-CLI), OR
3. Using parent project Cline's CLI, OR
4. Docker-based `@roo-code/evals` approach

## VS Code Extension Patterns

### Standard Extension Limitations

VS Code extensions typically require the VS Code UI. However, several patterns enable headless operation:

**1. IPC Server Approach (Used by Roo Code)**

- Extension exposes IPC socket
- External CLI connects to running VS Code
- Limitation: VS Code must be running

**2. Extension Bundling (Like Kilocode)**

- Bundle entire extension for standalone CLI
- Extension code runs unmodified outside VS Code
- Best approach for full headless support

**3. VS Code Server**

- Run VS Code in server mode on remote machine
- Connect via browser or VS Code client
- Extensions run in server environment

**4. code-server / OpenVSCode Server**

- Browser-based VS Code
- Extensions can run on remote server
- Access via web browser

**5. Docker-based Evaluation**

- `@roo-code/evals` package
- Runs in headless Docker container
- Useful for CI/CD and testing

### Headless Workarounds for Roo Code

1. **roo-ipc**: Unix socket IPC to running VS Code
2. **Roo-Code-CLI**: Terminal fork with pnpm
3. **Docker evals**: `@roo-code/evals` package
4. **Cline CLI**: Use parent project's official CLI

## Unique Features of Roo Code vs Cline

| Feature | Roo Code | Cline |
|---------|----------|-------|
| Modes | Code, Architect, Ask, Debug, Custom | Plan, Act |
| Focus | System admin friendly, CLI-focused natural language | Developer-focused |
| VS Code Code Actions | Supported | Limited |
| Script understanding | Enhanced for colleagues' scripts | Standard |
| Installation count | 50,000+ | 4M+ |

## Sources

- [Roo Code VS Code Marketplace](https://marketplace.visualstudio.com/items?itemName=RooVeterinaryInc.roo-cline)
- [Roo Code Documentation](https://docs.roocode.com/)
- [GitHub: RooCodeInc/Roo-Code](https://github.com/RooCodeInc/Roo-Code)
- [GitHub Issue #3835: CLI/Headless Support](https://github.com/RooCodeInc/Roo-Code/issues/3835)
- [GitHub: cte/roo-cli (IPC tool)](https://github.com/cte/roo-cli)
- [GitHub: rightson/Roo-Code-CLI (Terminal fork)](https://github.com/rightson/Roo-Code-CLI)
- [Cline Documentation](https://docs.cline.bot/)
- [Cline CLI Overview](https://docs.cline.bot/cline-cli/overview)
- [GitHub: cline/cline](https://github.com/cline/cline)
- [Qodo: Roo Code vs Cline](https://www.qodo.ai/blog/roo-code-vs-cline/)
- npm package search (2026-01-18)
