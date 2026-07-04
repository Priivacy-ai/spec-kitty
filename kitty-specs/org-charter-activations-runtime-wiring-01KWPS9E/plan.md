# Implementation Plan: Org-Charter Activations Runtime Wiring

**Branch**: `design/org-charter-activations-2365` | **Date**: 2026-07-04 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/org-charter-activations-runtime-wiring-01KWPS9E/spec.md` (rev 2, post-spec squad folded)

## Summary

Wire the already-parsed-and-folded org-pack `activations:` registry into the runtime charter-context render so consumers surface org-declared action-scoped activations without hand-copying. The fix is a **resolve-time org∪project union** at `_render_activation_block` (`charter/context.py`), mirroring the proven `required_<kind>` → `selected_<kind>` precedent (`_read_org_required_selections`/`_load_doctrine_selection`). It (1) relocates the 4-tuple identity key down into `charter.activations` and extracts a shared `_iter_org_charter_docs` reader so no third hand-rolled rescan copy accrues, (2) unions validated org activations into the text stanza pre-`except`, and (3) installs a bootstrap-mode-forced, refactor-stable regression invariant against the recurring "merged-but-never-rendered" class (#1465/#1242/#2365). Scope is the **text stanza only** (parity with project activations); structured-JSON and compact-mode surfacing are explicitly deferred (C-004).

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: pydantic (`ActivationEntry.model_validate`), ruamel.yaml / `YAML(typ="safe")` (raw org-charter rescan), existing `charter` + `specify_cli.doctrine.org_charter` packages
**Storage**: Filesystem — `org-charter.yaml` per doctrine pack; project `.kittify/charter/{charter.md,governance.yaml}`; `context-state.json` (compact-mode cache)
**Testing**: pytest; red-first through `build_charter_context(...).text` in bootstrap mode with a real org pack on disk. Reusable harness: `tests/charter/test_context_org_governance.py` (`_write_org_pack` + `_write_config`); parity references `tests/charter/test_context_activation_render.py`, `tests/specify_cli/doctrine/test_org_charter*.py`
**Target Platform**: CLI (`spec-kitty charter context`) + library (`build_charter_context`)
**Project Type**: single (Python package)
**Performance Goals**: N/A — resolve-time path already runs per invocation; the org rescan mirrors the existing `required_<kind>` rescan cost (one extra small-YAML read per configured pack, bootstrap only)
**Constraints**: Layer boundary ADR 2026-03-27-1 (`charter` must not import `specify_cli.doctrine.org_charter`); no new shadow path (`governance.yaml` stays project-pure); no redesign of `ActivationEntry`/`resolve_for_context`/`GovernanceConfig.activations`
**Scale/Scope**: ~2 source files (`charter/context.py`, `charter/activations.py`) + `org_charter.py` re-import; ~3–4 new/extended test modules. Flat single_branch topology.

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Single canonical authority** ✅ — consolidates dedup identity into ONE shared function (`charter.activations`) and org-charter reading into ONE shared iterator; removes duplication rather than adding a parallel path.
- **Architectural alignment / layering** ✅ — honors ADR 2026-03-27-1 (`kernel ← doctrine ← charter ← specify_cli`); the shared key moves *down* to `charter.activations`, `org_charter` imports it upward (already imports `ActivationEntry` from there). No `charter → specify_cli` import introduced.
- **ATDD-first / red-first** ✅ — NFR-001 mandates red-first through the pre-existing bootstrap entry point, forbidding the green-before-and-after seams (`render_activation_stanza`/`resolve_for_context`).
- **No new shadow paths** ✅ — resolve-time union only; `governance.yaml` stays project-pure (NFR-002), matching the `required_<kind>` precedent and the 3.2.x milestone goal.
- **Terminology** ✅ — no `feature`/legacy terms introduced; doctrine/charter prose only.
- **Campsite** — pre-spec squad found no domain-matched #1931 items; FR-006 opportunistically consolidates the accreting rescan-copy debt that is directly in-domain.

No violations → Complexity Tracking omitted.

## Project Structure

### Documentation (this mission)

```
kitty-specs/org-charter-activations-runtime-wiring-01KWPS9E/
├── spec.md              # rev 2 (committed)
├── issue-matrix.md      # committed
├── plan.md              # this file
├── research.md          # brownfield checks (this phase)
├── tasks.md             # /spec-kitty.tasks output
└── tasks/               # per-WP task files
```

### Source Code (repository root)

```
src/specify_cli/
├── charter/
│   ├── activations.py        # + shared 4-tuple identity key (relocated from org_charter); FR-003
│   ├── context.py            # + _iter_org_charter_docs (FR-006), _read_org_activations
│   │                         #   (FR-001/002/004), union into _render_activation_block pre-try;
│   │                         #   refactor _read_org_required_selections onto the shared reader
│   └── _activation_render.py # unchanged (render_activation_stanza) — confirm no edit needed
└── doctrine/
    └── org_charter.py        # re-import identity key from charter.activations (single caller)

tests/
├── charter/
│   ├── test_context_org_governance.py     # extend: org-pack activations → text stanza (SC-001)
│   ├── test_org_activations_resolution.py # NEW: union/dedup/order (SC-002), validation raise (SC-003)
│   └── test_iter_org_charter_docs.py      # NEW: shared reader unit (FR-006)
└── architectural/ or tests/charter/
    └── test_org_activations_reach_context.py  # NEW: FR-005 recurrence-class regression invariant
```

**Structure Decision**: Single Python package, flat topology. All production changes land in `charter/{context,activations}.py` with a one-line re-import in `doctrine/org_charter.py`. The regression invariant (FR-005) is a behavioral test placed with the charter tests (not a shape-pinning architectural gate) so it survives refactors per [[refactor-stable arch tests]].

## Implementation Concern Map

> Concerns, not work packages. `/spec-kitty.tasks` translates these into WPs.

### IC-01 — Shared seams (identity key + org-charter reader)

- **Purpose**: Eliminate the duplication that caused #2365 — one dedup identity, one org-charter document reader — before adding a new consumer, so the org and project paths cannot drift.
- **Relevant requirements**: FR-003, FR-006; C-001, C-002.
- **Affected surfaces**: `charter/activations.py` (host the identity key), `charter/context.py` (extract `_iter_org_charter_docs`; refactor `_read_org_required_selections` onto it), `doctrine/org_charter.py` (re-import key, single caller at ~:450).
- **Sequencing/depends-on**: none (foundation).
- **Risks**: Refactoring the *working* `_read_org_required_selections` onto the shared reader touches a live `required_<kind>` path — its existing tests are the safety net; keep the extraction behavior-preserving (pure move, no semantic change). Verify the identity key has no `org_charter`-local dependency before relocating (grounding confirms: depends only on `ActivationEntry` + stdlib).

### IC-02 — Org activations resolve-time union + validation

- **Purpose**: Read, validate, and union org-pack activations into the bootstrap text stanza at the correct (pre-`except`) attach point.
- **Relevant requirements**: FR-001, FR-002, FR-004; NFR-002, NFR-003; C-003, C-004.
- **Affected surfaces**: `charter/context.py` — new `_read_org_activations(repo_root)` (consumes IC-01's reader; validates each entry via `ActivationEntry.model_validate`, raises on malformed present-pack entries, skips missing packs); union+dedup into the list `_load_governance_activations` returns, placed **before** `_render_activation_block`'s `except Exception: return ""` (beside line ~2679) so the validation raise escapes to `build_charter_context`.
- **Sequencing/depends-on**: IC-01.
- **Risks**: Placement is load-bearing — inside the `try` the raise is swallowed (FR-004 defeated). Union must preserve project first-seen order (FR-002) and NOT mirror the silent-skip error handling of the precedent (C-002 override). Must not write into `governance.yaml` (NFR-002).

### IC-03 — Recurrence-class regression invariant + red-first coverage

- **Purpose**: Prove the fix red-first through the real entry point and install a durable, refactor-stable guard against a fourth recurrence.
- **Relevant requirements**: FR-005; NFR-001; SC-001..SC-004.
- **Affected surfaces**: `tests/charter/` (+ possibly `tests/architectural/`) — bootstrap-mode-forced behavioral test asserting org activations reach `build_charter_context(...).text`; union/order/dedup tests; validation-raise test; `governance.yaml`-purity + non-org-repo byte-identity assertions.
- **Sequencing/depends-on**: authored red-first ahead of IC-02's implementation; finalized alongside.
- **Risks**: Must force bootstrap mode (omit `context-state.json` / depth ≥ 2) or it false-greens in compact mode. Must assert behavior (stanza contents) not internal function names. Must run through `build_charter_context`/CLI, never `render_activation_stanza`/`resolve_for_context` (NFR-001 forbidden seams).
