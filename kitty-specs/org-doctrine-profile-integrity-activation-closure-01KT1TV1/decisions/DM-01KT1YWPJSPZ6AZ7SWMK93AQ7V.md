# Decision Moment `01KT1YWPJSPZ6AZ7SWMK93AQ7V`

- **Mission:** `org-doctrine-profile-integrity-activation-closure-01KT1TV1`
- **Origin flow:** `plan`
- **Slot key:** `plan.bulk-edit.change-mode`
- **Input key:** `bulk_edit_change_mode`
- **Status:** `resolved`
- **Created:** `2026-06-01T16:04:56.537974+00:00`
- **Resolved:** `2026-06-01T16:21:36.289814+00:00`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

DIRECTIVE_035: the hard-cutover retirement of enhances/overrides/specializes_from fields removes the same identifiers across many YAML artifacts, reader code, tests, and fixtures. Mark the mission change_mode: bulk_edit and produce occurrence_map.yaml (8-category classification, enforced at implement)?

## Options

- Yes — mark bulk_edit and generate occurrence_map.yaml
- No — treat as ordinary multi-file change, no occurrence map
- Only classify the field-retirement WPs, not the whole mission

## Final answer

Yes — mark change_mode: bulk_edit and generate occurrence_map.yaml. The field-retirement is the highest-risk slice; 8-category classification forces complete cutover (no missed reader/fixture) and the implement gate enforces it, consistent with the hard-cutover decision. Map scopes the field-retirement surface; the rest of the mission proceeds normally.

## Rationale

_(none)_

## Change log

- `2026-06-01T16:04:56.537974+00:00` — opened
- `2026-06-01T16:21:36.289814+00:00` — resolved (final_answer="Yes — mark change_mode: bulk_edit and generate occurrence_map.yaml. The field-retirement is the highest-risk slice; 8-category classification forces complete cutover (no missed reader/fixture) and the implement gate enforces it, consistent with the hard-cutover decision. Map scopes the field-retirement surface; the rest of the mission proceeds normally.")
