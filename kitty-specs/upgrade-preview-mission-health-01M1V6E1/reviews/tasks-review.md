# Task Slicing Review

Audience: agentic-framework-core-team. Date: 2026-09-06.
This records a bounded ownership adjudication, not the completed post-tasks
squad, canonical analysis, implementation or mission acceptance.

## Corpus Ownership Adjudication

Actual finalize-tasks --validate-only rejected WP11's mixed corpus/test paths
with INVALID_WP_OWNED_FILES_KITTY_SPECS. The existing restriction is deliberate:
mission_parsing._is_confined_planning_wp permits kitty-specs ownership only for
planning_artifact with every owned path under kitty-specs or docs. Existing
mode-discrimination tests require rejection of the mixed code-change shape.

Independent Architect Alphonso review: APPROVE the following reslice. A
read-only probe using the actual metadata classifier and lane computation
confirmed confinement and an acyclic graph; this was not finalization success.

- WP11 owns only exact corpus/document changes and a JSON evidence receipt
  under docs/archive/program-evidence. It uses the canonical planning workspace.
- WP12 owns tests/upgrade/test_mission_corpus_recovery.py plus its two existing
  archive-policy tests. It reads, but does not author, WP11's receipt.
- WP11 retains the real pre-recovery CLI red, all31 historical blob/mode
  restorations, both byte-identical document moves, scoped snapshot replays,
  all eight verdicts, independent provenance/no-churn checks and full zero-
  blocker audit. It may execute verification without authoring code deliverables.
- WP12 retains all persistent original/corrupted counterfactual regression
  requirements. Testing only the already-recovered checkout is insufficient.
- No ownership omission, hidden code under docs, codebase-wide exemption,
  guard relaxation, new WP, dependency change or acceptance reduction.

Receipt location and responsibilities are normative in corpus-recovery.md.
Root planning work must be serialized with other root mutations, preserving
unexpected user changes and exact targeted staging. Independent data review is
not an assertion that the unmodified archive gate already passes; WP12 and the
parent's full final gates remain responsible for that separate obligation.

## Remaining Review

Run canonical preflight and finalization on the amended complete task set.
Then conduct the post-tasks squad and persist canonical cross-artifact analysis.
Neither has completed as of this record; do not infer their verdicts from the
bounded architecture approval above.
