---
work_package_id: WP02
title: WP Manifest Schema and Rendering
dependencies:
- WP01
requirement_refs:
- FR-006
- FR-007
- FR-008
- FR-009
- FR-010
- FR-011
- FR-013
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T005
- T006
- T007
- T008
- T009
- T015
agent: claude
history:
- date: '2026-06-06'
  event: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/core/
execution_mode: code_change
owned_files:
- src/specify_cli/core/wps_manifest.py
- src/specify_cli/cli/commands/agent/mission.py
- src/doctrine/missions/mission-steps/software-dev/tasks-outline/prompt.md
- src/doctrine/missions/mission-steps/software-dev/tasks-packages/prompt.md
role: implementer
tags: []
review_status: acknowledged
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile:

```
/ad-hoc-profile-load python-pedro
```

This configures your working style, doctrine references, and capability constraints for this work package.

---

## Objective

Add `plan_concern_refs` and `cross_cutting` fields to `WorkPackageEntry` in `wps_manifest.py`. Extend `generate_tasks_md_from_manifest()` to render concern refs. Add `check_concern_refs_coverage()` helper and wire its output into the `finalize-tasks` non-fatal warning. Update the `tasks-outline` and `tasks-packages` prompts to require IC-## citation (in `wps.yaml` only — not in WP prompt frontmatter).

---

## Context

`WorkPackageEntry` in `src/specify_cli/core/wps_manifest.py` currently has six fields: `id`, `title`, `dependencies`, `owned_files`, `requirement_refs`, `subtasks`, `prompt_file`. There is no place to record which plan concern(s) a WP addresses. This WP adds that place.

**Key constraints**:
- Both new fields must be backwards-compatible: existing `wps.yaml` files without these keys must parse without error.
- `plan_concern_refs` items must match `^IC-\d{2}$` using an explicit ASCII pattern (project directive DIR-010).
- `cross_cutting` is advisory — `finalize-tasks` warns (does not hard-fail) for WPs missing both `plan_concern_refs` and `cross_cutting: true`.
- The project uses **pydantic v2** — use `@field_validator(..., mode="before")` syntax, not v1's `@validator`.

Read `src/specify_cli/core/wps_manifest.py` before editing. The file uses `PrivateAttr` and pydantic v2 `model_validate`; follow the existing patterns exactly.

---

## Subtask T005 — Add plan_concern_refs field to WorkPackageEntry

**File**: `src/specify_cli/core/wps_manifest.py`

**Purpose**: Add an optional `plan_concern_refs: list[str]` field with IC-## pattern validation.

**Read the file first**, then add after the existing `prompt_file` field:

```python
plan_concern_refs: list[str] = Field(default_factory=list)
cross_cutting: bool = False
```

Add a field validator immediately after (following the existing `validate_dependencies` pattern):

```python
@field_validator("plan_concern_refs")
@classmethod
def validate_plan_concern_refs(cls, v: list[str]) -> list[str]:
    import re
    for ref in v:
        if not re.match(r"^IC-\d{2}$", ref, re.ASCII):
            raise ValueError(
                f"plan_concern_ref must match IC-## (e.g. IC-01), got: {ref!r}"
            )
    return v
```

**Important**: The `re.ASCII` flag is required per project directive DIR-010. Do not use `\w` or default Unicode semantics.

**Validation**:
- [ ] `from specify_cli.core.wps_manifest import WorkPackageEntry; WorkPackageEntry(id="WP01", title="test")` — no error (backwards compat)
- [ ] `WorkPackageEntry(id="WP01", title="test", plan_concern_refs=["IC-01", "IC-23"])` — no error
- [ ] `WorkPackageEntry(id="WP01", title="test", plan_concern_refs=["IC-1"])` — raises `ValidationError`
- [ ] `WorkPackageEntry(id="WP01", title="test", plan_concern_refs=["WP01"])` — raises `ValidationError`
- [ ] `mypy --strict src/specify_cli/core/wps_manifest.py` passes

---

## Subtask T006 — Add cross_cutting field to WorkPackageEntry

**File**: `src/specify_cli/core/wps_manifest.py`

**Purpose**: Add `cross_cutting: bool = False` alongside `plan_concern_refs`. No validator needed — pydantic handles bool coercion.

This field signals that a WP intentionally has no concern refs because it is infrastructure shared across all concerns (e.g. a test harness setup WP). `finalize-tasks` will use it in the warning logic (FR-013).

**Update `WpsManifest`** if it has any `model_config` that rejects extra fields — the field must be declared, not treated as unknown.

**Validation**:
- [ ] `WorkPackageEntry(id="WP01", title="test", cross_cutting=True)` — no error
- [ ] `WorkPackageEntry(id="WP01", title="test")` — `entry.cross_cutting` is `False`
- [ ] `mypy --strict` still passes

---

## Subtask T007 — Extend generate_tasks_md_from_manifest()

**File**: `src/specify_cli/core/wps_manifest.py`

**Purpose**: When a WP's `plan_concern_refs` is non-empty, render a `**Plan Concerns**: IC-01, IC-03` line in the generated `tasks.md`. When empty, render nothing (no label, no blank line).

**Read the existing `generate_tasks_md_from_manifest()` function** to understand the current rendering pattern. The function currently renders:
```python
if wp.requirement_refs:
    lines.append(f"**Requirement Refs**: {', '.join(wp.requirement_refs)}")
if wp.owned_files:
    lines.append(f"**Owned Files**: {', '.join(wp.owned_files)}")
```

**Follow the exact same pattern** — the label format is title-case bold (`**Plan Concerns**:`), not sentence case. Insert after the `requirement_refs` block:

```python
if entry.plan_concern_refs:
    lines.append(f"**Plan Concerns**: {', '.join(entry.plan_concern_refs)}")
```

**Validation**:
- [ ] Generate tasks.md from a manifest where WP01 has `plan_concern_refs: [IC-01, IC-03]` → output contains `**Plan Concerns**: IC-01, IC-03` (exact string)
- [ ] Generate tasks.md from a manifest where WP02 has `plan_concern_refs: []` → output does NOT contain "Plan Concerns"
- [ ] Existing golden-file tests (if any) still pass

---

## Subtask T008 — Update tasks-outline/prompt.md

**File**: `src/doctrine/missions/mission-steps/software-dev/tasks-outline/prompt.md`

**Purpose**: The current prompt tells the tasks-outline agent to "Roll Subtasks into Work Packages" without any instruction to cite which plan concerns each WP covers. Add a step requiring IC-## citation.

**Read the file first** to find the "Roll Subtasks into Work Packages" section (around line 84 based on prior analysis).

**Add the following step** immediately after the subtask grouping instruction and before the `wps.yaml` schema section:

```markdown
### 4a. Cite plan concern refs for each WP

For each work package, record which implementation concern(s) from `plan.md` it
addresses by populating `plan_concern_refs` in `wps.yaml`.

- If the WP covers exactly one concern: `plan_concern_refs: [IC-01]`
- If the WP spans multiple concerns: `plan_concern_refs: [IC-01, IC-03]`
- If the WP is cross-cutting infrastructure with no specific concern (e.g. a test
  harness setup WP), set `cross_cutting: true` and leave `plan_concern_refs` empty.

A WP missing both `plan_concern_refs` and `cross_cutting: true` will trigger a
warning from `finalize-tasks`. Every WP should cite at least one IC-## ref or
declare itself cross-cutting.
```

**Validation**:
- [ ] The instruction appears in the prompt before the `wps.yaml` schema example
- [ ] The schema example in the prompt includes `plan_concern_refs` as a field (update the example `wps.yaml` block if one exists)

---

## Subtask T009 — Update tasks-packages/prompt.md

**File**: `src/doctrine/missions/mission-steps/software-dev/tasks-packages/prompt.md`

**Purpose**: The tasks-packages prompt generates individual `tasks/WP##.md` files from `wps.yaml`. It must NOT write `plan_concern_refs` into WP prompt frontmatter — `WPMetadata` (which parses WP prompt frontmatter) is configured `extra="forbid"` and will raise `ValidationError` on `finalize-tasks --validate-only`. Instead, the prompt should reinforce that `plan_concern_refs` lives in `wps.yaml` only and explain the finalize-tasks warning.

**Read the file first** to understand the frontmatter generation section.

**Find** the section that describes what fields to include in generated WP frontmatter, and **add a note**:

```markdown
> **Note**: Do NOT include `plan_concern_refs` in the WP prompt file frontmatter.
> `WPMetadata` (which validates WP frontmatter during `finalize-tasks`) does not
> accept this field — including it causes ValidationError. `plan_concern_refs`
> lives in `wps.yaml` entries only. `finalize-tasks` will emit a non-fatal warning
> for any WP whose `wps.yaml` entry has empty `plan_concern_refs` and
> `cross_cutting: false`.
```

**Validation**:
- [ ] The prompt explicitly says `plan_concern_refs` must NOT appear in WP prompt frontmatter
- [ ] The prompt explains where the field lives (`wps.yaml`) and what happens without it (warning from finalize-tasks)
- [ ] No frontmatter template or example in the prompt includes `plan_concern_refs`

---

## Subtask T015 — Add check_concern_refs_coverage() and wire into finalize-tasks

**Files**: `src/specify_cli/core/wps_manifest.py`, `src/specify_cli/cli/commands/agent/mission.py`

**Purpose**: Implement the FR-013 non-fatal warning for WPs missing both `plan_concern_refs` and `cross_cutting`. Extract the logic into a testable helper function in `wps_manifest.py`, then call it from `finalize_tasks` in `mission.py`.

**Step 1 — Add helper to wps_manifest.py**:

After the `generate_tasks_md_from_manifest()` function, add:

```python
def check_concern_refs_coverage(manifest: "WpsManifest") -> list[str]:
    """Return warning strings for WPs with no concern traceability."""
    warnings = []
    for entry in manifest.work_packages:
        if not entry.plan_concern_refs and not entry.cross_cutting:
            warnings.append(
                f"{entry.id}: no plan_concern_refs and cross_cutting is False — "
                f"add IC-## refs to wps.yaml or set cross_cutting: true"
            )
    return warnings
```

Follow existing module conventions — use `"WpsManifest"` as a forward reference if needed to avoid circular issues (check whether `WpsManifest` is defined before or after this function and adjust accordingly).

**Step 2 — Wire into finalize_tasks in mission.py**:

**Read the file first**. Find the `all_ownership_warnings` list (around lines 2366–2611 in `mission.py`) and locate where other soft-check warnings are appended. Add after the existing glob/audit warning blocks:

```python
# Soft check: warn when WPs have no plan concern traceability (FR-013)
from specify_cli.core.wps_manifest import check_concern_refs_coverage
concern_warnings = check_concern_refs_coverage(parsed_manifest)
all_ownership_warnings.extend(concern_warnings)
```

Adjust the import to match the project's import style (top-of-function vs module-level). Do not move the import if the codebase uses top-level imports only. Follow existing patterns exactly.

**Important**: The warning must not raise an exception; `finalize-tasks` must still exit 0 and commit when only warnings are present.

**Validation**:
- [ ] `check_concern_refs_coverage(manifest)` returns a list with one entry per non-compliant WP
- [ ] `check_concern_refs_coverage(manifest)` returns `[]` when all WPs have refs or are cross_cutting
- [ ] `finalize-tasks` emits the warning text to the console but exits 0
- [ ] `finalize-tasks` on an existing mission (no new fields in wps.yaml) produces warnings for each WP but does not fail
- [ ] `mypy --strict src/specify_cli/core/wps_manifest.py` passes

---

## Branch Strategy

Planning branch: `main`
Merge target: `main`
Execution worktree: allocated by `lanes.json` after `finalize-tasks`
Depends on: WP01 merged first

Implement using: `spec-kitty agent action implement WP02 --agent claude`

---

## Definition of Done

- [ ] `WorkPackageEntry` has `plan_concern_refs` and `cross_cutting` fields with correct defaults
- [ ] `validate_plan_concern_refs` rejects non-IC-## values using `re.ASCII`
- [ ] `generate_tasks_md_from_manifest()` renders `**Plan Concerns**: IC-01, IC-03` when non-empty, nothing when empty
- [ ] `check_concern_refs_coverage()` returns warning strings for WPs missing concern traceability
- [ ] `finalize-tasks` appends `check_concern_refs_coverage()` results to `all_ownership_warnings` (non-fatal)
- [ ] `tasks-outline/prompt.md` includes IC citation requirement before `wps.yaml` schema
- [ ] `tasks-packages/prompt.md` explicitly states `plan_concern_refs` must NOT appear in WP frontmatter
- [ ] `mypy --strict src/specify_cli/core/wps_manifest.py` passes
- [ ] Existing `wps.yaml` without new fields parses without error (backwards compat)

---

## Reviewer Guidance

1. **Schema change**: Verify both new fields have empty-list / False defaults, not `None`. `None` defaults would break the conditional rendering check.
2. **Validator**: Confirm `re.ASCII` flag is used. Unicode `\d` matches Arabic-Indic digits — that would pass `IC-١٢` which is invalid.
3. **Rendering**: Confirm the rendered label is `**Plan Concerns**:` (title case, bold) — not `**Plan concerns**:` (sentence case). Must match the `**Requirement Refs**:` pattern.
4. **Prompts**: Verify the `tasks-outline` schema example includes `plan_concern_refs` as a `wps.yaml` field. Verify `tasks-packages` prompt has a clear note that this field must NOT be written to WP prompt frontmatter.
5. **Warning wiring**: Confirm the warning is appended to `all_ownership_warnings` (not printed directly) so it follows the same display path as ownership warnings and doesn't bypass JSON output mode.
