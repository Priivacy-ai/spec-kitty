# Contract — Synthesize Library Seam & CLI (Charter Synthesize Reconciliation)

This mission has no HTTP/GraphQL surface. The "contracts" are the library seam signature +
return, the CLI flags, and the reconciler consumption — the interfaces tasks must honor.

## Library seam — `charter.activation.synthesizer.orchestrator.synthesize`

**Current**: `synthesize(request, adapter=None, repo_root=None) -> SynthesisResult`

**Contract after this mission**:
- Add a mode selector (default preserves): e.g. `synthesize(request, adapter=None, repo_root=None, *, mode: SynthesizeMode = SynthesizeMode.preserve) -> SynthesisResult`.
  - Backward compatible: existing positional callers (`synthesize(request, adapter, repo_root)`) and all current tests keep working; the default is `preserve`.
- Behavior by mode:
  - `preserve` (default): reconcile emitted overlay+manifest against on-disk (reuse `_merge_project_overlay` + `_rewrite_manifest`); **drop nothing**; write merged; succeed.
  - `dry_run`: compute the `ReconciliationDelta`; **write nothing**.
  - `prune`: write merged minus `removable`.
- Return: `SynthesisResult` carries (or exposes) a `ReconciliationDelta` (`retained/added/removable/manifest_delta/conflicts`).
- **MUST NOT**: silently drop backed nodes/edges/manifest entries in any mode except `prune` (NFR-001); introduce a new uncaught exception on divergent inputs (NFR-003) — preserved-content conflicts go into `delta.conflicts`, not a raise.
- **MUST**: keep a no-op (identical-input) `preserve` run byte-identical for graph AND manifest (NFR-002).

## CLI — `spec-kitty charter synthesize`

| Invocation | Mode | Exit | Output |
|-----------|------|------|--------|
| `charter synthesize` (backed divergence) | preserve | 0 | writes merged; reports retained content + any preserved-conflict warnings |
| `charter synthesize --dry-run` | dry_run | 0 | reports `removable` + `conflicts`; **writes nothing** |
| `charter synthesize --prune` | prune | 0 | removes `removable`, **lists each deletion** |
| `charter synthesize` (orphaned removal w/o `--prune`) | — | 1 | **refuses**, lists conflicts + remediation (DRG typed-conflict shape) |
| `charter synthesize` (unparseable on-disk overlay) | — | 1 | **refuses**, no write |

- Refusal/prune/dry-run output uses the NEW `ReconciliationConflict` object in
  `src/charter/activation/synthesizer/reconcile.py` (`kind` + `target_id` + `backing_artifact` +
  `remediation` + `provenance`), **modeled after — not reusing** — the `src/doctrine/drg/merge.py`
  typed-conflict shape (that `OrgDRGConflict`/`_CONFLICT_REMEDIATIONS` model is the org-pack
  fragment-merge subsystem: closed `kind` Literal with no `duplicate_triple`, no
  `backing_artifact`/`remediation`, and is not on the synthesize path — `validate_graph` returns
  `list[str]`). The reconciliation `kind` names are distinct — `duplicate_triple` and
  `preserved_dangling_endpoint` (not `merge.py`'s `unresolved_edge_endpoint`). Every reported
  class carries a remediation line, enforced by a completeness test in `reconcile.py` mirroring
  `merge.py`'s `test_every_conflict_class_carries_a_remediation_line`.

## Boundary reconciler — `charter_runtime.preflight.runner._attempt_auto_refresh`

- Invokes synthesize with **no prune/dry-run flags** (inheriting the preserve default), so a
  **backed** divergence heals exit-0 and non-destructively. This is NOT a "never refuses" guarantee:
  an **orphaned** node (backing artifact deleted) or an **unparseable on-disk overlay** still
  refuses (the same fail-closed guard the CLI surfaces), because the boundary runs the same flagless
  command and inherits its refusal. The boundary surfaces such a refusal as an actionable
  `blocked_reason` (name + remediation) — it never silently prunes.
- On the references-parity stale cause, additionally runs targeted `generate` honoring the
  `#2772` curated-`charter.md` contract (0 bytes changed).
- After a successful heal, `synthesized_drg` resolves to `fresh`; a repeat `implement`/`next`
  is not re-blocked.

## Activation — `cli/commands/charter/activate.py` / `deactivate.py`

- The in-process synthesize call defaults to `preserve` (no silent truncation).
- `run_resynthesize_pipeline` (which calls full synthesize) is renamed to reflect intent (FR-013).

## WP01→WP02 conflict interface (in-memory — NO filesystem sidecar)

The hand-off between conflict *detection* (WP01) and the suppress-vs-raise *decision* (WP02) is
entirely in-memory within one in-process `synthesize()` call. There is **no**
`.reconcile-conflicts.json` staging sidecar (filesystem IPC inside a single call would contradict
this in-memory contract-of-record).

- **WP01** (owns `orchestrator.py` + `reconcile.py`): after merging, detects and classifies
  preserved-content conflicts (via the structured duplicate/dangling helpers in `validator.py`,
  see below) and **populates `delta.conflicts`** with `ReconciliationConflict` objects (each tagged
  `provenance ∈ {preserved, new_emit}`) before returning the `ReconciliationDelta`.
- **WP02** (owns `validation_gate.py`): `validate()`'s signature is **widened** to accept the
  classified conflicts (the emitted-vs-preserved partition). It performs ONLY the suppress-vs-raise
  decision — a `preserved` conflict is suppressed + reported; a `new_emit` collision raises
  `ProjectDRGValidationError` as today. WP01 changes the call site to pass them; WP02 changes the
  signature. Clean split, no filesystem IPC.
- **Structured detection SSOT**: duplicate-`(source,target,relation)` and dangling-endpoint
  detection is extracted once as structured helpers in `src/doctrine/drg/validator.py`
  (e.g. `duplicate_edge_triples(graph) -> list[DRGEdge]`, `dangling_endpoints(graph) -> list[DRGEdge]`)
  that BOTH `validate_graph` (string formatting) and `reconcile.py` (provenance classification)
  consume — one definition of "duplicate"/"dangling", not a fork.

## Contract tests (map to the acceptance suite, IC-08)

- `preserve` keeps backed node+edge (committed) · `--prune` removes + lists · `--prune` no-op ·
  `--dry-run` non-empty delta + no write · `--dry-run` empty delta · no-op byte-stability
  (graph + manifest) · manifest version-skew reconcile · preserved duplicate-triple → report ·
  preserved dangling-endpoint → report · unparseable overlay → refuse/no-write · boundary heal
  non-destructive + clears stale + not re-blocked + `charter.md` untouched · activate/deactivate
  preserve · edge-wiring positive + no-fabrication.
