# Decision Moment `01KSPP3W3VW8GB4WCXFF7J7X1Z`

- **Mission:** `rename-ceremony-to-status-commit-01KSPN6C`
- **Origin flow:** `plan`
- **Slot key:** `plan.regression.grep-guard`
- **Input key:** `regression_grep_guard`
- **Status:** `resolved`
- **Created:** `2026-05-28T06:59:55.643623+00:00`
- **Resolved:** `2026-05-28T07:02:04.891134+00:00`
- **Other answer:** `false`

## Question

Should we add a regression test (pytest) that runs grep -rn 'ceremony|status-writing' against src/ tests/ docs/ and fails if either reappears, or rely on glossary + occurrence_map + reviewer attention?

## Options

- add_pytest_grep_guard
- glossary_only
- add_pre_commit_hook

## Final answer

add_pytest_grep_guard: new architectural test that greps src/ tests/ docs/ for 'ceremony' and 'status-writing', fails CI if either reappears. Excludes kitty-specs/ historical artifacts.

## Rationale

_(none)_

## Change log

- `2026-05-28T06:59:55.643623+00:00` — opened
- `2026-05-28T07:02:04.891134+00:00` — resolved (final_answer="add_pytest_grep_guard: new architectural test that greps src/ tests/ docs/ for 'ceremony' and 'status-writing', fails CI if either reappears. Excludes kitty-specs/ historical artifacts.")
