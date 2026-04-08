---
work_package_id: WP01
title: Selector Audit and Canonical Map
dependencies: []
requirement_refs:
- FR-001
- FR-022
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
history:
- actor: system
  at: '2026-04-08T12:45:50Z'
  event: created
authoritative_surface: kitty-specs/077-mission-terminology-cleanup/research/
execution_mode: planning_artifact
mission_slug: 077-mission-terminology-cleanup
owned_files:
- kitty-specs/077-mission-terminology-cleanup/research/selector-audit.md
priority: P0
tags: []
---

# WP01 — Selector Audit and Canonical Map

## Objective

Produce a complete, verified inventory of every CLI selector site in `src/specify_cli/cli/commands/**` that touches mission identity. Classify each site as one of:

- **tracked-mission** (the parameter resolves to a `kitty-specs/<slug>/` mission slug)
- **inverse-drift** (the parameter resolves to a mission type / blueprint, but the literal flag is `--mission`)
- **runtime-session** (the parameter resolves to a `mission_run_id`; legitimate use of `--mission-run`)
- **other** (mission_type selector that's already canonical, runtime selector that's already canonical, or unrelated)

The output is the canonical input to WP02-WP05. Without this audit, downstream WPs will miss sites or misclassify them.

## Context

This is the first WP in the mission. It is **planning work**, not code change. It produces one research artifact:

- `kitty-specs/077-mission-terminology-cleanup/research/selector-audit.md`

The audit enables every other Scope A WP to operate against a known, complete map. The verified-known sites at HEAD `35d43a25` (from spec §8.1) are the floor; this audit should find every additional site that exists.

### Verified-known sites (floor)

**Tracked-mission selector drift** (from spec §8.1.1):
- `src/specify_cli/cli/commands/next_cmd.py:33` — `typer.Option("--mission", "--mission-run", "--feature", help="Mission slug")`
- `src/specify_cli/cli/commands/next_cmd.py:48` — example help text uses `--mission-run`
- `src/specify_cli/cli/commands/agent/tasks.py` — 9 sites at lines 842, 1389, 1572, 1655, 1726, 1945, 2205, 2295, 2659
- `src/specify_cli/cli/commands/mission.py:172-194` — `mission current` with the dual-flag bug

**Inverse drift** (from spec §8.1.2):
- `src/specify_cli/cli/commands/agent/mission.py:488` — `agent mission create` with `--mission` meaning mission type
- `src/specify_cli/cli/commands/charter.py:67` — `charter interview` with `--mission` meaning mission type
- `src/specify_cli/cli/commands/lifecycle.py:27` — `lifecycle.specify` with `--mission` meaning mission type

The audit must confirm these and find any additional sites.

## Branch Strategy

- **Planning base branch**: `main`
- **Merge target**: `main`
- **Execution worktree**: created by `spec-kitty implement WP01` from the lane assigned by `lanes.json`. The lane is computed at `finalize-tasks` time. Do not guess the worktree path; use whatever `spec-kitty implement WP01` creates.
- **Run from**: the lane workspace returned by `spec-kitty implement WP01`.

## Detailed Subtasks

### T001 — Inventory tracked-mission selector sites

**Purpose**: Find every `typer.Option` declaration in `src/specify_cli/cli/commands/**/*.py` whose parameter resolves to a tracked-mission slug.

**Steps**:
1. Run a content grep for typer Option declarations that mention `--mission`, `--feature`, or `--mission-run`:
   ```bash
   grep -rn 'typer\.Option.*"--mission' src/specify_cli/cli/commands/
   grep -rn 'typer\.Option.*"--feature' src/specify_cli/cli/commands/
   grep -rn 'typer\.Option.*"--mission-run' src/specify_cli/cli/commands/
   ```
2. For each match, read the surrounding context:
   - The parameter name (e.g. `feature`, `mission`, `mission_run_id`)
   - The `help=` string
   - The function body that uses the value
3. Classify each site as **tracked-mission** if any of:
   - Parameter is passed to `require_explicit_feature`
   - Parameter is used to construct a path under `kitty-specs/<slug>/`
   - `help=` says "Mission slug" or similar
4. Record each tracked-mission site as a row in the audit document.

**Output row format** (markdown table in `selector-audit.md`):

```markdown
| File | Line | Function | Current declaration | Help string | Classification | Target alias list |
|---|---|---|---|---|---|---|
| src/specify_cli/cli/commands/next_cmd.py | 33 | next_cmd | typer.Option("--mission", "--mission-run", "--feature", ...) | "Mission slug" | tracked-mission | `--mission` (canonical) + `--feature` (hidden) |
```

### T002 — Inventory inverse-drift sites [P]

**Purpose**: Find every `typer.Option` declaration whose literal flag is `--mission` but whose parameter semantically means "mission type / blueprint".

**Steps**:
1. From the T001 grep results, isolate sites whose `help=` string contains "mission type", "mission key", or "blueprint".
2. Read each site's function body to confirm: does the value get used as a mission type (e.g. passed to `create_mission_core(mission=...)` where `mission` is a type key) or as a tracked-mission slug?
3. Sites where the value is used as a mission type but the flag is `--mission` are **inverse-drift**.
4. Record each as a row in the audit, with the same row format as T001 but classification = `inverse-drift` and target alias list = `--mission-type` (canonical) + `--mission` (hidden).

**Verified inverse-drift sites to confirm**:
- `agent/mission.py:488` (default value: `None`)
- `charter.py:67` (default value: `"software-dev"` — important: the default must move to `--mission-type` after refactor)
- `lifecycle.py:27` (default value: `None`)

The audit may find additional sites — record them.

### T003 — Cross-reference helper consumers [P]

**Purpose**: Confirm which sites currently feed `require_explicit_feature` (the existing presence helper at `src/specify_cli/core/paths.py:273`). This map ensures the new `resolve_selector` helper is wired upstream of `require_explicit_feature` consistently.

**Steps**:
1. Grep for `require_explicit_feature` in `src/specify_cli/`:
   ```bash
   grep -rn 'require_explicit_feature' src/specify_cli/
   ```
2. For each call site, identify which CLI command function it's inside.
3. Cross-reference with the T001 inventory: every tracked-mission site found in T001 should already call `require_explicit_feature` (or similar). If a site doesn't, flag it — that may be a separate bug to fix in WP04.
4. Add a "Calls require_explicit_feature?" column to the audit table.

### T004 — Produce canonical map document

**Purpose**: Write the audit artifact.

**Steps**:
1. Create `kitty-specs/077-mission-terminology-cleanup/research/selector-audit.md` with:
   - **Header**: mission slug, audit date, HEAD commit at audit time
   - **Summary table**: site count by classification
   - **Tracked-mission sites table** (one row per site, columns from T001)
   - **Inverse-drift sites table** (one row per site, columns from T002)
   - **Runtime-session sites table** (legitimate `--mission-run` uses; left untouched by this mission)
   - **Helper consumer cross-reference table** (from T003)
   - **Notes section** with any ambiguous classifications and the resolution
2. The document is the single source of truth for WP02 (which sites need the helper), WP03 (which file mission_current is in), WP04 (the bulk refactor list), and WP05 (the inverse-drift list).

## Files Touched

| File | Action |
|---|---|
| `kitty-specs/077-mission-terminology-cleanup/research/selector-audit.md` | CREATE |

No source code is modified by this WP. No tests are added. No imports change.

## Definition of Done

- [ ] `selector-audit.md` exists with all 4 tables (tracked-mission, inverse-drift, runtime-session, helper consumer cross-reference)
- [ ] Every verified-known site from spec §8.1 appears in the appropriate table
- [ ] Any additional sites discovered during the audit are also recorded
- [ ] The "Notes" section explains every ambiguous classification
- [ ] A reviewer can read the audit and identify the target alias list for any CLI command in scope
- [ ] The audit document references HEAD commit (`git rev-parse HEAD` at audit time)

## Risks and Reviewer Guidance

**Risks**:
- A site could be misclassified by reading help text alone. Always confirm with the function body.
- A site could legitimately accept `--mission-run` for runtime/session use; do not flag those as drift. Look for `mission_run_id` in the function body to distinguish.
- The audit might find a tracked-mission site that doesn't currently call `require_explicit_feature`. Flag it but do not fix it here — note it for WP04 to address.

**Reviewer checklist**:
- [ ] Are all 14+ verified-known sites present in the audit?
- [ ] Does every classification have a paragraph in Notes explaining the rationale?
- [ ] Does the audit reference the HEAD commit it was taken at?
- [ ] Are inverse-drift sites correctly distinguished from tracked-mission sites?

## Implementation Command

```bash
spec-kitty implement WP01
```

This WP has no dependencies. Start it as soon as the tasks.md is committed.

## References

- Spec §8.1 — Verified drift sites
- Spec §3 — Canonical model
- Plan §"Phase 0" — research method
- `contracts/selector_resolver.md` — helper interface this audit informs

## Activity Log

- 2026-04-08T13:13:58Z – unknown – Starting WP01 audit (planning artifact, runs in main checkout)
