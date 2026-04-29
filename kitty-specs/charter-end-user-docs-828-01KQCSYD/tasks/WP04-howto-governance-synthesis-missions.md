---
work_package_id: WP04
title: How-To — Governance, Synthesis, Missions, Glossary
dependencies:
- WP01
requirement_refs:
- FR-004
- FR-005
- FR-008
- FR-011
planning_base_branch: docs/charter-end-user-docs-828
merge_target_branch: docs/charter-end-user-docs-828
branch_strategy: Planning artifacts for this feature were generated on docs/charter-end-user-docs-828. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into docs/charter-end-user-docs-828 unless the human explicitly redirects the landing branch.
subtasks:
- T013
- T014
- T015
- T016
- T017
agent: curator-carla
history:
- date: '2026-04-29'
  author: spec-kitty.tasks
  note: Initial WP generated
authoritative_surface: docs/how-to/
execution_mode: planning_artifact
owned_files:
- docs/how-to/setup-governance.md
- docs/how-to/synthesize-doctrine.md
- docs/how-to/run-governed-mission.md
- docs/how-to/manage-glossary.md
tags: []
---

# WP04 — How-To: Governance, Synthesis, Missions, Glossary

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load the agent profile assigned to this work package:

```
/ad-hoc-profile-load curator-carla
```

This loads domain knowledge, tool preferences, and behavioral guidelines for documentation writing. Do not proceed until the profile confirms it has loaded.

## Objective

Update `setup-governance.md` and write three new how-to pages covering synthesis, governed missions, and the Charter glossary integration. These are P0 how-to guides covering the core Charter operator workflow.

This WP can run in parallel with WP02, WP03, WP05–WP08 after WP01 completes.

## Branch Strategy

- **Planning base branch**: `docs/charter-end-user-docs-828`
- **Merge target**: `main`
- **Execution workspace**: allocated by `lanes.json` at `spec-kitty agent action implement WP04 --agent <name>`; do not guess the worktree path

## Context

### How-to Page Format

Each how-to page is task-oriented. Structure:
1. Brief intro (one paragraph: what problem this solves, when to use it)
2. Context link to `docs/3x/charter-overview.md` for mental model
3. Steps (numbered, each with a command snippet and expected outcome)
4. "See also" block at the bottom

Each page must use DocFX frontmatter. Model: read `docs/how-to/setup-governance.md` for the current format.

### CLI Verification

Before writing any command snippet, verify it:
```bash
uv run spec-kitty charter --help
uv run spec-kitty charter interview --help
uv run spec-kitty charter generate --help
uv run spec-kitty charter synthesize --help     # doctrine synthesis (dry-run/apply)
uv run spec-kitty charter resynthesize --help   # partial resynthesis
uv run spec-kitty charter status --help
uv run spec-kitty charter lint --help
uv run spec-kitty charter bundle --help
uv run spec-kitty charter bundle validate --help
SPEC_KITTY_ENABLE_SAAS_SYNC=1 uv run spec-kitty charter sync --help  # syncs charter.md to YAML config files
uv run spec-kitty next --help
```

If a flag or subcommand is absent from `--help`, omit it from the page.

### Key Invariants (hold in all pages)

1. `charter.md` is the **only** human-edited governance file. State this where relevant.
2. Synthesis vs sync distinction: `charter synthesize` promotes doctrine into the DRG-backed context bundle; `charter resynthesize` performs partial regeneration; `charter sync` syncs `charter.md` to YAML config files — it does **not** push to SaaS. They are different operations.
3. No false claim that governed mission retrospective is deferred — verify against `mission-runtime.yaml` first.

## Subtask Guidance

### T013 — Update docs/how-to/setup-governance.md

**Action**: Update in place. Read the current file first. Identify sections that describe "Spec Kitty 2.x" prerequisites or that cover only interview/generate/sync without bundle validation or synthesis.

**Changes required**:
1. Remove or update the "Spec Kitty 2.x installed" prerequisite — replace with current requirement.
2. Add a new section covering the Charter synthesis flow after governance setup: `charter lint` -> `charter synthesize` -> `charter bundle validate`. One-line description of each.
3. Add a note on the synthesis vs sync distinction: `charter synthesize` promotes doctrine; `charter sync` syncs `charter.md` to YAML config files (not SaaS push).
4. Add "See also" block at the bottom pointing to:
   - `synthesize-doctrine.md`
   - `docs/3x/charter-overview.md`

Do not rewrite sections that are still accurate. Minimize diff.

### T014 — Write docs/how-to/synthesize-doctrine.md

**File**: `docs/how-to/synthesize-doctrine.md`  
**Title**: "How to Synthesize and Maintain Doctrine"

**Scope** (from data-model.md): dry-run, apply, status, lint, provenance, staging, recovery, what to do when the bundle is stale.

**Structure**:
1. Context link: "For background on the synthesis model, see [How Charter Works](../3x/charter-overview.md)."
2. **Check doctrine status** — `charter status` (what the output means, how to read it)
3. **Lint your charter file** — `charter lint` (what it checks, how to read errors)
4. **Synthesize doctrine (dry-run first)** — `charter synthesize --dry-run` (verify this flag exists with `--help`); explain what dry-run shows; **note**: `charter resynthesize` is available for partial regeneration — verify with `--help` and document if present
5. **Apply synthesis** — `charter synthesize` (apply mode); what changes on disk
6. **Validate the bundle** — `charter bundle validate`; what the bundle is and why you need a valid one
7. **Check provenance** — how to verify what synthesized the current doctrine (if `charter status` shows provenance info, describe it)
8. **Staging** — if `charter status` reports a staging state or pending synthesis, describe what it means and how to proceed
9. **Recovery: stale or corrupted bundle** — symptoms (e.g., `charter status` reports drift), fix steps

**CLI command list to verify before writing**:
```bash
uv run spec-kitty charter synthesize --help    # does --dry-run exist?
uv run spec-kitty charter resynthesize --help  # partial resynthesis
uv run spec-kitty charter status --help
uv run spec-kitty charter lint --help
uv run spec-kitty charter bundle --help
uv run spec-kitty charter bundle validate --help
```

**Cross-links at bottom ("See also")**:
- `docs/3x/charter-overview.md`
- `docs/3x/governance-files.md`
- `docs/reference/charter-commands.md`
- `docs/how-to/troubleshoot-charter.md`

### T015 — Write docs/how-to/run-governed-mission.md

**File**: `docs/how-to/run-governed-mission.md`  
**Title**: "How to Run a Governed Mission"

**Scope** (from data-model.md): `spec-kitty next --agent <agent>`, composed step contract, prompt resolution, how Charter context is injected, blocked decisions, how to read `next --json` output.

**Structure**:
1. Context link: "For background on governed profile invocation, see [How Charter Works](../3x/charter-overview.md)."
2. **Before you begin** — prerequisites: governance set up, doctrine synthesized, bundle current.
3. **Run a governed mission action** — `spec-kitty next --agent <agent>` with example. Explain that Charter context is injected automatically when the bundle is current.
4. **Read the output** — `spec-kitty next --json` output structure (verify this flag exists with `--help`).
5. **Composed steps** — briefly describe what composed steps are; how to see which step is next.
6. **Prompt resolution** — how `spec-kitty next` resolves which prompt to run for the current step (mission-runtime.yaml drives this; verify the resolution logic from `spec-kitty next --help` or `--json` output). Describe what it means when a prompt cannot be resolved.
7. **Blocked decisions** — what happens when a mission action is blocked by an open decision; how to resolve it (`spec-kitty agent decision resolve`).

**CLI to verify**:
```bash
uv run spec-kitty next --help              # --json flag? --agent flag?
uv run spec-kitty agent decision --help
uv run spec-kitty agent decision resolve --help
```

**Cross-links**:
- `docs/3x/charter-overview.md`
- `docs/explanation/governed-profile-invocation.md`
- `docs/reference/charter-commands.md`
- `docs/how-to/synthesize-doctrine.md`

### T016 — Update docs/how-to/manage-glossary.md

**Action**: Update in place. Read the current file. The current content predates Charter glossary runtime integration (FR-011).

**Changes required** — cover all four FR-011 relationships:

1. **Glossary as runtime doctrine** — explain that Charter exposes the project glossary as part of the doctrine surface so that agents receive consistent terminology at invocation time. Step-by-step: add a glossary term, run `charter synthesize` to propagate it, verify it appears in the bundle.

2. **Glossary and the DRG** — explain the DRG (Directive Relationship Graph) relationship: how glossary terms become reachable nodes or edge labels in the DRG, enabling consistent use of terms across directives and context injection.

3. **Glossary as project-local doctrine** — the glossary is project-local human policy (lives in the authoritative `charter.md` surface), not generated state. Adding or changing a term requires editing `charter.md` and re-running synthesis.

4. **Glossary and retrospective proposals** — the retrospective synthesizer can emit glossary-change proposals. Explain how these proposals appear in the default dry-run output from `agent retrospect synthesize --mission <mission>`, and how accepting them with `--apply` updates the project glossary via `charter.md`.

5. Add "See also" block:
   - `docs/how-to/synthesize-doctrine.md`
   - `docs/3x/charter-overview.md`
   - `docs/explanation/retrospective-learning-loop.md`

Do not remove existing glossary management content that is still accurate.

### T017 — Smoke-test synthesis/mission snippets; add cross-links to 3x hub

Smoke-test the key command snippets from T013, T014, and T015:

```bash
TMPDIR=$(mktemp -d)
cd "$TMPDIR"
git init -q
# T013 smoke: run the setup-governance.md setup flow
# Run: charter interview, charter generate
# Run: charter lint, charter synthesize, charter bundle validate (from T014)
# Run: spec-kitty next (with a test agent if available, from T015)
cd -
rm -rf "$TMPDIR"
```

**T013 (setup-governance.md) must also be smoke-tested**: verify the current flow described in `setup-governance.md` works from a fresh temp repo. This confirms the page teaches an executable workflow, not just theory.

If a step is interactive or requires a real project context, document that in the page ("This step requires an existing project with a populated `charter.md`").

After smoke-testing, verify every new and updated page has a cross-link to `docs/3x/` hub. The charter-overview link must appear in the opening context paragraph.

Also verify:
```bash
grep 'TODO' docs/how-to/synthesize-doctrine.md docs/how-to/run-governed-mission.md \
  docs/how-to/setup-governance.md
```
Zero results required.

## Definition of Done

- [ ] `setup-governance.md` updated: 2.x prereq removed, synthesis/bundle steps added, synthesis vs sync distinction noted, "See also" block present
- [ ] `synthesize-doctrine.md` written: status, lint, dry-run (`charter synthesize --dry-run`), apply (`charter synthesize`), resynthesize, bundle, staging, provenance, recovery
- [ ] `run-governed-mission.md` written: next command, composed steps, prompt resolution, Charter context injection, blocked decisions
- [ ] `manage-glossary.md` updated: all 4 FR-011 relationships covered (runtime, DRG, project-local, retrospective-proposal)
- [ ] All command snippets verified against `--help` (no assumed flags; `charter context` not used as synthesis verb)
- [ ] Smoke-test completed against temp project including `setup-governance.md` flow (no source-repo pollution)
- [ ] All pages have cross-link to `docs/3x/charter-overview.md`
- [ ] All pages appear in `docs/how-to/toc.yml` (added by WP01)
- [ ] `grep -r 'TODO' docs/how-to/` → zero results (in new/changed pages)
- [ ] `uv run pytest tests/docs/ -q` passes
