---
work_package_id: WP03
title: Harness Capability Matrix Completion
dependencies:
- WP01
- WP02
requirement_refs:
- FR-012
- FR-013
- FR-014
- FR-015
tracker_refs: []
planning_base_branch: feat/agent-profile-projection-plugin-production
merge_target_branch: feat/agent-profile-projection-plugin-production
branch_strategy: Planning artifacts for this mission were generated on feat/agent-profile-projection-plugin-production. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/agent-profile-projection-plugin-production unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-agent-profile-projection-plugin-production-01KV3NGS-01KV3NGS
base_commit: unknown
created_at: '2026-06-14T20:50:11.197360+00:00'
subtasks:
- T010
- T011
- T012
- T013
- T014
agent: claude
shell_pid: '78708'
history:
- at: '2026-06-14T00:00:00Z'
  event: created
  actor: claude
agent_profile: engineer
authoritative_surface: src/specify_cli/tool_surface/profiles/
create_intent:
- src/specify_cli/tool_surface/profiles/amazon_q_renderer.py
- src/specify_cli/tool_surface/profiles/augment_renderer.py
- src/specify_cli/tool_surface/profiles/capability_matrix.py
execution_mode: code_change
owned_files:
- src/specify_cli/tool_surface/profiles/amazon_q_renderer.py
- src/specify_cli/tool_surface/profiles/augment_renderer.py
- src/specify_cli/tool_surface/profiles/capability_matrix.py
- src/specify_cli/tool_surface/providers/agent_profiles.py
role: Senior Python Engineer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading any other section of this prompt, load your agent profile:

```
/ad-hoc-profile-load engineer
```

---

## Objective

Complete the harness capability matrix: implement `AmazonQProfileRenderer` (user-global path) and `AugmentProfileRenderer` (project-local); build a `HarnessCapabilityRecord` registry that marks the remaining 14 harnesses as `not_applicable` with machine-readable reasons; update `AgentProfilesProvider` to emit per-harness `not_applicable` findings. After this WP, `doctor tool-surfaces --kind agent-profile --json` must report only valid profile statuses for every configured harness.

---

## Context

Key principle from FR-014: do NOT create fake profile projections for harnesses that lack a native agent primitive. The correct behavior is `not_applicable` + clear reason, exposing Spec Kitty personas through skills/command surfaces instead. This keeps the doctor trustworthy.

Research findings (from research.md):
- **Amazon Q Developer CLI**: custom agent support exists at `~/.aws/amazonq/cli-agents/` but is user-global, not project-local. The renderer should output there but must NOT add to the project manifest. The doctor must use filesystem inspection, not manifest lookup, to check Amazon Q profile presence.
- **Augment Code**: subagent format is `.augment/agents/<id>.md` (YAML frontmatter + Markdown body), similar to Claude Code's `.claude/agents/` format. This IS project-local and manifest-tracked.
- **Remaining harnesses** (Windsurf, Cursor, Kiro, Gemini, Qwen, OpenCode, Kilocode, Roo Code [deprecated], GitHub Copilot chat, etc.): no confirmed native agent profile primitive as of research date. All should be `not_applicable`.

The six valid status values per FR-015 are: `present`, `missing`, `stale`, `drifted`, `not_applicable`, and `research_gap`. `research_gap` remains valid only for harnesses with genuinely unassessed native agent primitive support (i.e., not yet researched), and this WP should drive every assessed configured harness to either supported or `not_applicable`.

---

## Subtask Guidance

### T010 — Implement `AmazonQProfileRenderer` targeting user-global path

Create `src/specify_cli/tool_surface/profiles/amazon_q_renderer.py`:

```python
FORMAT_AMAZON_Q_AGENT = "amazon-q-agent"

class AmazonQProfileRenderer:
    format_key: str = FORMAT_AMAZON_Q_AGENT
    # User-global; NOT project-local. Do NOT add to project manifest.
    USER_GLOBAL = True

    def can_render(self, tool_key: str) -> bool:
        return tool_key in {"q", "amazon-q", FORMAT_AMAZON_Q_AGENT}

    def output_path(self, tool_key: str, profile: AgentProfile, project_root: Path) -> Path:
        # tool_key first, then profile, then project_root — matches ProfileRenderer Protocol.
        # project_root is ignored for user-global renderers.
        # Output goes to ~/.aws/amazonq/cli-agents/<profile_id>.json (JSON format per FR-012)
        _ = tool_key, project_root
        return Path.home() / ".aws" / "amazonq" / "cli-agents" / f"{profile.profile_id}.json"

    def render(self, profile: AgentProfile) -> str:
        # Returns JSON string (spec.md FR-012 says .json format, not Markdown)
        import json
        return json.dumps({
            "name": profile.name or profile.profile_id,
            "description": profile.description or profile.purpose or "",
            "instructions": profile.purpose or "",
        }, indent=2)
```

**Critical**: Because this is user-global, `AgentProfilesProvider` must NOT use the manifest to track Amazon Q profiles. Use filesystem inspection (`output_path.exists()`) directly in the provider when building findings for the `q` harness. Do NOT write `output_path` to the project manifest.

Also add a doctor note in the finding: when Amazon Q profiles are found at the user-global path but not in the project, that is expected (not an error).

### T011 — Implement `AugmentProfileRenderer` for `.augment/agents/<id>.md`

Create `src/specify_cli/tool_surface/profiles/augment_renderer.py`:

```python
FORMAT_AUGMENT_AGENT = "augment-agent"

class AugmentProfileRenderer:
    format_key: str = FORMAT_AUGMENT_AGENT
    USER_GLOBAL = False  # project-local, manifest-tracked

    def can_render(self, tool_key: str) -> bool:
        return tool_key in {"auggie", "augment", FORMAT_AUGMENT_AGENT}

    def output_path(self, tool_key: str, profile: AgentProfile, project_root: Path) -> Path:
        # tool_key first, then profile, then project_root — matches ProfileRenderer Protocol
        _ = tool_key
        return project_root / ".augment" / "agents" / f"{profile.profile_id}.md"
```

Render format: YAML frontmatter with `name`, `description`, `version`; Markdown body with the system prompt; provenance footer `<!-- generated by spec-kitty -->`. Pattern is identical to `ClaudeCodeProfileRenderer` — extract a shared `_render_markdown_profile(profile)` helper if the two are now identical in structure.

Register in `renderers.py` alongside `CodexProfileRenderer` from WP02.

### T012 — Build `HarnessCapabilityRecord` and register not-applicable harnesses

Create `src/specify_cli/tool_surface/profiles/capability_matrix.py`:

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class HarnessCapabilityRecord:
    harness_key: str
    has_native_agent_primitive: bool
    reason: str  # human-readable; used in doctor findings

HARNESS_CAPABILITY_MATRIX: dict[str, HarnessCapabilityRecord] = {
    "claude": HarnessCapabilityRecord("claude", True, "Native: .claude/agents/<id>.md"),
    "copilot": HarnessCapabilityRecord("copilot", True, "Native: .github/agents/<id>.agent.md"),
    "codex": HarnessCapabilityRecord("codex", True, "Native: .codex/agents/<id>.toml"),
    "auggie": HarnessCapabilityRecord("auggie", True, "Native: .augment/agents/<id>.md"),
    "q": HarnessCapabilityRecord("q", True, "User-global: ~/.aws/amazonq/cli-agents/<id>.json"),
    # Not-applicable harnesses — skills/workflows surface is the supported fallback
    "windsurf": HarnessCapabilityRecord("windsurf", False, "No native agent primitive; use workflow/rule surfaces"),
    "cursor": HarnessCapabilityRecord("cursor", False, "No native agent primitive; use rule surfaces"),
    "kiro": HarnessCapabilityRecord("kiro", False, "No native agent primitive; use prompt surfaces"),
    "gemini": HarnessCapabilityRecord("gemini", False, "No native agent primitive; use command surfaces"),
    "qwen": HarnessCapabilityRecord("qwen", False, "No native agent primitive; use command surfaces"),
    "opencode": HarnessCapabilityRecord("opencode", False, "No native agent primitive; use command surfaces"),
    "kilocode": HarnessCapabilityRecord("kilocode", False, "No native agent primitive; use workflow surfaces"),
    "vibe": HarnessCapabilityRecord("vibe", False, "No native agent primitive; use skill surfaces"),
    "pi": HarnessCapabilityRecord("pi", False, "No native agent primitive; use skill surfaces"),
    "letta": HarnessCapabilityRecord("letta", False, "No native agent primitive; use skill surfaces"),
}
```

Populate all 19 configured harnesses from `AI_CHOICES` in `config.py`. Do not hardcode — iterate `AI_CHOICES.keys()` to ensure every configured harness has a record, even if it defaults to `not_applicable`.

### T013 — Update `AgentProfilesProvider` to emit `not_applicable` findings

In `src/specify_cli/tool_surface/providers/agent_profiles.py`, update the findings builder:

```python
from specify_cli.tool_surface.findings import (
    PROFILE_PROJECTION_UNSUPPORTED,
    RESEARCH_GAP_SURFACE,
    SEVERITY_INFO,
    make_finding,
)
from specify_cli.tool_surface.profiles.capability_matrix import HARNESS_CAPABILITY_MATRIX

def _findings_for_harness(harness_key: str, project_root: Path, ...) -> SurfaceFinding:
    record = HARNESS_CAPABILITY_MATRIX.get(harness_key)
    if record is None:
        return make_finding(
            RESEARCH_GAP_SURFACE,
            SEVERITY_INFO,
            f"{harness_key} native agent profile support has not been assessed.",
            tool_key=harness_key,
            details={"status": "research_gap"},
        )
    if not record.has_native_agent_primitive:
        return make_finding(
            PROFILE_PROJECTION_UNSUPPORTED,
            SEVERITY_INFO,
            f"{harness_key} does not support native agent profile projection.",
            tool_key=harness_key,
            details={"status": "not_applicable", "reason": record.reason},
        )
    # existing logic for present/missing/stale/drifted...
```

Do not instantiate `SurfaceFinding(harness=..., kind=..., status=...)`; the current reporting model requires stable finding codes, severity, message, and optional `details`.

Ensure the Amazon Q harness uses filesystem inspection (`output_path.exists()`) rather than manifest lookup when building its finding.

### T014 — Verify `doctor tool-surfaces --kind agent-profile --json` emits six valid statuses

After implementing T010-T013, run:
```bash
spec-kitty doctor tool-surfaces --kind agent-profile --json
```

Inspect the `findings` array. Every finding's profile status must be one of: `present`, `missing`, `stale`, `drifted`, `not_applicable`, `research_gap`. If any assessed configured harness still shows `research_gap`, that harness still needs to be added to the capability matrix (or added to the renderer registry if confirmed).

Automated assertion: add a check in the unit tests (WP08 handles the full test suite, but add a smoke assertion here via CLI invocation in a tmp project).

---

## Branch Strategy

- **Planning base branch**: `feat/agent-profile-projection-plugin-production`
- **Final merge target**: `feat/agent-profile-projection-plugin-production`
- **Depends on**: WP01 (surface repair wiring) AND WP02 (CodexProfileRenderer) must be merged first — T014 checks that `research_gap` no longer appears for Codex, which requires WP02's renderer to be registered

To start work: `spec-kitty agent action implement WP03 --agent claude`

---

## Definition of Done

- [ ] `AmazonQProfileRenderer` implemented; outputs to `~/.aws/amazonq/cli-agents/`; NOT manifest-tracked
- [ ] `AugmentProfileRenderer` implemented; outputs to `.augment/agents/<id>.md`; manifest-tracked
- [ ] `HarnessCapabilityRecord` and `HARNESS_CAPABILITY_MATRIX` covering all 19 configured harnesses
- [ ] `AgentProfilesProvider` emits `not_applicable` findings for non-capable harnesses
- [ ] `doctor tool-surfaces --kind agent-profile --json` shows only six valid status values
- [ ] `ruff check` and `mypy --strict` pass on all changed modules

---

## Risks

- Amazon Q user-global path (`~/.aws/amazonq/cli-agents/`) may not exist on developer machines — handle `FileNotFoundError` gracefully in doctor inspection
- `AI_CHOICES` in `config.py` may not yet have all 19 harnesses after WP07 removes Roo Code; coordinate with WP07 on the final key set
- `HarnessCapabilityRecord.reason` must not contain user-identifying data or paths that vary by machine — keep reasons generic
