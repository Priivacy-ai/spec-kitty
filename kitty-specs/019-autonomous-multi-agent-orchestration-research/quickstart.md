# Quickstart: Testing Agent CLIs Locally

**Purpose**: Quick reference for installing and testing each agent's CLI tool.

## Prerequisites

- macOS, Linux, or WSL
- Node.js 18+ (for npm-based CLIs)
- Python 3.11+ (for pip-based CLIs)
- Homebrew (macOS) or equivalent package manager

## Agent CLI Testing Commands

### 1. Claude Code (Anthropic)

**Known CLI**: `claude`

```bash
# Check if installed
which claude && claude --version

# Install (if not present)
npm install -g @anthropic-ai/claude-code

# Test help
claude --help

# Test basic invocation
claude "What is 2+2?"
```

**Auth**: Requires `ANTHROPIC_API_KEY` environment variable.

---

### 2. GitHub Copilot

**Known CLI**: Unknown - primarily VS Code extension

```bash
# Check for any Copilot CLI
which copilot gh-copilot

# GitHub CLI has Copilot extension
gh extension list | grep copilot
gh copilot --help
```

**Note**: May be IDE-only. Research needed.

---

### 3. Google Gemini

**Known CLI**: `gemini` (Google AI CLI) or API-only

```bash
# Check if installed
which gemini

# Alternative: Google Cloud AI CLI
gcloud ai --help
```

**Auth**: Requires Google Cloud credentials or API key.

---

### 4. Cursor

**Known CLI**: User reports CLI exists - find it!

```bash
# Check common names
which cursor cursor-cli

# Check if Cursor app has CLI
ls /Applications/Cursor.app/Contents/Resources/app/bin/

# macOS: Check if shell command installed
cursor --help
```

**Note**: Priority research item per user request.

---

### 5. Qwen Code (Alibaba)

**Known CLI**: Likely API-only

```bash
# Check for any Qwen CLI
which qwen qwen-code

# May use Alibaba Cloud CLI
aliyun --help
```

**Note**: Research Alibaba Cloud AI services.

---

### 6. OpenCode

**Known CLI**: `opencode`

```bash
# Check if installed
which opencode && opencode --version

# Install
npm install -g opencode
# or
pip install opencode

# Test help
opencode --help
```

---

### 7. Windsurf (Codeium)

**Known CLI**: Unknown - primarily IDE

```bash
# Check for Codeium CLI
which codeium windsurf

# Codeium may have language server CLI
codeium --help
```

**Note**: Research Codeium's headless options.

---

### 8. GitHub Codex (OpenAI)

**Known CLI**: `codex` (OpenAI Codex CLI)

```bash
# Check if installed
which codex && codex --version

# Install
npm install -g @openai/codex

# Test help
codex --help

# Test basic invocation
codex "Write a hello world in Python"
```

**Auth**: Requires `OPENAI_API_KEY` environment variable.

---

### 9. Kilocode

**Known CLI**: Unknown - VS Code extension

```bash
# Check for any Kilocode CLI
which kilocode kilo

# Check npm
npm search kilocode
```

**Note**: Research needed.

---

### 10. Augment Code

**Known CLI**: Unknown - IDE extension

```bash
# Check for any Augment CLI
which augment augment-code

# Check npm/pip
npm search augment-code
pip search augment  # Note: pip search may be disabled
```

**Note**: Research needed.

---

### 11. Roo Cline

**Known CLI**: Unknown - VS Code extension (fork of Cline)

```bash
# Check for CLI
which roo roo-cline cline

# Cline (original) may have CLI
npm search cline-ai
```

**Note**: Research Cline project for CLI options.

---

### 12. Amazon Q

**Known CLI**: `q` (AWS Q Developer CLI)

```bash
# Check if installed
which q && q --version

# Install via AWS CLI v2
aws --version
# Q may be part of AWS CLI or separate

# Alternative: Amazon Q Developer CLI
brew install amazon-q  # hypothetical

# Test help
q --help
```

**Auth**: Requires AWS credentials configured.

---

## Batch Testing Script

Save as `test-all-clis.sh`:

```bash
#!/bin/bash

echo "=== Agent CLI Availability Check ==="

agents=(
  "claude:claude --version"
  "copilot:gh copilot --help"
  "gemini:gemini --version"
  "cursor:cursor --help"
  "qwen:qwen --version"
  "opencode:opencode --version"
  "windsurf:codeium --help"
  "codex:codex --version"
  "kilocode:kilocode --version"
  "augment:augment --version"
  "roo:roo --version"
  "amazon-q:q --version"
)

for entry in "${agents[@]}"; do
  name="${entry%%:*}"
  cmd="${entry#*:}"

  echo -n "$name: "
  if eval "$cmd" > /dev/null 2>&1; then
    echo "AVAILABLE"
  else
    echo "NOT FOUND"
  fi
done
```

Run with:

```bash
chmod +x test-all-clis.sh
./test-all-clis.sh
```

## Next Steps

1. Run the batch test to see which CLIs are already installed
2. Install available CLIs for agents you have subscriptions to
3. For each installed CLI, run `--help` and capture output
4. Test basic task invocation and record results in research files
