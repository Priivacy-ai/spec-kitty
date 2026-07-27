# Decision Moment `01KY03YGX7GQEBKV45Q2Q8FXK3`

- **Mission:** `docs-ia-onboarding-overhaul-01KY02JB`
- **Origin flow:** `plan`
- **Slot key:** `plan.glossary.linker-mechanism`
- **Input key:** `glossary_linker_mechanism`
- **Status:** `resolved`
- **Created:** `2026-07-20T15:57:37.575845+00:00`
- **Resolved:** `2026-07-20T16:04:19.200603+00:00`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

Should the glossary auto-linker rewrite markdown source files directly (baking [term](link) markup into .md prose), or run as a build-time post-processing pass over DocFX's rendered HTML output (like the existing seo_postprocess.py), leaving markdown source untouched?

## Options

- Rewrite markdown source
- Post-process rendered HTML
- Other

## Final answer

Post-process rendered HTML output at build time (like seo_postprocess.py); markdown source stays untouched.

## Rationale

_(none)_

## Change log

- `2026-07-20T15:57:37.575845+00:00` — opened
- `2026-07-20T16:04:19.200603+00:00` — resolved (final_answer="Post-process rendered HTML output at build time (like seo_postprocess.py); markdown source stays untouched.")
