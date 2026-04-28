# Decision Moment `01KQ84P1AJ8H3FPJN9J5C12CBY`

- **Mission:** `release-3-2-0a5-tranche-1-01KQ7YXH`
- **Origin flow:** `plan`
- **Slot key:** `plan.init.non-git-semantics`
- **Input key:** `init_non_git_semantics`
- **Status:** `resolved`
- **Created:** `2026-04-27T18:54:30.739325+00:00`
- **Resolved:** `2026-04-27T19:07:16.637020+00:00`
- **Other answer:** `false`

## Question

FR-005 init non-git semantics: when spec-kitty init runs in a non-git directory, should it (A) fail fast with no scaffold, or (B) warn loudly and complete the scaffold? The spec wording 'MUST NOT silently corrupt or partially populate' + 'before retrying' is ambiguous; the current contract chose (B), the reviewer reads spec as (A).

## Options

- A: fail fast with NO scaffold; user must run git init then retry
- B: warn loudly and complete scaffold; user can run git init later before agent commands
- C: other (you specify)

## Final answer

B: warn loudly and complete scaffold. spec-kitty init may scaffold a non-git target successfully (exit 0, full scaffold written, no auto-git-init), but it must loudly tell the user to run 'git init' before using agent/workflow commands. The canonical invariant: 'non-git init is allowed; silent non-git init is not.' Remove 'before retrying' language from FR-005 and from the related exception scenario because that implies fail-fast semantics, which is rejected.

## Rationale

_(none)_

## Change log

- `2026-04-27T18:54:30.739325+00:00` — opened
- `2026-04-27T19:07:16.637020+00:00` — resolved (final_answer="B: warn loudly and complete scaffold. spec-kitty init may scaffold a non-git target successfully (exit 0, full scaffold written, no auto-git-init), but it must loudly tell the user to run 'git init' before using agent/workflow commands. The canonical invariant: 'non-git init is allowed; silent non-git init is not.' Remove 'before retrying' language from FR-005 and from the related exception scenario because that implies fail-fast semantics, which is rejected.")
