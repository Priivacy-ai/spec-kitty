---
work_package_id: WP02
title: 'Wave T fix: tests/sync/test_events.py ModuleNotFoundError cluster (FR-002)'
dependencies:
- WP01
requirement_refs:
- FR-002
planning_base_branch: kitty/mission-test-stabilization-and-debt-pass-01KSF9HJ
merge_target_branch: kitty/mission-test-stabilization-and-debt-pass-01KSF9HJ
branch_strategy: Planning artifacts for this mission were generated on kitty/mission-test-stabilization-and-debt-pass-01KSF9HJ. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/mission-test-stabilization-and-debt-pass-01KSF9HJ unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-test-stabilization-and-debt-pass-01KSF9HJ
base_commit: 6fc83de923da771bfa3f00d5be5fb134db124d88
created_at: '2026-05-25T15:21:42.085196+00:00'
subtasks:
- T005
- T006
- T007
agent: "claude:opus-4-7:reviewer-renata:reviewer"
shell_pid: "2173274"
history:
- by: claude
  at: '2026-05-25T14:00:00+00:00'
  action: generated
agent_profile: python-pedro
authoritative_surface: src/spec_kitty_events/
execution_mode: code_change
mission_id: 01KSF9HJBFKRBC617JVHKZXNE2
mission_slug: test-stabilization-and-debt-pass-01KSF9HJ
owned_files:
- tests/sync/test_events.py
- src/spec_kitty_events/**
priority: P0
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Invoke `/ad-hoc-profile-load` with argument `python-pedro` before reading further. Pedro's primary focus (Python imports, pytest, type hints) is the strict overmatch for a ModuleNotFoundError cluster fix.

## Objective

Fix the ~27 `ModuleNotFoundError` failures in `tests/sync/test_events.py`. Per the post-mission audit, this cluster has a single suspected root cause: a vendored-events import path drifted relative to the test imports.

After this WP, `pytest tests/sync/test_events.py -q` reports 0 failures and the fix is locked by a regression test that asserts the import resolves.

## Branch strategy

- Planning base branch: mission lane branch
- Merge target branch: `main`
- Execution: lane workspace allocated by `finalize-tasks`.

## Context

- [`triage.md`](../triage.md) — WP01's deliverable; quote the specific cluster row for this WP's scope.
- [`spec.md`](../spec.md) FR-002.
- The CLAUDE.md "Shared Package Boundary" section (post-cutover) notes that `events` is now an external PyPI dependency consumed only via `spec_kitty_events.*` public imports; the vendored copy under `src/specify_cli/spec_kitty_events/` was removed in mission `shared-package-boundary-cutover-01KQ22DS`.

## Subtask details

### T005 — Investigate the ModuleNotFoundError pattern

Run one failing test with `--tb=long` and capture the exact missing module path:

```bash
PWHEADLESS=1 .venv/bin/pytest tests/sync/test_events.py::TestErrorLogged::test_optional_fields -x --tb=long 2>&1 | grep -A 20 "ModuleNotFoundError\|ImportError"
```

Likely candidates (verify):
- `from spec_kitty_events.error_logged import ErrorLoggedPayload` — module exists but wrong path?
- `from specify_cli.spec_kitty_events.*` — the deleted vendored path that some tests still reference?
- Missing optional dependency in `.venv/`?

### T006 — Apply the import fix

Two patterns to evaluate (per the actual root cause):

**Pattern A (vendored-path drift)**: update test imports to use the external `spec_kitty_events.*` path.
**Pattern B (event-name drift)**: the schema-versioning epic (#1198 + #1200 + #1203) may be re-shaping payload classes; if the import path is correct but the class name moved, adjust the test imports OR file a sub-issue if the schema change is in progress on another mission.

Add a regression test in `tests/architectural/test_spec_kitty_events_imports.py` (NEW or extend existing) asserting that:
```python
def test_spec_kitty_events_canonical_imports_resolve():
    """Lock the canonical event-class import paths so future vendored-path drift fails fast."""
    from spec_kitty_events.error_logged import ErrorLoggedPayload  # noqa: F401
    from spec_kitty_events.dependency_resolved import DependencyResolvedPayload  # noqa: F401
    # ... full canonical set
```

This makes the ModuleNotFoundError cluster regress-detectable at architectural-test time rather than at sync-test time.

### T007 — Verify all ~27 affected tests pass

```bash
PWHEADLESS=1 .venv/bin/pytest tests/sync/test_events.py -q
```

Expected: 0 failures across the previously-failing 27. The other ~64 tests in this file that were passing should still pass.

## Definition of Done

- [ ] Root cause identified and quoted in commit message (Pattern A or B).
- [ ] Import fix applied; no `from specify_cli.spec_kitty_events.*` references remain in `tests/sync/`.
- [ ] Regression test added in `tests/architectural/test_spec_kitty_events_imports.py`.
- [ ] `pytest tests/sync/test_events.py -q` reports 0 failures.
- [ ] `ruff check tests/sync/test_events.py src/spec_kitty_events/` clean.

## Risks

- **Schema-versioning epic interference**: if #1198/#1200/#1203 work is mid-flight in another branch, the canonical event names may be moving. Coordinate with that epic OR file a sub-issue.
- **Test class drift**: 27 failures across 3 test classes (`TestErrorLogged`, `TestDependencyResolved`, `TestValidation`) — if they have different root causes, scope this WP to the largest cluster and defer the others.

## Reviewer guidance

1. Verify the regression test in `test_spec_kitty_events_imports.py` actually fails if the import paths regress (delete the import line, watch the test fail, restore).
2. Confirm zero `from specify_cli.spec_kitty_events.*` remain in `tests/`.
3. Spot-check that 3+ previously failing tests pass.

## Activity Log

- 2026-05-25T15:21:42Z – claude:opus-4-7:python-pedro:implementer – shell_pid=2068163 – Assigned agent via action command
- 2026-05-25T15:41:59Z – claude:opus-4-7:python-pedro:implementer – shell_pid=2068163 – Events package aligned to 5.2.0; sync+contract slice 1934/1936 pass (was ~130 failing); cluster C1+C2+C3+C8 resolved. 2 remaining failures are DIR-013 C99-i issues (check_docs_freshness frontmatter, WPCreated fixture schema) per triage.
- 2026-05-25T15:42:32Z – claude:opus-4-7:reviewer-renata:reviewer – shell_pid=2173274 – Started review via action command
- 2026-05-25T15:50:39Z – claude:opus-4-7:reviewer-renata:reviewer – shell_pid=2173274 – Review passed: events 5.2.0 alignment verified (91/91 test_events.py); sync+contract slice 1934 pass / 2 DIR-013 C99-i residuals (out of WP02 scope per triage); daemon-intent-gate allowlist entry well-commented with WP04 caller-audit cross-ref; snapshot 5.2.0 header correct and consumed by test_events_envelope_matches_resolved_version (4/4 pass).
