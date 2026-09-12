# Implementation Plan: Self-documenting repo (Bucket 2) — workflow/CI/status mechanics

**Branch**: `kitty/mission-workflow-self-doc` | **Date**: 2026-08-15 | **Spec**: `spec.md`
**Input**: `spec.md` (post-spec-squad-hardened) + audit `work/bucket2-workflow-memory-audit.md`

## Summary

Migrate the ~49 workflow/CI/git/status-&-sync **mechanics** memories into the canonical homes established by merged mission #2860 (4-layer model: rules→charter, practices→doctrine toolguides/tactics, reference→Common Docs, learned-facts→git-tracked `.kittify/memory/`). Dominant finding: **20 are already-home echoes** (delete, no repo change); the genuine residue is **status/mission/sync gate mechanics** → Common Docs, plus **3 review-discipline heuristics → existing doctrine tactics** (curator MAJOR-1), one `gh` trap → the tracker toolguide, four learned-facts → `.kittify/memory/`, and a live **stale-doc correctness fix** (`AGENTS.md:307`). A committed manifest + a fresh completeness test are the proof. No charter edit (the one candidate is operator-gated, C-004).

## Technical Context

**Language/Version**: Markdown + YAML (docs, toolguides, tactics); Python 3.11+ (guard + completeness tests, `scripts/docs/`).
**Primary Dependencies**: pytest (`tests/docs/**`, `tests/architectural/**`), the docs inventory/retrieval-index tooling, `spec-kitty doctrine regenerate-graph`, `spec-kitty doctor doctrine`.
**Storage**: files (docs, toolguides, tactics, `.kittify/memory/`, a manifest under the mission dir + `docs/development/`).
**Testing**: pytest — a fresh manifest-completeness test (mission-specific token set), content-anchor greps (NFR-005), doctrine cross-link + graph-roundtrip gates, docs-freshness.
**Target Platform**: repo/CI (Linux).
**Project Type**: single project.
**Constraints**: reuse #2860 homes (C-001); already-home = delete not duplicate (C-002); cite-don't-restate (C-003); no unilateral charter edit (C-004); serialize the shared rollups (C-006); no new merge-blocking red (NFR-002); content-anchored not empty-stub (NFR-005).

## Charter Check

- **Canonical sources**: route to the four established homes; never invent a parallel home (C-001); edit sources not generated copies.
- **SSOT (the Bucket-1 M1 lesson)**: cite-don't-restate where a home already carries the fact — the post-spec squad already re-scoped the issue-matrix migration and surfaced the doctrine-tactic layer to prevent drift.
- **Derived-from-repo (C-005/NFR-003)**: every migrated fact verified against current code/behavior; the `AGENTS.md:307` stale claim is corrected, not copied.
- **Terminology + docs-freshness + doctrine-integrity**: run the guards on every prose/doctrine touch.

## Implementation Concern Map

### IC-01 — Review-gate mechanics + issue-matrix discovery half (FR-001)
- **Home**: `docs/development/how-to/review-gates.md` (widen its title/scope from pre-PR hygiene to include review-cycle/merge-gate mechanics).
- **Migrate**: `merge_review_artifact_invariant`, `review_cycle_artifact_frontmatter_trap`, `rejected_then_fixed_approval_override`, `review_artifact_no_hand_author` (mechanics), + the genuinely-absent issue-matrix half (`discover_issue_references` over ALL mission docs; `issue-verdict --actor`).
- **Cite, don't restate (C-003)**: verdict vocabulary/schema/`.json`-canonical/deferred-handle/in-mission → `ERROR_CODES.md` + `spec-kitty-mission-review/SKILL.md` (manifest `already-home` rows).
- **Risk**: restating the already-home half (paula MAJOR) — mitigated by the cite scoping.

### IC-02 — Sync-drain runbook (FR-002)
- **Home**: new `docs/operations/sync-drain.md` + `recovery-index.md`/`toc.yml`. Durable core only (3-gate order `SPEC_KITTY_ENABLE_SAAS_SYNC` — not `..._ENABLED`; `sync migrate`; TeamSpace blockers; the `sync doctor` false-green vs `sync status` Delivered trap). Drop the fixed #2995/#2985 defect analyses.

### IC-03 — CI reference enrichments (FR-004)
- **Homes**: `coverage-signals.md` (the git-mv-into-critical-path + mocked-fast-test remedy), `known-friction-points.md` (CI-label `pr:skip-ci` skip guard; the gitignored-`graph.yaml` lint-input trap), a multi-WP true-base classification note.

### IC-04 — Landing stale-stack + history-compression how-to (FR-005)
- **Homes**: `pr-landing.md` (new stale-stack two-dot/three-dot diagnostic subsection), new `docs/development/how-to/compress-mission-history.md` (path-bucket `git commit-tree` recipe + tree-parity proof; the "never `rebase -i`" reasoning). Governance is already home in `pr-landing.md` — migrate only the concrete recipe (C-003).

### IC-05 — Architecture stale-doc fix + seam checklist (FR-003 docs half)
- **Homes**: `execution-lanes.md` (the real `MissingLanesError` contract; the `bulk_edit` disjoint-ownership nuance), `git-worktrees.md` (cross-mission concurrency note), `artifact-placement-seam.md` (partition-move audit checklist — cite the read/write-symmetry principle/ADR 2026-06-24-1, NOT a phantom "INV-5").

### IC-06 — AGENTS.md stale-line correctness fix (FR-003 agents half) — STANDALONE FAST LANE
- **Home**: `AGENTS.md` line 307 (the `CLAUDE.md` symlink source) — delete the phantom `lanes.json`-absent `-WP##` fallback; a guard test pins the corrected statement. Repo-root, no rollup regen → its own parallel lane, the P1 quick win.

### IC-07 — Doctrine enrichment: tracker toolguide + review-discipline tactics (FR-006 + FR-009) — STANDALONE `packs/**` LANE
- **Homes**: `GITHUB_TRACKER.md` + `github-tracker.toolguide.yaml` (closing-keyword pitfall); `architectural-gate-non-vacuity.tactic.yaml` (+= `gate_unmask_cannot_self_validate`, `seam_classification_two_axes`), `reviewer-implementer-role-separation.tactic.yaml` (+= `review_artifact_no_hand_author` principle), `canonical-source-unification.tactic.yaml` (+= `seam_bypass_stale_comment`).
- **Gates (NFR-004)**: `test_no_dead_doctrine_paths.py`; `doctrine regenerate-graph --check` (regen ONLY if a node title changes); `doctor doctrine --json`; terminology. No golden-count/description-length (phantom), no 12-agent parity (toolguides/tactics not copied).

### IC-08 — Learned-facts seeding (FR-007) — STANDALONE `.kittify/memory/` LANE
- **Home**: `.kittify/memory/` — `sync_identity_form_split`, `lane_base_guard_vs_moving_upstream` (clean LF; cite ADR 2026-07-29-1, don't restate), `no_recursionerror_is_not_no_cycle` (gotcha). Reconsider `collect_universe_once` (already embodied in `_gate_coverage.collect_universe` — likely drop or → `EFFICIENT_LOCAL_TOOLING`). Add a one-note format convention per the `.kittify/memory/README.md` discipline so the store doesn't reproduce the grab-bag failure.

### IC-09 — Migration manifest + fresh completeness test (FR-008) — TERMINAL
- **Home**: `docs/development/agent-memory-workflow-migration-manifest.md` (Bucket-2 companion; distinct file from Bucket 1's) + a NEW `tests/docs/test_workflow_migration_manifest_complete.py`. Token set `home:`/`already-home:`/`learned-fact:`/`keep-private`/`charter-candidate`; path-check the first three, pathless-recognise the last two; clusters A/B/C; all 49 rows resolved. Depends on every home-producing WP.

---

## Post-plan squad reconciliation (folded)

Two lenses (implementer-ivan feasibility, paula-patterns brownfield/SSOT) confirmed the plan is implementable and corrected home-assignment + guard details:

- **True-base note relocation (paula MAJOR-1).** WP03's "multi-WP true-base classification note" homes in `pr-landing.md §4` (WP04's file), which already owns red-classification-against-the-merge-base; the genuinely-absent lane-tip nuance (`git merge-base <mission-branch> upstream/main`; a dep-merged lane tip already contains earlier WPs) is a §4 addition, not a new CI-ref doc. **Moved to WP04**; WP03 cites §4, does not restate.
- **Seam-heuristic home-split (paula MINOR-1).** `seam_classification_two_axes` splits: part (a) — two-axis resolver-site classification (raise-or-degrade AND anchor-root) — is a seam-migration heuristic → **WP05** `artifact-placement-seam.md` partition-move checklist; part (b) — authority-parse vacuity (prove the gate reads its authority; alias/re-export bite) — → **WP08** `architectural-gate-non-vacuity.tactic.yaml` as a new element that **cross-references** the existing self-mutation step (don't restate).
- **Parallel-lane scope pin for `no_hand_author` (paula MINOR-2).** WP01 (DOCS) and WP08 (DOCTRINE) run in parallel and could both restate it. Pin: **WP08 tactic** = doctrine rationale only (two-party review integrity; never manufacture a sign-off); **WP01 review-gates** = mechanics only (no CLI writer for an `approved` artifact; gate keys on highest-cycle verdict; write to both primary+coord surfaces).
- **sync-drain gate-1 cite (paula MINOR-3).** `SPEC_KITTY_ENABLE_SAAS_SYNC` + `sync doctor` semantics are already home in `docs/operations/internal-hosted-readiness.md` (L35–158). WP02 **cites** it for gate-1 and restates only the genuinely-absent gate-2 (`sync migrate`), gate-3 (TeamSpace blockers), and the false-green trap.
- **WP07 guard assertion (ivan NOTE-1).** Assert the distinctive stale phrase (`.worktrees/<feature>-WP##` or `absent → legacy`) — NOT the bare `WP##` token, which appears legitimately at `AGENTS.md:305/:315` (`spec-kitty implement WP##`). Also positively assert the corrected statement (flat/`SINGLE_BRANCH`/`LANES` still require `lanes.json`; no fallback). Extending `test_claudemd_template_source.py` (already symlink-aware) is the clean pattern.
- **WP08 tactic-graph ownership (ivan NOTE-2).** `packs/built-in/tactic.graph.yaml` is a separate file carrying tactic DRG edges. If any enrichment adds a `references:` entry (a new edge), a tactic-graph regen fires → WP08 must own `tactic.graph.yaml`. Default: keep enrichments as pure step/failure-mode additions (no new `references`) → no regen; only add the graph file to owned_files if a reference is genuinely needed.

**Verified sound (no action):** all owned_files paths + parent dirs resolve; NFR-004 gate commands all exist and run; the `AGENTS.md:307` stale claim + `MissingLanesError`-no-fallback are real; the tactic schema is single-`.tactic.yaml` (heuristics as steps/failure_modes); toolguide body-only edits leave the graph byte-identical (regen only on title change); WP06 cross-lane deps are acyclic (Bucket-1 `lane-c→{a,b}` shape) with distinct new filenames; the 3 other tactic enrichments + the merge-gate mechanic are genuine (not already-home); `SPEC_KITTY_ENABLE_SAAS_SYNC` and the "INV-5"-is-phantom corrections both re-confirmed.

## Work Package decomposition (feeds /tasks)

Lanes reflect the post-spec `finalize-tasks` reality (C-006): one serialized DOCS lane owns the rollups; three standalone parallel lanes; terminal manifest depends on all.

| WP | Scope | owned_files | lane | depends_on |
|----|-------|-------------|------|-----------|
| **WP01** | IC-01 review-gates section (2 H2s: gate mechanics + issue-matrix discovery half; cite ERROR_CODES/SKILL) | `docs/development/how-to/review-gates.md` | DOCS (serial) | — |
| **WP02** | IC-02 sync-drain runbook + registration | `docs/operations/sync-drain.md`, `docs/operations/recovery-index.md`, `docs/operations/toc.yml` | DOCS (serial) | WP01 |
| **WP03** | IC-03 CI reference enrichments (coverage module-move remedy; CI-label skip guard; lint-input trap) — cites WP04 §4 for true-base, does NOT restate | `docs/development/reference/coverage-signals.md`, `reference/known-friction-points.md` | DOCS (serial) | WP02 |
| **WP04** | IC-04 stale-stack + compress-history how-to + **the multi-WP true-base/lane-tip note in `pr-landing.md §4`** (moved from WP03) | `docs/development/how-to/pr-landing.md`, `docs/development/how-to/compress-mission-history.md` | DOCS (serial) | WP03 |
| **WP05** | IC-05 arch docs + seam checklist (incl. `seam_classification_two_axes` part-a: two-axis resolver classification) | `docs/architecture/execution-lanes.md`, `git-worktrees.md`, `artifact-placement-seam.md` | DOCS (serial) | WP04 |
| **WP06** | IC-09 manifest + fresh completeness test + rollup regen (TERMINAL) | `docs/development/agent-memory-workflow-migration-manifest.md`, `tests/docs/test_workflow_migration_manifest_complete.py`, `docs/development/3-2-page-inventory.yaml`, `docs/development/3-2-docs-retrieval-index.yaml` | DOCS (serial, last) | WP05, WP07, WP08, WP09 |
| **WP07** | IC-06 AGENTS.md:307 fix + guard (P1 quick win) | `AGENTS.md`, `tests/architectural/test_workspace_resolution_doc.py` (or extend the claude-md guard) | AGENTS (∥) | — |
| **WP08** | IC-07 tracker toolguide + 3 tactic enrichments + graph regen | `packs/built-in/toolguides/GITHUB_TRACKER.md` + `.toolguide.yaml`, `packs/built-in/tactics/{architectural-gate-non-vacuity,reviewer-implementer-role-separation,canonical-source-unification}.tactic.yaml`, `packs/built-in/toolguide.graph.yaml` (+ tactic graph if regen) | DOCTRINE (∥) | — |
| **WP09** | IC-08 learned-facts seeding + note-format convention | `.kittify/memory/**` | MEMORY (∥) | — |

Parallel lanes: AGENTS (WP07), DOCTRINE (WP08), MEMORY (WP09) run concurrently with the head of the DOCS lane. The DOCS lane is internally serial (shared rollups). WP06 (terminal manifest) depends on all home-producing WPs so its path-checks pass. Mirrors Bucket 1's proven lane-c→{lane-a,lane-b} shape.
