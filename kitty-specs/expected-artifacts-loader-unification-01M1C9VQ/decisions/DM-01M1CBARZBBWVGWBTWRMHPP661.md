# Decision Moment `01M1CBARZBBWVGWBTWRMHPP661`

- **Mission:** `expected-artifacts-loader-unification-01M1C9VQ`
- **Origin flow:** `specify`
- **Slot key:** `specify.unification.scope-depth`
- **Input key:** `unification_scope_depth`
- **Status:** `resolved`
- **Created:** `2026-08-31T16:44:37.739436+00:00`
- **Resolved:** `2026-08-31T16:44:39.035265+00:00`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

How far should #3770 unification reach, given C-001 (charter must not import specify_cli) and a 4th charter-tier raw-mapping loader?

## Options

- Scoped: brief 3 mirrors + follow-up
- Full: shared charter-side helper
- Relocate loader into charter

## Final answer

Relocate the canonical cached load_manifest wholesale into charter; deprecation shim re-export from specify_cli/dossier; re-point ALL consumers incl. charter-tier mission_type_profiles; retire from_yaml_file orphan; arch-gate bare model_validate; add an ADR for the charter relocation. Cleanest single-authority end-state (operator choice).

## Rationale

_(none)_

## Change log

- `2026-08-31T16:44:37.739436+00:00` — opened
- `2026-08-31T16:44:39.035265+00:00` — resolved (final_answer="Relocate the canonical cached load_manifest wholesale into charter; deprecation shim re-export from specify_cli/dossier; re-point ALL consumers incl. charter-tier mission_type_profiles; retire from_yaml_file orphan; arch-gate bare model_validate; add an ADR for the charter relocation. Cleanest single-authority end-state (operator choice).")
