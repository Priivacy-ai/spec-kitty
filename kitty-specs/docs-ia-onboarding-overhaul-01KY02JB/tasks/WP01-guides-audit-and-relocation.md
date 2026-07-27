---
work_package_id: WP01
title: Guides Audit & Contributor Content Relocation
dependencies: []
requirement_refs:
- FR-003
- FR-009
tracker_refs: []
planning_base_branch: feat/docs-ia-onboarding-overhaul
merge_target_branch: feat/docs-ia-onboarding-overhaul
branch_strategy: Planning artifacts for this mission were generated on feat/docs-ia-onboarding-overhaul. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/docs-ia-onboarding-overhaul unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
agent: "claude:sonnet-5:curator-carla:reviewer"
history: []
agent_profile: curator-carla
authoritative_surface: docs/development/
create_intent: []
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- docs/guides/pr-landing.md
- docs/guides/testing-flakiness.md
- docs/guides/keep-main-clean.md
- docs/guides/recover-from-interrupted-merge.md
- docs/guides/recover-from-implementation-crash.md
- docs/guides/run-mutation-tests.md
- docs/guides/review-artifacts-with-planbridge.md
- docs/guides/contract-pinning.md
- docs/guides/coverage-signals.md
- docs/guides/write-time-dependent-tests.md
- docs/guides/use-operation-history.md
- docs/guides/testing-parallel.md
- docs/guides/implement-work-package.md
- docs/guides/review-work-package.md
- docs/guides/merge-feature.md
- docs/guides/build-custom-orchestrator.md
- docs/guides/run-external-orchestrator.md
- docs/guides/sync-workspaces.md
- docs/guides/worktrees-with-mcp-agents.md
- docs/guides/tool-surface-upgrade-and-repair.md
- docs/guides/internal-hosted-readiness.md
- docs/guides/orchestrator-quickstart.md
- docs/guides/manage-issue-tracker.md
- docs/guides/red-main-and-release-readiness.md
- docs/guides/claude-code-workflow.md
- docs/development/**
- scripts/docs/redirect_map.yaml
role: implementer
tags: []
shell_pid: "75781"
shell_pid_created_at: "1784568130.024352"
---

## ⚡ Do This First: Load Agent Profile

`/ad-hoc-profile-load curator-carla` (role: implementer). Then read, in order:
[spec.md](../spec.md) FR-003/FR-009 and the Known Gaps in Documentation Scope,
[plan.md](../plan.md) §IC-01, [research.md](../research.md) items 1 and 2, and
[data-model.md](../data-model.md)'s `DocsPage` entity.

## Objective

`docs/guides/` is a flat 72-file pile mixing end-user tutorials/how-tos with contributor-only
runbooks. This WP produces ground-truth on every file in `docs/guides/` and the existing
`docs/development/` contributor root, physically relocates confirmed contributor-only files
into `docs/development/`, and regenerates the site's redirect map non-destructively so no
published URL 404s. This is the foundational WP — WP02 (navigation) and everything downstream
depends on final file locations being settled here.

## Context

- `docs/development/` already exists as a contributor root (7 files today: `index.md`,
  `sync-daemon-orphan-cleanup.md`, `mutation-testing-tactic.yaml`,
  `quality-and-tech-debt-standing-orders.md`, `3-2-page-inventory.yaml`, plus 2 more) — this WP
  extends it, does not create it.
- **Redirects are NOT hand-edited.** `scripts/docs/redirect_map.yaml` carries a header:
  `SINGLE-WRITER (WP07-owned): DERIVED, do not hand-edit. Regenerate with
  python3 scripts/docs/redirect_stub_generator.py regenerate-map`. It is deterministically
  derived from `scripts/docs/redirect_baseline_urls.json` (the pre-move baseline manifest) plus
  an `occurrence_map.yaml` `moves:` spine (see
  [contracts/redirect-map-entry-contract.md](../contracts/redirect-map-entry-contract.md)).
- **Critical non-destructiveness constraint**: `redirect_stub_generator.py`'s
  `--occurrence-map` flag defaults to
  `kitty-specs/common-docs-structural-move-01KW3SBK/occurrence_map.yaml` (the PRIOR docs
  mission's move spine, 29 entries, producing the archive-era redirects currently in
  `redirect_map.yaml`). If you `regenerate-map` using only a NEW occurrence_map.yaml containing
  just this mission's moves, you will **silently wipe all 29 prior redirect entries** — a real
  regression. You must merge forward.

## Subtask guidance

- **T001 — Full audit, disposition table.** Read every file in `docs/guides/` (72 files) and
  `docs/development/` (7 files). For each, record in a NEW file
  `kitty-specs/docs-ia-onboarding-overhaul-01KY02JB/docs-audit.md`: path, current zone guess
  (end-user/contributor), disposition (`keep`/`merge`/`rewrite`/`remove`/`relocate`), and a
  one-line rationale. Do NOT overwrite the auto-generated `gap-analysis.md` in the same
  directory — that's a separate, mechanical tool output (see research.md item 10); this is a
  new, hand-curated file. Use a markdown table, one row per file.
- **T002 — Verify the contributor-only candidate list.** This WP's `owned_files` list above
  names 24 files pre-identified by earlier research as contributor-only (PR-review, testing
  runbooks, merge/worktree recovery, orchestrator internals). Open each one and confirm its
  actual content is contributor/maintainer-facing, not end-user-facing, before moving it. If any
  candidate turns out to be genuinely end-user-relevant (e.g. a page a non-contributor adopter
  would plausibly need), leave it in `docs/guides/` and note the correction in `docs-audit.md`
  with rationale — do not move it just because it was on the candidate list.
- **T003 — Relocate confirmed contributor files.** For every file confirmed contributor-only in
  T002, `git mv docs/guides/<file>.md docs/development/<file>.md`. Update the file's own
  internal frontmatter/breadcrumbs if it references its old path. Do not touch
  `docs/guides/getting-started.md` or `docs/guides/your-first-feature.md` — WP03 owns those
  exclusively; touching them here is an ownership violation.
- **T004 — Merge-forward occurrence map and regenerate redirects.** Read
  `kitty-specs/common-docs-structural-move-01KW3SBK/occurrence_map.yaml` in full. Create
  `kitty-specs/docs-ia-onboarding-overhaul-01KY02JB/occurrence_map.yaml` whose `moves:` list is
  that file's existing 29 entries **plus** one new entry per file moved in T003 (schema:
  `{from: [<old_repo_path>], to: <new_repo_path_without_extension_or_as_the_tool_expects>}` —
  match the existing entries' exact shape, don't invent a new shape). Then run:
  ```bash
  python3 scripts/docs/redirect_stub_generator.py regenerate-map \
    --occurrence-map kitty-specs/docs-ia-onboarding-overhaul-01KY02JB/occurrence_map.yaml
  ```
  Confirm the output entry count is ≥ the prior map's entry count plus the number of files moved
  in T003 (never fewer — a drop means something was lost).
- **T005 — Verify redirect coverage.** Run:
  ```bash
  python3 scripts/docs/redirect_stub_generator.py check-map \
    --occurrence-map kitty-specs/docs-ia-onboarding-overhaul-01KY02JB/occurrence_map.yaml
  ```
  This performs the structural `uncovered == []` check against the baseline (no live DocFX build
  is available locally — see the script's own docstring, "No live build locally"). If it
  reports uncovered URLs, go back and fix the occurrence map before proceeding — do not move on
  with known gaps.

## Branch Strategy

Planning artifacts were generated on `feat/docs-ia-onboarding-overhaul`. This WP branches from
that base during `/spec-kitty.implement` and merges back into
`feat/docs-ia-onboarding-overhaul`. No dependencies — this WP can start immediately.

## Definition of Done

- [ ] `docs-audit.md` exists with a disposition row for every file in `docs/guides/` and
      `docs/development/` (79 rows minimum).
- [ ] Every file confirmed contributor-only in T002 has been `git mv`'d into `docs/development/`.
- [ ] `docs/guides/getting-started.md` and `docs/guides/your-first-feature.md` are untouched.
- [ ] `occurrence_map.yaml` at this mission's `kitty-specs/` path contains the prior mission's
      29 moves plus this WP's new moves.
- [ ] `redirect_map.yaml` regenerated via `--occurrence-map` pointing at the merged file; entry
      count did not decrease.
- [ ] `check-map` reports zero uncovered baseline URLs.

## Risks & Mitigations

- **Silent redirect-map data loss** if `regenerate-map` is run without `--occurrence-map`
  pointing at the merged file (defaults to the prior mission's map, which excludes this
  mission's new moves — the reverse failure mode). Always pass `--occurrence-map` explicitly.
- **Over-aggressive relocation**: moving a file that's actually end-user-relevant breaks User
  Story 1. T002 exists specifically to catch this — do not skip it.
- **Silent content loss** during "consolidation" — every disposition in `docs-audit.md` needs a
  rationale a reviewer can check against the actual file content.

## Review Guidance

- Spot-check 5 random `docs-audit.md` dispositions against the actual file content.
- Confirm `git log --follow` on 2-3 relocated files shows a clean rename (not a delete+add
  losing history).
- Re-run `check-map` yourself; do not trust the WP's self-report alone.

## Activity Log

- {{TIMESTAMP}} – system – Prompt created.
- 2026-07-20T16:37:02Z – claude:sonnet-5:curator-carla:implementer – shell_pid=62494 – Assigned agent via action command
- 2026-07-20T17:19:50Z – claude:sonnet-5:curator-carla:implementer – shell_pid=62494 – Ready for review: 13 contributor-only pages relocated to docs/development/ (10 pre-flagged + 3 found in audit), 15 pre-flagged candidates corrected to stay end-user with rationale recorded, docfx.json/redirect-baseline/CONTRIBUTING-symlink infra fixes required to make the move actually publish, occurrence_map.yaml merges prior mission's 29 moves forward with 13 new ones (redirect_map 136->149, zero entries lost), all docs validators + terminology guard + redirect tests green.
- 2026-07-20T17:22:12Z – claude:sonnet-5:curator-carla:reviewer – shell_pid=75781 – Started review via action command
- 2026-07-20T17:32:15Z – user – shell_pid=75781 – Review passed: docs-audit.md covers all 80 rows (60 guides incl. justified harnesses-dir summary row + 20 development, content-based rationale, spot-checked accurate). 13 files git-mv'd guides->development with clean --follow history; getting-started.md/your-first-feature.md (WP03) and docs/toc.yml (WP02) untouched. occurrence_map.yaml verified programmatically: all 29 prior moves preserved exactly (0 missing), 2 new grouped entries match the prior file's established multi-from/directory-to shape. redirect_map.yaml 136->149 entries, reproduced byte-for-byte via regenerate-map, check-map reports fresh/zero-uncovered. All 5 out-of-map edits (docfx.json glob, redirect_baseline_urls.json dated amendment, CONTRIBUTING.md symlink+guard script repoint, cross-reference link fixes across README/AGENTS.md/ADRs/CHANGELOG/CI workflow/doctrine YAML/plans/tests) independently confirmed necessary and minimal -- relative_link_fixer.py --check shows 0 dead links post-move. uv tool CLI side effect confirmed resolved (receipt points at main checkout, not worktree; pyproject.toml/src untouched; git status clean). Ran tests independently (not trusting self-report): tests/docs/ 525 passed, terminology guard + quarantine marker + redirect_stub_generator tests all green.
