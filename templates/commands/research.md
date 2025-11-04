---
description: Run the Phase 0 research workflow to scaffold research artifacts before task planning.
scripts:
  sh: spec-kitty research
  ps: spec-kitty research
---
**Path reference rule:** When you mention directories or files, provide either the absolute path or a path relative to the project root (for example, `kitty-specs/<feature>/tasks/`). Never refer to a folder by name alone.

**UTF-8 Encoding Rule:** When writing research.md, data-model.md, or CSV files, use only UTF-8 compatible characters. Avoid Windows-1252 smart quotes (" " ' '), em dashes, or copy-pasted content from Microsoft Office. When copying academic citations or research from web sources, replace smart quotes with standard quotes (" ') and use simple ASCII arrows (-> not →). See [templates/common/utf8-file-writing-guidelines.md](templates/common/utf8-file-writing-guidelines.md) for details.

*Path: [templates/commands/research.md](templates/commands/research.md)*


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

## Post-Generation Validation

After writing research.md, data-model.md, and CSV files, validate encoding:

```bash
python scripts/validate_encoding.py kitty-specs/$FEATURE_NUM-*/
```

**This is critical for research documents** which often include:
- Academic citations copied from papers (may have smart quotes)
- URLs and metadata from web sources
- Mathematical symbols (×, ÷, →, ≈)
- International author names with accented characters

If errors are found, run with `--fix` to convert to UTF-8:

```bash
python scripts/validate_encoding.py --fix kitty-specs/$FEATURE_NUM-*/
```
