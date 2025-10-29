---
description: Run the Phase 0 research workflow to scaffold research artifacts before task planning.
scripts:
  sh: spec-kitty research
  ps: spec-kitty research
---

## Goal

Create `research.md`, `data-model.md`, and supporting CSV stubs based on the active mission so implementation planning can reference concrete decisions and evidence.

## What to do

1. Confirm you are working inside the correct feature worktree (e.g., `001-feature-name`). Check with:
   ```bash
   git branch --show-current
   ```
   If you are still on `main`, switch into the feature worktree before proceeding.
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
