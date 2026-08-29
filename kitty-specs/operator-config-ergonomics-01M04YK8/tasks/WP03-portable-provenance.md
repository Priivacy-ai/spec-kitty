---
work_package_id: WP03
title: Portable provenance emit + heal + leak-check
dependencies:
- WP01
requirement_refs:
- FR-001
- FR-002
- FR-003
- NFR-002
- NFR-003
planning_base_branch: fix/operator-config-ergonomics
merge_target_branch: fix/operator-config-ergonomics
branch_strategy: Planning artifacts for this mission were generated on fix/operator-config-ergonomics. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/operator-config-ergonomics unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T012
- T013
- T014
- T015
- T016
history:
- '2026-08-16: authored by /spec-kitty.tasks'
agent_profile: python-pedro
authoritative_surface: src/charter/
create_intent:
- src/doctrine/provenance.py
- src/specify_cli/upgrade/migrations/m_3_2_7_heal_provenance_paths.py
- src/specify_cli/cli/commands/_provenance_doctor.py
- tests/doctrine/test_provenance_normalizer.py
- tests/charter/test_portable_provenance.py
- tests/specify_cli/upgrade/migrations/test_heal_provenance.py
- tests/architectural/test_no_absolute_pack_paths.py
execution_mode: code_change
model: claude-sonnet-4-6
owned_files:
- src/doctrine/provenance.py
- src/charter/activation/compiler.py
- src/specify_cli/tool_surface/profiles/projection.py
- src/specify_cli/tool_surface/profiles/_paths.py
- src/specify_cli/upgrade/migrations/m_3_2_7_heal_provenance_paths.py
- src/specify_cli/cli/commands/doctor.py
- src/specify_cli/cli/commands/_provenance_doctor.py
- tests/doctrine/test_provenance_normalizer.py
- tests/charter/test_portable_provenance.py
- tests/specify_cli/upgrade/migrations/test_heal_provenance.py
- tests/architectural/test_no_absolute_pack_paths.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile
Load `python-pedro` (implementer) via `/ad-hoc-profile-load`.

## Objective
Make committed provenance portable: one 3-class normalizer emits `${SPEC_KITTY_PACKS_ROOT}/built-in/...` tokens for built-in-pack paths at BOTH carriers, a heal migration fixes existing absolute paths, and a doctor sibling flags leaks. Contracts: [../contracts/provenance-and-channel.md](../contracts/provenance-and-channel.md) (C-PRV-1..6). Design D1; plan PPC-1/PPC-2. Deps: **WP01** (kernel authority). **Empirically real:** committed `charter.yaml:124` = a linux path, `agent_profiles_manifest.json` = a mac-wheel path.

## Branch Strategy
Base + merge target: `fix/operator-config-ergonomics`. Lane worktree from `lanes.json`.

## Subtasks

### T011 — `src/doctrine/provenance.py` (NEW): 3-class normalizer
- `def to_portable_source_path(abs_path, *, project_root) -> str`: (a) if under `kernel.paths.get_built_in_pack_root()` → `${SPEC_KITTY_PACKS_ROOT}/built-in/<rest>` token (use the owned `BUILT_IN_PACK_SIBLING_PATTERN`, never hand-type); (b) else if under `project_root` → repo-relative POSIX (preserve today's behavior); (c) else → absolute (preserve). Lives at doctrine layer so charter (below specify_cli) can import it.

### T012 — Charter catalog emit (`compiler.py`)
- Replace `_trim_source_path` usage at the CATALOG source caller `_doctrine_yaml_reference` (`:1424/1447`) with `to_portable_source_path`. **Do NOT touch** the mission-template callers `_template_reference` (`:1482/1494`) or the local-support decl (`:1279`) — leave them byte-unchanged. Retire `_trim_source_path` only if no caller remains (else keep for the excluded callers).

### T013 — Manifest emit (`projection.py` / `_paths.py`)
- Route the manifest SOURCE emit `_manifest_source_path` (`projection.py:53-56`) through `to_portable_source_path`. **Leave `output_path` (`manifest.py:112` via `relativize_under_root`) repo-relative — do not re-token it.** If `_paths.py` needs a helper, add it without changing `relativize_under_root`'s existing callers.

### T014 — Heal migration
- `m_3_2_7_heal_provenance_paths.py` (BaseMigration, **`target_version="3.2.7"`** — distinct from WP04 provision `3.2.8`): `detect` = any absolute built-in `source_path` in `charter.yaml` catalog or `agent_profiles_manifest.json`; `apply(dry_run)` rewrites to tokens via the charter-yaml safe round-trip (`charter_yaml_io.update_charter_yaml_section`) + `ProfileManifest` save; idempotent. (Heal is independent of the consent axis; provision, WP04, is the one ordered vs #3381.)

### T015 — Doctor auto-discovery seam + `_provenance_doctor.py` sibling
- **Add an auto-discovery registration seam to `cli/commands/doctor.py`** (this WP owns it): replace the hand-maintained per-sibling `import` + `@app.command` shells with a discovery loop that imports every `cli/commands/_*_doctor.py` module and calls its `register(app)` (mirror the migration auto-discovery at `upgrade/migrations/__init__.py:18`). This is the load-bearing fix for the three-lane collision — after it, WP04/WP05 drop self-registering siblings and touch `doctor.py` ZERO times.
- Add `cli/commands/_provenance_doctor.py` exposing `register(app)`; import shared collect/render infra from the canonical `_doctor_shared` (do not duplicate). Scans committed `charter.yaml`/manifest for absolute built-in paths; warns with a heal hint.
- RED-first: write the failing doctor-registration + leak-check tests before wiring.

### T016 — Tests (C-PRV-1..6)
- `test_provenance_normalizer.py`: 3-class matrix (built-in→token, in-tree→relative, out-of-tree→absolute).
- `test_portable_provenance.py`: C-PRV-1 (fresh emit tokens, both carriers), C-PRV-2 re-bake gate (`SPEC_KITTY_PACKS_ROOT=/abs` exported → still token, byte-identical), C-PRV-3 invariance (editable vs simulated-wheel root), and **excluded-callers byte-unchanged** (mission-template + `output_path`).
- `test_heal_provenance.py`: C-PRV-4 (heal + re-run 0 changes).
- `test_no_absolute_pack_paths.py`: architectural — no committed `charter.yaml`/manifest contains an absolute built-in path.

## Definition of Done
- C-PRV-1..6 green; excluded callers proven byte-unchanged; heal idempotent; arch no-absolute-path gate green.
- `ruff`/`mypy` clean.

## Reviewer guidance
- The surgical scope is critical: verify mission-template callers + `output_path` are untouched (a regression here re-creates drift).
- Verify the token, not a resolved path, is stored even with `SPEC_KITTY_PACKS_ROOT` set to an absolute path.
- Verify the doctor check is a `_provenance_doctor.py` sibling under `cli/commands/doctor.py`, not `runtime/doctor.py`.
