---
work_package_id: WP09
title: Docs / skills / snapshots — flip "charter.md is THE source"
dependencies:
- WP04
requirement_refs:
- FR-011
- NFR-004
tracker_refs:
- '#2773'
planning_base_branch: feat/consolidate-charter-bundle
merge_target_branch: feat/consolidate-charter-bundle
branch_strategy: Planning artifacts for this mission were generated on feat/consolidate-charter-bundle. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/consolidate-charter-bundle unless the human explicitly redirects the landing branch.
subtasks:
- T035
- T036
- T037
- T038
- T039
agent: "claude:opus:reviewer-renata:reviewer"
history: []
agent_profile: python-pedro
authoritative_surface: docs/
create_intent: []
execution_mode: code_change
owned_files:
- docs/context/charter-overview.md
- docs/context/governance-files.md
- docs/api/charter-commands.md
- docs/architecture/06_unified_charter_bundle.md
- src/doctrine/skills/spec-kitty-charter-doctrine
- src/doctrine/missions/mission-steps/software-dev/charter/prompt.md
- tests/specify_cli/regression/_twelve_agent_baseline
- tests/specify_cli/skills/__snapshots__
- docs/development/3-2-page-inventory.yaml
role: implementer
tags: []
shell_pid: "688604"
shell_pid_created_at: "1784390848.95"
---

## ⚡ Do This First: Load Agent Profile
Load `/ad-hoc-profile-load python-pedro` (implementer). Load the YAML.

## Objective
Flip every doc/doctrine surface that asserts **"charter.md is THE runtime source"** to the inverted model (charter.yaml authoritative, charter.md curated companion), update the charter-doctrine SKILL assets (deployed to consumers), and refresh baseline snapshots. Required by C-006 (the PR is a consistent whole). Depends on WP04 so docs match landed behavior.

**Authoritative**: [`plan.md`](../plan.md) IC-09; carla's docs checklist in [`research/pre-plan-grounding.md`](../research/pre-plan-grounding.md).

## Context / grounding (hard contradictions)
- `docs/context/charter-overview.md` (lines ~16/18/35/53/77/110-112/148 assert "charter.md is the runtime policy source; sync extracts from it").
- `docs/context/governance-files.md` (lines ~16/28/42/64 assert "edit charter.md for runtime policy; YAML derived from charter.md").
- `docs/api/charter-commands.md` (`generate`/`sync` semantics change), `docs/architecture/06_unified_charter_bundle.md` (single-file manifest + schema bump).
- SKILL assets: `src/doctrine/skills/spec-kitty-charter-doctrine/SKILL.md` + `references/*`; charter mission-step prompt `src/doctrine/missions/mission-steps/software-dev/charter/prompt.md`.

## Subtasks
### T035 — Flip context docs
- Rewrite `charter-overview.md` + `governance-files.md`: charter.yaml is the authoritative structured source (governance/directives/catalog/activation); charter.md is a curated companion, never a resolving input; config keeps a `charter:` pointer; the extractor is retired.
### T036 — API + architecture docs
- `charter-commands.md`: `generate` no longer writes charter.md; `sync` no longer scrapes prose. `06_unified_charter_bundle.md`: single-file `charter.yaml` manifest v2 + `content_hash_files`.
### T037 — SKILL assets + charter prompt
- Update the charter-doctrine SKILL + references + the charter mission-step prompt to reflect the inversion (deployed to consumer projects via upgrade).
### T038 — Baseline snapshots + inventory
- Regenerate the affected `_twelve_agent_baseline/*` + `skills/__snapshots__/*` fixtures (charter.* content). Freshen the page inventory: `python -m scripts.docs.freshen_adr_inventory` (ADR already added earlier) + verify `check_docs_freshness --ci`.
### T039 — Terminology guard
- Run `PWHEADLESS=1 pytest tests/architectural/test_no_legacy_terminology.py -q` before hand-off (CI-only gate; prose changes can trip it).

## ATDD note
Docs WP has no red-first product test; validate against landed behavior (WP04) + `check_docs_freshness --ci` + the terminology guard.

## Branch Strategy
Base `feat/consolidate-charter-bundle` per `lanes.json` (dep WP04); merges back to `feat/consolidate-charter-bundle`. Lands in the same PR (C-006).

## Definition of Done
- No doc/doctrine surface asserts charter.md-as-source; SKILL assets updated; baselines regenerated; inventory fresh; terminology guard green.

## Reviewer guidance
- Grep the docs for residual "charter.md is the source" / "derived from charter.md"; verify SKILL assets reflect the inversion; verify `check_docs_freshness --ci` errors=0 and the terminology guard passes.

## Activity Log

- 2026-07-18T15:41:09Z – claude:sonnet:python-pedro:implementer – shell_pid=609724 – Assigned agent via action command
- 2026-07-18T16:07:13Z – claude:sonnet:python-pedro:implementer – shell_pid=609724 – flipped charter-overview/governance-files/charter-commands/06_unified_bundle + charter-doctrine SKILL assets + charter mission-step prompt to charter.yaml-authoritative; regenerated 12-agent baselines + codex/vibe skill snapshots. Gates foreground (orchestrator-run): terminology guard 3 passed, check_docs_freshness --ci errors=0, no residual 'charter.md is source'. (Implementer backgrounded arch sweep + stalled; finished by orchestrator.)
- 2026-07-18T16:07:31Z – claude:opus:reviewer-renata:reviewer – shell_pid=688604 – Started review via action command
- 2026-07-18T16:12:35Z – user – shell_pid=688604 – Contradictions flipped: charter-overview/governance-files now describe charter.yaml=authoritative structured source, charter.md=curated companion (never resolving), config charter: pointer, extractor/sync-scrape retired. API (charter-commands) + arch (06_unified_charter_bundle manifest v2, content_hash_files=[charter.yaml], derived_files empty) accurate to WP01/03/04 landed behavior. SKILL assets (SKILL.md + both references + charter mission-step prompt) consistently inverted; no stale 'derived-from-charter.md' teaching (retired triad only named as anti-pattern). 12-agent baselines + codex/vibe skill snapshots regenerated consistently: skills 284 passed, twelve-agent parity 209 passed. Gates green: terminology guard 3 passed, check_docs_freshness --ci errors=0 (8 warnings all pre-existing external LINK-HEALTH). Scope clean: all 22 files owned. Anti-pattern checklist PASS/N-A (docs-only). Note: one out-of-scope historical plan doc docs/plans/doctrine/org-doctrine-layer-architecture-review.md still narrates old sync-extraction in a past-analysis snapshot — not an owned WP09 surface; candidate follow-up, non-blocking.
