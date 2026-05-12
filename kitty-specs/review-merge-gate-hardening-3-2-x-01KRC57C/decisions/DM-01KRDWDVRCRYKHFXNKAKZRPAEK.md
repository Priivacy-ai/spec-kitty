# Decision Moment `01KRDWDVRCRYKHFXNKAKZRPAEK`

- **Mission:** `review-merge-gate-hardening-3-2-x-01KRC57C`
- **Origin flow:** `plan`
- **Slot key:** `plan.cross-cutting.diagnostic-code-registry`
- **Input key:** `diagnostic_code_registry_form`
- **Status:** `resolved`
- **Created:** `2026-05-12T10:41:22.700842+00:00`
- **Resolved:** `2026-05-12T10:42:19.325627+00:00`
- **Other answer:** `false`

## Question

FR-009 + NFR-001 require JSON-stable diagnostic codes (MISSION_REVIEW_*, CHARTER_ENCODING_*) consumed by the #992 Phase 0 cross-surface harness. Where do these live as the single source of truth?

## Options

- python_enum_per_subsystem
- central_yaml_registry
- inline_string_constants
- Other

## Final answer

python_enum_per_subsystem — Each subsystem defines its own StrEnum for diagnostic codes: src/specify_cli/cli/commands/review/_diagnostics.py for MissionReviewDiagnostic; src/charter/_diagnostics.py for CharterEncodingDiagnostic. Type-safe, mypy-checkable, no central registry needed.

## Rationale

_(none)_

## Change log

- `2026-05-12T10:41:22.700842+00:00` — opened
- `2026-05-12T10:42:19.325627+00:00` — resolved (final_answer="python_enum_per_subsystem — Each subsystem defines its own StrEnum for diagnostic codes: src/specify_cli/cli/commands/review/_diagnostics.py for MissionReviewDiagnostic; src/charter/_diagnostics.py for CharterEncodingDiagnostic. Type-safe, mypy-checkable, no central registry needed.")
