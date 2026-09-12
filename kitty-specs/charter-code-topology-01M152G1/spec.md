# Mission Specification: Charter Code Topology (retire-doctrine-term M2)

**Mission Branch**: `feat/charter-code-topology` (stacked on M1 `feat/charter-authority-flip` / #3791)
**Created**: 2026-08-28
**Status**: Draft — planning only; implementation deferred until M1 (#3791) merges.
**Input**: Wave **M2** of `retire-doctrine-term-01M0JMK9` (#3664). Relocate the `src/doctrine/**` code topology into `src/charter/**` and rename every code/import/build/CLI/serialized/API/workflow/metadata coordinate of the retired `doctrine` token, establishing invariant **I2**. Authority: ADR `2026-08-22-2` §5; stacked-plan M2 row; methodology §1.3(2), §3.3.

**Scale (censused at M1 tip):** `src/doctrine/**` = **265 files** (83 py); **825 files** import the doctrine package; `src/charter/**` = 123 files (collision target). occurrence_map = **13,344 rows** across 22 OC classes. This is an architectural refactor, not a term flip.

## Governing design (fixed by ADR + #3684 fold)

`src/doctrine/**` splits into **two modules under `src/charter/`**, preserving the offer→activate layer that the retired-but-real `doctrine` package encoded:
- **`src/charter/offering/`** — the pure offer catalogue (mission types, step contracts, gates, assets; the former doctrine artefacts). **MUST NOT import `charter.activation`** (C-004, the invariant `test_layer_rules.py` enforced for free via top-level package separation).
- **`src/charter/activation/`** — the current charter activation code (activation_engine, cascade, kind_vocabulary, …). **MAY import `charter.offering`.**

A new intra-package AST gate `test_charter_offering_does_not_import_activation` replaces the lost `LayerRule` edge and is a **hard M2 exit criterion** (not a CR-budgeted exception). `test_layer_rules.py` + `test_kernel_no_doctrine_import.py` are **re-homed** with the layer-chain literal updated (`doctrine` node → the intra-charter split).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The topology map is frozen and approved before any source edit (Priority: P1)

A maintainer approves a complete, set-equal `canonical-operator-surface-map.md` (`MAP-###` rows: every collision resolved `merge-existing`/`relocate`, the two module names + boundary fixed) and `canonical-cli-route-map.md` (sorted `surface_kind=cli` projection incl. nested routes) **before the first `git mv`**.

**Why this priority**: A 265-file move + 825-importer closure with no frozen map is unreviewable and unrollbackable. The map is the merge gate's diff surface. This is M2's single bounded design question (§3.2).

**Independent Test**: `test_topology_map_set_equality_and_closure` + `test_cli_route_map_set_equal_and_canonical` — the map is set-equal to every M2-owned occurrence hit and every discovered producer/consumer; the CLI projection is canonical and complete.

**Acceptance Scenarios**:
1. **Given** the frozen I1 tree, **When** the map is built, **Then** every M2-owned occurrence and every `files("doctrine")` / `.kittify/doctrine` / collision site appears as a `MAP-###` row with a `merge-existing` or `relocate` disposition, and the set is closed (no unmapped producer/consumer).

### User Story 2 - `src/doctrine/**` is relocated into the two-module split with the boundary enforced (Priority: P1)

`src/doctrine/**` is gone; its content lives under `src/charter/offering/` (catalogue) and the charter activation code under `src/charter/activation/`, with the one-way import rule enforced by a new AST gate.

**Why this priority**: This is the mission's core deliverable (I2) and the C-004 risk the #3684 squad flagged.

**Independent Test**: `test_charter_offering_does_not_import_activation` (hard exit); `src/doctrine/` directory absent; re-homed `test_layer_rules.py`/`test_kernel_no_doctrine_import.py` green.

**Acceptance Scenarios**:
1. **Given** the relocation, **When** the AST gate runs, **Then** no module under `charter.offering` imports `charter.activation`; `activation`→`offering` is allowed.
2. **Given** the collision set (`__init__.py`, `pack_paths.py`, `provenance.py`, `resolver.py`, `template_catalog.py`, `versioning.py`, `errors.py`, `exceptions.py`, `primitives.py`; `Directive`, `DoctrineService`, `canonical_yaml`), **When** relocated, **Then** each is `merge-existing` into the exact target or `relocate`, never merged into a facade.

### User Story 3 - Every importer + build/wheel/CLI/CI coordinate is closed with compat shims (Priority: P1)

All 825 importers resolve; import/build/wheel closure holds per dependency slice; renamed CLI group / tracker mode / config key / URN prefix carry deprecation-warning compat readers (CR-02…CR-07).

**Why this priority**: A partial closure breaks import/build mid-tree; missing a compat shim fails-closed for consumers.

**Independent Test**: `test_doctrine_group_hidden_alias_warns` + `test_charter_group_canonical_routes`; `test_tracker_doctrine_mode_alias_warns` + `test_tracker_ownership_mode_canonical`; `test_org_pack_config_doctrine_key_warns`; `test_urn_doctrine_prefix_parsed_with_warning` + `test_urn_charter_prefix_canonical`; `test_doctrine_import_shim_warns` + `test_charter_api_is_canonical_surface`; `test_old_root_read_warns_and_migrates`; wheel/import/build closure per slice.

**Acceptance Scenarios**:
1. **Given** a renamed surface (CLI group, tracker mode, `doctrine.org.packs`→`charter_packs.org.packs`, `doctrine:<kind>:<id>`→`charter:<kind>:<id>` URN, `import doctrine`, `.kittify/doctrine/`), **When** the legacy form is used, **Then** it resolves with a one-time deprecation warning and maps forward (CR-02…07 within budget).

### Edge Cases
- `importlib.resources.files("doctrine")` sites — every one retargeted before a package-named shim lands, or resource resolution breaks.
- The dormant `spec-kitty-doctrine` wheel manifest — disposed per its map row (delete-vs-rename).
- Architectural baselines/allowlists (OC-22/OC-23) — **retargeted, never deleted** (retiring a token must not silently drop a gate).

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | Priority | Status |
|----|-------|----------|--------|
| FR-001 | Frozen `canonical-operator-surface-map.md` + `canonical-cli-route-map.md`, set-equal + closed, approved pre-edit | High | Open |
| FR-002 | `src/doctrine/**` → `src/charter/offering/` + `src/charter/activation/` two-module split | High | Open |
| FR-003 | New `test_charter_offering_does_not_import_activation` AST gate (hard exit); re-home `test_layer_rules.py` + `test_kernel_no_doctrine_import.py` | High | Open |
| FR-004 | Close all 825 importers; import/build/wheel closure per dependency slice | High | Open |
| FR-005 | CR-02…CR-07 compat shims (CLI group, tracker mode, `doctrine.org.packs`, URN prefix, import shim, `.kittify/doctrine` dual-root) with deprecation warnings | High | Open |
| FR-006 | Retarget live architectural baselines/allowlists (never delete); dispose dormant `spec-kitty-doctrine` manifest | Medium | Open |
| FR-007 | Closing audit: no M1/M2-owned live code/pathname hit outside registered CR-02…07; `src/doctrine/` absent | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Priority | Status |
|----|-------|-------------|----------|--------|
| NFR-001 | Import/build/wheel green per slice | Every dependency slice leaves import + `hatch` build + wheel resolution green | High | Open |
| NFR-002 | Archive gate byte-identical | Four exclusion roots unchanged (`test_archive_root_byte_identical`) | High | Open |
| NFR-003 | Clean static analysis | `ruff` + `mypy` zero issues; terminology guard green; full `tests/architectural/` sweep green | High | Open |

### Constraints

| ID | Title | Constraint | Priority | Status |
|----|-------|------------|----------|--------|
| C-001 | `bulk_edit` change mode | `occurrence_map.yaml` classifies all 13,344 rows (22 OC classes) across the 8 categories | High | Open |
| C-004 | Offer↛activate boundary | `charter.offering` MUST NOT import `charter.activation`; enforced by the new AST gate as a hard exit (preserves the retired-package layer edge) | High | Open |
| C-002 | Stacks on M1 | Base = M1 closing manifest (`feat/charter-authority-flip` / #3791); rebase onto merged main before implementation | High | Open |
| C-003 | Map-first | The topology + CLI map is approved before the first source edit; it cannot change scope/order/terminal-zero rule | High | Open |

## Success Criteria *(mandatory)*

- **SC-001**: Topology + CLI maps frozen, set-equal, closed, approved pre-edit. (`test_topology_map_set_equality_and_closure`, `test_cli_route_map_set_equal_and_canonical`)
- **SC-002**: `src/doctrine/` absent; two-module split with the offering↛activation AST gate green (hard exit); layer gates re-homed green. (`test_charter_offering_does_not_import_activation`)
- **SC-003**: All 825 importers + build/wheel/CLI/CI closed; CR-02…07 shims warn+map within budget. (the 12 CR/surface tests + per-slice closure)
- **SC-004**: Closing audit clean (no M2-owned live hit outside CR-02…07); archive + shrink-only guards green; full `tests/architectural/` sweep green.
