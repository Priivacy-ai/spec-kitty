# Decision Moment `01KWRWB0PPF5TQPNYF5D07XY3W`

- **Mission:** `ci-health-charter-path-and-arch-shard-01KWRTB2`
- **Origin flow:** `plan`
- **Slot key:** `plan.architecture.arch-shard-split`
- **Input key:** `arch_shard_split`
- **Status:** `resolved`
- **Created:** `2026-07-05T10:14:15.510814+00:00`
- **Resolved:** `2026-07-05T10:18:43.356496+00:00`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

How should arch-adversarial be split: N=2 shards (dominant tests/architectural directory bisected in half + the three small dirs bundled with one half) or N=3 shards (tests/architectural bisected + a dedicated misc shard for adversarial/architecture/lint)?

## Options

- N=2 (architectural-a / architectural-b+misc)
- N=3 (architectural-a / architectural-b / misc)
- Other

## Final answer

N=3 shards minimum, functional/module-level slicing (whole test files kept intact, not split), routed via dedicated pytest markers (not raw --ignore path lists) applied consistently across the arch-adversarial matrix.

## Rationale

_(none)_

## Change log

- `2026-07-05T10:14:15.510814+00:00` — opened
- `2026-07-05T10:18:43.356496+00:00` — resolved (final_answer="N=3 shards minimum, functional/module-level slicing (whole test files kept intact, not split), routed via dedicated pytest markers (not raw --ignore path lists) applied consistently across the arch-adversarial matrix.")
