# Post-acceptance integration review — reviewer-renata (opus subagent), 2026-06-11

**Scope:** the post-acceptance integration-fix diff on lane-j (landed as `8eb9b154e`, plus the same-class
post-merge follow-up `f4ce12537`). Context: after `spec-kitty accept`, 3 mission-introduced architectural
gate failures were found on the integrated tree (absent on the plain base branch, save one prior-debt
symbol): 13 `mission_runtime.context` submodule imports, one raw `KITTY_SPECS_DIR` path construction in
`agent/mission.py` (WP05), and `commit_guard::GuardVerdict` unimported.

## VERDICT: APPROVE

The uncommitted integration-fix diff correctly resolves all three mission-introduced architectural gate
failures, is behavior-preserving, and introduces no new debt. Every claim in the briefing was independently
verified.

### Findings

**1. Constructor-move semantics — EXACT path equivalence confirmed (the judgment call).**
- `src/specify_cli/missions/_read_path_resolver.py:384` — new `primary_feature_dir_for_mission` body is
  `get_main_repo_root(repo_root) / KITTY_SPECS_DIR / mission_slug`, character-for-character identical to
  the original inline construction.
- `src/specify_cli/core/paths.py:282-322` — `get_main_repo_root` is a pure git-pointer dereference (reads
  `.git`, follows worktree gitdir to main repo root). It does NOT consult CWD and does NOT call any
  topology-aware resolver. The function is therefore topology-invariant by construction.
- The new function **cannot accidentally become topology-aware**: it never calls
  `resolve_mission_read_path` / `candidate_feature_dir_for_mission`. The docstring explicitly documents the
  topology-blind contract and the F-001/FR-003 rationale.
- Call-site `src/specify_cli/cli/commands/agent/mission.py:2418` passes the same `repo_root` (from
  `locate_project_root()`) and `mission_slug` (`feature_dir.name`) the inline version used. The F-001
  finalize-idempotency invariant is preserved. The WP05/T020 rationale comment is retained.

**2. Import swaps — clean, no circular hazard.**
- `src/mission_runtime/__init__.py` re-exports both `CommitTarget` and `CommitTargetKind` (imported from
  `.context`, listed in `__all__`). All 13 swaps resolve.
- Spot-checked `commit_guard.py:63`, `tasks.py:47`, `safe_commit_cmd.py:31`, `runtime_bridge.py:157` — all
  correct.
- No circular-import risk: `mission_runtime/__init__` imports only `.context` + `.resolution` at module
  load; every `specify_cli.*` import in `resolution.py` is function-body-deferred. None of the 13 modules
  is imported by `mission_runtime` at import time.

**3. `__all__` trim — breaks nothing.**
- Both constants remain module-level (`_read_path_resolver.py:33-34`). `MISSION_AMBIGUOUS_SELECTOR_CODE` is
  still used internally (default `error_code`), so it is not dead.
- Only external importer is `tests/specify_cli/missions/test_read_path_handle_resolution.py:27` — a direct
  attribute import unaffected by `__all__` (which governs only `import *`). Test passes (4/4).
- `FEATURE_CONTEXT_UNRESOLVED_CODE` has no importer outside the module.

**4. GuardVerdict wiring — legitimate, ratchet-permitted.**
- `commit_guard.py:136` declares `evaluate(...) -> GuardVerdict`; the annotation at `commit_helpers.py:915`
  (`guard_verdict: GuardVerdict = evaluate_commit_guard(...)`) is the documented public return type —
  genuine wiring, not gate-gaming.
- WP10 ratchet `tests/architectural/test_safe_commit_import_boundary.py:48-50` explicitly whitelists
  `GuardVerdict` as a free-to-import public value type; only the `evaluate` *function* is boundary-gated,
  and `commit_helpers.py` is already a blessed `evaluate` importer. Ratchet passes.

**5. Scope check — clean.** `git diff --stat` shows exactly the 15 described files (13 one-line import
swaps, `commit_helpers.py` +import +annotation, `_read_path_resolver.py` new function + `__all__` trim,
`mission.py` call-site swap). Nothing extraneous.

### Gate outputs (counts, independently re-run by the reviewer)

| Gate | Result |
|------|--------|
| `tests/architectural/` | 332 passed (lane-j tree; 334 on the merged tree after `f4ce12537`) |
| dead-symbols + surface + raw-paths + ratchet (targeted) | 17 passed |
| protection-preserved + commit-guard suites | 41 passed |
| `test_read_path_handle_resolution.py` | 4 passed |
| finalize regression (`test_mission_finalize_tasks.py` + `test_sc6_planning_placement_e2e.py`) | 21 passed, 2 pre-existing xfail |
| `ruff check` (15 files) | clean |
| `mypy _read_path_resolver.py` | clean |

### Non-blocking note (NOT introduced by the diff)
`mypy src/specify_cli/git/commit_helpers.py` reports 2 `[no-any-return]` errors at lines 759-760 inside
`_resolve_build_id`. Verified against `git show HEAD:` that both exist identically on the committed lane
base, entirely outside the diff hunks. Pre-existing debt, does not block. (Same class: 6 pre-existing
`mypy` errors in `status/aggregate.py`, verified unchanged by the one-line import swap in `f4ce12537`.)

---
*Recorded by the orchestrator from the subagent's verbatim return; the same fix classes (import swap to
package root, pytestmark additions) were re-applied post-merge for lanes outside lane-j's reach
(`status/aggregate.py` + 5 test files) in `f4ce12537` under this approval's umbrella.*
