# Decision Moment `01KQ7ZSQKT9DVH7B4GGXWS8DTW`

- **Mission:** `release-3-2-0a5-tranche-1-01KQ7YXH`
- **Origin flow:** `plan`
- **Slot key:** `plan.release.python-version-shape`
- **Input key:** `python_version_shape`
- **Status:** `resolved`
- **Created:** `2026-04-27T17:29:08.987421+00:00`
- **Resolved:** `2026-04-27T17:31:47.178729+00:00`
- **Other answer:** `false`

## Question

FR-001 .python-version loosening shape: which form should the new .python-version take so it stops blocking local agents on 3.14 while keeping CI predictable?

## Options

- A: remove .python-version entirely (let uv resolve from pyproject requires-python >=3.11)
- B: loosen to a floor like 3.11 or 3.12
- C: keep a single pin but bump it to 3.14 to match active dev
- D: other (you specify)

## Final answer

B: floor at 3.11. Replace .python-version contents with '3.11' so it aligns with pyproject.toml's requires-python = '>=3.11' and stops imposing a higher implicit contributor floor than packaging does. Avoids broken patch-level pin behavior on 3.13/3.14 dev environments while leaving the contributor minimum unchanged.

## Rationale

_(none)_

## Change log

- `2026-04-27T17:29:08.987421+00:00` — opened
- `2026-04-27T17:31:47.178729+00:00` — resolved (final_answer="B: floor at 3.11. Replace .python-version contents with '3.11' so it aligns with pyproject.toml's requires-python = '>=3.11' and stops imposing a higher implicit contributor floor than packaging does. Avoids broken patch-level pin behavior on 3.13/3.14 dev environments while leaving the contributor minimum unchanged.")
