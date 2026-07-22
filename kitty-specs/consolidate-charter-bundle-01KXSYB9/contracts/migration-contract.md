# Contract: legacy → charter.yaml migration

New migration in `src/specify_cli/upgrade/migrations/m_*.py`. Body pattern = `src/doctrine/versioning.py:299 migrate_v1_to_v2` (yaml→yaml write-and-stamp), NOT the rc35 refresh-only shape. Registered via `@MigrationRegistry.register`; `runs_on_worktrees = False`; lazy `charter.*` imports (C-002).

## Inputs (read, safe-load)
- `.kittify/charter/governance.yaml`, `directives.yaml`, `metadata.yaml`, `references.yaml`
- `.kittify/config.yaml` `activated_*` section (relocated)

## Output
- `.kittify/charter/charter.yaml` composed from: governance ← governance.yaml; directives ← directives.yaml; catalog ← references.yaml body; activation ← config.yaml `activated_*`; metadata.bundle_schema_version ← 2.
- Deletes the four legacy bundle files.
- Removes `activated_*` from `.kittify/config.yaml` and **adds a single `charter: .kittify/charter/charter.yaml` pointer** (preserves `agents:` + non-doctrine keys; comment-preserving round-trip). The resolver locates `charter.yaml` via this pointer.
- Updates `.gitignore` (remove the four entries; charter.yaml tracked).

## Guarantees
- **MG1 (deterministic, NFR-003)**: pure yaml→yaml transform; no prose parsing; stable key ordering. Activation lists copied **VERBATIM** — an absent key stays absent (NEVER converted to `[]`, which would flip all-active→none), an explicit `[]` stays `[]` (paula MINOR-2 / SC-008).
- **MG2 (idempotent, NFR-003)**: state `charter.yaml present + four absent + config has no activated_*` → the migration reports **0 changes** and exits success. Idempotent even against re-seeding by the existing seed migrations (see MG6).
- **MG3 (fail-loud, C-003)**: a charter operation on `four-present / no-charter.yaml` raises the re-homed #2530 fail-closed error with a single actionable "run the migration" message; no silent legacy-file read.
- **MG4 (identity-safe)**: touches ONLY `.kittify/charter/metadata.yaml`; NEVER `.kittify/metadata.yaml` (project identity — `schema_version`/`project_uuid`).
- **MG5 (behavior-preserving activation)**: post-migration activation resolution (parity + DRG filter) is byte-identical to pre-migration (INV-4).
- **MG6 (migration ordering — paula MAJOR-3)**: the fold sequences **strictly AFTER** the existing activation-seed migrations that write `activated_*` INTO config.yaml — `m_unify_charter_activation.py` (whose "config is the activation authority" invariant is now REVERSED — annotate/reconcile it) and the rc35 pair (`m_3_2_0rc35_default_charter_pack.py`, `m_3_2_0rc35_activate_builtin_mission_types.py`, both `detect()` on absence). Their post-state (config has `activated_*`) is the fold's pre-state; the fold relocates then removes those keys (INV-2). The fold must not perpetually re-fire against a re-seeded config.

## Test obligations
- Legacy fixture (four files + config.activated_*, no charter.yaml) → fail-loud before; migrate; assert charter.yaml composed (flat activation) + four gone + config.activated_* gone + `charter:` pointer added; re-run → 0 changes.
- Absent-key fidelity: a config with an absent per-kind key migrates to charter.yaml with that key still absent (not `[]`).
- Ordering: after the rc35/unify seed migrations run, the fold relocates their output and leaves config activation-free.
- Reuse/extend `tests/upgrade/test_unified_bundle_migration.py`, `test_charter_rename_migration.py`, `tests/specify_cli/test_state_contract.py`, `test_state_gitignore_migration.py`.
