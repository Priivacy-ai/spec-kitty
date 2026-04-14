---
work_package_id: WP07
title: Regression Snapshots and Documentation
dependencies:
- WP01
- WP02
- WP03
- WP04
- WP05
- WP06
base_branch: main
base_commit: 1b6e14d8c28924c63e0d94f08aa23f37fd082eab
created_at: '2026-04-14T10:47:07.759646+00:00'
subtasks:
- T033
- T034
- T035
- T036
- T037
lane: "doing"
shell_pid: "22219"
history:
- at: '2026-04-14T00:00:00+00:00'
  actor: planner
  event: created
authoritative_surface: tests/specify_cli/regression/
branch_strategy: lane-worktree
execution_mode: code_change
merge_target_branch: main
owned_files:
- tests/specify_cli/regression/test_twelve_agent_parity.py
- tests/specify_cli/regression/_twelve_agent_baseline/**
- README.md
- CLAUDE.md
planning_base_branch: main
requirement_refs:
- FR-014
- FR-015
- FR-016
- NFR-005
---

# WP07 — Regression Snapshots and Documentation

## Objective

Lock in NFR-005 (the twelve non-migrated agents produce byte-identical command-file output before and after this mission) with a regression snapshot, and ship the documentation updates — README supported-tools table, `CLAUDE.md` Supported AI Agents section, quickstart validation — that let users actually discover Mistral Vibe support and understand the new Codex integration shape in the next release.

## Context

This is the close-out WP. It depends on every previous WP because:

- The regression baseline must be captured **before** WP02's template edits land (see WP02 §Subtask T009 Option A), but asserted **after** all other changes.
- Documentation must reflect the actual shipped behavior, which means it waits for WP04-WP06.

The regression baseline capture is the most delicate part. Do it via one of two options:

- **Option A (recommended)**: capture the baseline at mission start, **before any WP02 template edits**, and store it as a fixture. Assert parity at the end against the stored baseline.
- **Option B**: capture the baseline at mission end against a clean pre-mission checkout (branch from merge-base). More complex; more fragile in CI; prefer Option A.

Choose Option A. Capture T033's baseline as the very first task scheduled after `finalize-tasks` but before WP02's template edits land.

## Branch Strategy

- Planning base branch: `main`
- Final merge target: `main`
- Execution worktree: per-lane from `lanes.json` after `finalize-tasks`. Depends on every prior WP.

## Implementation

### Subtask T033 — Capture pre-mission baseline snapshot

Create `tests/specify_cli/regression/_twelve_agent_baseline/` with one subdirectory per non-migrated agent (`claude`, `copilot`, `gemini`, `cursor`, `qwen`, `opencode`, `windsurf`, `kilocode`, `auggie`, `roo`, `q`, `antigravity`). Inside each, store the exact bytes the pre-mission renderer would produce for each of the 16 canonical commands.

Mechanism (do this as the very first commit in WP07):

1. Check out the mission's merge-base on a scratch worktree.
2. Run the pre-mission renderer for each non-migrated agent against each canonical command template.
3. Copy the output files verbatim into the baseline fixture directory, preserving the agent-specific extension (`.md`, `.toml`, `.prompt.md`) and the exact content including any trailing newline.
4. Commit the fixture directory to this WP's worktree.

Name each file `<agent>/<command>.<ext>` — matching the agent's `AGENT_COMMAND_CONFIG` entry's extension. For Gemini (TOML), commit the TOML output; for others, markdown.

Document the capture procedure in a module docstring at `tests/specify_cli/regression/_twelve_agent_baseline/__init__.py` (or a sibling README) so a future maintainer can regenerate it.

### Subtask T034 — Regression test

Create `tests/specify_cli/regression/test_twelve_agent_parity.py`:

```python
NON_MIGRATED_AGENTS = (
    "claude", "copilot", "gemini", "cursor", "qwen", "opencode",
    "windsurf", "kilocode", "auggie", "roo", "q", "antigravity",
)

CANONICAL_COMMANDS = (
    "specify", "plan", "tasks", "tasks-outline", "tasks-packages",
    "tasks-finalize", "implement", "review", "accept", "merge",
    "analyze", "research", "checklist", "status", "dashboard", "charter",
)

@pytest.mark.parametrize("agent", NON_MIGRATED_AGENTS)
@pytest.mark.parametrize("command", CANONICAL_COMMANDS)
def test_command_output_unchanged(agent, command, tmp_path):
    baseline = _load_baseline(agent, command)
    produced = _render_for_agent(agent, command, tmp_path)
    assert produced == baseline, (
        f"Command-file output for {agent}/{command} changed. "
        f"This mission must not modify the twelve non-migrated agents. "
        f"If the change is intentional (e.g., a cross-agent template edit), "
        f"regenerate the baseline with: <documented procedure>."
    )
```

The `_render_for_agent` helper calls into Spec Kitty's existing command-file rendering path (the one that WP04 explicitly left unchanged for these twelve agents) and captures the bytes written to the agent's command directory.

The test should skip gracefully if the baseline is missing and print a clear error explaining how to regenerate it.

### Subtask T035 — Update README supported-tools table [P]

Find the supported-tools table in `README.md` (search for `opencode` or `Codex CLI`). Add a row for Mistral Vibe. Example layout (adapt to the existing table's column order and styling):

| Tool | Agent Key | Command Surface | Installation |
|------|-----------|-----------------|--------------|
| ... existing rows ... |
| **Mistral Vibe** | `vibe` | Agent Skills (`.agents/skills/`) | `uv tool install mistral-vibe` or `curl -LsSf https://mistral.ai/vibe/install.sh \| bash` |

Reword the Codex row to reflect the Agent Skills delivery:
- Command Surface column: change from `.codex/prompts` (or similar) to `Agent Skills (.agents/skills/)`.
- Add a short note in the table preamble or footer explaining that Codex and Vibe share the `.agents/skills/` root via reference-counted installation.

Also update the `spec-kitty init --ai` docs section to list `vibe` alongside the existing keys, ideally sorted alphabetically.

### Subtask T036 — Update `CLAUDE.md` [P]

Sections to edit:

- **Supported AI Agents table** — add a row for Mistral Vibe. Keep the format exactly consistent with existing rows (directory, subdirectory, slash-command notation).
- **Active Technologies** — optionally add a bullet noting the new `src/specify_cli/skills/command_*.py` modules and the manifest location, following the file's existing bullet style.
- **Any agent-list examples** — update to include vibe if vibe's absence would be misleading.

Do not restructure CLAUDE.md or add sections beyond what is strictly necessary for describing the new agent and the new modules. Minimum diff.

### Subtask T037 — Validate quickstart.md end-to-end

In a clean smoke-test project (can be a tmpdir on your workstation or a CI job), walk through every scenario in `kitty-specs/083-agent-skills-codex-vibe/quickstart.md`:

- Scenario 1: New Vibe user onboards — run the exact commands and confirm the printed output, file layout, and suggested next steps match the document.
- Scenario 2: Existing Codex user upgrades — start from a fixture seeded like `owned_unedited_only` (reuse WP06's fixture) and run `spec-kitty upgrade`.
- Scenario 3: Both configured.
- Scenario 4: Repair path with `spec-kitty doctor` and `spec-kitty agent config sync`.

If any scenario's written instructions diverge from observed behavior, update the quickstart to match reality (prefer updating docs over changing behavior this late in the mission).

Commit the adjusted `quickstart.md` — but note that `quickstart.md` is in `kitty-specs/083-agent-skills-codex-vibe/`, not in an owned path for this WP. Add that file to `owned_files` in this WP's frontmatter **only if** adjustments are needed (current draft should be correct). If edits are needed, coordinate the ownership addition with a small clarifying commit before the edit.

## Definition of Done

- [ ] `tests/specify_cli/regression/_twelve_agent_baseline/` contains expected output for all 12 agents × 16 commands.
- [ ] `pytest tests/specify_cli/regression/test_twelve_agent_parity.py` passes with zero skips and zero failures.
- [ ] README supported-tools table includes Vibe and reflects the Codex Agent Skills change.
- [ ] `CLAUDE.md` Supported AI Agents table includes Vibe; new modules referenced if material.
- [ ] Quickstart scenarios walk correctly against a clean smoke-test project.
- [ ] `ruff check tests/specify_cli/regression/` passes.
- [ ] No changes outside `owned_files` unless quickstart.md ownership is expanded deliberately.

## Risks

- **Baseline capture timing.** If T033 runs after WP02's template edits land, the baseline will bake in the edits and the parity test will falsely pass. Explicitly schedule T033 before any WP02 changes — the easiest enforcement is to capture the baseline in a separate early commit on this WP's branch before anything else.
- **Renderer invocation paths.** The `_render_for_agent` helper must exactly match the code path the production CLI uses, not a shortened test-only path. Any divergence produces false negatives. Factor out the renderer entry point so tests call the same function production calls.
- **README format drift.** If README uses a specific markdown table convention (e.g., pipe alignment, no trailing pipes), match it. A visually identical but pipe-misaligned addition is a review reject.

## Reviewer Guidance

- `git diff --stat` on this WP's branch should show README, CLAUDE.md, and a fixture tree — nothing else mission-critical.
- Run the regression test locally and confirm zero skips. A skip is a silent pass.
- Read the updated README table as a first-time user. Confirm the `vibe` row is no less informative than any existing row.
- Confirm `quickstart.md`'s command invocations match the real CLI surface after the mission lands.

## Command to run implementation

```bash
spec-kitty agent action implement WP07 --agent <name>
```
