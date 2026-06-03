---
work_package_id: WP03
title: Antigravity and Kiro Harness Verification
dependencies: []
requirement_refs:
- FR-009
- FR-010
- FR-011
- FR-012
tracker_refs: []
planning_base_branch: kitty/mission-agent-harness-install-audit-follow-through-01KT5YTQ
merge_target_branch: kitty/mission-agent-harness-install-audit-follow-through-01KT5YTQ
branch_strategy: Planning artifacts for this mission were generated on kitty/mission-agent-harness-install-audit-follow-through-01KT5YTQ. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/mission-agent-harness-install-audit-follow-through-01KT5YTQ unless the human explicitly redirects the landing branch.
subtasks:
- T012
- T013
- T014
- T015
- T016
- T017
- T018
agent: claude
history:
- date: '2026-06-03'
  status: planned
agent_profile: researcher-robbie
authoritative_surface: docs/reference/supported-harnesses.md
execution_mode: code_change
owned_files:
- docs/reference/supported-harnesses.md
- docs/how-to/harnesses/antigravity.md
- docs/how-to/harnesses/kiro.md
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned agent profile:

```
/ad-hoc-profile-load researcher-robbie
```

Apply the Lynn Cole engineering culture (DIRECTIVE_039) throughout: only document what is verified. Never present an assumption as a fact. Every install-surface claim in the output must cite a verified source (CLI output, upstream docs, or an explicit "unverified" label).

---

## Objective

Verify Antigravity CLI plugin/skills/MCP/hook install surfaces via live CLI access and document findings. Verify whether Kiro has a plugin/Powers bundle primitive via upstream docs. Commit verified findings — or explicit "not verified" records — to `docs/reference/supported-harnesses.md`, `docs/how-to/harnesses/antigravity.md`, and `docs/how-to/harnesses/kiro.md`. No changes to `src/`.

## Branch Strategy

- **Planning base**: `main`
- **Merge target**: `main`
- **Your workspace**: allocated by `spec-kitty agent action implement WP03 --agent claude`; use the resolved worktree path from `lanes.json`.

## Context

**Current Spec Kitty modeling for Antigravity**:
- Command/workflow surface: `.agent/workflows/`
- Possible skill surface: `.agent/skills/` and shared `.agents/skills/`
- No `docs/how-to/harnesses/antigravity.md` exists
- `docs/reference/supported-agents.md` line 22: Antigravity at `~/.agent/` globally

**Current Spec Kitty modeling for Kiro**:
- Local prompts: `.kiro/prompts/`
- Global prompts: `~/.kiro/prompts/`
- Hooks, MCP servers, steering docs
- Status in `docs/how-to/harnesses/kiro.md`: "bootstrap-only surface"
- No plugin/Powers/bundle surface verified

**Scope constraint (hard)**: This WP produces documentation only. Do NOT modify `src/specify_cli/core/config.py` or any harness registry, even if a plugin surface is confirmed. Plugin-install implementation is deferred to 3.3.x (#1635).

**Fallback rule**: If CLI access for Antigravity is unavailable, record `status: unverified` with the date and reason. Do not leave the entry blank or omit it — an explicit "not verified" record is a valid and required outcome.

---

## Subtask T012 — Access Antigravity CLI and Explore Command Surface

**Purpose**: Determine the actual Antigravity CLI command name and what plugin/config/skills subcommands exist.

**Steps**:
1. Check if Antigravity CLI is installed:
   ```bash
   which agent || which antigravity || command -v agent 2>/dev/null
   ```
2. If installed, run help:
   ```bash
   agent --help 2>&1
   agent plugin --help 2>&1 || agent plugins --help 2>&1
   agent config --help 2>&1
   agent skills --help 2>&1 || agent skill --help 2>&1
   ```
3. If not installed, attempt to access Antigravity via the browser and consult upstream docs.
4. Record: exact CLI binary name, available subcommands, any plugin/skill management operations.

**If CLI unavailable**: Note `"Antigravity CLI not installed on this system (2026-06-03). Verification deferred."` and proceed to T013 with available evidence.

**Validation**:
- [ ] Antigravity CLI availability status documented (installed/unavailable)
- [ ] If installed: available plugin/config/skills commands listed

---

## Subtask T013 — Document Verified Antigravity Install Targets

**Purpose**: Determine global vs workspace config dirs, manifest format (if any), and whether `.agent/workflows/` and `.agent/skills/` are confirmed workspace-local targets.

**Steps (if CLI available)**:
1. Check workspace config:
   ```bash
   ls .agent/ 2>/dev/null || echo "no .agent/ in cwd"
   agent config show 2>&1 || agent config list 2>&1
   ```
2. Check global config:
   ```bash
   ls ~/.agent/ 2>/dev/null
   ```
3. Look for manifest or package file:
   ```bash
   find ~/.agent .agent -name "*.json" -o -name "*.yaml" -o -name "manifest*" 2>/dev/null | head -10
   ```
4. Determine: is there a marketplace/index, a `package install` equivalent, or an import command?

**Steps (if CLI unavailable)**:
1. Browse current Antigravity documentation for: workspace config layout, global config layout, plugin/package primitives.
2. Record what can be confirmed from docs vs what requires live verification.

**Outcome to record** (one of):
- Full: global dir, workspace dir, manifest format, install command, invocation command
- Partial: what is confirmed with what evidence, what remains unverified
- None: "Antigravity install surface not verifiable without local CLI access (2026-06-03)"

**Validation**:
- [ ] Install surface documentation drafted with explicit evidence citations
- [ ] No claims presented without a source

---

## Subtask T014 — Smoke Test Spec Kitty Command Skill Under Antigravity

**Purpose**: If CLI is available and install surface is confirmed, verify end-to-end that a Spec Kitty command skill can be found and invoked by Antigravity.

**Steps (if CLI available and install confirmed)**:
1. Navigate to a test directory (or use the current worktree).
2. Confirm `.agents/skills/spec-kitty.specify/SKILL.md` exists (it should, from existing spec-kitty install).
3. Attempt to invoke: `$spec-kitty.specify` or equivalent from within Antigravity.
4. Record whether: (a) Antigravity finds the skill, (b) invocation works, (c) any config is required.

**Steps (if CLI unavailable)**:
- Skip smoke test; record "not performed — CLI unavailable".

**Validation**:
- [ ] Smoke test result documented (success, failure, or skipped with reason)

---

## Subtask T015 — Review Kiro Docs for Plugin/Powers Bundle Primitive

**Purpose**: Determine whether Kiro has any primitive that bundles prompts + hooks + MCP config + skills into one installable package.

**Steps**:
1. Browse `https://kiro.dev/docs` — look specifically for:
   - "Powers" (any bundling or packaging feature)
   - "Extensions" or "Plugins"
   - "MCP packaging" or bundle manifests
   - Release notes mentioning package installation
2. Check Kiro CLI help if available:
   ```bash
   kiro --help 2>&1
   kiro plugin --help 2>&1 || kiro powers --help 2>&1
   ```
3. Check GitHub or changelog if public — look for any `package.json`-like manifest for Kiro extensions.

**Validation**:
- [ ] Kiro docs reviewed for Powers/extensions/plugins
- [ ] Findings recorded: exists/does not exist, with source citations

---

## Subtask T016 — Classify Kiro for 3.3 Scope

**Purpose**: Make a definitive classification based on T015 findings.

**Classification logic**:
- **Promote to plugin-candidate** only if: a verified bundle primitive exists that can package prompts + hooks + MCP + skills into one installable unit with a manifest and install command.
- **Record as prompt-only** if: no such primitive exists or was found. Kiro remains prompt/hook/MCP-only and is explicitly out of #1635 scope for 3.3.

**If ambiguous**: Classify as prompt-only with a noted caveat ("Kiro may have extensions in development; classification current as of 2026-06-03 docs review").

**Record**:
```
Kiro classification (2026-06-03):
  result: prompt-only | plugin-candidate
  evidence: <cite the docs or CLI output>
  caveat: <any uncertainty>
  recommendation: include in #1635 scope | exclude from #1635 scope
```

**Validation**:
- [ ] Explicit classification written with evidence and recommendation

---

## Subtask T017 — Update `docs/reference/supported-harnesses.md`

**Purpose**: Add or update Antigravity and Kiro entries in the supported-harnesses reference with verified findings.

**Steps**:
1. Read the current `docs/reference/supported-harnesses.md` to understand the table/section format.
2. Find or create the Antigravity entry. Write it using the verified data from T012–T014:
   - If verified: list confirmed install targets, invocation syntax, global/workspace dirs
   - If unverified: write `status: unverified (2026-06-03 audit — CLI not available for verification)`
3. Find or update the Kiro entry using the classification from T016:
   - If plugin-candidate: note verified bundle primitive and install approach
   - If prompt-only: note "prompt/hook/MCP-only as of 2026-06-03 docs review; excluded from #1635 plugin-install scope"
4. Maintain the existing document structure and formatting conventions.

**Validation**:
- [ ] Antigravity entry present with sourced verification status
- [ ] Kiro entry present with explicit 3.3 scope classification
- [ ] Surrounding content unchanged

---

## Subtask T018 — Create or Update Harness How-To Pages

**Purpose**: Ensure `docs/how-to/harnesses/antigravity.md` and `docs/how-to/harnesses/kiro.md` reflect findings.

**For Antigravity**:
- If verified install surface: create `docs/how-to/harnesses/antigravity.md` using the same structure as other harness how-to pages (e.g., `docs/how-to/harnesses/codex.md`). Include: install check, command surface, Spec Kitty skill path, invocation example.
- If unverified: create a minimal stub:
  ```markdown
  # Use Spec Kitty in Antigravity

  > **Status (2026-06-03):** Install surface not yet verified. See [supported-harnesses.md](../../reference/supported-harnesses.md) for current status.

  Verification of Antigravity plugin/skills/MCP/hook install targets is pending live CLI access.
  Track progress at GitHub issue #1646.
  ```

**For Kiro**:
- Read existing `docs/how-to/harnesses/kiro.md`.
- Update the classification status section: replace the current "bootstrap-only" ambiguity with the definitive classification from T016.
- If prompt-only: add a note: "Kiro uses prompt/hook/MCP surfaces only. Plugin-bundle installation is not supported in Spec Kitty 3.3. See [supported-harnesses.md](../../reference/supported-harnesses.md) for details."
- Do not rewrite sections that are already accurate.

**Validation**:
- [ ] `docs/how-to/harnesses/antigravity.md` exists with appropriate content
- [ ] `docs/how-to/harnesses/kiro.md` updated with definitive classification
- [ ] Both pages reference `docs/reference/supported-harnesses.md` for the canonical record

---

## Definition of Done

- [ ] `docs/reference/supported-harnesses.md` has Antigravity entry with sourced verification status
- [ ] `docs/reference/supported-harnesses.md` has Kiro classification entry with explicit 3.3 scope note
- [ ] `docs/how-to/harnesses/antigravity.md` exists (either verified guide or dated stub)
- [ ] `docs/how-to/harnesses/kiro.md` reflects definitive classification
- [ ] No changes to `src/specify_cli/core/config.py` or any Python source file
- [ ] Every install-surface claim cites a verified source or explicit "unverified" label
- [ ] No files outside `owned_files` modified

## Reviewer Guidance

Check `docs/reference/supported-harnesses.md` for Antigravity and Kiro entries — both must be present, neither may present unverified claims as facts. For Kiro: the entry must have an explicit statement about 3.3 scope (in or out of #1635). Confirm `src/` was not touched. If Antigravity's entry says "unverified", that is a valid and acceptable outcome per the spec (NFR-003, C-001, C-002).
