# Decision Moment `01KZ375V17RFAJTYGXG20JJACW`

- **Mission:** `review-cycle-verdict-seam-rebuild-01KZ2W7W`
- **Origin flow:** `plan`
- **Slot key:** `plan.authority.override-vocabulary-revised`
- **Input key:** `override_vocabulary_revised`
- **Status:** `resolved`
- **Created:** `2026-08-03T07:07:28.167506+00:00`
- **Resolved:** `2026-08-03T07:07:49.297105+00:00`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

SUPERSEDES 01KZ336SP7VNGZ5ZH4PY43H32N. That decision chose between widening ReviewResult.verdict and adding a flag beside it. Both options were malformed: an event-sourced ReviewOverride already exists as the declared authority, and ADR 2026-07-19-1 pins the typed WPInnerStateDelta slot as the chartered mechanism. How should the override be represented?

## Options

_(none)_

## Final answer

Reuse the existing event-sourced ReviewOverride as the single authority; add no new representation. IC-09 retires the others into it: the arbiter_override frontmatter block (arbiter.py:437-460) and the arbiter-override-N.json sidecars (_persist_standalone_json). The review_artifact_override_* frontmatter fields are read-only with no writer since 2026-07-01 and are owned by wp-runtime-state-eviction-01KXWN13's deferred WP10 — out of scope here, recorded as a cross-mission dependency. Backing: ADR 2026-07-19-1 pins the typed WPInnerStateDelta slot on InnerStateChanged as the chartered mechanism and states 'one authority per datum'; ReviewOverride's docstring explicitly forbids inventing review_artifact_override_* fields. This also closes the external-ingress hole: orchestrator_api/commands.py:1296 validates ReviewResult at exactly four fields, so a flag there would have left an external orchestrator unable to express a waiver.

## Rationale

_(none)_

## Change log

- `2026-08-03T07:07:28.167506+00:00` — opened
- `2026-08-03T07:07:49.297105+00:00` — resolved (final_answer="Reuse the existing event-sourced ReviewOverride as the single authority; add no new representation. IC-09 retires the others into it: the arbiter_override frontmatter block (arbiter.py:437-460) and the arbiter-override-N.json sidecars (_persist_standalone_json). The review_artifact_override_* frontmatter fields are read-only with no writer since 2026-07-01 and are owned by wp-runtime-state-eviction-01KXWN13's deferred WP10 — out of scope here, recorded as a cross-mission dependency. Backing: ADR 2026-07-19-1 pins the typed WPInnerStateDelta slot on InnerStateChanged as the chartered mechanism and states 'one authority per datum'; ReviewOverride's docstring explicitly forbids inventing review_artifact_override_* fields. This also closes the external-ingress hole: orchestrator_api/commands.py:1296 validates ReviewResult at exactly four fields, so a flag there would have left an external orchestrator unable to express a waiver.")
