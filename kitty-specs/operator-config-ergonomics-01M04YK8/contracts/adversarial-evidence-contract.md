# Contract: Adversarial Evidence

Every contested finding from an adversarial-squad pass carries a recorded disposition — `accepted`, `changed`, or `deferred_with_rationale`. No contested finding may be silently dropped.

- **Post-spec squad** (reviewer-renata / architect-alphonso / planner-priti): dispositions recorded in [../research.md](../research.md) §Adversarial Evidence. All HIGH/MEDIUM findings `changed`; two `deferred_with_rationale` (extracted-pack layout → #3022; Windows-CI matrix → out of scope, covered by parametrized unit tests).
- **Post-plan squad**: dispositions to be appended to research.md before `/spec-kitty.tasks`.
- **No new dependency** is introduced (hand-rolled parser), so the supply-chain adversarial pass reduces to confirming the null-change + the D6 pin-exact-rc mitigation.
