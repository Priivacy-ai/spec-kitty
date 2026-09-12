# Mission Specification: Charter Activation Split (retire-doctrine-term M2b)

**Mission Branch**: `feat/charter-activation-split` (on merged main; M1+M2 landed)
**Created**: 2026-08-29
**Status**: Draft — planning; execution gated on operator approval of the frozen topology map.
**Input**: Wave **M2b** of `retire-doctrine-term-01M0JMK9` (#3664) — the physical `offering ↔ activation` two-module split deferred from M2. Relocate the activation-side charter modules into `src/charter/activation/`, make `charter/__init__.py` lazy, close all importers, and collapse the C-004 gate to a real `charter.activation.*` package wall.

**Scale**: 66 top-level `charter/*.py` + subpackages; **355 files** import an activation module (75 src, 239 tests, 40 charter-internal). Latent offering→activation violations: **0** (boundary already holds; M2b makes it a wall). Not a term change — a package reorganization.

## User Scenarios & Testing

### US1 — `charter.offering` imports no longer drag the activation layer (P1)
Making `charter/__init__.py` lazy (PEP-562) severs the eager parent-drag; `import charter.offering.X` stops transitively importing `compiler`/`sync`/`context`/… This un-xfails `test_interview_mapping_mission_alias` (the M2-deferred roster-isolation test).
**Test**: the xfail flips to hard pass; a targeted import assert that `charter.offering.*` does not pull `charter.activation.*`.

### US2 — the activation layer is a real package with an enforced boundary (P1)
`src/charter/activation/` houses the activation modules; the C-004 AST gate forbids `charter.offering` → `charter.activation.*` (collapsed from the M2 interim explicit set).
**Test**: `test_charter_offering_does_not_import_activation` green against the real package; `src/charter/activation/` present.

### US3 — every importer closed, no behavior change (P1)
The 75 `src/` + 239 test deep-path `from charter.<name> import` callers re-point to `charter.activation.<name>`; import/build/CLI green; no serialized-surface or CR shim breaks.
**Test**: full suite green (arch shards + docs freshness + terminology baselines included — the M2 landing-pass blind spot); CLI + `import doctrine` (warns) OK.

## Requirements
| ID | Title | Priority |
|----|-------|----------|
| FR-001 | Relocate the MAP-A activation set + `synthesizer/**` → `src/charter/activation/` | High |
| FR-002 | Lazy `charter/__init__.py` (PEP-562 `__getattr__` table; `__all__` verbatim) | High |
| FR-003 | Close all 355 importers (rewrite deep-path call sites to `charter.activation.*`) | High |
| FR-004 | Collapse C-004 gate to `{"charter.activation"}`; un-xfail the roster test | High |
| FR-005 | Resolve DEC-1 (`drg.py` split) + DEC-2 (5 subpkgs) before the map freeze | High |
| FR-006 | Keep the 13 offering facades + shared primitives top-level (MAP-C12) | High |

## Constraints
| ID | Constraint | Priority |
|----|------------|----------|
| C-001 | `bulk_edit` change mode; occurrence-map governs the call-site rewrite | High |
| C-004 | `offering` MUST NOT import `activation` — now a package wall | High |
| C-002 | Offering facades + `resolution`/`parser`/`bundle` stay top-level `charter.*` (MAP-C12) | High |
| C-003 | Map-first: no `git mv` until the frozen `activation-topology-map.md` is approved | High |

## Success Criteria
- **SC-001**: `src/charter/activation/` exists; the C-004 gate is a real package wall (collapsed to `charter.activation`), green.
- **SC-002**: `charter/__init__.py` lazy; the roster xfail flips to hard pass; `charter.offering.*` imports don't pull activation.
- **SC-003**: All 355 importers closed; full-sweep verify green; no CR/serialized shim regression.
