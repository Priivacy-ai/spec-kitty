# Implementation Plan: Charter Synthesize Reconciliation

**Branch**: `fix/charter-synthesize-reconciliation` | **Date**: 2026-08-09 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/charter-synthesize-reconciliation-01KZJQN6/spec.md`

## Summary

Make `charter synthesize` non-destructive by reconciling the freshly-emitted project DRG
overlay **and** synthesis manifest against what is already on disk, instead of rebuilding both
from the current target set and whole-file-swapping them in. The reconciliation reuses the
existing `resynthesize` primitives at the single shared `orchestrator.synthesize` seam:
`_merge_project_overlay` merges the graph inside `_validation_callback` (which persists the merged
overlay), while `_rewrite_manifest` reconciles the manifest in the `synthesize` **body** — loading
the existing on-disk manifest and passing it as `promote(..., manifest_override=…)`. The manifest
reconcile is NOT done in `_validation_callback` (it only receives `staged_dir` and writes the
graph). Manual `synthesize`, boundary `auto_refresh`, and `activate`/`deactivate` are all covered.

Per the post-spec squad (ledger `01KZJV6H7TW63M6ZGNM05XKM2S`), the **library seam defaults to
preserve-and-succeed** (exit 0, drops nothing, returns a reconciliation delta). The **CLI layer**
owns `--prune` (explicit removal, lists deletions), `--dry-run` (reports the delta, writes
nothing), and a **narrow non-zero refusal** for genuinely-unpreservable cases only (orphaned
content removed without `--prune`; an unparseable on-disk overlay). Conflicts introduced by
preserving on-disk content (duplicate triple / dangling endpoint) are routed to the DRG
typed-conflict report channel rather than an uncaught `ProjectDRGValidationError`. The boundary
heal additionally clears `synthesized_drg` stale so `implement`/`next` are not re-blocked. Two
siblings fold in: `#2777` (auto_refresh runs targeted `generate` for references-parity, honoring
the landed `#2772` curated-`charter.md` contract) and `#3052` (populate `source_urns` for
consumer-pack sections so synthesize emits charter-relevant edges without fabricating any).

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer, pydantic, ruamel.yaml (existing spec-kitty-cli deps) — **no new runtime dependencies**
**Storage**: filesystem — `.kittify/doctrine/graph.yaml`, `.kittify/charter/synthesis-manifest.yaml`, `.kittify/doctrine/**` artifacts (no database)
**Testing**: pytest (charter fast-lane slice), ruff, mypy; ATDD red-first — `tests/charter/synthesizer/test_synthesize_node_preservation.py` already committed and failing
**Target Platform**: cross-platform CLI (Linux / macOS)
**Project Type**: single (Python package `src/charter` + `src/specify_cli`)
**Performance Goals**: the existing performance-envelope test stays green (absolute ~30s envelope) — the NFR-004 acceptance; the "≤ 20% wall-clock vs current synthesize on ≤200 nodes" is an informational target only (no relative benchmark exists to gate it)
**Constraints**: zero silent deletions of nodes/edges/manifest entries (NFR-001); zero new uncaught-exception paths on divergent inputs (NFR-003); byte-stable no-op re-synthesis of graph AND manifest (NFR-002); curated `charter.md` untouched by the heal (NFR-006); ruff/mypy zero new issues, complexity ≤ 15, no new suppressions (NFR-005)
**Scale/Scope**: the charter synthesizer subsystem — ~6–8 modules across `src/charter/synthesizer/` and `src/specify_cli/charter_runtime/` + `cli/commands/charter/`; no schema/API surface changes

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Compact charter context loaded (`mode: compact`, software-dev-default, DIR-001..013). Relevant gates:

- **ATDD-first** — SATISFIED: red-first reproduction is committed on the branch and drives the P0 contract (C-004).
- **Canonical sources / no improvised equivalents** — SATISFIED by design: C-002 mandates reusing the existing `_merge_project_overlay` / `_rewrite_manifest` primitives rather than a parallel merge; C-001 anchors behavior to the canonical DRG conflict model (ADR `2026-07-26-3`).
- **Architectural alignment / warn-not-block doctrine** — SATISFIED: preserve-and-warn default aligns with the prevailing "warn, do not hard-block" posture; hard-fail reserved for unpreservable states only.
- **Terminology adherence** — GATE: run `tests/architectural/test_no_legacy_terminology.py` on touched `src/`/`docs/` surfaces (C-005).
- **Git/workflow discipline** — SATISFIED: work on `fix/charter-synthesize-reconciliation`, PR into `main`; no direct pushes.
- **Tiered rigour** — P0 spine carries full test rigour; P2/P3 folds carry proportional coverage.

No unjustified violations → **Charter Check passes**. (Re-checked post-Phase 1: no new gates.)

## Project Structure

### Documentation (this mission)

```
kitty-specs/charter-synthesize-reconciliation-01KZJQN6/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (library seam + CLI contract)
└── tasks.md             # Phase 2 output (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)

```
src/charter/synthesizer/
├── orchestrator.py          # synthesize() seam — add reconcile-preserve + delta return (IC-01)
├── resynthesize_pipeline.py # source of _merge_project_overlay / _rewrite_manifest (reuse; IC-01)
├── write_pipeline.py        # promote() — pass manifest_override on the synthesize path (IC-01)
├── project_drg.py           # emit_project_layer + edge derivation (IC-02, IC-07)
├── validation_gate.py       # route merged-overlay conflicts to the report channel (IC-02)
├── interview_mapping.py     # populate source_urns for consumer-pack sections (IC-07)
└── targets.py               # source_urns propagation into targets (IC-07)

src/doctrine/drg/
├── merge.py                 # typed-conflict SHAPE reference only — model after, NOT reused/edited (IC-02)
├── loader.py / validator.py # merge_layers / validate_graph; extract structured dup/dangling helpers (IC-02)

src/specify_cli/cli/commands/charter/
├── synthesize.py / _synthesis.py / _fresh_doctrine.py  # CLI: preserve/prune/dry-run/refuse (IC-03)
├── activate.py / deactivate.py                         # preserve reconcile + rename footgun (IC-05)
└── generate.py                                         # references-parity heal (#2777; IC-06)

src/specify_cli/charter_runtime/
├── preflight/runner.py      # _attempt_auto_refresh: consume preserve path; clear stale (IC-04)
├── preflight/hook.py        # boundary abort/return semantics (IC-04)
└── freshness/computer.py    # synthesized_drg re-stamp after non-destructive heal (IC-04)

tests/charter/synthesizer/   # + tests/specify_cli/charter_runtime/  (IC-08, co-delivered per IC)
```

**Structure Decision**: Single Python package. The fix concentrates at the library seam
(`src/charter/synthesizer/`) with CLI-policy and boundary-reconciler changes in
`src/specify_cli/`. No new modules or directories are required; the reconciliation primitives
already exist and are relocated into the synthesize path.

## Complexity Tracking

*No Charter Check violations — section intentionally empty.*

## Implementation Concern Map

> Implementation concerns are NOT work packages. `/spec-kitty.tasks` translates these into
> executable WPs. Each concern co-delivers its focused tests (NFR-008, C-004).

**Spine (P0, independently landable — C-003): IC-01 … IC-05. Folds (P2/P3): IC-06, IC-07.**

### IC-01 — Library reconciliation seam (preserve-and-succeed)

- **Purpose**: Make `orchestrator.synthesize` reconcile the emitted overlay + manifest against the on-disk overlay + manifest (reuse `_merge_project_overlay` + `_rewrite_manifest`), preserving backed content and returning a reconciliation-delta envelope; default drops nothing.
- **Relevant requirements**: FR-001, FR-002, FR-004, FR-005, FR-009; NFR-001, NFR-002.
- **Affected surfaces**: `src/charter/synthesizer/orchestrator.py` (`_validation_callback`), `write_pipeline.py` (`promote(..., manifest_override=…)`), `resynthesize_pipeline.py` (extract/share primitives), `project_drg.py`.
- **Sequencing/depends-on**: none (foundation).
- **Risks**: preserving on-disk content re-injects nodes/edges that bypass `emit_project_layer`'s additive guard → hand-off to IC-02; must keep no-op re-synthesis byte-stable for graph AND manifest; do NOT bake a `--prune` default into the library signature (breaks existing `synthesize(request, adapter, repo_root)` callers incl. `activate`).

### IC-02 — Merged-overlay conflict routing (report, not crash)

- **Purpose**: Run the additive-collision / dangling-endpoint check over the merged (preserved + emitted) overlay and translate a *pre-existing preserved-content* conflict into a `ReconciliationConflict` report (new object in `reconcile.py`, modeled after — not reusing — the DRG typed-conflict shape); only a *new-emit* collision remains a hard error.
- **Net-new, not reuse**: the synthesize path's `validate_graph` returns `list[str]`, and `OrgDRGConflict`/`_CONFLICT_REMEDIATIONS` in `src/doctrine/drg/merge.py` are produced by the org-pack fragment-merge subsystem (closed `kind` Literal, no `duplicate_triple`, no `backing_artifact`/`remediation`). Translating string-formatted validator output into the typed `ReconciliationConflict` is therefore net-new work, not a call into `merge.py`.
- **Relevant requirements**: FR-006, FR-014; NFR-003; C-001.
- **Affected surfaces**: `src/charter/synthesizer/validation_gate.py`, `project_drg.py`; `reconcile.py` (WP01's `ReconciliationConflict` + reconciliation remediation vocabulary); `src/doctrine/drg/loader.py` / `validator.py` (extract structured duplicate/dangling helpers — see IC-08/WP02). `src/doctrine/drg/merge.py` is NOT reused or edited.
- **Sequencing/depends-on**: IC-01.
- **Risks**: correctly attributing conflict provenance (new vs preserved); a since-removed built-in endpoint makes a preserved edge dangle — must report, not `ProjectDRGValidationError`.

### IC-03 — CLI preserve/prune/dry-run + narrow refusal

- **Purpose**: The CLI consumes the library delta: preserve-and-warn output by default; `--prune` removes and lists deletions; `--dry-run` reports the delta and writes nothing; non-zero refusal only for unpreservable cases (orphaned removal without `--prune`; unparseable overlay).
- **Relevant requirements**: FR-003, FR-007, FR-010, FR-014.
- **Affected surfaces**: `src/specify_cli/cli/commands/charter/synthesize.py`, `_synthesis.py`, `_fresh_doctrine.py`.
- **Sequencing/depends-on**: IC-01, IC-02.
- **Risks**: dry-run must compute the same delta the real run would (normal path today emits no `planned_deletes`); reuse the conflict-object shape for messaging rather than a hand-rolled format.

### IC-04 — Non-destructive boundary heal that clears stale

- **Purpose**: Route `_attempt_auto_refresh` to the preserve path (no prune/delete for **backed** divergence — exit-0, non-destructive) and ensure a successful heal re-stamps `synthesized_drg` to fresh so `implement`/`next` proceed and are not re-blocked on the next run. This is not a "never refuses" boundary: an **orphaned** node or an **unparseable overlay** still refuses (inherited from the flagless command, WP04 amendment #1), surfaced as an actionable `blocked_reason`, never a silent prune.
- **Relevant requirements**: FR-008; NFR-006.
- **Affected surfaces**: `src/specify_cli/charter_runtime/preflight/runner.py` (`_attempt_auto_refresh`), `hook.py`, `freshness/computer.py`.
- **Sequencing/depends-on**: IC-01, IC-03.
- **Risks**: auto_refresh judges the synthesize step purely by exit code — the preserve default (exit 0) must reach it. Freshness **self-clears**: `synthesized_drg` compares `compute_bundle_content_hash` against the manifest's `bundle_content_hash`, which WP01's `_rewrite_manifest` re-stamps on every write, so the non-destructive heal clears it without a destructive rebuild — verify by test; treat `computer.py` as a guarded fallback only and do **not** weaken its hash comparison (that would blind the boundary to real drift).

### IC-05 — Activation-flow coverage + naming footgun

- **Purpose**: Ensure `activate`/`deactivate` reach the preserve seam (no silent truncation), and rename the mis-named `run_resynthesize_pipeline` (which calls full synthesize) so the intent is legible.
- **Relevant requirements**: FR-013; FR-005.
- **Affected surfaces**: `src/specify_cli/cli/commands/charter/activate.py`, `deactivate.py`.
- **Sequencing/depends-on**: IC-01.
- **Risks**: the direct in-process `_synthesize(...)` call takes no prune/preserve arg — must default-preserve; rename ripples across imports/tests.

### IC-06 — References-parity auto-refresh completion (#2777)

- **Purpose**: When the stale cause is references-parity, `_attempt_auto_refresh` runs a targeted `generate` (recompiling `references.yaml`) without clobbering curated `charter.md`.
- **Relevant requirements**: FR-011; NFR-006.
- **Affected surfaces**: `src/specify_cli/charter_runtime/preflight/runner.py`, `cli/commands/charter/generate.py`.
- **Sequencing/depends-on**: IC-04.
- **Risks**: `generate` writes `charter.md` — must honor the landed `#2772` preservation contract; run `generate` only for the references-parity cause, not unconditionally.

### IC-07 — Edge wiring from evidence (#3052)

- **Purpose**: Populate `source_urns` for the currently-empty consumer-pack interview sections so synthesize emits the charter-relevant edges those sections declare, and the DRG lint stops flagging generated directives — emitting **no** edge where no evidence exists.
- **Relevant requirements**: FR-012; NFR-007; SC-004.
- **Affected surfaces**: `src/charter/synthesizer/interview_mapping.py`, `targets.py`, `project_drg.py` (edge derivation from `source_urns`).
- **Sequencing/depends-on**: IC-01.
- **Risks**: fabricating wrong relationships is worse than an orphan node — the rule must be conservative (edge only where a section declares an upstream URN); assert the negative (no fabrication) as well as the positive.

### IC-08 — Regression & acceptance test schedule (cross-cutting)

- **Purpose**: Deliver the full missing-test suite the squad enumerated, co-located with the IC each pins (per NFR-008 / C-004): preserve-and-succeed (committed), `--prune` removal + listing, `--prune` no-op, `--dry-run` non-empty + empty delta (writes nothing), no-op byte-stability of graph AND manifest, edge preservation on prune/refuse paths, manifest version-skew reconcile, merged-overlay duplicate-triple + dangling-endpoint → report-not-crash, boundary non-destructive heal + `synthesized_drg` cleared + not-re-blocked + curated `charter.md` untouched, `activate`/`deactivate` preserve coverage, edge-wiring positive + no-fabrication.
- **Relevant requirements**: C-004, NFR-008; all FRs.
- **Affected surfaces**: `tests/charter/synthesizer/**`, `tests/specify_cli/charter_runtime/**`.
- **Sequencing/depends-on**: co-delivered with the IC under test (not a standalone trailing phase).
- **Risks**: the `FixtureAdapter` is inputs-hash-keyed — new synthesize scenarios must use recorded fixtures or add them; real-behavior coverage over API-shape assertions.
