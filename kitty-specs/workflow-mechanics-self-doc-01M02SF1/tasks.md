# Work Packages: Self-documenting repo (Bucket 2) — workflow/CI/status mechanics

**Mission**: workflow-mechanics-self-doc-01M02SF1 | **Branch**: `kitty/mission-workflow-self-doc`
**Spec**: `spec.md` | **Plan**: `plan.md` | **Audit**: `work/bucket2-workflow-memory-audit.md`

Decomposition per the post-plan squad. DOCS WPs (01–06) share the two generated rollups → collapse into one serialized lane. AGENTS (WP07), DOCTRINE (WP08), MEMORY (WP09) are standalone parallel lanes. WP06 (manifest) is terminal, depends on all home-producing WPs.

---

## WP01: Review-gate mechanics + issue-matrix discovery half (Priority: P1)
**Goal**: Widen `review-gates.md` to carry the review-cycle/merge-gate mechanics + the genuinely-absent issue-matrix discovery half; CITE `ERROR_CODES.md`/`spec-kitty-mission-review/SKILL.md` for the already-home verdict vocabulary (C-003).
**Prompt**: `/tasks/WP01-review-gates-mechanics.md` | **Dependencies**: None | **Refs**: FR-001, C-003, NFR-001, NFR-005
### Subtasks
- [ ] T001 Add a "Review-cycle artifacts and the merge gate" H2: `terminal_wp_latest_review_artifact_must_not_be_rejected`, the `--review-feedback-file` two-file trap, the `--skip-review-artifact-check --force` override (superseded-rejection only), and the no-hand-author *mechanics* (gate keys on highest-cycle verdict; write both primary+coord). NOT the doctrine rationale (that is WP08).
- [ ] T002 Add the issue-matrix discovery half: `discover_issue_references` runs over ALL mission docs; `issue-verdict --actor` required. CITE `ERROR_CODES.md` + `spec-kitty-mission-review/SKILL.md` for verdict vocabulary/schema/`.json`-canonical/`in-mission` semantics — do not restate.
- [ ] T003 Widen the doc's title/description to cover review-cycle mechanics (not just pre-PR hygiene). Content anchor present (`terminal_wp_latest_review_artifact_must_not_be_rejected`).

---

## WP02: Sync-drain operations runbook (Priority: P1)
**Goal**: New `docs/operations/sync-drain.md`: gate-2 (`sync migrate`), gate-3 (TeamSpace blockers), the `sync doctor` false-green vs `sync status` Delivered trap; CITE `internal-hosted-readiness.md` for gate-1 (`SPEC_KITTY_ENABLE_SAAS_SYNC`). Register in recovery-index + toc.
**Prompt**: `/tasks/WP02-sync-drain-runbook.md` | **Dependencies**: WP01 | **Refs**: FR-002, C-003, NFR-001, NFR-005
### Subtasks
- [ ] T004 Author `sync-drain.md` (frontmatter matching ops runbooks; `divio_type: none`; description 50–180). Content anchor `SPEC_KITTY_ENABLE_SAAS_SYNC` (never `..._ENABLED`); cite gate-1's home.
- [ ] T005 Register in `recovery-index.md` + `toc.yml`.

---

## WP03: CI reference enrichments (Priority: P2)
**Goal**: `coverage-signals.md` git-mv-into-critical-path + mocked-fast-test remedy; `known-friction-points.md` CI-label `pr:skip-ci` skip guard + gitignored-`graph.yaml` lint-input trap. CITE `pr-landing.md §4` for true-base (do not restate — that lives in WP04).
**Prompt**: `/tasks/WP03-ci-reference-enrichments.md` | **Dependencies**: WP02 | **Refs**: FR-004, C-003, NFR-001, NFR-005
### Subtasks
- [ ] T006 `coverage-signals.md`: the "git mv into critical-path + non-`fast` tests → add a `fast` mocked test module" remedy (fresh, PR #3437).
- [ ] T007 `known-friction-points.md`: `pr:deferred`/`pr:skip-ci` job-skip guard; `charter lint` reads gitignored generated `graph.yaml` (confirm input tracked+in-diff before filing).

---

## WP04: Landing stale-stack + history-compression how-to (Priority: P2)
**Goal**: `pr-landing.md §4` gets the multi-WP true-base/lane-tip note (`git merge-base <mission-branch> upstream/main`) + a stale-stack two-dot/three-dot diagnostic subsection; new `compress-mission-history.md` (path-bucket `git commit-tree` recipe + tree-parity proof).
**Prompt**: `/tasks/WP04-landing-history-howto.md` | **Dependencies**: WP03 | **Refs**: FR-005, C-003, NFR-001, NFR-005
### Subtasks
- [ ] T008 `pr-landing.md`: true-base/lane-tip note in §4 + stale-stack diagnostic subsection ("charter files in a small-fix PR = smuggled governance").
- [ ] T009 New `compress-mission-history.md`: the `git commit-tree` snapshot-chain recipe, tree-parity proof, "never `rebase -i`" reasoning. Content anchor `git commit-tree`.

---

## WP05: Architecture docs + seam checklist (Priority: P2)
**Goal**: `execution-lanes.md` the real `MissingLanesError` contract + `bulk_edit` disjoint-ownership nuance; `git-worktrees.md` cross-mission concurrency note; `artifact-placement-seam.md` partition-move audit checklist (cite ADR 2026-06-24-1, NOT "INV-5") + the two-axis resolver-site classification.
**Prompt**: `/tasks/WP05-architecture-docs.md` | **Dependencies**: WP04 | **Refs**: FR-003, C-003, NFR-001, NFR-005
### Subtasks
- [ ] T010 `execution-lanes.md` `MissingLanesError` contract (no `-WP##` fallback); `git-worktrees.md` two-missions-per-checkout race.
- [ ] T011 `artifact-placement-seam.md`: partition-move audit checklist (grep every reader; watch out-of-loop coord-resolving callers; e2e-not-unit catches it) + two-axis classification; cite the read/write-symmetry ADR wording.

---

## WP06: Migration manifest + completeness test (TERMINAL) (Priority: P1)
**Goal**: `agent-memory-workflow-migration-manifest.md` mapping all 49 audited memories → `home:`/`already-home:`/`learned-fact:`/`keep-private`/`charter-candidate`; a NEW `tests/docs/test_workflow_migration_manifest_complete.py`; single rollup regen; freshness errors=0.
**Prompt**: `/tasks/WP06-manifest-and-test.md` | **Dependencies**: WP05, WP07, WP08, WP09 | **Refs**: FR-008, NFR-001, NFR-005
### Subtasks
- [ ] T012 Author the manifest (clusters A/B/C; every row a resolution token; already-home rows cite existing homes incl. `ERROR_CODES.md`/SKILL.md).
- [ ] T013 New completeness test: parse the manifest; `home:`/`already-home:`/`learned-fact:` path-checked, `keep-private`/`charter-candidate` pathless; all 49 resolved; anti-tautology self-test.
- [ ] T014 Regenerate `3-2-page-inventory.yaml` + `3-2-docs-retrieval-index.yaml`; `check_docs_freshness --ci` errors=0.

---

## WP07: AGENTS.md stale-line fix + guard (Priority: P1) — STANDALONE
**Goal**: Delete the phantom `lanes.json`-absent `-WP##` fallback at `AGENTS.md:307`; a guard asserts the stale phrase absent + the corrected statement present.
**Prompt**: `/tasks/WP07-agents-stale-fix.md` | **Dependencies**: None | **Refs**: FR-003, NFR-002, NFR-005
### Subtasks
- [ ] T015 Correct `AGENTS.md:307` (flat/`SINGLE_BRANCH`/`LANES` still require `lanes.json`; no fallback — `resolve_workspace_for_wp` raises `MissingLanesError`).
- [ ] T016 New guard `test_workspace_resolution_doc.py`: assert the stale phrase (`.worktrees/<feature>-WP##` / `absent → legacy`) absent AND the corrected statement present. Do NOT ban the bare `WP##` token (legit at :305/:315).

---

## WP08: Tracker toolguide + review-discipline tactic enrichments (Priority: P2) — STANDALONE
**Goal**: `GITHUB_TRACKER.md` closing-keyword pitfall; enrich three tactics with their review-discipline heuristics (mechanics stay in WP01). Keep enrichments as step/failure-mode additions (no new `references:` → no graph regen).
**Prompt**: `/tasks/WP08-doctrine-enrichment.md` | **Dependencies**: None | **Refs**: FR-006, FR-009, NFR-004, NFR-005
### Subtasks
- [ ] T017 `GITHUB_TRACKER.md` + a pitfall row: `gh` "Closes #A,#B" links only #A. Keep `.toolguide.yaml` consistent (no title change → no graph regen).
- [ ] T018 `architectural-gate-non-vacuity.tactic.yaml` += authority-parse vacuity (gate reads its authority; alias/re-export bite) as a new element cross-referencing the self-mutation step; `reviewer-implementer-role-separation.tactic.yaml` += two-party-review-integrity rationale (never manufacture a sign-off); `canonical-source-unification.tactic.yaml` += "can't-reuse-the-seam is a red flag" linked to Parity/Fallback failure modes.
- [ ] T019 Gates: `test_no_dead_doctrine_paths.py`; `doctrine regenerate-graph --check` (byte-identical); `doctor doctrine --json` clean; terminology.

---

## WP09: Learned-facts seeding (Priority: P3) — STANDALONE
**Goal**: Seed `.kittify/memory/` with the genuinely-narrow-but-shareable heuristics + a one-note format convention.
**Prompt**: `/tasks/WP09-learned-facts.md` | **Dependencies**: None | **Refs**: FR-007, C-003, NFR-005
### Subtasks
- [ ] T020 Add notes: `sync-identity-form-split` (cite seam + #883), `lane-base-vs-moving-upstream` (cite ADR 2026-07-29-1, don't restate), `no-recursionerror-is-not-no-cycle`. Reconsider `collect-universe-once` (already embodied in `_gate_coverage.collect_universe` → drop or route to EFFICIENT_LOCAL_TOOLING).
- [ ] T021 Add a one-note format convention (each note states its own "why it's here") per `.kittify/memory/README.md` discipline.
