# Decision Moment `01KTRFSF2S8CAPX6YD6QYF3MM6`

- **Mission:** `01KTRC04`
- **Origin flow:** `plan`
- **Slot key:** `plan.architecture.guard-home`
- **Input key:** `guard_home`
- **Status:** `resolved`
- **Created:** `2026-06-10T10:03:33.849276+00:00`
- **Resolved:** `2026-06-10T10:08:38.812724+00:00`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

Which bounded-context home for the consolidated commit-guard entry point?

## Options

- shared-kernel
- execution-domain
- keep-in-git-module

## Final answer

Shared Kernel policy module (operator choice after trade-off review): safe_commit in git/commit_helpers.py remains the single entry point (mechanism, no caller import churn); the protection POLICY is extracted to a small owned SK module (e.g. core/commit_guard.py) consuming CommitTarget + protection state + caller capability — mechanism/policy separated, independently tested, doc-17 ownership settled.

## Rationale

_(none)_

## Change log

- `2026-06-10T10:03:33.849276+00:00` — opened
- `2026-06-10T10:08:38.812724+00:00` — resolved (final_answer="Shared Kernel policy module (operator choice after trade-off review): safe_commit in git/commit_helpers.py remains the single entry point (mechanism, no caller import churn); the protection POLICY is extracted to a small owned SK module (e.g. core/commit_guard.py) consuming CommitTarget + protection state + caller capability — mechanism/policy separated, independently tested, doc-17 ownership settled.")
