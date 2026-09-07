# Decision Moment `01M1V8J667A286GPHKTWYB1WCS`

- **Mission:** `fsm-write-path-integrity-01M1TZV6`
- **Origin flow:** `plan`
- **Slot key:** `plan.wp02.emit-privates-landing`
- **Input key:** `emit_privates_landing`
- **Status:** `resolved`
- **Created:** `2026-09-06T11:44:51.399381+00:00`
- **Resolved:** `2026-09-06T12:44:26.919507+00:00`
- **Resolved by:** `claude-fable-5-1`
- **Opened by:** `cli`
- **Other answer:** `true`

## Question

Q6: Do the five _emit privates become pipeline-internal or narrow public helpers? (implementation detail; frontmatter lane mirror must stay the only write_frontmatter of lane)

## Options

- Defer to WP02 implementer
- Pipeline-internal
- Public helpers
- Other

## Final answer

Module-private in status/emit.py; the pipeline consumes them via the same-package module reference (from . import emit as _emit), attribute-resolved at call time; nothing becomes public; _mirror_phase1_frontmatter_lane stays the only write_frontmatter of lane and is called only by shells

## Rationale

Reads (_derive_from_lane, _infer_*) and the one write (_mirror_phase1_frontmatter_lane) are shell concerns; status->status reference is layering-clean (C-006); no facade widening (status/__init__ untouched); call-time resolution keeps existing emit_module monkeypatches effective. Full note: design-notes/WP02-pipeline.md section 3.

## Change log

- `2026-09-06T11:44:51.399381+00:00` — opened
- `2026-09-06T12:44:26.919507+00:00` — resolved (final_answer="Module-private in status/emit.py; the pipeline consumes them via the same-package module reference (from . import emit as _emit), attribute-resolved at call time; nothing becomes public; _mirror_phase1_frontmatter_lane stays the only write_frontmatter of lane and is called only by shells")
