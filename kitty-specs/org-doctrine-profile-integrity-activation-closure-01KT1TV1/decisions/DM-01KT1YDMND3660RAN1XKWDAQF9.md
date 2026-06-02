# Decision Moment `01KT1YDMND3660RAN1XKWDAQF9`

- **Mission:** `org-doctrine-profile-integrity-activation-closure-01KT1TV1`
- **Origin flow:** `plan`
- **Slot key:** `plan.migration.field-retirement`
- **Input key:** `field_retirement_strategy`
- **Status:** `resolved`
- **Created:** `2026-06-01T15:56:43.053331+00:00`
- **Resolved:** `2026-06-01T15:59:02.498396+00:00`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

OQ-2 chose DRG-fragment-only authoring, retiring the enhances/overrides/specializes_from FIELDS. How should existing field-authored artifacts (built-in doctrine + the 5 kinds #1291 just shipped + agent profiles) transition?

## Options

- Deprecation window: tolerate fields (read+warn, auto-project to DRG), remove later
- Hard cutover: migrate all artifacts to DRG fragments in this mission, fields rejected
- Tolerate built-in fields indefinitely as projection, only org/project packs must use fragments

## Final answer

Hard cutover. 3.2.0 is unreleased, so rc/bleeding-edge breakage is acceptable and preferred over a deprecation window that would leave problematic dual-path code. Migrate all built-in + shipped artifacts (incl. the 5 #1291 kinds and agent_profile.specializes_from) to DRG-fragment authoring in this mission; the relationship FIELDS become a validation error. No tolerate/auto-project compatibility path.

## Rationale

_(none)_

## Change log

- `2026-06-01T15:56:43.053331+00:00` — opened
- `2026-06-01T15:59:02.498396+00:00` — resolved (final_answer="Hard cutover. 3.2.0 is unreleased, so rc/bleeding-edge breakage is acceptable and preferred over a deprecation window that would leave problematic dual-path code. Migrate all built-in + shipped artifacts (incl. the 5 #1291 kinds and agent_profile.specializes_from) to DRG-fragment authoring in this mission; the relationship FIELDS become a validation error. No tolerate/auto-project compatibility path.")
