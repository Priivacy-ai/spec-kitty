# Decision Moment `01KW1KDHVGWZ0QERDMV1CRJ15S`

- **Mission:** `spec-kitty-home-isolation-01KW1JXX`
- **Origin flow:** `plan`
- **Slot key:** `plan.windows-compat.normalize-base`
- **Input key:** `windows_base_normalization`
- **Status:** `resolved`
- **Created:** `2026-06-26T09:15:49.488836+00:00`
- **Resolved:** `2026-06-26T11:01:18.332584+00:00`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

On unset Windows, several surfaces (sync config, queue, clock, tracker DB) currently leak to ~/.spec-kitty instead of the platformdirs app-data base used by daemon/auth/tracker-creds. Should the fix normalize ALL Windows surfaces onto the single platformdirs base, or strictly preserve each surface's exact current Windows path and only add the SPEC_KITTY_HOME override?

## Options

- Normalize all Windows surfaces onto platformdirs base
- Strictly preserve current per-surface Windows paths
- Other

## Final answer

Normalize all Windows surfaces onto the single platformdirs app-data base via get_runtime_root().base. Leaking surfaces (sync config, queue, clock, tracker DB) move from ~/.spec-kitty to platformdirs base on unset Windows; documented as intended normalization in CHANGELOG. No auto-migration (C-001). POSIX unset behavior stays byte-identical.

## Rationale

_(none)_

## Change log

- `2026-06-26T09:15:49.488836+00:00` — opened
- `2026-06-26T11:01:18.332584+00:00` — resolved (final_answer="Normalize all Windows surfaces onto the single platformdirs app-data base via get_runtime_root().base. Leaking surfaces (sync config, queue, clock, tracker DB) move from ~/.spec-kitty to platformdirs base on unset Windows; documented as intended normalization in CHANGELOG. No auto-migration (C-001). POSIX unset behavior stays byte-identical.")
