# WP08 Review Cycle 1 — Reviewer Feedback

Reviewer: codex:gpt-4o:reviewer-renata:reviewer
Verdict: Changes requested (one factual accuracy fix)

## Summary

Three new docs are well-structured, audience-appropriate, and comfortably over
the 150-line bar (explanation 274, how-to 434, migration 252). TOC entries are
present and YAML parses cleanly. All internal Markdown links resolve. Every CLI
command and every flag shown matches the real `--help` output verbatim
(`doctrine fetch --pack/--dry-run`, `doctrine pack validate --json`,
`doctrine pack assemble --conflicts-out/--force/--json`, `doctor doctrine --json`,
`charter context --action --json`, `charter lint`). All documented config keys
(`local_path`, `source_type`, `url`, `ref`, `name`) and all `org-charter.yaml`
fields (`schema_version`, `org_name`, `interview_defaults`, `required_directives`,
`governance_policies`) exist exactly as named in the pydantic models. Merge
semantics for org-charter composition match `org_charter.py` precisely. The
`_resolve_org_root` inert-stub explanation matches the source comments and the
architectural-test rationale faithfully. Multi-pack support in the FAQ is
correct: `PackRegistry` does accept multiple packs.

There is exactly **one factual accuracy issue** that must be fixed before
approval. It is small but it would mislead any reader who runs
`charter context --json` and greps the output for the documented literal.

## Issue 1 (must-fix): `source` field value is `"builtin"`, not `"built-in"`

The docs claim the resolved `source` provenance tag for shipped artifacts is the
literal string `built-in` (with hyphen). The code emits `builtin` (no hyphen).

**Evidence in code:**

- `src/charter/context.py:775` constrains the value:
  `"source": source if source in {"builtin", "org", "project"} else "builtin"`
- `src/doctrine/base.py:225` initialises provenance:
  `self._provenance = {k: "builtin" for k in self._items}`
- `src/doctrine/base.py:247` docstring: `Returns one of "builtin", "org", or "project"`

**Locations in docs that contradict the code:**

1. `docs/explanation/org-doctrine-layer.md:135` — the provenance table row reads
   `` | `built-in` | Shipped with the CLI | ``. Change the cell to `` `builtin` ``.

2. `docs/how-to/create-an-org-doctrine-pack.md:389` — the sentence reads
   "Resolved artifacts will have a `source` field of `built-in`, `org`, or
   `project`." Change `built-in` to `builtin`.

**Do NOT change** any of the prose uses of "built-in" elsewhere in the docs —
those are English prose ("the built-in layer", "shipped/built-in graph", etc.),
not literal field values, and they are fine. The fix is scoped to the two
places that present `built-in` as a literal `source` tag value.

## Out of scope (do not change)

- The scope expansion to per-section `docs/<section>/toc.yml` files alongside
  `docs/toc.yml` is necessary (those files hold the actual entries) and is not
  a defect.
- The subtask-ID mismatch between WP08 frontmatter (T038–T041) and any T049
  reference in `tasks.md` is content-covered by the three docs; not a defect.
- The "multiple org layers" FAQ answer is intentionally permissive because
  `PackRegistry` does support multiple packs. The task description's earlier
  "single org slot" note was superseded by WP02's multi-pack design.

## How to verify after the fix

```bash
# Should print zero matches:
grep -nE '\`built-in\`' docs/explanation/org-doctrine-layer.md docs/how-to/create-an-org-doctrine-pack.md docs/migration/doctrine-local-overlay-to-org-layer.md \
  | grep -E 'source|provenance|tag'
```

Once Issue 1 is fixed, the WP is approvable. No other changes requested.
