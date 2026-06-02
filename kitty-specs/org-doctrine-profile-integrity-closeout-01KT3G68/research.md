# Research — Org Doctrine Profile Integrity Close-Out

Hardening mission; the only genuinely ambiguous decisions are recorded here. All others are mechanical (see plan.md). No new technology evaluation — the stack is the existing spec-kitty Python codebase.

## R1 — Inline-reference rejection: skip vs propagate (drives FR-001, FR-003, I-1/I-9)

**Context.** `repository.py:423-424` deliberately *propagates* `InlineReferenceRejectedError` ("a hard, fail-closed contract violation … so the author fixes the error"). `diagnostics.py:6` lists inline-ref rejection as a *skip reason*. The doctor health collector `_collect_profile_health` wraps profile loading in a broad `except Exception` that degrades to an empty report → `healthy = all([]) = True`. Net: a pack with an inline-ref-invalid profile is reported HEALTHY and all profiles vanish (the #1584 false-healthy class, reproduced).

**Decision (default — surgical, minimal blast radius):** Keep the load-layer's deliberate propagation for general callers (`resolve_profile`/`get_ancestors` continue to fail-closed on a contract violation), but make the **doctor health consumer** the place that surfaces it: `_collect_profile_health` must catch `InlineReferenceRejectedError` (specifically, not a blanket `except Exception`) and translate it into a degraded `PackHealth(healthy=False)` with the invalid profile surfaced (path, id, error summary) — never an empty/green report. Reconcile `diagnostics.py`'s docstring to state: inline-ref rejection propagates from the load layer and is surfaced by the health collector as an invalid profile (resolving I-9 in lockstep).

**Rationale:** A hardening mission must not change global profile-load semantics (regression risk to every `resolve_profile` caller). Confining the fix to the diagnostics consumer restores the #1584 invariant ("invalid profiles are visible, packs are not falsely healthy") with the smallest possible surface, and keeps the deliberate fail-fast the parent authors chose.

**Alternative considered (reviewer-debbie's first option):** Catch in `repository._load_layer` → `_record_skip` so inline-ref rejection becomes a recoverable skip everywhere (aligns code to the existing diagnostics docstring). Rejected as the default because it silently changes the load contract for all callers and weakens an intentional fail-closed; may be revisited if the team prefers "broken profile = unavailable, never raises." The integration test (FR-002) is written against the *observable* `doctor doctrine` outcome, so it stays valid under either design.

## R2 — FR-036 dead-symbol claim accuracy (drives FR-009, I-6)

**Decision:** Remove the two redundant re-exports (`SignificanceEvaluatedPayload`, `TimeoutExpiredPayload`) from `events.py.__all__` — the canonical definitions and live callers are in `…_internal_runtime/significance.py`; the `events.py` entries are unused re-exports masking that fact. Drop their `_SYMBOL_ALLOWLIST` entries. Keep `JsonlEventLog` allowlisted (genuinely no `src/` caller) with a precise rationale.
**Rationale:** Makes the dead-symbol gate reflect the true surface and honors FR-036's literal "remove the stale entries" rather than papering over with allowlist. Lowest-risk: removing an unused re-export cannot break a caller (verified none import from `events.py`).
**Alternative:** Re-scope the FR-036 claim text to admit two re-exports remain — rejected; the cleaner state is achievable.

## R3 — Cascade-warning removal (drives FR-008, I-5)

**Decision:** The CLI owns cascade via `charter.cascade`; pass `cascade=False` to `manager.activate/deactivate` so `pack_manager`'s obsolete deferral-warning branch never fires (preferred over deleting the branch, to avoid touching `pack_manager`'s broader contract). If passing `False` proves to disable needed behavior, fall back to deleting the stale warning blocks. Add a test asserting the "not yet implemented"/"deferred" string is absent from `--cascade` output.
**Rationale:** Minimal, reversible; keeps `pack_manager` API stable while removing the contradictory operator message (FR-016/FR-020 intent).

## R4 — Charter facade for template catalog (drives FR-006, I-4)

**Decision:** Add `src/charter/template_catalog.py` as a pure re-export facade (mirroring `charter.profiles`/`charter.resolution`) exposing `discover_templates`, `TemplateRef`, `TierRoot` from `doctrine.template_catalog`, with `__all__`. Repoint `list_cmd.py` (and `activate.py`'s artifact-kind imports) to `charter.*`. Then both files leave the boundary allowlist → baseline 0.
**Rationale:** Sanctioned ACL/facade pattern already established for other doctrine types; the only reason the allowlist grew was the missing facade. Net-positive for C-006/C-004.
