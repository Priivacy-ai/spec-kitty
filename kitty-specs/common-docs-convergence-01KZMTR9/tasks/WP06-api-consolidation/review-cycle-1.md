---
affected_files: []
cycle_number: 1
mission_slug: common-docs-convergence-01KZMTR9
reproduction_command:
reviewed_at: '2026-08-10T08:26:12Z'
reviewer_agent: user
wp_id: WP06
---

# WP06 Review — REJECTED (one owned-file body link broken by the move)

## Verdict
Reject. WP06 is 95% clean — renames preserve history, fixtures intact, kebab + single index,
audience/type/description all resolve, terminology green, WP13 flags complete. But **one criterion
genuinely fails**: an outbound body link **originating from a WP06-owned, moved file** now dangles as a
direct result of the move. The DoD explicitly requires "owned-file links resolve" and review
criterion #4 requires "no body links ORIGINATING from WP06-owned files dangle." This is a regression:
the link resolved before the move and is broken after.

## The one blocker

**File:** `docs/api/batch-api-contract.md` (moved from `contracts/batch-api-contract.md`, R098)
**Line (near end, "See also" for the tracker snapshot):**

```
See [tracker-snapshot-publish.md](../kitty-specs/048-tracker-publish-resource-routing/contracts/tracker-snapshot-publish.md) ...
```

- At the **old** path `contracts/`, `../kitty-specs/...` resolved to `<repo-root>/kitty-specs/...` — **correct**.
- At the **new** path `docs/api/`, `../kitty-specs/...` resolves to `docs/kitty-specs/...` — **does not exist (404 in rendered docs)**.
- The target file **does exist** at `<repo-root>/kitty-specs/048-tracker-publish-resource-routing/contracts/tracker-snapshot-publish.md`.

**Fix (trivial):** bump the relative depth by one segment —
`../kitty-specs/...` → `../../kitty-specs/...`
(`docs/api/../../kitty-specs/...` = `<repo-root>/kitty-specs/...`, verified to resolve).

This is NOT a WP13 reference-sweep item: WP13 owns **inbound** refs from non-owned files. This is an
**outbound** link inside the file WP06 itself moved, so it is WP06's to fix. `relative_link_fixer`
(which the task instructed you to run on owned files) evidently did not touch cross-boundary
`docs/ → kitty-specs/` links; fix it by hand or extend the tool's scope.

## What passed (for the record — do NOT redo)
- **T017:** `docs/reference/` fully gone (no empty dir); skills/ + agent_profiles/ folded into `docs/api/`
  as git renames (R79–R98, history preserved); umbrella + `docs/api/README.md` + `docs/reference/index.md` deleted.
- **T018:** contract rehomed as a rename; `contracts/fixtures/*.json` untouched (5 fixtures intact, C-002 satisfied);
  three api indexes reconciled to a single `docs/api/index.md`; `docs/api/toc.yml` regenerated.
- **T019:** `docs/api/` is kebab-case; exactly one top-level `index.md`; `audience:` on the substantively-authored
  index/contract pages resolves (`docs/context/audience/internal/maintainer.md`,
  `docs/context/audience/internal/lead-developer.md` both exist); descriptions 102–176 chars (all in 50–180);
  `type: reference` set. Leaf profile page (curator-carla) frontmatter compliant.
- **Frontmatter `related:` links** from owned files all resolve; `test_related_validator.py` 18 passed.
- **Terminology:** `test_no_legacy_terminology.py` green.
- **WP13 flags:** complete and accurate (docfx.json dead globs incl. the description-gate cause, global toc.yml,
  inventory yaml, inbound dangling links, docstrings, stale fixture, scripts/docs comments).
- **description-gate reds (2)** correctly attributed to WP13-owned `docs/docfx.json` `reference/**.md` dead glob —
  independently confirmed (the ValueError names docfx.json's vacuous glob, not any WP06 page). Not a WP06 defect.

## Scope to re-touch
Only the single link in `docs/api/batch-api-contract.md`. Do not re-do the moves or frontmatter.
