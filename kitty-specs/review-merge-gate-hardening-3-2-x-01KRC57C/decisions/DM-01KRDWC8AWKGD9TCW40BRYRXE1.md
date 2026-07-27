# Decision Moment `01KRDWC8AWKGD9TCW40BRYRXE1`

- **Mission:** `review-merge-gate-hardening-3-2-x-01KRC57C`
- **Origin flow:** `plan`
- **Slot key:** `plan.wp06.charset-normalizer-dep`
- **Input key:** `charset_normalizer_dep_promotion`
- **Status:** `resolved`
- **Created:** `2026-05-12T10:40:30.044539+00:00`
- **Resolved:** `2026-05-12T10:41:10.304695+00:00`
- **Other answer:** `false`

## Question

charset-normalizer is already a transitive dep via requests (locked at 3.4.7). MIT, no sub-deps, no known CVEs, pure-Python with optional mypyc fast-path. Approach for WP06?

## Options

- promote_to_direct_dep
- stick_with_transitive
- hand_roll_detector
- Other

## Final answer

promote_to_direct_dep — Add charset-normalizer to pyproject.toml [project.dependencies] with pin '>=3.4,<4'. Already a transitive dep at 3.4.7 via requests; zero net new install surface. Direct-dep declaration makes the version contract intentional and immune to upstream-requests detector drift.

## Rationale

_(none)_

## Change log

- `2026-05-12T10:40:30.044539+00:00` — opened
- `2026-05-12T10:41:10.304695+00:00` — resolved (final_answer="promote_to_direct_dep — Add charset-normalizer to pyproject.toml [project.dependencies] with pin '>=3.4,<4'. Already a transitive dep at 3.4.7 via requests; zero net new install surface. Direct-dep declaration makes the version contract intentional and immune to upstream-requests detector drift.")
