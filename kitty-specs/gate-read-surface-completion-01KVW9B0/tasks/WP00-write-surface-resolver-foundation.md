---
work_package_id: WP00
title: Write-surface resolver foundation — re-point commit/branch resolution onto the primary/kind-aware seam
dependencies: []
requirement_refs:
- FR-004
- FR-009
tracker_refs:
- '#2107'
- '#2085'
planning_base_branch: feat/gate-read-surface-completion
merge_target_branch: feat/gate-read-surface-completion
branch_strategy: Planning artifacts for this mission were generated on feat/gate-read-surface-completion. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/gate-read-surface-completion unless the human explicitly redirects the landing branch.
subtasks:
- T000a
- T000b
- T000c
- T000d
- T000e
phase: Phase 0 - Write-surface foundation (implemented FIRST, unblocks the implement loop)
assignee: ''
agent: claude
shell_pid: "0"
history:
- at: '2026-06-24T15:40:00Z'
  actor: system
  action: Prompt generated via post-tasks adversarial-squad remediation (planner-priti)
agent_profile: python-pedro
authoritative_surface: src/specify_cli/core/
create_intent:
- tests/specify_cli/core/test_write_surface_resolver_foundation.py
- tests/specify_cli/cli/commands/agent/test_finalize_tasks_commit_surface.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/core/paths.py
- src/specify_cli/core/git_ops.py
- tests/specify_cli/core/test_write_surface_resolver_foundation.py
- tests/specify_cli/cli/commands/agent/test_finalize_tasks_commit_surface.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP00 – Write-surface resolver foundation

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter
**before parsing the rest of this prompt**, and behave according to its guidance.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If the profile cannot be loaded, run `spec-kitty agent profile list` and select the
best match for `task_type: implement` on `authoritative_surface: src/specify_cli/core/`.

---

## Objective

**Fix the write-side surface-resolution twin of this mission's read-side consolidation,
implemented FIRST so the editable CLI is correct and the implement loop is unblocked.**

The read side (WP01–WP06) re-points planning *reads* onto the kind-aware
`resolve_planning_read_dir` seam. This WP re-points the planning *write / commit-branch
resolution* onto the **primary** surface — the WRITE twin (FR-004 anti-"resolution to the
repo primary", FR-009(e) finalize-tasks commit). Without it, **`spec-kitty implement WP##`
and `finalize-tasks` both misresolve their commit/planning branch to the protected repo
primary `main`** and refuse to proceed (live dogfood repro). This is a chicken-and-egg
blocker: until it is fixed in the live editable CLI, no other WP can run its implement loop.

### The bug (live-verified, debugger-debbie post-tasks finding)

Three call sites resolve a mission's `meta.json` via `candidate_feature_dir_for_mission`,
which under coord topology resolves to the **coordination worktree** — whose mission dir
holds only `status.events.jsonl` / `status.json`, **no `meta.json`**. The lookup finds
nothing and silently falls back to `resolve_primary_branch()` → the repo primary `main`:

| # | File:line | Symbol | Current (buggy) | Fix |
|---|-----------|--------|-----------------|-----|
| 1 | `src/specify_cli/core/paths.py:617` | `get_feature_target_branch` | `candidate_feature_dir_for_mission(main_root, slug) / "meta.json"` | `primary_feature_dir_for_mission(...)` |
| 2 | `src/specify_cli/core/git_ops.py:371` | `resolve_target_branch` | `candidate_feature_dir_for_mission(repo_path, slug) / "meta.json"` | `primary_feature_dir_for_mission(...)` |
| 3 | `mission.py` (finalize-tasks COMMIT, site #14) | the finalize-tasks commit-branch resolution | resolves protected primary `main` instead of `target_branch` | route via the same primary/kind-aware write seam |

**Canonical reference fix already in the tree (do NOT invent a new pattern):**
`resolve_merge_target_branch` at `src/specify_cli/core/paths.py:630-675` was ALREADY
corrected for this exact class — it reads `primary_feature_dir_for_mission(main_root, slug)
/ "meta.json"` and its docstring (`:642-646`) documents the precise failure mode:

> "Under coordination topology that candidate resolves to the coordination worktree, whose
> mission dir has no meta.json; reading it found nothing and silently fell back to the repo
> default (main), merging the mission into the wrong branch."

WP00 brings `get_feature_target_branch`, `resolve_target_branch`, and the finalize-tasks
commit onto that already-proven seam. **Unification, not parity** — the
`candidate_feature_dir_for_mission` write-resolution is the mess to remove, not a contract
to preserve. (See standing memory: *unification not parity*.)

## Context & Constraints

Ground truth — read before editing:
- [spec.md](../spec.md) FR-004 (the anti-"resolution to the repo primary" clause + the
  finalize-tasks COMMIT in the residual-site list), FR-009(e) (the finalize-tasks
  commit-surface is the write-side twin, must resolve via the same kind-aware seam).
- [data-model.md](../data-model.md) site-map **row 14** (`finalize-tasks` COMMIT,
  RESIDUAL — write-side, IC-01/04).
- [contracts/gate-read-seam.md](../contracts/gate-read-seam.md) **G-6** (the write-surface
  clause added by this remediation) + the ratchet write arm.
- [research/dogfood-finalize-tasks-repro.md](../research/dogfood-finalize-tasks-repro.md)
  — the live repro: finalize-tasks refused to commit ("Refusing to commit planning
  artifacts to the protected branch 'main'") because it resolved its planning-commit
  surface to `main` instead of `feat/...`. Flatten did NOT help — it is the COMMIT-surface,
  not topology.
- [research/debbie-posttasks.md](../research/debbie-posttasks.md) — the precise fix
  targets, the chicken-and-egg analysis (implement loop is blocked by the SAME bug), and
  the falsified hypotheses (it is `paths.py:617`, not the read-side seam).

**The reference:** `paths.py:630-675` `resolve_merge_target_branch` — copy its
deferred-import shape (`core.paths` is imported very early; module-level imports of the
`missions`/`git` layers form a circular import — use the same in-function imports the
reference uses) and its `primary_feature_dir_for_mission` anchoring.

**Negative scope:**
- Do NOT introduce a new resolver (C-001). Re-point onto the existing
  `primary_feature_dir_for_mission` / the kind-aware write seam.
- Do NOT change the STATUS/coord write destinations (status events still emit to coord —
  C-002/C-003). This WP only fixes the **planning commit/branch** resolution.
- Do NOT touch the read-side seam (WP01–WP06 own that).
- Forward-only (C-004); behavior-neutral for flattened missions (NFR-001) — a flattened
  mission already has `meta.json` on the only checkout, so the fix is a no-op there.

## Branch Strategy

- **Strategy**: `foundation-lane` (Phase 0 — lands FIRST; the editable CLI must be correct
  before any other WP can run its implement loop).
- **Planning base branch**: `feat/gate-read-surface-completion`
- **Merge target branch**: `feat/gate-read-surface-completion`

> WP00 OWNS `src/specify_cli/core/paths.py` and `src/specify_cli/core/git_ops.py`
> exclusively (no other WP touches `core/`). The finalize-tasks COMMIT fix is a
> **justified out-of-map edit** to `src/specify_cli/cli/commands/agent/mission.py`
> (which WP01 owns). See **Ownership / out-of-map note** below.

### Ownership / out-of-map note for the `mission.py` finalize-tasks edit

WP01 OWNS `mission.py`. WP00's finalize-tasks COMMIT fix (T000c) is a small, well-justified
out-of-map edit to `mission.py`. It is auto-merge-safe and serialized:

- **Disjoint regions (auto-merge safe):** the finalize-tasks commit/branch resolution lives
  in `_resolve_feature_target_branch` (`mission.py:482`), `_resolve_planning_branch`
  (`mission.py:981` → `load_mission_target_branch`), and the `finalize_tasks` body
  (`mission.py:2806+`). **None of these are adjacent to** WP01's chokepoint helpers
  (`_ARTIFACT_TYPE_TO_KIND`/`_artifact_kind_for`/`_planning_read_dir` at `~1106-1357`),
  WP02's `setup_plan` (`:2044`), or WP04's `record_analysis` (`:1898`). They are hundreds
  of lines apart on different functions → git 3-way auto-merge succeeds.
- **Serialization:** WP00 has `dependencies: []` and lands **before** WP01 (WP01 depends on
  WP00). So WP01 branches from a base that **already contains** WP00's finalize-tasks edit
  — no conflicting concurrent edit to the same `mission.py` region. If, at implement time,
  the finalize-tasks commit fix turns out to touch a helper that WP01 also narrows, land
  WP00 → WP01 strictly sequentially (the dependency edge already enforces this).
- **Rationale recorded:** this out-of-map `mission.py` edit is FR-009(e) (site #14), which
  has no other owner; assigning it to WP00 keeps the write twin a first-class,
  separately-reviewable site (alphonso/paula post-tasks: site #14 was UNOWNED).

## Subtasks & Detailed Guidance

### Subtask T000a – Red-first: drive the REAL write-resolution entry points (NFR-002)

- **Purpose**: Prove RED on the current (buggy) resolver — it resolves `main` for a
  coord-topology mission — through the PRE-EXISTING entry points, not a new API.
- **Files**: new `tests/specify_cli/core/test_write_surface_resolver_foundation.py`.
- **Steps (red-first — DIRECTIVE_034 / NFR-002)**:
  1. Build a **coord-topology** fixture (composed `<slug>-<mid8>` primary dir, real ULID
     `01KVW9B0XFXPKTBE77QT3KRSW8` / mid8 `01kvw9b0`): primary checkout dir
     `gate-read-surface-completion-01kvw9b0/` containing `meta.json` with
     `target_branch: feat/gate-read-surface-completion` and a `coordination_branch` set;
     a materialized coordination worktree whose mission dir holds ONLY
     `status.events.jsonl` / `status.json` (**no `meta.json`**) — the exact shape debbie
     reproduced.
  2. Drive the real entry points (NOT a new helper):
     - `get_feature_target_branch(repo_root, mission_slug)` (`paths.py:599`)
     - `resolve_target_branch(mission_slug, repo_path, current_branch, respect_current=...)`
       (`git_ops.py:331`)
  3. Assert **RED on current code**: both return `main` (the protected primary) instead of
     `feat/gate-read-surface-completion`.
  4. **Prove RED against the unfixed resolver**: run the test on the pre-WP00 tree (it
     passes the "returns main" red assertion); record the evidence. After the T000b fix,
     flip the assertion to GREEN (`target_branch`).
- **Notes**: NEVER use a bare-slug primary dir — a bare-slug fixture is canonicalized and
  masks the coord/primary divergence (false green). Use the composed `<slug>-<mid8>` dir.

### Subtask T000b – Fix `get_feature_target_branch` + `resolve_target_branch`

- **Purpose**: Re-point both write-side resolvers onto `primary_feature_dir_for_mission`.
- **Files**: `src/specify_cli/core/paths.py:617`, `src/specify_cli/core/git_ops.py:371`.
- **Steps**:
  1. `paths.py:614-617` — change the import + lookup:
     ```python
     from specify_cli.missions._read_path_resolver import primary_feature_dir_for_mission
     ...
     meta_file = primary_feature_dir_for_mission(main_root, mission_slug) / "meta.json"
     ```
     Mirror `resolve_merge_target_branch` (`:658,:665`) exactly — same deferred import,
     same anchoring.
  2. `git_ops.py:369-371` — same change: import `primary_feature_dir_for_mission`, anchor
     the `meta.json` lookup to it instead of `candidate_feature_dir_for_mission`.
  3. Preserve every existing fallback/except path (missing/corrupt meta.json → primary
     branch) byte-for-byte — only the dir-resolution primitive changes.
- **Notes**: `candidate_feature_dir_for_mission` may have no remaining callers in these two
  modules after the change — leave the symbol (other modules import it for genuine
  topology-aware reads); only stop using it for the **write-branch** lookup.

### Subtask T000c – Fix the finalize-tasks COMMIT (site #14, FR-009(e))

- **Purpose**: Route the finalize-tasks planning-artifact COMMIT branch via the
  primary/kind-aware write seam so it commits to `target_branch`, not protected `main`.
- **Files**: `src/specify_cli/cli/commands/agent/mission.py` (the finalize-tasks
  commit/branch resolution: `_resolve_feature_target_branch:482`,
  `_resolve_planning_branch:981` / `load_mission_target_branch`, and/or the
  `finalize_tasks` body at `2806+` — **trace the actual resolution at implement time**;
  the dogfood repro is the authority that it lands on `main`). **Out-of-map edit — see the
  ownership note above.**
- **Steps**:
  1. Find where finalize-tasks resolves the branch it commits planning artifacts to. The
     two candidates: (a) `_resolve_feature_target_branch` reads meta off the
     topology-resolved `feature_dir` (coord → no meta.json → falls through to
     `get_current_branch`/`main`); (b) the commit uses `get_feature_target_branch`
     (fixed transitively by T000b). Confirm which path the live repro exercises (drive
     `finalize_tasks` per T000d and observe the resolved branch).
  2. Re-point the resolution so it reads `meta.json` from the **primary** surface
     (`primary_feature_dir_for_mission`) — i.e. the finalize-tasks COMMIT resolves
     `target_branch` for a coord-topology mission, identical to how the planning reads now
     resolve primary. If T000b's `get_feature_target_branch` fix already routes it
     correctly, T000c reduces to a regression test (T000d) + an assertion in the audit; do
     NOT add a redundant resolution.
  3. Preserve the #2106 FR-008 protected-primary guard (it correctly refuses `main`) — the
     fix is the resolution to `main`, NOT the guard.
- **Notes**: Do NOT change the status/coord commit destination (C-002/C-003). Only the
  planning-artifact COMMIT branch is re-pointed.

### Subtask T000d – Red-first regression test: finalize-tasks COMMIT → `target_branch`

- **Purpose**: Lock site #14 with a scenario-driving guard through the real entry point.
- **Files**: new
  `tests/specify_cli/cli/commands/agent/test_finalize_tasks_commit_surface.py`.
- **Steps (red-first)**:
  1. Coord-topology composed `<slug>-<mid8>` fixture (as T000a). Drive `finalize_tasks(...)`
     (the pre-existing CLI entry point) — NOT a new helper.
  2. Assert the resolved commit branch is `feat/gate-read-surface-completion`
     (`target_branch`), and the commit is NOT refused with "Refusing to commit … protected
     branch 'main'". RED on pre-WP00 code (resolves/refuses `main`); GREEN after.
  3. If driving the full commit is heavy, assert on the **resolved branch** the commit path
     computes (mock the git commit, capture the target ref) — still through `finalize_tasks`,
     not a private resolver. Record red-run evidence.
  4. Real ULID/mid8; no bare-slug.

### Subtask T000e – FR-004/FR-009(e) write-side audit

- **Purpose**: Prove no surviving write-branch resolution lands on the repo primary via
  `candidate_feature_dir_for_mission` (the consolidation, write side).
- **Files**: (audit, recorded in the activity log — no new logic).
- **Steps**:
  1. Grep `core/paths.py`, `core/git_ops.py`, and the finalize-tasks region of `mission.py`
     for `candidate_feature_dir_for_mission` feeding a **branch/commit** resolution — each
     must now anchor to `primary_feature_dir_for_mission`.
  2. Record the audit result so WP06's ratchet author (write arm) knows the consolidated
     write-side baseline. Note this WP covers WP06's write-arm territory in product code;
     WP06 fences it.

## Test Strategy

- `pytest tests/specify_cli/core/test_write_surface_resolver_foundation.py tests/specify_cli/cli/commands/agent/test_finalize_tasks_commit_surface.py -q`.
- Red-first evidence for BOTH the resolver and the finalize-tasks commit (run against the
  unfixed code, observe `main`, then GREEN after).
- `ruff check src/specify_cli/core/paths.py src/specify_cli/core/git_ops.py` +
  `mypy` on the touched files and the `mission.py` region — zero issues, no suppressions.
- After landing, **reinstall the editable CLI** (`pip install -e .` if not already live)
  so the implement loop for WP01+ sees the fix (this is the unblock).

## Definition of Done

- [ ] `get_feature_target_branch` (`paths.py:617`) anchors its `meta.json` lookup to
  `primary_feature_dir_for_mission` (mirrors `resolve_merge_target_branch:665`).
- [ ] `resolve_target_branch` (`git_ops.py:371`) anchors its `meta.json` lookup to
  `primary_feature_dir_for_mission`.
- [ ] The finalize-tasks COMMIT (site #14) resolves `target_branch` (not protected `main`)
  for a coord-topology mission; the #2106 protected-primary guard preserved.
- [ ] Red-first tests via the REAL entry points (`get_feature_target_branch`,
  `resolve_target_branch`, `finalize_tasks`) — RED on unfixed code (resolves `main`),
  GREEN after; composed `<slug>-<mid8>` fixtures, real ULID/mid8 (NFR-002).
- [ ] Flattened-mission behavior unchanged (NFR-001 — no-op there).
- [ ] FR-004/FR-009(e) write-side audit recorded: no write-branch resolution survives via
  `candidate_feature_dir_for_mission`.
- [ ] `mission.py` finalize-tasks edit recorded as a justified out-of-map edit with the
  WP01 serialization note.
- [ ] ruff + mypy clean; no suppressions. Editable CLI reinstalled (the implement-loop
  unblock).

## Risks & Mitigations

- **Chicken-and-egg (the unblock):** the implement loop for WP01+ is blocked by THIS bug.
  Mitigation: WP00 lands FIRST (root dependency of WP01/WP07/WP08/WP09); reinstall the
  editable CLI immediately after T000b/T000c so subsequent WPs run normally.
- **Wrong resolution target for site #14:** the finalize-tasks commit may resolve via a
  different path than `get_feature_target_branch`. Mitigation: T000c step 1 traces the live
  path via the `finalize_tasks` entry point; the dogfood repro is the authority.
- **Out-of-map `mission.py` collision with WP01:** Mitigation: disjoint functions
  (`_resolve_feature_target_branch:482`/`_resolve_planning_branch:981`/`finalize_tasks:2806+`
  vs WP01's `~1106-1357`); WP00 lands before WP01 via the dependency edge.
- **Over-reach into status/coord writes:** Mitigation: only the planning commit/branch
  resolution moves; status events still emit to coord (C-002/C-003).

## Review Guidance

- Confirm both resolvers anchor to `primary_feature_dir_for_mission` and mirror the
  already-proven `resolve_merge_target_branch` reference — no new resolver (C-001).
- Confirm the red-first tests drove the REAL entry points and proved RED on the unfixed
  resolver (resolves `main`) — ask for the red-run evidence. A test green-before-and-after
  captures nothing.
- Confirm the finalize-tasks COMMIT resolves `target_branch` for a coord-topology fixture
  and the protected-primary guard is preserved (the fix is the resolution, not the guard).
- Confirm the editable CLI was reinstalled (the implement-loop unblock is the WP's reason
  to exist).
- Confirm the `mission.py` out-of-map edit carries the rationale + WP01 serialization note.

## Activity Log

- 2026-06-24T15:40:00Z – system – Prompt created (post-tasks adversarial-squad remediation;
  write-side foundation per operator decision).
- 2026-06-24T14:55:33Z – user – Bootstrap WP00 implemented directly on feat (loop was dogfood-blocked)
- 2026-06-24T14:55:34Z – user – Write-surface resolver fix landed (3a16473a2)
- 2026-06-24T14:55:36Z – claude – paths.py/git_ops.py candidate→primary + finalize-tasks transitively fixed; red-first RED→GREEN, ruff/mypy clean, CLI unblock verified
- 2026-06-24T15:02:25Z – user – Review passed: src fix mirrors proven resolve_merge_target_branch (candidate->primary_feature_dir_for_mission, only dir primitive swapped, fallbacks byte-preserved, no STATUS/coord over-reach C-002/C-003). Red-first VERIFIED by reviewer: reverted src to candidate, 5/6 coord-topology tests RED (resolve 'main' incl literal dogfood refusal), restored GREEN. finalize-tasks site#14 transitively fixed via resolve_placement_only reading get_feature_target_branch (no redundant resolution, no mission.py edit). T000e audit clean. ruff+mypy clean no suppressions. Scope=4 owned files. CLI unblock confirmed. 8 core regression tests green.
