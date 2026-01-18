# Research: Autonomous Multi-Agent Orchestrator

**Status**: Complete (leverages feature 019 research)

## Summary

This feature builds directly on the comprehensive research conducted in feature 019 (Autonomous Multi-Agent Orchestration Research). No additional research was required.

## Key Findings from Feature 019

### Agent CLI Capabilities

- **9 of 12 agents** have CLI support suitable for autonomous orchestration
- **8 Tier-1 agents** (ready without workarounds): Claude Code, GitHub Codex, GitHub Copilot, Google Gemini, Qwen Code, OpenCode, Kilocode, Augment Code
- **1 Tier-2 agent** (requires workaround): Cursor (needs timeout wrapper)
- **3 agents not suitable**: Windsurf (GUI-only), Roo Code (no official CLI), Amazon Q (transitioning)

### Feasibility Verdict

**Fully Feasible** - All quality gates passed:
- QG-001: ≥6 agents with CLI (9 found)
- QG-002: Cursor CLI documented with workaround
- QG-003: All findings include source links
- QG-004: Parallel constraints documented

### Architecture Recommendation

The research recommended a Python-based orchestrator with:
- **Scheduler**: Reads WP dependencies, assigns agents
- **Executor**: Spawns agent processes via asyncio
- **Monitor**: Detects completion via exit codes and JSON
- **State Manager**: Persists state for resume

### Minimum Viable Agent Set

For initial implementation:
- **Implementation**: Claude Code (best task input support)
- **Review**: GitHub Codex (different perspective)
- **Fallback**: OpenCode (multi-provider flexibility)

## References

- [Feature 019 Spec](../019-autonomous-multi-agent-orchestration-research/spec.md)
- [Feature 019 Data Model](../019-autonomous-multi-agent-orchestration-research/data-model.md)
- [Feature 019 Research Findings](../019-autonomous-multi-agent-orchestration-research/research.md)
- [Sample agents.yaml](../019-autonomous-multi-agent-orchestration-research/sample-agents.yaml)

## Technical Decisions

All technical decisions for this feature are derived from the 019 research:

| Decision | Source | Rationale |
|----------|--------|-----------|
| Python + asyncio | 019 Architecture | Native async, subprocess support |
| JSON state file | 019 Data Model | Human-readable, git-friendly |
| Priority-based selection | 019 Config Schema | User control, fallback support |
| Per-agent invokers | 019 CLI Matrix | Different flags per agent |
