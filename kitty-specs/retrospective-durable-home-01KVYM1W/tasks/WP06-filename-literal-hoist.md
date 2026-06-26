---
work_package_id: WP06
title: Hoist the retrospective.yaml filename literal to one named constant
dependencies:
- WP03
requirement_refs:
- FR-010
tracker_refs:
- '#2119'
planning_base_branch: fix/3.2.3-coord-surface-regressions
merge_target_branch: fix/3.2.3-coord-surface-regressions
branch_strategy: Planning artifacts for this mission were generated on fix/3.2.3-coord-surface-regressions. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/3.2.3-coord-surface-regressions unless the human explicitly redirects the landing branch.
subtasks:
- T061
- T062
- T063
- T064
phase: Phase 2 - Filename-literal hoist (crosses the shared-package boundary; own WP)
assignee: ''
agent: "claude:sonnet:reviewer-renata:reviewer"
shell_pid: "1784200"
history:
- at: '2026-06-25T19:36:37Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks (planner-priti)
agent_profile: python-pedro
authoritative_surface: src/specify_cli/core/constants.py
create_intent:
- tests/core/test_retrospective_filename_constant.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/core/constants.py
- src/specify_cli/retrospective/writer.py
- src/specify_cli/retrospective/lifecycle_events.py
- src/specify_cli/retrospective/summary.py
- src/specify_cli/cli/commands/retrospect.py
- src/specify_cli/post_merge/retrospective_terminus.py
- src/runtime/next/_internal_runtime/retrospective_terminus.py
- tests/core/test_retrospective_filename_constant.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP06 — `retrospective.yaml` filename-literal hoist (FR-010)

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter
**before parsing the rest of this prompt**, and behave according to its guidance.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If the profile cannot be loaded, run `spec-kitty agent profile list` and select the best
match for `task_type: implement` on `authoritative_surface:
src/specify_cli/core/constants.py`.

---

## Objective

**Hoist the `retrospective.yaml` filename literal to ONE named constant** (Sonar S1192). The
literal appears as **8 hoistable string literals + 2 `.tmp` f-string prefixes across 6 `.py`
files** (re-censused — the earlier "47 occurrences / 13 files" conflated docstrings and prose,
which are NOT in scope). The hoist crosses the **shared-package boundary** (`src/runtime/next` +
`src/mission_runtime`-adjacent), so the constant lives where all three packages can import it
cleanly.

> **Why this is its own WP, depending on WP03:** the hoist crosses the shared-package boundary and
> warrants an isolated review. It edits the SAME retrospective files WP03 owns (writer,
> lifecycle_events, both terminus). That shared ownership is legal because **WP06 `depends: [WP03]`
> → the pair is dependency-ordered (sequential) → overlap-exempt** (`ownership/validation.py:198-207`).
> WP06 lands AFTER WP03, so it hoists the literals on the already-consolidated resolver calls.

## The 10 literal sites (live-verified on `e36547461`)

| # | Site | Form |
|---|------|------|
| 1 | `src/runtime/next/_internal_runtime/retrospective_terminus.py:76` | `... / "retrospective.yaml"` (in `_record_path_str`; note WP03 re-pointed this resolver — hoist the literal) |
| 2 | `src/specify_cli/cli/commands/retrospect.py:1025` | `(mission_dir / "retrospective.yaml")` |
| 3 | `src/specify_cli/post_merge/retrospective_terminus.py:71` | `feature_dir / "retrospective.yaml"` |
| 4 | `src/specify_cli/retrospective/lifecycle_events.py:344` | `feature_dir / "retrospective.yaml"` |
| 5 | `src/specify_cli/retrospective/summary.py:336` | `mission_dir / "retrospective.yaml"` |
| 6 | `src/specify_cli/retrospective/summary.py:666` | `feature_dir / "retrospective.yaml"` |
| 7 | `src/specify_cli/retrospective/writer.py:49` | `feature_dir / "retrospective.yaml"` |
| 8 | `src/specify_cli/retrospective/writer.py:60` | `... / mission_id / "retrospective.yaml"` (inside `_legacy_record_path` — hoist the LITERAL only; do NOT change the function's resolution, it is the load-bearing `.kittify` read) |
| 9 | `src/specify_cli/retrospective/writer.py:148` | `f"retrospective.yaml.tmp.{os.getpid()}.{...}"` (`.tmp` prefix) |
| 10 | `src/specify_cli/retrospective/writer.py:424` | `f"retrospective.yaml.tmp.{os.getpid()}.{...}"` (`.tmp` prefix) |

**NOT in scope:** docstring/prose mentions (`writer.py:1,37,40,71,72,112,138,480,481,525`,
`lifecycle_events.py:480,481`, `post_merge/retrospective_terminus.py:11,45,74`, etc.) — these are
documentation, not hoistable code literals.

## Constant home (boundary-safe — verified)

`src/specify_cli/core/constants.py` already houses `KITTY_SPECS_DIR = "kitty-specs"` (`:5`), and
**all three packages already import from it**:
- `src/mission_runtime/artifacts.py:19` → `from specify_cli.core.constants import KITTY_SPECS_DIR`
- `src/runtime/next/_internal_runtime/planner.py:36` → `from specify_cli.core.constants import KITTY_SPECS_DIR`

So define `RETROSPECTIVE_FILENAME = "retrospective.yaml"` in `core/constants.py` and consume it via
`from specify_cli.core.constants import RETROSPECTIVE_FILENAME` — the EXISTING public import surface
(C-006 / FR-010: "consume via the public import surface; do not anchor a new cross-boundary import").

## Context & Constraints

Ground truth — read before editing:
- [spec.md](../spec.md) **FR-010** + **SC-006(a)** (exactly one named constant) + **C-005** (the
  atomic-YAML `.tmp` dup is NOT folded — but the `.tmp` PREFIX literal IS hoisted; the dup is the
  duplicated *write logic*, not the filename string).
- [contracts/terminal-artifact-teardown-contract.md](../contracts/terminal-artifact-teardown-contract.md) **C5**.
- [research.md](../research.md) brownfield split-brain/LOC scan (8 literals + 2 `.tmp`).

**Negative scope:**
- Do NOT touch docstrings/prose mentions (not hoistable code).
- Do NOT change `_legacy_record_path`'s resolution (site #8 — hoist its LITERAL only; the function
  stays the load-bearing `.kittify` read path WP03 left untouched).
- Do NOT anchor a new bespoke cross-boundary import — use the established `core.constants` surface.
- Do NOT fold the atomic-YAML write duplication (RELATE #2125, C-005).

## Branch Strategy

- **Strategy**: depends on WP03 (lands AFTER the consolidation; shares the retrospective files,
  overlap-exempt via the dependency edge).
- **Planning base branch**: `fix/3.2.3-coord-surface-regressions`
- **Merge target branch**: `fix/3.2.3-coord-surface-regressions`

> WP06 OWNS `core/constants.py` (exclusively), `summary.py`, `retrospect.py`, and shares the four
> retrospective files with WP03 (dependency-ordered → overlap-exempt). WP06 lands after WP03.

## Subtasks & Detailed Guidance

### Subtask T061 — Define the constant

- **Purpose**: One named constant in the boundary-safe home.
- **Files**: `src/specify_cli/core/constants.py`.
- **Steps**:
  1. Add `RETROSPECTIVE_FILENAME = "retrospective.yaml"` near `KITTY_SPECS_DIR` (`:5`), with a
     one-line comment.
  2. Confirm `core/constants.py` has no imports that would cycle (it is a leaf module — `KITTY_SPECS_DIR`
     proves it imports cleanly into `mission_runtime` and `runtime/next`).

### Subtask T062 — Hoist the 8 string literals

- **Purpose**: Replace each `"retrospective.yaml"` path literal with the constant.
- **Files**: sites #1–#8 (the 6 `.py` files).
- **Steps**:
  1. In each module, `from specify_cli.core.constants import RETROSPECTIVE_FILENAME` and replace
     the literal: `feature_dir / "retrospective.yaml"` → `feature_dir / RETROSPECTIVE_FILENAME`.
  2. Site #8 (`writer.py:60`, inside `_legacy_record_path`): replace ONLY the `"retrospective.yaml"`
     literal; leave the `.kittify / missions / mission_id` resolution exactly as-is (WP03 left this
     function untouched as the load-bearing back-compat read).
  3. Site #1 (`runtime/next/.../retrospective_terminus.py:76`): WP03 re-pointed this resolver to
     the primary authority; hoist the remaining filename literal onto the constant via the public
     import.
- **Notes**: each module gains ONE import; no new cross-boundary import surface.

### Subtask T063 — Compose the 2 `.tmp` f-string prefixes from the constant

- **Purpose**: Make the `.tmp` temp-name prefix derive from the constant (site #9, #10).
- **Files**: `writer.py:148`, `:424`.
- **Steps**:
  1. `f"retrospective.yaml.tmp.{os.getpid()}.{os.urandom(4).hex()}"` →
     `f"{RETROSPECTIVE_FILENAME}.tmp.{os.getpid()}.{os.urandom(4).hex()}"`.
  2. Both occurrences are byte-identical — confirm they remain identical after the hoist
     (consider extracting a tiny `_tmp_name()` helper IF Sonar flags the duplicated f-string, but
     the atomic-write LOGIC is NOT consolidated — C-005 / RELATE #2125; only the filename string
     is hoisted).
- **Notes**: this is the filename-string hoist ONLY, not the atomic-YAML write-dup consolidation.

### Subtask T064 — Single-definition assertion test (SC-006a)

- **Purpose**: Lock "exactly one named constant" and zero surviving hoistable literals.
- **Files**: new `tests/core/test_retrospective_filename_constant.py`.
- **Steps**:
  1. Assert `RETROSPECTIVE_FILENAME == "retrospective.yaml"` and is importable from
     `specify_cli.core.constants`.
  2. GREP the 6 `.py` files (the literal sites) and assert no bare `"retrospective.yaml"` PATH
     literal survives outside the constant definition (docstrings/prose excluded). Count-agnostic
     phrasing preferred (fail on any surviving code literal).
- **Notes**: a structural single-definition guard; do NOT hardcode the site count.

## Test Strategy

- `PWHEADLESS=1 pytest tests/core/test_retrospective_filename_constant.py -q`.
- Re-run `tests/retrospective/` (WP03's tests) to confirm the hoist is behavior-neutral.
- `ruff check` + `mypy --strict` on all 7 touched modules — zero issues, no suppressions.

## Definition of Done

- [ ] `RETROSPECTIVE_FILENAME` defined ONCE in `core/constants.py`.
- [ ] All 8 string literals + both `.tmp` f-string prefixes consume the constant via the public
  `specify_cli.core.constants` import (no new cross-boundary import surface).
- [ ] Site #8 (`_legacy_record_path`) literal hoisted WITHOUT changing its resolution.
- [ ] Single-definition assertion test passes; no bare path literal survives (count-agnostic).
- [ ] Atomic-YAML write LOGIC unchanged (C-005 — only the filename string is hoisted).
- [ ] WP03's tests still green (behavior-neutral); ruff + `mypy --strict` clean, no suppressions.

## Risks & Mitigations

- **Cross-boundary import cycle:** mitigated by using `core/constants.py` (a leaf module already
  imported by `mission_runtime` and `runtime/next` — proven by `KITTY_SPECS_DIR`).
- **Accidentally changing `_legacy_record_path` resolution:** mitigated by the negative scope —
  hoist the literal ONLY (site #8).
- **Scope creep into the atomic-YAML dup:** mitigated by C-005 — only the filename string moves.

## Review Guidance

- Confirm exactly ONE constant definition and every hoistable literal consumes it via the existing
  public import (no bespoke cross-boundary import).
- Confirm `_legacy_record_path`'s resolution is unchanged (only its literal hoisted).
- Confirm the atomic-write logic is untouched (C-005); the `.tmp` change is the filename prefix only.
- Confirm WP03's behavioral tests still pass (the hoist is behavior-neutral).

## Activity Log

- 2026-06-25T19:36:37Z – system – Prompt created via /spec-kitty.tasks (planner-priti); FR-010.
</content>
- 2026-06-25T22:05:14Z – claude:sonnet:python-pedro:implementer – shell_pid=1766531 – Started implementation via action command
- 2026-06-25T22:12:44Z – claude:sonnet:python-pedro:implementer – shell_pid=1766531 – Ready: retrospective.yaml literal hoisted to RETROSPECTIVE_FILENAME constant in core/constants.py across 9 sites (8 path-composition + 2 .tmp f-strings); single-definition AST guard test green; 512 retrospective+post_merge tests pass; ruff+mypy clean
- 2026-06-25T22:13:21Z – claude:sonnet:python-pedro:implementer – shell_pid=1766531 – Code on lane-c (a5904322d): retrospective.yaml hoisted to RETROSPECTIVE_FILENAME across 9 sites, 512 passed
- 2026-06-25T22:13:23Z – claude:sonnet:reviewer-renata:reviewer – shell_pid=1784200 – Started review via action command
- 2026-06-25T22:20:34Z – user – shell_pid=1784200 – renata APPROVE: literal hoisted to RETROSPECTIVE_FILENAME, AST guard mutation-probed, behaviorally neutral, gates clean
