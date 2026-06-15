---
work_package_id: WP08
title: '#1916 accept-gate ensure_identity off the readiness path'
dependencies: []
requirement_refs:
- FR-008
- FR-009
tracker_refs: []
planning_base_branch: mission/mission-identity-seam-and-1908-panel
merge_target_branch: mission/mission-identity-seam-and-1908-panel
branch_strategy: Planning artifacts for this mission were generated on mission/mission-identity-seam-and-1908-panel. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/mission-identity-seam-and-1908-panel unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-mission-identity-seam-and-1908-panel-01KV6510
base_commit: f5c3301699713f5a2f75de64d3f243f6b808e23b
created_at: '2026-06-15T18:59:22.555914+00:00'
subtasks:
- T033
- T034
- T035
- T036
phase: Phase 3 - Cluster B
assignee: ''
agent: claude
shell_pid: '1021252'
history:
- at: '2026-06-15T17:53:20Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/acceptance/
create_intent:
- tests/specify_cli/cli/commands/test_accept_readiness_no_write.py
execution_mode: code_change
owned_files:
- src/specify_cli/acceptance/__init__.py
- src/specify_cli/sync/events.py
- src/specify_cli/identity/project.py
- tests/specify_cli/cli/commands/test_accept_readiness_no_write.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP08 – #1916 accept readiness side-effect-free

## ⚡ Do This First: Load Agent Profile
`/ad-hoc-profile-load` → `python-pedro` (implementer, claude).

---

## Objectives & Success Criteria
The accept `--no-commit`/readiness path must be **side-effect-free**: it must NOT mint/persist
project identity into `.kittify/config.yaml`. Move `ensure_identity`'s *write* off the readiness
path to a write-authorized boundary, then **retire the #1908 stopgap**
`_filter_accept_owned_project_config`. Read [spec.md](../spec.md) FR-008/FR-009,
[research.md](../research.md) R4 (Cluster B), [plan.md](../plan.md) IC-06.

**Done when:** a first `accept --no-commit` run on a project with incomplete identity leaves
`.kittify/config.yaml` **unchanged** (no write); the dirty-exclusion stopgap and its caller are gone;
accept readiness produces a stable verdict across two runs without the exclusion.

## Context & Constraints
- TDD-first. Only the 4 named files. Independent of the seam (no WP01 dependency).
- **Root cause (already documented in `acceptance/__init__.py:63-75`):** accept readiness emits a
  sync event → `sync/events.get_emitter()` (`:157`) eagerly calls
  `identity.project.ensure_identity(repo_root)` (`:174-177`), which **writes**
  `.kittify/config.yaml` when identity is incomplete. In `--no-commit`/diagnose mode that write is
  never folded into a commit, so the second-run `git_dirty` snapshot trips on a file the gate itself
  wrote. PR #1908 papered over it with `_filter_accept_owned_project_config` (`:581`, called `:1080`).
- **The clean seam already exists:** `identity/project.py` has a read-only `load_identity(config_path)`
  (`:~285`) that never writes, vs the writing `ensure_identity` (`:299`). The readiness/emitter path
  should use the read-only loader (tolerating an incomplete in-memory identity); the *write* belongs
  only at a write-authorized boundary (e.g. `init`, or a commit-authorized accept).
- **HIGH CARE — no-op-stability pattern (#1914):** do not merely relocate the write so it still fires
  on readiness. The acceptance criterion is that readiness performs **zero** config writes. Preserve
  the existing identity *availability* for emitted events (read-only/in-memory is acceptable on the
  readiness path; full persistence happens only where a write is authorized).
- Keep the `ACCEPT_OWNED_PATHS` exclusions for genuinely accept-owned artifacts
  (`acceptance-matrix.json`, `status.json`) — those are a different, legitimate class. Only the
  *project-config* exclusion (`_filter_accept_owned_project_config`) is the stopgap being retired.

## Subtasks
### T033 — Failing regression (#1916) — RED requires two explicit preconditions
Create `tests/specify_cli/cli/commands/test_accept_readiness_no_write.py`. **Squad note — without
these the test is green-from-start:** (1) the fixture project's `.kittify/config.yaml` MUST have
**provably-incomplete** identity (assert a required `project.*` field is missing) — `ensure_identity`
returns early WITHOUT writing when identity is already complete, so a default/complete fixture never
reproduces the bug; (2) the emitter is a **process-global double-checked singleton** that calls
`ensure_identity` only on FIRST init — call `reset_emitter()` (or equivalent) before the readiness run
so the eager-init path is actually hit. Then: snapshot `.kittify/config.yaml` mtime+content, run the
accept readiness/`--no-commit` path, assert the file is **byte-unchanged**. With today's code this
FAILS (the gate writes identity, masked only by the filter). Also assert two consecutive readiness
runs yield the same verdict **without** `_filter_accept_owned_project_config`.

### T034 — Stop the write on the READINESS CALL PATH (not globally)
**Squad note:** do NOT thread a `persist=False` flag through the global `get_emitter()` — it is the
shared singleton; a global read-only flag either only affects the first caller to win the lock
(non-deterministic) or makes identity read-only for ALL callers (scope creep beyond #1916). Instead
make the *acceptance readiness path itself* not trigger a persisting identity mint — e.g. route its
identity access through the read-only `load_identity` (no write), or have readiness emit through a
read-only/diagnose context. Keep the writing `ensure_identity` for write-authorized boundaries
(`init`, commit-authorized accept). Add a POSITIVE test that a non-readiness / write-authorized emit
STILL persists identity (proves the write was scoped, not globally killed). Identity must remain
*available* in-memory on the readiness path (event emission not regressed).

### T035 — Retire the stopgap
Remove `_filter_accept_owned_project_config` (`acceptance/__init__.py:581`) **and** its call site
(`:1080`), plus the now-stale `_PROJECT_CONFIG_RELPATH` constant and the explanatory comment block
(`:63-75`) if they are no longer referenced. The git-dirty gate must again see
`.kittify/config.yaml` verbatim — which is now safe because readiness no longer writes it.

### T036 — Gates
`ruff`+`mypy`; `PWHEADLESS=1 pytest tests/specify_cli/cli/commands/test_accept_readiness_no_write.py
tests/specify_cli/ -k accept -q` (run the accept-readiness + acceptance suites).
- [ ] readiness leaves `.kittify/config.yaml` unchanged; [ ] stopgap + caller removed; [ ] two-run
  verdict stable without the filter; [ ] ruff/mypy clean.

## Branch Strategy
Planning base / merge target: `mission/mission-identity-seam-and-1908-panel`; lane-per-WP.

## Definition of Done
Accept readiness writes nothing to `.kittify/config.yaml`; `ensure_identity` write happens only at a
write-authorized boundary; `_filter_accept_owned_project_config` + caller retired; regressions green.

## Reviewer Guidance
Confirm: (1) the regression genuinely reproduces the config write **before** the fix (verify red);
(2) readiness performs zero config writes after the fix (not just a relocated/re-filtered write);
(3) `_filter_accept_owned_project_config` and its `:1080` caller are gone, and the dirty gate no
longer special-cases project config; (4) emitted-event identity is still available (in-memory ok).
Reject if the write was merely moved but still fires on the readiness path.
