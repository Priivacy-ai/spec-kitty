# Tasks: Resolution & Activation Foundation

**Mission**: `resolution-activation-foundation-01KZ9FKG` · **Branch**: `feat/resolution-activation-foundation`
**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Contracts**: [contracts/](./contracts/resolution-and-activation-contracts.md)

Work packages slice the 6 implementation concerns (IC-01…IC-06). ATDD-first: each WP opens with a
RED acceptance test tied to its FRs/contracts before implementation. Subtask rows are event-sourced
reference rows — record completion with `spec-kitty agent tasks mark-status Txxx --status done`, not
by ticking a box.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | RED: PACKS_ROOT relocates the door + fail-closed on missing tree | WP01 | |
| T002 | Kernel PACKS_ROOT-aware built-in-pack-root primitive (PACKS_ROOT-first, keep TEMPLATE_ROOT) | WP01 | |
| T003 | Repoint the `get_package_asset_root` door onto the primitive (`<root>/missions`) | WP01 | |
| T004 | Collapse `home.py` onto the primitive; drop legacy fallbacks (fail-closed); wildcard detector; retarget seams | WP01 | |
| T005 | De-duplicate `_find_relocated_missions_ancestor` (one definition) | WP01 | |
| T006 | Correct false re-export docstrings (`kernel/__init__.py`, `kernel/README.md`) | WP01 | [P] |
| T007 | Green `tests/kernel/test_paths.py` + `tests/runtime/test_home_unit.py` | WP01 | |
| T008 | RED: both `default_missions_root()` and the door relocate via PACKS_ROOT + both-vars precedence | WP02 | |
| T009 | `pack_paths._resolve_built_in` delegates to the kernel primitive; keep `PackRootNotFound` translation | WP02 | |
| T010 | `default_missions_root = built_in_root()/"missions"` + `.is_dir()` + `MissionsRootNotFound` | WP02 | |
| T011 | Hoist sibling pattern to kernel authority; collapse drifting constants (`repository.py`, `agent_commands.py`) | WP02 | |
| T012 | Fix the false `dev_roots` docstring (`repository.py:37-44`) | WP02 | [P] |
| T013 | Green doctrine/charter resolver tests | WP02 | |
| T014 | RED: fresh-init writes explicit copied activations; missing default.yaml fails closed; idempotent re-run | WP03 | |
| T015 | Provisioning helper: COPY `default.yaml` mission_type_activations (no re-scan); customization-safe | WP03 | |
| T016 | Wire fresh-init provisioning into `init.py` (re-anchor around #3211 gitattributes) | WP03 | |
| T017 | Regression: both rc35 migrations unchanged + idempotent | WP03 | [P] |
| T018 | Green `tests/upgrade/*` + new init-provisioning test | WP03 | |
| T019 | RED: absent-key provisioned project → provisioned set; no all-four backfill; authored `[]` empty; authority parity | WP04 | |
| T020 | Remove the config-absent backfill at `pack_context._read_activated_mission_types` | WP04 | |
| T021 | Update `mission_type_profiles.existing_mission_types` delegation/docstring (no behavior change) | WP04 | |
| T022 | Update `test_pack_context.py` + `test_mission_type_activation_gating.py` (keep T034/T036) | WP04 | |
| T023 | Single-source arch guard: 0 second PACKS_ROOT read / door body / mission_type_activations fallback | WP05 | |
| T024 | Scope-fence guard: MissionTypeNotAnArtifactKind raised; readers unchanged; specify_cli/missions present | WP05 | |
| T025 | Layer + terminology gates green (from the primary checkout) | WP05 | |

## Work Packages

### WP01 — Kernel PACKS_ROOT-aware resolution primitive + collapse the second copy
- **Goal**: One kernel-floor `SPEC_KITTY_PACKS_ROOT`-aware built-in-pack-root primitive; the door resolves `<root>/missions` through it; `home.py` collapses onto it (fail-closed); one ancestor-walk; kernel docstrings corrected.
- **Priority**: P1 · **Dependencies**: none (root) · **FRs**: FR-001, FR-002, FR-004, FR-005, FR-006, FR-013
- **Independent test**: with `SPEC_KITTY_PACKS_ROOT` set the door resolves under it; missing tree fails closed; one primitive/ancestor-walk.
- **Subtasks**: T001–T007 · **Prompt**: [tasks/WP01-kernel-packs-root-primitive.md](./tasks/WP01-kernel-packs-root-primitive.md) (~260 lines)

### WP02 — Downstream delegation, `default_missions_root`, sibling-pattern authority
- **Goal**: `pack_paths._resolve_built_in` delegates to the kernel primitive; `default_missions_root = built_in_root()/"missions"` (+`.is_dir()`); sibling pattern owned once; false `dev_roots` docstring fixed; PACKS_ROOT missions regression added.
- **Priority**: P1 · **Dependencies**: WP01 · **FRs**: FR-001, FR-003, FR-004, FR-005, FR-012, FR-013, NFR-006
- **Independent test**: new `tests/doctrine/test_missions_root_packs_env.py` proves both resolvers relocate via PACKS_ROOT + both-vars precedence.
- **Subtasks**: T008–T013 · **Prompt**: [tasks/WP02-downstream-delegation-sibling-authority.md](./tasks/WP02-downstream-delegation-sibling-authority.md) (~240 lines)

### WP03 — Fail-closed provisioning (fresh-init + migration parity)
- **Goal**: `spec-kitty init` seeds `mission_type_activations` by COPYING `packs/default.yaml`'s authored list (no re-scan); fail-closed on missing default.yaml; both rc35 migrations kept + idempotent.
- **Priority**: P1 · **Dependencies**: none (root) · **FRs**: FR-009, FR-010, FR-011, NFR-004
- **Independent test**: fresh init yields explicit non-empty activations copied from default.yaml; broken install fails closed; re-run byte-identical.
- **Subtasks**: T014–T018 · **Prompt**: [tasks/WP03-fail-closed-provisioning.md](./tasks/WP03-fail-closed-provisioning.md) (~230 lines)

### WP04 — Activation authority + retire the implicit fallback
- **Goal**: Provisioned charter is the authority; remove the config-absent all-four backfill; authored `[]` preserved; no behavior change at the activation authority for provisioned projects.
- **Priority**: P1 · **Dependencies**: WP03 · **FRs**: FR-007, FR-008 (+ NFR-003 parity)
- **Independent test**: absent key on a provisioned project resolves from the provisioned charter; no backfill site remains; authority parity holds.
- **Subtasks**: T019–T022 · **Prompt**: [tasks/WP04-activation-authority.md](./tasks/WP04-activation-authority.md) (~200 lines)

### WP05 — Single-source + scope-fence architectural guards
- **Goal**: Regression guards proving one resolution/availability source and an intact scope fence.
- **Priority**: P2 · **Dependencies**: WP01, WP02, WP04 · **FRs**: NFR-001, NFR-002, NFR-005 (+ SC-001, SC-005; C-001, C-003)
- **Independent test**: arch suite green — 0 second PACKS_ROOT read / door body / mission_type_activations fallback; MissionTypeNotAnArtifactKind raised; readers unchanged.
- **Subtasks**: T023–T025 · **Prompt**: [tasks/WP05-scope-fence-guards.md](./tasks/WP05-scope-fence-guards.md) (~180 lines)

## MVP / sequencing

- **Independent roots**: WP01 and WP03 (can start in parallel).
- **Chains**: WP01 → WP02 (resolver chain); WP03 → WP04 (provision before removing the fallback).
- **Verify last**: WP05 (depends WP01, WP02, WP04).
- **MVP slice**: WP01 + WP02 deliver the unified resolver (#3210 half); WP03 + WP04 deliver the activation authority (#2657 half). Both halves are needed for the foundation; neither repoints availability readers (that is #2659).
