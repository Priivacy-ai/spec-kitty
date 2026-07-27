# Research — Doctrine-activation freshness integrity

Phase-0 consolidation. Evidence lives in `research/grounding-brief.md` (architect-alphonso
seam grounding) and `research/code-state-verification.md` (paula code-state falsification +
carla foldability). This file records the *decisions* those briefs drove.

## Decision 1 — Reconcile via read-path parity, not eager-always regen

- **Decision**: Close the seam with option (c): wire the already-built `run_consistency_check`
  parity (config↔references / config↔graph) into the freshness **read-path**
  (`_compute_synthesized_drg`), plus an opt-in `--resynthesize`. (Q2 = option a.)
- **Rationale**:
  - `commit_plan` (the config-write chokepoint) is **pure charter** and cannot import
    `specify_cli` (C-001) — the regen pipeline is `specify_cli`-orchestrated, so eager regen
    would invert the layer or duplicate at every call-site.
  - Default activate must stay fast (NFR-001) and the `spec-kitty upgrade` migration +
    `org_charter` `promote_activations` must pay no synthesis (NFR-003).
  - **Decisive**: `merge_defaults` (`pack_manager.py:747/753`) writes `activated_*` state
    **outside** `commit_plan`, is test-covered, and is ADR-slated (2026-07-15-1 S1) for the
    `init` path. A write-side marker stamped at the chokepoint would be **blind** to it and
    re-open the hole on init. Read-path parity reads `config.yaml` directly
    (`consistency_check.py:_load_raw_activation_lists:197`) → **writer-agnostic** → dominates.
- **Alternatives considered**:
  - *(a) regenerate-on-activate*: rejected — layer inversion + hot-path + migration harm.
  - *(b) fail-closed only*: insufficient alone — needs the signal made visible first.
  - *(c-marker) write-side invalidation marker*: rejected — blind to the `merge_defaults`/`init` bypass.

## Decision 2 — Sequence #2758 → #2759 → #2157a; #2770 early-standalone

- **Decision**: Fix the signal's input-set (#2758) before wiring more consumers (#2759),
  then aggregate the gate (#2157a). Land the #2770 un-pin **first and independently**.
- **Rationale**: A definitional false-stale (#2758) would be inherited by the seam if wired
  first. The gate aggregation (#2157a) is meaningful only once the `synthesized_drg` signal is
  activation-visible (#2759). #2770 is release-sensitive (P0, red-main ADR 2026-07-17-1) and has
  no hard dependency on the mechanism — the seam prevents *recurrence*, the un-pin clears the
  *current* red — so it lands early (operator decision).

## Decision 3 — Q1: references.yaml fail-closed preflight (not hash-narrowing)

- **Decision** (operator, decision_id `01KXRVT2KA1Y3M4XQAYVQ3HHXF`): keep the 4-file content-hash;
  when `references.yaml` is absent, surface a single actionable "run `charter generate` first"
  preflight instead of a dead-end `None`.
- **Rationale**: #2773 (same epic #2519) is separately deprecating `references.yaml` and making
  `charter.yaml` authoritative. Narrowing the hash to the sync-triad now would build a stopgap
  #2773 later rips out (#2773's body already flags the #2767 references recompile as exactly that
  anti-pattern). Fail-closed leaves #2773 clean and requires no dual-edit
  (`bundle.py:47` + `computer.py:137`) nor reconciling the manifest derived-set(3)/hash-set(4)
  mismatch. **No `references.yaml` stopgap.**
- **Alternatives considered**: *narrow-to-triad* — simpler signal but pre-empts #2773 and needs
  the dual-edit + manifest reconciliation; deferred to #2773's owner.

## Decision 4 — Preserve the #2732 content-identity machinery

- **Decision**: Any new invalidation **composes with** content-identity, never replaces it.
  Keep the per-file BOM-strip/CRLF hash recipe, the write-side manifest stamps
  (`write_pipeline.py:685`, `resynthesize_pipeline.py:205`), the `built_in_only` read-time
  normalization, and the fresh-seed early-exit (`computer.py:367-408`).
- **Rationale**: #2732 just landed (the mtime→content-identity move); the parity signal is an
  *additional*, orthogonal signal, not a change to what the hash covers. NFR-002/SC-006.

## Decision 5 — Fences (out of scope)

- **#2760** (overlay-vs-new-built-in DRG URN collision on `spec-kitty upgrade`) → DRG-model lane
  #2721 (it exists *because* #2721 grows the built-in NodeKind set — an upgrade⇒overlay-revalidation
  axis, orthogonal to config↔derived blindness). Fence confirmed by carla.
- **#2157b** (analyzer-freshness: creating the charter re-hashes it as an analysis input) →
  a different subsystem (`analysis_report.check_analysis_report_current`), not the charter/DRG
  freshness seam. C-004. Only #2157a (charter-owed aggregation) is in scope. Fence confirmed by carla.
- Broader **#2519** authoring/`charter init` surface, and step-model **Family 2**
  (#2751/#2761/#2769) — separate slices.

## Open items carried into implement

- The exact charter→reference citation surface for IC-01 (which file declares/compiles the
  built-in citation that `test_no_new_charter_reference_danglers` checks) — resolve red-first in the WP.
- The exact synthesize/generate preflight surface for IC-02's fail-closed guard — resolve in the WP.
- The DRG regen delta N — **compute** from a fresh `generate_graph`, then re-freeze the baseline.
