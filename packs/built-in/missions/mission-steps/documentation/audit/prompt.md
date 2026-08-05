---
description: Audit existing documentation coverage and build an evidence-based gap analysis
---
# /spec-kitty.audit - Audit Documentation Coverage

**Path reference rule:** When you mention directories or files, provide either the absolute path or a path relative to the project root (for example, `kitty-specs/<mission>/gap-analysis.md`). Never refer to a folder by name alone.

**In repos with multiple missions, always pass `--mission <handle>` to every spec-kitty command.** The `<handle>` can be the mission's `mission_id` (ULID), `mid8` (first 8 chars of the ULID), or `mission_slug`.

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Location Pre-flight Check

**BEFORE PROCEEDING:** Verify you are working in the repository root checkout.

```bash
pwd
git branch --show-current
```

Expected: `pwd` ends in your project root; the branch is your mission branch, not `main`. If either is wrong, `cd` to the repository root checkout and switch branches before continuing.

## What This Step Produces

- **`kitty-specs/<mission>/gap-analysis.md`** — the coverage matrix, drift findings, and prioritized gap list.

This step reads `spec.md` (the discover deliverable) to know the areas and audience in scope, and reads the actual documentation and source-of-truth surface on disk — it does not invent structure or claims.

## Goal

Produce an evidence-based gap analysis that another author could read, reproduce, and use to plan content work. Audit is the empirical step that distinguishes "we think docs are missing" from "here is the matrix of cells that are missing, ranked by user impact."

## What to Do

1. **Treat the audit as evidence-based, not impressionistic.** Every claimed gap must be traceable to either a missing artifact, a missing Divio type, or a documented mismatch between the docs and the code surface they describe.

2. **Build a coverage matrix** keyed by `(area, Divio type)`. Areas come from the discover `spec.md`; Divio types are `tutorial`, `how-to`, `reference`, `explanation`. Empty cells are gaps; populated-but-stale cells are debt.

3. **Classify each existing document by its Divio type** using frontmatter when present and content heuristics when not. Record the classification confidence (`high` / `low-confidence`) so reviewers know which entries to spot-check. Where automated detection is uncertain, mark the cell `low-confidence` rather than silently guessing — the `validate` step will revisit it.

4. **Cross-reference the documentation against the actual source-of-truth surface** (modules, endpoints, CLI commands, configuration keys). Drift between docs and code is itself a finding, not a footnote.

5. **Inventory every file under the documentation root.** Ungoverned content (a file nobody classified) is a finding, not a free pass.

6. **Prioritize gaps by user impact**, tied to the audience recorded in `spec.md`: blocks-onboarding > blocks-task > blocks-discoverability > nice-to-have. A missing tutorial for a core feature outranks a missing explanation for an edge case, even when the tutorial is harder to write.

7. **Surface drift findings at high priority.** Wrong information is worse than missing information — a stale reference page that contradicts current behavior outranks an empty cell.

8. **Make the analysis reproducible.** Capture the classification rule for every Divio-type assignment so a reviewer can challenge it: "frontmatter declares `type: how-to` and content matches the task-oriented heuristic" is a finding; "I think this is a how-to" is not.

## Success Criteria

- `gap-analysis.md` exists and the coverage matrix is complete: every `(area, Divio type)` cell carries a status (`present`, `present-but-stale`, or `missing`).
- Every gap has a stated user impact and a target audience tied back to `spec.md`.
- Drift findings cite the conflicting docs path and the contradicting source-of-truth location.
- Low-confidence classifications are flagged for the `validate` step rather than silently promoted.

## Handoff

This step produces the gap analysis and priority list only. It does **not** re-open the documentation needs or scope (those are `discover` decisions, already locked), design the documentation architecture (`design`'s job), write or fill any documentation cells (`generate`'s job), or validate the produced content against quality gates (`validate`'s job). An audit that already proposes new section trees or generator configurations is a leaked design — keep the phases clean.
