# Decision Moment `01KZ2S8HWCRJ5X84SAFJQYCZRZ`

- **Mission:** `review-verdict-write-integrity-01KZ1CGF`
- **Origin flow:** `plan`
- **Slot key:** `plan.post-plan-squad.guard-relaxation-disposition`
- **Input key:** `guard_relaxation_disposition`
- **Status:** `resolved`
- **Created:** `2026-08-03T03:05:13.250620+00:00`
- **Resolved:** `2026-08-03T03:07:41.900000+00:00`
- **Opened by:** `landing-fold`
- **Other answer:** `false`

## Question

FR-001's implementation deleted `_guard_rejected_verdict`'s plain-refuse arm in `src/specify_cli/cli/commands/agent/tasks_transition_core.py` — a rejected verdict with no `--skip-review-artifact-check` no longer fails closed; it now falls through to the ordinary approve path. This behaviour change was justified only inside two Python docstrings (the module header's `EXCEPTION` note and `_guard_rejected_verdict`'s own docstring), with no plan.md or decision-log record. A PR-landing adversarial review squad adjudicated the removal: is it defensible as shipped, and if so, what governs the residual risk it introduces?

## Options

- Revert the removal — restore the plain-refuse arm so a rejected verdict always requires --skip-review-artifact-check --note <reason>
- Keep the removal, ratify it as a decision record naming the surviving controls and residual risk
- Other

## Final answer

Keep the removal. The deleted arm was a consistency guard, not an authorization control: it was already bypassable by the same actor via --skip-review-artifact-check --note "<any string>" (any non-empty string satisfies the note check), so it never actually prevented a determined approve-over-rejection — it only added friction to the ordinary reject-fix-approve cycle now that FR-001's durable writer (create_rejected_review_cycle, generalized to both verdicts) persists and commits a real verdict: approved artifact. The real backstops are unchanged by this diff and still fail closed: rejected_review_artifact_for_terminal_lane and find_rejected_review_artifact_conflicts in src/specify_cli/post_merge/review_artifact_consistency.py (post-merge consistency sweep), and _guard_self_review in tasks_transition_core.py (unchanged, still refuses same-actor review).

## Rationale

What was removed: the arm of _guard_rejected_verdict that refused move-task --to approved/--to done outright whenever the WP's latest review verdict was rejected and --skip-review-artifact-check was not supplied. What remains in that guard: refusing an unparseable verdict (always), and refusing --skip-review-artifact-check supplied without --note (the override still requires durable justification when a caller invokes it explicitly).

Why consistency-not-authorization: before FR-001, refusing here was the only mechanism that stopped a rejected verdict from being silently approved over — nothing could yet record a genuine approval artifact, so blocking was the safest available failure mode. But the same actor could always route around the block with --skip-review-artifact-check --note "<any string>", and the note content was never validated beyond non-emptiness. A guard that a caller can satisfy by supplying an arbitrary string is enforcing a procedural step (acknowledge you're overriding), not authorizing who may approve — so removing it once a real writer exists does not remove an authorization boundary, only a now-redundant confirmation step.

Surviving controls (unchanged by this diff, still fail closed): rejected_review_artifact_for_terminal_lane / find_rejected_review_artifact_conflicts (src/specify_cli/post_merge/review_artifact_consistency.py) — the post-merge consistency sweep that actually blocks a stale-rejected WP from reaching a terminal lane undetected; and _guard_self_review (tasks_transition_core.py) — unchanged, still refuses an actor approving their own submitted work.

Residual risk: with the plain-refuse arm gone, the ordinary approve-over-rejection path requires no --note at all, so its review_result.reference degrades to the default approval:{wp_id} instead of carrying an operator-supplied reason. This is a smaller loss than it looks: the durable writer still persists a real verdict: approved artifact with a genuine reviewer identity (this mission's core fix), so the event is recorded and auditable — it just carries a generic reference string rather than a human-authored one on the ordinary path. Callers who want a durable, human-readable reason must still use --skip-review-artifact-check --note <reason>, which remains available and unchanged.

## Change log

- `2026-08-03T03:05:13.250620+00:00` — opened
- `2026-08-03T03:07:41.900000+00:00` — resolved (final_answer="Keep the removal. The deleted arm was a consistency guard, not an authorization control: it was already bypassable by the same actor via --skip-review-artifact-check --note "<any string>" (any non-empty string satisfies the note check), so it never actually prevented a determined approve-over-rejection — it only added friction to the ordinary reject-fix-approve cycle now that FR-001's durable writer (create_rejected_review_cycle, generalized to both verdicts) persists and commits a real verdict: approved artifact. The real backstops are unchanged by this diff and still fail closed: rejected_review_artifact_for_terminal_lane and find_rejected_review_artifact_conflicts in src/specify_cli/post_merge/review_artifact_consistency.py (post-merge consistency sweep), and _guard_self_review in tasks_transition_core.py (unchanged, still refuses same-actor review).")
