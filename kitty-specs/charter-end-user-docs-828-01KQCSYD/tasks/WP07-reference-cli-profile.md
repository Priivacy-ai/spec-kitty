---
work_package_id: WP07
title: Reference — CLI and Profile Invocation
dependencies:
- WP01
requirement_refs:
- FR-007
- FR-012
planning_base_branch: docs/charter-end-user-docs-828
merge_target_branch: docs/charter-end-user-docs-828
branch_strategy: Planning artifacts for this feature were generated on docs/charter-end-user-docs-828. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into docs/charter-end-user-docs-828 unless the human explicitly redirects the landing branch.
subtasks:
- T026
- T027
- T028
- T029
- T030
agent: curator-carla
history:
- date: '2026-04-29'
  author: spec-kitty.tasks
  note: Initial WP generated
authoritative_surface: docs/reference/
execution_mode: planning_artifact
owned_files:
- docs/reference/charter-commands.md
- docs/reference/cli-commands.md
- docs/reference/profile-invocation.md
tags: []
---

# WP07 — Reference: CLI and Profile Invocation

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load the agent profile assigned to this work package:

```
/ad-hoc-profile-load curator-carla
```

This loads domain knowledge, tool preferences, and behavioral guidelines for documentation writing. Do not proceed until the profile confirms it has loaded.

## Objective

Write `charter-commands.md` and `profile-invocation.md`; update `cli-commands.md`. All CLI reference content must be verified against live `--help` output — never assume flags or subcommands exist.

This WP can run in parallel with WP02–WP06, WP08 after WP01 completes.

## Branch Strategy

- **Planning base branch**: `docs/charter-end-user-docs-828`
- **Merge target**: `main`
- **Execution workspace**: allocated by `lanes.json` at `spec-kitty agent action implement WP07 --agent <name>`; do not guess the worktree path

## Context

### CRITICAL: CLI Verification Rule

**All flags and subcommands must be verified against live `--help` output before writing.** Use `uv run spec-kitty`, not the ambient PATH binary.

**Do not guess. Do not assume. Do not invent.** If a flag is not in `--help`, do not include it in the reference. If a subcommand returns "No such command", omit its section and note "not yet available."

Reference pages describe only what exists, not what might exist or what used to exist.

### Commands to Run (T026)

```bash
uv run spec-kitty charter --help
uv run spec-kitty charter interview --help
uv run spec-kitty charter generate --help
uv run spec-kitty charter synthesize --help      # doctrine synthesis (the primary synthesis verb)
uv run spec-kitty charter resynthesize --help    # partial resynthesis
uv run spec-kitty charter status --help
SPEC_KITTY_ENABLE_SAAS_SYNC=1 uv run spec-kitty charter sync --help  # syncs charter.md to YAML config files
uv run spec-kitty charter lint --help
uv run spec-kitty charter bundle --help          # verify this exists
uv run spec-kitty charter bundle validate --help
uv run spec-kitty next --help
uv run spec-kitty profiles --help
uv run spec-kitty profiles list --help
uv run spec-kitty ask --help
uv run spec-kitty advise --help
uv run spec-kitty do --help
uv run spec-kitty profile-invocation --help
uv run spec-kitty profile-invocation complete --help
uv run spec-kitty mission --help
uv run spec-kitty glossary --help
uv run spec-kitty retrospect --help
uv run spec-kitty retrospect summary --help
uv run spec-kitty agent retrospect synthesize --help
uv run spec-kitty agent decision --help
uv run spec-kitty agent decision open --help
uv run spec-kitty agent decision resolve --help
```

Capture all output. Build the reference from this output, not from reading source code.

### DocFX Format for Reference Pages

Reference pages use DocFX frontmatter. Model: read existing `docs/reference/cli-commands.md` for format.

## Subtask Guidance

### T026 — Run all Charter subcommand --help and capture output

**Action**: Execute all commands listed in the Context section. For each:
1. Record whether the command exists (or returns "No such command")
2. Copy the exact flags and descriptions from `--help` output
3. Note any unexpected flags or behavior

Capture this into notes before writing T027 — the reference is built entirely from this output.

Key questions to answer:
- Does `charter bundle validate` exist? (Plan assumes yes — verify)
- Does `charter synthesize` have a `--dry-run` flag?
- Does `charter resynthesize` exist? What flags does it accept?
- Does `agent retrospect synthesize` require `--mission <mission>`, default to dry-run, and mutate only with `--apply`?
- What flags does `spec-kitty next` accept?
- What is the exact behavior of `charter sync`? (It syncs charter.md to YAML config files — confirm with `--help`)
- Do `profiles list`, `ask`, `advise`, `do`, `profile-invocation complete`, `mission`, and `glossary` exist? Capture their exact usage and flags.

### T027 — Write docs/reference/charter-commands.md

**File**: `docs/reference/charter-commands.md`  
**Title**: "Charter CLI Reference"

**Structure**: One section per verified subcommand.

For each subcommand, include:
- **Description**: one sentence (from `--help` description)
- **Usage**: `uv run spec-kitty charter <subcommand> [OPTIONS]`
- **Options table**: flag | description | default (from `--help`)
- **Example**: one realistic example with expected output description

**Subcommands to cover** (only those verified in T026):
- `charter interview`
- `charter generate`
- `charter synthesize` (the primary doctrine synthesis verb — includes `--dry-run` if verified)
- `charter resynthesize` (partial resynthesis — if verified to exist)
- `charter status`
- `charter sync` (syncs `charter.md` to YAML config files — document what it actually does per `--help`)
- `charter lint`
- `charter bundle validate` (if it exists)

For each section, include exactly what `--help` says — do not embellish or paraphrase flag descriptions.

**Options table format**:
```markdown
| Flag | Description | Default |
|---|---|---|
| `--flag-name` | Description from --help | `default-value` |
```

**At the top of the page**:
```markdown
> **Note**: All Charter commands use `uv run spec-kitty charter`, not the ambient `spec-kitty`
> binary. Flags in this reference are verified against spec-kitty 3.x.
```

### T028 — Update docs/reference/cli-commands.md

**Action**: Update in place. Read the current file first.

**Add a Charter-era section** at the appropriate location (after existing content or before the end):

```markdown
## Charter Commands (3.x)

Spec Kitty 3.x adds the Charter governance layer. Charter commands use the `charter` subcommand group.

- **[Charter CLI Reference](charter-commands.md)** — Full reference for `charter interview`, `generate`, `synthesize`, `resynthesize`, `status`, `sync`, `lint`, and `bundle validate`.
- **[Profile Invocation Reference](profile-invocation.md)** — Reference for `ask`/`advise`/`do` flags and the invocation trail.
- **`spec-kitty next`** — Run a governed mission action. Flags: [list from --help output].
- **`spec-kitty profiles list`** — List available agent profiles.
- **`spec-kitty mission ...`** — Mission discovery and runtime commands.
- **`spec-kitty glossary ...`** — Glossary list/show/conflict commands.
- **`spec-kitty retrospect summary`** — View retrospective summary.
- **`spec-kitty agent retrospect synthesize --mission <mission>` / `--mission <mission> --apply`** — Preview or apply synthesis proposals.
```

Do not duplicate flag tables — cross-link to `charter-commands.md` instead.

Verify the `next` and `retrospect` commands appear in the Charter-era section with accurate flags from T026 output.

### T029 — Write docs/reference/profile-invocation.md

**File**: `docs/reference/profile-invocation.md`  
**Title**: "Profile Invocation Reference"

**Scope** (from data-model.md): `ask`/`advise`/`do` flag semantics; `profile-invocation complete` syntax; invocation trail fields; lifecycle states; example JSON output.

**Structure**:
1. Brief intro: "Profile invocation is the mechanism by which a governed agent persona is called with Charter context. For an explanation of the model, see [Understanding Governed Profile Invocation](../explanation/governed-profile-invocation.md)."
2. **Invocation modes** — reference table:

| Mode | CLI | Behavior |
|---|---|---|
| Ask | `spec-kitty ask <profile> <request>` | Invoke a named profile directly for a query/advisory flow |
| Advise | `spec-kitty advise [--profile <profile>] <request>` | Open an advisory invocation record for a routed request |
| Do | `spec-kitty do <request>` | Route a request to the best-matching profile for action |

Verify command syntax against `spec-kitty ask --help`, `spec-kitty advise --help`, `spec-kitty do --help`, and `spec-kitty profile-invocation complete --help` before writing.

3. **`profile-invocation complete` syntax** — the signal that closes the trail. Show the exact syntax from the CLI (verify with `--help` or from `docs/trail-model.md` if it exists).
4. **Invocation trail fields** — table of trail record fields (check `docs/trail-model.md` if present; otherwise derive from available documentation):

| Field | Type | Description |
|---|---|---|
| `profile` | string | Agent profile identifier |
| `action` | string | Mission action being performed |
| `governance_context` | object | Charter context snapshot at invocation |
| `started_at` | ISO timestamp | When the invocation opened |
| `completed_at` | ISO timestamp | When `profile-invocation complete` was called |

5. **Lifecycle states** — opened → in_progress → complete (or failed). Describe each transition.
6. **Example JSON output** — show a representative trail record (format it clearly; note it is illustrative).

**Cross-links**:
- `docs/explanation/governed-profile-invocation.md`
- `docs/how-to/run-governed-mission.md`
- `docs/3x/charter-overview.md`

### T030 — Verify docs/reference/toc.yml has all reference page entries

The three reference pages should already appear in `docs/reference/toc.yml` (added by WP01). Verify:
```bash
grep -E 'charter-commands|cli-commands|profile-invocation' docs/reference/toc.yml
```
All three hrefs must appear. Do not modify the toc in this WP.

Also verify:
```bash
grep -r 'TODO' docs/reference/charter-commands.md docs/reference/profile-invocation.md
```
Zero results required.

## Definition of Done

- [ ] T026: All Charter `--help` output captured and reviewed before writing; includes `charter synthesize` and `charter resynthesize`
- [ ] `charter-commands.md` written with one section per verified subcommand; includes `synthesize` and `resynthesize` sections; all flags match live `--help`
- [ ] `cli-commands.md` updated with Charter-era section and cross-links (no duplicate flag tables); uses `retrospect summary` and `agent retrospect synthesize` — not `retro` variants
- [ ] `profile-invocation.md` written: ask/advise/do modes, profile-invocation complete, trail fields, lifecycle states, example JSON
- [ ] No flags or subcommands invented — only what `--help` confirms
- [ ] All pages use DocFX frontmatter
- [ ] All three pages appear in `docs/reference/toc.yml`
- [ ] `grep -r 'TODO' docs/reference/charter-commands.md docs/reference/profile-invocation.md` → zero results
- [ ] `uv run pytest tests/docs/ -q` passes
