---
work_package_id: WP03
title: Consolidate the 6 retrospective home-resolution sites onto the primary-anchored authority
dependencies:
- WP01
- WP02
requirement_refs:
- FR-001
- FR-003
- FR-011
tracker_refs:
- '#2119'
- '#1771'
- '#2136'
planning_base_branch: fix/3.2.3-coord-surface-regressions
merge_target_branch: fix/3.2.3-coord-surface-regressions
branch_strategy: Planning artifacts for this mission were generated on fix/3.2.3-coord-surface-regressions. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/3.2.3-coord-surface-regressions unless the human explicitly redirects the landing branch.
subtasks:
- T031
- T032
- T033
- T034
- T035
- T036
- T037
phase: Phase 1 - Consolidation (the retrospective durable-home spine)
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1756364"
history:
- at: '2026-06-25T19:36:37Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks (planner-priti)
agent_profile: python-pedro
authoritative_surface: src/specify_cli/retrospective/
create_intent:
- tests/retrospective/test_retrospective_durable_home_coord.py
- tests/retrospective/test_home_resolution_single_authority.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/retrospective/writer.py
- src/specify_cli/retrospective/lifecycle_events.py
- src/specify_cli/post_merge/retrospective_terminus.py
- src/runtime/next/_internal_runtime/retrospective_terminus.py
- tests/retrospective/test_retrospective_durable_home_coord.py
- tests/retrospective/test_home_resolution_single_authority.py
- tests/retrospective/test_record_committable_1771.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP03 — Consolidate the 6 retrospective home-resolution sites

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter
**before parsing the rest of this prompt**, and behave according to its guidance.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If the profile cannot be loaded, run `spec-kitty agent profile list` and select the best
match for `task_type: implement` on `authoritative_surface:
src/specify_cli/retrospective/`.

---

## Objective

**Route ALL retrospective home-resolution through the ONE primary-anchored authority** so the
record lives in the durable PRIMARY home `kitty-specs/<slug>/retrospective.yaml` for **every
topology** — never the ephemeral coordination worktree. Today **6 sites** independently resolve
the home (5 via coord-aware resolvers, 1 hardcoded payload). The coord-aware resolvers select
the coordination worktree once it exists, so the record is written into `.worktrees/<slug>-coord/`
and lost on teardown. Re-point each onto `primary_feature_dir_for_mission`
gated by `is_primary_artifact_kind(RETROSPECTIVE)` (WP02).

**WP03 owns the WRITE-leg handle-canonicalization (FR-011 write half).** `primary_feature_dir_for_mission`
(`:1212`) is topology-blind by contract (it does NOT canonicalize its handle — WP01 keeps it blind to
avoid the `:418`→`:454` recursion). So each WRITE site here MUST canonicalize its handle via
`_canonicalize_bare_modern_handle` (`_read_path_resolver.py:418`) BEFORE composing through the blind
primitive — mirroring the live read-side exemplars `:1204`/`:1208`/`:820`. WP01 owns the READ-leg
canonicalization (`resolve_planning_read_dir:1306`); WP03 owns the WRITE-leg canonicalization at these
6 placement sites. Both reuse the SAME shared helper at disjoint call sites — **no `owned_files` overlap**.

## The 6 sites (live-verified on `e36547461` — re-censused against HEAD; it is 6, NOT 4)

| # | Site | Today (verified) | After |
|---|------|------------------|-------|
| 1 | `retrospective/writer.py:48` | `resolve_feature_dir_for_slug(repo_root, mission_slug)` | primary authority |
| 2 | `post_merge/retrospective_terminus.py:68` | `resolve_feature_dir_for_slug(repo_root, mission_slug)` | primary authority |
| 3 | `retrospective/lifecycle_events.py:336` | `resolve_feature_dir_for_mission(repo_root, record.mission_slug)` | primary authority |
| 4 | `retrospective/lifecycle_events.py:411` | `resolve_feature_dir_for_mission(repo_root, mission_slug)` | primary authority |
| 5 | `retrospective/lifecycle_events.py:480` | `resolve_feature_dir_for_mission(repo_root, mission_slug)` | primary authority |
| 6 | `runtime/next/_internal_runtime/retrospective_terminus.py:76` `_record_path_str` | hardcoded `repo_root / ".kittify" / "missions" / <id> / "retrospective.yaml"` | primary authority (report the ACTUAL home) |

The coord-aware resolvers being replaced are `resolve_feature_dir_for_slug` (`_read_path_resolver.py:1359`)
and `resolve_feature_dir_for_mission` (`:1393`). The replacement is
`primary_feature_dir_for_mission(repo_root, mission_slug)` (`:1212`, now handle-safe).

**LEAVE UNTOUCHED:** `writer.py:60` `_legacy_record_path` — the load-bearing `.kittify`
back-compat **read** path (records authored before #1771 still resolve through it). It is NOT a
home-resolution site. (Its `"retrospective.yaml"` literal IS hoisted later by WP06 — WP03 does
NOT touch the function.)

## Context & Constraints

Ground truth — read before editing:
- [spec.md](../spec.md) **FR-001** (placement; assert `".worktrees" not in resolved.parts`) +
  **FR-003** (6 sites, GREP/AST enumerating test) + **NFR-002** (live coord divergence) +
  **NFR-003** (flattened byte-identical) + **C-004** (read-side unchanged).
- [data-model.md](../data-model.md) the 6-site table + "Enumerating structural test".
- [contracts/terminal-artifact-teardown-contract.md](../contracts/terminal-artifact-teardown-contract.md) **C1**.
- [research.md](../research.md) **Decision 2** (it is 6 sites; the "4" was the false-green keystone).

**Negative scope:**
- Do NOT model on `resolve_status_surface` (topology-aware → reproduces the coord bug).
- Do NOT touch `writer.py:60` `_legacy_record_path` (load-bearing `.kittify` back-compat read).
- Do NOT change the read-side status access (`resolve_status_surface` — C-004).
- Do NOT hoist the filename literal here — that is WP06 (depends on WP03). WP03 changes the
  *resolver* call; WP06 changes the *literal*.

## Branch Strategy

- **Strategy**: depends on WP01 (handle-safe seam) + WP02 (the kind). Branch from a base
  containing both.
- **Planning base branch**: `fix/3.2.3-coord-surface-regressions`
- **Merge target branch**: `fix/3.2.3-coord-surface-regressions`

> WP03 OWNS `retrospective/writer.py`, `retrospective/lifecycle_events.py`,
> `post_merge/retrospective_terminus.py`, `runtime/next/.../retrospective_terminus.py`. WP06
> (FR-010 hoist) `depends: [WP03]` and edits the SAME files for the literal — that shared
> ownership is **dependency-ordered (sequential)** and therefore overlap-exempt
> (`ownership/validation.py:198-207`). WP06 lands AFTER WP03.

## Subtasks & Detailed Guidance

### Subtask T031 — Red-first live-coord behavioral test (NFR-002 — the keystone)

- **Purpose**: Prove RED — a coord-topology mission writes the retrospective into the coord
  worktree today.
- **Files**: new `tests/retrospective/test_retrospective_durable_home_coord.py`.
- **Steps (red-first — NFR-002)**:
  1. Build a **genuinely-divergent coord-topology** fixture: a composed `<slug>-<mid8>` primary
     dir with `meta.json` (real ULID/mid8), a `coordination_branch` set, AND a **materialized
     coordination worktree whose mission dir lacks `meta.json`/`lanes.json`** (the surface
     diverges from primary — the #1771 trap requires this).
  2. Drive the retrospective WRITE through the REAL entry point (`writer.py`'s
     `record_retrospective` / the lifecycle emitter — NOT a private resolver).
  3. Assert **RED on current code**: the resolved path contains `.worktrees` (the coord home).
  4. After T033–T035, flip GREEN: assert **`".worktrees" not in resolved.parts`** AND the file
     lands at `kitty-specs/<slug>/retrospective.yaml`. **`kitty-specs in parts` alone is the
     #1771 false-green and is FORBIDDEN as the assertion** (it passed flat in #1771).
  5. Record the red-run evidence.
- **Notes**: a stub resolver / bare-slug / flattened fixture is REJECTED (NFR-002) — the coord
  surface MUST genuinely diverge.

### Subtask T032 — Enumerating structural test (FR-003, GREP/AST — no hardcoded count)

- **Purpose**: Lock "no site resolves the home independently" so a 7th site fails the build.
- **Files**: new `tests/retrospective/test_home_resolution_single_authority.py`.
- **Steps**:
  1. Derive the home-resolution call-site set by **GREP or AST** over the retrospective surfaces
     (search for `resolve_feature_dir_for_slug` / `resolve_feature_dir_for_mission` /
     hardcoded `.kittify/missions/.../retrospective.yaml`). A **hardcoded count is FORBIDDEN** —
     the test must enumerate dynamically.
  2. Assert every discovered home-resolution site routes through the single authority
     (`primary_feature_dir_for_mission` gated by `is_primary_artifact_kind`).
  3. Assert that re-introducing an independent resolution (a 7th site, or reverting site #6 to
     the hardcoded payload) FAILS the test (anti-rename-vacuous).
- **Notes**: this is the guard against a rename-only "consolidation" that leaves the duplication.

### Subtask T033 — Re-point sites #1 and #2

- **Purpose**: Route the writer + post-merge terminus through the authority.
- **Files**: `retrospective/writer.py:46-48`, `post_merge/retrospective_terminus.py:65-68`.
- **Steps**:
  1. `writer.py:46-48` — swap the import + call from `resolve_feature_dir_for_slug` to
     `primary_feature_dir_for_mission(repo_root, canonical)` gated by
     `is_primary_artifact_kind(MissionArtifactKind.RETROSPECTIVE)`, where
     `canonical = _canonicalize_bare_modern_handle(repo_root, mission_slug)` (FR-011 write leg —
     the blind primitive does NOT self-canonicalize). The function's docstring (`:37-43`) already
     describes the canonical tracked path — keep it accurate.
  2. `post_merge/retrospective_terminus.py:65-68` — same swap + same canonicalize-before-compose
     (it imports `resolve_feature_dir_for_slug` at `:65`).
  3. Preserve the surrounding behavior (idempotency check, postcondition). Let
     `MissionSelectorAmbiguous` propagate (no silent pick — C-009).
- **Notes**: both currently use the *slug* resolver; the primary authority takes the same
  `(repo_root, mission_slug)` signature. Reuse the SAME `_canonicalize_bare_modern_handle` helper
  WP01 uses on the read leg — NO bespoke resolver (C-006).

### Subtask T034 — Re-point sites #3, #4, #5 (the three lifecycle emitters)

- **Purpose**: Route all three `lifecycle_events.py` emitters through the authority.
- **Files**: `retrospective/lifecycle_events.py:336`, `:411`, `:480` (import at `:27`).
- **Steps**:
  1. Replace each `resolve_feature_dir_for_mission(...)` call with the primary authority gated by
     the kind, canonicalizing the handle first via `_canonicalize_bare_modern_handle` (FR-011 write
     leg). Note `:336` passes `record.mission_slug`; `:411`/`:480` pass `mission_slug`.
  2. Update the module import at `:27` if `resolve_feature_dir_for_mission` becomes unused in the
     module (leave the symbol in `_read_path_resolver` — other modules use it for genuine
     topology-aware reads; only stop importing it HERE). Add the
     `_canonicalize_bare_modern_handle` import.
  3. Keep the FR-006 (#1771) comment blocks accurate to the new resolution.
- **Notes**: three emitters, not one (the census correction — `:336`/`:411`/`:480`). All three
  canonicalize before composing through the blind primitive.

### Subtask T035 — Re-point site #6 (the hardcoded payload string)

- **Purpose**: Make the event-payload path report the ACTUAL home, not the legacy `.kittify`.
- **Files**: `runtime/next/_internal_runtime/retrospective_terminus.py:73-76` (`_record_path_str`).
- **Steps**:
  1. `_record_path_str` today returns `repo_root / ".kittify" / "missions" / <id> /
     "retrospective.yaml"` (hardcoded). Re-point it to the primary authority so the emitted
     payload equals the actual write home.
  2. This crosses into `src/runtime/next/` — consume `primary_feature_dir_for_mission` /
     `is_primary_artifact_kind` via the public import surface (this module already imports
     `from specify_cli.core.constants import KITTY_SPECS_DIR` per `planner.py` precedent — the
     boundary is established). Do NOT anchor a new bespoke cross-boundary import path.
  3. `_record_path_str` takes `(record, repo_root)`; derive the slug from
     `record.mission.mission_slug` (or `_mission_slug_from_feature_dir` at `:68` if that is the
     available handle) to call the authority — canonicalizing the handle first (FR-011 write leg)
     so the emitted payload matches the canonical write home for a bare handle too.
- **Notes**: this is the payload-parity fix — without it the file re-homes but the event still
  reports the legacy path (re-splitting the brain). FR-003's structural test (T032) catches a
  revert here.

### Subtask T036 — Payload-parity + flattened no-regression; LEAVE `_legacy_record_path`

- **Purpose**: Assert the emitted payload equals the actual home, and flattened is byte-identical.
- **Files**: `tests/retrospective/test_retrospective_durable_home_coord.py` (additional cases).
- **Steps**:
  1. **Payload parity:** the lifecycle-event payload path equals the actual write home (no longer
     the hardcoded `.kittify/missions/<id>/` string).
  2. **Flattened no-regression (NFR-003):** a flattened/single-branch mission resolves the SAME
     home before/after — byte-identical (the primary authority on a flattened mission is a no-op
     change vs the old coord-aware resolver, since there is no coord worktree).
  3. **Read-side unchanged (C-004):** confirm `writer.py:60` `_legacy_record_path` is untouched
     and the back-compat read still finds pre-#1771 records.
- **Notes**: real ULID/mid8; no bare-slug fixtures.

### Subtask T037 — RE-PIN the dormant #1771 false-green twin (DIR-041 — update, not delete)

- **Purpose**: Kill the false-green assertion in the existing #1771 regression test. Today
  `tests/retrospective/test_record_committable_1771.py:60`
  (`test_canonical_record_path_is_not_gitignored`) asserts only
  `assert "kitty-specs" in record_path.parts` (live-verified at `:60`). That is the SAME #1771
  false-green this mission forbids as the behavioral assertion (T031): it passes on a FLAT fixture
  even when the coord husk would leak, because `kitty-specs in parts` is true for both the durable
  home AND a `.worktrees/<slug>-coord/kitty-specs/...` husk path. It is a dormant twin that masks
  the very divergence WP03 cures.
- **Files**: `tests/retrospective/test_record_committable_1771.py` (re-pin `:60`; the file is now a
  WP03 `owned_file`).
- **Steps (DIR-041 — re-pin a valid+current test to the stronger contract; never delete-to-green)**:
  1. Keep the existing committable/gitignore assertions (they are still valid — the path must be
     tracked).
  2. Add (or strengthen to) a **coord-divergent fixture**: a composed `<slug>-<mid8>` primary dir
     with `meta.json` + a `coordination_branch` set + a materialized coord worktree whose mission
     dir lacks `meta.json`/`lanes.json` (the same genuine-divergence shape as T031 — real ULID/mid8,
     no bare-slug/flat fixture).
  3. Re-pin the assertion to ALSO require `assert ".worktrees" not in record_path.parts` — so the
     test fails if the record re-homes into the coord husk. `kitty-specs in parts` ALONE is
     insufficient and must no longer be the sole guard.
- **Notes**: this is the standing "tests as scaffold, not friction" framework — the test is
  valid+current, only its asserted contract is strengthened to the divergence-aware form. Do NOT
  delete the test; do NOT weaken it to keep the flat path passing.

## Test Strategy

- `PWHEADLESS=1 pytest tests/retrospective/test_retrospective_durable_home_coord.py tests/retrospective/test_home_resolution_single_authority.py -q` — RED first, GREEN after; capture red-run evidence.
- Confirm the behavioral assertion is `".worktrees" not in resolved.parts` (NOT `kitty-specs in parts`).
- `ruff check` + `mypy --strict` on all four touched modules — zero issues, no suppressions; `maxCC ≤ 15`.

## Definition of Done

- [ ] All 6 home-resolution sites route through `primary_feature_dir_for_mission` gated by
  `is_primary_artifact_kind(RETROSPECTIVE)` — none resolves independently.
- [ ] Each WRITE site **canonicalizes its handle via `_canonicalize_bare_modern_handle` BEFORE**
  composing through the blind primitive (FR-011 write leg) — reusing the SAME helper as WP01's read
  leg (no bespoke resolver, C-006); `MissionSelectorAmbiguous` propagates (no silent pick, C-009).
- [ ] Live-coord behavioral test asserts **`".worktrees" not in resolved.parts`** AND the file
  at `kitty-specs/<slug>/retrospective.yaml` (NOT `kitty-specs in parts` — that is the #1771
  false-green).
- [ ] **T037: `test_record_committable_1771.py:60` RE-PINNED** (DIR-041) — the `"kitty-specs" in
  parts` assertion is strengthened to ALSO require `".worktrees" not in record_path.parts` on a
  coord-divergent fixture (the dormant false-green twin no longer masks a husk leak); test NOT
  deleted/weakened.
- [ ] GREP/AST enumerating structural test passes; a 7th site / a reverted site #6 FAILS it
  (no hardcoded count).
- [ ] Payload parity (site #6 reports the actual home); flattened byte-identical (NFR-003).
- [ ] `writer.py:60` `_legacy_record_path` untouched (load-bearing `.kittify` read — C-004).
- [ ] WP03 touches ONLY its `owned_files` (write sites + 3 tests); the READ leg is WP01's; no overlap.
- [ ] Red-first evidence captured; ruff + `mypy --strict` clean, no suppressions; `maxCC ≤ 15`.

## Risks & Mitigations

- **#1771 false-green:** mitigated by the `".worktrees" not in resolved.parts` assertion on a
  genuinely-divergent coord fixture (NFR-002) — reviewer MUST reject a `kitty-specs in parts`
  assertion or a flattened fixture.
- **Payload re-split (site #6 missed):** mitigated by T032's structural test + T036's payload
  parity assertion.
- **Boundary crossing at site #6:** mitigated by consuming the public import surface (the
  established `core.constants` precedent), no new bespoke import.

## Review Guidance

- Confirm the behavioral test drives a genuinely-divergent coord fixture (coord surface lacks
  `meta.json`/`lanes.json`) and asserts `".worktrees" not in resolved.parts`. A bare-slug or
  flattened fixture, or a `kitty-specs in parts` assertion, is REJECTED (the #1771 trap).
- Confirm the structural test enumerates by GREP/AST (no hardcoded count) and fails on a 7th
  site / reverted site #6.
- Confirm `writer.py:60` `_legacy_record_path` is untouched (C-004).
- Confirm red-first evidence (the coord write landed under `.worktrees` on unfixed code).

## Activity Log

- 2026-06-25T19:36:37Z – system – Prompt created via /spec-kitty.tasks (planner-priti); FR-001/003.
</content>
- 2026-06-25T21:40:12Z – claude:opus:python-pedro:implementer – shell_pid=1736101 – Assigned agent via action command
- 2026-06-25T21:55:36Z – claude:opus:python-pedro:implementer – shell_pid=1736101 – Ready: 6 sites consolidated onto resolve_retrospective_home (FR-001/003), write-leg handle-canonicalization (FR-011), #1771 twin re-pinned (T037), live-coord-divergence asserts '.worktrees' not in parts; red-first evidence captured. --force: behind-target (flat-mission lane carries code-only, orchestrator reconciles)
- 2026-06-25T21:56:25Z – claude:opus:python-pedro:implementer – shell_pid=1736101 – Code on lane-c (543ccfac2): 6 sites consolidated onto resolve_retrospective_home, RED-first proven, #1771 twin re-pinned, 1129 passed
- 2026-06-25T21:56:27Z – claude:opus:reviewer-renata:reviewer – shell_pid=1756364 – Started review via action command
- 2026-06-25T22:05:07Z – user – shell_pid=1756364 – renata APPROVE: 6 sites consolidated (old calls grep-gone), keystone+structural mutation-probed RED, #1771 twin re-pinned, gates clean
