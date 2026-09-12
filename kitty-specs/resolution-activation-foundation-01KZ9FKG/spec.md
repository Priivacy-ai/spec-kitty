# Mission Specification: Resolution & Activation Foundation

**Mission Branch**: `feat/resolution-activation-foundation`
**Created**: 2026-08-05 · **Revised**: 2026-08-05 (post-#3211, post-review-squad — DR-1/DR-2 + M3/M4 + folds)
**Status**: Draft
**Input**: Bundle #2657 (provisioned default charter as the single mission-type activation authority) + #3210 (unify built-in mission-tree resolution). Governing decision + addendum: [`docs/adr/3.x/2026-08-05-1-mission-type-availability-before-kind-promotion.md`](../../docs/adr/3.x/2026-08-05-1-mission-type-availability-before-kind-promotion.md). Review findings: [`post-plan-review-findings.md`](./post-plan-review-findings.md).

## Overview

Spec Kitty is moving mission types toward being **fully doctrine-provided and charter-activated**. That end state (issue #2652 / #2468 family) has been deferred by several missions because it rests on two foundations that were never built. This mission builds both — and stops there, so the follow-on (#2659) is a wiring step, not another deferral.

1. **One resolution primitive (#3210, DR-1).** After PR #3204 relocated built-in mission data to `packs/built-in/missions/`, that tree is resolved by two functions with disjoint callers (`get_package_asset_root` and `default_missions_root`), only one env-aware — a split-brain. The `built-in` pack (missions included) is installed/available from the default- or env-supplied pack root (`SPEC_KITTY_PACKS_ROOT`). This mission makes the mission-tree `<built-in-pack-root>/missions` resolved through **one** primitive: the kernel floor owns a PACKS_ROOT-aware built-in-pack-root resolver; `doctrine.pack_paths` and `default_missions_root` and the door all consume it downward.
2. **One activation authority (#2657).** The implicit "all four" backfill in `charter/pack_context.py` is removed; the provisioned `packs/default.yaml` becomes the single authority, with fail-closed provisioning at fresh-init and legacy-migration.

**This mission prepares the resolver and the authority; it does NOT repoint the availability readers (that is #2659).** The two halves edit largely disjoint files; the coupling is a foundation/sequencing pairing.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - One PACKS_ROOT-aware resolution primitive (Priority: P1)

A Spec Kitty maintainer, and any consumer relocating the pack tree via `SPEC_KITTY_PACKS_ROOT`, needs the tool to locate built-in mission files through exactly one primitive, so that every reader — the `get_package_asset_root` door *and* `default_missions_root` — relocates together and cannot diverge.

**Why this priority**: The duplicated, partially-env-aware resolution is the load-bearing ambiguity. Until there is one PACKS_ROOT-aware primitive, any later change to mission availability risks being applied to only one resolver and silently diverging.

**Independent Test**: With `SPEC_KITTY_PACKS_ROOT` set, both the door and `default_missions_root` resolve the missions tree under the relocated pack root; an architectural test confirms one resolver primitive and one ancestor-walk definition.

**Acceptance Scenarios**:

1. **Given** the shipped tree, **When** an architectural test enumerates the built-in-pack-root resolution logic, **Then** the `SPEC_KITTY_PACKS_ROOT` env read lives in exactly one place (the kernel primitive); `doctrine.pack_paths._resolve_built_in` and `default_missions_root` and the door delegate to it; and `_find_relocated_missions_ancestor` has exactly one definition.
2. **Given** `SPEC_KITTY_PACKS_ROOT=<relocated>` with `<relocated>/built-in/missions` present, **When** either `default_missions_root()` or `get_package_asset_root()` resolves, **Then** both resolve under `<relocated>` — the same tree.
3. **Given** both `SPEC_KITTY_PACKS_ROOT` and `SPEC_KITTY_TEMPLATE_ROOT` are set, **When** the built-in pack root is located, **Then** `SPEC_KITTY_PACKS_ROOT` governs pack-root location and wins; `SPEC_KITTY_TEMPLATE_ROOT` continues to govern only the asset-copy/template path (its existing role is preserved for `template/manager.py`, `init.py`, `bootstrap.py`, and the upgrade migrations).
4. **Given** `kernel/__init__.py`, `kernel/README.md`, and `doctrine/missions/repository.py:37-44`, **When** a reader consults the "re-export"/`dev_roots` claims, **Then** each accurately describes the real topology (no false "re-exported by `specify_cli.runtime.home`" claim; no non-existent `dev_roots` tuple).
5. **Given** an env var pointing at a path with no `built-in/missions` tree, **When** resolution runs, **Then** it fails closed (no fall-through to `specify_cli/missions` or an arbitrary tree).

---

### User Story 2 - One activation authority, no silent backfill (Priority: P1)

An operator initializing a new project, and one upgrading a legacy project, both need the set of mission types their project has to come from one authoritative, explicit source — the provisioned default charter — never an implicit code default.

**Why this priority**: The implicit fallback is the hidden second availability source; it must be removed for the activation set to be trustworthy, but removal without provisioning breaks every project — so provisioning and removal ship together, fail-closed.

**Independent Test**: A fresh project has an explicit, non-empty `mission_type_activations` seeded from `packs/default.yaml`; removing the implicit fallback changes nothing a provisioned project offers *through the activation authority*.

**Acceptance Scenarios**:

1. **Given** a brand-new `spec-kitty init`, **When** it completes, **Then** the project config carries an explicit `mission_type_activations` set copied from the provisioned default charter (not re-derived by scanning the tree).
2. **Given** a config with no `mission_type_activations` key and the implicit fallback removed, **When** the activation set is read, **Then** it resolves from the provisioned charter if present, or fails closed with an actionable error — never a silent full-roster backfill.
3. **Given** a project whose activation set includes a custom (non-built-in) mission type, **When** provisioning runs or re-runs, **Then** the custom entry is preserved (no intersection against the built-in catalog).
4. **Given** a broken install missing `packs/default.yaml`, **When** init or migration provisions, **Then** it fails closed with an actionable error.

---

### User Story 3 - The foundation stays scoped (Priority: P2)

A reviewer needs proof this mission built only the two foundations and did not smuggle in the deferred, higher-risk work.

**Why this priority**: The repeated deferral came from conflating these foundations with the blocked work. A regression fence keeps the slice honest.

**Independent Test**: Regression tests confirm `mission-type` is still not an ArtifactKind and the availability readers are unchanged.

**Acceptance Scenarios**:

1. **Given** the merged mission, **When** a test asserts the artifact-kind contract, **Then** `MissionTypeNotAnArtifactKind` is still raised and `_MISSION_TYPE_UNIVERSE_EXTENSION` is intact.
2. **Given** the merged mission, **When** the availability readers are inspected, **Then** `list_available_missions` and `_build_discovery_context` are unchanged (filesystem-based) and `src/specify_cli/missions/` is not deleted.

### Edge Cases

- **Config present but `mission_type_activations: []`**: means the empty set (an authored choice), never a backfill (preserves the pre-existing authored-empty-list contract). Distinct from the `_read_activated_kinds` empty-list fallback, which is a different contract and is out of scope.
- **`SPEC_KITTY_PACKS_ROOT` set to a path with no `built-in/missions`**: fail closed, never fall through.
- **Both env vars set**: PACKS_ROOT wins for pack-root location; TEMPLATE_ROOT still overrides the copy path.
- **Legacy layout with a `specify_cli/missions` tree but no `packs/built-in/missions`**: the door no longer resolves to `specify_cli/missions` (DR-2) — it fails closed. The drop is intended; the missing-`packs` behavior is contract-pinned.
- **Provisioning re-run on an already-provisioned project**: idempotent (byte-identical config), custom entries retained.
- **Monkeypatch seams** in `tests/runtime/test_home_unit.py`: retargeted onto the surviving primitive, not orphaned.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Single built-in-pack-root resolution primitive | As a maintainer, I want the `SPEC_KITTY_PACKS_ROOT` read + built-in-pack-root resolution to live in exactly one kernel-floor primitive that `doctrine.pack_paths._resolve_built_in`, `default_missions_root`, and the `get_package_asset_root` door all delegate to, so resolution cannot diverge. | High | Open |
| FR-002 | De-duplicate the ancestor walk | As a maintainer, I want a single `_find_relocated_missions_ancestor` definition so the relocated-root walk has one behavior. | High | Open |
| FR-003 | Missions tree = `<built-in-pack-root>/missions` | As a consumer, I want `default_missions_root()` to resolve as `built_in_root()/"missions"` so it honors `SPEC_KITTY_PACKS_ROOT` by construction, like every other built-in kind. | High | Open |
| FR-004 | Env precedence: PACKS_ROOT governs pack-root location | As a consumer, I want `SPEC_KITTY_PACKS_ROOT` to govern built-in-pack-root location and win when both env vars are set, while `SPEC_KITTY_TEMPLATE_ROOT` retains its asset-copy/template-override role, documented and tested. | High | Open |
| FR-005 | Correct false documentation | As a reader, I want the false "re-exported by `specify_cli.runtime.home`" claims (`kernel/__init__.py`, `kernel/README.md`) and the non-existent `dev_roots` note (`doctrine/missions/repository.py:37-44`) corrected to the real topology. | Medium | Open |
| FR-006 | Retire the runtime second copy; fail-closed | As a maintainer, I want the parallel resolution stack in `specify_cli/runtime/home.py` collapsed onto the single primitive, dropping its `specify_cli/missions`/`dev_root` legacy fallbacks (fail-closed), with the surviving content detector using the enumeration-free wildcard. | High | Open |
| FR-007 | Provisioned charter is the activation authority | As an operator, I want the activation set read from the provisioned default charter, not an implicit code default. | High | Open |
| FR-008 | Retire the implicit "all four" fallback | As an operator, I want the config-absent backfill at `pack_context.py:601-619` removed so absent config resolves via provisioning or fails closed. | High | Open |
| FR-009 | Fresh-init provisioning (copy, not re-scan) | As an operator, I want `spec-kitty init` to seed `mission_type_activations` by copying the provisioned `packs/default.yaml` authored list (not by re-scanning the tree), so a fresh project has an explicit set independent of the resolver env. | High | Open |
| FR-010 | Legacy-migration provisioning preserved & customization-safe | As an operator upgrading, I want the two rc35 migrations kept and provisioning to preserve custom activation entries (no catalog intersection). | Medium | Open |
| FR-011 | Fail-closed on unprovisionable install | As an operator, I want init/migration to fail with an actionable error when `packs/default.yaml` cannot be provisioned. | High | Open |
| FR-012 | Single authority for the missions sibling pattern | As a maintainer, I want the `packs/built-in/missions` shape owned once (the kernel `built-in` pattern + the existing `missions` leaf name), so the three drifting per-module constants (`kernel/paths.py`, `doctrine/missions/repository.py`, `agent_commands.py`) collapse onto it. | Medium | Open |
| FR-013 | Fail-closed resolution is explicit | As a maintainer, I want resolution to raise a closed, named error when the tree is absent (never a silent nonexistent path), pinned by a contract. | Medium | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | No second resolution/availability source | An architectural test asserts: 0 second `SPEC_KITTY_PACKS_ROOT` read outside the kernel primitive, 0 second `get_package_asset_root` body, 0 implicit config-absent all-four fallback site. Present and green. Scope: the `mission_type_activations` fallback specifically — NOT the `_read_activated_kinds`/directive three-state fallbacks. | Maintainability | High | Open |
| NFR-002 | Layer integrity | `kernel` retains 0 import edges to `doctrine`/`specify_cli` (the PACKS_ROOT env read moving to kernel adds no upward edge); existing layer/AST gates stay green (0 new upward edges). | Architecture | High | Open |
| NFR-003 | No behavior change at the activation authority + resolved paths | For a normally-provisioned project under default env: 0 diff in the set returned by the **activation authority** (`charter.mission_type_profiles.existing_mission_types` / drg gating) — explicitly NOT `list_available_missions` (fenced unchanged) — and 0 diff in resolved mission-asset paths. | Compatibility | High | Open |
| NFR-004 | Provisioning idempotence | Re-running init/migration on a provisioned config yields byte-identical config (0 drift) and retains 100% of custom entries. | Reliability | High | Open |
| NFR-005 | Terminology canon | 0 new `feature*` identifiers/prose; `tests/architectural/test_no_legacy_terminology.py` green. | Compliance | Medium | Open |
| NFR-006 | Env-relocation regression coverage | A new test asserts the missions tree honors `SPEC_KITTY_PACKS_ROOT` (none exists today), including the both-vars precedence case (FR-004). Present and green. | Testability | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | OUT: mission-type-as-ArtifactKind | MUST NOT promote `mission-type`; `MissionTypeNotAnArtifactKind` stays raised, `_MISSION_TYPE_UNIVERSE_EXTENSION` intact (regression-asserted). #2468/#2467. | Scope | High | Open |
| C-002 | OUT: nested-vs-flat path decision | MUST NOT decide the `mission_types/` flatten-vs-nest question. #2468. **Review-only fence** (no positive code marker; not automatable). | Scope | High | Open |
| C-003 | OUT: availability-reader repoint & tree deletion | MUST NOT repoint `list_available_missions`/`_build_discovery_context` or delete `src/specify_cli/missions/`. #2659/#2660/#2661. | Scope | High | Open |
| C-004 | OUT: keystone & schema follow-up | MUST NOT attempt #2467 or the kernel↔doctrine schema decouple. **Review-only fence.** | Scope | High | Open |
| C-005 | Layer direction | Convergence flows downward (`kernel ← doctrine ← charter ← specify_cli`); the PACKS_ROOT-aware primitive lives in `kernel`; `kernel` imports no `doctrine`/`specify_cli`. | Technical | High | Open |
| C-006 | Quality gates | ATDD-first (C-011); tests for every new branch/helper in-PR; complexity ≤15; S1192 constants; `mypy --strict` + `ruff` clean; no new suppressions. | Technical | High | Open |
| C-007 | Preserve test seams | Monkeypatch seams in `tests/runtime/test_home_unit.py` retargeted, not orphaned, when `home.py` collapses onto the primitive. | Technical | Medium | Open |
| C-008 | Preserve authored-empty semantics | `mission_type_activations: []` stays the empty set — never provisioning/backfill (preserves the pre-existing authored-empty-list contract). | Technical | High | Open |
| C-009 | Preserve TEMPLATE_ROOT copy-path role | The unification MUST NOT break `SPEC_KITTY_TEMPLATE_ROOT` for the asset-copy/template path (`template/manager.py`, `asset_generator.py`, `init.py`, `bootstrap.py`, upgrade migrations); a door-caller census confirms it. | Technical | High | Open |

### Key Entities

- **Built-in-pack-root resolver (kernel primitive)**: the single PACKS_ROOT-aware entry point locating `packs/built-in`. Owned by `kernel`; consumed downward by `doctrine.pack_paths`, `default_missions_root`, and the door.
- **Missions root**: `<built-in-pack-root>/missions` — no longer a separately-anchored sibling walk.
- **Activation authority (`activated_mission_types` / provisioned charter)**: the single source of which mission types a project has; provisioned from `packs/default.yaml`.

## Success Criteria *(mandatory)*

- **SC-001**: The `SPEC_KITTY_PACKS_ROOT` read + built-in-pack-root resolution exists in exactly one place (kernel), verified by an architectural test; one `_find_relocated_missions_ancestor` def; one `get_package_asset_root` body.
- **SC-002**: A new regression test proves both `default_missions_root()` and the door relocate via `SPEC_KITTY_PACKS_ROOT` (including both-vars precedence) — a test that did not exist before — green.
- **SC-003**: A freshly `init`-ed project has an explicit, non-empty `mission_type_activations` copied from `packs/default.yaml` (not re-scanned).
- **SC-004**: Removing the implicit fallback yields 0 diff in the set returned by the **activation authority** for a provisioned project, and 0 diff in resolved mission-asset paths under default env.
- **SC-005**: A scope-fence regression test proves `mission-type` is still not an ArtifactKind and the availability readers are unchanged.
- **SC-006**: Full architectural suite (layer, terminology, built-in-location authority) green with 0 new suppressions.

## Assumptions

- `src/charter/packs/default.yaml` already carries the full activation surface (verified); this mission wires it as the authority + adds fresh-init provisioning, not new default content.
- Both `3.2.0rc35` migrations remain unchanged (operator decision); no consolidation.
- "The four built-in types" is never a literal — the roster is the disk-scanned `builtin_mission_type_id_set()`.
- Post-#3211: the only surface overlap is `init.py` (a gitattributes constant); FR-009 provisioning re-anchors around #3211's additions.

## Dependencies

- Governing ADR `docs/adr/3.x/2026-08-05-1-…` (Accepted, with the 2026-08-05 DR-1/DR-2 addendum).
- Downstream (not this mission): #2659 repoints availability readers onto the resolver + authority this mission establishes.
