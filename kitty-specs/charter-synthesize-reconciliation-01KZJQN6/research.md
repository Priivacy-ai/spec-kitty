# Phase 0 Research — Charter Synthesize Reconciliation

Consolidated from the mission research + adversarial grounding + post-spec squad. Every entry
resolves a design unknown; there are no open `[NEEDS CLARIFICATION]` markers.

## D1 — Where the loss happens (mechanism)

- **Decision**: Reconcile at `orchestrator.synthesize._validation_callback` (`src/charter/activation/synthesizer/orchestrator.py:179-188`), which today calls `emit_project_layer(targets=targets)` and persists a brand-new overlay with no read of the on-disk graph; `write_pipeline.promote` (`write_pipeline.py:635-643`) whole-file-swaps it in.
- **Rationale**: All three lossy surfaces (manual `synthesize`, boundary `auto_refresh` subprocess, `activate`/`deactivate` via `run_resynthesize_pipeline`) funnel through this one seam, so a single fix covers them.
- **Alternatives considered**: Fixing only the CLI command (misses auto_refresh/activate); a byte-equality short-circuit (`_substantively_equal` already exists and does NOT prevent loss when the target set genuinely differs).

## D2 — Preserve-and-warn vs refuse-with-prune (the load-bearing decision)

- **Decision**: **Preserve-and-succeed at the library seam**; `--prune` (CLI) removes; non-zero refusal narrowed to the manual CLI for unpreservable cases only. (Ledger `01KZJV6H7TW63M6ZGNM05XKM2S`, supersedes `01KZJQP5K4C0VGNB53GZZT3QWP`.)
- **Rationale**: `auto_refresh` runs a flagless `charter synthesize` judged purely by exit code (`preflight/runner.py:406,508`). An abort default keeps `implement`/`next` trapped; a `--prune` default deletes at the boundary (reintroduces the P0). Only preserve-and-succeed is exit-0-and-non-destructive. It also matches the committed test and the doctrine "warn, do not hard-block" posture.
- **Alternatives considered**: strict refuse-with-prune (breaks auto_refresh + committed test + doctrine); hybrid backed/unbacked (folded in: backed → preserve, orphaned removal without `--prune` → refuse).

## Doctrine anchor

- **Decision**: Conform to ADR `2026-07-26-3`'s warn/report posture. Introduce a NEW `ReconciliationConflict` in `src/charter/activation/synthesizer/reconcile.py`, **modeled after** — not reusing — the DRG typed-conflict shape in `src/doctrine/drg/merge.py` (`OrgDRGConflict.kind`, `resolution_applied`, `_CONFLICT_REMEDIATIONS`). `merge.py` is the org-pack fragment-merge subsystem — its `kind` Literal is closed (no `duplicate_triple`), it has no `backing_artifact`/`remediation` fields, and the synthesize path's `validate_graph` returns `list[str]` — so this is net-new translation, not reuse; `merge.py` is not edited. `reconcile.py` carries its own remediation vocab (`duplicate_triple`, `preserved_dangling_endpoint`) with a completeness gate mirroring `test_every_conflict_class_carries_a_remediation_line`. Use that new object for refusal/prune/dry-run messaging.
- **Rationale**: That is the canonical node/edge no-silent-drop machinery with a warn/report posture and per-class remediations. ADR `2026-05-16-1` (originally cited) is field-grain layer merge and chose warn-not-block Option C — precedent only.
- **Alternatives considered**: a hand-rolled "name each URN + artifact" message (FR-014 rejects this — reuse the typed shape).

## Manifest reconciliation

- **Decision**: Apply `_rewrite_manifest` + pass `manifest_override` on the synthesize path (`orchestrator.py:193-198` currently passes none), mirroring `resynthesize_pipeline.py:453,483`.
- **Rationale**: Reconciling only the graph while rebuilding the manifest from current results recreates the reported version-skew (manifest registers fewer artifacts than the graph) and breaks manifest no-op byte-stability (NFR-002).
- **Alternatives considered**: graph-only reconcile (rejected — recreates the bug on the manifest).

## Merged-overlay conflict handling

- **Decision**: Validate the merged (preserved + emitted) overlay and route a *preserved-content* conflict (duplicate `(source,target,relation)` triple; dangling endpoint) to the report channel; keep a *new-emit* collision as a hard error.
- **Rationale**: Preserved nodes/edges bypass `emit_project_layer`'s additive guard, then hit `merge_layers` (`loader.py:189` concatenates edges) + `validate_graph` (`validator.py:209-237` hard-fails on dup triple / dangling). Without routing, silent loss becomes a hard crash-and-trap on exactly the target inputs.
- **Alternatives considered**: let validation raise (rejected — converts P0 loss into P0 crash).

## Boundary heal clears freshness

- **Decision**: After a non-destructive heal, re-stamp `synthesized_drg` to fresh; ensure `_attempt_auto_refresh` consumes the preserve path (exit 0) and is not re-blocked on the next run.
- **Rationale**: Preserving content without clearing the stale signal yields an infinite non-destructive re-block loop; FR-008/SC-002 require the workflow to actually un-trap.
- **Alternatives considered**: rely on the existing rebuild re-stamp (rejected — it is coupled to the destructive rebuild we are removing).

## #2777 references-parity completion

- **Decision**: `_attempt_auto_refresh` runs a targeted `generate` only when the stale cause is references-parity, honoring the landed `#2772` curated-`charter.md` preservation contract.
- **Rationale**: `synthesize` never recompiles `references.yaml`; only `generate` does. `#2772`/`#2759` are merged, so the clobber risk is contracted, not open.
- **Alternatives considered**: unconditionally add `generate` to auto_refresh (rejected — clobbers `charter.md`, trips the dirty-tree guard).

## #3052 edge wiring

- **Decision**: Populate `source_urns` for the currently-empty consumer-pack interview sections (`interview_mapping.py` / `targets.py`) so `emit_project_layer`'s existing `source_urns`→edge derivation (`project_drg.py:215-241`) emits the declared edges; emit no edge without declared evidence.
- **Rationale**: The only safe edge evidence at synthesis time is the interview mapping's `source_urns`; inferring relationships from the DRG risks fabricating wrong governance edges (worse than an orphan).
- **Alternatives considered**: infer edges from the built-in DRG snapshot (rejected — fabrication risk; NFR-007 forbids).

## Library-vs-CLI placement

- **Decision**: Preserve/merge lives in the library seam; `--prune`/`--dry-run`/refusal decisioning lives in the CLI. Thread mode via an explicit parameter/return, NOT a `--prune` default on `synthesize(request, adapter, repo_root)`.
- **Rationale**: Keeps FR-004's one-seam coverage, gives `auto_refresh`/`activate` a safe default, and avoids breaking the many existing library/test callers.
- **Alternatives considered**: refuse in the library (breaks callers + auto_refresh).
