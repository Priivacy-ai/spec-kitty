---
work_package_id: WP01
title: Host-Surface Inventory Matrix
dependencies: []
requirement_refs:
- FR-001
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
agent: "claude:sonnet-4-6:reviewer:reviewer"
shell_pid: "12701"
history:
- event: created
  at: '2026-04-23T05:10:00Z'
  note: Initial generation from /spec-kitty.tasks
authoritative_surface: kitty-specs/phase-4-closeout-host-surfaces-and-trail-01KPWA5X/artifacts/
execution_mode: planning_artifact
owned_files:
- kitty-specs/phase-4-closeout-host-surfaces-and-trail-01KPWA5X/artifacts/host-surface-inventory.md
tags: []
---

# WP01 — Host-Surface Inventory Matrix

## Objective

Produce the authoritative parity matrix that catalogues every supported host surface and its current state against the advise/ask/do governance-injection contract. The matrix drives the scope of WP02, WP03, and WP04; WP05 promotes it to `docs/host-surface-parity.md` at Tranche A closeout.

This is a pure **audit + documentation** work package. No source code is modified. No tests are added here (the coverage test is part of WP05 since it runs against the promoted doc).

## Context

**Mission**: `phase-4-closeout-host-surfaces-and-trail-01KPWA5X`

**Why this work exists**: `#496` was originally "update the skill packs so every host LLM knows about advise/ask/do." The 3.2.0a5 priority slice landed two of the 15 surfaces at parity (`spec-kitty-runtime-next` for Claude Code, `spec-kitty.advise` for Codex and Vibe). The remaining 13 surfaces are unaudited. Without an authoritative matrix, WP04 has no scope and WP05 has nothing to promote.

**Ground truth for the surface list**: `src/specify_cli/upgrade/migrations/m_0_9_1_complete_lane_migration.py::AGENT_DIRS`. Per the project CLAUDE.md, this constant is the single source of truth for the 13 slash-command agent directories. The 2 Agent Skills surfaces (Codex, Vibe) live at `.agents/skills/` per the `.vibe/config.toml::skill_paths` convention.

**Scope decision required during the audit**: for each non-parity surface, decide between:
- **Inline parity content** — host the advise/ask/do guidance directly in a file within the agent directory (fits surfaces that already host skill-pack files authored in-repo).
- **Pointer** — a short file that points at the canonical skill pack (`.agents/skills/spec-kitty.advise/SKILL.md`) and explains that the host should load that content.

Record the decision per row in the matrix's `guidance_style` and `notes` columns so WP04 can execute mechanically.

## Branch Strategy

- **Planning base**: `main` (unchanged).
- **Final merge target**: `main`.
- **Execution worktree**: allocated from `lanes.json` at implement time. This WP is independent and lane-assignable without waiting.

## Subtask Guidance

### T001 — Scaffold the inventory file

**Purpose**: Create the markdown file with schema header and an empty table skeleton.

**Steps**:
1. Create the file at `kitty-specs/phase-4-closeout-host-surfaces-and-trail-01KPWA5X/artifacts/host-surface-inventory.md` (the `artifacts/` directory is already present).
2. Write a preamble that:
   - Names the purpose: "authoritative parity matrix for the 15 supported host surfaces".
   - Links back to `contracts/host-surface-inventory.md` for schema.
   - Names the canonical source-of-truth for surfaces: `src/specify_cli/upgrade/migrations/m_0_9_1_complete_lane_migration.py::AGENT_DIRS`.
3. Write the table header with all 9 columns in this order: `surface_key`, `directory`, `kind`, `has_advise_guidance`, `has_governance_injection`, `has_completion_guidance`, `guidance_style`, `parity_status`, `notes`.
4. Leave the body empty — rows are populated in T004.

**Reference**: [contracts/host-surface-inventory.md](../contracts/host-surface-inventory.md) for the full schema and example rows.

### T002 — Audit slash-command surfaces (13)

**Purpose**: For each of the 13 slash-command host surfaces, determine whether advise/ask/do guidance is present, how it is expressed, and what gap (if any) exists.

**Surfaces to audit** (from `AGENT_DIRS`):

| surface_key | directory |
|-------------|-----------|
| `claude` | `.claude/commands/` |
| `copilot` | `.github/prompts/` |
| `gemini` | `.gemini/commands/` |
| `cursor` | `.cursor/commands/` |
| `qwen` | `.qwen/commands/` |
| `opencode` | `.opencode/command/` |
| `windsurf` | `.windsurf/workflows/` |
| `kilocode` | `.kilocode/workflows/` |
| `auggie` | `.augment/commands/` |
| `roo` | `.roo/commands/` |
| `q` | `.amazonq/prompts/` |
| `kiro` | `.kiro/prompts/` |
| `agent` | `.agent/workflows/` |

**Per surface, check for**:

1. **`has_advise_guidance`**: Does any file in this directory (or its skill-pack siblings, where applicable) teach the host when to call `spec-kitty advise` / `ask` / `do`?
2. **`has_governance_injection`**: Does any file teach how to read `governance_context_text` from the response and inject it into the host's working context?
3. **`has_completion_guidance`**: Does any file teach the host to call `spec-kitty profile-invocation complete --invocation-id <id> --outcome <outcome>` after the work is done?

**Method**:
- `grep -rl "spec-kitty advise\|spec-kitty ask\|spec-kitty do\|profile-invocation complete\|governance_context_text" <directory>` in each surface directory.
- Open the top matches; judge whether the matches are meaningful guidance or incidental references.
- If guidance exists but is fragmentary, mark `partial` and note the gap.

**Special case — `claude`**: the canonical content for Claude Code lives at `src/doctrine/skills/spec-kitty-runtime-next/SKILL.md`, which is distributed to Claude Code hosts via the doctrine skill distribution (not via `.claude/commands/`). Record the parity source for `claude` with `guidance_style=inline` and note the actual source path in `notes`.

### T003 — Audit Agent Skills surfaces (2)

**Purpose**: Confirm parity status for Codex CLI and Vibe.

**Surfaces**:
- **codex**: reads `.agents/skills/` directly. Canonical file: `.agents/skills/spec-kitty.advise/SKILL.md` (already at parity per 3.2.0a5).
- **vibe**: reads `.agents/skills/` via `.vibe/config.toml::skill_paths`. Shares the same skill pack.

**Per surface**:
1. Open `.agents/skills/spec-kitty.advise/SKILL.md` and verify the three parity sections exist: "Discover profiles", "Get governance context (advise/ask/do)", "Close the record", and the "Governance context injection" subsection added in 3.2.0a5.
2. Confirm `has_advise_guidance=yes`, `has_governance_injection=yes`, `has_completion_guidance=yes`.
3. For `vibe`, also confirm `.vibe/config.toml` exists and references `.agents/skills/` via `skill_paths`. If `.vibe/config.toml` is missing, record a `partial` with a note; otherwise `at_parity`.

### T004 — Populate rows with parity_status and notes

**Purpose**: Convert the audit findings from T002 + T003 into the matrix body.

**Steps**:
1. For each of the 15 surfaces, emit one row using the schema from T001.
2. Derive `parity_status`:
   - `at_parity`: all three guidance flags are `yes` AND the content matches the shape of the canonical reference content.
   - `partial`: some flags `yes`, some `no`, or guidance present but misaligned.
   - `missing`: all three flags `no`.
3. For every non-`at_parity` row, write a `notes` entry that explains the gap and recommends either:
   - `inline` style with the specific file path where WP04 will add the content, OR
   - `pointer` style with the specific file path where WP04 will add a pointer to `.agents/skills/spec-kitty.advise/SKILL.md`.
4. Per FR-006: every `pointer` style row MUST have a rationale in `notes` explaining why the surface does not host the content inline.

**Example row** (well-formed):

```markdown
| claude | .claude/commands/ | slash_command | yes | yes | yes | inline | at_parity | Canonical content lives at src/doctrine/skills/spec-kitty-runtime-next/SKILL.md ("Standalone Invocations (Outside Missions)" section) and is distributed via doctrine skills. |
```

**Example row** (non-parity with remediation plan):

```markdown
| cursor | .cursor/commands/ | slash_command | no | no | no | pointer | missing | No advise/ask/do guidance in .cursor/commands/. WP04 will add `.cursor/commands/spec-kitty-standalone.md` as a pointer file referencing the canonical content in `.agents/skills/spec-kitty.advise/SKILL.md`, because Cursor reads per-command files and inlining the full canonical content would duplicate doctrine. |
```

## Definition of Done

- [ ] `kitty-specs/phase-4-closeout-host-surfaces-and-trail-01KPWA5X/artifacts/host-surface-inventory.md` exists with a schema-compliant 9-column table.
- [ ] Every `AGENT_DIRS` surface key has exactly one row; both Agent Skills surfaces (`codex`, `vibe`) also each have exactly one row. Total rows: 15.
- [ ] Every row has a non-empty `parity_status` (`at_parity`, `partial`, or `missing`).
- [ ] Every non-`at_parity` row has a `notes` entry specifying the file path for WP04 and the rationale for `inline` vs `pointer`.
- [ ] Rows for `claude`, `codex`, `vibe` are marked `at_parity` (per 3.2.0a5 priority slice).
- [ ] Commit message references the mission slug and `#496`.

## Risks

- **Audit miss**: a surface is marked `at_parity` but the content does not actually teach a host LLM. Mitigation: when in doubt, read the full file and compare to the canonical `.agents/skills/spec-kitty.advise/SKILL.md` structure before judging.
- **Generated-copy confusion**: some agent directories host `/spec-kitty.*` slash-command mirrors that are generated from `src/specify_cli/missions/*/command-templates/`. These generated files are NOT the target of WP04's parity work; they carry per-mission-step content, not standalone-invocation content. Do not conflate them with skill-pack guidance. Mitigation: WP01 only records standalone-invocation guidance, not `/spec-kitty.*` command content.
- **Ambiguous parity**: a file mentions `advise` but doesn't teach completion. Mark `partial`, not `at_parity`.

## Reviewer Guidance

Reviewer should:
- Spot-check 3 randomly selected rows for accuracy (read the actual surface file and verify the audit claim).
- Confirm `parity_status=at_parity` is reserved for surfaces that genuinely cover all three guidance dimensions.
- Confirm every `pointer` row names the exact file path WP04 will create, and the rationale is specific (not boilerplate).

## Activity Log

- 2026-04-23T05:24:13Z – claude:sonnet-4-6:implementer:implementer – shell_pid=11864 – Started implementation via action command
- 2026-04-23T05:27:27Z – claude:sonnet-4-6:implementer:implementer – shell_pid=11864 – Host-surface inventory matrix complete: 15/15 surfaces audited and scoped for WP04 rollout
- 2026-04-23T05:28:03Z – claude:sonnet-4-6:reviewer:reviewer – shell_pid=12701 – Started review via action command
