---
description: Accept the published documentation handoff as the mission baseline
---
# /spec-kitty.accept - Accept Documentation Handoff

**Path reference rule:** When you mention directories or files, provide either the absolute path or a path relative to the project root (for example, `kitty-specs/<mission>/release.md`). Never refer to a folder by name alone.

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

## What This Step Produces

An explicit **acceptance decision** — not new documentation. This is the final checkpoint that the published handoff is complete, traceable, and ready to become the baseline for future documentation work.

## Goal

Confirm the publication handoff is complete and accountable, and record the mission as accepted — or block and route back to the appropriate earlier step.

## What to Do

1. **Confirm `release.md` exists and names what shipped**, where it shipped, the source revision, and the living-documentation cadence. A handoff document missing any of these is not acceptable as-is.

2. **Confirm the publish handoff has an accountable owner** for support and future revalidation. "Someone will pick this up eventually" is not an owner.

3. **Confirm any caveats accepted during `publish` are visible and linked to follow-up work where needed.** A caveat buried in prose with no tracked follow-up is a silent risk.

4. **Do not introduce new content here.** If acceptance surfaces a content gap, block acceptance and route the gap back to the appropriate earlier step (`generate` for missing content, `design` for missing architecture, `discover` for missing scope) rather than patching it in this step.

5. **Check for hidden blockers.** Read `audit-report.md` and `release.md` for any unresolved blocker recorded only in free-text prose rather than as an explicit disposition — a `block-publish` risk that never got a resolution is a reason to withhold acceptance, not a footnote to wave through.

## Success Criteria

- `audit-report.md` records a `ready-to-publish` verdict, or explicitly accepted caveats with rationale.
- `release.md` records published URLs (or the exact publication target), source revision, generator versions, and a maintenance owner.
- Living-documentation expectations are explicit enough for the next `discover`/`audit` cycle to consume directly.
- No unresolved blocker is hidden in prose-only notes.

## Handoff

This step does **not** reopen scope, generate documentation, validate generated content, or publish artifacts. It only records whether the publication handoff is accepted as the mission baseline. If acceptance is blocked, name the specific earlier step the gap belongs to and stop here — do not attempt to close the gap yourself in this step.
