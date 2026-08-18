# Adversarial review ledger

This mission used the `adversarial-squad` protocol at each evidence-bearing
point-cut. Reviewers were read-only and profile-loaded. Their findings changed
the research design and claims; they did not substitute judgment for missing
evidence.

| Date | Point-cut | Reviewer task / profile | Reviewed revision | Sharp question | Disposition |
|---|---|---|---|---|---|
| 2026-08-18 | Post-scoping | `/root/postspec_arch` / `architect-alphonso` | `1e708653a` | Does scope preserve every authority posture and enumerate logical mission/consumer boundaries? | REVISE → APPROVE after authority preselection was removed and the option lattice/read model/consumer census were added. |
| 2026-08-18 | Post-methodology | `/root/postplan_arch` / `architect-alphonso` | `e6d13408b` | Are authority, representation, persistence, refresh, aggregation, and egress axes independently instantiated with fair gates? | REVISE → APPROVE after the lattice and structural/semantic gate boundaries were repaired. |
| 2026-08-18 | Gold set A | `/root/bundle_gold_reviewer_a` / `reviewer-renata` | sealed gold SHA in attestation | Do atom boundaries and truth labels exactly follow the rubric? | Findings adjudicated; APPROVE. |
| 2026-08-18 | Gold set B | `/root/bundle_gold_reviewer_b` / `debugger-debbie` | sealed gold SHA in attestation | Can an independent falsification lens reproduce or refute every atom? | Findings adjudicated; APPROVE. |
| 2026-08-18 | Preregistration | `/root/bundle_repro_redteam` / `debugger-debbie` | `e6fcdb4ba` | Can selection, mutation, genericity, privacy, and raw-output checks false-PASS or leak post-hoc flexibility? | BLOCK → APPROVE after selector/oracle/isolation/privacy/coverage fixes and resealing. |
| 2026-08-18 | Post-gathering | `/root/postgather_authority`, `/root/postgather_claims`, `/root/postgather_empirical` / `architect-alphonso`, `reviewer-renata`, `debugger-debbie` | `ebbd860b6` plus repair commits | Do raw evidence, provenance, authority, privacy, and utility labels support any adoption claim? | REVISE → APPROVE after `NOT_EVIDENCE`/`UNKNOWN` repairs, manifests, provenance, source closure, and sanitizer restoration. |
| 2026-08-18 | Post-synthesis | same 3 tasks / same 3 profiles | `d2b3a6f33` plus repair commits | Does every disposition obey frozen gates and the bounded consumer census? | REVISE → APPROVE after `UNKNOWN` → defer and census corrections. |
| 2026-08-18 | Pre-publication content | same 3 tasks / same 3 profiles | report blob `a6089b352e6aff63373b1dda76b7172294a3086d` | Does reader-facing language preserve evidence strength, risks, and option symmetry? | REVISE → APPROVE after focused citations, risk table, and EV-029 rule mapping. |
| 2026-08-18 | Publication integrity, round 1 | same 3 tasks / same 3 profiles | working tree after `2864accfb` | Can the publication seal drift, false-PASS, or approve a stale report? | REVISE: align canonical artifact paths, verify transitive raw files, bind gate tokens, and make review history auditable. |
| 2026-08-18 | Publication integrity, round 2 | `/root/postgather_authority`, `/root/postgather_claims`, `/root/postgather_empirical` / `architect-alphonso`, `reviewer-renata`, `debugger-debbie` | d1e13c6a4ae1ecc95cbfd450db541abf93b785aa | Do the repaired manifest, verifier, ledger, pointer, report blob, and gate binding form a closed integrity proof? | APPROVE |

## Publication-integrity round 1 findings

| Finding | Severity | Lens | Disposition |
|---|---|---|---|
| PIR-01: manifest did not traverse execution/preregistration records or directly seal the verifier and review ledger | HIGH | All 3 | Repaired: typed required inventory, direct hashes, 183 nested result/procedure checks, 32-file seal-commit comparison, and post-seal invocation. |
| PIR-02: approval event could match a stale type/name pair | HIGH | All 3 | Repaired: latest-event matching binds manifest/report/ledger hashes, report blob/source commit, 3 reviewers, verdict, timestamp, and an exact reviewed Git revision. |
| PIR-03: canonical contradiction/review paths disagreed with the frozen artifact map | HIGH | Authority + claims | Repaired: artifacts moved to the plan-declared paths and publication-sealed. |
| PIR-04: scorecard verifier allowed invalid gate/disposition mutations | HIGH | Empirical | Repaired: disposition whitelist and `FAIL` → reject / otherwise `UNKNOWN` → defer precedence, with explicit C0/C1 controls. |
| PIR-05: evidence validation omitted raw hashes, source IDs, schemas, range interiors, pointer, and ledger | MEDIUM | Claims + empirical | Repaired: schemas/uniqueness/source resolution/raw hashes/range expansion and every publication surface are checked. |
| PIR-06: manifest topology and exclusions were implicit | MEDIUM | Authority | Repaired: mission/revision/seal consistency, confined unique paths, required artifacts, empirical/redaction records, trackedness, clean-tree enforcement, and named mutable-process exclusions. |

## Lens boundaries

- `architect-alphonso`: ownership, canonicality, logical-mission reads,
  migration, lifecycle, and single-source publication.
- `reviewer-renata`: claim/evidence fit, option symmetry, residual uncertainty,
  and cross-artifact consistency.
- `debugger-debbie`: selectors, fixtures, hashes, raw manifests, false-PASS
  paths, reproducibility, and sanitization.

Gold-review hashes and disagreements are preserved in
`research/fixtures/gold/`. Methodology execution chronology is preserved in
`research/execution-ledger.jsonl`. Final approval means internal consistency
and bounded evidence; it does not convert deferred options or unknown demand
into an adoption recommendation.
