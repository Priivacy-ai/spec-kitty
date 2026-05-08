---
work_package_id: WP01
title: RISK-1 — Daemon-Intent Gate Scan Expansion
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- NFR-001
planning_base_branch: feature/650-dashboard-ui-ux-overhaul
merge_target_branch: feature/650-dashboard-ui-ux-overhaul
branch_strategy: Planning artifacts for this feature were generated on feature/650-dashboard-ui-ux-overhaul. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/650-dashboard-ui-ux-overhaul unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
agent: claude
history:
- date: '2026-05-02'
  event: created
  note: Auto-generated alongside tasks.md
agent_profile: implementer-ivan
authoritative_surface: tests/sync/
execution_mode: code_change
owned_files:
- tests/sync/test_daemon_intent_gate.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load implementer-ivan
```

## Objective

Expand `test_no_unauthorized_daemon_call_sites` so the gate covers `src/dashboard/` in addition to `src/specify_cli/`. Without this, a future direct call to `ensure_sync_daemon_running` from the new `src/dashboard/services/` tree would not be caught.

## Subtasks (already implemented at commit `dcbba9439`)

### T001 — `_scan_for_callers` helper + `SCAN_ROOTS`

```python
SCAN_ROOTS: tuple[Path, ...] = (
    REPO_ROOT / "src" / "specify_cli",
    REPO_ROOT / "src" / "dashboard",
)


def _scan_for_callers(roots: tuple[Path, ...]) -> set[str]:
    hits: set[str] = set()
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            if "ensure_sync_daemon_running(" in text:
                rel = str(path.relative_to(REPO_ROOT))
                hits.add(rel)
    return hits
```

### T002 — Allowlist update

`ALLOWED_CALL_SITES` adds `"src/dashboard/services/sync.py"` with a comment explaining the DI default reference is the authorized path.

### T003 — Negative-path test

`test_gate_detects_unauthorized_call_in_dashboard_tree` builds a synthetic tree under `tmp_path`, drops in a fake `rogue.py` that calls `ensure_sync_daemon_running(intent=None)`, and asserts the scanner finds it.

## Definition of Done

- [ ] `pytest tests/sync/test_daemon_intent_gate.py -q` passes (13 + 1 = 14 tests).
- [ ] `_scan_for_callers` is exported (or at module-level) so future tests can reuse it.
- [ ] The negative-path test fails if the scan does not cover `src/dashboard/` (verified by intentionally regressing the SCAN_ROOTS tuple and confirming the test fails).

## Reviewer guidance

- Confirm the new test does not depend on any production code path — uses `tmp_path` only.
- Confirm `ALLOWED_CALL_SITES` rationale is in a comment.

## Risks

- Scan-time regression on the daemon-gate test (NFR-001). Mitigation: the additional root adds ~10 files to walk; well under the 100 ms budget.

## Activity Log

- 2026-05-02T19:50:29Z – claude – Moved to claimed
- 2026-05-02T19:50:32Z – claude – Moved to in_progress
- 2026-05-02T19:52:23Z – claude – Moved to for_review
- 2026-05-02T19:52:26Z – claude – Moved to in_review
- 2026-05-02T19:52:29Z – claude – Moved to approved
- 2026-05-02T19:54:13Z – claude – Done override: Implementation landed directly on feature/650-dashboard-ui-ux-overhaul at commit dcbba9439 without lane worktrees; the work-package decomposition in this followup mission formalizes the post-merge review trail for findings already in the tree
