# Gold Annotation Rubric

## Blinding and Roles

- Reviewer A: `/root/bundle_gold_reviewer_a` (`reviewer-renata` profile).
- Reviewer B: `/root/bundle_gold_reviewer_b` (`debugger-debbie` profile).
- Adjudicator: `/root` after both independent reviews are final.
- Reviewers may inspect only baseline `cf0f7e3a7`, the query registry, and gold rows. Candidate outputs are prohibited and do not yet exist.

## Per-Atom Decision

Mark `PASS` only when all conditions hold:

1. `source_blob` equals `git rev-parse cf0f7e3a7:<source_path>`.
2. Zero-based half-open raw-byte offsets resolve and hash to `span_sha256`.
3. The cited bytes directly support the subject-predicate-object fact at P0.
4. Subject identity is namespaced enough for its fixture.
5. Criticality follows the frozen rule: requirements, dependencies, authority, approval, and provenance are critical; inferred themes are not.
6. The atom answers its query without adding an unregistered inference.

Otherwise mark `FAIL` and name the smallest correction. Reviewers must evaluate every row. Silence is not approval.

## Completeness and Disagreement

After atom review, each reviewer separately checks whether the expected set is complete and whether forbidden atoms capture the load-bearing false-positive case. The adjudicator may only choose one reviewer's recorded interpretation or remove an invalid atom/query. Adding a new favorable atom after review requires a new preregistration version. Every disagreement and resolution is published before candidate execution.
