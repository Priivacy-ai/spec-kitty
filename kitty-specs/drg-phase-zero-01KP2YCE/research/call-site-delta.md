# Call-Site Audit and Oracle Confirmation

**WP00 research artifact for mission drg-phase-zero-01KP2YCE**
**Date: 2026-04-13**

---

## T001: Behavioral Delta Between Canonical and Legacy Implementations

### Overview

| Property | Canonical (`src/charter/context.py`) | Legacy (`src/specify_cli/charter/context.py`) |
|---|---|---|
| Module | `charter.context` | `specify_cli.charter.context` |
| `depth` parameter | Yes (1, 2, 3) | No |
| `CharterContextResult.depth` field | Yes | No |
| Action doctrine injection | Yes (`_append_action_doctrine_lines`) | No |
| Action-filtered references | Yes (`_filter_references_for_action`) | No |
| Styleguide/toolguide rendering | Yes (at depth 3) | No |
| Guidelines rendering | Yes (at depth >= 2) | No |
| `_load_references` fields | `id`, `title`, `local_path`, `kind`, `summary` | `id`, `title`, `local_path` only |
| Resolver module | `charter.resolver` (richer `GovernanceResolution` with tactics, styleguides, toolguides, procedures, profile_id, role) | `specify_cli.charter.resolver` (simpler `GovernanceResolution` with paradigms, directives, tools only) |
| Atomic write import | `kernel.atomic.atomic_write` | `specify_cli.core.atomic.atomic_write` |

### Detailed Comparison: All 4 Actions x 3 Depths

#### Legend

- **Bootstrap mode**: Full charter context with Policy Summary + references
- **Compact mode**: Short governance summary (template set, paradigms, directives, tools)
- **Action doctrine**: Directives + tactics resolved from `index.yaml` for that action, intersected with project governance.yaml selections
- **Guidelines**: Action-specific prose from `guidelines.md`
- **Extended**: Styleguides + toolguides (depth 3 only)

---

### Action: `specify`

**Action index** (`src/doctrine/missions/software-dev/actions/specify/index.yaml`):
- Directives: `010-specification-fidelity-requirement`, `003-decision-documentation-requirement`
- Tactics: `requirements-validation-workflow`
- Styleguides: (none)
- Toolguides: (none)

| Depth | Canonical Output | Legacy Output | Delta |
|-------|-----------------|---------------|-------|
| 1 (compact) | `mode=compact`. Compact governance only: template set, paradigms, directives, tools. No action doctrine, no references, no guidelines. `depth=1` field present. | (same behavior on subsequent loads) `mode=compact`. Compact governance. No `depth` field. | **Structural**: canonical has `depth` field. **Content**: identical when both render compact. |
| 2 (bootstrap) | `mode=bootstrap`. Policy Summary (up to 8 bullets) + **Action Doctrine (specify)**: Directives section (DIRECTIVE_010, DIRECTIVE_003 intersected with project selections), Tactics section (requirements-validation-workflow) + **Guidelines** (specify/guidelines.md content) + **Reference Docs** (action-filtered: only refs matching action=specify or global refs). `depth=2`. | `mode=bootstrap` (first load only). Policy Summary (up to 8 bullets) + **Reference Docs** (ALL references, no action filtering, no `kind`/`summary` fields extracted). No action doctrine. No guidelines. No `depth` field. | **LARGE DELTA**: Canonical adds action doctrine (2 directives, 1 tactic), guidelines prose, and action-scoped reference filtering. Legacy shows raw unfiltered references. |
| 3 (extended) | Same as depth 2 plus **Extended** section with styleguides + toolguides. For specify: both are empty, so no visible difference from depth 2. `depth=3`. | N/A (no depth parameter) | Same as depth 2 delta (specify has no styleguides/toolguides). |

### Action: `plan`

**Action index** (`src/doctrine/missions/software-dev/actions/plan/index.yaml`):
- Directives: `003-decision-documentation-requirement`, `010-specification-fidelity-requirement`
- Tactics: `requirements-validation-workflow`, `adr-drafting-workflow`
- Styleguides: (none)
- Toolguides: (none)

| Depth | Canonical Output | Legacy Output | Delta |
|-------|-----------------|---------------|-------|
| 1 | Compact governance. `depth=1`. | Compact governance (subsequent loads). No `depth`. | Structural only. |
| 2 | Bootstrap + **Action Doctrine (plan)**: Directives (DIRECTIVE_003, DIRECTIVE_010), Tactics (requirements-validation-workflow, adr-drafting-workflow) + **Guidelines** (plan/guidelines.md) + action-filtered refs. `depth=2`. | Bootstrap: Policy Summary + unfiltered refs. No doctrine. No guidelines. | **LARGE DELTA**: +2 directives, +2 tactics, +guidelines, +action-filtered refs. |
| 3 | Same as depth 2 (plan has no styleguides/toolguides). `depth=3`. | N/A | Same as depth 2 delta. |

### Action: `implement`

**Action index** (`src/doctrine/missions/software-dev/actions/implement/index.yaml`):
- Directives: `024-locality-of-change`, `025-boy-scout-rule`, `028-search-tool-discipline`, `029-agent-commit-signing-policy`, `030-test-and-typecheck-quality-gate`, `034-test-first-development`
- Tactics: `acceptance-test-first`, `tdd-red-green-refactor`, `change-apply-smallest-viable-diff`, `autonomous-operation-protocol`, `quality-gate-verification`, `stopping-conditions`
- Styleguides: (none)
- Toolguides: `efficient-local-tooling`

| Depth | Canonical Output | Legacy Output | Delta |
|-------|-----------------|---------------|-------|
| 1 | Compact governance. `depth=1`. | Compact governance (subsequent loads). No `depth`. | Structural only. |
| 2 | Bootstrap + **Action Doctrine (implement)**: Directives (6 directives), Tactics (6 tactics) + **Guidelines** (implement/guidelines.md) + action-filtered refs. `depth=2`. | Bootstrap: Policy Summary + unfiltered refs. | **VERY LARGE DELTA**: +6 directives, +6 tactics, +guidelines. This is the richest action doctrine payload. |
| 3 | Same as depth 2 plus **Toolguides**: `efficient-local-tooling`. `depth=3`. | N/A | Same as depth 2 delta + toolguide. Depth 3 is the only level where implement differs from depth 2. |

### Action: `review`

**Action index** (`src/doctrine/missions/software-dev/actions/review/index.yaml`):
- Directives: `010-specification-fidelity-requirement`, `030-test-and-typecheck-quality-gate`
- Tactics: `review-intent-and-risk-first`, `quality-gate-verification`, `stopping-conditions`
- Styleguides: (none)
- Toolguides: (none)

| Depth | Canonical Output | Legacy Output | Delta |
|-------|-----------------|---------------|-------|
| 1 | Compact governance. `depth=1`. | Compact governance (subsequent loads). No `depth`. | Structural only. |
| 2 | Bootstrap + **Action Doctrine (review)**: Directives (DIRECTIVE_010, DIRECTIVE_030), Tactics (review-intent-and-risk-first, quality-gate-verification, stopping-conditions) + **Guidelines** (review/guidelines.md) + action-filtered refs. `depth=2`. | Bootstrap: Policy Summary + unfiltered refs. | **LARGE DELTA**: +2 directives, +3 tactics, +guidelines, +action-filtered refs. |
| 3 | Same as depth 2 (review has no styleguides/toolguides). `depth=3`. | N/A | Same as depth 2 delta. |

### Non-bootstrap Actions

For any action not in `{specify, plan, implement, review}`:

| | Canonical | Legacy | Delta |
|---|---|---|---|
| Behavior | Returns compact governance immediately. `depth` defaults to 1 (or explicit override). `first_load=False`. | Returns compact governance immediately. `first_load=False`. | Structural only (`depth` field). |

### Depth Resolution Logic

| Scenario | Canonical | Legacy |
|---|---|---|
| First load, no explicit depth | `depth=2` (bootstrap) | N/A (always bootstrap on first load) |
| Subsequent load, no explicit depth | `depth=1` (compact) | Always compact |
| Explicit `depth=1` on first load | Compact governance (overrides bootstrap) | N/A (no depth param) |
| Explicit `depth=3` on subsequent load | Full bootstrap + extended | N/A (no depth param) |

### `_load_references` Difference

Canonical extracts 5 fields per reference: `id`, `title`, `local_path`, `kind`, `summary`.
Legacy extracts 3 fields per reference: `id`, `title`, `local_path`.

The `kind` and `summary` fields are required by `_filter_references_for_action()` to implement action-scoped reference filtering (canonical-only feature).

---

## T002: Oracle Verification -- Canonical Path Correctness

### Methodology

The canonical path loads action indices via:
1. `MissionTemplateRepository.default()` to find the missions root
2. `load_action_index(missions_root, "software-dev", action)` to parse `index.yaml`
3. `_normalize_directive_id()` to convert raw slugs to `DIRECTIVE_NNN` format
4. Intersection with `governance.yaml` `selected_directives` to filter to project-relevant directives

### Verification: specify

| Source | Directives | Tactics |
|---|---|---|
| `actions/specify/index.yaml` | `010-specification-fidelity-requirement`, `003-decision-documentation-requirement` | `requirements-validation-workflow` |
| After `_normalize_directive_id()` | `DIRECTIVE_010`, `DIRECTIVE_003` | (unchanged) |
| Expected in WP prompt (T002) | DIRECTIVE_010, DIRECTIVE_003 | requirements-validation-workflow |

**Result**: MATCH. The canonical path correctly resolves specify's 2 directives + 1 tactic.

### Verification: plan

| Source | Directives | Tactics |
|---|---|---|
| `actions/plan/index.yaml` | `003-decision-documentation-requirement`, `010-specification-fidelity-requirement` | `requirements-validation-workflow`, `adr-drafting-workflow` |
| After `_normalize_directive_id()` | `DIRECTIVE_003`, `DIRECTIVE_010` | (unchanged) |
| Expected in WP prompt (T002) | DIRECTIVE_003, DIRECTIVE_010 | requirements-validation-workflow, adr-drafting-workflow |

**Result**: MATCH. The canonical path correctly resolves plan's 2 directives + 2 tactics.

### Verification: implement

| Source | Directives | Tactics | Toolguides |
|---|---|---|---|
| `actions/implement/index.yaml` | `024-locality-of-change`, `025-boy-scout-rule`, `028-search-tool-discipline`, `029-agent-commit-signing-policy`, `030-test-and-typecheck-quality-gate`, `034-test-first-development` | `acceptance-test-first`, `tdd-red-green-refactor`, `change-apply-smallest-viable-diff`, `autonomous-operation-protocol`, `quality-gate-verification`, `stopping-conditions` | `efficient-local-tooling` |
| After `_normalize_directive_id()` | `DIRECTIVE_024`, `DIRECTIVE_025`, `DIRECTIVE_028`, `DIRECTIVE_029`, `DIRECTIVE_030`, `DIRECTIVE_034` | (unchanged) | (unchanged) |
| Expected in WP prompt (T002) | 6 directives | 6 tactics | 1 toolguide |

**Result**: MATCH. The canonical path correctly resolves implement's 6 directives + 6 tactics + 1 toolguide.

### Verification: review

| Source | Directives | Tactics |
|---|---|---|
| `actions/review/index.yaml` | `010-specification-fidelity-requirement`, `030-test-and-typecheck-quality-gate` | `review-intent-and-risk-first`, `quality-gate-verification`, `stopping-conditions` |
| After `_normalize_directive_id()` | `DIRECTIVE_010`, `DIRECTIVE_030` | (unchanged) |
| Expected in WP prompt (T002) | DIRECTIVE_010, DIRECTIVE_030 | review-intent-and-risk-first, quality-gate-verification, stopping-conditions |

**Result**: MATCH. The canonical path correctly resolves review's 2 directives + 3 tactics.

### Project-Directive Intersection

The canonical path intersects action directives with `governance.yaml` `selected_directives`. The intersection logic in `_build_directive_lines()` (line 156):

```python
if project_directives and norm_id not in project_directives:
    continue
```

This means:
- If `governance.yaml` has `selected_directives`, only those directives that appear in BOTH the action index AND the project selections are rendered.
- If `governance.yaml` has no `selected_directives` (empty set), ALL action index directives are rendered (the `if project_directives` guard skips filtering when the set is empty).

This is correct behavior: project-level governance narrows the action index, not the other way around.

### Discrepancies Found

**None.** All four action indices resolve correctly through the canonical path. The normalization function handles both slug format (`024-locality-of-change`) and ID format (`DIRECTIVE_024`) correctly.

### Oracle Confirmation

**The canonical path (`src/charter/context.py`) is confirmed as the correct oracle for WP04 invariant tests.** Each action's resolved artifacts match its `index.yaml` source exactly. The project-directive intersection logic is sound.

---

## T003: Phase 1 Reroute Plan

### Current Callers

| # | Caller | Import | Current Path |
|---|--------|--------|-------------|
| 1 | `src/specify_cli/next/prompt_builder.py:13` | `from specify_cli.charter.context import build_charter_context` | Legacy |
| 2 | `src/specify_cli/cli/commands/agent/workflow.py:20` | `from specify_cli.charter.context import build_charter_context` | Legacy |
| 3 | `src/specify_cli/cli/commands/charter.py:13` | `from charter.context import build_charter_context` | Canonical (already correct) |

### Caller 1: `prompt_builder.py` (spec-kitty next)

**Current behavior** (legacy path):
- Called via `_governance_context(repo_root, action=action)` at line 273.
- On first load for a bootstrap action: renders Policy Summary + unfiltered references.
- On subsequent loads: renders compact governance.
- Falls back to `_legacy_governance_context()` if charter context returns `mode="missing"` or raises an exception.
- No action doctrine, no guidelines, no filtered references.

**After reroute** (canonical path):
- Import changes to `from charter.context import build_charter_context`.
- The caller passes no `depth` parameter, so the canonical default applies: first load gets `depth=2` (bootstrap + action doctrine + guidelines + filtered refs), subsequent loads get `depth=1` (compact).
- **Net change**: First-load prompts for implement will now include 6 directives, 6 tactics, guidelines prose, and action-filtered references. First-load prompts for specify/plan/review similarly gain their respective doctrine payloads.
- The `CharterContextResult` gains a `depth` field. The caller only reads `.text` and `.mode`, so the new field is harmless.

**Prompt behavior change for agents**:

| Action | Current first-load prompt | Post-reroute first-load prompt | Change |
|--------|--------------------------|-------------------------------|--------|
| specify | Policy Summary + all refs | Policy Summary + 2 directives + 1 tactic + guidelines + action-filtered refs | Moderate: agents now see doctrine constraints |
| plan | Policy Summary + all refs | Policy Summary + 2 directives + 2 tactics + guidelines + action-filtered refs | Moderate |
| implement | Policy Summary + all refs | Policy Summary + 6 directives + 6 tactics + guidelines + action-filtered refs | **Large**: significantly richer prompt |
| review | Policy Summary + all refs | Policy Summary + 2 directives + 3 tactics + guidelines + action-filtered refs | Moderate |
| (subsequent) | Compact governance | Compact governance | None |

### Caller 2: `workflow.py` (agent workflow commands)

**Current behavior** (legacy path):
- Called via `_render_charter_context(repo_root, action)` at line 192.
- Returns `context.text` directly, or falls back to `f"Governance: unavailable ({exc})"` on error.
- Same legacy behavior as caller 1: no action doctrine, no guidelines, no filtered references.

**After reroute** (canonical path):
- Import changes to `from charter.context import build_charter_context`.
- The caller passes no `depth`, so canonical defaults apply identically to caller 1.
- **Net change**: Same as caller 1. The `_render_charter_context` wrapper only reads `.text`, so the additional `depth` field is invisible.

**Prompt behavior change**: Identical to caller 1 (same table above).

### Caller 3: `charter.py` (already canonical)

No change needed. Already imports from `charter.context`.

### Reroute Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| **Prompt size increase on first load** | Medium | The action doctrine + guidelines adds 200-500 tokens per first-load prompt. For implement, the payload is largest (~6 directives + 6 tactics + guidelines). This is intentional enrichment, not bloat, but agents consuming token-constrained contexts should be aware. |
| **Behavioral shift: agents now see directive constraints** | Low-Medium | Legacy callers gave agents no directive/tactic guidance. Post-reroute, agents will see explicit doctrine ("DIRECTIVE_024: Locality of Change", "tdd-red-green-refactor", etc.). This is the desired outcome but means agent behavior may change -- they will now follow these directives when they were previously unaware of them. |
| **Action-filtered references reduce visible refs** | Low | Legacy showed all references. Canonical filters `local_support` refs by action scope. Non-local_support refs are always shown. This means agents may see fewer references on first load, but only because irrelevant action-scoped support docs are hidden. |
| **`_load_references` field expansion** | None | The canonical `_load_references` extracts `kind` and `summary` in addition to `id`, `title`, `local_path`. These extra fields are consumed internally by `_filter_references_for_action()` and do not appear in rendered text differently. |
| **Exception handling difference** | Low | Legacy `_load_references` catches bare `Exception`. Canonical catches `(YAMLError, UnicodeDecodeError, OSError)` explicitly. The canonical path also has `_load_state` with similarly narrow exception handling. The prompt_builder wrapper already has its own try/except around the call, so this is safe. |
| **State file compatibility** | None | Both implementations use the same `context-state.json` file at `.kittify/charter/context-state.json` with the same schema. Rerouting does not break existing state. |
| **Fallback behavior in prompt_builder** | Low | The prompt_builder `_governance_context()` function falls back to `_legacy_governance_context()` if charter context returns `mode="missing"` or raises. After reroute, the canonical implementation uses `charter.resolver.resolve_governance` (richer GovernanceResolution with tactics, styleguides, etc.) for compact mode, while the fallback uses `specify_cli.charter.resolver.resolve_governance` (simpler). The compact text output format is identical (same 5 lines), but they use different resolver instances. The fallback path should be evaluated separately -- it may need to switch to `charter.resolver` too. |

### Recommendation

Phase 1 reroute is **safe and recommended**. The behavioral delta is entirely additive (agents gain doctrine context they previously lacked). No existing functionality is removed or broken. The main consideration is that agent prompts will be materially richer on first load, which is the explicit goal of the canonical path.

**Action items for Phase 1**:
1. Change import in `prompt_builder.py:13` from `specify_cli.charter.context` to `charter.context`.
2. Change import in `workflow.py:20` from `specify_cli.charter.context` to `charter.context`.
3. Consider whether `prompt_builder.py`'s `_legacy_governance_context()` fallback should also switch to `charter.resolver.resolve_governance` for consistency.
4. Add integration test confirming first-load implement prompt includes action doctrine section.
5. No signature changes needed: both callers pass `action=action, mark_loaded=True` which is compatible with the canonical signature (canonical's `depth` parameter has a default of `None`).

---

## Validation Checklist

### T001 Validation
- [x] All 4 actions x 3 depths documented for canonical
- [x] All 4 actions documented for legacy (single depth equivalent)
- [x] Delta clearly shows what canonical adds over legacy

### T002 Validation
- [x] specify: 2 directives + 1 tactic verified against index.yaml
- [x] plan: 2 directives + 2 tactics verified against index.yaml
- [x] implement: 6 directives + 6 tactics + 1 toolguide verified against index.yaml
- [x] review: 2 directives + 3 tactics verified against index.yaml
- [x] Project-directive intersection logic verified correct
- [x] No discrepancies found
- [x] **Canonical path is confirmed as correct oracle**

### T003 Validation
- [x] Both legacy callers' reroute impact documented
- [x] Net prompt behavior change described per action
- [x] Risks flagged with severity and mitigation
- [x] Actionable reroute steps listed for Phase 1
