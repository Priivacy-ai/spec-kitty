---
work_package_id: WP03
title: Charter End-to-End Tutorial
dependencies:
- WP01
requirement_refs:
- FR-017
planning_base_branch: docs/charter-end-user-docs-828
merge_target_branch: docs/charter-end-user-docs-828
branch_strategy: Planning artifacts for this feature were generated on docs/charter-end-user-docs-828. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into docs/charter-end-user-docs-828 unless the human explicitly redirects the landing branch.
subtasks:
- T010
- T011
- T012
agent: curator-carla
history:
- date: '2026-04-29'
  author: spec-kitty.tasks
  note: Initial WP generated
authoritative_surface: docs/tutorials/
execution_mode: planning_artifact
owned_files:
- docs/tutorials/charter-governed-workflow.md
tags: []
---

# WP03 — Charter End-to-End Tutorial

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load the agent profile assigned to this work package:

```
/ad-hoc-profile-load curator-carla
```

This loads domain knowledge, tool preferences, and behavioral guidelines for documentation writing. Do not proceed until the profile confirms it has loaded.

## Objective

Write `docs/tutorials/charter-governed-workflow.md` — the single end-to-end Charter workflow tutorial (FR-017). This is the highest-value user-facing deliverable. A new user with no Charter knowledge should be able to follow it from a fresh project to a completed governed mission action.

This WP can run in parallel with WP02, WP04–WP08 after WP01 completes.

## Branch Strategy

- **Planning base branch**: `docs/charter-end-user-docs-828`
- **Merge target**: `main`
- **Execution workspace**: allocated by `lanes.json` at `spec-kitty agent action implement WP03 --agent <name>`; do not guess the worktree path

## Context

### Tutorial Arc (from data-model.md)

The tutorial must cover this complete arc:
1. Initialize governance (run `charter interview`, `charter generate`)
2. Validate the bundle (`charter lint`, `charter bundle validate`)
3. Synthesize doctrine (`charter synthesize`, `charter status`)
4. Run one governed mission action (`spec-kitty next`)
5. View retrospective summary (`retrospect summary`)
6. Next steps (where to go from here)

No assumed knowledge of the Charter model. Link to `docs/3x/charter-overview.md` for background at the top.

### Prerequisites for Writing

Run every command in the tutorial before including it:

```bash
uv run spec-kitty charter --help
uv run spec-kitty charter interview --help
uv run spec-kitty charter generate --help
uv run spec-kitty charter synthesize --help
uv run spec-kitty charter resynthesize --help
uv run spec-kitty charter status --help
uv run spec-kitty charter lint --help
uv run spec-kitty charter bundle --help
uv run spec-kitty charter bundle validate --help
uv run spec-kitty next --help
uv run spec-kitty retrospect --help
uv run spec-kitty retrospect summary --help
```

If any subcommand returns "No such command", mark that step with a note ("This command requires X") and omit it from the tutorial rather than inventing behavior.

### Smoke-Test Procedure

Run every command snippet against a temp project before publishing:

```bash
TMPDIR=$(mktemp -d)
cd "$TMPDIR"
git init -q
# Execute each tutorial step in sequence
cd -
rm -rf "$TMPDIR"
```

Never run smoke tests inside the spec-kitty source repo. If a step requires hosted auth, prefix with `SPEC_KITTY_ENABLE_SAAS_SYNC=1` and note this in the tutorial.

### Invariants

- `charter.md` is the only human-edited governance file — state this explicitly when the tutorial introduces the governance layer.
- If any tutorial step contacts hosted services, label it clearly: "**Note**: This step requires SaaS sync (`SPEC_KITTY_ENABLE_SAAS_SYNC=1`)."

## Subtask Guidance

### T010 — Write docs/tutorials/charter-governed-workflow.md

**File**: `docs/tutorials/charter-governed-workflow.md`

**Format**: DocFX frontmatter block. Title: "Tutorial: Governed Charter Workflow End-to-End"

**Structure**:

```markdown
---
title: "Tutorial: Governed Charter Workflow End-to-End"
description: Learn to set up governance, synthesize doctrine, and run a governed mission action from scratch.
---

# Tutorial: Governed Charter Workflow End-to-End

> **Background**: If you're new to Charter, read [How Charter Works](../3x/charter-overview.md) first.

## What you'll build
[One paragraph: what the reader will have at the end — a project with governance set up, doctrine synthesized, and one governed mission action run.]

## Prerequisites
- Spec Kitty 3.x installed (`uv run spec-kitty --version`)
- A git repository (new or existing)
- [If SaaS steps included: a Spec Kitty account and `SPEC_KITTY_ENABLE_SAAS_SYNC=1`]

## Step 1: Initialize governance
[charter interview + charter generate — explain what each does in one sentence before the code block]

## Step 2: Validate the bundle
[charter lint + charter bundle]

## Step 3: Synthesize doctrine
[charter synthesize --dry-run (preview) + charter synthesize (apply) + charter status — explain the dry-run vs apply distinction]

## Step 4: Run a governed mission action
[spec-kitty next — explain that Charter context is now injected automatically]

## Step 5: View the retrospective summary
[retrospect summary — show example output]

## What's next
- [How to synthesize and maintain doctrine](../how-to/synthesize-doctrine.md)
- [How to run a governed mission](../how-to/run-governed-mission.md)
- [Understanding Charter: Synthesis, DRG, and Governed Context](../explanation/charter-synthesis-drg.md)
```

Each step must include:
- One sentence explaining what this step does and why
- The command code block (verified against `--help`)
- Expected output snippet (or description of what success looks like)

**Length target**: 200–350 lines. Prioritize clarity over completeness — better to have a clean 6-step flow than an exhaustive 20-step reference.

### T011 — Smoke-test all tutorial command snippets

Execute each command in the tutorial against a temp project using the procedure in the Context section. Verify:
- Each command completes without error (or the error is expected and documented in the tutorial)
- The tutorial output matches what users will actually see
- No commands pollute the spec-kitty source repo

For steps that require a real governance interview (interactive), note that in the tutorial: "This step is interactive — follow the prompts to describe your project."

If a command fails in the smoke test:
- Check `uv run spec-kitty <command> --help` — the command may have different syntax
- Update the tutorial snippet to match reality
- Do not document behavior you cannot verify

### T012 — Verify tutorial in toc.yml; add cross-links

The tutorial should already appear in `docs/tutorials/toc.yml` (added by WP01). Verify:

```bash
grep 'charter-governed-workflow' docs/tutorials/toc.yml
```

If missing, that is a WP01 error to flag. Do not modify the toc in this WP.

Add a "See also" block at the bottom of the tutorial:

```markdown
## See also

- [How to Set Up Project Governance](../how-to/setup-governance.md)
- [How to Synthesize and Maintain Doctrine](../how-to/synthesize-doctrine.md)
- [How to Run a Governed Mission](../how-to/run-governed-mission.md)
- [How Charter Works: Synthesis, DRG, and the Bundle](../3x/charter-overview.md)
```

Verify no `[TODO: ...]` placeholders remain:
```bash
grep 'TODO' docs/tutorials/charter-governed-workflow.md
```
Zero results required.

## Definition of Done

- [ ] `docs/tutorials/charter-governed-workflow.md` written with all 6 arc steps
- [ ] DocFX frontmatter present
- [ ] Every command snippet verified against `--help` output
- [ ] Smoke-test completed against temp project (no source-repo pollution)
- [ ] Link to `docs/3x/charter-overview.md` at the top
- [ ] "See also" cross-links at the bottom
- [ ] `grep 'TODO' docs/tutorials/charter-governed-workflow.md` → zero results
- [ ] Page appears in `docs/tutorials/toc.yml`
- [ ] `uv run pytest tests/docs/ -q` passes
