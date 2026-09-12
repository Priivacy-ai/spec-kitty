---
description: Generate documentation content against the locked design — Divio-typed pages plus generator output
---
# /spec-kitty.generate - Generate Documentation Content

**Path reference rule:** When you mention directories or files, provide either the absolute path or a path relative to the project root (for example, `docs/reference/api/`). Never refer to a folder by name alone.

**In repos with multiple missions, always pass `--mission <handle>` to every spec-kitty command.** The `<handle>` can be the mission's `mission_id` (ULID), `mid8` (first 8 chars of the ULID), or `mission_slug`.

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Location Pre-flight Check

**BEFORE PROCEEDING:** Verify you are working in the repository root checkout (or your lane worktree, if `spec-kitty implement` allocated one for this work).

```bash
pwd
git branch --show-current
```

## What This Step Produces

- Documentation content pages under the target documentation directory (per `plan.md`'s navigation hierarchy), organized by Divio type: `tutorials/`, `how-to/`, `reference/`, `explanation/`.
- Generator output for reference content: Sphinx `autodoc`/`napoleon` for Python, JSDoc for JavaScript/TypeScript, rustdoc for Rust — whichever the `design` step selected.

## Goal

Produce the documentation content itself — Divio-typed pages written against the design's templates, plus any auto-generated reference output. This step is **execution**: the planning is already done in `discover`/`audit`/`design`.

## What to Do

1. **Stay faithful to `plan.md` and the design's architecture.** This is not the place to redesign; if the design has a defect, fix it in `design` and rerun this step — do not silently patch around it here.

2. **Honor the Divio type contract for every page.** Tutorial pages teach (learning-oriented, hands-on). How-to pages solve a stated task (goal-oriented). Reference pages describe a stable surface (information-oriented). Explanation pages give context and rationale (understanding-oriented). Mixing voices inside one page is a defect.

3. **Drive every reference-style page from the source of truth** — code, schemas, configuration. Invoke the configured generator (for example: `sphinx-build -b html docs/ docs/_build/html/`, `npx jsdoc -c jsdoc.json`, `cargo doc --no-deps`) and capture the exact command and configuration in your notes so a future author can rerun it. Hand-maintained reference drifts; generated reference stays aligned.

4. **Leave deferred Divio cells deferred.** Where `plan.md` deferred a cell, filling it here silently expands scope and breaks the discover→design→generate trace. If you believe a deferred cell must be filled now, that's a re-scoping decision — escalate, don't just write it.

5. **Populate templates completely.** Replace every bracketed stub marker (e.g. `[NEEDS CONTENT: ...]`) with real content. A published page carrying an unresolved stub marker is a quality-gate failure caught after the fact — do not leave one for `validate` to catch first.

6. **Link as designed.** Cross-links from reference into how-to, how-to into tutorial, explanation into the rest follow `plan.md`'s link graph. Do not invent ad-hoc links the navigation does not anticipate.

7. **Make tutorials and how-tos verbatim runnable.** Every command, every code block, every URL is something a reader will actually type. If it does not work in your environment, it will not work in the reader's — test it before you write it down.

8. **Mark unstable-API examples with their stability status** so readers can self-protect, and declare the living-documentation cadence and owner for pages expected to evolve with the code.

9. **Commit content in small, reviewable increments.** A single commit covering an entire section is hard to review and harder to revert.

## Success Criteria

- Every required Divio cell from `plan.md` is filled or explicitly deferred with a recorded reason.
- Generator output is reproducible: the recorded command and configuration produce the same result in a clean environment.
- Reference content is aligned with the source of truth at the moment of generation.
- No bracketed stub markers remain in any page flagged for publication.

## Handoff

This step produces documentation content against the locked design only. It does **not** reopen needs, audience, or scope (`discover` decisions), reopen the gap analysis (`audit` decisions), reopen the architecture or generator selection (`design` decisions), or decide whether the result is fit to publish (`validate`'s job). A generate output that includes new design decisions or revised audit findings is a leaked planning step — keep the phases clean.
