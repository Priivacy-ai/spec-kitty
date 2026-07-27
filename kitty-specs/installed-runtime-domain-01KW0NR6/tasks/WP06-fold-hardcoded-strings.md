---
work_package_id: WP06
title: Fold hardcoded upgrade strings in version_checker + schema_version (optional)
dependencies:
- WP05
requirement_refs:
- FR-021
tracker_refs: []
planning_base_branch: feat/installed-runtime-domain
merge_target_branch: feat/installed-runtime-domain
branch_strategy: Planning artifacts for this mission were generated on feat/installed-runtime-domain. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/installed-runtime-domain unless the human explicitly redirects the landing branch.
subtasks:
- T029
- T030
- T031
phase: Phase 6 - hardcoded string cleanup (strangler step 6, optional)
assignee: ''
agent: ''
shell_pid: '2508825'
history:
- at: '2026-06-26T00:00:00Z'
  actor: system
  action: Prompt generated via spec-kitty.tasks
agent_profile: ''
authoritative_surface: src/specify_cli/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/core/version_checker.py
- src/specify_cli/migration/schema_version.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP06 – Fold hardcoded upgrade strings (optional, FR-021)

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter
**before parsing the rest of this prompt**, and behave according to its guidance.

If the profile cannot be loaded, run `spec-kitty agent profile list` and select the
best match for `task_type: implement` on `authoritative_surface: src/specify_cli/`.

---

## Objective

Route the two hardcoded `"pipx upgrade spec-kitty-cli"` strings in
`core/version_checker.py` (line 218) and `migration/schema_version.py` (line 182)
through `plan_remediation()` so no install-method strings are hardcoded outside the
planner.

**This WP is explicitly DEFERRABLE** (spec.md FR-021, assumption 3). If scope
proves excessive, open a follow-up issue and proceed to WP07 without completing
this WP. The `detect_install_method()` shim remains alive through this step, so
deferring does not block WP07.

## Context & Constraints

Ground truth — read before editing:
- [`spec.md`](../spec.md) FR-021 (Low priority, explicitly optional)
- [`plan.md`](../plan.md) IC-06

**Deferral condition**: If routing through `plan_remediation()` requires adding
non-trivial state (e.g., threading `InstalledCliRuntime` through multiple callers
that have no current knowledge of it), defer the WP and create a follow-up issue.
A simple `detect_runtime()` + `plan_remediation()` inline call at the usage site is
acceptable scope; deeper refactoring is not.

**No snapshot regressions**: `version_checker.py` and `schema_version.py` tests must
pass before and after this change. The rendered output for a PIPX install must equal
`"pipx upgrade spec-kitty-cli"` — same as the hardcoded string.

## Branch Strategy

- **Planning base branch**: `feat/installed-runtime-domain`
- **Merge target branch**: `feat/installed-runtime-domain`

## Subtasks & Detailed Guidance

### T029 — Route hardcoded string in `version_checker.py`

Locate the hardcoded `"pipx upgrade spec-kitty-cli"` at line 218 in
`core/version_checker.py`.

**Replacement pattern** (inline, no new parameter threading):
```python
# Old:
upgrade_cmd = "pipx upgrade spec-kitty-cli"

# New (deferred import inside function to avoid circular imports):
from specify_cli.compat._detect.runtime import detect_runtime
from specify_cli.compat.remediation import plan_remediation, RemediationIntent
_runtime = detect_runtime()
_cmd = plan_remediation(_runtime, RemediationIntent.UPGRADE, target_version=None)
try:
    upgrade_cmd = _cmd.render(_runtime.platform)
except ValueError:
    upgrade_cmd = "pipx upgrade spec-kitty-cli"  # safe fallback
```

If the surrounding function already has significant context about the install method,
use it — do not call `detect_runtime()` redundantly if `install_method` is already known.

**Deferral check**: If the usage site is inside a tightly coupled path that would
require threading `InstalledCliRuntime` through 3+ callframes, record a
`# TODO(FR-021): defer to follow-up — plan_remediation threading too invasive` comment
and skip this subtask. Report the deferral in the WP completion message.

### T030 — Route hardcoded string in `schema_version.py`

Same pattern as T029 for `migration/schema_version.py` line 182.

Apply the same deferral criterion: if threading through callers is invasive, defer.

### T031 — Green-gate verification

Run version_checker and schema_version tests:
```bash
PWHEADLESS=1 pytest tests/ -k "version_checker or schema_version" -q
```

Run full suite:
```bash
PWHEADLESS=1 pytest tests/ -n auto --dist loadfile -q
pytest tests/architectural/test_no_legacy_terminology.py -q
```

Run ruff + mypy on modified files:
```bash
ruff check src/specify_cli/core/version_checker.py src/specify_cli/migration/schema_version.py
mypy src/specify_cli/core/version_checker.py src/specify_cli/migration/schema_version.py
```

No snapshot regressions for PIPX UPGRADE output.

## Success Criteria

- [ ] Hardcoded `"pipx upgrade spec-kitty-cli"` replaced by `plan_remediation()` in both files (OR deferral recorded with TODO comment + follow-up issue)
- [ ] PIPX UPGRADE render output matches pre-change value: `"pipx upgrade spec-kitty-cli"`
- [ ] All version_checker + schema_version tests pass
- [ ] Full test suite green; zero ruff/mypy issues
- [ ] If deferred: follow-up issue created; TODO comment added at both usage sites

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| `detect_runtime()` adds latency in version-check hot path | `detect_runtime()` is lightweight (no network); acceptable in a version-check context |
| Circular import between `version_checker` → `compat.remediation` → `compat._detect.runtime` | Use deferred imports inside the function body |
| Rendering for non-PIPX installs changes version_checker display | Snapshot test asserts PIPX render equals old hardcoded string; other methods produce planner-generated output which is the desired outcome |

## Deferral Note

Per spec.md assumption 3 and FR-021 (Low priority):
> FR-021 is independently shippable and may be deferred to a follow-up mission if it
> increases step 6 scope materially.

If deferred, create a GitHub issue with title "FR-021: fold hardcoded pipx strings in version_checker + schema_version" and link the spec.md reference. The `detect_install_method()` shim is still retired in WP07 regardless — the hardcoded strings in these two files will then use the non-shim path (direct call to the planner or a static fallback).
