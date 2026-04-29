---
work_package_id: WP05
title: How-To — Retrospective and Troubleshooting
dependencies:
- WP01
requirement_refs:
- FR-010
- FR-014
planning_base_branch: docs/charter-end-user-docs-828
merge_target_branch: docs/charter-end-user-docs-828
branch_strategy: Planning artifacts for this feature were generated on docs/charter-end-user-docs-828. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into docs/charter-end-user-docs-828 unless the human explicitly redirects the landing branch.
subtasks:
- T018
- T019
- T020
agent: curator-carla
history:
- date: '2026-04-29'
  author: spec-kitty.tasks
  note: Initial WP generated
authoritative_surface: docs/how-to/
execution_mode: planning_artifact
owned_files:
- docs/how-to/use-retrospective-learning.md
- docs/how-to/troubleshoot-charter.md
tags: []
---

# WP05 — How-To: Retrospective and Troubleshooting

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load the agent profile assigned to this work package:

```
/ad-hoc-profile-load curator-carla
```

This loads domain knowledge, tool preferences, and behavioral guidelines for documentation writing. Do not proceed until the profile confirms it has loaded.

## Objective

Write two new how-to pages: `use-retrospective-learning.md` and `troubleshoot-charter.md`. These are P1 how-to guides covering the retrospective learning loop operator workflow and Charter failure diagnostics.

This WP can run in parallel with WP02–WP04, WP06–WP08 after WP01 completes.

## Branch Strategy

- **Planning base branch**: `docs/charter-end-user-docs-828`
- **Merge target**: `main`
- **Execution workspace**: allocated by `lanes.json` at `spec-kitty agent action implement WP05 --agent <name>`; do not guess the worktree path

## Context

### CLI Verification

Before writing any command snippet, run:

```bash
uv run spec-kitty retrospect --help
uv run spec-kitty retrospect summary --help
uv run spec-kitty agent retrospect synthesize --help
uv run spec-kitty agent retrospect synthesize --dry-run --help   # verify --dry-run flag
uv run spec-kitty agent retrospect synthesize --apply --help     # verify --apply flag
```

If a subcommand is absent, omit it rather than inventing behavior.

**Note on command names**: The retrospective command tree is `spec-kitty retrospect` (not `retro`). The synthesizer is `spec-kitty agent retrospect synthesize` (not `retro synthesizer`). Always use `uv run spec-kitty`, never the ambient `spec-kitty` binary.

### Retrospective Gate Invariant

**Autonomous mode**: the retrospective cannot be skipped. **HiC (Human in Charge) mode**: skipping requires explicit operator action with an audit trail. Both modes must be documented accurately.

### Source: research.md

`kitty-specs/charter-end-user-docs-828-01KQCSYD/research.md` Section 2 covers what exists and what's missing for the retrospective learning loop. The existing `docs/retrospective-learning-loop.md` has partial content (HiC/autonomous behavior, lacks synthesizer dry-run/apply).

## Subtask Guidance

### T018 — Write docs/how-to/use-retrospective-learning.md

**File**: `docs/how-to/use-retrospective-learning.md`  
**Title**: "How to Use the Retrospective Learning Loop"

**Scope** (from data-model.md): `retrospect summary`; `agent retrospect synthesize --dry-run`; `agent retrospect synthesize --apply`; proposal kinds; conflict resolution; staleness; provenance; facilitator failures; HiC vs autonomous behavior; skip semantics.

**Structure**:
1. Context link: "For an explanation of why retrospectives exist and the gate model, see [Understanding the Retrospective Learning Loop](../explanation/retrospective-learning-loop.md)."
2. **View the retrospective summary** — `uv run spec-kitty retrospect summary` with example output description.
3. **Preview synthesis proposals (dry-run)** — `uv run spec-kitty agent retrospect synthesize --dry-run`; what it shows; how to read proposal kinds.
4. **Apply synthesis** — `uv run spec-kitty agent retrospect synthesize --apply`; what changes; provenance trail.
5. **Resolve conflicts** — what to do when the synthesizer rejects proposals; conflict output reading.
6. **Staleness** — when the retrospective report is stale (too many unreviewed missions); how to detect and resolve.
7. **Facilitator failures** — what happens when the retrospective facilitator itself fails (e.g., the retrospective record cannot be loaded, the synthesis process errors). Symptoms, diagnostics (`retrospect summary` output), and recovery steps.
8. **HiC vs Autonomous behavior**:
   - Autonomous mode: retrospective gate is mandatory, cannot be skipped.
   - HiC mode: operator can skip with explicit action; an audit record is created.
9. **Skip semantics** — how to skip in HiC mode (if the CLI supports it — verify with `retrospect --help`); what the audit record looks like.
10. **Exit codes** — `agent retrospect synthesize` exit codes (0 = success, non-zero = failure reason). Check `--help` for documented exit codes; if undocumented, note "see [retrospective-schema.md](../reference/retrospective-schema.md) for exit codes."

**Cross-links ("See also")**:
- `docs/explanation/retrospective-learning-loop.md`
- `docs/reference/retrospective-schema.md`
- `docs/3x/charter-overview.md`

### T019 — Write docs/how-to/troubleshoot-charter.md

**File**: `docs/how-to/troubleshoot-charter.md`  
**Title**: "Troubleshooting Charter Failures"

**Scope** (from data-model.md): stale bundle, missing doctrine, compact-context limitation, retrospective gate failure, synthesizer rejection.

**Structure** — one section per failure mode:

#### 1. Stale bundle
- **Symptoms**: `charter status` reports drift between `charter.md` and the bundle; `spec-kitty next` injects outdated context.
- **Fix**: `charter lint` → `charter bundle`.

#### 2. Missing doctrine
- **Symptoms**: `charter status` reports no bundle or bundle is empty; `spec-kitty next` fails with a "no governance context" error (verify exact error message against the CLI).
- **Fix**: Run the full synthesis flow: `charter synthesize` → `charter bundle`.

#### 3. Compact-context limitation
- **Symptoms**: Governed mission actions receive incomplete Charter context; large project governance gets truncated.
- **What it is**: When DRG context is too large to include in full, the runtime falls back to compact-context mode (issue #787 — check if open/closed; if closed, note the version that fixed it; if open, link or write "see issue #787").
- **Workaround**: Reduce doctrine scope by trimming `charter.md`; or break the project into smaller governance domains.

#### 4. Retrospective gate failure
- **Symptoms**: `spec-kitty next` or mission completion blocks with a retrospective gate error.
- **Fix**: Run `retrospect summary` to review the pending retrospective; `agent retrospect synthesize --apply` to process it. In HiC mode, you can skip with the appropriate command (verify with `retrospect --help`).

#### 5. Synthesizer rejection
- **Symptoms**: `agent retrospect synthesize --apply` exits with non-zero code; proposals not applied.
- **Diagnosis**: Read the rejection output; check proposal kinds and conflict fields.
- **Fix**: Resolve conflicts manually in `charter.md`; re-run synthesis.

**Cross-links ("See also")**:
- `docs/how-to/synthesize-doctrine.md`
- `docs/how-to/use-retrospective-learning.md`
- `docs/reference/retrospective-schema.md`
- `docs/3x/charter-overview.md`

### T020 — Smoke-test retro snippets; add cross-links

Smoke-test the retrospect commands from T018:

```bash
TMPDIR=$(mktemp -d)
cd "$TMPDIR"
git init -q
SPEC_KITTY_ENABLE_SAAS_SYNC=1 uv run spec-kitty retrospect summary 2>&1
# Document the actual output/error in the page — do NOT use || true to mask errors
cd -
rm -rf "$TMPDIR"
```

**Important**: Do NOT append `|| true` to mask command failures. If the command fails, document the actual error message in the page rather than hiding it. Failures are expected output when no retrospective record exists — document them accurately.

For retrospect commands that require a real retrospective record (i.e., need a completed mission first), document in the page: "This command requires at least one completed mission with a retrospective record."

After smoke-testing:
- Verify both pages link to `docs/reference/retrospective-schema.md`
- Verify `grep 'TODO' docs/how-to/use-retrospective-learning.md docs/how-to/troubleshoot-charter.md` → zero results

## Definition of Done

- [ ] `use-retrospective-learning.md` written: `retrospect summary`, `agent retrospect synthesize --dry-run`, `agent retrospect synthesize --apply`, conflict resolution, facilitator failures, HiC vs autonomous, skip semantics, exit codes
- [ ] `troubleshoot-charter.md` written: stale bundle, missing doctrine, compact-context limitation, retro gate failure, synthesizer rejection
- [ ] All command snippets use `retrospect summary` / `agent retrospect synthesize` — not `retro summary` / `retro synthesizer`
- [ ] No `|| true` masking in smoke-test commands
- [ ] Compact-context limitation section links issue #787 or notes resolution status
- [ ] Smoke-test completed (retrospect commands verified or noted as requiring completed mission)
- [ ] Both pages link to `docs/reference/retrospective-schema.md`
- [ ] Both pages appear in `docs/how-to/toc.yml` (added by WP01)
- [ ] `grep 'TODO' docs/how-to/use-retrospective-learning.md docs/how-to/troubleshoot-charter.md` → zero results
- [ ] `uv run pytest tests/docs/ -q` passes
