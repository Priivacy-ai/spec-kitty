# Implementation Plan: Charter Ownership Consolidation and Neutrality Hardening

**Branch contract**: planning/base `main` → merge target `main` (single branch; no divergence)
**Date**: 2026-04-17
**Spec**: [/Users/robert/spec-kitty-dev/charter/spec-kitty/kitty-specs/charter-ownership-consolidation-and-neutrality-hardening-01KPD880/spec.md](./spec.md)
**Mission ID**: `01KPD8804H8XZR8NJVJKV12HCW` · **mid8**: `01KPD880`
**Change mode**: `bulk_edit` (DIRECTIVE_035 applies; see `./occurrence_map.yaml`)

---

## Summary

Spec Kitty's charter package has **already been canonicalized in `src/charter/`**. The baseline inventory confirms `src/charter/` owns 18 modules and both hard-success-criterion functions (`build_charter_context()` at `src/charter/context.py:67`, `ensure_charter_bundle_fresh()` at `src/charter/sync.py:66`) have exactly one definition. The legacy `src/specify_cli/charter/` surface has collapsed to 4 pure re-export shims totalling 135 lines.

This mission therefore has **less implementation work than a naive read of #611 suggested** and can focus on three structural completions the baseline does not yet cover:

1. **Install explicit deprecation signalling** on the surviving shim package so external importers are warned and the removal release (one minor after landing) is documented — no shim currently emits `DeprecationWarning`, so FR-005 is not yet satisfied.
2. **Audit and migrate callable legacy imports** while preserving intentional C-005 compatibility coverage. A naive `specify_cli.charter → charter` rewrite would destroy legacy-import tests that exist *by design* (e.g., `tests/specify_cli/charter/test_defaults_unit.py`, `tests/charter/test_sync_paths.py`, `tests/charter/test_chokepoint_coverage.py`). Per-path exceptions are specified in [occurrence_map.yaml](./occurrence_map.yaml).
3. **Build neutrality tripwires from scratch**: a content-lint pytest, a banned-terms config, a language-scoped allowlist, all owned by `src/charter/neutrality/`. No neutrality guardrail currently exists in the repo. The lint must scan the real doctrine bias surface (`src/doctrine/` — see Technical Context), not just `src/charter/` and mission templates.

The mission also addresses one latent `pyproject.toml` reference to `specify_cli.charter.context`. That reference is **not** package metadata — it sits inside a `[[tool.mypy.overrides]]` "Transitional quarantine" block at `pyproject.toml:218` relaxing strictness for legacy modules. Since `specify_cli.charter.context` never existed as an independent submodule (there is no `src/specify_cli/charter/context.py`), the entry is stale. The plan treats its removal as a **typing-scope change**, not cosmetic cleanup: removing the line may surface previously-suppressed `mypy --strict` errors against `charter.context`. That check is an explicit task (see Phase 1 below).

## Technical Context

**Language/Version**: Python 3.11+ (existing spec-kitty requirement)
**Primary Dependencies**: `typer` (CLI), `rich` (console output), `ruamel.yaml` (YAML), `pytest` (tests), `mypy --strict` (type checking) — all already pinned in charter policy.
**Storage**: Filesystem only. No database changes. On-disk bundle layout under `.kittify/charter/bundle/` is frozen (C-001).
**Testing**: pytest. New neutrality lint lives at `tests/charter/test_neutrality_lint.py` and runs as part of the existing test suite (no separate CI job). Coverage goal ≥ 90% on new code (NFR-002, charter policy).
**Target Platform**: Developer machines and CI (Linux, macOS). No runtime platform surface change.
**Project Type**: Single project, internal Python package refactor + shipped-artifact lint.
**Performance Goals**: Neutrality lint ≤ 5s on a baseline dev machine (NFR-001). CLI cold-import regression ≤ 5% vs v3.1.5 (NFR-005).
**Constraints**: No CLI surface changes (C-004); no on-disk bundle migration (C-001); no doctrine schema redesign (C-003); external Python importers of `specify_cli.charter.*` get one-minor-cycle deprecation window (C-005).
**Scale/Scope**: Package `__init__.py` gains a single `warnings.warn` call + four module-level deprecation constants (submodule shims stay silent per C-2); ~25 import-site migrations across `tests/` and spec markdown (28 sites minus 3 files retained as intentional C-005 compatibility fixtures per R-007 / occurrence_map.yaml exceptions); 1 new neutrality lint module scanning `src/doctrine/` + `src/charter/` + mission templates + `.kittify/charter/`; 2 config YAMLs (`banned_terms.yaml` with 4 seed entries, `language_scoped_allowlist.yaml` with 4 seed entries for existing Python-scoped `src/doctrine/` artifacts); 1 CHANGELOG entry; 1 migration guide; 1 `pyproject.toml` edit (remove stale `specify_cli.charter.context` override, which is a typing-scope change gated on a real `mypy --strict` run — see R-008).

## Charter Check

*GATE: Must pass before Phase 0 research. Re-evaluated after Phase 1 design.*

| Directive / Policy | Applies to this mission? | Compliance plan |
|---|---|---|
| **DIRECTIVE_003** — Decision Documentation | Yes | Shim sunset decision (single-minor window), neutrality tripwire design, and consolidation completion are captured in `plan.md`, `CHANGELOG.md`, and `docs/migration/charter-ownership-consolidation.md`. ADR is not required (no novel architectural trade-off beyond what's in spec + plan). |
| **DIRECTIVE_010** — Specification Fidelity | Yes | All 16 FRs, 6 NFRs, and 7 constraints in `spec.md` are addressed by tasks in this plan. Any deviation flagged during implementation must land as a spec amendment before acceptance. |
| **DIRECTIVE_035** — Bulk-edit classification | Yes | `meta.json` has `change_mode: bulk_edit`. `occurrence_map.yaml` is authored in this plan phase with user-ratified category actions (see `./occurrence_map.yaml`). |
| **Test coverage ≥ 90%** on new code | Yes | Applies to the new `src/charter/neutrality/` module and any new helper code. Shim-file edits are purely additive (DeprecationWarning + docstring) and tested indirectly through existing CLI tests + a dedicated shim-warning test. |
| **`mypy --strict` must pass** | Yes | New module gets type annotations; CI enforces. |
| **Integration tests for CLI commands** | Yes | No new CLI commands; existing integration tests cover behavioral invariance (FR-007). |

**Gate status**: PASS. No charter conflicts. No complexity tracking entries needed.

## Project Structure

### Documentation (this mission)

```
kitty-specs/charter-ownership-consolidation-and-neutrality-hardening-01KPD880/
├── spec.md                    # /spec-kitty.specify output
├── meta.json                  # mission identity + change_mode: bulk_edit
├── plan.md                    # THIS FILE (/spec-kitty.plan output)
├── research.md                # Phase 0 output
├── data-model.md              # Phase 1 output
├── quickstart.md              # Phase 1 output
├── contracts/                 # Phase 1 output — API / lint / config contracts
├── occurrence_map.yaml        # DIRECTIVE_035 bulk-edit classification
├── checklists/
│   └── requirements.md        # Spec-phase quality checklist (already complete)
└── tasks/                     # Populated by /spec-kitty.tasks
```

### Source Code (repository root)

Only touched paths are listed. Single-project Python layout; the refactor reshapes import ownership, not directory topology.

```
src/charter/                                    # Canonical owner (already populated)
├── __init__.py                                 # Public API surface — unchanged
├── context.py                                  # build_charter_context (sole definition)
├── sync.py                                     # ensure_charter_bundle_fresh (sole definition)
├── bundle.py, catalog.py, compiler.py, …       # Other owned modules — unchanged
├── neutrality/                                 # NEW — neutrality tripwire module
│   ├── __init__.py                             # NEW — public API for lint helpers
│   ├── banned_terms.yaml                       # NEW — 4 seed terms (PY-001..PY-004)
│   ├── language_scoped_allowlist.yaml          # NEW — 4 seed entries for existing src/doctrine/ Python-scoped artifacts
│   └── lint.py                                 # NEW — scanner over src/doctrine/, src/charter/, mission templates, .kittify/charter/
└── …

src/specify_cli/charter/                        # Legacy shim surface — deprecated-in-place
├── __init__.py                                 # EDIT — add warnings.warn + 4 deprecation constants (sole warning site per C-2)
├── compiler.py                                 # UNCHANGED (stays silent per C-2; optional informational __deprecated__/__canonical_import__ attrs)
├── interview.py                                # UNCHANGED (stays silent per C-2; optional informational __deprecated__/__canonical_import__ attrs)
└── resolver.py                                 # UNCHANGED (stays silent per C-2; optional informational __deprecated__/__canonical_import__ attrs)

tests/
├── charter/
│   └── test_neutrality_lint.py                 # NEW — content-lint pytest (FR-010, FR-011)
├── charter/
│   └── test_charter_ownership_invariant.py     # NEW — enforces SC-001 going forward
├── specify_cli/charter/
│   └── test_shim_deprecation.py                # NEW — verifies DeprecationWarning emits (FR-005)
└── …                                           # 28 test files migrate legacy imports (tests_fixtures: rename)

docs/
└── migration/
    └── charter-ownership-consolidation.md      # NEW — sunset guide for external importers

pyproject.toml                                  # EDIT — remove stale `specify_cli.charter.context` override from [[tool.mypy.overrides]] quarantine block; gated on a passing `mypy --strict src/charter/context.py` run (see R-008)
CHANGELOG.md                                    # EDIT — add mission entry + shim removal-target note
```

**Structure Decision**: Single-project layout preserved. The only new subpackage is `src/charter/neutrality/` — placed under `charter` (not `specify_cli`) so the canonical owner is obvious from day one, per user directive.

## Complexity Tracking

*No Charter Check violations. Complexity tracking section intentionally empty.*

---

## Phase 0 — Outline & Research

See [research.md](./research.md). Summary:

- **R-001**: Baseline inventory of `src/charter/` and `src/specify_cli/charter/` — **resolved** (4 pure shims, 18 canonical modules, both target functions already single-defined).
- **R-002**: Pre-mortem inventory of 6 silent-breakage categories — **resolved** (zero dynamic imports, zero test-mock string patches, zero agent-profile references, zero doc-teaching material; one low-stakes `pyproject.toml` metadata hit; 28 import sites to migrate).
- **R-003**: Banned-term regex list and allowlist format design — **resolved** (YAML with commented examples; initial term list enumerated in `research.md`).
- **R-004**: Shim sunset release policy — **resolved** (single-minor window per user direction Q1).
- **R-005**: Deprecation-warning emission strategy for `sys.modules`-aliasing shim files — **resolved** (warn at alias-registration time; stacklevel=2; filter disabled in tests via `pytest.warns`).

No `NEEDS CLARIFICATION` markers remain after Phase 0.

---

## Phase 1 — Design & Contracts

See [data-model.md](./data-model.md), [contracts/](./contracts/), and [quickstart.md](./quickstart.md).

- **Data model**: Two config artifacts (`banned_terms.yaml` seeded with 4 Python-bias terms, `language_scoped_allowlist.yaml` seeded with 4 existing Python-scoped `src/doctrine/` entries) with documented schemas; one runtime `NeutralityLintResult` value type; one `ShimDeprecationRecord` metadata carrier (on the package `__init__.py` only).
- **Contracts**:
  - Neutrality lint CLI contract (`pytest` entry point semantics + expected failure output format; scans `src/doctrine/` as the primary bias surface alongside `src/charter/`, mission templates, and `.kittify/charter/`).
  - Public import surface contract for `src/charter/*` (no surface change versus baseline).
  - Shim deprecation warning contract: the package `__init__.py` emits a single `DeprecationWarning`; submodule shims stay silent to avoid double-warning common `from specify_cli.charter.X import Y` idioms.
- **Quickstart**: Developer walkthrough — how to add a Python-scoped doctrine file to the allowlist; how to extend the banned-terms list; how to run the lint locally.
- **Dedicated mypy verification task**: Per R-008, before deleting the stale `specify_cli.charter.context` entry from the `[[tool.mypy.overrides]]` "Transitional quarantine" block at `pyproject.toml:218`, run `mypy --strict src/charter/context.py`. If the run is clean, delete the line. If strict errors surface, either fix them within this mission's scope or (as a compromise) rename the override to target the real module `charter.context` with a `# TODO: remove in mission NNN` comment; do not silently delete without the check.

---

## Post-Design Charter Check (re-evaluation)

| Check | Verdict after Phase 1 design |
|---|---|
| DIRECTIVE_003 captures decisions? | PASS — plan.md + research.md + migration guide. |
| DIRECTIVE_010 spec fidelity preserved? | PASS — every FR/NFR/C is addressed by a design artifact, no scope expansion. |
| DIRECTIVE_035 occurrence map authored? | PASS — `./occurrence_map.yaml` generated with user-ratified categories (Q2). |
| Test coverage plan realistic? | PASS — new code is a small module + two config files; 90%+ coverage achievable with 3 test modules. |
| `mypy --strict` feasible? | PASS — new module is pure-Python with straightforward types. The `[[tool.mypy.overrides]]` quarantine removal is gated on a real `mypy --strict src/charter/context.py` run per R-008; no silent deletions. |
| CLI behavioral invariance? | PASS — shim warnings are import-time only and wrapped to avoid breaking first-load output; integration tests continue to cover invariance. |

**Gate status after design**: PASS. Ready for `/spec-kitty.tasks`.
