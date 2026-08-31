# Implementation Plan: Charter Code Topology (retire-doctrine-term M2)

**Branch**: `feat/charter-code-topology` (stacked on M1 `feat/charter-authority-flip` / #3791) | **Date**: 2026-08-28
**Status**: **Planning only.** Implementation deferred until M1 (#3791) merges; then rebase onto merged `main` and re-derive the frozen topology map on that base.
**Input**: Wave M2 of `retire-doctrine-term-01M0JMK9` (#3664). Authority: ADR `2026-08-22-2` §5; stacked-plan M2 row (`stacked-plan.md:109-125`); methodology §1.3(2), §3.3.

Planning informed by a 3-scout brownfield squad (two-module split, import/build closure, serialized-surface CR shims). Their scope corrections are binding.

## Scope corrections from the squad (BINDING — resize the mission)

- **SC-1 — Two `doctrine` packages; only one relocates.** The top-level `doctrine` (`src/doctrine/`) relocates. **`specify_cli.doctrine*` / `doctrine_synthesizer` / `doctrine_service_factory` / `org_charter` are a SEPARATE package — OUT OF SCOPE** (323 imports / 94 files a naive regex would wrongly sweep). Every occurrence rule scopes to **top-level `doctrine`**.
- **SC-2 — Live census, not the frozen literals.** `src/doctrine` = **96 `.py`** (spec said 83); `src/charter` = 113 `.py`. **730** `from doctrine.X import Y` (hard rewrites) + **7** bare/module-form (shim-absorbable) + **0** `src.doctrine`. Importer files: 456 (320 tests, 64 intra, **53 `src/charter`** = the CR-06 sizing / 158 edges). The map's set-equality gate must be built from a fresh census at implementation time.
- **SC-3 — One token, five serialized classes, THREE target words.** Keying the occurrence map on the bare token `doctrine` is wrong: it lumps five distinct owners and hides that **tracker mode renames to `ownership`, not `charter`**. Per-surface occurrence classes with distinct target strings are mandatory.
- **SC-4 — Census blind spots.** Split/assembled literals have no contiguous token to match: `_DOCTRINE_BASE = Path(".kittify")/"doctrine"` (`apply.py:187`), `_DOCTRINE_DIRNAME` (`write_pipeline.py:62`, `reconcile.py:67`). Normalize these to route through the CR-07 helper BEFORE trusting any "0 remaining" census. Census is also structurally blind to the out-of-tree `spec_kitty_events` conformance fixture (CR-05) — a paired cross-package change.

## Governing design — the two-module split

All of former `src/doctrine/**` → **`src/charter/offering/`** (pure offer catalogue). The **`src/charter/activation/`** module is populated from the *current* `src/charter` activation code (`activation_engine`, `cascade`, `kind_vocabulary`, `synthesizer/`, `compiler`, `interview`, `sync`, the `resolver.py` wrapper, …). Boundary: **`offering` MUST NOT import `activation`** (C-004); `activation` MAY import `offering`.

- **Zero `offering→activation` edges exist today** — `doctrine` is a leaf below `charter` (0 real `doctrine`→`charter` code imports; 54 files/162 lines `charter`→`doctrine` = the correct consumer direction, becomes `activation`→`offering`). The new AST gate guards **future** regressions.
- **Name-trap**: `doctrine/spdd_reasons/activation.py` is an offer-side read-only predicate → **`offering`** despite its name. State it in the map.

### Collision set dispositions (`src/doctrine` vs existing `src/charter`)
| Kind | Names | Disposition |
|------|-------|-------------|
| **Collapse-facade** (charter copy is a pure re-export) | `pack_paths`, `provenance`, `template_catalog`, `versioning`, `primitives` | relocate real → `offering/`; collapse the charter facade to a **top-level `charter.*` CR-06 shim** (NOT inside `offering/` or `activation/` — placement matters or it manufactures an offering→activation edge) |
| **Relocate-both-distinct** (genuinely different offer vs activation impls — NEVER merge) | `resolver.py`/`DoctrineService`, `exceptions.py`, `errors.py`, symbol `Directive` | offer → `offering/…`; activation → `activation/…` |
| **De-dup fold** | `canonical_yaml` (doctrine `yaml_utils.py:24` SSOT vs synthesizer `synthesize_pipeline.py:157` independent duplicate — a live drift) | relocate SSOT → `offering/yaml_utils.py`; fold the synthesizer copy to delegate |
| **Role-split relocate** | `__init__.py` (16 sub-pkg inits) | inits travel into `offering/**`; `charter/__init__.py` stays as parent of both sub-modules |

## Phase 0 — Frozen topology map (FR-001, the ONE bounded design question)

Before the first `git mv`, freeze + get maintainer approval for `canonical-operator-surface-map.md` (`MAP-###` rows: every collision `merge-existing`/`relocate`, the two module names, the spdd_reasons/activation placement, the canonical_yaml fold, facade placements) + `canonical-cli-route-map.md` (sorted `surface_kind=cli` projection incl. nested routes). Gates: `test_topology_map_set_equality_and_closure`, `test_cli_route_map_set_equal_and_canonical`. Built from a **live census at the rebased base**, not the stacked one.

## Phase 1 — Implementation slices (dependency-ordered; import/build green per slice)

- **S1 — Skeleton + AST gate + layer re-home** (map approved first): create `src/charter/offering/` + `src/charter/activation/` package roots; author the new **`test_charter_offering_does_not_import_activation`** gate (copy `tests/architectural/test_charter_no_specify_cli_import.py`; **add level-aware `ast.ImportFrom` resolution** for relative `from ..activation import` + a `tmp_path` non-vacuity case for the relative form); re-home `conftest.py:89` landscape (drop `doctrine` node), `test_layer_rules.py` `_DEFINED_LAYERS`, `test_kernel_no_doctrine_import.py` (`_FORBIDDEN_IMPORT_ROOTS` doctrine→charter; **retarget** the 2 `kernel/schema_utils.py` exemptions, never delete).
- **S2 — Relocate offering + CR-06 import shim**: `git mv src/doctrine/** → src/charter/offering/**`; collapse the 5 facades to top-level `charter.*` shims; the CR-06 module-only shim (budget 8) covers the 7 bare/module-form call sites (`__getattr__` re-export from `runtime/next/__init__.py` mechanics + warn-once from `retrospective/deprecation.py` + identity-guard from `test_charter_facades_reexport_doctrine.py`; register in `compat/shim-registry.yaml`). Retarget the 13 `files("doctrine")` resource sites + `kernel/schema_utils.py:22` + `kernel/sibling_paths.py:45` FIRST.
- **S3 — Importer closure** (the 730 `from doctrine.X` rewrites → `charter.offering.*`/`charter.activation.*` across 456 files; the 53 `src/charter` files split by boundary). Import/build closure verified per dependency slice.
- **S4 — Serialized-surface CR shims** (each replicates the CR-01 read-both/canonical-wins/warn-once pattern at `src/charter/sync.py:278-311`):
  - **CR-02** CLI group: `doctrine` typer group `deprecated=True` + callback stderr warn → delegate. **Do NOT fold `doctrine mission-type` (activation-blind) into `charter mission-type` (activation-filtered)** — resolve the semantics split (a `--include-inactive` flag or a distinct home). `__init__.py:258,293`, `doctrine.py:60,67,74,81,87`.
  - **CR-03** tracker `doctrine`→**`ownership`** (target word differs!): 6 sites `tracker/config.py:125-126,176-178,192,200-209`, `tracker.py:422,624-626,720-721,899`, `saas_service.py`; dual-key reader + `--doctrine-mode` hidden alias; **machine-status payload is a downstream contract**.
  - **CR-04** `doctrine.org.packs`→`charter_packs.org.packs`: `org_pack_config.py:~573,462-485` reader/writer; add as the 3rd accepted shape (charter_packs → doctrine.org → legacy organisation_packs).
  - **CR-05** URN `doctrine:<kind>:<id>`→`charter:`: producer `doctrine_synthesizer/apply.py:409,663` ONLY (NOT `drg/merge.py`/`models.py` — different two-part URN space); event/`target_urn` validators accept both for the window (durable event-log contract); external `spec_kitty_events` fixture = paired change.
  - **CR-07** `.kittify/doctrine/`→`.kittify/charter-packs/` dual-root reader (42 src files); **normalize the split-literal constants first** (`_DOCTRINE_BASE`, both `_DOCTRINE_DIRNAME`) so every path routes through the shim.
- **S5 — Build/wheel/CI + closing audit**: `pyproject.toml` (149 packages, 152-163 exclude, **178-186 artifacts — WIDEN charter globs to `.md/.json/.csv/.template`**, 201-210 sdist, 488), `release.yml:210-245` counts; **delete** the dormant `spec-kitty-doctrine` wheel (`src/doctrine/pyproject.toml` + `hatch_build.py` + `tests/doctrine/test_hatch_build.py` + `test_doctrine_wheel_closure.py`); skills tree `git mv` + registry/wheel/release retargets (IDs stay → M4); retarget baselines/allowlists (never delete); closing audit + shrink-only guard + archive gate.

## Risk register (from squad findings)

| # | Risk | Mitigation |
|---|------|-----------|
| R1 | Bulk regex sweeps `specify_cli.doctrine*` (out of scope) | Scope every rule to top-level `doctrine`; exclude `specify_cli.doctrine`/`doctrine_synthesizer`/`org_charter` |
| R2 | **Wheel silent-drop** — charter artifact globs ship only `*.yaml`; a mechanical move ships zero skills/schemas/mission data | Widen `pyproject.toml` artifacts to `.md/.json/.csv/.template`; the `release.yml` count gate is the only catch — keep it |
| R3 | Tracker `doctrine` misfiled as `charter` (renames to `ownership`) | Per-surface occurrence class with target `ownership`; CR-03 distinct |
| R4 | Census reports "0 remaining" but split-literal constants keep the old root | Normalize `_DOCTRINE_BASE`/`_DOCTRINE_DIRNAME` through CR-07 shim before trusting the census |
| R5 | New AST gate misses a relative `from ..activation import` | Level-aware `ImportFrom` resolution + relative-form non-vacuity test |
| R6 | Facade collapsed inside `activation/` manufactures an offering→activation edge | Collapse every offer-facade to a top-level `charter.*` shim (outside both sub-modules) |
| R7 | CR-05 URN rewrite bleeds into `drg/merge.py` 2-part node URNs | CR-05 touches synthesizer target-URN only; do NOT touch drg endpoint resolution |
| R8 | `spec-kitty-doctrine` wheel renamed carries dead hatch machinery | Delete, not rename (#3101 charter-wheel is a separate deferred decision) |
| R9 | Retiring a token silently drops an architectural gate/baseline | Retarget baselines/allowlists, never delete (spec edge case) |

## Progress
- [x] Scope corrected via brownfield squad (SC-1…SC-4)
- [ ] Rebase onto merged `main` (after #3791) + fresh census
- [ ] Phase 0 frozen topology map (approved pre-edit)
- [ ] S1…S5 implementation
- [ ] Review squad, consolidation, docs/CHANGELOG, PR

## SCOPE AMENDMENT (operator decision, 2026-08-29) — M2 ships S2a; activation split → M2b

After S2a landed the token retirement (src/doctrine → src/charter/offering, package `doctrine` gone), the census showed the **full physical activation split** (relocating charter's own `sync`/`compiler`/`resolver`/`interview`/`pack_context`/… into `src/charter/activation/`) is a **439-file** closure that re-touches M1's freshly-landed CR-01 code — an S2a-scale mega-refactor for the architectural boundary alone.

**Operator decision:** ship S2a's token retirement as **M2** (+ S4 CR shims + S5 build/wheel/gate re-home), and carve the physical `offering ↔ activation` two-module split into a dedicated follow-up mission **M2b** (`charter-code-topology-b`). Rationale: S2a is a coherent, valuable deliverable; the activation split is separable, huge, and risky over M1's fresh code.

**Consequences:**
- The `test_charter_offering_does_not_import_activation` gate (S1) remains armed and green (offering does not import activation today); it fully engages when M2b physically creates `charter/activation/`.
- 2 tests carry the coupling that M2b resolves: `test_interview_mapping_mission_alias::test_synthetic_mission_type_is_picked_up_by_both_rosters` is xfail'd (strict=False) with an M2b reference; a 2nd import-order-pollution red (combined-suite only) is tracked for the closeout full-suite pass.
- M2b (to be created) owns: relocate the activation-side charter modules into `src/charter/activation/`, close the 439 importers, make `charter/__init__.py` lazy so `charter.offering.*` resolves without dragging activation, and flip the S1 gate + the two xfails to hard green.
