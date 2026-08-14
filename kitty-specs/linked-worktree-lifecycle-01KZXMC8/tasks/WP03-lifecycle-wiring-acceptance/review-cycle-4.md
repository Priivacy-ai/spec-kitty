---
affected_files: []
cycle_number: 4
mission_slug: linked-worktree-lifecycle-01KZXMC8
reproduction_command:
reviewed_at: '2026-08-14T06:00:56Z'
reviewer_agent: reviewer-renata
wp_id: WP03
---

# WP03 review cycle 4 — REQUEST_CHANGES

## Blocking finding

`src/specify_cli/cli/commands/agent/tasks_shared.py:305` introduces a functional raw Mission-path join:

```python
repo_root / KITTY_SPECS_DIR / raw_handle / "meta.json"
```

This bypasses the canonical Mission resolver/placement boundary. The existing repo architectural contract detects it:

```text
tests/architectural/test_single_mission_surface_resolver.py::test_zero_functional_raw_bypass_on_collapsed_tree
Unexpected raw KITTY_SPECS_DIR/slug path joins detected.
specify_cli/cli/commands/agent/tasks_shared.py:305 key=('_find_mission_slug', 'repo_root')
```

Reproduction:

```powershell
uv run --with pytest --with pytest-timeout python -m pytest tests/mission_runtime/test_dual_root_mission_placement.py tests/specify_cli/missions/test_operation_context.py tests/specify_cli/cli/commands/agent/test_tasks_canonical_cleanup.py tests/specify_cli/cli/commands/agent/test_tasks_finalize_seam.py tests/architectural/test_single_mission_surface_resolver.py --confcutdir=tests --timeout=60 -q
```

Observed: `1 failed, 61 passed`. `git blame` attributes the raw join to cycle-4 commit `336e3ef7c`; it is not a baseline failure.

## Required correction

Route the legacy no-`meta.json` compatibility check through an existing canonical resolver/placement surface, or add a narrowly justified reviewed exception only if the path is demonstrably topology-blind by design. Extend the dynamic cycle-4 guard so this path-join bypass class cannot escape its repo-wide census. The existing `test_single_mission_surface_resolver.py` gate must pass.

## Confirmed non-blocking evidence

- Production caller-owned lifecycle: `13 passed` (`mark-status`, real `move-task` to `for_review`, review claim, real `move-task` to `approved`, `next`, `accept`; primary snapshot unchanged).
- Dynamic root-authority guard: `3 passed`; source census is `src/**/*.py`, static shrink-only allowlist, mutation in `mission_branch_context.py`.
- Changed-file Ruff and py_compile: pass.
- Codemap JSON/HTML parity: 8 nodes / 16 edges; both SHA-256 lock entries exact.
- Scoped task/status set: `241 passed` plus one unrelated Windows separator baseline in unchanged `test_tasks_move_task_pre_review_gate_observability.py:618`.
- Pre-review collection error at `test_sync_doctor_consent_health_3030.py:498` reproduces on Windows because `os.geteuid` is absent; file and line are unchanged from base.
- Strict mypy over all eight touched source files reports six errors, all on unchanged blamed lines predating this WP; no new typed-surface regression was found.

## Anti-pattern checklist

- Dead code: no new unreachable production surface found.
- Synthetic-only acceptance: previous blocker resolved by real production CLI lifecycle.
- Silent empty fallback: no new silent success found.
- Requirement coverage: caller-owned lifecycle is covered, but architectural SSOT coverage remains incomplete because the new census misses raw path joins.
- Frozen artifact integrity: not applicable.
- Locked decision compliance: blocked by the raw resolver bypass above.
- Shared ownership: no unreviewed cross-WP edit found in this delta.
- Fragility: no new broad-exception or import-fallback blocker found beyond existing compatibility seams.
