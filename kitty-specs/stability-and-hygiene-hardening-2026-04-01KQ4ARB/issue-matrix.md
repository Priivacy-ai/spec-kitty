# Issue Traceability Matrix — Stability & Hygiene Hardening (April 2026)

**Mission**: `stability-and-hygiene-hardening-2026-04-01KQ4ARB`
**Mission ID**: `01KQ4ARB0P4SFB0KCDMVZ6BXC8`
**Generated**: 2026-04-26
**Source of issue list**: `/Users/robert/spec-kitty-dev/spec-kitty-20260426-091819-hxH6lN/start-here.md`
**FR**: FR-037
**WP08 deliverable**: T044

This matrix is the canonical record of "what GitHub issue maps to what work
package and how it was resolved" for this mission. The
`spec-kitty-mission-review` skill (T050) treats this file as a hard gate:
every row MUST have a non-empty `verdict` and `evidence_ref`. Verdict ∈
{`fixed`, `verified-already-fixed`, `deferred-with-followup`}.

Verdict semantics:

- `fixed` — bug present on `main` at mission start, fix landed in WPxx.
  `evidence_ref` is the WP commit SHA and a test name that exercises the
  bug surface.
- `verified-already-fixed` — bug was already resolved on `main` (typically by
  an earlier mission such as `shared-package-boundary-cutover-01KQ22DS`);
  this mission added or pointed at a regression test that would have failed
  pre-fix. `evidence_ref` is that test name.
- `deferred-with-followup` — fix is deliberately out of scope; the row names
  the precise narrower follow-up issue title that captures the remaining
  work.

## Matrix

| repo | issue | theme | verdict | wp_id | evidence_ref |
|------|-------|-------|---------|-------|--------------|
| Priivacy-ai/spec-kitty | #785 | Merge / worktree / lane safety | verified-already-fixed | WP01 | commit `0465c04b`; tests/merge/test_lane_planning_artifacts_merge.py |
| Priivacy-ai/spec-kitty | #416 | Merge / worktree / lane safety | verified-already-fixed | WP01 | commit `0465c04b`; tests/merge/test_resume_idempotent.py |
| Priivacy-ai/spec-kitty | #784 | Merge / worktree / lane safety | fixed | WP01 | commit `0465c04b`; tests/merge/test_post_merge_index_refresh.py |
| Priivacy-ai/spec-kitty | #772 | Merge / worktree / lane safety | verified-already-fixed | WP01 | commit `0465c04b`; tests/merge/test_untracked_worktrees_do_not_block.py |
| Priivacy-ai/spec-kitty | #675 | Merge / worktree / lane safety | verified-already-fixed | WP01 | commit `0465c04b`; tests/lanes/test_dependent_wp_lane_assignment.py |
| Priivacy-ai/spec-kitty | #715 | Merge / worktree / lane safety | fixed | WP01 | commit `0465c04b`; tests/saas/test_lane_specific_test_db.py |
| Priivacy-ai/spec-kitty | #770 | Merge / worktree / lane safety | verified-already-fixed | WP01 | commit `0465c04b`; tests/merge/test_resume_after_interrupt.py |
| Priivacy-ai/spec-kitty | #724 | Intake security / state hygiene | fixed | WP02 | commit `c7510bae`; tests/intake/test_provenance_escaping.py |
| Priivacy-ai/spec-kitty | #720 | Intake security / state hygiene | fixed | WP02 | commit `c7510bae`; tests/intake/test_traversal_blocked.py |
| Priivacy-ai/spec-kitty | #721 | Intake security / state hygiene | fixed | WP02 | commit `c7510bae`; tests/intake/test_symlink_escape_blocked.py |
| Priivacy-ai/spec-kitty | #722 | Intake security / state hygiene | fixed | WP02 | commit `c7510bae`; tests/intake/test_size_cap_pre_read.py |
| Priivacy-ai/spec-kitty | #723 | Intake security / state hygiene | fixed | WP02 | commit `c7510bae`; tests/intake/test_atomic_write.py |
| Priivacy-ai/spec-kitty | #727 | Intake security / state hygiene | fixed | WP02 | commit `c7510bae`; tests/intake/test_missing_vs_corrupt.py |
| Priivacy-ai/spec-kitty | #725 | Intake security / state hygiene | fixed | WP02 | commit `c7510bae`; tests/intake/test_root_consistency.py |
| Priivacy-ai/spec-kitty | #539 | Status / runtime / orchestration | fixed | WP03 | commit `6be29f6f`; tests/status/test_canonical_root_emit.py |
| Priivacy-ai/spec-kitty | #538 | Status / runtime / orchestration | fixed | WP03 | commit `6be29f6f`; tests/status/test_planned_to_in_progress_pre_alloc.py |
| Priivacy-ai/spec-kitty | #541 | Status / runtime / orchestration | verified-already-fixed | WP04 | commit `d09aab94`; tests/contract/test_next_no_implicit_success.py |
| Priivacy-ai/spec-kitty | #542 | Status / runtime / orchestration | verified-already-fixed | WP04 | commit `d09aab94`; tests/contract/test_next_no_unknown_state.py |
| Priivacy-ai/spec-kitty | #551 | Status / runtime / orchestration | verified-already-fixed | WP04 | commit `d09aab94`; tests/runtime/test_for_review_to_in_review.py |
| Priivacy-ai/spec-kitty | #622 | Status / runtime / orchestration | verified-already-fixed | WP04 | commit `d09aab94`; tests/contract/test_mark_status_input_shapes.py |
| Priivacy-ai/spec-kitty | #783 | Status / runtime / orchestration | verified-already-fixed | WP04 | commit `d09aab94`; tests/dashboard/test_progress_counters.py |
| Priivacy-ai/spec-kitty | #775 | Status / runtime / orchestration | fixed | WP04 | commit `d09aab94`; tests/missions/test_plan_mission_runtime_yaml.py |
| Priivacy-ai/spec-kitty | #540 | Status / runtime / orchestration | fixed | WP04 | commit `d09aab94`; tests/lanes/test_planning_artifact_workspace.py |
| Priivacy-ai/spec-kitty | #443 | Status / runtime / orchestration | fixed | WP03 | commit `6be29f6f`; tests/status/test_status_event_target_repo.py |
| Priivacy-ai/spec-kitty | #710 | Status / runtime / orchestration | fixed | WP03 | commit `6be29f6f`; tests/status/test_worktree_invocation_emits_to_main.py |
| Priivacy-ai/spec-kitty | #526 | Status / runtime / orchestration | fixed | WP03 | commit `6be29f6f`; tests/status/test_config_writes_target_canonical.py |
| Priivacy-ai/spec-kitty | #552 | Status / runtime / orchestration | fixed | WP03 | commit `6be29f6f`; tests/status/test_review_claim_transition.py |
| Priivacy-ai/spec-kitty | #343 | Status / runtime / orchestration | fixed | WP03 | commit `6be29f6f`; tests/status/test_in_progress_emit_pre_alloc.py |
| Priivacy-ai/spec-kitty | #335 | Status / runtime / orchestration | fixed | WP04 | commit `d09aab94`; tests/runtime/test_bare_next_no_implicit_advance.py |
| Priivacy-ai/spec-kitty | #336 | Status / runtime / orchestration | fixed | WP04 | commit `d09aab94`; tests/runtime/test_no_unknown_query_placeholder.py |
| Priivacy-ai/spec-kitty | #791 | Cross-repo package contracts | fixed | WP05 | commit `bdd14e7d`; tests/contract/test_events_envelope_matches_resolved_version.py |
| Priivacy-ai/spec-kitty | #792 | Cross-repo package contracts | fixed | WP05 | commit `bdd14e7d`; tests/contract/test_cross_repo_consumers.py |
| Priivacy-ai/spec-kitty | #419 | Cross-repo package contracts | fixed | WP05 | commit `bdd14e7d`; tests/architectural/test_events_tracker_public_imports.py |
| Priivacy-ai/spec-kitty | #420 | Cross-repo package contracts | fixed | WP05 | commit `bdd14e7d`; tests/architectural/test_pyproject_shape.py |
| Priivacy-ai/spec-kitty | #421 | Cross-repo package contracts | fixed | WP05 | commit `bdd14e7d`; tests/contract/test_cross_repo_consumers.py |
| Priivacy-ai/spec-kitty-events | #16 | Cross-repo package contracts | fixed | WP05 | commit `bdd14e7d`; tests/contract/test_event_envelope.py + downstream consumer test |
| Priivacy-ai/spec-kitty-events | #7 | Cross-repo package contracts | fixed | WP05 | commit `bdd14e7d`; tests/contract/spec_kitty_events_consumer/ |
| Priivacy-ai/spec-kitty-events | #8 | Cross-repo package contracts | fixed | WP05 | commit `bdd14e7d`; tests/contract/test_event_envelope.py |
| Priivacy-ai/spec-kitty-tracker | #12 | Cross-repo package contracts | fixed | WP05 | commit `bdd14e7d`; tests/contract/spec_kitty_tracker_consumer/ |
| Priivacy-ai/spec-kitty-tracker | #5 | Cross-repo package contracts | fixed | WP05 | commit `bdd14e7d`; tests/architectural/test_events_tracker_public_imports.py |
| Priivacy-ai/spec-kitty-tracker | #6 | Cross-repo package contracts | fixed | WP05 | commit `bdd14e7d`; tests/contract/test_cross_repo_consumers.py |
| Priivacy-ai/spec-kitty-runtime | #16 | Cross-repo package contracts | verified-already-fixed | WP05 | retired by `shared-package-boundary-cutover-01KQ22DS`; tests/architectural/test_no_runtime_pypi_dep.py |
| Priivacy-ai/spec-kitty-runtime | #7 | Cross-repo package contracts | verified-already-fixed | WP05 | retired by `shared-package-boundary-cutover-01KQ22DS`; tests/architectural/test_no_runtime_pypi_dep.py |
| Priivacy-ai/spec-kitty-runtime | #8 | Cross-repo package contracts | verified-already-fixed | WP05 | retired by `shared-package-boundary-cutover-01KQ22DS`; tests/architectural/test_shared_package_boundary.py |
| Priivacy-ai/spec-kitty-runtime | #11 | Cross-repo package contracts | verified-already-fixed | WP05 | retired by `shared-package-boundary-cutover-01KQ22DS`; tests/architectural/test_no_runtime_pypi_dep.py |
| Priivacy-ai/spec-kitty | #306 | Sync / tracker / SaaS / hosted flow | fixed | WP06 | commit `cd66f4f8`; tests/sync/test_offline_queue_overflow.py |
| Priivacy-ai/spec-kitty | #352 | Sync / tracker / SaaS / hosted flow | fixed | WP06 | commit `cd66f4f8`; tests/sync/test_replay_identity_collision.py |
| Priivacy-ai/spec-kitty | #717 | Sync / tracker / SaaS / hosted flow | fixed | WP06 | commit `cd66f4f8`; tests/auth/test_token_refresh_dedup.py |
| Priivacy-ai/spec-kitty | #564 | Sync / tracker / SaaS / hosted flow | fixed | WP06 | commit `cd66f4f8`; tests/architectural/test_auth_transport_singleton.py |
| Priivacy-ai/spec-kitty-tracker | #1 | Sync / tracker / SaaS / hosted flow | deferred-with-followup | WP06 | follow-up issue: "tracker/saas_client.py migration to AuthenticatedClient (130+ test mocks need re-targeting)" — captured in WP06 reviewer note |
| Priivacy-ai/spec-kitty | #773 | Repo context / governance / hygiene | fixed | WP07 | commit `67a9a14e`; tests/cli/test_uninitialized_repo_fails_loud.py |
| Priivacy-ai/spec-kitty | #765 | Repo context / governance / hygiene | fixed | WP07 | commit `67a9a14e`; tests/missions/test_pr_branch_strategy_gate.py |
| Priivacy-ai/spec-kitty | #787 | Repo context / governance / hygiene | fixed | WP07 | commit `67a9a14e`; tests/contract/test_charter_compact_includes_section_anchors.py |
| Priivacy-ai/spec-kitty | #790 | Repo context / governance / hygiene | fixed | WP07 | commit `67a9a14e`; tests/cli/test_legacy_feature_alias_hidden.py |
| Priivacy-ai/spec-kitty | #801 | Repo context / governance / hygiene | verified-already-fixed | WP07 | commit `67a9a14e` (T043 verification); tests/missions/test_local_custom_mission_loader_post_merge.py |

## Summary

| Verdict | Count |
|---------|-------|
| `fixed` | 39 |
| `verified-already-fixed` | 15 |
| `deferred-with-followup` | 1 |
| **Total rows** | **55** |

The single `deferred-with-followup` row is `Priivacy-ai/spec-kitty-tracker#1`,
where WP06 internalized the auth transport but `tracker/saas_client.py`
still constructs its own `httpx.Client` because re-targeting 130+ test mocks
to the `AuthenticatedClient` shim is out of WP06 scope. The follow-up is
captured verbatim in the WP06 reviewer note in `kitty-specs/<this
mission>/tasks/WP06-…/review-cycle-*.md`.

## Cross-references

- Spec: `kitty-specs/stability-and-hygiene-hardening-2026-04-01KQ4ARB/spec.md`
  FR-037 (this matrix is its primary deliverable).
- Research: `research.md` D1 (decision to use a single Markdown matrix
  alongside `spec.md`).
- Mission-review skill: `src/doctrine/skills/spec-kitty-mission-review/SKILL.md`
  reads this file and rejects mission acceptance if any row has an empty
  verdict or verdict `unknown`.
- ADR: `architecture/2.x/adr/2026-04-26-3-e2e-hard-gate.md` — the
  cross-repo e2e gate rides on top of this matrix as a paired
  mission-review check.
