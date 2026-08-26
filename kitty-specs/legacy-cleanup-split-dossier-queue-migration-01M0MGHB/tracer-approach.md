# Approach — legacy-cleanup-split-dossier-queue-migration

## Scope (settled by the operator dispatch, not re-litigated here)

IN SCOPE — components 2-5 of issue #1058's plan:
1. Make live dossier emitters canonical-only: delete the local Pydantic mirror in
   `src/specify_cli/dossier/events.py` and the legacy-positional `*args` bridge
   (`_coerce_legacy_positional_args`); import `LocalNamespaceTuple`, `ArtifactIdentity`,
   `ContentHashRef` and the four `MissionDossier*Payload` types from `spec_kitty_events`.
2. Replace the four hand-maintained dossier entries in `_PAYLOAD_RULES`
   (`src/specify_cli/sync/emitter.py`, ~lines 827-897) with
   `spec_kitty_events.conformance.validate_event(payload, event_type, strict=True)`.
3. Add an AST-based guard test preventing production positional calls to the dossier
   emitters.
4. Re-point imports in `tests/dossier/test_events.py`, `tests/dossier/test_emitter_adapter.py`,
   `tests/sync/test_events_namespace.py`.

OUT OF SCOPE — binding operator decision:
- The issue's plan step 1 (queue-drain-path migration, `_migrate_legacy_dossier_payload` in
  `sync/queue.py`) is superseded by mission #3293 (merged 2026-08-13), which deleted that
  symbol wholesale. `sync/migrate_journal.py` is its replacement and is NOT in scope for this
  mission. The spec records this as a Clarification/decision, not as work to do.

## Decisions to persist into spec.md `## Clarifications`

1. Queue-drain half of #1058 is superseded by #3293 — closed as such in the PR description,
   not implemented.
2. No transitional deprecated wrapper needed (readiness probe: no external callers; every
   in-repo call site is keyword-only).
3. Canonical validation via `spec_kitty_events.conformance.validate_event()` is in scope now,
   NOT coupled to `spec-kitty-events#50` merging — the checkout already pins
   `spec-kitty-events>=6.0.0,<7.0.0` and 6.1.0 already ships `validate_event()` with the
   `manifest_step` minLength:1 and `artifact_count` minimum:0 constraints enforced in its
   JSON schemas. #50 adds fixtures, not new constraints. Mission writes its own regression
   tests against `validate_event()`.

## Charter clauses driving this spec
- §Architecture: Shared Package Boundaries — do not vendor `spec-kitty-events` source into
  the CLI package; the 24KB local mirror in `dossier/events.py` is close to precisely what
  that forbids.
- §Pre-existing Failure Reporting Rule — baseline against issue #3284 (23 known-red tests,
  2 errors) before attributing any red to this mission; anything beyond that set needs a
  NEW issue.
- Silent-success is the dominant failure mode here — spec states explicit raise/report/
  refuse behaviour for every changed path.
- Red-first/ATDD — every changed behaviour gets a test that fails when the change is
  reverted.
