---
work_package_id: WP05
title: Verification and Closeout
dependencies:
- WP01
- WP02
- WP03
- WP04
requirement_refs:
- C-001
- C-002
- C-004
- FR-010
- FR-011
- NFR-001
- NFR-002
- NFR-003
planning_base_branch: feat/retire-doctrine-term
merge_target_branch: feat/retire-doctrine-term
branch_strategy: Planning artifacts for this mission were generated on feat/retire-doctrine-term. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/retire-doctrine-term unless the human explicitly redirects the landing branch.
subtasks:
- T016
- T017
- T018
- T019
- T020
phase: Phase 5 - Verification Gate
history:
- at: '2026-08-21T00:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: reviewer-renata
authoritative_surface: kitty-specs/retire-doctrine-term-01M0JMK9/
create_intent:
- kitty-specs/retire-doctrine-term-01M0JMK9/verification-report.md
execution_mode: planning_artifact
model: ''
owned_files:
- kitty-specs/retire-doctrine-term-01M0JMK9/verification-report.md
role: reviewer
tags: []
task_type: review
tracker_refs: []
---

# Work Package Prompt: WP05 – Verification and Closeout

## Start and role boundary

Run `spec-kitty agent profile show reviewer-renata`, load it, then read all mission artifacts and `quickstart.md`. Check review feedback first. You verify; route substantive failures to WP01–WP04 and only write `verification-report.md`.

Every report check includes command/procedure, output excerpt or reviewer answers, timestamp, base SHA where relevant, and pass/fail. Missing evidence = fail.

## T016 — CI, scope, and ADR

Run the quickstart targeted tests and ADR freshness check. Verify the new ADR is `Accepted` with actual date/deciders/reviewers and explicit M1/I1 effectuation boundary; verify the old ADR body is byte-identical except `Superseded` status/pointer metadata.

Record two C-001 anchors:

- planning base = WP01-frozen `target_tip` from `implementation-baseline.json`; validate `target_ref: origin/main`, 40-character commit, capture metadata, and ancestry to the frozen implementation base; allowed planning/lifecycle artifacts, ADR/registration surfaces, squad evidence, and required docs-contract CI metadata;
- implementation base from the same atomic WP01 snapshot, captured before its first edit; validate schema, 40-character SHA, ancestry to `HEAD`, and `git merge-base <target_ref> HEAD == target_tip`; permit only the union of WP-owned implementation deliverables plus exact mission-relative runtime placements: `status.events.jsonl`, reduced `status.json`, `lanes.json`, `acceptance-matrix.json`, `issue-matrix.json`, `analysis-report.md`, `.kittify/dossiers/<mission>/...`, and `tasks/<WP-slug>/review-cycle-N.md` (all below `kitty-specs/<mission>/`). Prompt files must remain unchanged during execution. If the merge-base equality shows a different target was incorporated after capture, require the fresh-branch/replay-planning/restart-WP01 procedure.

Inspect committed delta plus working tree. Do not use an absolute file list that rejects pre-existing planning artifacts.

## T017 — Exact ADR self-sufficiency pass

One named independent reviewer (squad **or** operator; a second review is optional) reads only the new ADR and answers:

1. What decision was made and replacement is canonical?
2. How does Charter Pack differ from Charter Bundle, and what distinguishes Active Charter from Inactive Charter?
3. Which kind labels survive in their existing roles, and what replaces the former “Doctrine Domain” glossary sense?
4. What is in/out of scope, including operator-ID mappings and non-public internal versus supported public Python API, exact `doctrine.api.__all__`, and distribution/wheel treatment?
5. What is the 3.x compatibility policy and 4.0 removal rule?
6. How does the governance term differ from `src/charter/`?

Record answers and reviewer identity. Do not replace question 6 with the Terminology Canon line.

## T018 — Inventory proof

Load the same WP01-frozen `target_tip`, verify `target_tip=base_commit`, target→implementation→HEAD
ancestry, and no post-capture target incorporation before rerunning both exact audit commands. A stale
branch-point or silently repointed snapshot fails. Then verify:

- one manifest row per content occurrence and matching pathname;
- fixed eight-column header including nullable `compatibility_registry_id`;
- no duplicate coordinate, missing classification, or unknown S/OC/X ID;
- the CR column empty in the planning snapshot and for every X row; later product-compatibility rows remain OC and join exactly one CR;
- CR candidate observed coordinates/counts pairwise disjoint, with no source coordinate funding two candidates;
- manifest SHA and deterministic ordering;
- `total = content + path = OC + X1 + X2 + X3`;
- no active/unmerged-current-mission X2, active-glossary/alias X3, or supported-public-API/operator-ID X1;
- X2 mission classification starts at merge and does not depend on later archival;
- all deferrals have repo, owner, milestone, tracking reference/process, rationale, and no `TBD`.

Reproduce evidence at the frozen base. Record the expected mission-authored HEAD delta separately;
do not repoint or rewrite the pinned evidence from this reviewer WP.

## T019 — Plan and M1 dry run

Verify every OC appears exactly once across M1–M5 and every CR appears once at its M1–M4 introduction plus once at M6 removal; inventory owns no assignment, every funded source hit's OC primary owner equals its CR introduction wave, mixed-owner OCs/CRs are split, and no source/product coordinate is double-funded. Confirm bulk/invariants/rollback/M1 zero questions. For M2's sole question, prove every command/serialized/API/supported-public-Python-API/public-distribution OC and consumer is M2-owned, both map/projection are required, mandatory catalog/selection/service rows, exact `doctrine.api.__all__`, `spec-kitty-doctrine` distribution/wheel contract, publication evidence, and external owners are complete, M3–M5 exclude mapped hits, and only non-public internals or non-emitted physical paths are X1.

Repeat the M1 dry run: `docs/context/charter.md` plus all active referrers and old-path redirect, byte-identical X2 historical refs plus zero dangling active refs, both YAML authorities under parity/#2727 coordination; owner-correct bundle edits; `governance.charter` migration; exact canon; canonical Charter Pack vs Charter Bundle semantics; and replacement of the former “Doctrine Domain” entry with the governance-artefact-layer sense without a new domain brand. Verify complete pre-M1 ordinary preimage/M1 shrink plus the non-owning CR candidate overlay, actual-base drift reconciliation, owner=introduction joins, disjoint source budgets, fixed X3 control path/fingerprints, M2 fail-closed target/disposition resolution before edits, controlled introductions, and X-only/empty-CR I6. Verify M2 maps/projection/config and fixed M3 overlay migration require no decision.

## T020 — Methodology and report closeout

Verify every S1–S10 class/mixed-root portion has one primary verifier, each ordering step has concrete rationale, each I0–I6 invariant has a named check, every wave regenerates per-hit evidence, and rollback is prefix-safe.

Specifically confirm methodology tests fail for:

1. added hit in baselined file;
2. equal-count user-facing substitution;
3. removed source hit without baseline shrink;
4. new file hit.
5. unregistered or wrong-wave compatibility addition/move;
6. compatibility fingerprints above a frozen per-entry maximum;
7. product compatibility assembled from fragments.
8. one pre-M1 source coordinate funding two CRs;
9. one product fingerprint belonging to two CRs;
10. a duplicated, moved, or stale X3 control record.

Also prove a fail-closed M2 target/disposition prevents introduction before any source edit.

Write summary mapping SC-001..SC-004 to evidence and list routed findings. Ready only when all checks pass and no routed finding remains.

## Verification/review guidance

Reject self-authored “independent” ADR review, requiring both squad and operator, the broken shell-expanded audit, pathname omission, file/count guard baselines, ownerless deferrals, M1 Terminology Canon in `AGENTS.md`, sync-as-writer, wrong invariant mapping, or an open M4 canonical-name decision.

## Activity Log

The generation record below is immutable. Do not edit this prompt to append activity;
status/history is event-log owned. Use
`spec-kitty agent tasks move-task WP05 --to <status>`.

- 2026-08-21T00:00:00Z – system – Prompt created.
