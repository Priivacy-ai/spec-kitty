# Agent: Amazon Q Developer CLI

## Basic Info
- **Directory**: `.amazonq/`
- **Primary Interface**: CLI
- **Vendor**: Amazon Web Services (AWS)
- **Documentation**: https://docs.aws.amazon.com/amazonq/latest/qdeveloper-ug/command-line.html

## Important Notice

**Rebranding**: As of November 2024, Amazon Q Developer CLI has been rebranded to **Kiro CLI**. The open-source amazon-q-developer-cli repository is no longer actively maintained. For latest features, use Kiro CLI instead.

- Original: `amazon-q-developer-cli` (open source, Rust-based)
- Current: Kiro CLI (closed source)
- Homebrew cask: `brew install --cask amazon-q` (may install Kiro)

## CLI Availability

### Installation
```bash
# macOS via Homebrew
brew install --cask amazon-q

# macOS via DMG
# Download from AWS

# Linux
# Ubuntu/Debian packages available
# AppImage format supported
```

### Verification
```bash
which q && q --version
# Or for Kiro:
which kiro && kiro --version
```

### Local Test Results
```bash
$ which q
q not found

$ which kiro
kiro not found
```

**Status**: NOT INSTALLED on test system.

## Task Specification (Based on Documentation)

### How to Pass Instructions
- [x] Command line argument - Chat subcommand accepts prompts
- [ ] Stdin - Not documented
- [ ] File path (--file, -f) - Not documented
- [ ] Prompt file in working directory - Not documented
- [ ] Environment variable - Not supported

### Example Invocation (Theoretical)
```bash
# Based on documentation, the CLI provides:
# - Agentic chat in terminal
# - Natural language application building
# - Code generation, file editing
# - Git workflow automation

# The chat_cli binary is the main interface
chat_cli "Build a simple web server"

# Or via q/kiro command
q chat "Review this code"
kiro chat "Fix the bug"
```

### Context Handling
- Operates within current directory
- Can interact with Git repositories
- Agentic capabilities for file editing

## Completion Detection

### Exit Codes
| Code | Meaning |
|------|---------|
| 0 | Success (assumed) |
| Non-zero | Error (assumed) |

Note: Exit codes not documented in available sources.

### Output Format
- [ ] Stdout (plain text) - Likely supported
- [ ] Stdout (JSON) - Not documented
- [ ] File output - Not documented
- [ ] Structured logs - Not documented

## Parallel Execution

### Rate Limits
- AWS service limits apply
- IAM permissions required
- May have per-account quotas

### Concurrent Sessions
- Unknown - not documented

### Resource Requirements
- Memory: Unknown
- CPU: Unknown
- Network: Required (AWS cloud)
- Authentication: AWS credentials or IAM role

## Authentication

### Methods
1. **AWS IAM Identity Center** (recommended for enterprise)
2. **IAM Roles** (for CI/CD pipelines)
3. **Builder ID** (for individual developers)

### Headless Login for CI/CD
For headless environments (CI/CD), use IAM roles with Amazon Q policy instead of browser-based login.

```bash
# Headless login approach (theoretical)
# Use IAM role attached to compute instance
# Or environment variables:
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
```

## Orchestration Assessment

### Can participate in autonomous workflow?
[ ] Partial - Requires further investigation

### Capabilities for Orchestration
- **Non-interactive mode**: Unclear if fully supported
- **Task input**: Chat-based, method unclear for automation
- **Completion detection**: Not documented
- **Agentic execution**: Supported with permission

### Limitations
- CLI is undergoing transition (Amazon Q → Kiro)
- Open-source version deprecated
- Limited headless automation documentation
- Requires AWS authentication setup
- Not installed on test system - cannot verify

### Integration Complexity
**High** - AWS authentication complexity, unclear headless automation story, transitioning product.

## Recommended Action

1. **Install Kiro CLI** to test actual capabilities
2. **Investigate Kiro documentation** for headless mode
3. **Test with AWS credentials** to verify automation support

## Alternative for Orchestration

Given the complexity and transition state, consider:
- Using other CLI agents (Claude, Codex, OpenCode) for autonomous orchestration
- Amazon Q may be better suited for IDE integration than headless automation

## Sources
- [Amazon Q Command Line Documentation](https://docs.aws.amazon.com/amazonq/latest/qdeveloper-ug/command-line.html)
- [Amazon Q CLI GitHub (Deprecated)](https://github.com/aws/amazon-q-developer-cli)
- [Amazon Q CLI Command Reference](https://docs.aws.amazon.com/amazonq/latest/qdeveloper-ug/command-line-reference.html)
- [Installing on Linux Headless](https://dev.to/aws/the-essential-guide-to-installing-amazon-q-developer-cli-on-linux-headless-and-desktop-3bo7)
- [AWS Blog: Enhanced CLI Experience](https://aws.amazon.com/blogs/devops/introducing-the-enhanced-command-line-interface-in-amazon-q-developer/)
