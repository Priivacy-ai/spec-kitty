---
work_package_id: WP08
title: 'Glossary Activation: Anchors + Linker'
dependencies: []
requirement_refs:
- FR-011
- FR-012
tracker_refs: []
planning_base_branch: feat/docs-ia-onboarding-overhaul
merge_target_branch: feat/docs-ia-onboarding-overhaul
branch_strategy: Planning artifacts for this mission were generated on feat/docs-ia-onboarding-overhaul. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/docs-ia-onboarding-overhaul unless the human explicitly redirects the landing branch.
subtasks:
- T033
- T034
- T035
- T036
- T037
agent: "claude:sonnet-5:python-pedro:reviewer"
history: []
agent_profile: python-pedro
authoritative_surface: scripts/docs/glossary_linker.py
create_intent:
- scripts/docs/glossary_linker.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- scripts/docs/generate_kitty_specs_docs.py
- scripts/docs/glossary_linker.py
role: implementer
tags: []
shell_pid: "76558"
shell_pid_created_at: "1784568151.243852"
---

## ⚡ Do This First: Load Agent Profile

`/ad-hoc-profile-load python-pedro` (role: implementer). Then read, in order:
[spec.md](../spec.md) FR-011/FR-012/NFR-004 + Edge Cases, [plan.md](../plan.md) §IC-07,
[data-model.md](../data-model.md)'s `GlossaryTerm`/`GlossaryLink` entities,
[contracts/glossary-anchor-contract.md](../contracts/glossary-anchor-contract.md), and
[contracts/glossary-linker-contract.md](../contracts/glossary-linker-contract.md) — these two
contracts are the literal spec for what you're building; follow them precisely.

## Objective

Make the published glossary (104 terms, `kitty-specs/glossary.html`, generated from
`.kittify/glossaries/spec_kitty_core.yaml`) individually addressable per term, and build a
build-time HTML post-processing pass that auto-links the first mention of each term on every
doc page with a hover tooltip. No markdown source file is ever mutated — this was a deliberate,
user-confirmed decision (Decision Moment `01KY03YGX7GQEBKV45Q2Q8FXK3`), rejecting the
alternative of baking links into markdown prose.

## Context

- `glossary_page()` in `scripts/docs/generate_kitty_specs_docs.py` currently renders the 104
  terms with no stable per-term anchor — read this function fully before editing it.
- The new `glossary_linker.py` runs in the same pipeline-stage pattern as the existing
  `scripts/docs/seo_postprocess.py` — read that file for the established pattern (how it's
  invoked, what directory it operates over) before writing the new script, so yours is
  consistent with the existing pipeline's conventions.
- DocFX's `xref` system was investigated and explicitly rejected for this (research.md item 4)
  — do not reach for it.

## Subtask guidance

- **T033 — Anchor ID generation.** In `glossary_page()`, for each of the 104 terms, generate
  `anchor_id` = lowercase, ASCII-only, hyphen-separated slug of `surface`
  (`"branch strategy gate"` → `"branch-strategy-gate"`). Render it as `id="term-{anchor_id}"` on
  each term's card element, per the anchor contract's exact HTML shape.
- **T034 — Collision handling.** Implement the collision rule: if two terms slugify to the same
  `anchor_id`, append a numeric suffix (`-2`, `-3`, ...) in seed-file order. Write a small unit
  check (can be inline in the module or in `tests/` if this repo has a place for script tests —
  check for an existing `tests/scripts/` or similar convention) proving two colliding inputs get
  distinct anchors. With the current 104 real terms this may never trigger, but the code path
  must exist and be provably correct.
- **T035 — `glossary_linker.py` skeleton.** New file. Load `.kittify/glossaries/spec_kitty_core.yaml`
  (reuse whatever YAML-loading pattern the rest of `scripts/docs/` already uses — check
  `generate_kitty_specs_docs.py` for the exact loader). Accept a directory of rendered HTML
  files as input (mirror `seo_postprocess.py`'s CLI argument shape for consistency). Parse each
  HTML file's text content (use whatever HTML parsing library is already a project dependency —
  check `pyproject.toml`; do not add a new dependency without checking first).
- **T036 — Linking logic.** Implement exactly per the linker contract: walk text nodes skipping
  `<code>`, `<pre>`, `<script>`, `<style>`, and existing `<a>` inner text; match `surface`
  strings case-insensitively with **longest-match-first**; on first match per page, wrap in
  `<a href="/kitty-specs/glossary.html#term-{anchor_id}" class="glossary-link"
  title="{definition, HTML-escaped}">`; every subsequent occurrence on the same page stays
  plain text. Track per-page "already-linked" state explicitly (a set of matched terms, reset
  per file). Handle the failure mode from the contract: a missing/unparseable glossary entry
  logs a warning and is skipped, never crashes the whole pass.
- **T037 — Document the pipeline integration point.** Since this repo's docs build runs in CI
  only (no live DocFX build locally, per `redirect_stub_generator.py`'s own docstring), you
  cannot literally wire this into `.github/workflows/docs-pages.yml` and test it end-to-end
  locally — and C-001 puts pipeline-workflow changes out of scope anyway. Instead, write a short
  comment block at the top of `glossary_linker.py` documenting exactly where in the pipeline it
  should run (after DocFX render, alongside `seo_postprocess.py`, before the redirect-stub
  generation step) and how it would be invoked, so a future WP or the pipeline owner can wire it
  in without re-deriving this design.

## Branch Strategy

Planning artifacts were generated on `feat/docs-ia-onboarding-overhaul`. This WP branches from
that base during `/spec-kitty.implement` and merges back into `feat/docs-ia-onboarding-overhaul`.
No dependencies — starts immediately, independent of the content/nav work.

## Definition of Done

- [ ] Every one of the 104 glossary terms has a unique, stable `anchor_id`.
- [ ] Collision handling is implemented and provably correct (even if untriggered by current
      data).
- [ ] `glossary_linker.py` implements first-mention-only, longest-match-first,
      code-block-skipping linking exactly per the contract.
- [ ] The pipeline integration point is documented, not silently left unintegrated with no
      explanation.
- [ ] No markdown source file is touched anywhere in this WP's diff.

## Risks & Mitigations

- **No local DocFX build** means this WP's linker logic must be tested against synthetic/sample
  HTML fixtures, not a real site build — write a small local test harness (sample HTML input →
  assert expected output) rather than skipping verification entirely.
- **Longest-match-first correctness** is easy to get subtly wrong (e.g. sorting by length
  without also handling equal-length ties deterministically) — write it carefully and test with
  at least one deliberately overlapping pair of terms from the real 104-term list if one exists,
  or a synthetic example if not.

## Review Guidance

- Run the linker against a small synthetic HTML fixture containing: a term inside a `<code>`
  block (must NOT be linked), a term appearing twice in prose (only first linked), and two
  overlapping terms (longest wins).
- Confirm no markdown file appears in this WP's `git diff`.

## Activity Log

- {{TIMESTAMP}} – system – Prompt created.
- 2026-07-20T16:37:37Z – claude:sonnet-5:python-pedro:implementer – shell_pid=64169 – Assigned agent via action command
- 2026-07-20T16:51:34Z – claude:sonnet-5:python-pedro:implementer – shell_pid=64169 – Ready for review: anchor ids + glossary linker, 15 new tests, ruff clean
- 2026-07-20T17:22:33Z – claude:sonnet-5:python-pedro:reviewer – shell_pid=76558 – Started review via action command
- 2026-07-20T17:28:27Z – user – shell_pid=76558 – Review passed: FR-011/FR-012/NFR-004 satisfied. assign_anchor_ids() + glossary_page() anchor injection and glossary_linker.py both verified against contracts. mypy --explicit-package-bases scripts/docs/generate_kitty_specs_docs.py scripts/docs/glossary_linker.py: only 5 pre-existing errors, all baseline-identical to the base branch (lines 57/79/210/211, unrelated sort_key/markdown_to_html code) - zero new errors from WP08's code, and assign_anchor_ids imports/resolves cleanly (no unknown-symbol). pytest tests/docs/test_glossary_linker.py -v: 15/15 passed with real imports (no skips). Longest-match-first proven with real overlapping terms (main repository / main repository root) and repeat-on-page proven with a term appearing twice. Zero markdown files touched by WP08's own commit (WP09 task-file diff is coordination-branch merge noise, not WP08's authored content). Pipeline integration (T037) is documented with concrete insertion point + exact CLI invocation, legitimately deferred per C-001. ruff clean. All anti-pattern checklist items PASS.
