# Decision Moment `01KT1YJ5PJ8MV48KZF53XEE3NV`

- **Mission:** `org-doctrine-profile-integrity-activation-closure-01KT1TV1`
- **Origin flow:** `plan`
- **Slot key:** `plan.templates.identity`
- **Input key:** `template_identity`
- **Status:** `resolved`
- **Created:** `2026-06-01T15:59:11.570711+00:00`
- **Resolved:** `2026-06-01T16:00:24.139069+00:00`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

#1333: templates today are resolved by name/path through 5 tiers, have no ID and no file extension, and live in mission-scoped dirs. To make them DRG-addressable (template:<id>) and listable per C-009, what identity scheme should templates use?

## Options

- Mission-qualified name as ID (e.g. software-dev/spec) minted as DRG template nodes
- Add explicit id field/frontmatter to template files, mint DRG nodes from it
- Discovery+listing only; do NOT make templates DRG nodes (keep name-based resolution)

## Final answer

Mission-qualified name as template ID (e.g. software-dev/spec). Mint DRG template nodes from the existing tier+mission+filename layout — no template-file frontmatter churn. Disambiguates same-named templates across missions; templates become DRG-addressable (template:<id>) per C-009.

## Rationale

_(none)_

## Change log

- `2026-06-01T15:59:11.570711+00:00` — opened
- `2026-06-01T16:00:24.139069+00:00` — resolved (final_answer="Mission-qualified name as template ID (e.g. software-dev/spec). Mint DRG template nodes from the existing tier+mission+filename layout — no template-file frontmatter churn. Disambiguates same-named templates across missions; templates become DRG-addressable (template:<id>) per C-009.")
