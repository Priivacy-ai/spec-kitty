---
work_package_id: WP01
title: Deterministic identity completion (deterministic build_id)
dependencies: []
requirement_refs:
- FR-002
tracker_refs: []
planning_base_branch: fix/sync-worktree-clean-invariant
merge_target_branch: fix/sync-worktree-clean-invariant
branch_strategy: Planning artifacts for this mission were generated on fix/sync-worktree-clean-invariant. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/sync-worktree-clean-invariant unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
phase: Phase 1 - Foundation
assignee: ''
agent: claude
history:
- at: '2026-06-30T13:20:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/identity/
create_intent:
- tests/specify_cli/identity/test_identity_build_id_determinism.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/identity/project.py
- tests/specify_cli/identity/test_identity_build_id_determinism.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP01 – Deterministic identity completion

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter
**before parsing the rest of this prompt**, and behave according to its guidance.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If the profile cannot be loaded, run `spec-kitty agent profile list` and select the
best match for `task_type: implement` on `authoritative_surface: src/specify_cli/identity/`.

---

## Objective

Make a *minted* `build_id` **deterministic** so the read-only identity resolver
(`resolve_identity`) returns a stable identity for an incomplete-identity checkout
without writing `.kittify/config.yaml`. This is the foundation for WP02's call-site
migration: today `with_defaults` mints `build_id = str(uuid4())` (random), so a
non-persisting read path would drift `build_id` on every call. After this WP, a
missing `build_id` is derived from the already-stable `project_uuid` + `node_id`.

This implements **Decision C** (see `research.md`). Do **not** change how
`project_uuid` is generated.

## Context & Constraints

- File: `src/specify_cli/identity/project.py`.
- Current behavior (read before editing):
  - `ProjectIdentity.is_complete` (≈line 53) requires `project_uuid, project_slug, node_id, build_id`.
  - `ProjectIdentity.with_defaults` (≈line 62) fills missing fields: `project_uuid or generate_project_uuid()` (uuid4), `project_slug or derive_project_slug()` (deterministic), `node_id or generate_node_id()` (deterministic sha256(host:user)), `build_id or generate_build_id()` (uuid4 — **the drift source**).
  - `ensure_identity` (≈line 299) → completes + persists (write-authorized). `resolve_identity` (≈line 336) → completes **in memory, no write**.
- **Constraints**:
  - C-003: `config.yaml` stays the canonical store; only behavior changes.
  - C-005: an already-present `build_id` (or any persisted complete identity) is returned **unchanged**.
  - `project_uuid` generation is **unchanged** (Option A is explicitly out of scope).
  - No new `# noqa` / `# type: ignore`. `mypy --strict` + `ruff` clean. Complexity ≤ 15.
- Contract reference: `contracts/identity-resolution.md` (C-IR-1, C-IR-2, C-IR-4).

## Branch Strategy

- **Strategy**: `shared-lane`
- **Planning base branch**: `fix/sync-worktree-clean-invariant`
- **Merge target branch**: `fix/sync-worktree-clean-invariant`

> `lanes.json` (written at finalize-tasks) governs the actual lane. WP01 has no
> dependencies and owns `identity/project.py` exclusively.

## Subtasks & Detailed Guidance

### T001 — Add `derive_build_id` helper + NAMESPACE constant

**Purpose**: a pure, deterministic function for the `build_id` field.

**Steps**:
1. Add a module-level constant namespace, e.g.
   `_BUILD_ID_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "spec-kitty:identity:build_id")`
   (a fixed namespace; do not inline the literal more than once — S1192).
2. Add `def derive_build_id(project_uuid: UUID, node_id: str) -> str:` returning
   `str(uuid.uuid5(_BUILD_ID_NAMESPACE, f"{project_uuid}:{node_id}"))`.
3. Keep it pure (no I/O, no randomness). Place it next to `generate_build_id`.

**Validation**: same inputs → identical output across calls; different `(project_uuid, node_id)` → different output.

### T002 — Wire deterministic `build_id` into `with_defaults` (only when missing)

**Purpose**: a minted `build_id` is derived, not random — but only when absent.

**Steps**:
1. In `with_defaults`, compute `project_uuid` and `node_id` first (as today).
2. Replace `build_id=self.build_id or generate_build_id()` with:
   `build_id=self.build_id or derive_build_id(resolved_project_uuid, resolved_node_id)`
   where `resolved_*` are the values just computed (so derivation uses the final
   `project_uuid`/`node_id`, not the possibly-None originals).
3. Leave `project_uuid`, `project_slug`, `node_id`, `repo_slug` untouched.
4. `generate_build_id` may remain (used nowhere else after this, or kept for back-compat); do not delete if other modules import it — grep first.

**Validation**: an identity already carrying `build_id` is returned unchanged; an identity missing only `build_id` gets the derived value.

### T003 — Honor the uninitialized-checkout edge (C-IR-4)

**Purpose**: never persist on read paths; define behavior when `project_uuid` is absent.

**Steps**:
1. Confirm `resolve_identity` performs **no write** under any input (it must not call `atomic_write_config`). Add a regression test in T004.
2. Decide the truly-uninitialized case (no `project_uuid` on disk): `with_defaults` will still mint a fresh random `project_uuid` in memory. Per C-IR-4 this is acceptable **only** because such a checkout is expected to pass through `init` (write-authorized) first; `resolve_identity` must still not persist it.
3. Add a short docstring note on `resolve_identity` clarifying the realistic stable case (legacy missing `build_id`) vs the uninitialized case, referencing C-IR-4.

**Validation**: calling `resolve_identity` on an empty config writes nothing (assert file unchanged/absent).

### T004 — Unit tests

**Purpose**: lock the determinism + no-write guarantees (NFR-001 / SC-003 / C-005).

**File**: `tests/specify_cli/identity/test_identity_build_id_determinism.py`.

**Cases**:
- `derive_build_id` is stable across N≥5 calls for fixed inputs; varies with inputs.
- Legacy identity (uuid+slug+node present, `build_id=None`): two `resolve_identity` calls return identical `(project_uuid, build_id)`; no `config.yaml` write.
- Complete identity on disk is returned unchanged (C-005).
- `resolve_identity` on an empty/missing config performs no write.
- `is_complete` is True after `with_defaults` (build_id populated).

**Validation**: ≥90% coverage on new lines; tests deterministic.

### T005 — Constants + lint/type clean

**Steps**:
1. Hoist any repeated literal (namespace string, separators) into module constants.
2. `mypy --strict src/specify_cli/identity/project.py` clean; `ruff check` clean.
3. Keep `with_defaults`/helpers under complexity 15.

## Test Strategy

Unit-level only for this WP (pure functions + resolver no-write). Integration of
the emit path is WP02; full invariant enforcement is WP04.

```bash
PWHEADLESS=1 .venv/bin/pytest tests/specify_cli/identity/test_identity_build_id_determinism.py -q
.venv/bin/mypy --strict src/specify_cli/identity/project.py
.venv/bin/ruff check src/specify_cli/identity/project.py
```

## Risks & Mitigations

- **Risk**: `generate_build_id` still referenced elsewhere → breakage. **Mitigation**: grep all callers before removing; keep the function if imported.
- **Risk**: changing `with_defaults` also changes `init`'s minted `build_id` (now derived). **Mitigation**: this is acceptable and consistent (still unique per project since `project_uuid` is unique per init); call it out in the PR. Persisted identities are unaffected.
- **Risk**: deriving from a None `project_uuid`. **Mitigation**: derive only after resolving `project_uuid`/`node_id` to their final values inside `with_defaults`.

## Review Guidance

- Confirm `project_uuid` generation is untouched.
- Confirm `resolve_identity` writes nothing under any path.
- Confirm a present `build_id` is never overwritten.
- Confirm determinism test exists and passes.

## Activity Log

- 2026-06-30 — Prompt generated via /spec-kitty.tasks.
