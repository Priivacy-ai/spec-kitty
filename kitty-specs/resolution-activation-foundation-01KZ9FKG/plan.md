# Implementation Plan: Resolution & Activation Foundation

**Branch**: `feat/resolution-activation-foundation` | **Date**: 2026-08-05 (revised post-#3211/review) | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/resolution-activation-foundation-01KZ9FKG/spec.md`

## Summary

Build the two foundations charter-loaded mission types depend on, without repointing availability readers (that is #2659). **(1) #3210 (DR-1 — unify the resolver):** the `built-in` pack (missions included) is installed/available from the default- or env-supplied pack root (`SPEC_KITTY_PACKS_ROOT`). Make the mission-tree `<built-in-pack-root>/missions` resolved through one kernel-floor PACKS_ROOT-aware primitive that `doctrine.pack_paths._resolve_built_in`, `default_missions_root`, and the `get_package_asset_root` door all delegate to; drop `home.py`'s legacy fallbacks (fail-closed); collapse the drifting sibling-pattern constants; correct the false docstrings. **(2) #2657:** retire the implicit "all four" fallback in `charter/pack_context.py`; the provisioned `packs/default.yaml` becomes the activation authority; add fail-closed provisioning at fresh-init (copy, not re-scan) and keep both rc35 migrations.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: spec-kitty CLI internals (`kernel`, `doctrine`, `charter`, `specify_cli`); no new third-party dependency.
**Storage**: `.kittify/config.yaml`; shipped `src/charter/activation/packs/default.yaml`; built-in pack tree at `<pack-root>/built-in/missions`. No database.
**Testing**: pytest (ATDD-first); `-n auto --dist loadfile` suite, `-n0` for any daemon/real-port test; `mypy --strict` + `ruff` zero-issue; `tests/architectural/` from the **primary checkout**.
**Target Platform**: Cross-platform CLI (DIR-001).
**Project Type**: single (Python package + tests).
**Performance Goals**: N/A — resolution is not a hot path; behavior-preserving (NFR-003).
**Constraints**: Layer `kernel ← doctrine ← charter ← specify_cli`, no upward imports (C-005); the PACKS_ROOT env read lives in `kernel` (kernel reading an env var is layer-legal); complexity ≤15; S1192 constants; no new suppressions; fail-closed; preserve TEMPLATE_ROOT copy-path role (C-009); Terminology Canon.
**Scale/Scope**: ~7 production files across 3 layers + init; ~9 test files updated/added. No persisted-schema change.

## Charter Check

*GATE: Must pass before Phase 0. Re-check after Phase 1.*

| Gate | Applies | Satisfied by |
|---|---|---|
| Single canonical authority | Yes — core intent | One PACKS_ROOT-aware resolver primitive (kernel); one activation authority (provisioned charter). NFR-001 forbids a second env-read/body/fallback. |
| Architectural alignment / layer (C-004/C-005) | Yes | Primitive in `kernel`; the PACKS_ROOT env read moves to kernel (no upward edge — kernel reads an env var, does not import doctrine); `doctrine.pack_paths`/`default_missions_root`/door consume downward. Layer/AST gates green (NFR-002). |
| No-silent-fallback / fail-closed (R-009/FR-032) | Yes | Implicit config-absent all-four fallback removed; `home.py` legacy fallbacks dropped → fail-closed. ArtifactKind contract untouched (C-001). |
| `__all__` convention (C-007-charter) | Partial | Kernel primitive + any re-export surface get matching `__all__`; no deep-import bypass. |
| ATDD-first (C-011) | Yes | Red acceptance test per FR — single-primitive invariant, PACKS_ROOT relocation (both resolvers), activation-authority parity. |
| Terminology Canon | Yes | No new `feature*`; doc edits (FR-005) run the CI-only terminology shard locally before push. |
| Campsite / domain-matched folds (DIR-025) | Yes | Folds F1 (sibling-pattern authority), F2 (`dev_roots` docstring), F3 (third-resolver constant); freeze out-of-domain (nested-vs-flat, availability readers, ArtifactKind). |

**Result: PASS** — no violations; no Complexity Tracking entries.

## Project Structure

### Documentation (this mission)

```
kitty-specs/resolution-activation-foundation-01KZ9FKG/
├── plan.md · spec.md · research.md · data-model.md · quickstart.md
├── contracts/resolution-and-activation-contracts.md
├── post-plan-review-findings.md        # squad findings + revision checklist
├── traces/{tooling-friction,approach,design-decisions}.md
└── tasks.md                            # Phase 2 (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)

```
src/
├── kernel/
│   ├── sibling_paths.py          # resolve_installed_sibling (env-agnostic algo — already exists)
│   ├── paths.py                  # NEW: PACKS_ROOT-aware built-in-pack-root primitive; door delegates (IC-01/02)
│   ├── __init__.py               # correct false re-export claim (IC-03, FR-005)
│   └── README.md                 # correct false re-export claim (IC-03, FR-005)
├── doctrine/
│   ├── pack_paths.py             # _resolve_built_in delegates to kernel primitive; drop dup PACKS_ROOT read (IC-02, FR-001)
│   └── missions/repository.py    # default_missions_root = built_in_root()/"missions"; fix dev_roots docstring (IC-01/02/03, FR-003/005)
├── charter/
│   ├── pack_context.py           # retire implicit all-four fallback (IC-04, FR-008)
│   ├── mission_type_profiles.py  # activation-authority delegation/docstring (IC-04, FR-007)
│   └── packs/default.yaml         # authored activation surface COPIED by provisioning (IC-05)
└── specify_cli/
    ├── runtime/home.py           # collapse onto primitive; drop legacy fallbacks (IC-01, FR-006)
    ├── runtime/__init__.py       # re-export mapping → single authority (IC-01)
    ├── runtime/agent_commands.py # converge pattern constant onto kernel authority (IC-02, FR-012/F3)
    └── cli/commands/init.py      # fresh-init provisioning, copy default.yaml (IC-05, FR-009/011); re-anchor around #3211's gitattributes addition

tests/
├── kernel/test_paths.py · runtime/test_home_unit.py (retarget seams, C-007)
├── doctrine/ (new) test_missions_root_packs_env.py            # NFR-006 (both resolvers + both-vars precedence)
├── charter/test_pack_context.py · test_mission_type_activation_gating.py (keep T034/T036)
├── upgrade/test_m_3_2_0rc35_*.py · (new) init-provisioning test # FR-009/010
└── architectural/ single-resolver invariant + scope-fence guards (IC-06)
```

**Structure Decision**: Single Python package; the PACKS_ROOT-aware built-in-pack-root primitive is added at the kernel floor and consumed downward.

## Complexity Tracking

*No Charter Check violations — section intentionally empty.*

## Implementation Concern Map

> Concerns are NOT work packages. `/spec-kitty.tasks` translates these into WPs.

### IC-01 — Kernel-floor PACKS_ROOT-aware resolution primitive + collapse the second copy

- **Purpose**: Add one kernel primitive that reads `SPEC_KITTY_PACKS_ROOT` and resolves the built-in pack root via `resolve_installed_sibling`; the `get_package_asset_root` door resolves `<root>/missions` through it; `home.py` collapses onto it (dropping legacy fallbacks, fail-closed); one `_find_relocated_missions_ancestor`; surviving detector is the enumeration-free wildcard.
- **Relevant requirements**: FR-001, FR-002, FR-006, FR-013.
- **Affected surfaces**: `kernel/paths.py`, `kernel/sibling_paths.py` (consume), `specify_cli/runtime/home.py`, `specify_cli/runtime/__init__.py`; `tests/kernel/test_paths.py`, `tests/runtime/test_home_unit.py`.
- **Sequencing/depends-on**: none (root).
- **Risks**: C-007 retarget monkeypatch seams; **C-009 door-caller census** — the door currently honors `SPEC_KITTY_TEMPLATE_ROOT`; enumerate its callers (`init.py`, `resolver.py`, `bootstrap.py`, `migrate.py`, `show_origin.py`, `agent_commands.py`, `charter/catalog.py`) and confirm the copy-path TEMPLATE_ROOT semantics survive when PACKS_ROOT governs pack-root location. **Delta-review caveat**: insert the PACKS_ROOT branch **ahead of** (not replacing) the retained TEMPLATE_ROOT branch (PACKS_ROOT-first ordering, FR-004); assert the TEMPLATE_ROOT-only dev path (resolver/init/bootstrap) stays unchanged. Neither door reads PACKS_ROOT today, so there is no existing both-set behavior to preserve.

### IC-02 — Downstream delegation + sibling-pattern single authority

- **Purpose**: `doctrine.pack_paths._resolve_built_in` delegates to the kernel primitive (retire the duplicate `SPEC_KITTY_PACKS_ROOT` read at `pack_paths.py:204`); `default_missions_root()` = `built_in_root()/"missions"`; the three drifting sibling-pattern constants collapse onto the kernel authority + the existing `missions` leaf name.
- **Relevant requirements**: FR-001, FR-003, FR-004, FR-012.
- **Affected surfaces**: `doctrine/pack_paths.py`, `doctrine/missions/repository.py`, `specify_cli/runtime/agent_commands.py` (constant only); new `tests/doctrine/test_missions_root_packs_env.py`.
- **Sequencing/depends-on**: follows IC-01 (primitive must exist).
- **Risks**: `_resolve_built_in`'s `PackRootNotFound` translation must survive at the doctrine boundary (`pack_validator.py:83,793` depend on the specific type); FR-004 precedence must be pinned by a both-vars test. **Delta-review caveat**: `default_missions_root = built_in_root()/"missions"` must re-add an `.is_dir()` check + `MissionsRootNotFound` raise — `built_in_root()` only verifies `packs/built-in` exists, so a bare join could return a nonexistent `…/missions` path, regressing FR-013/C-R4/I-4.

### IC-03 — Docstring/documentation truth

- **Purpose**: Correct the false "re-exported by" claims (`kernel/__init__.py`, `kernel/README.md`) AND the non-existent `dev_roots` note (`doctrine/missions/repository.py:37-44`, fold F2).
- **Relevant requirements**: FR-005.
- **Affected surfaces**: `kernel/__init__.py`, `kernel/README.md`, `doctrine/missions/repository.py` (docstring).
- **Sequencing/depends-on**: follows IC-01/IC-02 (topology must be real first).
- **Risks**: touches shipped prose → run the CI-only terminology shard locally (tracer W2). Name the FR-005 test surface (a grep/assertion).

### IC-04 — Activation authority + retire the implicit fallback

- **Purpose**: Provisioned charter is the authority; remove the config-absent all-four backfill (`pack_context.py:601-619`).
- **Relevant requirements**: FR-007, FR-008; preserves C-008.
- **Affected surfaces**: `charter/pack_context.py`, `charter/mission_type_profiles.py`; `tests/charter/test_pack_context.py`, `test_mission_type_activation_gating.py`.
- **Sequencing/depends-on**: **must follow IC-05** (provisioning before removal).
- **Risks**: NFR-003 parity measured at the **activation authority** (`existing_mission_types`/drg gating), NOT `list_available_missions`; keep T034 (custom type) + T036 (subset); NFR-001 arch test targets only the `mission_type_activations` fallback, not `_read_activated_kinds`.

### IC-05 — Fail-closed provisioning (fresh-init + migration), copy not re-scan

- **Purpose**: Seed the activation surface from `packs/default.yaml` at fresh `init` by **copying its authored list** (not re-scanning via the resolver — keeps IC-02→IC-05 decoupled); keep both rc35 migrations; fail closed if `default.yaml` is unprovisionable.
- **Relevant requirements**: FR-009, FR-010, FR-011; NFR-004.
- **Affected surfaces**: `specify_cli/cli/commands/init.py` (re-anchor around #3211's `_REVIEW_CYCLE_GITATTRIBUTES_ENTRY`), read `charter/packs/default.yaml`, both `m_3_2_0rc35_*` migrations (kept), a shared provisioning helper; `tests/upgrade/*`, new init-provisioning test.
- **Sequencing/depends-on**: none (root); gates IC-04.
- **Risks**: idempotence + customization-safety (no catalog intersection); **must copy default.yaml, not re-derive via `builtin_mission_type_id_set()`** (else IC-02 becomes a hard upstream dep).

### IC-06 — Scope-fence + no-second-source regression guards

- **Purpose**: Prove the foundation stayed scoped and single-sourced.
- **Relevant requirements**: NFR-001, NFR-002, NFR-005; C-001, C-003. (C-002/C-004 are review-only fences — no automatable marker; optional guard: assert `built_in_dir(kind)` gains no mission-type entry.)
- **Affected surfaces**: `tests/architectural/` — single-resolver invariant, `MissionTypeNotAnArtifactKind` raised, availability readers unchanged, layer + terminology.
- **Sequencing/depends-on**: follows IC-01 and IC-04.
- **Risks**: arch gates vacuous inside a worktree — verify from the primary checkout (tracer W3).

**Suggested sequencing** (finalized at `/spec-kitty.tasks`): IC-05 → IC-04 (provision before removing fallback); IC-01 → IC-02 → IC-03 (#3210 chain; IC-01 owns the primitive IC-02 delegates to); IC-06 verifies last. IC-01 and IC-05 are independent roots. The "#3210-first" preference is soft (the chains edit largely disjoint files); IC-01→IC-02 is the only hard resolver-chain edge.
