---
description: Run the Phase 0 research workflow to scaffold research artifacts before task planning.
scripts:
  sh: spec-kitty research
  ps: spec-kitty research
---
**Path reference rule:** When you mention directories or files, provide either the absolute path or a path relative to the project root (for example, `kitty-specs/<feature>/tasks/`). Never refer to a folder by name alone.


*Path: [templates/commands/research.md](templates/commands/research.md)*


## Location Pre-flight Check

**BEFORE PROCEEDING:** Verify you are working in the feature worktree.

```bash
pwd
git branch --show-current
```

**Expected output:**
- `pwd`: Should end with `.worktrees/001-feature-name` (or similar feature worktree)
- Branch: Should show your feature branch name like `001-feature-name` (NOT `main`)

**If you see the main branch or main repository path:**

⛔ **STOP - You are in the wrong location!**

This command creates research artifacts in your feature directory. You must be in the feature worktree.

**Correct the issue:**
1. Navigate to your feature worktree: `cd .worktrees/001-feature-name`
2. Verify you're on the correct feature branch: `git branch --show-current`
3. Then run this research command again

---

## What This Command Creates

When you run `{SCRIPT}`, the following files are generated in your feature directory:

**Generated files**:
- **research.md** – Decisions, rationale, and supporting evidence
- **data-model.md** – Entities, attributes, and relationships
- **research/evidence-log.csv** – Sources and findings audit trail
- **research/source-register.csv** – Reference tracking for all sources

**Location**: All files go in `kitty-specs/001-feature-name/`

---

## Workflow Context

**Before this**: `/spec-kitty.plan` calls this as "Phase 0" research phase

**This command**:
- Scaffolds research artifacts
- Creates templates for capturing decisions and evidence
- Establishes audit trail for traceability

**After this**:
- Fill in research.md, data-model.md, and CSV logs with actual findings
- Continue with `/spec-kitty.plan` which uses your research to drive technical design

---

## Goal

Create `research.md`, `data-model.md`, and supporting CSV stubs based on the active mission so implementation planning can reference concrete decisions and evidence.

## What to do

1. You should already be in the correct feature worktree (verified above with pre-flight check).
2. Run `{SCRIPT}` to generate the mission-specific research artifacts. (Add `--force` only when it is acceptable to overwrite existing drafts.)
3. Open the generated files and fill in the required content:
   - `research.md` – capture decisions, rationale, and supporting evidence.
   - `data-model.md` – document entities, attributes, and relationships discovered during research.
   - `research/evidence-log.csv` & `research/source-register.csv` – log all sources and findings so downstream reviewers can audit the trail.
4. If your research generates additional templates (spreadsheets, notebooks, etc.), store them under `research/` and reference them inside `research.md`.
5. Summarize open questions or risks at the bottom of `research.md`. These should feed directly into `/spec-kitty.tasks` and future implementation prompts.

## Success Criteria

- `kitty-specs/<feature>/research.md` explains every major decision with references to evidence.
- `kitty-specs/<feature>/data-model.md` lists the entities and relationships needed for implementation.
- CSV logs exist (even if partially filled) so evidence gathering is traceable.
- Outstanding questions from the research phase are tracked and ready for follow-up during planning or execution.
