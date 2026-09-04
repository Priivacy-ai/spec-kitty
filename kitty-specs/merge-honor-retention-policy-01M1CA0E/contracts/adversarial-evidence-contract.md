# Contract: Adversarial Evidence (planning point-cut)

Every security- or data-loss-impacting decision made during planning must survive
an adversarial-squad challenge, and each contested finding's disposition must be
recorded — `accepted`, `changed`, or `deferred_with_rationale`. No contested
finding may be silently dropped.

- **Squad run**: post-spec point-cut, two profile-loaded lenses — data-loss
  (reviewer-renata) and canonical-authority/architecture (paula-patterns).
- **Dispositions**: recorded in `research.md` → "Adversarial Evidence" table.
- **Result**: two BLOCKER-class findings (coupled coord teardown, abort path) and
  one BLOCKER-class partition finding were `changed` (folded into spec D-4/D-5,
  FR-011/012, NFR-001..003); minors `accepted`; the config.yaml tier
  `deferred_with_rationale` (separate mission). Zero dropped.
- **Pre-merge**: a second adversarial pass (reviewer-renata + a merge/git lens)
  runs against the aggregate diff before the draft PR is un-drafted (charter
  close-out sequence).
