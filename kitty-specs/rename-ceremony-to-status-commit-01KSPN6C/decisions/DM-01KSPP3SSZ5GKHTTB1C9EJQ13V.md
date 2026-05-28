# Decision Moment `01KSPP3SSZ5GKHTTB1C9EJQ13V`

- **Mission:** `rename-ceremony-to-status-commit-01KSPN6C`
- **Origin flow:** `plan`
- **Slot key:** `plan.doctrine.rewording-strategy`
- **Input key:** `doctrine_rewording_strategy`
- **Status:** `resolved`
- **Created:** `2026-05-28T06:59:53.279630+00:00`
- **Resolved:** `2026-05-28T07:02:03.187036+00:00`
- **Other answer:** `false`

## Question

In src/doctrine/skills/spec-kitty-program-orchestrate/SKILL.md the phrase 'full ceremony' means 'the full mission workflow', not a status commit. Mechanical substitution produces nonsense. How to handle these workflow-sense occurrences?

## Options

- semantic_rewrite_per_context
- strict_substitution
- case_by_case_with_review

## Final answer

semantic_rewrite_per_context: each occurrence reworded to convey actual meaning (workflow-sense -> 'full mission workflow' or 'all phases'; commit-class -> 'status commit'). occurrence_map.yaml flags each per category.

## Rationale

_(none)_

## Change log

- `2026-05-28T06:59:53.279630+00:00` — opened
- `2026-05-28T07:02:03.187036+00:00` — resolved (final_answer="semantic_rewrite_per_context: each occurrence reworded to convey actual meaning (workflow-sense -> 'full mission workflow' or 'all phases'; commit-class -> 'status commit'). occurrence_map.yaml flags each per category.")
