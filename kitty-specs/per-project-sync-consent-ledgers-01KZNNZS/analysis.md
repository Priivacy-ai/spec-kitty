# Analysis: per-project sync consent ledgers

Date: 2026-08-10  
Mission: `per-project-sync-consent-ledgers-01KZNNZS`  
Mapped phase: requested `analyze`; installed Spec Kitty 3.2.6 exposes no standalone
`spec-kitty analyze` command, so this artifact records the required analysis step.

## Source-state findings

The current core tree already includes substantial #3030/#3167 hardening. The
implementation must therefore be gap-driven, not a rewrite.

### Existing strengths to preserve

- `src/specify_cli/sync/consent.py` already documents and implements a consent
  precedence chain where project-local records outrank machine index and absence
  denies. Its module documentation explicitly says `SPEC_KITTY_ENABLE_SAAS_SYNC`
  is machine-global arming, not per-project consent.
- `src/specify_cli/delivery/selection.py` already selects by stored
  `project_uuid`, resolves consent over distinct project UUIDs, and fetches only
  consented rows from the journal.
- `src/specify_cli/delivery/consent_gate.py` already uses `ConsentAnswer` and
  `ConsentedBatch` to make ordinary delivery calls carry resolved consent.
- `src/specify_cli/sync/body_upload.py` already asks the bodies' own
  `project_uuid` via `project_consents_to_hosted_sync()`, rather than relying on
  checkout-level routing.
- `src/specify_cli/sync/preflight.py` already reports legacy event/body-upload
  rows and refuses sync when legacy rows remain in scope.
- Existing tests with suffixes `_3030.py`, `_3108.py`, and architectural guards
  are valuable anchors. New tests should extend them or add narrowly named
  `_3262.py` fixtures only where the acceptance behavior is not already pinned.

### Remaining risk seams to inspect first

- Whether `ConsentLevel.ENV` can still produce a grant path in
  `resolve_project_consent()` or helper functions despite the module-level
  documentation.
- Whether machine-index grants can be created from environment-only state or
  stale checkout data without an explicit project opt-in.
- Whether acknowledgement, purge, retention, daemon drain, and history-import
  upload all consume `ConsentedBatch` / `ConsentAnswer` and do not mark refused
  rows terminal-success.
- Whether body-upload queued rows retain enough project identity to re-check
  consent at actual POST time, not only enqueue time.
- Whether migration from shared stores distinguishes imported, refused,
  ambiguous, and unchanged rows in a durable, idempotent way.
- Whether `sync status`, `sync doctor`, and docs clearly state that the global
  flag is not consent.

## Implementation guidance

1. Start WP01 by writing a failing test against any remaining env-as-grant path.
   If the current tree is already green for that behavior, document the existing
   passing test and move to the first unpinned edge.
2. Prefer small amendments to existing #3030 surfaces over new parallel
   abstractions. A second consent resolver is a regression.
3. Keep tests isolated from the operator's real `~/.spec-kitty` queue state.
4. Leave PR #3135 repair separate. This mission may reference it as related
   evidence but must not fold it into the implementation.
5. Treat SaaS #585 prevention evidence and historical remediation disposition as
   separate closure rows.

## Gate status

- Spec: committed.
- Plan: committed and accepted as substantive.
- Tasks/WPs: committed; `spec-kitty next` reports mission state `implement`,
  WP01 selected, 6 planned WPs.
- Tooling wrinkle: `spec-kitty tasks` generates valid lane metadata but fails its
  internal auto-commit with a stale protected-branch diagnostic claiming `main`.
  Manual commits on `feat/per-project-sync-consent` are therefore the safe path
  for mission artifacts until the metadata is reconciled.
