# WP04 Review Feedback — Cycle 10

## Verdict

Rejected by the independent correction reviewer. The typed
`ownership_refusal` envelope is otherwise truthful, but the implementation
also emits it when `auto_commit` is false.

## Required correction

Limit the new typed refusal envelope to automatic verdict saves. Preserve the
existing local-only (`--no-auto-commit`) ownership-refusal output unchanged.
Add a negative compatibility test proving local-only requests do not receive
the automatic durability diagnostic.

Do not alter the ownership policy, exit code, queue scope, or retry behavior.

## Evidence already accepted

The live automatic-mode test proves exit 1, exact causal fields, no status
event, no review-cycle artifact, and unchanged Git HEAD. The focused suite
passed 90 tests; Ruff and strict mypy passed.
