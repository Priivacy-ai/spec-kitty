# Decision Moment `01M0JN29JGRA2GVEJJ89JZH3R2`

- **Mission:** `retire-doctrine-term-01M0JMK9`
- **Origin flow:** `specify`
- **Slot key:** `specify.compatibility.alias-policy`
- **Input key:** `compatibility_alias_policy`
- **Status:** `resolved`
- **Created:** `2026-08-21T17:14:30.352336+00:00`
- **Resolved:** `2026-08-21T17:14:31.493043+00:00`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

Compatibility policy for executable user-facing surfaces (CLI command/flag names, skill names): hard break now, or deprecate in 3.x with removal by 4.0?

## Options

- Hard break, no aliases
- Deprecate in 3.x (hidden aliases + warnings), all user-visible doctrine gone by 4.0
- Split: prose renames outright, executable surfaces get aliases

## Final answer

Deprecate in 3.x: old executable names become hidden aliases with deprecation warnings. Hard rule: by 4.0, zero user-visible 'doctrine' remains.

## Rationale

_(none)_

## Change log

- `2026-08-21T17:14:30.352336+00:00` — opened
- `2026-08-21T17:14:31.493043+00:00` — resolved (final_answer="Deprecate in 3.x: old executable names become hidden aliases with deprecation warnings. Hard rule: by 4.0, zero user-visible 'doctrine' remains.")
