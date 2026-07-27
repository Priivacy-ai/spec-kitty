---
affected_files: []
cycle_number: 2
mission_slug: cli-interview-decision-moments-01KPWT8P
reproduction_command:
reviewed_at: '2026-04-23T14:15:56Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP01
---

**Issue 1 — BLOCKER: `pip install -e ".[dev]"` fails due to unresolved transitive conflict with `spec-kitty-runtime`**

`pyproject.toml` now pins `spec-kitty-events==4.0.0` and `spec-kitty-runtime==0.4.5`. These two pins are mutually incompatible: `spec-kitty-runtime==0.4.5` requires `spec-kitty-events==3.3.0`. Running `pip install -e ".[dev]"` produces:

```
ERROR: Cannot install spec-kitty-cli[dev]==3.2.0a4 because these package versions have conflicting dependencies.
The conflict is caused by:
    spec-kitty-cli 3.2.0a4 depends on spec-kitty-events==4.0.0
    spec-kitty-runtime 0.4.5 depends on spec-kitty-events==3.3.0
```

This means the acceptance criterion "pip install -e '[dev]' exits 0" fails. The spec-kitty-runtime version must be updated to one that is compatible with spec-kitty-events==4.0.0, or the runtime pin must be removed/relaxed if runtime compatibility with 4.0.0 can be confirmed. As of review time, no published spec-kitty-runtime version (0.4.0 through 0.4.5) requires spec-kitty-events==4.0.0; this may mean runtime 4.0.0-compatible release is forthcoming or the runtime pin should be loosened (e.g., `>=0.4.3`) so pip can resolve. The implementer should investigate whether a compatible runtime version exists or coordinate the runtime bump alongside this WP.

**How to fix:** Check whether a `spec-kitty-runtime` release that lists `spec-kitty-events>=4.0.0` or `==4.0.0` exists (currently versions 0.4.0–0.4.5 only support events up to 3.3.0). Options:
1. If a compatible runtime release exists on PyPI, bump `spec-kitty-runtime` to that version in `pyproject.toml`.
2. If no compatible runtime release yet exists, the events bump may need to be coordinated with a runtime release, or the runtime pin in `pyproject.toml` should be relaxed to allow `pip` to pick the installed 0.4.3 (which requires events==3.0.0 and is already installed at 4.0.0 on this machine without complaint from the runtime itself).
3. Document the chosen resolution in the commit message.

**Note on pre-existing test failure:** `tests/audit/test_no_legacy_agent_profiles_path.py::test_no_legacy_agent_profiles_path_literals_in_active_codebase` fails but is pre-existing (hits `docs/assets/spec-kitty-backlog.html`, which is unchanged by this WP). This is not a regression from the dep bump.

**Everything else passed:**
- T001: pyproject.toml shows `spec-kitty-events==4.0.0` correctly.
- T002: Vendored tree at `src/specify_cli/spec_kitty_events/` contains all required 4.0.0 types (`DecisionPointOpenedInterviewPayload`, `DecisionPointWidenedPayload`, `OriginSurface`, `DECISION_POINT_WIDENED`, etc.).
- T003: Zero legacy DecisionPoint emitter calls outside the vendored tree.
- Relative imports: Zero absolute `from spec_kitty_events` imports in the vendored tree.
- sync patches: `emitter.py` and `diagnose.py` have correct minimal fallbacks for the new required 4.0.0 Event fields (`build_id`, `project_uuid`, `correlation_id`).
- Scope: Only `pyproject.toml`, `src/specify_cli/spec_kitty_events/**`, `src/specify_cli/sync/emitter.py`, `src/specify_cli/sync/diagnose.py` were modified.
- Test suite (excluding pre-existing failure): 1425 sync tests pass; overall suite passes on all WP01-relevant code paths.
