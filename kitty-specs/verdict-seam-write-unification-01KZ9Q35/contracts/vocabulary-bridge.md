# Contract — Vocabulary Bridge (FR-005)

**Owner**: one canonical surface beside `status/models.py` (e.g. `verdict_vocab.py`). Single source.

## Mapping (total, both directions)

Artifact vocabulary → event vocabulary:

| Artifact verdict | Event verdict |
|---|---|
| `approved` | `approved` |
| `rejected` | `changes_requested` |
| `arbiter_override` | `approved` *(override is an approval outcome; distinguishability lives in the ReviewOverride record, not the verdict)* |
| `approved_after_orchestrator_fix` | `approved` |

Event vocabulary → artifact/render (for prose display): `approved → approved`,
`changes_requested → rejected`.

## Guarantees

- **G1**: the mapping is **total** over all four inbound artifact values — no inbound value falls
  through to "damaged". *(FR-005; edge case)*
- **G2 (no drift surface)**: no module other than this canonical surface spells the
  `rejected`↔`changes_requested` equivalence inline. Enforced by an architectural guard test
  (grep-guard on co-occurring literals outside the owner module). *(paula finding — today inline in 9 modules)*

## Verified by

An arch-test forbidding inline equivalence + an end-to-end test driving an `arbiter_override` record
through to a resolved verdict.
