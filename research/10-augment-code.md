# Agent: Augment Code

## Basic Info

- **Directory**: `.augment/`
- **Primary Interface**: CLI / IDE (VS Code and JetBrains extensions with dedicated CLI - Auggie)
- **Vendor**: Augment Code (augmentcode.com)
- **Documentation**: <https://docs.augmentcode.com/>

## CLI Availability

### Installation

```bash
# npm (global installation) - requires Node.js 22+
npm install -g @augmentcode/auggie

# Verify installation
auggie --version

# Authentication (opens browser)
auggie login

# Print access token (for CI/CD)
auggie token print
```

**Package**: `@augmentcode/auggie` on npm
**Latest Version**: 0.14.0 (as of 2026-01-14)
**License**: Proprietary (SEE LICENSE IN LICENSE.md)

### Python SDK Installation

```bash
# Install Python SDK
pip install auggie-sdk

# With test dependencies
pip install auggie-sdk[test]

# With development dependencies
pip install auggie-sdk[dev]
```

**Python Package**: `auggie-sdk` on PyPI
**Latest Version**: 0.1.7 (as of 2026-01-08)
**Python**: Requires >=3.10 (supports 3.10, 3.11, 3.12, 3.13)

### Verification

```bash
# Command to verify installation
which auggie
auggie --version
```

### Local Test Results

```bash
$ which auggie
# Not installed locally

$ npm info @augmentcode/auggie
@augmentcode/auggie@0.14.0 | SEE LICENSE IN LICENSE.md | deps: none | versions: 124
Auggie CLI Client by Augment Code
https://augmentcode.com

bin: auggie

published 4 days ago by mpauly11 <mpauly@augmentcode.com>
```

## Task Specification

### How to Pass Instructions

- [x] Command line argument (prompt as argument)
- [x] Stdin (piping supported)
- [ ] File path (--file, -f)
- [ ] Prompt file in working directory
- [x] Environment variable (AUGMENT_SESSION_AUTH for authentication)

### Example Invocation

```bash
# Interactive mode
auggie "Refactor the authentication module"

# Headless/non-interactive mode (ACP mode)
auggie --acp "Fix all TypeScript errors"

# With specific shell
auggie --shell bash --startup-script ~/.bashrc "Your task"

# Piping git diff for code review
git diff | auggie "Review these changes"

# Using in CI/CD with service account token
AUGMENT_SESSION_AUTH=$TOKEN auggie --acp "Run tests and fix failures"
```

### Context Handling

- Advanced context engine that understands codebases from single lines to 100M+ lines
- Automatic workspace indexing (`--allow-indexing` flag)
- MCP (Model Context Protocol) support for external tools
- OAuth authentication for remote MCP servers

## Completion Detection

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error / Task failed |

### Output Format

- [x] Stdout (plain text) - default interactive mode
- [x] Stdout (JSON) - ACP mode supports structured output
- [x] Structured logs - thinking summaries in ACP mode
- [ ] File output

## Parallel Execution

### Rate Limits

- Community Plan: 3,000 messages/month
- Developer Plan ($30/month): Unlimited
- Enterprise: Custom limits
- No per-token charges - flat rate pricing

### Concurrent Sessions

- Yes, multiple instances can run simultaneously
- CLI runs anywhere Node.js runs (CI pipelines, serverless, cron jobs)
- Checkpoint-based rollback prevents catastrophic agent mistakes

### Resource Requirements

- Node.js 22+ required for CLI
- Python 3.10+ for SDK
- Memory depends on codebase size and context engine

## Orchestration Assessment

### Can participate in autonomous workflow?

[x] Yes

### Limitations

- Requires authentication (browser-based login or service account token)
- Proprietary licensing (not open source)
- Rate limits on Community plan (3,000 messages/month)

### Integration Complexity

**Low** - Augment Code (Auggie) has excellent CLI support with:

- Full ACP (Agent Client Protocol) mode for non-interactive operation
- Service accounts for CI/CD automation
- Python and TypeScript SDKs for programmatic access
- Terminal authentication support
- Shell configuration options

## VS Code Extension Patterns

Augment Code provides a separate CLI tool (`auggie`) rather than bundling the extension:

- CLI and VS Code extension share the same backend context engine
- Works in any environment where Node.js runs
- Same AI assistance whether in VS Code, terminal, or CI pipeline

### Headless Workarounds

- No workarounds needed - native CLI support via Auggie
- Works in CI/CD pipelines with service account tokens
- Python SDK for complex automation scenarios

## Agent Wrapper

On GitHub (as of 2026-01-08), Augment Code offers an "augment-agent" repository described as "A simple wrapper to bring Auggie in to your development lifecycle," written in TypeScript. This can be used for additional orchestration capabilities.

## Sources

- [Augment Code VS Code Marketplace](https://marketplace.visualstudio.com/items?itemName=augment.vscode-augment)
- [Install Auggie CLI](https://docs.augmentcode.com/cli/setup-auggie/install-auggie-cli)
- [npm: @augmentcode/auggie](https://www.npmjs.com/package/@augmentcode/auggie)
- [PyPI: auggie-sdk](https://pypi.org/project/auggie-sdk/)
- [Augment Code Product - CLI](https://www.augmentcode.com/product/CLI)
- [Augment Code Changelog](https://www.augmentcode.com/changelog)
- [GitHub: augmentcode](https://github.com/augmentcode)
- [Developer Walk-Through of Auggie CLI (The New Stack)](https://thenewstack.io/developer-walk-through-of-auggie-cli-an-agentic-terminal-app/)
- npm package inspection (2026-01-18)
