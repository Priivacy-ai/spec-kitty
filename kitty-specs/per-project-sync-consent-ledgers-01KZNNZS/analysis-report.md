---
schema_version: 1
artifact_type: spec-kitty.analysis-report
command: /spec-kitty.analyze
mission_slug: per-project-sync-consent-ledgers-01KZNNZS
mission_id: 01KZNNZSMG4FTNQ7AY6ZXJAJNG
generated_at: '2026-08-10T11:32:39.964845+00:00'
analyzer_agent: codex
input_artifacts:
  spec.md:
    path: /private/var/folders/h5/zqph_vqs3_77ctcqwvr_1b6m0000gn/T/spec-kitty-20260810-130708-cEJgwV/spec-kitty/kitty-specs/per-project-sync-consent-ledgers-01KZNNZS/spec.md
    sha256: b8b9e05b5930f5dfed4e88a655bdc523ea8afd89550d732637efbd7e5ca74822
  plan.md:
    path: /private/var/folders/h5/zqph_vqs3_77ctcqwvr_1b6m0000gn/T/spec-kitty-20260810-130708-cEJgwV/spec-kitty/kitty-specs/per-project-sync-consent-ledgers-01KZNNZS/plan.md
    sha256: 12142faf29c961e89e70e0ee956a10933b2c635045a0cbfb1237047b2c5e2bdb
  tasks.md:
    path: /private/var/folders/h5/zqph_vqs3_77ctcqwvr_1b6m0000gn/T/spec-kitty-20260810-130708-cEJgwV/spec-kitty/kitty-specs/per-project-sync-consent-ledgers-01KZNNZS/tasks.md
    sha256: ecaaedbf3af4b636ea51543f3d6db73e1ad0bfc4f1fd2c12c1f4623562bbbd45
  charter:
    path: /private/var/folders/h5/zqph_vqs3_77ctcqwvr_1b6m0000gn/T/spec-kitty-20260810-130708-cEJgwV/spec-kitty/.kittify/charter/charter.yaml
    sha256: c304520c64195493fc9394b11cb5b84c91569eafe268aa3d194be58ffaee8305
verdict: unknown
issue_counts:
  info:
  medium:
  high:
  low:
  critical:
findings: []
---

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
