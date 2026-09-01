# Contract — Adversarial Evidence Disposition

Every contested finding from an adversarial pass (here: the post-spec squad) MUST carry an
explicit disposition; none may be silently dropped.

## Disposition vocabulary

- **accepted** — the finding stands; captured as a constraint/note without a code change now.
- **changed** — the artifact was revised to resolve the finding (spec/plan edit).
- **deferred_with_rationale** — not acted on in this mission; the reason is recorded.

## Record

The disposition table lives in [../research.md](../research.md) ("Adversarial evidence
dispositions"), keyed by finding id (F1…F7 + lower-severity items), with the lens(es) that
raised it. The full evidence with file:line anchors is in
[../research/post-spec-squad-findings.md](../research/post-spec-squad-findings.md).

All squad findings are dispositioned there. No contested finding was silently dropped.
