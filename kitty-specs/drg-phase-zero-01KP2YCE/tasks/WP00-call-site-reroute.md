---
work_package_id: WP00
title: Call-Site Audit and Oracle Confirmation
dependencies: []
requirement_refs:
- FR-001
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
history:
- date: '2026-04-13'
  author: claude
  action: created
  note: Initial WP generation from /spec-kitty.tasks
- date: '2026-04-13'
  author: claude
  action: revised
  note: Reframed from reroute to audit after review identified behavior-change risk
authoritative_surface: kitty-specs/drg-phase-zero-01KP2YCE/
execution_mode: planning_artifact
owned_files:
- kitty-specs/drg-phase-zero-01KP2YCE/research/call-site-delta.md
tags: []
---

# WP00: Call-Site Audit and Oracle Confirmation

## Objective

Document the behavioral delta between the canonical `src/charter/context.py` and the legacy `src/specify_cli/charter/context.py`, confirm the canonical path is the correct parity oracle for WP04, and document what Phase 1's reroute will change in live prompt behavior.

**No production code is changed in this WP.** The two implementations have materially different behavior (canonical has depth semantics, action doctrine injection, and guideline rendering; legacy does not). Rerouting callers would change live prompt output and is Phase 1 scope.

## Context

Three callers exist:
- `src/specify_cli/next/prompt_builder.py:13` -- imports from `specify_cli.charter.context` (legacy)
- `src/specify_cli/cli/commands/agent/workflow.py:20` -- imports from `specify_cli.charter.context` (legacy)
- `src/specify_cli/cli/commands/charter.py:13` -- imports from `charter.context` (canonical)

The canonical implementation (`src/charter/context.py`) has:
- `depth` parameter (1=compact, 2=bootstrap+action doctrine, 3=extended+styleguides)
- Action doctrine injection via `_append_action_doctrine_lines()` (directives, tactics, guidelines)
- Action-filtered reference docs via `_filter_references_for_action()`
- `CharterContextResult.depth` field

The legacy implementation (`src/specify_cli/charter/context.py`) has:
- No `depth` parameter
- Simple binary: first_load -> bootstrap (policy summary + references), else -> compact governance
- No action doctrine injection, no guideline rendering

## Branch Strategy

- **Planning/base branch**: `main`
- **Merge target**: `main`
- Execution worktrees allocated per computed lane from `lanes.json`.

## Detailed Guidance

### T001: Document behavioral delta

**Purpose**: Produce a structured comparison of what each implementation renders for each (action, depth) combination.

**Steps**:
1. Create `kitty-specs/drg-phase-zero-01KP2YCE/research/call-site-delta.md`
2. For each bootstrap action (`specify`, `plan`, `implement`, `review`):
   a. Call the canonical `charter.context.build_charter_context(repo_root, action=action, depth=d)` for depths 1, 2, 3
   b. Call the legacy `specify_cli.charter.context.build_charter_context(repo_root, action=action)` (no depth parameter)
   c. Document:
      - Which artifact IDs (directives, tactics) appear in each output
      - Which sections are present/absent (action doctrine, guidelines, filtered references)
      - The `mode` and `references_count` fields
3. Organize as a table: rows = (action, depth), columns = canonical artifacts, legacy artifacts, delta

**Files**: `kitty-specs/drg-phase-zero-01KP2YCE/research/call-site-delta.md`

**Validation**:
- [ ] All 4 actions x 3 depths documented for canonical
- [ ] All 4 actions documented for legacy (single depth)
- [ ] Delta clearly shows what canonical adds over legacy

### T002: Verify canonical path as correct oracle

**Purpose**: Confirm the canonical implementation resolves the correct set of governance artifacts for each (action, depth), so the invariant test (WP04) compares against a trustworthy baseline.

**Steps**:
1. For each action, verify the canonical path's resolved directives match the action index file:
   - `specify`: should resolve DIRECTIVE_010, DIRECTIVE_003 + tactic `requirements-validation-workflow`
   - `plan`: should resolve DIRECTIVE_003, DIRECTIVE_010 + tactics `requirements-validation-workflow`, `adr-drafting-workflow`
   - `implement`: should resolve 6 directives + 6 tactics + 1 toolguide (per index)
   - `review`: should resolve 2 directives + 3 tactics (per index)
2. Verify project-directive intersection works correctly (canonical intersects with governance.yaml selections)
3. Document any discrepancies between action index content and canonical path resolution
4. If discrepancies exist, file them as issues and document whether they affect oracle suitability

**Files**: Extend `call-site-delta.md` with oracle verification section

**Validation**:
- [ ] Each action's resolved artifacts match its action index
- [ ] Any discrepancies documented with issue references
- [ ] Explicit statement: "canonical path is confirmed as correct oracle" or "canonical path has issues that must be resolved first"

### T003: Document Phase 1 reroute scope

**Purpose**: Pre-document what happens when Phase 1 reroutes the two legacy callers, so Phase 1 can make the change with full awareness.

**Steps**:
1. In `call-site-delta.md`, add a "Phase 1 Reroute Plan" section
2. For each caller:
   - What it renders today (legacy path output)
   - What it will render after reroute (canonical path output at the depth it will use)
   - Net change in prompt behavior agents experience
3. Flag any reroute risks: will agents get materially different prompts? Will any existing workflows break?

**Files**: Extend `call-site-delta.md`

**Validation**:
- [ ] Both callers' reroute impact documented
- [ ] Net prompt behavior change described
- [ ] Risks flagged if any

## Definition of Done

1. `call-site-delta.md` exists with complete behavioral delta
2. Canonical path confirmed as correct oracle (or issues filed if not)
3. Phase 1 reroute scope documented with expected behavior changes
4. No production code modified

## Risks

- **Canonical path has a bug**: If the canonical path resolves wrong artifacts, the invariant test will use a faulty oracle. This WP must verify correctness, not just document.
- **Delta is too large for Phase 1**: If the behavioral delta is so large that Phase 1 reroute is risky, this WP should flag it as a concern for Phase 1 planning.

## Reviewer Guidance

- Verify the delta covers all actions and depths, not just a sample
- Verify the oracle verification actually checks against action index files, not just against itself
- Verify the Phase 1 reroute documentation is actionable (not just "it will change")
