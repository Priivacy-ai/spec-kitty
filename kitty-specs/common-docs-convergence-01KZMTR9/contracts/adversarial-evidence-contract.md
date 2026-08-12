# Contract — Adversarial Evidence

Every adversarial-squad pass on this mission records, for each contested finding, a disposition of
exactly one of: `accepted`, `changed`, or `deferred_with_rationale`. No contested finding may be
silently dropped.

- **post-spec** squad → `reviews/post-spec-squad.md` (done; dispositions folded into revised spec).
- **post-plan** squad → `reviews/post-plan-squad.md` (dispositions folded into plan/artifacts).
- **post-tasks** squad (anti-laziness) → `reviews/post-tasks-squad.md`.

Each review lists: finding, lens, severity, disposition, and the resulting spec/plan/tasks change
(or the rationale for deferral). This contract satisfies the plan step's mandatory adversarial-evidence
requirement.
