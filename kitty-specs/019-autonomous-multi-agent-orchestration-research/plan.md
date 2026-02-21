# Research Plan: Autonomous Multi-Agent Orchestration

**Branch**: `019-autonomous-multi-agent-orchestration-research` | **Date**: 2026-01-18 | **Spec**: [spec.md](spec.md)
**Mission**: Research

## Summary

Investigate the headless/CLI invocation capabilities of all 12 AI coding agents supported by spec-kitty. The research combines documentation review with hands-on local CLI testing to produce a comprehensive capability matrix and orchestration feasibility assessment.

**Primary Deliverable**: CLI capability matrix with working invocation examples for all agents that support headless operation.

## Research Context

**Methodology**: Documentation review + local CLI testing
**Data Sources**: Official docs, GitHub repos, npm/pip packages, local CLI execution
**Verification**: All CLI-capable agents tested locally with `--help` and basic invocation
**Output Format**: Markdown reports with source links and command examples
**Scope**: Headless/CLI only (no IDE integration)

## Constitution Check

*No constitution file defined. Proceeding with standard research practices.*

- Research will cite all sources
- Findings will be verifiable through provided commands
- No proprietary information will be included

## Research Structure

### Documentation (this feature)

```
kitty-specs/019-autonomous-multi-agent-orchestration-research/
├── plan.md              # This file - research methodology
├── spec.md              # Research specification
├── research/            # Individual agent research files
│   ├── 01-claude-code.md
│   ├── 02-github-copilot.md
│   ├── 03-google-gemini.md
│   ├── 04-cursor.md
│   ├── 05-qwen-code.md
│   ├── 06-opencode.md
│   ├── 07-windsurf.md
│   ├── 08-github-codex.md
│   ├── 09-kilocode.md
│   ├── 10-augment-code.md
│   ├── 11-roo-cline.md
│   └── 12-amazon-q.md
├── research.md          # Consolidated findings & capability matrix
├── data-model.md        # Agent profile schema for orchestration config
└── quickstart.md        # How to test each agent CLI locally
```

### No Source Code Changes

This is a research-only mission. No implementation code will be written.

## Research Methodology

### Phase 1: Agent Investigation (Per Agent)

For each of the 12 agents:

1. **Documentation Review**
   - Official documentation site
   - GitHub repository README
   - npm/pip package documentation
   - Release notes for CLI features

2. **Local CLI Testing** (if available)
   - Check if installed: `which <cli-name>` or `<cli-name> --version`
   - Inspect help: `<cli-name> --help`
   - Test basic invocation with a simple prompt
   - Document authentication requirements
   - Test task file input methods

3. **Capability Assessment**
   - Can it run headless (no IDE)?
   - How do you pass a task/prompt?
   - How do you detect completion?
   - What are the exit codes?
   - Can multiple instances run in parallel?

### Phase 2: Synthesis

1. **Build Capability Matrix**
   - All 12 agents in rows
   - Columns: CLI available, invocation command, task input method, completion detection, parallel support

2. **Identify Orchestration-Ready Agents**
   - Which agents can participate in autonomous workflows?
   - What are the limiting factors for others?

3. **Propose Configuration Schema**
   - YAML schema for `.kittify/agents.yaml`
   - Implementation vs review role assignment
   - Fallback strategies

## Agent Investigation Template

Each agent research file (`research/XX-agent-name.md`) will follow this structure:

```markdown
# Agent: [Name]

## Basic Info
- **Directory**: `.agent/`
- **Primary Interface**: CLI / IDE / API
- **Vendor**: [Company]
- **Documentation**: [URL]

## CLI Availability

### Installation
[How to install the CLI tool]

### Verification
```bash
# Command to verify installation
```

### Local Test Results

```bash
# Actual output from running --help or version
```

## Task Specification

### How to Pass Instructions

- [ ] Command line argument
- [ ] Stdin
- [ ] File path (--file, -f)
- [ ] Prompt file in working directory
- [ ] Environment variable

### Example Invocation

```bash
# Working command example
```

### Context Handling

[How does it handle codebase context?]

## Completion Detection

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error |
| ... | ... |

### Output Format

- [ ] Stdout (plain text)
- [ ] Stdout (JSON)
- [ ] File output
- [ ] Structured logs

## Parallel Execution

### Rate Limits

[Documented rate limits or quotas]

### Concurrent Sessions

[Can multiple instances run simultaneously?]

### Resource Requirements

[Memory, CPU, tokens]

## Orchestration Assessment

### Can participate in autonomous workflow?

[ ] Yes / [ ] No / [ ] Partial

### Limitations

[What prevents full participation?]

### Integration Complexity

Low / Medium / High

## Sources

- [Link 1]
- [Link 2]

```

## Data Collection Checklist

| # | Agent | Docs Reviewed | CLI Tested | Assessment Complete |
|---|-------|---------------|------------|---------------------|
| 1 | Claude Code | [ ] | [ ] | [ ] |
| 2 | GitHub Copilot | [ ] | [ ] | [ ] |
| 3 | Google Gemini | [ ] | [ ] | [ ] |
| 4 | Cursor | [ ] | [ ] | [ ] |
| 5 | Qwen Code | [ ] | [ ] | [ ] |
| 6 | OpenCode | [ ] | [ ] | [ ] |
| 7 | Windsurf | [ ] | [ ] | [ ] |
| 8 | GitHub Codex | [ ] | [ ] | [ ] |
| 9 | Kilocode | [ ] | [ ] | [ ] |
| 10 | Augment Code | [ ] | [ ] | [ ] |
| 11 | Roo Cline | [ ] | [ ] | [ ] |
| 12 | Amazon Q | [ ] | [ ] | [ ] |

## Quality Gates

From spec - research must satisfy:

- **QG-001**: At least 6 of 12 agents have documented CLI invocation paths
- **QG-002**: Cursor CLI specifically documented (user priority)
- **QG-003**: All findings include source links
- **QG-004**: Parallel execution constraints documented for CLI-capable agents

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Agent has no CLI | Document API alternative if available |
| CLI is undocumented | Test empirically, note "unofficial" status |
| Rate limits block testing | Document limits, test one request only |
| Auth requirements | Note setup steps, don't store credentials |
