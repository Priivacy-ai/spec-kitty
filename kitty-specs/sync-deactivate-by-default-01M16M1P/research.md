# Research: Sync Deactivated By Default

## Decision 1 — Single `sync_active()` seam (replace, not stack)
- **Decision**: Add `sync_active()` to `src/specify_cli/core/env.py` = `is_saas_sync_enabled() and first_set_sync_disable_env() is None`. Route registration, daemon spawn, all emission, emitter local-capture, and body-capture through it, **replacing** the existing scattered `is_saas_sync_enabled()` checks.
- **Rationale**: The current surface gates *some* sites on `is_saas_sync_enabled()` (daemon.py:1154, events.py:109/182) and *others* not at all (registration only checks MINIMAL_IMPORT; local-capture is deliberately un-gated per #1072). A single predicate makes "disable wins" structural and closes the asymmetry defect class (DIR-043/044).
- **Alternatives considered**: (a) minimal 3-site routing through `is_saas_sync_enabled()` (research-01) — REJECTED: leaves precedence drift (disable doesn't win at the already-gated sites) and misses the local-capture warning path. (b) a new dedicated `SPEC_KITTY_SYNC_ACTIVE` flag — REJECTED by C-001 (no new sync flag).

## Decision 2 — Arming is not consent (C-007)
- **Decision**: `sync_active()` is machine-level arming, strictly upstream of the per-project egress consent gate (`sync/egress.py:55-70`). The consent gate is untouched.
- **Rationale**: Conflating the two would let "armed" imply "may egress", bypassing consent — a privacy regression. Post-spec architect lens flagged this boundary explicitly.

## Decision 3 — #3470 keyed on sync-inactive, before enqueue
- **Decision**: Short-circuit `trigger_feature_dossier_sync_if_enabled` (`dossier_pipeline.py:471`) on `not sync_active()`, returning before any enqueue/permit.
- **Rationale**: The traceback (`body_queue.py:106` raise, surfaced via `dossier_pipeline.py:290` `logger.exception`) fires on a bare install where NO disable var is set. Research-02's disable-vars-only guard would never fire there → traceback survives. Keying on inactive fixes the default path. It is a gated early-return, not a `try/except` widen (FR-008 anti-swallow), so real destination violations still surface when active. `_require_project_destination` is a correct INV-5 invariant and stays (C-003).

## Decision 4 — #2801 clean-cut
- **Decision**: `tasks_move_task.py:993` pre-review gate reads only a new `SPEC_KITTY_PRE_REVIEW_GATE_DISABLE`; it stops honoring `first_set_sync_disable_env()`. Its tests (`tests/review/test_pre_review_gate_*.py`) are rewritten to the new env.
- **Rationale**: Deactivating sync via the shared toggles would otherwise silently disable a correctness gate on every install. Blast-radius check: the only behavioral consumers of the sync toggles are the pre-review gate and the (redundant) daemon skip → cut is safe. `SPEC_KITTY_PRE_REVIEW_GATE_DISABLE` is a gate flag, not a sync flag, so C-001/FR-016 hold.

## Decision 5 — Test de-masking + gating mechanism
- **Decision**: Module-level `skipif` on the opt-in (NOT the `quarantine` marker, which the visibility job re-runs). Invert `tests/conftest.py:223` setdefault + `:427` autouse to default-off; add `sync_enabled`/`sync_disabled` fixtures; add one CI job running `tests/sync/` opted-in, keeping lane markers so the collection-completeness gate stays green. A checked-in file-count census (FR-013) fails on deletion AND un-skipping.
- **Rationale**: The completeness gate is about SELECTION not execution; skipif preserves selection. The conftest force-opt-in currently masks the default-off path — without inverting it, every skipif is inert (SC-003 unsatisfiable).

## Supply-chain security
- **N/A**: this mission adds/upgrades/removes **no** dependency. No registry/lifecycle-script/LTS considerations apply.

## Adversarial evidence (post-spec squad, 3 lenses)
All contested findings folded — dispositions:
- Seam should replace not stack (architect FLAW-2) → **accepted** (Decision 1, C-008).
- #3470 predicate mismatch (architect FLAW-1) → **accepted** (Decision 3, FR-007).
- Emitter local-capture gap (completeness) → **accepted** (FR-006).
- Conftest masking makes SC-003 unsatisfiable (adversarial + architect FLAW-3) → **accepted** (Decision 5, FR-010).
- Anti-swallow criterion (adversarial) → **accepted** (FR-008, SC-005).
- NFR-004 as collection diff (adversarial) → **accepted** (NFR-004 restated).
- Deletion loophole (adversarial) → **accepted** (FR-013).
- Docs/CHANGELOG/doctor advisory missing (completeness) → **accepted** (FR-017/018).
No contested finding dropped.
