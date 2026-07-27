# Implementation Plan: Doctrine-activation freshness integrity

**Branch**: `feat/doctrine-activation-freshness` | **Date**: 2026-07-17 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/doctrine-activation-freshness-01KXRSDN/spec.md`

## Summary

Close the **`activate ⇒ refresh-or-fail-closed`** seam. `charter activate`/`deactivate`
mutate `config.yaml` (`activated_*`), which is *not* one of the four files the #2732
content-identity signal hashes, so every freshness gate stays "fresh" while the derived
references/DRG drift — a recurring, revision-driven drift class (#2770/#2759/#2758/#2157).

**Approach (locked; option (c)):** make config-activation visible by wiring the
**already-built** `run_consistency_check` parity (config↔references / config↔graph) into
the freshness **read-path**, plus an opt-in `--resynthesize` for eager refresh. **Not**
eager-always regeneration — that would invert the `charter → specify_cli` layer (C-001),
tax the activation hot-path (NFR-001), and harm the `spec-kitty upgrade` migration path
(NFR-003). The read-path choice is *writer-agnostic*, which matters because
`merge_defaults` (`pack_manager.py:747`) writes `activated_*` outside `commit_plan` and is
ADR-slated for the `init` path — a write-side marker would be blind to it.

**Four-part reconciler, sequenced:** #2758 (fix the signal's input-set) → #2759 (make
activation visible) → #2157a (aggregate the gate) → #2770 (regenerate the shipped graph +
un-pin the 4 `@regression` tests). #2770 lands **early and standalone** (release-sensitive;
clears the *current* red, independent of the seam that prevents *recurrence*).

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: charter layer (`src/charter/`: `activation_engine`, `bundle`, `sync`, `consistency_check`, `pack_manager`, `synthesizer/*`); specify_cli charter_runtime consumers (`src/specify_cli/charter_runtime/`: `freshness/computer.py`, `preflight/runner.py`); Typer CLI (`src/specify_cli/cli/commands/charter/`); doctrine DRG (`src/doctrine/*.graph.yaml`, `doctrine.drg.migration.extractor`)
**Storage**: YAML on disk — `.kittify/config.yaml` (activation ledger), `.kittify/charter/{governance,directives,references,metadata}.yaml` (hashed bundle), `.kittify/doctrine/graph.yaml` + shipped `src/doctrine/*.graph.yaml`, `synthesis-manifest.yaml` (`bundle_content_hash` stamp)
**Testing**: pytest — `tests/charter/`, `tests/specify_cli/charter_runtime/`, `tests/doctrine/drg/` (freshness), `tests/architectural/`; ATDD red-first through the pre-existing entry point (`charter activate` / `compute_freshness` / implement preflight / `regenerate-graph --check`); subprocess/call-count spies for NFR-001/003
**Target Platform**: Linux/macOS/Windows CLI (cross-platform, DIR-001)
**Project Type**: single (Python CLI + library)
**Performance Goals**: default `charter activate`/`deactivate` spawns **zero** synthesis/`regenerate-graph` subprocess and adds no new filesystem graph walk (NFR-001, spy-verified); activation latency unchanged
**Constraints**: C-001 layer boundary (`commit_plan` stays pure charter, no `specify_cli` import); reuse `run_consistency_check` not reimplement (C-007); must not regress #2732 content-identity machinery (NFR-002); ruff + mypy `--strict` clean, zero new suppressions, complexity ≤ 15
**Scale/Scope**: ~6 charter/runtime modules touched + shipped DRG regen; behavior-preserving except the intentional freshness-visibility change, the fail-closed references preflight, the new `--resynthesize` flag, and the graph regen

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Single canonical authority** ✅ — reuses `run_consistency_check` (the one parity authority) and `compute_bundle_content_hash` (the one content-identity authority); introduces no parallel freshness computation.
- **Architectural alignment / layer boundary (C-001)** ✅ — the reconciler read lives in `specify_cli` freshness (which may import `charter`); `commit_plan` (charter) is untouched. Direction of dependency preserved.
- **DDD + tiered rigour** ✅ — core freshness/parity code (high rigour: ATDD, ≤15 complexity, strict types); CLI flag plumbing (glue). 
- **ATDD-first** ✅ — every WP opens with a red test through the pre-existing entry point.
- **Terminology adherence** ✅ — no `feature*` aliases; "Mission" canon.
- **Regression vigilance / no-op stability (#1914 class)** ✅ — NFR-002 preserves #2732; NFR-001/003 assert no new eager work. 
- **Architectural gate discipline** ✅ — DRG zero-delta re-baselined deliberately (NFR-004); `regenerate-graph --check` green.

No charter violations. Complexity Tracking below is empty.

## Project Structure

### Documentation (this mission)

```
kitty-specs/doctrine-activation-freshness-01KXRSDN/
├── plan.md              # This file
├── spec.md              # committed + squad-hardened
├── research.md          # Phase 0 — consolidated decisions (this command)
├── data-model.md        # Phase 1 — entities + state (this command)
├── quickstart.md        # Phase 1 — validation scenarios (this command)
├── contracts/           # Phase 1 — seam behavior contracts (this command)
├── research/            # grounding-brief.md + code-state-verification.md (squad evidence)
├── traces/              # 3 tracer files (seeded this command)
├── issue-matrix.md      # #2519 slice; folds #2770/#2759/#2758/#2157
└── tasks.md             # Phase 2 — /spec-kitty.tasks (NOT created here)
```

### Source Code (repository root)

```
src/
├── charter/
│   ├── bundle.py                 # compute_bundle_content_hash (4-file hash; #2758 None-path)
│   ├── sync.py                   # _SYNC_OUTPUT_FILES (triad; omits references.yaml)
│   ├── consistency_check.py      # run_consistency_check + parity checks (reuse for #2759)
│   ├── activation_engine.py      # commit_plan chokepoint (READ-ONLY — C-001)
│   ├── pack_manager.py           # merge_defaults bypass (context only; not edited)
│   └── synthesizer/*             # write/resynthesize pipelines (#2732 stamps — preserve)
├── specify_cli/
│   ├── charter_runtime/
│   │   ├── freshness/computer.py # _compute_synthesized_drg (SEAM CORE #2759)
│   │   └── preflight/runner.py   # _attempt_auto_refresh (#2157a one-pass)
│   └── cli/commands/charter/
│       ├── activate.py           # --resynthesize (#FR-007)
│       └── deactivate.py         # --resynthesize (#FR-007)
└── doctrine/
    ├── *.graph.yaml              # shipped DRG fragments (regenerated — #2770)
    └── drg/migration/extractor.py# generate_graph (regen source)

tests/
├── charter/                      # bundle, preflight, consistency_check wiring
├── specify_cli/charter_runtime/  # freshness read-path, preflight aggregation
├── doctrine/drg/                 # zero-delta baseline (re-frozen — #2770)
└── architectural/                # fences + regression markers (un-pin — #2770)
```

**Structure Decision**: Single Python project. The seam splits cleanly along the existing
layer line: **charter** owns content-identity + parity computation (`bundle.py`,
`consistency_check.py`); **specify_cli charter_runtime** owns the read-side consumers that
this mission re-wires (`computer.py`, `runner.py`) and the CLI flag (`activate.py`).
`activation_engine.commit_plan` is deliberately **not** in any WP's edit set (C-001).

## Complexity Tracking

*No Charter Check violations — no entries.*

## Implementation Concern Map

> Concerns are NOT work packages. `/spec-kitty.tasks` translates these into executable WPs.

### IC-01 — Shipped-DRG un-pin & charter citation (#2770) — EARLY / STANDALONE

- **Purpose**: Clear the *current* red — regenerate the shipped `graph.yaml`, wire the charter→reference citation into compiled references, and re-freeze the zero-delta baseline so the four `@pytest.mark.regression` DRG-staleness tests pass un-pinned. This is the mission's **acceptance signal**.
- **Relevant requirements**: FR-004; SC-001; NFR-004 (DRG zero-delta).
- **Affected surfaces**: regenerated `src/doctrine/*.graph.yaml` fragments; the charter reference-declaration + compilation surface that resolves the dangling citation; `tests/doctrine/drg/migration/test_extractor_projection.py` (baseline `289/765/11` — recompute-then-re-freeze, never guess); the 4 `@regression` test sites (`test_no_new_charter_reference_danglers`, `TestDRGZeroDelta::{test_regenerated_graph_matches_baseline_counts, test_shipped_graph_is_fresh_and_byte_identical}`, `test_check_reports_committed_graph_fresh`) — remove the markers.
- **Sequencing/depends-on**: **none** — lands first, independent of the seam. No hard dependency on the mechanism (the seam prevents *recurrence*; this clears the *current* red).
- **Risks**: fixture-entangled with the doctrine-synthesis pipeline; the regen delta N must be *computed* from a fresh regeneration, then the baseline re-frozen to match (NFR-004). Release-sensitive (P0, red-main ADR 2026-07-17-1) — keep it small and landable ahead of everything else.

### IC-02 — Freshness input-set correctness: references.yaml fail-closed preflight (#2758)

- **Purpose**: Kill the permanent-stale `None`. `references.yaml` is one of the four hashed files but `sync` never writes it (only `charter generate` compiles it), so a synced-but-not-generated project gets a dead-end `None`. **Q1 resolved (operator, decision 01KXRVT2KA…): fail-closed preflight** — keep the 4-file hash; when `references.yaml` is absent, surface a single actionable "run `charter generate` first" instead of a dead-end. Leaves #2773 (references.yaml deprecation, same epic) clean — **no `references.yaml` stopgap**.
- **Relevant requirements**: FR-005; SC-003.
- **Affected surfaces**: `src/charter/bundle.py` (the missing-file `None` path `:170-171`); the synthesize/generate preflight surface that gates on bundle completeness; `tests/charter/` (bundle + preflight). **Do NOT** narrow the hash set — so `bundle.py:47 BUNDLE_CONTENT_HASH_FILES`, `computer.py:137 _BUNDLE_FILES`, and `CANONICAL_MANIFEST.derived_files` are all left as-is (Q5 dual-edit is moot under the chosen fork).
- **Sequencing/depends-on**: **none** (can parallel IC-01); sequenced *before* IC-03 among the seam concerns (the signal must be definitionally correct before more consumers read it).
- **Risks**: must not change the hash of a *complete* bundle (NFR-002/SC-006). The preflight is a new fail-closed guard — its actionable message is the whole UX win; keep the message a hoisted constant.

### IC-03 — Seam core: consistency parity into the freshness read-path (#2759)

- **Purpose**: Make config-activation visible. Wire `run_consistency_check` (`consistency_check.py:645`; today only called by the `charter consistency-check` CLI at `pack.py:30`) into `_compute_synthesized_drg` (`computer.py:349`) so a config↔references / config↔graph mismatch reports **stale by construction** (fail-closed, FR-003). **Q2 resolved: read-path parity (option a)** — writer-agnostic, so it also covers the `merge_defaults`/`init` bypass a write-side marker would miss.
- **Relevant requirements**: FR-001, FR-002, FR-003; SC-002; NFR-002 (preserve #2732 — compose with content-identity, do not replace).
- **Affected surfaces**: `src/specify_cli/charter_runtime/freshness/computer.py` (`_compute_synthesized_drg` — add the parity read; **campsite**: extract the `built_in_only` branch + the hash-compare tail so the function stays ≤15 / ≤6 returns); `src/charter/consistency_check.py` (**campsite**: pre-extract sub-checks from `_check_reference_id_parity` (complexity 12) before it becomes a read-path dependency); `tests/specify_cli/charter_runtime/` incl. the SC-002 end-to-end seam test (activate → stale → reconcile → fresh) and an NFR-002 preserve-regression (unchanged bundle → unchanged hash).
- **Sequencing/depends-on**: **IC-02** (definitional correctness first).
- **Risks**: C-001 — the parity call lives in `specify_cli` (allowed to import `charter`); `commit_plan` stays untouched. Fresh-seed early-exit (`computer.py:367-408`) must still short-circuit — the parity read must not force a never-synthesized project stale spuriously.

### IC-04 — One-pass prerequisite gate (#2157a)

- **Purpose**: Stop the implement boundary bouncing a clean mission through `charter_source → synced_bundle → synthesized_drg` one-at-a-time (`stale_analysis` is #2157b, C-004-fenced OUT). The real one-at-a-time site is `_build_blocked_reason` (`runner.py:224`, "pick the first non-passing check"); enumerate **all** non-passing checks into the `blocked_reason` string in **one pass**.
- **Relevant requirements**: FR-006; SC-004.
- **Affected surfaces**: `src/specify_cli/charter_runtime/preflight/runner.py` (`_attempt_auto_refresh`; **campsite**: hoist the `["spec-kitty","charter",…]` prefix list appearing ×3); `tests/specify_cli/charter_runtime/`. **C-004 FENCE**: the analyzer-freshness coupling (#2157b — `workflow.py:835 → analysis_report.check_analysis_report_current`, hashing spec/plan/tasks/charter) is a **different subsystem** and is OUT.
- **Sequencing/depends-on**: **IC-03** (the aggregation reports the now-activation-visible `synthesized_drg` signal).
- **Risks**: must aggregate without changing per-prerequisite verdicts; the one-pass report is additive, not a re-computation of freshness.

### IC-05 — Opt-in `--resynthesize` + hot-path guards (FR-007 / NFR-001 / NFR-003)

- **Purpose**: Give operators an eager-refresh escape hatch (`charter activate/deactivate --resynthesize`) so fail-closed-by-default is ergonomic, while proving the default path stays cheap.
- **Relevant requirements**: FR-007; NFR-001 (default activate = zero synthesis subprocess); NFR-003 (upgrade migration + `org_charter` `promote_activations` pay no synthesis).
- **Affected surfaces**: `src/specify_cli/cli/commands/charter/activate.py` + `deactivate.py` (the `--resynthesize` flag + the eager synthesize orchestration, which lives in `specify_cli` — C-001 keeps it out of `commit_plan`); `tests/specify_cli/cli/commands/charter/` incl. the NFR-001 subprocess/call-count spy (default = zero synthesis) and an NFR-003 migration-path assertion.
- **Sequencing/depends-on**: **IC-03** (`--resynthesize` refreshes the signal IC-03 made visible; the NFR-001 spy asserts the seam added no eager regen to the default path).
- **Risks**: the flag must orchestrate the existing synthesize pipeline, not a new one (single authority). Default-path spy is the guard against accidentally making the seam eager.

### Concern DAG & lanes

```
IC-01 (#2770, early standalone) ─────────────────────────────► (lands first, independent)
IC-02 (#2758) ──► IC-03 (#2759 seam core) ──┬──► IC-04 (#2157a)
                                             └──► IC-05 (--resynthesize + guards)
```

Roughly **2–3 lanes**: IC-01 is its own lane (early); IC-02→IC-03 is the seam spine;
IC-04 and IC-05 fan out from IC-03. Proofs are distributed to their change concerns (no
monolithic proofs WP): SC-001/NFR-004 in IC-01, SC-003 in IC-02, SC-002/NFR-002 in IC-03,
SC-004 in IC-04, NFR-001/NFR-003 in IC-05.

## Design Decisions (record)

- **DD-01 — Option (c), read-path parity (Q2=a).** Reconcile via `run_consistency_check`
  wired into the freshness read-path, not eager-always regen. *Rationale:* C-001 layer
  (commit_plan is pure charter), NFR-001 hot-path, NFR-003 migration cost — and decisively,
  the `merge_defaults` (`pack_manager.py:747`) writer bypasses `commit_plan` and is
  ADR-slated for `init`, so only a **writer-agnostic read-path** parity closes the hole on
  every writer. A write-side marker (Q2c) is rejected. (paula code-state finding.)
- **DD-02 — Sequence #2758 → #2759 → #2157a; #2770 early-standalone.** Signal correctness
  before wiring consumers; gate aggregation after the signal is visible; the release-sensitive
  un-pin lands first and independent (operator decision).
- **DD-03 — Q1 = fail-closed preflight (decision 01KXRVT2KA…).** Keep the 4-file hash; missing
  `references.yaml` → actionable "run `charter generate`" preflight. No hash-narrowing → no
  `references.yaml` stopgap → **#2773 coordination clean** (#2773 owns the deprecation).
- **DD-04 — Fences.** #2760 (upgrade⇒overlay-revalidation) OUT → DRG-model lane #2721.
  #2157b (analyzer-freshness, a different subsystem) OUT → C-004. Broader #2519 authoring/`charter init`
  surface OUT. Step-model Family 2 (#2751/#2761/#2769) OUT.
- **DD-05 — Preserve #2732.** Any new invalidation composes with content-identity, never
  replaces it: keep the per-file BOM-strip/CRLF hash recipe, the write-side manifest stamps
  (`write_pipeline.py:685`, `resynthesize_pipeline.py:205`), `built_in_only` normalization,
  and the fresh-seed early-exit. NFR-002/SC-006.
- **DD-06 — Campsite in-WP.** Three SAFE-to-fold cleanups (`_compute_synthesized_drg`
  extraction, `_check_reference_id_parity` pre-extract, `_attempt_auto_refresh` literal hoist)
  sit inside the mission's edit targets — fold in their WP, no separate campsite WP.

## Follow-ups (out of scope — file at close)

- **#2760** — overlay-vs-new-built-in DRG URN collision on `spec-kitty upgrade` → #2721 lane.
- **#2157b** — analyzer-freshness coupling (charter creation invalidating a clean analysis).
- **#2773 coordination** — the references.yaml deprecation; DD-03 deliberately avoids a stopgap.
- Broader **#2519** authoring/`charter init` surface; step-model **Family 2** (#2751/#2761/#2769).
