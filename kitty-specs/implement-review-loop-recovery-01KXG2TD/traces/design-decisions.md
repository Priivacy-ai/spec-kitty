# Design Decisions

> Capture the rationale that would otherwise evaporate.

## Entries

- 2026-07-14 — Decision: keep `pre_review_gate.py` as the sole gate-verdict authority and observe its call at `_mt_run_pre_review_gate`. Alternatives: stream pytest output, shorten timeout, or add a universal CLI progress layer. Rationale: the selected seam satisfies local liveness and JSON requirements without policy duplication or scope expansion.
- 2026-07-14 — Decision: use injected timing/wait/progress collaborators for cadence tests. Alternatives: real 65-second sleeps. Rationale: deterministic tests prove the threshold without slow or flaky wall-clock dependence.
- 2026-07-14 — Decision: treat catchable cancellation only before transition mutation and use the existing event log for post-SIGKILL truth. Alternatives: add rollback persistence. Rationale: no transition is authorized before the gate returns, and uncatchable termination cannot guarantee cleanup.
- 2026-07-14 — Decision: the canonical gate runner owns polling, its single timeout, typed termination, child cleanup, and reap; the CLI owns only presentation and advance/refuse policy. Alternatives: put the blocking gate in a worker thread. Rationale: a CLI observer cannot safely terminate the child hidden inside `subprocess.run`.
- 2026-07-14 — Decision: move deliverable auto-commit after the gate and include dirty deliverables in prospective scope. Alternatives: accept pre-gate commits or revert them after interruption. Rationale: the specification requires zero placement commits and destructive rollback would risk operator work.
- 2026-07-14 — Decision: bound checkout cleanliness to Spec Kitty-owned effects and preserve/surface test-owned writes. Alternatives: promise absolute cleanliness or destructively restore the checkout. Rationale: invoked tests are arbitrary code, and transition recovery must never erase operator work.
- 2026-07-14 — Decision: retain one WP with review checkpoints after RED proof, runner completion, and CLI integration. Alternatives: split runner and CLI into sequential WPs. Rationale: the exact-entry RED test needs both seams to become green, while a split would create an unapprovable red-only WP or overlapping ownership.
- 2026-07-14 — Decision: explicit sync-disable controls remain truthful pre-I/O skips rather than verdict-equivalent real gate runs. Alternatives: compare skip with enabled success/failure outcomes. Rationale: delivered behavior intentionally prevents workspace and subprocess access.
