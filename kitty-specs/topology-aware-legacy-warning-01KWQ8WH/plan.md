# Implementation Plan: Topology-Aware Legacy Warning

**Branch**: `fix/topology-aware-legacy-warning` | **Date**: 2026-07-04 | **Spec**: [spec.md](./spec.md)
**Input**: Mission specification from `kitty-specs/topology-aware-legacy-warning-01KWQ8WH/spec.md`

## Summary

Stop the once-per-mission legacy-topology warning from over-firing on intentional coordination-less (`single_branch`/`lanes`) and `flattened` missions, while still warning on genuinely pre-SSOT legacy missions. Do this by **adding a warning-only classifier** that reads the stored `MissionTopology`, and **re-pointing only the warning emit** at it — leaving the shared `_is_legacy_mission()` predicate (which also drives routing + write-contract) untouched. Full live-code evidence in [research.md](./research.md).

### Key decisions (from the live-code investigation)

- **Split, don't repurpose (C-005).** `_is_legacy_mission()` (`transaction.py:200-230`) feeds worktree routing (`:719-729`), write-contract (`:909`), AND the warning (`:730`) via one `legacy_mode` boolean. Making it topology-aware would break routing/write-contract for coord-less shapes (they'd fall into the coordination-worktree `else` arm → `BookkeepingWorktreeMissing`). So it stays unchanged; a new `_warrants_legacy_warning()` gates only the emit.
- **Use the non-deriving reader (C-001).** Read topology via `stored_topology_from_meta` (`missions/_read_path_resolver.py:117`), which returns `None` for absent/malformed. The *deriving* readers (`read_topology`/`resolve_topology`) collapse genuine-legacy and created-`single_branch` both to `SINGLE_BRANCH` — using one would silence real legacy warnings.
- **Trigger**: warn iff `coordination_branch` falsy AND `stored_topology_from_meta(meta) is None` AND `meta.get("flattened")` falsy. Malformed/unknown topology → warns (conservative default, falls out of the reader returning `None`).

## Technical Context

**Language/Version**: Python 3.11 (repo `requires-python = ">=3.11"`, pinned `3.11.15`)
**Primary Dependencies**: stdlib `json`; canonical reader `stored_topology_from_meta` (`specify_cli.missions._read_path_resolver`); `MissionTopology` enum (`mission_runtime.context`)
**Storage**: filesystem — mission `meta.json` (`topology`, `flattened`, `coordination_branch`)
**Testing**: pytest (`tests/integration/test_legacy_mission_fallback.py`, new `tests/specify_cli/coordination/`); `mypy --strict`; `ruff`; `tests/architectural/test_no_legacy_terminology.py` for the runbook prose
**Target Platform**: cross-platform CLI (Linux, macOS, Windows 10+)
**Project Type**: single project (CLI)
**Performance Goals**: negligible — at most one additional small `meta.json` read on the coord-less path; optional DRY hoist removes even that
**Constraints**: keep `_is_legacy_mission()` + routing + write-contract unchanged (C-005/FR-005); consume the canonical non-deriving reader, no ad-hoc parse (C-001); no `coordination_branch is None` topology-inference site (ADR SC-001); `mypy --strict`/`ruff` zero-issue, no new suppressions
**Scale/Scope**: 1 production file (`coordination/transaction.py`) + 1 doc (`docs/migrations/legacy-to-coordination.md`) + tests; no `__init__.py`/version change

## Charter Check

*GATE: must pass before task decomposition.*

- **Single canonical authority** — reuse `stored_topology_from_meta`; do not re-implement topology parsing. ✅
- **ATDD-first** — the 7-case matrix + routing-invariance + backfill-suppression tests drive the change red-first. ✅
- **Locality of change (DIR-024)** — the warning gate is added in the module that owns the seam (`transaction.py`); no new subsystem. ✅
- **Non-vacuous gate (standing order)** — a routing/write-contract **invariance** test proves the change touched only the warning, guarding against a future collapse back into `_is_legacy_mission`. ✅
- **Quality gates (DIR-006/030)** — `mypy --strict` + `ruff` zero-issue, no new suppressions; every new branch covered. ✅
- **Terminology canon** — runbook prose passes `test_no_legacy_terminology.py`. ✅

No violations → Complexity Tracking not required.

## Project Structure

### Documentation (this mission)
```
kitty-specs/topology-aware-legacy-warning-01KWQ8WH/
├── spec.md      # committed
├── plan.md      # this file
├── research.md  # live-code brief
└── tasks.md     # created by /spec-kitty.tasks
```

### Source Code (repository root)
```
src/specify_cli/coordination/transaction.py   # IC-01: add _warrants_legacy_warning + re-point emit (:730); _is_legacy_mission UNCHANGED
src/specify_cli/missions/_read_path_resolver.py # reused unchanged (stored_topology_from_meta)
docs/migrations/legacy-to-coordination.md      # IC-02: fix 3 paragraphs (:61-65, :66-69, :125-127)

tests/
├── integration/test_legacy_mission_fallback.py        # extend: parametrize _make_legacy_mission (topology=/flattened=)
└── specify_cli/coordination/test_legacy_warning_classifier.py  # new: unit-test _warrants_legacy_warning
```

**Structure Decision**: single-project CLI. One production-code concern (the warning gate) + one documentation concern (the runbook), plus tests.

## Implementation Concern Map

### IC-01 — Warning-only topology-aware classifier

- **Purpose**: gate the legacy warning on the stored topology so coord-less/flattened shapes don't warn, without altering routing or write-contract.
- **Relevant requirements**: FR-001, FR-002, FR-003, FR-004, FR-005; SC-001, SC-002, SC-003, SC-005.
- **Affected surfaces**: `src/specify_cli/coordination/transaction.py` — (a) add `_warrants_legacy_warning(repo_root, mission_slug, mid8) -> bool` near `_coordination_branch_from_meta` (`~:233`); wrap the emit at `:730` with it (reuse `stored_topology_from_meta` via a **function-local import** to avoid cycles); (b) **amend the `_emit_legacy_warning_once` message (`:341-347`)** to cite `spec-kitty migrate backfill-topology` alongside the runbook — a **message-only** change (not trigger/logic), required so the genuine-legacy warning satisfies US2/FR-004/SC-002 (and the issue's fix direction). Optional: hoist a shared `_load_mission_meta(...)` since `_is_legacy_mission`, `_coordination_branch_from_meta`, and the new helper read the same file (S1192/DRY). Leave `_is_legacy_mission` (`:200-230`), routing (`:719-729`), `_legacy_mode` (`:831`), and the write-contract branch (`:909`) untouched.
- **Sequencing/depends-on**: none.
- **Risks**: **reader-choice trap** — wiring a deriving reader silences genuine-legacy; the genuine-legacy + single_branch tests together pin it (both mandatory). Import cycle → function-local import. The gate now sits *before* the marker write, so suppressed missions never write a marker (expected).

### IC-02 — Coupled runbook update

- **Purpose**: keep `docs/migrations/legacy-to-coordination.md` truthful once the warning no longer fires for coord-less shapes.
- **Relevant requirements**: FR-001 (behavior), SC-004; C-003, C-004.
- **Affected surfaces**: `docs/migrations/legacy-to-coordination.md` — rewrite bullet `:61-65` (single_branch/lanes no longer warn — topology-aware), clarify the flattened bullet `:66-69` (no warning), and fix the Path A note `:125-127` (backfill now *suppresses* future warnings, a deliberate contract change). Then run `pytest tests/architectural/test_no_legacy_terminology.py`.
- **Sequencing/depends-on**: pairs with IC-01 (docs must match the shipped behavior).
- **Risks**: terminology gate runs only in CI's `integration-tests-core-misc` job — run it locally before pushing (CLAUDE.md).

### Residual risks the tasks phase must carry
1. **Reader-choice trap** (highest) — mandatory genuine-legacy + single_branch tests.
2. **Routing/write-contract invariance** — an explicit test that `single_branch`/`lanes` still take the legacy lane-worktree + `primary_checkout_append` path (only the warning changed).
3. **Backfill-suppression is a documented-contract change** (Path A note) — assert with a test so it isn't reverted later.
4. Malformed-topology → warns: an explicit test documents the deliberate default.
5. **Backfill pointer in the message**: the genuine-legacy test must assert the emitted stderr contains **both** the runbook path **and** the `spec-kitty migrate backfill-topology` command string (the existing test only checks `"migrating"`), pinning FR-004/SC-002.
