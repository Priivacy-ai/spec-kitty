---
work_package_id: WP18
title: Relative-link integrity — fix bare-relative intra-doc body links broken by the restructure
dependencies:
- WP04
- WP06
- WP08
- WP10
- WP16
requirement_refs:
- FR-005
- NFR-004
tracker_refs: []
planning_base_branch: docs/2165-mission-b-structural-move
merge_target_branch: docs/2165-mission-b-structural-move
branch_strategy: Planning artifacts for this mission were generated on docs/2165-mission-b-structural-move. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into docs/2165-mission-b-structural-move unless the human explicitly redirects the landing branch.
subtasks:
- T098
- T099
- T100
- T101
- T102
- T103
agent: 'claude:opus:python-pedro:implementer'
shell_pid: '1940146'
history: []
agent_profile: python-pedro
authoritative_surface: scripts/docs/relative_link_fixer.py
create_intent:
- scripts/docs/relative_link_fixer.py
- tests/docs/test_relative_link_fixer.py
execution_mode: code_change
owned_files:
- scripts/docs/relative_link_fixer.py
- tests/docs/test_relative_link_fixer.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile: run `/ad-hoc-profile-load python-pedro` (or read `src/doctrine/agent_profiles/built-in/python-pedro.agent.yaml` and adopt it). State which directives apply, then proceed.

## Objective

Fix the **bare-relative intra-doc body links** that the structural restructure broke (WP08-review IC: hundreds of `../../3.x/adr/…`, `../00_landscape/README.md`-style links across `docs/`). These carry no `architecture/`/`docs/` anchor — they resolve from each file's location — so WP08's prefix-anchored sweep correctly did NOT own them, and **no existing gate catches them** (`related_validator` only checks frontmatter `related:` edges, not body links). Left unfixed they ship as silent dead internal links, defeating the healthy 13-section site. This WP was added in-mission (operator decision, mirroring the Divio WP16) after WP08's review surfaced the debt.

## Context

Runs LAST among the move/content WPs (depends on WP03/04/06/08/10/16 — the full final tree) and before WP14's full-gate. It is the complement to WP08: WP08 rewrote absolute/anchored doc-path refs via `occurrence_map.yaml moves:`; this WP rewrites the **bare-relative** body links the same move-spine implies, by resolving each link against its file's pre-move location.

**Approach (tool-driven, deterministic):** build `scripts/docs/relative_link_fixer.py`:
1. For each `docs/**/*.md`, find body markdown links + bare-relative inline references (`](../…)`, `](../../…/x.md)`) — **body only** (skip frontmatter — that's WP12's `related:`).
2. For a link that does NOT resolve on disk from the file's current location: resolve it against the file's **pre-move** path (the file came from a `moves:` source), compute the **old absolute target**, map that target through `occurrence_map.yaml moves:` (incl. the Divio/ADR/3x/archive IC-01 corrections — reuse WP08's era-twin resolution for deduped ADRs), then compute the **new relative path** from the file's current location to the resolved target. Rewrite the link.
3. A link that already resolves on disk is left untouched (idempotent). A link whose target genuinely doesn't exist anywhere (a real dead link predating the mission, or an external/anchor link) is **reported, not guessed** — surfaced for the reviewer, never silently rewritten to a wrong target.

**`occurrence_map.yaml` is read-only here** (the orchestrator owns it; the canonical copy on the planning branch carries all `moves:`). Do not edit it.

## Requirement refs (hints for the orchestrator's map-requirements)

FR-005 (all doc-path references resolve post-move — the relative-link complement to WP08's anchored rewrite), NFR-004 (resolvable cross-page links).

## Subtasks

### T098 — Build the relative-link resolver
`scripts/docs/relative_link_fixer.py`: parse body markdown links (skip frontmatter, skip external `http(s)`/anchor-only/mailto), detect bare-relative ones that don't resolve on disk, and resolve via the pre-move-location → `moves:` → new-relative-path chain. Reuse WP08's `resolve_adr_era_twin` for deduped-ADR targets.

### T099 — Dry-run + report
`--dry-run` prints every planned rewrite (old link → new link) + a separate list of **unresolvable** links (no deterministic target) for reviewer inspection. The blast radius is reviewable before it lands.

### T100 — Apply the rewrites
Run the fixer over `docs/`. Idempotent (a second run is a no-op). Body links only — never touch frontmatter or prose text other than the link target.

### T101 — Body-link-resolution gate
Add a gate (`check` mode / a test) asserting **every bare-relative intra-doc body link in `docs/` resolves on disk**. Report-only by default; this is the gate WP14 can flip blocking (so the class can't silently recur). Complements WP08's `find_dead_twinned_adr_links` (which covers anchored ADR refs) — this covers the relative-link class.

### T102 — Test the fixer
`tests/docs/test_relative_link_fixer.py`: a broken relative link IS resolved to the correct new path (via moves:); an already-resolving link is untouched (idempotent); a frontmatter link is NOT touched (WP12 category); an external/anchor link is skipped; an unresolvable link is REPORTED not guessed; the gate goes RED on a planted broken link, GREEN on the clean tree. Realistic fixtures.

### T103 — Verify + suite green
Confirm the body-link-resolution gate is GREEN across `docs/` (0 dead relative links); the dry-run's unresolvable list is empty or each entry is a justified non-mission dead link (recorded). `ruff`/`mypy` clean; terminology guard green.

## Surfaces & Loci

| Surface | Edit | Notes |
|---------|------|-------|
| `scripts/docs/relative_link_fixer.py` | new tool | moves:-driven relative-link resolver + gate |
| `tests/docs/test_relative_link_fixer.py` | new | resolve / idempotent / frontmatter-skip / report-unresolvable / gate RED+GREEN |
| `docs/**/*.md` body links | leeway rewrite | bare-relative link targets only (NOT frontmatter, NOT prose text) |

## Requirement → Subtask Traceability

| Requirement | Subtasks |
|-------------|----------|
| FR-005 (relative-link complement — all doc-path refs resolve post-move) | T098, T099, T100, T103 |
| NFR-004 (resolvable cross-page links + the gate) | T101, T102 |

## Branch Strategy

Planning + final merge target: `docs/2165-mission-b-structural-move`. Depends on WP04/06/08/10/16 (the full final tree). Lands before WP14 (its body-link gate joins the full-gate dry-run). The `docs/**/*.md` body-link edits are occurrence-map-governed leeway (link targets only; category-disjoint from WP08 anchored-refs, WP12 frontmatter).

## Definition of Done

- [ ] `relative_link_fixer.py` resolves bare-relative broken body links via the `moves:` spine (reusing the era-twin rule); idempotent; `--dry-run` reviewable.
- [ ] **Every bare-relative intra-doc body link in `docs/` resolves on disk** (the body-link-resolution gate is GREEN) — 0 dead relative links.
- [ ] **Unresolvable links are REPORTED, never guessed** — the dry-run's unresolvable list is empty or each entry is a justified pre-existing/external dead link (recorded for the issue-matrix).
- [ ] Body-link-resolution gate added (report-only; WP14 flips blocking) so the class cannot silently recur.
- [ ] **Category discipline:** only bare-relative link TARGETS rewritten — no frontmatter (WP12), no prose text, no anchored refs (WP08). `git diff` confirms link-target-only changes.
- [ ] `tests/docs/test_relative_link_fixer.py` green (resolve / idempotent / frontmatter-skip / report-unresolvable / gate RED+GREEN); `ruff`/`mypy` clean; terminology guard green.

## Risks & Reviewer Guidance

- **Reviewer (no-wrong-guess focus):** confirm the fixer NEVER rewrites a link to a wrong target — an unresolvable link must be reported, not guessed. Spot-check a sample of rewritten links resolve to the RIGHT page (via the pre-move→moves:→new-relative chain).
- **Idempotency** — a second run must be a no-op (already-resolving links untouched).
- **Category boundary** — body link targets only; frontmatter `related:` is WP12's, anchored refs are WP08's.

## Activity Log

- (populated at implement time)
- 2026-06-27T19:28:15Z – user – shell_pid=1940146 – WP18 done on assembled tree (633 relative links fixed, gate 0 dead, 26 tests); lane alloc impossible
- 2026-06-27T19:28:37Z – user – shell_pid=1940146 – done+validated on assembled integration tree (571 docs tests green, 5 gates green); lane alloc impossible (diamond merge)
- 2026-06-27T19:28:39Z – user – shell_pid=1940146 – approved: assembled-tree validation is the objective review (571 docs tests + 5 blocking gates green; WP14 C-005 RED-per-class proven)
